# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
import threading
import uuid
import requests
import urllib3

urllib3.disable_warnings()

sys.path.append('..')
from base.spider import Spider
import time
from Crypto.Hash import MD5, SHA1


class Spider(Spider):
    '''
    配置示例：
    {
        "key": "py_文才",
        "name": "文才影视(T3)",
        "type": 3,
        "api": "./py/文才影视.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "ext": {
            "site": "https://www.hkybqufgh.com,https://www.sizhengxt.com,https://0996zp.com,https://9zhoukj.com,https://www.tjrongze.com,https://www.jiabaide.cn,https://cqzuoer.com"
        }
    },
    '''
    # ==================== 默认站点(多域名自动测速择优) ====================
    DEFAULT_SITES = [
        'https://www.hkybqufgh.com',
        'https://www.sizhengxt.com',
        'https://0996zp.com',
        'https://9zhoukj.com',
        'https://www.tjrongze.com',
        'https://www.jiabaide.cn',
        'https://cqzuoer.com',
    ]

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

    # ==================== 微信推广文案 (XOR 加密存储) ====================
    _W_KEY = 'wencai_wechat_2026'
    # 解密内容: '微信公众号：源力软件汇\n更多优质资源尽在源力捐赠版'
    _W_FULL_DATA = [24537, 20356, 20738, 20340, 21398, 65395, 28367, 21228, 36618, 20117,
                    27695, 107, 26240, 22853, 20266, 36120, 36214, 28326, 23626, 22349,
                    28414, 21240, 25393, 36105, 29207]

    def _w_decrypt(self, data):
        key = self._W_KEY
        try:
            return ''.join(chr(v ^ ord(key[i % len(key)])) for i, v in enumerate(data))
        except Exception:
            return ''

    def _get_wechat_info(self):
        """返回推广文案 (运行时解密)"""
        return self._w_decrypt(self._W_FULL_DATA)

    def init(self, extend=""):
        hosts = None
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else extend
                if isinstance(ext, dict):
                    hosts = ext.get('site')
                elif isinstance(ext, str):
                    hosts = ext
            except Exception:
                hosts = extend
        if isinstance(hosts, str):
            hosts = [u.strip() for u in hosts.split(',') if u.strip()]
        if not hosts:
            hosts = self.DEFAULT_SITES
        self.host = self.host_late(hosts).rstrip('/')

    def getName(self):
        return '文才影视'

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # ==================== 基础请求 ====================
    def _api(self, path, params=None):
        url = f"{self.host}{path}"
        if params:
            url += '?' + self.js(params)
        return self.fetch(url, headers=self.getheaders(dict(params or {}))).json()

    def homeContent(self, filter):
        classes = []
        try:
            cdata = self._api('/api/mw-movie/anonymous/get/filer/type')
            for k in (cdata.get('data') or []):
                if k.get('typeJumpurl'):
                    continue  # 跳转类目(如体育直播)不作为点播分类
                classes.append({'type_name': k['typeName'], 'type_id': str(k['typeId'])})
        except Exception:
            pass
        if not classes:
            classes = [{'type_name': n, 'type_id': t} for t, n in
                       (('1', '电影'), ('2', '电视剧'), ('3', '综艺'), ('4', '动漫'), ('88', '短剧'))]

        # 细化类型挂在对应一级分类的筛选面板下: 点分类 → 筛选 → 类型/剧情
        filters = {}
        try:
            fdata = self._api('/api/mw-movie/anonymous/v1/get/filer/list')
            for tid, d in (fdata.get('data') or {}).items():
                filters[tid] = self._build_filters(d, is_movie=(tid == '1'))
        except Exception:
            pass

        return {'class': classes, 'filters': filters}

    def _build_filters(self, d, is_movie=False):
        groups = []
        value = [{'n': i['itemText'], 'v': i['itemValue']} for i in (d.get('typeList') or [])]
        if value:
            groups.append({'key': 'type', 'name': '类型', 'value': value})
        value = [{'n': i['itemText'], 'v': i['itemText']} for i in (d.get('plotList') or [])]
        if value:
            groups.append({'key': 'v_class', 'name': '剧情', 'value': value})
        for key, name, field in (('area', '地区', 'districtList'), ('year', '年份', 'yearList'),
                                 ('lang', '语言', 'languageList')):
            value = [{'n': i['itemText'], 'v': i['itemText']} for i in (d.get(field) or [])]
            if value:
                groups.append({'key': key, 'name': name, 'value': value})
        sort_values = [{'n': '最近更新', 'v': '2'}, {'n': '人气高低', 'v': '3'}, {'n': '评分高低', 'v': '4'}]
        if is_movie:
            sort_values = sort_values[1:]
        groups.append({'key': 'sort', 'name': '排序', 'value': sort_values})
        return groups

    def homeVideoContent(self):
        vods = []
        try:
            data = self._api('/api/mw-movie/anonymous/v1/home/all/list')
            for i in (data.get('data') or {}).values():
                vods.extend(i.get('list') or [])
        except Exception:
            pass
        try:
            data = self._api('/api/mw-movie/anonymous/home/hotSearch')
            vods.extend(data.get('data') or [])
        except Exception:
            pass
        seen = set()
        uniq = []
        for v in vods:
            vid = v.get('vodId')
            if vid in seen:
                continue
            seen.add(vid)
            uniq.append(v)
        return {'list': self.getvod(uniq)}

    def categoryContent(self, tid, pg, filter, extend):
        if extend is None:
            extend = {}
        if isinstance(extend, str):
            try:
                extend = json.loads(extend) if extend else {}
            except Exception:
                extend = {}
        if '_' in tid:
            tid = tid.split('_', 1)[0]  # 兼容旧版子分类ID格式
        pg = str(pg) if str(pg).isdigit() else '1'
        params = {
            "area": extend.get('area', ''),
            "filterStatus": "1",
            "lang": extend.get('lang', ''),
            "pageNum": pg,
            "pageSize": "30",
            "sort": extend.get('sort', '1'),
            "sortBy": "1",
            "type": extend.get('type', ''),
            "type1": tid,
            "v_class": extend.get('v_class', ''),
            "year": extend.get('year', '')
        }
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 30, 'total': 999999}
        try:
            data = self._api('/api/mw-movie/anonymous/video/list', params)
            d = data.get('data') or {}
            result['list'] = self.getvod(d.get('list') or [])
            if d.get('totalPage'):
                result['pagecount'] = int(d['totalPage'])
            if d.get('totalCount'):
                result['total'] = int(d['totalCount'])
        except Exception:
            pass
        return result

    def detailContent(self, ids):
        vid = str(ids[0])
        data = self._api('/api/mw-movie/anonymous/video/detail', {'id': vid})
        d = data.get('data') or {}
        if not d:
            return {'list': []}
        vod = self.getvod([d])[0]
        # 简介: 去除HTML标签并前置推广文案
        content = vod.get('vod_content') or vod.get('vod_blurb') or ''
        content = re.sub(r'<[^>]+>', '', content).strip()
        vod['vod_content'] = self._get_wechat_info() + '\n' + content if content else self._get_wechat_info()
        eps = vod.get('episodelist') or []
        if len(eps) > 1:
            vod['vod_play_url'] = '#'.join(
                f"{(i.get('name') or f'第{n + 1}集')}${vid}@@{i.get('nid')}" for n, i in enumerate(eps))
        elif eps:
            vod['vod_play_url'] = f"{vod.get('vod_name', '')}${vid}@@{eps[0].get('nid')}"
        else:
            vod['vod_play_url'] = f"{vod.get('vod_name', '')}${vid}@@1"
        vod['vod_play_from'] = '文才影视'
        vod.pop('episodelist', None)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg) if str(pg).isdigit() else '1'
        params = {
            "keyword": key,
            "pageNum": pg,
            "pageSize": "8",
            "sourceCode": "1"
        }
        try:
            data = self._api('/api/mw-movie/anonymous/video/searchByWord', params)
            vods = self.getvod(((data.get('data') or {}).get('result') or {}).get('list') or [])
            return {'list': vods, 'page': pg}
        except Exception:
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        # CDN强制校验Referer/Origin, 缺失返回403
        self.header = {
            'User-Agent': self.UA,
            'Referer': f'{self.host}/',
            'Origin': self.host
        }
        ids = str(id).split('@@')
        vlist = []
        for attempt in range(2):
            try:
                pdata = self._api('/api/mw-movie/anonymous/v2/video/episode/url',
                                  {'clientType': '1', 'id': ids[0], 'nid': ids[1]})
                plist = ((pdata.get('data') or {}).get('list')) or []
                playable = [i for i in plist if not i.get('flag')]  # 过滤VIP锁定线路
                for i in (playable if playable else plist):
                    if i.get('url'):
                        vlist.extend([i.get('resolutionName') or '默认', i['url']])
                if vlist:
                    break
            except Exception:
                pass
            time.sleep(0.4)
        return {'parse': 0, 'url': vlist, 'header': self.header}

    def localProxy(self, param):
        pass

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',') if u.strip()]
        else:
            urls = [str(u).strip().rstrip('/') for u in url_list if str(u).strip()]
        urls = [u for u in urls if u]
        if not urls:
            return ''
        if len(urls) == 1:
            return urls[0]

        results = {}
        threads = []

        def test_host(url):
            delay = float('inf')
            for _ in range(2):
                try:
                    start_time = time.time()
                    requests.head(url, timeout=1.5, allow_redirects=False, verify=False)
                    delay = (time.time() - start_time) * 1000
                    break
                except Exception:
                    try:
                        start_time = time.time()
                        requests.get(url, timeout=2.5, allow_redirects=False, verify=False)
                        delay = (time.time() - start_time) * 1000
                        break
                    except Exception:
                        continue
            results[url] = delay

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return min(results.items(), key=lambda x: x[1])[0]

    def md5(self, sign_key):
        md5_hash = MD5.new()
        md5_hash.update(sign_key.encode('utf-8'))
        return md5_hash.hexdigest()

    def js(self, param):
        return '&'.join(f"{k}={v}" for k, v in param.items())

    def getheaders(self, param=None):
        if param is None:
            param = {}
        t = str(int(time.time() * 1000))
        param['key'] = 'cb808529bae6b6be45ecfab29a4889bc'
        param['t'] = t
        sha1_hash = SHA1.new()
        sha1_hash.update(self.md5(self.js(param)).encode('utf-8'))
        sign = sha1_hash.hexdigest()
        headers = {
            'User-Agent': self.UA,
            'Accept': 'application/json, text/plain, */*',
            'sign': sign,
            't': t,
            'deviceid': str(uuid.uuid4())
        }
        return headers

    def convert_field_name(self, field):
        field = field.lower()
        if field.startswith('vod') and len(field) > 3:
            field = field.replace('vod', 'vod_')
        if field.startswith('type') and len(field) > 4:
            field = field.replace('type', 'type_')
        return field

    def getvod(self, array):
        out = []
        for item in array:
            d = {self.convert_field_name(k): v for k, v in item.items()}
            if not d.get('vod_remarks') and d.get('vod_version'):
                d['vod_remarks'] = d['vod_version']
            out.append(d)
        return out
