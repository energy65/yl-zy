#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import time
import ssl
import gzip
import urllib.request
import urllib.parse
import html as html_mod

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
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    _key = b"m1999_yl_2026"

    _s_site = [0x05, 0x45, 0x4d, 0x49, 0x4a, 0x65, 0x56, 0x43, 0x32, 0x03, 0x09, 0x0b, 0x0f, 0x43, 0x42, 0x5b, 0x4a]
    _s_wx = [0x8b, 0x8b, 0xa9, 0xdc, 0xb3, 0xc4, 0x91, 0xd1, 0xf0, 0xd6, 0x8b, 0x84, 0xd0, 0xdc, 0xb6]
    _s_qq = [0x5c, 0x01, 0x0c, 0x0d, 0x0c, 0x66, 0x4b, 0x5d, 0x6a, 0x00]
    _s_promo = [0x67, 0x3b, 0xdc, 0x87, 0x97, 0xbb, 0xc6, 0xcd, 0xba, 0xb7, 0x9c, 0xd6, 0x8a, 0xfa, 0xd4, 0xb6, 0x8e, 0xda, 0xdf, 0xf5, 0x8a, 0xe5, 0xa2, 0xd5, 0xb8, 0xad, 0x85, 0x8c, 0x96, 0xdd, 0x82, 0xe9, 0x9f, 0xdd, 0xd8, 0xd1, 0xb0, 0xbf, 0x3c, 0x3c, 0x60, 0xde, 0x87, 0x9d, 0xb0, 0xc5, 0xf6, 0x6e, 0x02, 0x05, 0x06, 0x03, 0x54, 0x03, 0x08, 0x0c, 0x0b, 0x55, 0x9f, 0xf7, 0xeb, 0xd7, 0x94, 0xa8, 0xd2, 0xd1, 0xa9, 0xd1, 0x8d, 0x91, 0xb7, 0xcc, 0xe8, 0xb9, 0x88, 0xa0, 0xd7, 0x86, 0xd0, 0xd4, 0xa5, 0x91, 0xdf, 0xe5, 0xe9, 0x89, 0xd5, 0xa9, 0xdf, 0x8e, 0xba, 0x8b, 0x9d, 0x9b, 0xd1, 0x86, 0xd1, 0x9c, 0xe9, 0xec, 0xd4, 0x83, 0x9a, 0xd9, 0xd1, 0xb0]

    CATEGORIES = [
        {"type_id": "1", "type_name": "最新电影"},
        {"type_id": "2", "type_name": "国产剧"},
        {"type_id": "3", "type_name": "日韩剧"},
        {"type_id": "4", "type_name": "美剧"},
        {"type_id": "5", "type_name": "番剧"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "蓝光影视网"

    def _dec(self, data):
        key = self._key
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)]).decode("utf-8")

    @property
    def BASE_URL(self):
        return self._dec(self._s_site)

    @property
    def WECHAT_INFO(self):
        return self._dec(self._s_promo)

    @property
    def WECHAT_NAME(self):
        return self._dec(self._s_wx)

    @property
    def QQ_GROUP(self):
        return self._dec(self._s_qq)

    def _fetch(self, url, data=None):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": self.BASE_URL + "/",
        }
        try:
            quoted = urllib.parse.quote(url, safe=":/?&=%+~-._#$")
            req = urllib.request.Request(quoted, headers=headers)
            if data is not None:
                req.method = "POST"
                req.data = urllib.parse.urlencode(data).encode("utf-8")
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if "gzip" in enc:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                for coding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        return raw.decode(coding)
                    except Exception:
                        continue
                return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def getHtml(self, url):
        return self._fetch(url)

    def _post_json(self, url, data):
        text = self._fetch(url, data=data)
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _norm_filter(self, data):
        if isinstance(data, dict):
            pass
        elif isinstance(data, str):
            try:
                parsed = json.loads(data)
                if not isinstance(parsed, dict):
                    return {}
                data = parsed
            except Exception:
                return {}
        else:
            return {}
        out = {}
        for key, val in data.items():
            if isinstance(val, (list, tuple)):
                val = next((x for x in val if x not in (None, "")), "")
            if val not in (None, ""):
                out[key] = str(val)
        return out

    def _api_vod_list(self, tid, page, extend=None, filter_data=None):
        data = {"type": str(tid), "page": str(page), "by": "time"}
        for key, val in self._norm_filter(extend).items():
            if key not in ("type", "page", "by"):
                data[key] = val
        for key, val in self._norm_filter(filter_data).items():
            if key not in data:
                data[key] = val
        return self._post_json(self.BASE_URL + "/index.php/ds_api/vod", data)

    def _api_to_vod(self, item):
        return {
            "vod_id": str(item.get("vod_id", "")),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "vod_remarks": item.get("vod_remarks") or "",
        }

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            for cat in self.CATEGORIES:
                resp = self._api_vod_list(cat["type_id"], 1, None, None)
                if resp.get("code") == 1:
                    for item in (resp.get("list") or []):
                        result["list"].append(self._api_to_vod(item))
        except Exception:
            pass
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
            resp = self._api_vod_list(tid, page, extend, filter)
            if resp.get("code") == 1:
                for item in (resp.get("list") or []):
                    result["list"].append(self._api_to_vod(item))
                result["pagecount"] = str(resp.get("pagecount") or page)
                result["total"] = str(resp.get("total") or len(result["list"]))
            return result
        except Exception:
            return result

    def _extract_episodes(self, html):
        names = []
        tab_m = re.search(r'<div class="anthology-tab[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S)
        if tab_m:
            for a in re.findall(r'<a[^>]*>(.*?)</a>', tab_m.group(1), re.S):
                n = re.sub(r'<span[^>]*class="[^"]*badge[^"]*"[^>]*>.*?</span>', '', a)
                n = self.clean(re.sub(r'<[^>]+>|&nbsp;', '', n))
                if n:
                    names.append(n)

        groups = []
        for m in re.finditer(r'<a[^>]*href="(/vod/play/id/(\d+)/sid/(\d+)/nid/(\d+)\.html)"[^>]*>(.*?)</a>', html, re.S):
            full, sid, nid, txt = m.group(1), m.group(3), m.group(4), m.group(5)
            ep = self.clean(re.sub(r'<[^>]+>', '', txt))
            if not ep:
                ep = "第%s集" % nid
            if groups and groups[-1][0] == sid:
                groups[-1][1].append((ep, full))
            else:
                groups.append((sid, [(ep, full)]))

        if not groups:
            return "", ""

        sources = []
        for i, (sid, eps) in enumerate(groups):
            sn = names[i] if i < len(names) else "线路%s" % sid
            sources.append((sn, eps))

        play_from = "$$$".join(sn for sn, eps in sources)
        play_url = "$$$".join("#".join("%s$%s" % (ep, u) for ep, u in eps) for sn, eps in sources)
        return play_from, play_url

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = re.sub(r"\D", "", str(ids[0] if isinstance(ids, list) and ids else ids))
            if not vid:
                return result
            html = self.getHtml("{}/vod/detail/id/{}.html".format(self.BASE_URL, vid))
            if not html:
                return result

            vod = {"vod_id": vid}
            desc = ""

            m = re.search(r'<h3 class="slide-info-title hide">([^<]+)', html)
            if m:
                vod["vod_name"] = self.clean(m.group(1))
            if not vod.get("vod_name"):
                vod["vod_name"] = vid

            m = re.search(r'<div class="detail-pic"><img[^>]*data-src="([^"]+)"', html)
            if m:
                vod["vod_pic"] = m.group(1)

            info_m = re.search(r'<div class="info-parameter none">(.*?)</div>\s*</div>', html, re.S)
            if info_m:
                for li in re.findall(r'<li[^>]*>(.*?)</li>', info_m.group(1), re.S):
                    em = re.search(r'<em[^>]*>([^<：:]+)[：:]\s*</em>\s*(.*)$', li, re.S)
                    if not em:
                        continue
                    label = self.clean(em.group(1))
                    val = self.clean(re.sub(r'<[^>]+>', '', em.group(2))).strip('，,')
                    if label == "片名" and not vod.get("vod_name"):
                        vod["vod_name"] = val
                    elif label == "状态":
                        vod["vod_remarks"] = val
                    elif label == "主演":
                        vod["vod_actor"] = val
                    elif label == "导演":
                        vod["vod_director"] = val
                    elif label == "年份":
                        vod["vod_year"] = val
                    elif label == "地区":
                        vod["vod_area"] = val
                    elif label == "类型":
                        vod["vod_class"] = val
                    elif label == "语言":
                        vod["vod_lang"] = val
                    elif label == "简介":
                        desc = val

            if not vod.get("vod_remarks"):
                m = re.search(r'<span class="slide-info-remarks cor5">([^<]+)', html)
                if m:
                    vod["vod_remarks"] = self.clean(m.group(1))

            if not vod.get("vod_class"):
                cls = re.findall(r'/vod/search/class/([^\"]+)"[^>]*>([^<]+)</a>', html)
                if cls:
                    parts = [self.clean(c[1]) for c in cls if self.clean(c[1])]
                    if parts:
                        vod["vod_class"] = "/".join(parts[:8])

            if not desc:
                m = re.search(r'<div id="height_limit" class="text cor3">(.*?)</div>', html, re.S)
                if m:
                    desc = self.clean(re.sub(r'<[^>]+>', '', m.group(1)))

            wechat = self.WECHAT_INFO
            vod["vod_content"] = (wechat + "\n\n" + desc) if desc else wechat

            play_from, play_url = self._extract_episodes(html)
            if play_url:
                vod["vod_play_from"] = play_from
                vod["vod_play_url"] = play_url

            result["list"] = [vod]
            return result
        except Exception:
            return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
            kw = urllib.parse.quote(str(key))
            url = "{}/vod/search/wd/{}.html".format(self.BASE_URL, kw)
            if page > 1:
                url = "{}/vod/search/wd/{}/page/{}.html".format(self.BASE_URL, kw, page)
            html = self.getHtml(url)
            if not html:
                return result

            items = []
            seen = set()
            blocks = re.split(r'<div class="vod-detail[^"]*search-list[^"]*">', html)
            for block in blocks[1:]:
                m = re.search(r'/vod/detail/id/(\d+)\.html', block)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                name = ""
                nm = re.search(r'<h3 class="slide-info-title hide">([^<]+)', block)
                if nm:
                    name = self.clean(nm.group(1))
                pic = ""
                pm = re.search(r'data-src="([^"]+)"', block)
                if pm:
                    pic = pm.group(1)
                remark = ""
                rm = re.search(r'<span class="slide-info-remarks cor5">([^<]+)', block)
                if rm:
                    remark = self.clean(rm.group(1))
                items.append({
                    "vod_id": vid,
                    "vod_name": name or vid,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })

            result["list"] = items
            result["total"] = str(len(items))
            return result
        except Exception:
            return result

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = id
            if play_url and not play_url.startswith("http"):
                play_url = self.BASE_URL + "/" + play_url.lstrip("/")
            html = self.getHtml(play_url)
            if html:
                m = re.search(r'var player_aaaa=(\{.*\})</script>', html, re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))
                    except Exception:
                        data = {}
                    video_url = data.get("url", "")
                else:
                    m2 = re.search(r'"url"\s*:\s*"([^"]+)"', html)
                    video_url = m2.group(1) if m2 else ""
                video_url = video_url.replace("\\/", "/")
                if video_url and (".m3u8" in video_url or ".mp4" in video_url or video_url.startswith("http")):
                    headers = {"User-Agent": self.UA, "Referer": self.BASE_URL + "/"}
                    return {
                        "url": video_url,
                        "parse": "0",
                        "header": json.dumps(headers),
                        "playUrl": "",
                        "subtitle": "",
                    }
        except Exception:
            pass

        return {
            "url": id,
            "parse": "0",
            "header": "",
            "playUrl": "",
            "subtitle": "",
        }

    def __jsEvalReturn(self):
        return {"proxy": None}
