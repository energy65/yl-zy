"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '多多追剧',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
import time as time_module
import hashlib
import random
import requests
import urllib3
from urllib.parse import quote
from base.spider import Spider as BaseSpider

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(BaseSpider):
    def init(self, extend=""):
        self.permanent_domain = "https://duoduozhuiju.com"
        self.web_sign = "ddtvf65f3a83d6d9ad6f"
        self.host_list = self._default_hosts()
        self._discover_hosts()
        self.host_index = 0
        self.host = self.host_list[0]
        self.web_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Accept": "application/json",
            "X-Client": "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a",
            "web-sign": self.web_sign,
            "Referer": self.host + "/",
        }
        self.pkg = 'com.sunshine.tv'
        self.ver = '4'
        self.device_id = self._random_str(16)
        self.finger = 'SF-C3B2B41F6EFFFF9869176CF68F6790E8F07506FC88632C94B4F5F0430D5498CA'
        self.app_base_headers = {
            "User-Agent": "okhttp/4.12.0",
            "Accept": "application/json",
            "x-aid": self.pkg,
            "x-device-brand": "vivo",
            "x-device-model": "V2309A",
            "x-update-id": "0245861b-2ebf-5524-389d-f983830651ec",
            "Referer": self.host + "/",
        }
        self.type_map = {
            '1': '电影',
            '2': '剧集',
            '3': '动漫',
            '4': '综艺',
        }
        self._decode_cache = {}

    def _default_hosts(self):
        return [
            "https://323433ssdfd.top",
            "https://duoduosdf12223234334.top",
            "https://xds2435u23422342342u.top",
            "https://dduotv01.top",
        ]

    def _discover_hosts(self):
        try:
            url = self.permanent_domain + "/js/config.js"
            rsp = self.fetch(url, headers={"User-Agent": "Mozilla/5.0"})
            if rsp and rsp.text:
                hosts = re.findall(r"host:\s*['\"]([^'\"]+)['\"]", rsp.text)
                if hosts:
                    discovered = ["https://" + h for h in dict.fromkeys(hosts)]
                    merged = []
                    seen = set()
                    for h in discovered + self._default_hosts():
                        if h not in seen:
                            seen.add(h)
                            merged.append(h)
                    self.host_list = merged
        except Exception as e:
            print(f'_discover_hosts error: {e}')

    def _iter_hosts(self):
        n = len(self.host_list)
        if n == 0:
            return
        for k in range(n):
            idx = (self.host_index + k) % n
            yield self.host_list[idx]
    
    def _random_str(self, len, chars='0123456789abcdef'):
        return ''.join(random.choice(chars) for _ in range(len))
    
    def _sha256(self, text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    
    def _get_app_headers(self):
        timestamp = str(int(time_module.time()))
        nonce = self._random_str(3, '0123456789')
        sign_str = f'finger={self.finger}&id={self.pkg}&nonce={nonce}&sk=SK-thanks&time={timestamp}&v={self.ver}'
        sign = self._sha256(sign_str)
        headers = dict(self.app_base_headers)
        headers.update({
            'x-ave': self.ver,
            'x-time': timestamp,
            'x-nonc': nonce,
            'x-sign': sign,
            'x-device-id': self.device_id,
        })
        return headers

    def getName(self):
        return '多多追剧'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '剧集'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺'},
        ], "list": self.homeVideoContent().get('list', [])}

    def homeVideoContent(self):
        html = self._api_get('/api.php/web/index/home', use_app=False)
        result = []
        try:
            data = json.loads(html)
            if data.get('code') == 200 and data.get('data'):
                home_data = data['data']
                for item in home_data.get('recommend', []):
                    if isinstance(item, dict) and item.get('vod_id'):
                        v = self._parse_vod(item)
                        if v:
                            result.append(v)
                for cat in home_data.get('categories', []):
                    if not isinstance(cat, dict):
                        continue
                    for item in cat.get('videos', []):
                        if isinstance(item, dict) and item.get('vod_id'):
                            v = self._parse_vod(item)
                            if v and v not in result:
                                result.append(v)
                        if len(result) >= 30:
                            break
                    if len(result) >= 30:
                        break
        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {"list": result}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        type_name = self.type_map.get(tid, '')
        url = f'/api.php/web/filter/vod?type_id={tid}&type_name={quote(type_name)}&page={page}&sort=hits'
        html = self._api_get(url, use_app=False)
        items = []
        total = 0
        page_count = 1
        try:
            data = json.loads(html)
            if data.get('code') == 200 and data.get('data'):
                list_data = data['data']
                if isinstance(list_data, list):
                    for item in list_data:
                        v = self._parse_vod(item)
                        if v:
                            items.append(v)
                total = data.get('total', len(items))
                page_count = data.get('pageCount', page)
        except Exception as e:
            print(f'categoryContent error: {e}')
        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": total}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            url = f'/api.php/web/vod/get_detail?vod_id={vid}'
            html = self._api_get(url, use_app=False)
            if not html:
                return result
            data = json.loads(html)
            if data.get('code') != 200 or not data.get('data'):
                return result

            detail_list = data['data']
            if not isinstance(detail_list, list) or len(detail_list) == 0:
                return result

            vodplayer = data.get('vodplayer', [])
            player_map = {}
            for p in vodplayer:
                player_map[p.get('from', '')] = p

            item = detail_list[0]
            vod = {
                "vod_id": str(item.get('vod_id', '')),
                "vod_name": item.get('vod_name', ''),
                "vod_pic": item.get('vod_pic', ''),
                "vod_director": item.get('vod_director', ''),
                "vod_actor": item.get('vod_actor', ''),
                "vod_year": str(item.get('vod_year', '')),
                "vod_area": item.get('vod_area', ''),
                "vod_remarks": item.get('vod_remarks', ''),
                "vod_content": re.sub(r'<[^>]+>', '', item.get('vod_content', '')).strip(),
            }

            vod_play_from = item.get('vod_play_from', '')
            vod_play_url = item.get('vod_play_url', '')

            if vod_play_from and vod_play_url:
                sources = vod_play_from.split('$$$')
                urls = vod_play_url.split('$$$')
                play_from = []
                play_url = []

                for i in range(len(sources)):
                    src = sources[i].strip()
                    if not src:
                        continue
                    url_str = urls[i] if i < len(urls) else ''
                    if not url_str:
                        continue
                    
                    player_info = player_map.get(src, {})
                    show_name = player_info.get('show', src)
                    decode_status = str(player_info.get('decode_status', '0'))
                    
                    if show_name.lower() != src.lower():
                        display_name = f'{show_name} ({src})'
                    else:
                        display_name = show_name

                    eps = []
                    ep_items = url_str.split('#')
                    for ep_item in ep_items:
                        if not ep_item:
                            continue
                        parts = ep_item.split('$')
                        if len(parts) >= 2:
                            ep_name = parts[0].strip()
                            ep_addr = parts[1].strip()
                            if ep_name and ep_addr:
                                ep_id = f'{src}@{decode_status}@{ep_addr}'
                                eps.append(f'{ep_name}${ep_id}')
                    if eps:
                        play_from.append(display_name)
                        play_url.append('#'.join(eps))

                vod['vod_play_from'] = '$$$'.join(play_from)
                vod['vod_play_url'] = '$$$'.join(play_url)
            else:
                vod['vod_play_from'] = ''
                vod['vod_play_url'] = ''

            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            parts = id.split('@')
            if len(parts) < 3:
                if id.startswith('http'):
                    result["url"] = id
                    result["header"] = json.dumps(self._get_play_headers())
                return result
            
            play_from = parts[0]
            need_parse = parts[1]
            raw_url = '@'.join(parts[2:])
            
            cache_key = raw_url
            if cache_key in self._decode_cache:
                cached = self._decode_cache[cache_key]
                if time_module.time() - cached['time'] < 3600:
                    result["url"] = cached['url']
                    result["parse"] = 0
                    result["header"] = json.dumps(self._get_play_headers())
                    return result
            
            final_url = ''
            
            if need_parse == '1':
                decoded = self._decode_url(raw_url, play_from)
                if decoded:
                    final_url = decoded
            
            if not final_url:
                final_url = raw_url
            
            if final_url and final_url.startswith('http'):
                self._save_cache(cache_key, final_url)
                result["url"] = final_url
                result["parse"] = 0
                
                if re.search(r'(www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com', final_url):
                    result["parse"] = 1
                
                result["header"] = json.dumps(self._get_play_headers())

        except Exception as e:
            print(f'playerContent error: {e}')
        return result
    
    def _build_protobuf(self, url, frm, sig):
        def field(field_num, s):
            b = s.encode('utf-8')
            tag = (field_num << 3) | 2
            out = bytearray([tag])
            l = len(b)
            while True:
                x = l & 0x7F
                l >>= 7
                if l:
                    out.append(x | 0x80)
                else:
                    out.append(x)
                    break
            return bytes(out) + b

        def field_varint(field_num, v):
            v = int(v) & 0xFFFFFFFFFFFFFFFF
            out = bytearray([(field_num << 3)])
            while True:
                b = v & 0x7F
                v >>= 7
                if v:
                    out.append(b | 0x80)
                else:
                    out.append(b)
                    break
            return bytes(out)

        return (field(1, url) + field(2, frm) +
                field_varint(3, sig.get('time', '0')) +
                field(4, sig.get('nonc', '')) +
                field(5, sig.get('sign', '')) +
                field(6, sig.get('aid', '')) +
                field_varint(7, sig.get('ave', '0')))

    def _parse_protobuf(self, data):
        fields = {}
        i = 0
        n = len(data)
        while i < n:
            tag = data[i]
            i += 1
            fn = tag >> 3
            wt = tag & 7
            if wt == 2:
                ln = data[i]
                i += 1
                val = data[i:i + ln]
                i += ln
                fields[fn] = val.decode('utf-8', 'ignore')
            elif wt == 0:
                val = 0
                shift = 0
                while i < n:
                    b = data[i]
                    i += 1
                    val |= (b & 0x7f) << shift
                    if not (b & 0x80):
                        break
                    shift += 7
                fields[fn] = val
            else:
                break
        return {
            'code': fields.get(1, 0),
            'msg': fields.get(2, ''),
            'data': fields.get(3, ''),
        }

    def _get_signature_headers(self):
        try:
            import time as _time
            import hashlib as _hashlib
            _finger = 'WF-2c064bc5b3400788f31b848849bc3a60f835423ba2dfe69d7ea93974c216e4f2'
            _sk = 'WEB-50a8e9c84a1dc05669a692ded99a2dac46527229e607a7be15db88dbc59059d1'
            _nonc = '00000000000000000000000000000000'
            _t = str(int(_time.time()))
            _msg = f'finger={_finger}&id=com.web.player&nonce={_nonc}&sk={_sk}&time={_t}&v=1'
            _sign = _hashlib.sha256(_msg.encode('utf-8')).hexdigest().upper()
            return {
                'sign': _sign,
                'time': _t,
                'nonc': _nonc,
                'aid': 'com.web.player',
                'ave': '1',
            }
        except Exception as e:
            print(f'_get_signature_headers error: {e}')
            return {}

    def _decode_url(self, raw_url, play_from):
        try:
            sig = self._get_signature_headers()
        except Exception as e:
            print(f'_get_signature_headers error: {e}')
            return ''
        real_from = play_from
        if '(' in play_from and play_from.endswith(')'):
            _rf = play_from[play_from.rfind('(') + 1:-1].strip()
            if _rf:
                real_from = _rf
        try:
            body = self._build_protobuf(raw_url, real_from, sig)
        except Exception as e:
            print(f'_build_protobuf error: {e}')
            return ''
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Accept": "application/x-protobuf",
            "Content-Type": "application/x-protobuf",
            "X-Client": "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a",
            "web-sign": self.web_sign,
            "Referer": self.host + "/",
        }
        if sig:
            headers.update({k: str(sig[k]) for k in ('sign', 'time', 'nonc', 'aid', 'ave') if k in sig})
        for host in self._iter_hosts():
            try:
                sep = '&' if '?' in host else '?'
                url = f'{host}/api.php/web/decode/url{sep}url={requests.utils.quote(raw_url)}&from={requests.utils.quote(real_from)}'
                r = requests.post(
                    url,
                    data=body,
                    headers=headers,
                    timeout=10,
                    verify=False,
                )
                if r.content:
                    data = self._parse_protobuf(r.content)
                    if data.get('code') == 1 and data.get('data'):
                        decoded = data['data']
                        idx = decoded.find('http')
                        if idx > 0:
                            decoded = decoded[idx:]
                        if host != self.host_list[self.host_index]:
                            self.host_index = self.host_list.index(host)
                            self.host = host
                        return decoded
            except Exception as e:
                print(f'_decode_url error: {e}')
                continue
        return ''

    def _save_cache(self, key, url):
        self._decode_cache[key] = {
            'url': url,
            'time': time_module.time()
        }
        if len(self._decode_cache) > 200:
            old_keys = sorted(self._decode_cache.keys(), 
                             key=lambda k: self._decode_cache[k]['time'])[:100]
            for k in old_keys:
                del self._decode_cache[k]
    
    def _get_play_headers(self):
        return {
            "User-Agent": "com.sunshine.tv/1.2.0 (Linux;Android 15) AndroidXMedia3/1.4.1",
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "*/*",
        }

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f'/api.php/web/search/index?wd={quote(key)}&page={page}&limit=20'
        html = self._api_get(url, use_app=False)
        items = []
        total = 0
        page_count = 1
        try:
            data = json.loads(html)
            if data.get('code') == 200 and data.get('data'):
                list_data = data['data']
                if isinstance(list_data, list):
                    for item in list_data:
                        v = self._parse_vod(item)
                        if v:
                            items.append(v)
                total = data.get('total', len(items))
                page_count = data.get('pageCount', page)
        except Exception as e:
            print(f'searchContentPage error: {e}')
        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": total}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _api_get(self, url, use_app=False):
        try:
            if url.startswith('http'):
                headers = self._get_app_headers() if use_app else dict(self.web_headers)
                rsp = self.fetch(url, headers=headers)
                if rsp and rsp.text:
                    return rsp.text
                return ''
            for i in range(len(self.host_list)):
                idx = (self.host_index + i) % len(self.host_list)
                host = self.host_list[idx]
                try:
                    full_url = host + url
                    headers = self._get_app_headers() if use_app else dict(self.web_headers)
                    headers["Referer"] = host + "/"
                    rsp = self.fetch(full_url, headers=headers)
                    if rsp and rsp.text:
                        if idx != self.host_index:
                            self.host_index = idx
                            self.host = host
                        return rsp.text
                except:
                    continue
            return ''
        except Exception as e:
            print(f'_api_get error: {e}')
            return ''

    def _parse_vod(self, item):
        try:
            vid = str(item.get('vod_id', ''))
            name = item.get('vod_name', '')
            if not vid or not name:
                return None
            return {
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": item.get('vod_pic', ''),
                "vod_remarks": item.get('vod_remarks', ''),
            }
        except:
            return None
