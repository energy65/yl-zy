"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '布布追剧',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
import time as time_module
import hashlib
import random
from urllib.parse import quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host_list = [
            "https://asd123sx23xdacsx.top",
        ]
        self.host = self.host_list[0]
        self.host_index = 0
        self.web_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Accept": "application/json",
            "X-Client": "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a",
            "web-sign": "f65f3a83d6d9ad6f",
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
        return '布布追剧'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '剧集'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺'},
        ]}

    def homeVideoContent(self):
        html = self._api_get('/api.php/web/index/home', use_app=False)
        result = []
        try:
            data = json.loads(html)
            if data.get('code') == 200 and data.get('data'):
                home_data = data['data']
                for key in home_data:
                    items = home_data[key]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and item.get('vod_id'):
                                v = self._parse_vod(item)
                                if v:
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
            url = f'/api.php/app/vod/get_detail?vod_id={vid}'
            html = self._api_get(url, use_app=True)
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
                decode_api = f'/api.php/app/decode/url/?url={quote(raw_url)}&vodFrom={quote(play_from)}'
                resp = self._api_get(decode_api, use_app=True)
                if resp:
                    try:
                        data = json.loads(resp)
                        if data.get('code') == 1 and data.get('data'):
                            decoded = data['data']
                            if decoded.startswith('http'):
                                final_url = decoded
                    except:
                        pass
            
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
