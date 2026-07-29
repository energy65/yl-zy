# -*- coding: utf-8 -*-
import json
import re
import ssl
import gzip
import urllib.request
import urllib.parse

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return ""
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}
        def localProxy(self, params): return None


class Spider(BaseSpider):
    API_URL = "https://api.bilibili.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

    HEADERS = {
        "User-Agent": UA,
        "Referer": "https://search.bilibili.com",
    }
    HEADERX = {
        "User-Agent": UA,
        "Referer": "https://www.bilibili.com",
    }

    CATEGORIES = [
        {"type_id": "书法", "type_name": "书法"},
        {"type_id": "毛笔字", "type_name": "毛笔字"},
        {"type_id": "硬笔书法", "type_name": "硬笔书法"},
        {"type_id": "楷书", "type_name": "楷书"},
        {"type_id": "行书", "type_name": "行书"},
        {"type_id": "草书", "type_name": "草书"},
        {"type_id": "隶书", "type_name": "隶书"},
        {"type_id": "篆书", "type_name": "篆书"},
        {"type_id": "瘦金体", "type_name": "瘦金体"},
        {"type_id": "书法入门", "type_name": "书法入门"},
        {"type_id": "书法教学", "type_name": "书法教学"},
        {"type_id": "国画", "type_name": "国画"},
        {"type_id": "篆刻", "type_name": "篆刻"},
        {"type_id": "文房四宝", "type_name": "文房四宝"},
        {"type_id": "书法欣赏", "type_name": "书法欣赏"},
    ]

    _w_key = [15, 22, 31, 18, 27, 14, 29, 16, 25, 19, 30, 13, 28, 17, 24, 20]
    _w_data = [
        234, 168, 177, 246, 164, 175, 248, 149, 181, 247, 162, 154, 249, 158, 175, 54,
        233, 172, 143, 247, 145, 149, 245, 173, 182, 247, 165, 187, 250, 160, 159, 54,
        224, 170, 147, 244, 128, 186, 248, 180, 131, 247, 162, 149, 244, 165, 176, 252,
        186, 146, 249, 168, 139, 235, 173, 173, 252, 143, 182, 235, 166, 129, 253, 158,
        148, 240, 146, 130, 243, 187, 189, 247, 144, 155
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "书法"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _decrypt_wx(self):
        try:
            plain = bytes([b ^ self._w_key[i % len(self._w_key)] for i, b in enumerate(self._w_data)])
            return plain.decode('utf-8')
        except:
            return '微信公众号"源力软件汇"'

    def _wx_info(self):
        return self._decrypt_wx() + '，更多优质资源尽在源力捐赠版'

    def _fmt(self, num):
        try:
            num = int(num)
            if num >= 100000000:
                return f"{num/100000000:.1f}亿"
            elif num >= 10000:
                return f"{num/10000:.1f}万"
            return str(num)
        except:
            return str(num)

    def _http_get(self, url, headers=None):
        if headers is None:
            headers = self.HEADERS
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in encoding:
                    data = gzip.decompress(data)
                return data.decode('utf-8')
        except:
            return ""

    def _search_bili(self, keyword, pg=1):
        url = f'{self.API_URL}/x/web-interface/wbi/search/type?search_type=video&page={pg}&page_size=42&keyword={urllib.parse.quote(keyword)}'
        html = self._http_get(url, self.HEADERS)
        if not html:
            return []
        try:
            kjson = json.loads(html)
        except:
            return []
        videos = []
        for item in kjson.get('data', {}).get('result', []):
            bvid = item.get('bvid', '')
            if not bvid:
                continue
            title = item.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
            pic = item.get('pic', '')
            if pic and 'http' not in pic:
                pic = 'http:' + pic
            play = item.get('play', 0)
            try:
                play = int(play)
            except:
                play = 0
            if play >= 100000000:
                remarks = f"{play/100000000:.1f}亿播放"
            elif play >= 10000:
                remarks = f"{play/10000:.1f}万播放"
            else:
                remarks = f"{play}播放"
            videos.append({
                "vod_id": f"shufa|{bvid}",
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })
        return videos

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        all_vids = []
        seen = set()
        for cat in self.CATEGORIES[:6]:
            items = self._search_bili(cat["type_id"], 1)
            for v in items:
                if v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    all_vids.append(v)
                    if len(all_vids) >= 30:
                        break
            if len(all_vids) >= 30:
                break
        result["list"] = all_vids[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        items = self._search_bili(tid, pg)
        return {
            "list": items,
            "page": pg,
            "pagecount": 9999,
            "limit": 42,
            "total": 999999,
        }

    def detailContent(self, ids):
        result = {"list": []}
        did = ids[0]
        bvid = did
        if '|' in did:
            bvid = did.split('|', 1)[1]

        html = self._http_get(f'https://www.bilibili.com/video/{bvid}', self.HEADERX)
        if not html:
            return result

        start_str = 'window.__INITIAL_STATE__='
        s_idx = html.find(start_str)
        if s_idx == -1:
            return result
        s_idx += len(start_str)
        e_idx = html.find('}};', s_idx)
        if e_idx == -1:
            return result
        try:
            kjson = json.loads(html[s_idx:e_idx] + '}}')
        except:
            return result

        vd = kjson.get('videoData', {})
        name = vd.get('title', '')
        pic = vd.get('pic', '')
        if pic and 'http' not in pic:
            pic = 'http:' + pic
        desc = vd.get('desc', '')
        owner = vd.get('owner', {})
        up_name = owner.get('name', '')
        stat = vd.get('stat', {})

        parts = []
        parts.append(f"视频简介：{desc}")
        parts.append(f"播放量：{self._fmt(stat.get('view', 0))}")
        parts.append(f"弹幕数：{self._fmt(stat.get('danmaku', 0))}")
        parts.append(f"点赞数：{self._fmt(stat.get('like', 0))}")
        parts.append(f"UP主：{up_name}")
        parts.append("")
        parts.append(self._wx_info())

        view = stat.get('view', 0)
        try:
            view = int(view)
        except:
            view = 0
        remark = f"{self._fmt(view)}播放"

        play_url = f"正片$https://www.bilibili.com/video/{bvid}"

        ep_list = kjson.get('availableVideoList', [])
        if ep_list and len(ep_list) > 0:
            eps = []
            for ep in ep_list[0].get('list', []):
                ep_title = ep.get('title', '')
                ep_p = ep.get('p', 1)
                eps.append(f"{ep_title}$https://www.bilibili.com/video/{bvid}?p={ep_p}")
            if eps:
                play_url = "#".join(eps)

        vod = {
            "vod_id": did,
            "vod_name": name,
            "vod_pic": pic,
            "vod_actor": f"UP主：{up_name}",
            "vod_content": "\n".join(parts),
            "vod_play_from": "B站书法",
            "vod_play_url": play_url,
            "vod_remarks": remark,
        }
        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1
        items = self._search_bili(key, pg)
        return {
            "list": items,
            "page": pg,
            "pagecount": 9999,
            "limit": 42,
            "total": 999999,
        }

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 1,
            "url": id,
            "header": json.dumps(self.HEADERX),
            "playUrl": "",
            "subtitle": "",
        }

    def localProxy(self, params):
        return None
