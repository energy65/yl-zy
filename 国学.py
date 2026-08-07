#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
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
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    BASE_URL = "https://api.bilibili.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    _w_key = [121, 117, 97, 110, 108, 105, 95, 50, 48, 50, 54]
    _w_data = [
        156, 203, 207, 138, 211, 200, 186, 183, 156, 214, 138, 238, 144,
        238, 217, 78, 143, 229, 162, 213, 184, 173, 145, 200, 206, 138,
        215, 223, 185, 131, 183, 16, 217, 197, 249, 135, 245, 216, 140,
        251, 168, 212, 142, 174, 145, 193, 201, 134, 217, 237, 185, 136,
        160, 215, 134, 196, 144, 253, 198, 138, 211, 207, 215, 186, 169,
        208, 244, 229, 137, 219, 204, 142, 214, 186
    ]

    CATEGORIES = [
        {"type_id": "国学经典", "type_name": "国学经典"},
        {"type_id": "唐诗", "type_name": "唐诗"},
        {"type_id": "宋词", "type_name": "宋词"},
        {"type_id": "论语", "type_name": "论语"},
        {"type_id": "弟子规", "type_name": "弟子规"},
        {"type_id": "三字经", "type_name": "三字经"},
        {"type_id": "千字文", "type_name": "千字文"},
        {"type_id": "诗经", "type_name": "诗经"},
        {"type_id": "古文观止", "type_name": "古文观止"},
        {"type_id": "四大名著", "type_name": "四大名著"},
        {"type_id": "中医养生", "type_name": "中医养生"},
        {"type_id": "书法", "type_name": "书法"},
        {"type_id": "国画", "type_name": "国画"},
        {"type_id": "围棋", "type_name": "围棋"},
        {"type_id": "京剧", "type_name": "京剧"},
        {"type_id": "茶道", "type_name": "茶道"},
        {"type_id": "中国历史", "type_name": "中国历史"},
        {"type_id": "古诗词", "type_name": "古诗词"},
    ]

    def _get_wechat_info(self):
        try:
            result = bytearray()
            for i, b in enumerate(self._w_data):
                key_byte = self._w_key[i % len(self._w_key)]
                result.append(b ^ key_byte)
            return result.decode('utf-8')
        except Exception:
            return ''

    def init(self, extend=""):
        pass

    def getName(self):
        return "国学"

    def getHtml(self, url, ref=""):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                "User-Agent": self.UA,
                "Referer": ref or "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Cookie": "buvid3=infoc; b_nut=1; _uuid=1",
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
                return data.decode('utf-8', errors='replace')
        except Exception:
            return ""

    def clean(self, text):
        if not text:
            return ""
        text = str(text)
        text = text.replace("&#34;", '"').replace("&#39;", "'")
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&nbsp;", " ")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(
            "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=%E5%9B%BD%E5%AD%A6&page=1&order=click",
            "https://www.bilibili.com/"
        )
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])[:30]
            for v in items:
                bvid = v.get("bvid", "")
                if not bvid:
                    continue
                title = self.clean(v.get("title", ""))
                pic = v.get("pic", "")
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                duration = v.get("duration", "")
                if isinstance(duration, (int, float)):
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    duration = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_score": str(v.get("video_review", "")),
                    "vod_remarks": duration,
                    "vod_content": self._get_wechat_info(),
                })
        except Exception:
            pass
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1
        tid_str = str(tid)
        keyword = urllib.parse.quote(tid_str)
        url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={keyword}&page={page}&order=click"
        html = self.getHtml(url, "https://www.bilibili.com/")
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])
            for v in items:
                bvid = v.get("bvid", "")
                if not bvid:
                    continue
                title = self.clean(v.get("title", ""))
                pic = v.get("pic", "")
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                duration = v.get("duration", "")
                if isinstance(duration, (int, float)):
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    duration = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_score": str(v.get("video_review", "")),
                    "vod_remarks": duration,
                    "type_id": tid,
                    "type_name": tid_str,
                })
            pagecount = "1"
            num_pages = data.get("data", {}).get("numPages", 0)
            if num_pages > 0:
                pagecount = str(num_pages)
            result["pagecount"] = pagecount
            result["total"] = data.get("data", {}).get("numResults", len(items))
        except Exception:
            pass
        return result

    def detailContent(self, ids):
        result = {"list": []}
        bvid = ids[0] if isinstance(ids, list) and ids else ids
        bvid = str(bvid).strip()
        if not bvid:
            return result
        html = self.getHtml(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            "https://www.bilibili.com/"
        )
        if not html:
            return result
        try:
            data = json.loads(html)
            if data.get("code") != 0:
                return result
            vd = data.get("data", {})
            title = self.clean(vd.get("title", ""))
            pic = vd.get("pic", "")
            if pic and pic.startswith("//"):
                pic = "https:" + pic
            desc = self.clean(vd.get("desc", ""))
            owner = vd.get("owner", {})
            author = owner.get("name", "") if owner else ""
            vod = {
                "vod_id": bvid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": author,
                "vod_director": author,
                "vod_content": self._get_wechat_info() + "\n" + desc if desc else self._get_wechat_info(),
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_class": "国学",
                "vod_lang": "国语",
            }
            pages = vd.get("pages", [vd])
            play_urls = []
            for i, p in enumerate(pages):
                cid = p.get("cid", vd.get("cid", 0))
                part_name = p.get("part", f"P{i+1}")
                ep_name = self.clean(part_name) if part_name != "" else f"P{i+1}"
                play_urls.append(f"{ep_name}${bvid}_{cid}")
            vod["vod_play_from"] = "B站"
            vod["vod_play_url"] = "#".join(play_urls) if play_urls else ""
            result["list"] = [vod]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1
        keyword = urllib.parse.quote(str(key))
        url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={keyword}&page={page}"
        html = self.getHtml(url, "https://www.bilibili.com/")
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])
            for v in items:
                bvid = v.get("bvid", "")
                if not bvid:
                    continue
                title = self.clean(v.get("title", ""))
                pic = v.get("pic", "")
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                duration = v.get("duration", "")
                if isinstance(duration, (int, float)):
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    duration = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_score": str(v.get("video_review", "")),
                    "vod_remarks": duration,
                    "type_id": "国学",
                    "type_name": "搜索结果",
                })
            pagecount = "1"
            num_pages = data.get("data", {}).get("numPages", 0)
            if num_pages > 0:
                pagecount = str(num_pages)
            result["pagecount"] = pagecount
            result["total"] = data.get("data", {}).get("numResults", len(items))
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags):
        parts = str(id).split("_")
        if len(parts) < 2:
            return {"url": id, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}
        bvid = parts[0]
        cid = parts[1]
        url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&platform=html5&otype=json&high_quality=1"
        html = self.getHtml(url, "https://www.bilibili.com/")
        if html:
            try:
                data = json.loads(html)
                if data.get("code") == 0:
                    dd = data.get("data", {})
                    durl = dd.get("durl", [])
                    if durl and durl[0].get("url"):
                        video_url = durl[0]["url"]
                        headers = {
                            "User-Agent": self.UA,
                            "Referer": "https://www.bilibili.com/",
                            "Accept": "*/*",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                            "Connection": "keep-alive",
                        }
                        return {"url": video_url, "parse": "0", "header": json.dumps(headers), "playUrl": "", "subtitle": ""}
            except Exception:
                pass
        return {"url": id, "parse": "1", "header": json.dumps({"User-Agent": self.UA, "Referer": "https://www.bilibili.com/"}), "playUrl": "", "subtitle": ""}

    def __jsEvalReturn(self):
        return {"proxy": None}
