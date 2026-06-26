# coding = utf-8
#!/usr/bin/python
import re, sys, uuid, json, base64, random, time, hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base.spider import Spider
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    xurl, key, iv, init_data = '', '', '', ''
    header = {}
    sort_rule = []
    use_sign = None
    api_prefix = '/api/vod'
    app_ver = '621'

    def __init__(self):
        self.header = {'User-Agent': 'okhttp/3.14.9'}

    def getName(self):
        return "首页"

    # ---------- URL ----------
    def _build_url(self, endpoint):
        base = self.xurl.rstrip('/')
        if self.api_prefix.endswith('.index'):
            return f"{base}{self.api_prefix}/{endpoint}"
        return f"{base}{self.api_prefix}/{endpoint}"

    # ---------- 请求头 ----------
    def _build_headers(self):
        h = {
            'User-Agent': self.header.get('User-Agent', 'okhttp/3.14.9'),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        if self.use_sign:
            t = str(int(time.time()))
            sign = self.aes_encrypt(t)
            h['app-version-code'] = '521'
            h['app-ui-mode'] = 'light'
            h['app-api-verify-time'] = t
            h['app-api-verify-sign'] = sign
            h['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            h['app-user-device-id'] = hashlib.md5(t.encode()).hexdigest()
            h['app-device-id'] = h['app-user-device-id']
            h['Referer'] = self.xurl
        else:
            h['App-Device-Id'] = ''.join(random.choices('0123456789abcdef', k=32))
            h['App-Os-Type'] = 'android'
            h['App-Ui-Mode'] = 'dark'
            h['App-Version-Code'] = self.app_ver
        return h

    # ---------- 图片补全 ----------
    def _fix_image_url(self, pic):
        if not pic:
            return ''
        if pic.startswith('http://') or pic.startswith('https://'):
            return pic
        base = self.xurl.rstrip('/')
        if pic.startswith('/'):
            return base + pic
        return base + '/' + pic

    # ---------- 加解密 ----------
    def aes_encrypt(self, plain_text):
        key = self.key.encode('utf-8')
        iv = (self.iv or self.key).encode('utf-8')
        data = plain_text.encode('utf-8')
        data = pad(data, AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        enc = cipher.encrypt(data)
        return base64.b64encode(enc).decode('utf-8')

    def decrypt(self, b64_str):
        key = self.key.encode('utf-8')
        iv = (self.iv or self.key).encode('utf-8')
        raw = base64.b64decode(b64_str)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = cipher.decrypt(raw)
        return unpad(dec, AES.block_size).decode('utf-8')

    # ---------- 初始化 ----------
    def init(self, extend=''):
        ext = json.loads(extend.strip())
        self.xurl = ext['host'].rstrip('/')
        self.key = ext['datakey']
        self.iv = ext.get('dataiv', self.key)
        self.sort_rule = [s.strip().lower() for s in ext.get('排序', '').split('>') if s.strip()]

        api_raw = ext.get('api', '/api/vod')
        if api_raw == '1':
            self.api_prefix = '/api.php/getappapi'
        elif api_raw == '2':
            self.api_prefix = '/api.php/qijiappapi'
        elif api_raw == '3':
            self.api_prefix = '/api/vod'
            self.use_sign = True
        else:
            self.api_prefix = str(api_raw)

        if self.use_sign is None:
            for mode in (False, True):
                self.use_sign = mode
                try:
                    res = self.post(self._build_url('init'), headers=self._build_headers(), data={}, verify=False)
                    if res.status_code == 200:
                        self.init_data = json.loads(self.decrypt(res.json()['data']))
                        break
                except:
                    continue
        else:
            res = self.post(self._build_url('init'), headers=self._build_headers(), data={}, verify=False)
            self.init_data = json.loads(self.decrypt(res.json()['data']))

        if not self.init_data:
            self.init_data = {}

    # ---------- 首页 ----------
    def homeContent(self, filter):
        data = self.init_data
        result = {"class": [], "filters": {}}
        name_map = {'class': '类型', 'area': '地区', 'lang': '语言', 'year': '年份', 'sort': '排序'}
        for t in data.get('type_list', []):
            tid, tname = t.get('type_id'), t.get('type_name', '')
            if tname in {'全部','QQ','juo.one'} or '企鹅群' in tname: continue
            result['class'].append({"type_id": tid, "type_name": tname})
            filters = t.get('filter_type_list', [])
            if not filters: continue
            items = []
            for f in filters:
                fname = f.get('name')
                vals = f.get('list', [])
                if not vals: continue
                key = 'by' if fname == 'sort' else fname
                items.append({"key": key, "name": name_map.get(fname,fname), "value": [{"n":v,"v":v} for v in vals]})
            if items: result["filters"][str(tid)] = items
        return result

    def homeVideoContent(self):
        videos = []
        for item in self.init_data.get('recommend_list', []):
            videos.append({
                "vod_id": item['vod_id'],
                "vod_name": item['vod_name'],
                "vod_pic": self._fix_image_url(item.get('vod_pic', '')),
                "vod_remarks": item.get('vod_remarks','')
            })
        return {'list': videos}

    # ---------- 分类 ----------
    def categoryContent(self, cid, pg, filter, ext):
        payload = {'area': ext.get('area','全部'), 'year': ext.get('year','全部'), 'type_id': cid, 'page': str(pg), 'sort': ext.get('sort','最新'), 'lang': ext.get('lang','全部'), 'class': ext.get('class','全部')}
        res = self.post(self._build_url('typeFilterVodList'), headers=self._build_headers(), data=payload, verify=False)
        data = json.loads(self.decrypt(res.json()['data']))
        videos = []
        for i in data.get('recommend_list', []):
            videos.append({
                "vod_id": i['vod_id'],
                "vod_name": i['vod_name'],
                "vod_pic": self._fix_image_url(i.get('vod_pic', '')),
                "vod_remarks": i.get('vod_remarks','')
            })
        return {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        did = ids[0]
        res = self.post(self._build_url('vodDetail'), headers=self._build_headers(), data={'vod_id': did}, verify=False)
        detail = json.loads(self.decrypt(res.json()['data']))
        vod = detail.get('vod', {})

        play_from, play_url = '', ''
        name_count = {}

        player_source_list = detail.get('player_source_list', [])
        vod_play_url_list = detail.get('vod_play_url_list', [])
        vod_play_list = detail.get('vod_play_list', [])

        if vod_play_list and not vod_play_url_list:
            # getappapi 风格
            if self.sort_rule:
                def sorter(item):
                    pname = item['player_info']['show'].lower()
                    for i, r in enumerate(self.sort_rule):
                        if r in pname: return i
                    return len(self.sort_rule)
                vod_play_list.sort(key=sorter)

            line_id = 1
            for line in vod_play_list:
                pname = line['player_info']['show']
                parse = line['player_info']['parse']
                parse_type = line['player_info']['parse_type']
                player_parse_type = line['player_info']['player_parse_type']

                if any(kw in pname for kw in ['防走丢','群','防失群','官网']):
                    pname = f'{line_id}线'

                cnt = name_count.get(pname, 0) + 1
                name_count[pname] = cnt
                if cnt > 1: pname = f'{pname}{cnt}'

                play_from += pname + '$$$'
                kurls = []
                for ep in line.get('urls', []):
                    ep_name = ep.get('name', f'第{ep.get("nid",1)}集')
                    token = ep.get('token', '')
                    kurls.append(f"{ep_name}${parse},{ep['url']},token+{token},{player_parse_type},{parse_type}")
                play_url += '#'.join(kurls) + '$$$'
                line_id += 1
        else:
            # apivod 风格
            code_to_id = {ps['player_code']: ps['id'] for ps in player_source_list if 'player_code' in ps and 'id' in ps}
            player_map = {p['player_code']: p for p in player_source_list if 'player_code' in p}
            if self.sort_rule:
                def sorter(item):
                    pcode = item.get('player_code','')
                    pname = player_map.get(pcode,{}).get('player_name',pcode).lower()
                    for i,r in enumerate(self.sort_rule):
                        if r in pname: return i
                    return len(self.sort_rule)
                vod_play_url_list.sort(key=sorter)

            line_id = 1
            for play in vod_play_url_list:
                pcode = play.get('player_code','')
                pinfo = player_map.get(pcode, {})
                pname = pinfo.get('player_name', pcode)
                parse_type = pinfo.get('jx_type', 1)
                player_parse_type = pinfo.get('player_parse_type', 1)
                source_id = code_to_id.get(pcode, pcode)

                if any(kw in pname for kw in ['防走丢','群','防失群','官网']): pname = f'{line_id}线'
                cnt = name_count.get(pname,0) + 1
                name_count[pname] = cnt
                if cnt > 1: pname = f'{pname}{cnt}'

                play_from += pname + '$$$'
                urls = play.get('urls', [])
                kurls = [f"{ep.get('name', f'第{ei+1}集')}${did},{pcode},{source_id},{ei},{player_parse_type},{parse_type}" for ei, ep in enumerate(urls)]
                play_url += '#'.join(kurls) + '$$$'
                line_id += 1

        play_from = play_from.rstrip('$$$')
        play_url = play_url.rstrip('$$$')

        videos = [{
            "vod_id": did,
            "vod_name": vod.get('vod_name',''),
            "vod_actor": vod.get('vod_actor','').replace('演员',''),
            "vod_director": vod.get('vod_director','').replace('导演',''),
            "vod_content": vod.get('vod_content',''),
            "vod_remarks": vod.get('vod_remarks',''),
            "vod_year": vod.get('vod_year','')+'年' if vod.get('vod_year') else '',
            "vod_area": vod.get('vod_area',''),
            "vod_play_from": play_from,
            "vod_play_url": play_url
        }]
        return {'list': videos}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        parts = id.split(',')
        if len(parts) == 5:
            parse_type = parts[4]
            url = parts[1]
            if parse_type == '0' and url.startswith('http'):
                return {"parse": 0, "url": url, "header": self._build_headers()}
            return {"parse": 0, "url": "", "header": self._build_headers()}

        if len(parts) < 6:
            return {"parse": 0, "url": "", "header": self._build_headers()}

        vod_id, pcode, sid, ei, pptype, ptype = parts[:6]
        if ptype == '2' or pptype == '2':
            try:
                resp = self.fetch(f"{vod_id}{pcode}", headers=self._build_headers(), verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    url = data.get('url') or data.get('data',{}).get('url')
                    if url: return {"parse": 0, "url": url, "header": self._build_headers()}
            except: pass
            return {"parse": 0, "url": "", "header": self._build_headers()}

        try:
            payload_sid = int(sid)
        except:
            payload_sid = sid
        try:
            ei = int(ei)
        except:
            ei = 0
        payload = {'vod_id': vod_id, 'player_source_id': payload_sid, 'episode_index': ei}
        try:
            resp = self.post(self._build_url('vodParse'), headers=self._build_headers(), data=payload, verify=False)
            jresp = resp.json()
            if jresp.get('code') == 0 and jresp.get('data'):
                dec = self.decrypt(jresp['data'])
                url = self._extract_url(dec)
                if url: return {"parse": 0, "url": url, "header": self._build_headers()}
        except: pass
        return {"parse": 0, "url": "", "header": self._build_headers()}

    def _extract_url(self, raw):
        if isinstance(raw, str):
            if raw.startswith('http'): return raw
            try: raw = json.loads(raw)
            except: return ''
        if isinstance(raw, dict):
            for k in ('url','play_url','video_url','src'):
                if k in raw and raw[k]: return self._extract_url(raw[k])
            if 'data' in raw: return self._extract_url(raw['data'])
            if 'json' in raw: return self._extract_url(raw['json'])
        return ''

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        headers = self._build_headers()
        combos = [
            {'keywords': key},
            {'vod_name': key},
            {'keywords': key, 'type_id': '0'},
            {'vod_name': key, 'type_id': '0'}
        ]
        for params in combos:
            payload = {'page': str(pg), **params}
            try:
                resp = self.post(self._build_url('searchList'), headers=headers, data=payload, verify=False)
                j = resp.json()
                if j.get('data'):
                    data = json.loads(self.decrypt(j['data']))
                    items = data.get('search_list', [])
                    if items:
                        videos = [{"vod_id": i['vod_id'], "vod_name": i['vod_name'], "vod_pic": self._fix_image_url(i.get('vod_pic', '')), "vod_remarks": f"{i.get('vod_year','')} {i.get('vod_class','')}"} for i in items]
                        return {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
            except: continue
        return {'list': []}

    def localProxy(self, params):
        if params['type'] == "m3u8": return self.proxyM3u8(params)
        elif params['type'] == "media": return self.proxyMedia(params)
        elif params['type'] == "ts": return self.proxyTs(params)
        return None

    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass