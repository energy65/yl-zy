# coding = utf-8
# !/usr/bin/python
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。
# by @多弗朗明哥
import base64
import sys
import json
import re
import gzip
from urllib.parse import urlencode, unquote

import requests
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend='{}'):
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; NOH-AN00 Build/N2G47H)'})
      
        try:
            ext = json.loads(extend) if extend else {}
        except:
            ext = {}
        
        self.apiHost = ext.get('Host', '').rstrip('/')          
        self.fixedAccount = ext.get('Account', '')            
        self.fixedPassword = ext.get('Password', '')           
        self.fixedToken = ext.get('token', '')    
        self.fixedMachineId = ext.get('MachineId', '')         
        self.cmsPath = '/cms//api.php/smtv/vod/'
        self.clientPath = '/user//Client/'
        self.rc4Key = '67eb9580d9ededc2a3a48694d1088f13'
        self.fixedTime = '1780412537'
        self.fixedKey = '0e6619a1e98425d0e942'
        self.fixedOs = '25'
        self.fixedSign = 'cjJ1cjJjclZVVGN3ZlNXSg%3D%3D%0A'
        self.fixedData = 'wjBO%2B0pJGs6v%2BcG2gYZNkja9nV80T%2BZb1gOWrqpuyqtTHnW6jUWbY%2FYGdSyQM9EX'
        self.detailTime = '1780411554'
        self.detailKey = 'ba09aa4d29fef5f4b945'
        self.categoryTime = '1780463568'
        self.categoryKey = '0355edbf73f54d5d3805'
        self.fixedEdition = '9.2'
        self.app = '10004'

    def getName(self):
        return "神马影视"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def rc4(self, data):
        key = self.rc4Key
        s = list(range(256))
        j = 0
        key_len = len(key)
        for i in range(256):
            j = (j + s[i] + ord(key[i % key_len])) & 0xFF
            s[i], s[j] = s[j], s[i]
        i = j = 0
        output = bytearray()
        for byte in data:
            i = (i + 1) & 0xFF
            j = (j + s[i]) & 0xFF
            s[i], s[j] = s[j], s[i]
            output.append(byte ^ s[(s[i] + s[j]) & 0xFF])
        return bytes(output)

    def request(self, url, post_data=None, is_get=False):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': self.session.headers['User-Agent'],
            'Authorization': 'Basic ' + base64.b64encode(b'shenma:shenma').decode()
        }
        if post_data and not is_get:
            response = self.session.post(url, data=post_data, headers=headers, timeout=20)
        else:
            response = self.session.get(url, headers=headers, timeout=20)
        return response

    def requestList(self, ac, class_name='', page=1, zm=''):
        url = f"{self.apiHost}{self.cmsPath}?ac={ac}"
        if class_name:
            url += f"&class={class_name}"
        if page > 0:
            url += f"&page={page}"
        if zm:
            url += f"&zm={zm}"
        postFields = f"time={self.fixedTime}&key={self.fixedKey}&os={self.fixedOs}&sign={self.fixedSign}&data={self.fixedData}&"
        try:
            response = self.request(url, postFields)
            raw_response = response.content
            try:
                decompressed = gzip.decompress(raw_response)
                response_text = decompressed.decode('utf-8')
            except:
                response_text = raw_response.decode('utf-8')
            decoded = base64.b64decode(response_text)
            decrypted = self.rc4(decoded)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            print(f"请求列表失败: {e}")
            return None

    def requestDetail(self, ids):
        url = f"{self.apiHost}{self.cmsPath}?ac=detail&ids={ids}"
        postFields = f"time={self.detailTime}&key={self.detailKey}&os={self.fixedOs}&sign={self.fixedSign}&data={self.fixedData}&"
        try:
            response = self.request(url, postFields)
            response_text = response.content.decode('utf-8')
            return json.loads(response_text)
        except Exception as e:
            print(f"请求详情失败: {e}")
            return None

    def homeContent(self, filter):
        category_url = f"{self.apiHost}/cms//api.php/smtv/Category"
        post_data = f"time={self.categoryTime}&key={self.categoryKey}&"
        try:
            response = self.request(category_url, post_data=post_data)
            resp_text = response.content.decode('utf-8')
            categories = json.loads(resp_text)
            class_list = []
            for cat in categories:
                if cat.get('type_status') == 1:
                    type_id = cat.get('type_en', '').lower()
                    type_name = cat.get('type_name', '')
                    if type_id and type_name:
                        class_list.append({'type_id': type_id, 'type_name': type_name})
            return {'class': class_list, 'filters': {}}
        except Exception as e:
            print(f"获取分类失败: {e}")
            return {'class': [], 'filters': {}}

    def homeVideoContent(self):
        result = self.categoryContent('movie', '1', False, {})
        return {'list': result['list'][:10] if result['list'] else []}

    def categoryContent(self, tid, pg, filter, extend):
        result = self.requestList('list', tid, int(pg))
        if not result or result.get('code') != 200:
            return {'list': [], 'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0}
        vlist = []
        for item in result.get('data', []):
            match = re.search(r'ids=(\d+)', item.get('nextlink', ''))
            vlist.append({
                'vod_id': match.group(1) if match else '',
                'vod_name': item.get('title', ''),
                'vod_pic': item.get('pic', ''),
                'vod_remarks': item.get('state', ''),
            })
        return {
            'list': vlist,
            'page': result.get('pageindex', int(pg)),
            'pagecount': result.get('totalpage', 1),
            'limit': 20,
            'total': result.get('videonum', 0)
        }

    def detailContent(self, ids):
        result = self.requestDetail(ids[0])
        if not result or result.get('code') != 200:
            return {'list': []}
        vod_name = result.get('title', '')
        globalToken = result.get('token', self.fixedToken)
        playFrom = []
        playUrl = []
        for source in result.get('video_list', []):
            sourceName = source.get('name') or source.get('type')
            playFrom.append(sourceName)
            episodes = []
            for ep in source.get('list', []):
                title = ep.get('title', '')
                url = ep.get('url', '')
                enhancedUrl = f"{url}|{source.get('type')}|{title}|{vod_name}|{globalToken}"
                episodes.append(f"{title}${enhancedUrl}")
            playUrl.append('#'.join(episodes))
        actor = result.get('actor', '')
        if isinstance(actor, list):
            actor = ','.join(actor)
        director = result.get('director', '')
        if isinstance(director, list):
            director = ','.join(director)
        vod = {
            'vod_id': str(result.get('id', ids[0])),
            'vod_name': vod_name,
            'vod_pic': result.get('img_url', ''),
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': result.get('intro', ''),
            'vod_play_from': '$$$'.join(playFrom),
            'vod_play_url': '$$$'.join(playUrl)
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        result = self.requestList('list', '', int(pg), key)
        if not result or result.get('code') != 200:
            return {'list': [], 'page': int(pg), 'pagecount': 0}
        vlist = []
        for item in result.get('data', []):
            match = re.search(r'ids=(\d+)', item.get('nextlink', ''))
            vlist.append({
                'vod_id': match.group(1) if match else '',
                'vod_name': item.get('title', ''),
                'vod_pic': item.get('pic', ''),
                'vod_remarks': item.get('state', ''),
            })
        return {
            'list': vlist,
            'page': result.get('pageindex', int(pg)),
            'pagecount': result.get('totalpage', 1)
        }

    def playerContent(self, flag, id, vipFlags):
        raw = unquote(id)
        parts = raw.split('|')
        original_url = parts[0] if parts else ''
        second = parts[1] if len(parts) > 1 else ''
        third = parts[2] if len(parts) > 2 else ''
        fourth = parts[3] if len(parts) > 3 else ''
        fifth = parts[4] if len(parts) > 4 else ''
        line = ''
        if flag and re.sub(r'\s*\|\s*.+$', '', flag).strip() == '华数':
            line = '华数'
        valid = ['NSYS','NS4K','nmys','rose','CO4K','NBY','gzvip','kl','yhczy','华数']
        ep = title = token = suf = ''

        if not line:
            if second in valid:
                line, ep, title, token = second, third, fourth, fifth
            elif third in valid:
                suf, line, ep, title, token = second, third, fourth, fifth, parts[5] if len(parts)>5 else ''

        if not line:
            suf, ep, title, token = second, third, fourth, fifth
            if original_url.startswith('NS4K-'): line='NS4K'
            elif original_url.startswith('NSYS-'): line='NSYS'
            elif 'nmys' in original_url: line='nmys'
            elif original_url.startswith('rose_'): line='rose'
            elif original_url.startswith('CO4K_'): line='CO4K'
            elif original_url.startswith('NBY-'): line='NBY'
            elif original_url.startswith('gzvip-'): line='gzvip'
            elif original_url.startswith('kl-'): line='kl'
            elif 'yhczy' in original_url: line='yhczy'
            else: line='NSYS'

        if line == '华数':
            clean = original_url.split('|')[0]
            return {'parse': 0, 'url': clean}

        enc_url = original_url
        if suf and len(suf) <= 20 and not re.search(r'[第集]', suf):
            enc_url = f"{original_url}|{suf}"
        if line == 'nmys':
            enc_url = original_url

        vodname = ''
        if title and ep:
            vodname = f"{title}-第{ep}集" if ep.isdigit() else f"{title}-{ep}"

        use_token = token if token else self.fixedToken
        params = {
            'url': enc_url,
            'app': self.app,
            'account': self.fixedAccount,
            'password': self.fixedPassword,
            'token': use_token,
            'machineid': self.fixedMachineId,
            'edition': self.fixedEdition,
            'vodname': vodname,
            'line': line,
            'new': 1
        }
        api_url = f"{self.apiHost}{self.clientPath}?{urlencode(params)}"

        try:
            resp = self.session.get(api_url, timeout=20)
            text = resp.text
            start = text.find('"url":"')
            if start == -1:
                return {'parse': 0, 'url': ''}
            start += 7
            end = text.find('"', start)
            if end == -1:
                return {'parse': 0, 'url': ''}
            play_url = text[start:end].replace('\\/', '/')
            if '|' in play_url:
                play_url = play_url.split('|')[0]

            return {'parse': 0, 'url': play_url}
        except Exception as e:
            print(f"播放错误: {e}")
            return {'parse': 0, 'url': ''}

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass


if __name__ == "__main__":
    sp = Spider()
    sp.init()
    print(json.dumps(sp.homeContent(False), ensure_ascii=False, indent=2))