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
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

    # XOR 密钥
    _w_key = b"paobu_2026_key"

    # XOR 加密的微信信息
    _w_data = [149, 223, 193, 134, 202, 254, 215, 181, 158, 210, 227, 252, 128, 246, 199, 67,
               137, 216, 229, 186, 184, 171, 218, 139, 240, 143, 222, 207, 150, 208, 232, 64,
               154, 227, 190, 214, 169, 130, 186, 207, 255, 157, 204, 249, 135, 214, 221, 183,
               135, 180, 212, 140, 207, 142, 213, 196, 149, 253, 199, 132, 207, 207, 215, 186, 169]

    # XOR 加密的源站地址
    _u_data = [24, 21, 27, 18, 6, 101, 29, 31, 69, 65, 40, 69, 7, 16, 28, 8, 13, 11, 25, 54, 28, 83, 93, 91, 112]

    # XOR 加密的接口地址
    _a_data = [24, 21, 27, 18, 6, 101, 29, 31, 83, 70, 54, 69, 7, 16, 28, 8, 13, 11, 25, 54, 28, 83, 93, 91]

    # 分类：跑步类游戏
    CATEGORIES = [
        {"type_id": "跑步游戏", "type_name": "跑步游戏"},
        {"type_id": "神庙逃亡", "type_name": "神庙逃亡"},
        {"type_id": "地铁跑酷", "type_name": "地铁跑酷"},
        {"type_id": "天天跑酷", "type_name": "天天跑酷"},
        {"type_id": "像素跑酷", "type_name": "像素跑酷"},
    ]

    def _xor_decrypt(self, data):
        try:
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ self._w_key[i % len(self._w_key)]
            return plain.decode('utf-8')
        except Exception:
            return ""

    def _get_wechat_info(self):
        return self._xor_decrypt(self._w_data)

    def _get_site_url(self):
        return self._xor_decrypt(self._u_data).rstrip("/")

    def _get_api_url(self):
        return self._xor_decrypt(self._a_data).rstrip("/")

    def init(self, extend=""):
        pass

    def getName(self):
        return "跑步游戏"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def getHtml(self, url, ref=""):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            site_url = self._get_site_url()
            headers = {
                "User-Agent": self.UA,
                "Referer": ref or (site_url + "/"),
                "Origin": site_url,
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
        site_url = self._get_site_url()
        api_url = self._get_api_url()
        html = self.getHtml(
            api_url + "/x/web-interface/search/type?search_type=video&keyword=" + urllib.parse.quote("跑步游戏") + "&page=1&order=click",
            site_url + "/"
        )
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])[:30]
            wechat = self._get_wechat_info()
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
                    duration = "%02d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": duration,
                    "vod_content": wechat,
                })
        except Exception:
            pass
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        site_url = self._get_site_url()
        api_url = self._get_api_url()
        page = int(pg) if str(pg).isdigit() else 1
        tid_str = str(tid)
        keyword = urllib.parse.quote(tid_str)
        url = api_url + "/x/web-interface/search/type?search_type=video&keyword=" + keyword + "&page=" + str(page) + "&order=click"
        html = self.getHtml(url, site_url + "/")
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])
            wechat = self._get_wechat_info()
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
                    duration = "%02d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": duration,
                    "vod_content": wechat,
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
        site_url = self._get_site_url()
        api_url = self._get_api_url()
        wechat = self._get_wechat_info()
        bvid = ids[0] if isinstance(ids, list) and ids else ids
        bvid = str(bvid).strip()
        if not bvid:
            return result
        html = self.getHtml(
            api_url + "/x/web-interface/view?bvid=" + bvid,
            site_url + "/"
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
                "vod_content": (wechat + "\n" + desc) if desc else wechat,
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_class": "跑步游戏",
                "vod_lang": "国语",
            }
            pages = vd.get("pages", [vd])
            play_urls = []
            for i, p in enumerate(pages):
                cid = p.get("cid", vd.get("cid", 0))
                part_name = p.get("part", "P" + str(i + 1))
                ep_name = self.clean(part_name) if part_name else ("P" + str(i + 1))
                play_urls.append(ep_name + "$" + bvid + "_" + str(cid))
            vod["vod_play_from"] = "B站跑步游戏"
            vod["vod_play_url"] = "#".join(play_urls) if play_urls else ""
            result["list"] = [vod]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        site_url = self._get_site_url()
        api_url = self._get_api_url()
        page = int(pg) if str(pg).isdigit() else 1
        keyword = urllib.parse.quote(str(key))
        url = api_url + "/x/web-interface/search/type?search_type=video&keyword=" + keyword + "&page=" + str(page)
        html = self.getHtml(url, site_url + "/")
        if not html:
            return result
        try:
            data = json.loads(html)
            items = data.get("data", {}).get("result", [])
            wechat = self._get_wechat_info()
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
                    duration = "%02d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)
                result["list"].append({
                    "vod_id": bvid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": duration,
                    "vod_content": wechat,
                    "type_id": "search",
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
        site_url = self._get_site_url()
        api_url = self._get_api_url()
        parts = str(id).split("_")
        if len(parts) < 2:
            return {"url": id, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}
        bvid = parts[0]
        cid = parts[1]
        url = api_url + "/x/player/playurl?bvid=" + bvid + "&cid=" + cid + "&qn=80&platform=html5&otype=json&high_quality=1"
        html = self.getHtml(url, site_url + "/")
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
                            "Referer": site_url + "/",
                            "Accept": "*/*",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                            "Connection": "keep-alive",
                        }
                        return {"url": video_url, "parse": "0", "header": json.dumps(headers), "playUrl": "", "subtitle": ""}
            except Exception:
                pass
        return {"url": id, "parse": "1", "header": json.dumps({"User-Agent": self.UA, "Referer": site_url + "/"}), "playUrl": "", "subtitle": ""}

    def localProxy(self, params):
        return None

    def __jsEvalReturn(self):
        return {"proxy": None}
