# -*- coding: utf-8 -*-
# by @嗷呜
import re, os, sys, time, json, uuid, binascii, requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Util.Padding import unpad, pad
from Crypto.Hash import MD5
sys.path.append('..')

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

class Spider(Spider):

    fallback_hosts = [
        'http://42.193.137.125:2025',
        'http://42.193.137.125:8891',
        'https://bysp2.10000.im',
        'http://42.193.137.125:9984',
        'https://bysp.10000.im'
    ]

    # 播放兜底资源站（原站解析服务只返回"更新提示"视频，需要外部资源站兜底）
    cj_apis = {
        '光速资源': 'https://api.guangsuapi.com/api.php/provide/vod/',
        '红牛资源': 'https://www.hongniuzy2.com/api.php/provide/vod/',
        '金鹰资源': 'https://jinyingzy.com/api.php/provide/vod/',
        '速播资源': 'https://subocaiji.com/api.php/provide/vod/',
        '新浪资源': 'https://api.xinlangapi.com/xinlangapi.php/provide/vod/'
    }

    filter_names = {'type': '类型', 'area': '地区', 'lang': '语言', 'year': '年份'}

    # 细化后的类型筛选（n 为显示名称，v 为接口实际使用的关键词）
    type_extend = {
        '1': [('动作片', '动作'), ('喜剧片', '喜剧'), ('爱情片', '爱情'), ('科幻片', '科幻'),
              ('奇幻片', '奇幻'), ('战争片', '战争'), ('犯罪片', '犯罪'), ('悬疑片', '悬疑'),
              ('惊悚片', '惊悚'), ('恐怖片', '恐怖'), ('冒险片', '冒险'), ('武侠片', '武侠'),
              ('历史片', '历史'), ('文艺片', '文艺'), ('动画片', '动画'), ('剧情片', '剧情'),
              ('青春片', '青春'), ('纪录片', '纪录'), ('灾难片', '灾难'), ('古装片', '古装'),
              ('网络电影', '网络电影')],
        '2': [('古装', '古装'), ('都市', '都市'), ('历史', '历史'), ('谍战', '谍战'),
              ('家庭', '家庭'), ('年代', '年代'), ('宫廷', '宫廷'), ('悬疑', '悬疑'),
              ('爱情', '爱情'), ('喜剧', '喜剧'), ('战争', '战争'), ('犯罪', '犯罪'),
              ('青春', '青春'), ('武侠', '武侠'), ('玄幻', '玄幻'), ('仙侠', '仙侠'),
              ('农村', '农村'), ('情景', '情景'), ('商战', '商战'), ('网剧', '网剧'),
              ('其他', '其他')]
    }

    mp_notice = '<p style="color:#ff5a00;font-weight:bold;">微信公众号：源力软件汇</p>'

    def init(self, extend=""):
        try:
            self.host = self.gethost()
        except Exception as e:
            print(f'获取服务器失败: {e}')
            self.host = self.fallback_hosts[0]

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'AppID': '534',
        'app_id': '534',
        'version': '1.0.3',
        'package': 'com.hjmore.wallpaper',
        'user_id': '3507f394e83d2424',
        'user-id': '3507f394e83d2424',
        'app_name': 'lanlan',
        'app-name': 'lanlan',
        'Content-Type': 'application/json; charset=utf-8;',
        'User-Agent': 'okhttp/4.9.0'
    }

    def homeContent(self, filter):
        hdata = self.getdata('/api.php/provide/index', self.getbody({'tid': '0'}))
        vlist = hdata['data'].get('tj', [])
        result = {}
        classes = []
        filters = {}
        for i in hdata['data']['sub_data']:
            id = str(i['type_id'])
            classes.append({'type_id': id, 'type_name': i['type_name']})
            if len(i['data']):
                vlist.extend(i['data'])
        with ThreadPoolExecutor(max_workers=len(classes)) as executor:
            results = executor.map(self.getf, classes)
            for id, ft in results:
                for f in ft:
                    f['name'] = self.filter_names.get(f['key'], f['key'])
                if id in self.type_extend:
                    ft = [f for f in ft if f['key'] != 'type']
                    ft.insert(0, {
                        'key': 'type',
                        'name': '类型',
                        'value': [{'n': '全部', 'v': ''}] + [{'n': n, 'v': v} for n, v in self.type_extend[id]]
                    })
                if len(ft):
                    filters[id] = ft
        result['class'] = classes
        result['filters'] = filters
        result['list'] = vlist
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        body = {
            "tid": tid,
            "type": extend.get('type'),
            "lang": extend.get('lang'),
            "area": extend.get('area'),
            "year": extend.get('year'),
            "pg": pg
        }
        body = {k: v for k, v in body.items() if v is not None and v != ""}
        data = self.getdata('/api.php/provide/nav', self.getbody(body))
        result = {}
        result['list'] = data['data']['data']
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result
        pass

    def detailContent(self, ids):
        data = self.getdata('/api.php/provide/vod', self.getbody({'ids': ids[0]}))
        vod = data['data']
        plist = []
        names = []
        vname = vod.get('vod_name') or ''
        total = int(vod.get('vod_total') or 0)
        for i in vod['vod_play_url']:
            ulist = []
            names.append(i['name'].split(' ')[0])
            parse = ''
            if i.get('parse') and isinstance(i['parse'], list) and len(i['parse']):
                parse = self.e64(json.dumps(i['parse']))
            for idx, j in enumerate(i['data']):
                jdata = {
                    'url': j['url'],
                    'parse': parse,
                    'name': vname,
                    'ep': idx,
                    'total': total or len(i['data'])
                }
                ulist.append(f'{j["name"]}${self.e64(json.dumps(jdata))}')
            plist.append('#'.join(ulist))
        vod['vod_play_from'] = '$$$'.join(names)
        vod['vod_play_url'] = '$$$'.join(plist)
        vod['vod_content'] = self.mp_notice + (vod.get('vod_content') or '')
        vod.pop('cover_list', None)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        body = {"wd": key, "tid": "0", "pg": pg}
        data = self.getdata('/api.php/provide/search', self.getbody(body))
        vlist = []
        for i in data['data']:
            i.pop('vod_play_from', None)
            vlist.append(i)
        return {'list': vlist, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        try:
            data = json.loads(self.d64(id))
        except Exception:
            return {'parse': 1, 'url': id, 'header': {}}
        url = data.get('url') or ''
        name = data.get('name') or ''
        ep = int(data.get('ep') or 0)
        total = int(data.get('total') or 0)
        parse = data.get('parse')
        if parse:
            try:
                parse = json.loads(self.d64(parse))
            except Exception:
                parse = []
        if self._isvideo(url):
            if self._health(url):
                return {'parse': 1, 'url': url, 'header': {}}
            jurl = self.getplayurl(name, ep, total)
            return {'parse': 1, 'url': jurl or url, 'header': {}}
        # 原站解析服务现在只返回"请下载新版本"的提示视频，必须校验并丢弃
        if parse:
            for p in parse:
                try:
                    response = self._get(f'{p}{url}')
                    jdata = response.json()
                    jdata = jdata.get('data') or jdata
                    jurl = jdata.get('url')
                    if jurl and '/static/videos/' not in jurl and self._isvideo(jurl):
                        return {'parse': 0, 'url': jurl, 'header': jdata.get('header') or {}}
                except Exception:
                    continue
        # 原站无法播放时，用资源站同名影片兜底
        jurl = self.getplayurl(name, ep, total)
        if jurl:
            return {'parse': 1, 'url': jurl, 'header': {}}
        return {'parse': 1, 'url': url, 'header': {}}

    def _isvideo(self, url):
        return bool(url) and bool(re.search(r'(\.m3u8|\.mp4|\.flv)(\?|$)', url))

    def _health(self, url):
        try:
            response = requests.get(url, timeout=4, verify=False, stream=True,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            code = response.status_code
            response.close()
            return 200 <= code < 400 or code in (403, 416)
        except Exception:
            return False

    def _normname(self, name):
        return re.sub(r'[^\w\u4e00-\u9fff]', '', name or '').lower()

    def _checkm3u8(self, url):
        try:
            response = requests.get(url, timeout=6, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
            return response.status_code == 200 and '#EXTM3U' in (response.text or '')[:300]
        except Exception:
            return False

    def _reallink(self, url):
        if not url or not url.startswith('http'):
            return ''
        if self._isvideo(url):
            if '.m3u8' in url:
                return url if self._checkm3u8(url) else ''
            return url
        if '/share/' in url:
            return ''
        # 大部分资源站的播放页只需拼上 index.m3u8
        if self._checkm3u8(url.rstrip('/') + '/index.m3u8'):
            return url.rstrip('/') + '/index.m3u8'
        response = self._get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response is not None:
            match = re.search(r'''https?://[^"'\\\s]+\.m3u8[^"'\\\s]*''', response.text or '')
            if match and self._checkm3u8(match.group(0)):
                return match.group(0)
        return ''

    def _sourceurl(self, api, wd, ep, total):
        try:
            response = requests.get(api, params={'ac': 'videolist', 'wd': wd}, timeout=8, verify=False,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            vlist = response.json().get('list') or []
        except Exception:
            return ''
        nn = self._normname(wd)
        best = None
        for v in vlist:
            urls = [x.split('$')[-1] for x in (v.get('vod_play_url') or '').split('#') if '$' in x]
            if not urls or ep >= len(urls):
                continue
            cn = self._normname(v.get('vod_name'))
            if not cn or not (cn == nn or cn.startswith(nn) or nn.startswith(cn)):
                continue
            score = 40 if cn == nn else 0
            if total <= 1:
                if len(urls) > 2:
                    continue
                score += 30
            else:
                score += max(0, 30 - abs(len(urls) - total))
            if best is None or score > best[0]:
                best = (score, urls[ep])
        return best[1] if best else ''

    def getplayurl(self, name, ep, total=0):
        if not name:
            return ''
        queries = [name]
        simple = re.sub(r'第[一二三四五六七八九十0-9]+季.*$', '', name).strip()
        if simple and simple != name:
            queries.append(simple)
        else:
            simple = re.sub(r'[（(].*[）)]', '', name).strip()
            if simple and simple != name:
                queries.append(simple)
        for wd in queries:
            checked = 0
            with ThreadPoolExecutor(max_workers=len(self.cj_apis)) as executor:
                futures = [executor.submit(self._sourceurl, api, wd, ep, total) for api in self.cj_apis.values()]
                for fut in as_completed(futures):
                    try:
                        url = fut.result()
                    except Exception:
                        continue
                    if not url:
                        continue
                    real = self._reallink(url)
                    if real:
                        return real
                    checked += 1
                    if checked >= 3:
                        break
        return ''

    def localProxy(self, param):
        pass

    def getf(self, map):
        ft, id = [], map['type_id']
        try:
            fdata = self.getdata('/api.php/provide/nav', self.getbody({'tid': id, 'pg': '1'}))
            dy = ['area', 'year', 'lang', 'type']
            fd = fdata['data']['type_extend']
            has_non_empty_field = False
            for key in dy:
                if key in fd and fd[key].strip() != "":
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                for dkey in fd:
                    if dkey in dy and fd[dkey].strip() != "":
                        values = fd[dkey].split(",")
                        value_array = [{"n": value.strip(), "v": value.strip()} for value in values if
                                       value.strip() != ""]
                        ft.append({"key": dkey, "name": dkey, "value": value_array})
            return (id, ft)
        except:
            return (id, ft)

    def getskey(self):
        random_bytes = os.urandom(16)
        return binascii.hexlify(random_bytes).decode()

    def getohost(self):
        url = 'https://bianyuan1.oss-cn-hangzhou.aliyuncs.com/bianyuan20250605.json'
        response = self._get(url, headers=self.headers)
        if response is None:
            raise Exception('获取线路配置失败')
        text = response.text
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            data_ = self.daes(text, b64decode('kzCsPVrVY4+AGjtOFW8Wug=='), 1)
            data = json.loads(data_)
        return data.get('servers') or []

    def gethost(self):
        body = {
            "gr_rp_size": "1080*2272",
            "gr_app_list": "%E5%B1%8F%E5%B9%95%E5%BD%95%E5%88%B6%EF%BC%88com.miui.screenrecorder%29%0A%E5%A4%B8%E5%85%8B%EF%BC%88com.quark.browser%29%0A%E8%BE%B9%E7%BC%98%E8%A7%86%E9%A2%91%EF%BC%88com.hjmore.wallpaper%29%0A%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9%EF%BC%88tv.danmaku.bili%29%0A%E7%81%AB%E6%98%9F%E6%90%9C%E9%A2%98%EF%BC%88com.fenbi.android.souti%29%0A%E6%94%AF%E4%BB%98%E5%AE%9D%EF%BC%88com.eg.android.AlipayGphone%29%0AWPS%20Office%EF%BC%88cn.wps.moffice_eng%29",
            "gr_lal": "0.0%2C0.0",
            "gr_system_type": "android",
            "gr_device_imei": "3507f394e83d2424",
            "gr_app_version": "1.0.3",
            "gr_device_model": "Xiaomi%20M2012K10C%20%28Android%20%E7%89%88%E6%9C%AC%3A%2011%2C%20SDK%E7%89%88%E6%9C%AC%3A%2030%29",
            "gr_city": "%E8%B4%B5%E5%B7%9E%2C%E6%9C%AA%E7%9F%A5%2C%E6%9C%AA%E7%9F%A5",
            "requestId": self.uuid(),
            "timeStamp": str(int(time.time() * 1000)),
            "version": "1.0.3",
            "package": "com.hjmore.wallpaper",
            "userLoginToken": "",
            "app_id": "534",
            "appName": 2131951658,
            "device_id": "3507f394e83d2424",
            "device-id": "3507f394e83d2424",
            "oaid": "",
            "imei": "",
            "referer_shop": "边缘影视",
            "referer-shop": "边缘影视",
            "access_fine_location": 0,
            "access-fine-location": 0
        }
        hosts = []
        try:
            hosts = self.getohost()
        except Exception as e:
            print(f'获取线路配置失败: {e}')
        for host in hosts + self.fallback_hosts:
            try:
                data = self.getdata('/api.php/settings/grayscale_list', body, host)
                servers = data['data']['grayscale'].get('server_url') or []
                for server_url in servers:
                    parsed_url = urlparse(server_url)
                    if parsed_url.netloc:
                        return f'{parsed_url.scheme}://{parsed_url.netloc}'
            except Exception as e:
                print(f'线路 {host} 不可用: {e}')
        raise Exception('无法获取有效服务器地址')

    def drsa(self, encrypted_data):
        private_key_pem = """-----BEGIN RSA PRIVATE KEY-----
    MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDA5NWiAwRjH50/
    IJY1N0zLopa4jpuWE7kWMn1Qunu6SjBgTvNRmRUoPDHn54haLfbfXIa2X+/sIaMB
    /O3HhrpVsz55E5W2vpZ5fBYWh+M65bQERKTW+l72H7GR9x0yj3QPByzzfsj/QkyP
    81prpwR9i8yMe7yG9TFKqUQCPE+/GrhNU1Qf6nFmV+vMnlP9DantkwAt4fPOMZn3
    j4da65/1YQV+F5bYzaLenNVKbHf8U8fVYLZWIy4yk2Vpe4R2Z+JX/eHWsChE9hOu
    iFm02eTW5NJLZlWUxYrSE23VXi8oXSEdON3UEOrwSdAUh4SXxLZ9U7KpNVdTwWyR
    AS4GyzJ/AgMBAAECggEBAKzmcXefLLeNBu4mz30z7Go7es5DRcLoOudiqmFKRs1c
    4q/xFLj3drdx/WnZZ6ctvDPKRBYFOJF4NRz7Ekfew/c9i6oLnA8KFuceCs53T37j
    ltCclwT7t1L2ZbxovIsteuJdlDVOV+w2CVqez1Xfh27heKAT6ZEvBtfdkVBPr0uj
    oVwa2+XlJmYZw5dHeB7ySVeAQ+69zDuADB8OWxPWsv6Del+Fhf0kTHAw4WgqcYsd
    JUunCjgLdJUlDgXzH/M/Nj8NYVEuq6QpmhaktJ4fwn/F7u3lQllVCFKj5lr0Xb92
    y7lvQlGqMKX1oxf+P5c5/vie1kDx1Rj4S++flIcVlUECgYEA4BuxCZ1c8oOF98bs
    KTAONnnZniQ1BRt7rA+O9+++lDjxJhxkuthwjB9YzrnZtxHJtvIIie9Jv8MVfzHa
    p2woDtiEh3YYwmIlgNUFvTcGe++tTiEiLDcGc/xNhpvfbLaw9QB7/HQ+LT1QCMxJ
    ufdBrR98l0khIGjYqxDW3W5pV70CgYEA3Ff/9+GM2XI/EUSTYrpnwp5R5OsXz1DL
    3CFFgp1EPCNk/c3YNWnrUtTkfmKAlRqWIHfphvH/jS6jpGrfRxDggPwGMtBc134b
    brIM5i4KNj/EcE+w5g03HaKBf1ZihHDQ53c6wTn6IFOHJNSPRLqMNqRymfbclNyO
    lBMHQmB8yOsCgYBCdZPTwRnuRTi2WQRx1nFwkEQL1Lrwb80GInsIZc2DkTtaTPNG
    QadmtmkUrSK2Wo0SNsZ3eUHKn2TBmpw4KCfc9zKeJVSEWKy8fu+7xBSlLlebotHK
    gOrl/H1VHOZuC+OAVItwO1yw98zDPynh/0Q3ve2pw6MSRGV0nYLKmdKdlQKBgQCJ
    Ty1rw1qKhu9WS22tMIxIc3CFPxtvTeI8I1+1rVtAPq5Im2YIoyDKVXCucaO/RvoW
    8aLNPTELQe0oIJFTL+k3d9ZFBCNXBncB3GK9biNe+w3nD0IlmkamaQZZ2/M4pTUJ
    iPtMPlzomCS3ht5g7f9CbegcmgGLooYXMGRtsMMSUQKBgQCoj+3UciH2i+HyUla5
    1FxivjH3MqSTE4Q7OdzrELb6DoLYzjgWAbpG8HIuodD4uG5xz1oR5H7vkblf1itB
    hwOwDEiabyX76e/I3Q0ovwBV+9PMjM4UVU0kHoiu3Z2s90ckwNh58w3QH5fn9E0b
    fqMnB6uWze+xrXWijaOzVZhIZg==
    -----END RSA PRIVATE KEY-----"""
        private_key = RSA.import_key(private_key_pem)
        cipher = PKCS1_v1_5.new(private_key)
        decrypted_data = cipher.decrypt(b64decode(encrypted_data), None)
        return decrypted_data.decode('utf-8')

    def ersa(self, data):
        public_key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+0QMb3WDXjNBRovRhTLH
    g3d+CliZAva2tepWNNN0Pj6DgE3ZTnPR34iL/cjo9Jbd3dqAJs/YkKnFurGkDxz5
    TthIqvmz244wiFcHt+FGWoJsj5ZVvrH3pPwH85ggmI1DjxSJEUhB12Z9X6FGli8D
    drR9xeLe5y8vFekux8xCQ7pwH1mNQu4Wy32WVM8aLjmRjNzEWOvEMAWCRuwymEdS
    zlWoH53qk1dqd6DAmOJhWU2hH6Yt2ZY9LTaDGiHrS+g0DuwajAQzhbM8eonGYMph
    nP4q0UTHWEfaGR3HoILmeM32M+qF/UCGfgfR6tCMiXPoHwnD2zoxbZ2p+QlYuTZL
    vQIDAQAB
    -----END PUBLIC KEY-----"""
        key = RSA.importKey(public_key)
        cipher = PKCS1_v1_5.new(key)
        encrypted = cipher.encrypt(data.encode())
        return b64encode(encrypted).decode()

    def eaes(self, data, key):
        key = key.encode('utf-8')
        cipher = AES.new(key, AES.MODE_ECB)
        padded = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded)
        word = b64encode(encrypted).decode('utf-8')
        return word

    def daes(self, encrypted_data, key, hexi=0):
        if hexi == 0:
            key = key.encode('utf-8')
            encrypted = b64decode(encrypted_data)
        else:
            encrypted = bytes.fromhex(encrypted_data)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted)
        unpadded = unpad(decrypted, AES.block_size)
        return unpadded.decode('utf-8')

    def getbody(self, params=None):
        body = {
            "requestId": self.uuid(),
            "timeStamp": str(int(time.time() * 1000)),
            "version": "1.0.3",
            "package": "com.hjmore.wallpaper",
            "userLoginToken": "",
            "app_id": "534",
            "appName": 2131951658,
            "device_id": "3507f394e83d2424",
            "device-id": "3507f394e83d2424",
            "oaid": "",
            "imei": "",
            "referer_shop": "边缘影视",
            "referer-shop": "边缘影视",
            "access_fine_location": 0,
            "access-fine-location": 0
        }
        if params:
            body.update(params)
        return body

    def _get(self, url, headers=None, timeout=10):
        try:
            response = requests.get(url, headers=headers or self.headers, timeout=timeout, verify=False)
            response.encoding = 'utf-8'
            return response
        except Exception:
            try:
                return self.fetch(url, headers=headers or self.headers, timeout=timeout)
            except Exception:
                return None

    def _post_raw(self, url, data, headers=None, timeout=15):
        try:
            response = requests.post(url, headers=headers or self.headers, data=data, timeout=timeout, verify=False)
            response.encoding = 'utf-8'
            return response
        except Exception:
            try:
                return self.post(url, headers=headers or self.headers, data=data, timeout=timeout)
            except Exception:
                return None

    def getdata(self, path, body, host=None):
        jdata = json.dumps(body)
        msign = self.md5(jdata)
        skey = self.getskey()
        jsign = {'key': skey, 'sign': msign}
        Sign = self.ersa(json.dumps(jsign))
        header = self.headers.copy()
        header['Sign'] = Sign
        dbody = self.eaes(jdata, skey)
        response = self._post_raw(f'{host or self.host}{path}', dbody, header)
        if response is None:
            raise Exception(f'请求失败: {path}')
        rdata = response.text
        sign = None
        try:
            sign = response.headers.get('Sign')
        except Exception:
            sign = None
        if sign:
            dkey = self.drsa(sign)
            rdata = self.daes(rdata, dkey)
        return json.loads(rdata)

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def md5(self, text):
        h = MD5.new()
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    def uuid(self):
        return str(uuid.uuid4())
