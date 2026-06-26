# -*- coding: utf-8 -*-

import re
import json
import time
import uuid
import zlib
import gzip
import base64
import hashlib
import urllib.parse
import urllib.request
import urllib.error

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from base.spider import Spider


class Spider(Spider):

    host = ''
    api = ''
    appkey = ''
    version = ''
    uuid_str = ''
    token = ''
    user_agent = ''

    config = {}
    init_data = {}

    headers_base = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'client_type': 'android',
        'api_version': 'v1'
    }

    def init(self, extend=''):
        self.log('99APP 初始化开始')
        try:
            if isinstance(extend, str):
                extend = json.loads(extend)
            self.config = extend
            self.host = extend.get('host', '').rstrip('/')
            self.api = self.host
            self.appkey = extend.get('appkey', '')
            self.version = extend.get('version', '0b4328287a5d953e')
            self.user_agent = extend.get('ua', self.headers_base['User-Agent'])
            self.uuid_str = str(uuid.uuid4())
            self.token = ''

            self.system_init()
            self.user_login()

        except Exception as e:
            self.log(f'初始化失败: {e}')

    def system_init(self):
        try:
            data = {
                'v': self.config.get('versionName', '1.0.0'),
                'n': self.config.get('name', ''),
                's': self.config.get('buildSignature', ''),
                'pl': '1',
                'apiVersion': 'v2',
                'token': '',
                'timestamp': self.timestamp(),
                'nonce': self.nonce()
            }
            res = self.request('/app/systemInit', data)
            self.init_data = res or {}
        except Exception as e:
            self.log(f'systemInit失败: {e}')

    def user_login(self):
        try:
            path = self.config.get('LoginPath', '/app/userInfo')
            device_id = str(uuid.uuid4()).replace('-', '')
            data = {
                'os': 'android',
                'name': 'xiaomi',
                'version': '15',
                'sdkInt': 32,
                'device': 'xiaomi',
                'brand': 'xiaomi',
                'manufacturer': 'xiaomi',
                'product': 'xiaomi',
                'hardware': 'qcom',
                'isPhysicalDevice': True,
                'androidId': 'V417IR',
                'bootloader': 'unknown',
                'display': 'V417IR release-keys',
                'host': 'a11-gz01-test',
                'tags': 'release-keys',
                'type': 'user',
                'finger': 'xiaomi/b0q/b0q:15/V619IR/613:user/release-keys',
                'app': {
                    'version': self.config.get('versionName', ''),
                    'name': self.config.get('name', ''),
                    'package': self.config.get('package', ''),
                    'buildNumber': self.config.get('buildNumber', ''),
                    'buildSignature': self.config.get('buildSignature', '')
                },
                'did': device_id,
                'apiVersion': 'v2',
                'channel': '',
                'token': '',
                'timestamp': self.timestamp(),
                'nonce': self.nonce()
            }
            res = self.request(path, data)
            if res.get('userInfo'):
                self.token = res['userInfo'].get('user_token', '')
            if not self.token:
                self.token = device_id
        except Exception as e:
            self.log(f'登录失败: {e}')

    # ==================== 分类排序辅助函数 ====================
    def sort_categories(self, categories, sort_str):
        """根据 sort_str 排序分类列表，未匹配的放最后"""
        if not sort_str:
            return categories
        order_list = [x.strip() for x in sort_str.split('>')]
        # 构建排序键
        def get_order(cat):
            name = cat.get('type_name', '')
            for idx, kw in enumerate(order_list):
                if kw in name:  # 模糊匹配
                    return idx
            return len(order_list)  # 未匹配的放最后
        return sorted(categories, key=get_order)

    # ==================== 线路排序辅助函数 ====================
    def sort_sources(self, keys, player_map, sort_str):
        """根据 sort_str 对线路（播放源）进行排序，支持模糊匹配，未匹配的按原 sort 值排序但排在匹配后面"""
        if not sort_str:
            # 如果没有配置，按原 sort 降序
            return sorted(keys, key=lambda x: player_map.get(x, {}).get('sort', 0), reverse=True)
        
        order_list = [x.strip() for x in sort_str.split('>')]
        matched = []
        unmatched = []
        for key in keys:
            player_name = player_map.get(key, {}).get('name', key)
            matched_flag = False
            for idx, kw in enumerate(order_list):
                if kw in player_name or kw in key:  # 模糊匹配线路名或源key
                    matched.append((idx, key))
                    matched_flag = True
                    break
            if not matched_flag:
                unmatched.append(key)
        # 匹配的部分按 order_list 顺序排序
        matched.sort(key=lambda x: x[0])
        matched_keys = [item[1] for item in matched]
        # 未匹配的部分按原 sort 降序
        unmatched.sort(key=lambda x: player_map.get(x, {}).get('sort', 0), reverse=True)
        return matched_keys + unmatched

    # ==================== homeContent 增加分类排序 ====================
    def homeContent(self, filter):
        result = {'class': [], 'filters': {}}
        try:
            categorys = self.init_data.get('categorys', {})
            data = categorys.get('data', [])
            sort_values = [
                {'n': '最新', 'v': 'time'},
                {'n': '高分', 'v': 'vod_score'},
                {'n': '最热', 'v': 'vod_hits'},
                {'n': '日热度', 'v': 'vod_hits_day'},
                {'n': '周热度', 'v': 'vod_hits_week'},
                {'n': '月热度', 'v': 'vod_hits_month'}
            ]
            # 构建原始分类列表
            raw_categories = []
            for item in data:
                tid = str(item.get('id'))
                name = item.get('name', '')
                raw_categories.append({'type_id': tid, 'type_name': name})
                filters = []
                extend = {}
                try:
                    extend = json.loads(item.get('type_extend', '{}'))
                except:
                    pass
                if extend.get('class'):
                    values = [{'n': '全部', 'v': ''}]
                    for i in extend['class'].split(','):
                        values.append({'n': i, 'v': i})
                    filters.append({'key': 'class', 'name': '类型', 'value': values})
                if extend.get('area'):
                    values = [{'n': '全部', 'v': ''}]
                    for i in extend['area'].split(','):
                        values.append({'n': i, 'v': i})
                    filters.append({'key': 'area', 'name': '地区', 'value': values})
                if extend.get('lang'):
                    values = [{'n': '全部', 'v': ''}]
                    for i in extend['lang'].split(','):
                        values.append({'n': i, 'v': i})
                    filters.append({'key': 'lang', 'name': '语言', 'value': values})
                if extend.get('year'):
                    values = [{'n': '全部', 'v': ''}]
                    for i in extend['year'].split(','):
                        values.append({'n': i, 'v': i})
                    filters.append({'key': 'year', 'name': '年份', 'value': values})
                filters.append({'key': 'sort', 'name': '排序', 'value': sort_values})
                result['filters'][tid] = filters
            
            # 应用分类排序
            category_sort_str = self.config.get('category_sort', '')
            sorted_categories = self.sort_categories(raw_categories, category_sort_str)
            result['class'] = sorted_categories

        except Exception as e:
            self.log(f'homeContent失败: {e}')
        return result

    def homeVideoContent(self):
        data = {
            'kw': '',
            'page': '1',
            'limit': 21,
            'pid': '1',
            'orderBy': 'time',
            'isCategory': 1,
            'token': '',
            'timestamp': self.timestamp(),
            'nonce': self.nonce()
        }
        res = self.request('/vod/search', data)
        return {'list': self.parse_vods(res.get('data', []))}

    def categoryContent(self, tid, pg, filter, extend):
        data = {
            'pid': str(tid),
            'page': str(pg),
            'limit': 21,
            'kw': extend.get('class', ''),
            'orderBy': extend.get('sort', 'time'),
            'isCategory': 1,
            'token': self.token,
            'timestamp': self.timestamp(),
            'nonce': self.nonce()
        }
        if extend.get('class'):
            data['type'] = 'class'
        if extend.get('area'):
            data['area'] = extend['area']
        if extend.get('lang'):
            data['lang'] = extend['lang']
        if extend.get('year'):
            data['year'] = extend['year']
        res = self.request('/vod/search', data)
        return {
            'list': self.parse_vods(res.get('data', [])),
            'page': int(pg),
            'pagecount': res.get('page_count', 1),
            'limit': 21,
            'total': 9999
        }

    def searchContent(self, key, quick=False, pg='1'):
        data = {
            'kw': key,
            'page': int(pg),
            'limit': 21,
            'orderBy': 'vod_hits_month',
            'sort': 'desc',
            'token': self.token,
            'timestamp': self.timestamp(),
            'nonce': self.nonce()
        }
        res = self.request('/vod/search', data)
        return {
            'list': self.parse_vods(res.get('data', [])),
            'page': int(pg),
            'pagecount': res.get('page_count', 1)
        }

    # ==================== detailContent 增加线路排序 ====================
    def detailContent(self, ids):
        vid = ids[0]
        data = {
            'id': vid,
            'eps': '1',
            'v': '2.0.0',
            'pl': 1,
            'token': self.token,
            'timestamp': self.timestamp(),
            'nonce': self.nonce()
        }
        res = self.request('/vod/detail', data)
        info = res.get('data', {})
        player_map = self.init_data.get('player', {})
        play_from = []
        play_url = []
        pf = info.get('play_from', '').split('$$$')
        pu = info.get('play_url', '').split('$$$')
        temp = {}
        for i in range(len(pf)):
            if i < len(pu):
                temp[pf[i]] = pu[i]
        keys = list(player_map.keys())
        # 应用线路排序
        source_sort_str = self.config.get('source_sort', '')
        sorted_keys = self.sort_sources(keys, player_map, source_sort_str)
        
        vod_name = info.get('name', '')

        for key in sorted_keys:
            if key not in temp:
                continue
            p = player_map.get(key, {})
            enable = str(p.get('enable_show', '1'))
            if enable not in ['1', 'true', 'True']:
                continue
            from_name = p.get('name', key)
            urls = []
            episodes = temp[key].split('#')
            for idx, item in enumerate(episodes, start=1):
                if '$' not in item:
                    continue
                parts = item.split('$', 1)
                enc_id = parts[1]
                urls.append(f'{idx}${enc_id}@{key}@{vod_name}@{idx}')
            if urls:
                play_from.append(from_name)
                play_url.append('#'.join(urls))
        vod = {
            'vod_id': info.get('id'),
            'vod_name': vod_name,
            'vod_pic': info.get('pic'),
            'vod_remarks': info.get('remarks'),
            'vod_year': info.get('year'),
            'vod_area': info.get('area'),
            'vod_actor': info.get('actor'),
            'vod_director': info.get('director'),
            'vod_content': info.get('content'),
            'type_name': info.get('class'),
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }
        return {'list': [vod]}

    # ==================== playerContent 保持不变（已正常工作） ====================
    def playerContent(self, flag, pid, vipFlags):
        parse = 0
        jx = 0
        header = {}
        final_url = ''

        try:
            parts = pid.split('@')
            if len(parts) < 4:
                return {'parse': 1, 'jx': 0, 'url': pid, 'header': {}}

            video_id = parts[0]
            source = parts[1]
            vod_name = parts[2]
            episode = parts[3]

            players = self.init_data.get('player', {})
            player_cfg = players.get(source, {})
            ptype = player_cfg.get('type', 0)

            parser_list = self.init_data.get('parser_api', [])
            whitelist = player_cfg.get('parseUrl', '').split(',') if player_cfg.get('parseUrl') else []

            for parser in parser_list:
                if whitelist and str(parser.get('id')) not in whitelist:
                    continue
                supports = parser.get('api_supports_code', '')
                if supports and source not in supports.split(','):
                    continue
                api_type = parser.get('api_type', '')
                if api_type == 'json' and parser.get('is_server_parser') == 1:
                    pdata = {
                        'id': parser.get('id'),
                        'url': video_id,
                        'token': self.token,
                        'timestamp': self.timestamp(),
                        'nonce': self.nonce()
                    }
                    try:
                        res = self.request('/app/vodParser', pdata)
                        purl = res.get('data', '')
                        if purl and purl.startswith('http'):
                            final_url = purl
                            parse = 0
                            break
                    except Exception as e:
                        self.log(f'服务器解析失败: {e}')
                        continue
                else:
                    api_url = parser.get('api_url', '')
                    if api_url and api_url.startswith('http'):
                        req_url = api_url + video_id
                        req_headers = {
                            'User-Agent': self.user_agent,
                            'Accept': 'application/json',
                            'client_type': 'android'
                        }
                        try:
                            req = urllib.request.Request(req_url, headers=req_headers)
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                data = json.loads(resp.read().decode('utf-8'))
                                purl = data.get('url') or data.get('data') or data.get('play_url') or data.get('video_url')
                                if purl and purl.startswith('http'):
                                    final_url = purl
                                    parse = 0
                                    break
                        except Exception as e:
                            self.log(f'webview解析失败: {e}')
                            continue

            if not final_url:
                final_url = video_id
                parse = 1

            if re.search(r'www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili', final_url):
                jx = 1

            if ptype == 2:
                header = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6299.95 Safari/537.36'
                }

        except Exception as e:
            self.log(f'playerContent异常: {e}')
            final_url = pid
            parse = 1

        return {'parse': parse, 'jx': jx, 'url': final_url, 'header': header}

    def parse_vods(self, arr):
        videos = []
        for item in arr:
            videos.append({
                'vod_id': item.get('id'),
                'vod_name': item.get('name'),
                'vod_pic': item.get('pic'),
                'vod_remarks': item.get('remarks'),
                'vod_year': item.get('year'),
                'vod_content': item.get('blurb'),
                'type_name': item.get('class'),
                'vod_area': item.get('area'),
                'vod_actor': item.get('actor'),
                'vod_director': item.get('director')
            })
        return videos

    def request(self, path, data):
        try:
            body = self.encrypt(json.dumps(data))
            headers = self.build_headers(body)
            url = self.api + path
            res = self.post(url=url, data=body, headers=headers)
            text = res.text.strip()
            dec = self.decrypt(text)
            return json.loads(dec)
        except Exception as e:
            self.log(f'request失败: {e}')
            return {}

    def encrypt(self, text):
        key = self.uuid_str.replace('-', '').encode('utf-8')
        iv = self.random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        enc = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
        return base64.b64encode(iv + enc).decode()

    def decrypt(self, text):
        try:
            key = self.uuid_str.replace('-', '').encode('utf-8')
            raw = base64.b64decode(text)
            iv = raw[:16]
            data = raw[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            dec = unpad(cipher.decrypt(data), AES.block_size)
            try:
                dec = gzip.decompress(dec)
            except:
                try:
                    dec = zlib.decompress(dec)
                except:
                    pass
            return dec.decode('utf-8')
        except Exception as e:
            self.log(f'decrypt失败: {e}')
            return '{}'

    def build_headers(self, body):
        timestamp = self.timestamp()
        nonce = self.nonce()
        sign_str = f'{nonce}:{timestamp}:{body}:{self.token}:{self.appkey}'
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        headers = self.headers_base.copy()
        headers.update({
            'appkey': self.appkey,
            'version': self.version,
            'uuid': self.uuid_str,
            'timestamp': timestamp,
            'sign': sign,
            'nonce': nonce
        })
        headers['User-Agent'] = self.user_agent
        return headers

    def random_bytes(self, n):
        return bytes([int(time.time() * 1000 + i) % 256 for i in range(n)])

    def timestamp(self):
        return str(int(time.time() * 1000))

    def nonce(self):
        return base64.b64encode(uuid.uuid4().bytes).decode()

    def getName(self):
        return '99APP'

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass