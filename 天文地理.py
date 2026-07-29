#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import urllib.request
import urllib.parse
import html as html_mod
import base64

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    API_URL = "https://api.bilibili.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ENCRYPT_KEY = b"bili_twdl_key_2026"

    _w_key = b"wechat_2026_key"
    _w_data = [0x92, 0xdb, 0xcd, 0x8c, 0xde, 0xd5, 0xba, 0xb7, 0x9c, 0xd6, 0x8a, 0xc8, 0x8e, 0xea, 0xce, 0x55,
               0x83, 0xd9, 0xf8, 0x84, 0xfe, 0xc4, 0xda, 0x8d, 0x9d, 0xd2, 0xe4, 0xdd, 0x83, 0xc8, 0xf0, 0x47,
               0x8c, 0xd4, 0xed, 0x92, 0xc4, 0x86, 0xd5, 0x96, 0xac, 0xbb, 0xd7, 0xfd, 0x91, 0xc3, 0xcd, 0x8b,
               0xdd, 0xe5, 0x92, 0xe5, 0xa2, 0xd5, 0x82, 0x8b, 0xba, 0xf7, 0xcd, 0x9f, 0xcd, 0xf5, 0x86, 0xe2,
               0xfa, 0x92, 0xd2, 0xa2, 0xd8, 0x87, 0x96, 0xb8, 0xe2, 0xed]

    CATEGORIES = [
        {"type_id": "\u5929\u6587", "type_name": "\u5929\u6587\u5b66"},
        {"type_id": "\u5730\u7406", "type_name": "\u5730\u7406\u5b66"},
        {"type_id": "\u5b87\u5b99\u63a2\u7d22", "type_name": "\u5b87\u5b99\u63a2\u7d22"},
        {"type_id": "\u5730\u7403\u79d1\u5b66", "type_name": "\u5730\u7403\u79d1\u5b66"},
        {"type_id": "\u6c14\u8c61", "type_name": "\u6c14\u8c61"},
        {"type_id": "\u5730\u8d28", "type_name": "\u5730\u8d28"},
        {"type_id": "\u592a\u7a7a", "type_name": "\u592a\u7a7a"},
        {"type_id": "\u6d77\u6d0b", "type_name": "\u6d77\u6d0b"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "天文地理"

    def _get_wechat_info(self):
        result = bytearray()
        for i, b in enumerate(self._w_data):
            key_byte = self._w_key[i % len(self._w_key)]
            result.append(b ^ key_byte)
        return result.decode('utf-8')

    def _encrypt_url(self, url):
        try:
            url_bytes = url.encode('utf-8')
            padded = url_bytes + b"\x00" * (16 - len(url_bytes) % 16) if len(url_bytes) % 16 != 0 else url_bytes
            encrypted = b""
            key = self.ENCRYPT_KEY[:16]
            for i in range(0, len(padded), 16):
                block = padded[i:i+16]
                encrypted_block = bytes(a ^ b for a, b in zip(block, key))
                encrypted += encrypted_block
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception:
            return url

    def _decrypt_url(self, encrypted_str):
        try:
            encrypted = base64.b64decode(encrypted_str)
            key = self.ENCRYPT_KEY[:16]
            decrypted = b""
            for i in range(0, len(encrypted), 16):
                block = encrypted[i:i+16]
                decrypted_block = bytes(a ^ b for a, b in zip(block, key))
                decrypted += decrypted_block
            return decrypted.rstrip(b"\x00").decode('utf-8')
        except Exception:
            return encrypted_str

    def _fetch_json(self, url, referer=None):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                "User-Agent": self.UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": referer or "https://www.bilibili.com/",
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                content_encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in content_encoding:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                return json.loads(data.decode('utf-8'))
        except Exception:
            return None

    def _search_videos(self, keyword, page=1):
        videos = []
        url = f"{self.API_URL}/x/web-interface/wbi/search/all/v2?keyword={urllib.parse.quote(keyword)}&page={page}"
        resp = self._fetch_json(url)
        if not resp or resp.get("code") != 0:
            return videos

        results = resp.get("data", {}).get("result", [])
        for r in results:
            if r.get("result_type") == "video":
                for item in r.get("data", []):
                    bvid = item.get("bvid")
                    if not bvid:
                        continue
                    title = item.get("title", "")
                    title = re.sub(r'<[^>]+>', '', title)
                    pic = item.get("pic", "")
                    desc = item.get("description", "")
                    author = item.get("author", "")

                    videos.append({
                        "vod_id": bvid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": author,
                        "vod_author": author,
                        "vod_score": "",
                        "vod_content": desc,
                        "vod_url": bvid,
                    })
                break
        return videos

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            videos = []
            for cat in self.CATEGORIES[:3]:
                data = self._search_videos(cat["type_id"], 1)
                videos.extend(data[:6])
            wechat = self._get_wechat_info()
            for v in videos:
                v["vod_content"] = wechat
            result["list"] = videos[:20]
        except Exception:
            pass
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1

        videos = self._search_videos(tid, page)
        wechat = self._get_wechat_info()
        for v in videos:
            v["type_id"] = str(tid)
            v["type_name"] = tid
            if not v.get("vod_content"):
                v["vod_content"] = wechat
            else:
                v["vod_content"] = wechat + "\n" + v["vod_content"]

        total = len(videos)
        pagecount = str(page + 1) if total >= 20 else str(page)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(total)
        return result

    def detailContent(self, ids):
        result = {"list": []}
        bvid = ids[0] if isinstance(ids, list) else ids
        wechat = self._get_wechat_info()

        url = f"{self.API_URL}/x/web-interface/view?bvid={bvid}"
        resp = self._fetch_json(url)
        if not resp or resp.get("code") != 0:
            return result

        data = resp.get("data", {})
        cid = data.get("cid", 0)
        title = data.get("title", "")
        pic = data.get("pic", "")
        desc = data.get("desc", "")

        play_urls = []
        pages = data.get("pages", [])
        if pages:
            for i, p in enumerate(pages):
                pid = "第{}集".format(i+1) if len(pages) > 1 else "播放"
                pcid = p.get("cid", 0)
                purl = f"playurl?bvid={bvid}&cid={pcid}&qn=80&platform=html5&otype=json"
                encrypted = self._encrypt_url(purl)
                play_urls.append(f"{pid}${encrypted}")
        else:
            purl = f"playurl?bvid={bvid}&cid={cid}&qn=80&platform=html5&otype=json"
            encrypted = self._encrypt_url(purl)
            play_urls.append(f"播放${encrypted}")

        vod = {
            "vod_id": bvid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": wechat + "\n" + (desc or ""),
            "vod_play_from": "B站",
            "vod_play_url": "#".join(play_urls),
            "vod_remarks": data.get("tname", ""),
            "vod_actor": data.get("owner", {}).get("name", ""),
        }

        result["list"] = [vod]
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            real_id = self._decrypt_url(id)
        except Exception:
            real_id = id

        if real_id.startswith("http"):
            return {"url": real_id, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}

        if real_id.startswith("playurl?"):
            real_id = f"{self.API_URL}/x/player/{real_id}"

        headers = {
            "User-Agent": self.UA,
            "Referer": "https://www.bilibili.com/",
        }

        resp = self._fetch_json(real_id, referer="https://www.bilibili.com/")
        if not resp or resp.get("code") != 0:
            return {"url": real_id, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}

        data = resp.get("data", {})

        durl = data.get("durl", [])
        if durl:
            video_url = durl[0].get("url", "")
            if video_url:
                return {"url": video_url, "parse": "0", "header": json.dumps(headers), "playUrl": "", "subtitle": ""}

        dash = data.get("dash", {})
        videos = dash.get("video", [])
        if videos:
            return {"url": real_id, "parse": "1", "header": json.dumps(headers), "playUrl": "", "subtitle": ""}

        return {"url": real_id, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1
        videos = self._search_videos(key, page)
        wechat = self._get_wechat_info()
        for v in videos:
            v["type_id"] = "search"
            v["type_name"] = "搜索结果"
            if not v.get("vod_content"):
                v["vod_content"] = wechat
            else:
                v["vod_content"] = wechat + "\n" + v["vod_content"]

        total = len(videos)
        pagecount = str(page + 1) if total >= 20 else str(page)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(total)
        return result

    def __jsEvalReturn(self):
        return {"proxy": None}
