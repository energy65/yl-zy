# -*- coding: utf-8 -*-
import re
import sys
import json
import time
import ssl
import os
import html as html_mod
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

        def getName(self):
            return ""

        def homeContent(self, filter):
            return {}

        def homeVideoContent(self):
            return {}

        def categoryContent(self, tid, pg, filter, extend):
            return {}

        def searchContent(self, key, quick, pg="1"):
            return {}

        def searchContentPage(self, key, quick, page):
            return {}

        def detailContent(self, ids):
            return {}

        def playerContent(self, flag, id, vipFlags):
            return {}


S_TABLE = {
    "S11": 7, "S12": 12, "S13": 17, "S14": 22,
    "S21": 5, "S22": 9, "S23": 14, "S24": 20,
    "S31": 4, "S32": 11, "S33": 16, "S34": 23,
    "S41": 6, "S42": 10, "S43": 15, "S44": 21,
}
OP_RE = re.compile(
    r"([abcd])\s*=\s*(FF|GG|HH|II)\(\s*([abcd])\s*,\s*([abcd])\s*,\s*([abcd])\s*,\s*([abcd])\s*,\s*"
    r"x\[k\s*\+\s*(\d+)\]\s*,\s*(S\d+)\s*,\s*(0x[0-9A-Fa-f]+)\s*\)"
)
AFFIX_RE = re.compile(r'temp\s*=\s*"([^"]*)"\s*\+\s*temp\s*\+\s*"([^"]*)"')


def _rotl(x, s):
    return ((x << s) | (x >> (32 - s))) & 0xffffffff


def _f(x, y, z):
    return (x & y) | ((~x) & z)


def _g(x, y, z):
    return (x & z) | (y & (~z))


def _h(x, y, z):
    return x ^ y ^ z


def _i(x, y, z):
    return y ^ (x | (~z))


def _ff(a, b, c, d, x, s, ac):
    return (_rotl((a + _f(b, c, d) + x + ac) & 0xffffffff, s) + b) & 0xffffffff


def _gg(a, b, c, d, x, s, ac):
    return (_rotl((a + _g(b, c, d) + x + ac) & 0xffffffff, s) + b) & 0xffffffff


def _hh(a, b, c, d, x, s, ac):
    return (_rotl((a + _h(b, c, d) + x + ac) & 0xffffffff, s) + b) & 0xffffffff


def _ii(a, b, c, d, x, s, ac):
    return (_rotl((a + _i(b, c, d) + x + ac) & 0xffffffff, s) + b) & 0xffffffff


_FNS = {"FF": _ff, "GG": _gg, "HH": _hh, "II": _ii}


def _words(msg):
    n = len(msg)
    nw = ((n + 8 - ((n + 8) % 64)) // 64 + 1) * 16
    w = [0] * nw
    for idx, ch in enumerate(msg):
        w[idx // 4] |= ord(ch) << ((idx % 4) * 8)
    w[n // 4] |= 0x80 << ((n % 4) * 8)
    w[nw - 2] = (n << 3) & 0xffffffff
    w[nw - 1] = (n >> 29) & 0xffffffff
    return w


def _custom_md5(c2, ops):
    x = _words(c2)
    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    for k in range(0, len(x), 16):
        aa, bb, cc, dd = a, b, c, d
        st = {"a": a, "b": b, "c": c, "d": d}
        for lhs, fn, v1, v2, v3, v4, idx, s, ac in ops:
            st[lhs] = _FNS[fn](st[v1], st[v2], st[v3], st[v4], x[k + int(idx)], S_TABLE[s], int(ac, 16))
        a = (st["a"] + aa) & 0xffffffff
        b = (st["b"] + bb) & 0xffffffff
        c = (st["c"] + cc) & 0xffffffff
        d = (st["d"] + dd) & 0xffffffff

    def hx(v):
        return ''.join('%02x' % ((v >> (8 * j)) & 255) for j in range(4))

    return hx(a) + hx(b) + hx(c) + hx(d)


class Spider(BaseSpider):
    HOST = "https://www.bykhw.com"
    MHOST = "https://m.bykhw.com"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    MUA = (
        "Mozilla/5.0 (Linux; Android 10; Pixel 3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"
    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n"
        "QQ群：1054592152"
    )

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "14", "type_name": "电视剧"},
        {"type_id": "23", "type_name": "综艺"},
        {"type_id": "28", "type_name": "动漫"},
        {"type_id": "34", "type_name": "短剧"},
        {"type_id": "42", "type_name": "体育赛事"},
        {"type_id": "9", "type_name": "纪录片"},
        {"type_id": "47", "type_name": "演唱会"},
    ]

    CLASS_MAP = {
        "1": {
            "动作": "2", "动作片": "2", "喜剧": "3", "喜剧片": "3",
            "爱情": "4", "爱情片": "4", "科幻": "5", "科幻片": "5",
            "恐怖": "6", "恐怖片": "6", "剧情": "7", "剧情片": "7",
            "战争": "8", "战争片": "8", "悬疑": "10", "悬疑片": "10",
            "动画": "11", "动画片": "11", "犯罪": "12", "犯罪片": "12",
            "奇幻": "13", "奇幻片": "13", "解说": "48", "影视解说": "48",
            "预告": "49", "预告片": "49",
            "武侠": "2", "历史": "7", "文艺": "7",
        },
        "14": {
            "国产": "15", "国产剧": "15", "香港": "16", "香港剧": "16",
            "台湾": "17", "台湾剧": "17", "欧美": "18", "欧美剧": "18",
            "韩国": "19", "韩国剧": "19", "日本": "20", "日本剧": "20",
            "泰剧": "21", "海外": "22", "海外剧": "22",
            "古装": "15", "都市": "15", "历史": "15", "谍战": "15", "家庭": "15",
        },
        "28": {
            "国产": "29", "国产动漫": "29", "日韩": "30", "日韩动漫": "30",
            "欧美": "31", "欧美动漫": "31", "港台": "32", "港台动漫": "32",
            "海外": "33", "海外动漫": "33", "有声": "35", "有声动漫": "35",
        },
        "23": {
            "大陆": "24", "大陆综艺": "24", "日韩": "25", "日韩综艺": "25",
        },
    }

    AREA_MAP = {
        "大陆": "1", "香港": "2", "台湾": "3", "美国": "4", "法国": "5",
        "英国": "6", "日本": "7", "韩国": "8", "德国": "9", "泰国": "10",
        "印度": "11", "意大利": "12", "西班牙": "13", "加拿大": "14",
    }
    YEAR_MAP = {
        "2026": "1", "2025": "2", "2024": "3", "2023": "4", "2022": "5",
        "2021": "6", "2020": "7", "2019": "8", "2018": "9", "2017": "10",
        "2016": "11", "更早": "12",
    }
    LANG_MAP = {
        "国语": "1", "粤语": "2", "闽南语": "3", "韩语": "4",
        "日语": "5", "英语": "6", "法语": "7", "德语": "8",
    }

    FILTER_TYPES = {
        "1": ["动作片", "喜剧片", "爱情片", "科幻片", "恐怖片", "剧情片",
              "战争片", "悬疑片", "动画片", "犯罪片", "奇幻片", "影视解说",
              "预告片", "武侠", "历史", "文艺"],
        "14": ["国产剧", "香港剧", "台湾剧", "欧美剧", "韩国剧", "日本剧",
               "泰剧", "海外剧", "古装", "都市", "历史", "谍战", "家庭"],
        "28": ["国产动漫", "日韩动漫", "欧美动漫", "港台动漫", "海外动漫", "有声动漫"],
        "23": ["大陆综艺", "日韩综艺"],
    }

    def init(self, extend=""):
        self.host = self.HOST
        self.mhost = self.MHOST
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        self._cj = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cj),
            urllib.request.HTTPSHandler(context=self._ctx),
        )
        self._index = {}
        self._index_ts = 0
        self._index_built = False
        self._deep_turn = 0
        self._deep_cursor = {}
        self._deep_done = set()
        self._load_index()

    def getName(self):
        return "葵花影视网"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def _request(self, url, referer=None, xhr=False, timeout=25):
        headers = {
            "User-Agent": self.MUA if "m.bykhw.com" in url else self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        if xhr:
            headers["X-Requested-With"] = "XMLHttpRequest"
        req = urllib.request.Request(url, headers=headers)
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                return resp.status, resp.read(), resp.geturl()
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read(), url
            except Exception:
                return e.code, b"", url
        except Exception:
            return 0, b"", url

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("gbk", "gb2312", "utf-8"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _challenge(self, text):
        return 'c2="' in text and "/nnxswnn/" in text

    def _solve_challenge(self, text, page_url):
        m = re.search(r'c2\s*=\s*"([^"]+)"', text)
        s = re.search(r'src="([^"]*?/nnxswnn/[^"]+)"', text)
        if not m or not s:
            return False
        js_url = urllib.parse.urljoin(page_url, s.group(1))
        status, data, _ = self._request(js_url, referer=page_url)
        if status != 200 or not data:
            return False
        js = self._decode(data)
        ops = OP_RE.findall(js)
        affix = AFFIX_RE.search(js)
        if len(ops) < 64 or not affix:
            return False
        path = affix.group(1) + _custom_md5(m.group(1), ops) + affix.group(2)
        ch_url = urllib.parse.urljoin(page_url, path)
        status, data, _ = self._request(ch_url, referer=page_url, xhr=True)
        return status == 200 and data[:4].lower().startswith(b"ok")

    def _get(self, url, referer=None, retries=5):
        if not url.startswith("http"):
            url = self.host + url
        for _ in range(retries):
            status, data, _ = self._request(url, referer=referer)
            if status == 503:
                time.sleep(5)
                continue
            if status == 0:
                time.sleep(1)
                continue
            text = self._decode(data)
            if self._challenge(text):
                if self._solve_challenge(text, url):
                    time.sleep(0.2)
                    continue
                return text
            return text
        return ""

    def _img(self, url):
        if not url:
            return self.DEFAULT_PIC
        url = html_mod.unescape(url).strip()
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = self.host + url
        return url

    def _clean(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        return html_mod.unescape(text).replace("\xa0", " ").strip()

    def _parse_items(self, text):
        items = []
        seen = set()
        if not text:
            return items
        for block in re.findall(r'<dl\b[^>]*class="[^"]*B[^"]*"[^>]*>(.*?)</dl>', text, re.S):
            m = re.search(r'href="(?:https?://[^"]*)?/kuihuamv/(\d+)/"', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            name = ""
            am = re.search(r'alt="([^"]+)"', block)
            if am:
                name = self._clean(am.group(1))
            if not name:
                tm = re.search(r'<dt>\s*<a[^>]*>([^<]+)</a>', block, re.S)
                if tm:
                    name = self._clean(tm.group(1))
            if not name:
                continue
            pic = ""
            pm = re.search(r'(?:data-src|data-original|src)="([^"]+)"', block)
            if pm:
                pic = self._img(pm.group(1))
            remark = ""
            rm = re.search(r'<span class="bott">\s*<a[^>]*>([^<]+)</a>', block, re.S)
            if rm:
                remark = self._clean(rm.group(1))
            if not remark:
                rm = re.search(r'<span class="ysj">([^<]+)</span>', block)
                if rm:
                    remark = self._clean(rm.group(1))
            actor = ""
            ac = re.search(r'<dd class="act">\s*<a[^>]*>([^<]+)</a>', block, re.S)
            if ac:
                actor = self._clean(ac.group(1))
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
                "vod_actor": actor,
            })
        return items

    def _meta(self, text, prop):
        m = re.search(r'property="%s"\s+content="([^"]*)"' % re.escape(prop), text)
        if not m:
            m = re.search(r'content="([^"]*)"\s+property="%s"' % re.escape(prop), text)
        return html_mod.unescape(m.group(1)).strip() if m else ""

    def _extract_m3u8(self, text):
        if not text:
            return ""
        patterns = [
            r'property="og:video:url"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:video:url"',
            r'<source[^>]+src="([^"]+)"',
            r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1',
            r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.S)
            if not m:
                continue
            url = m.group(m.lastindex) if m.lastindex else m.group(1)
            url = url.replace("\\/", "/").strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http"):
                return url
        return ""

    def _index_file(self):
        base = globals().get("__file__")
        if base:
            base = os.path.dirname(os.path.abspath(base))
        else:
            base = os.getcwd()
        return os.path.join(base, "葵花影视网_index.json")

    def _load_index(self):
        try:
            with open(self._index_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            for it in data.get("items", []):
                if it.get("vod_id"):
                    self._index[it["vod_id"]] = it
            self._index_ts = data.get("ts", 0)
            if self._index:
                self._index_built = True
        except Exception:
            pass

    def _save_index(self):
        try:
            items = list(self._index.values())
            if len(items) > 40000:
                items = items[-40000:]
            with open(self._index_file(), "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "items": items}, f, ensure_ascii=False)
        except Exception:
            pass

    def _add_items(self, items):
        for it in items:
            vid = it.get("vod_id")
            if vid and vid not in self._index:
                self._index[vid] = it

    def _build_base_index(self):
        if self._index_built:
            return
        pages = ["/", "/kuihuan/newmovie.html"]
        for c in self.CATEGORIES:
            pages.append("/kuihuamc%s/" % c["type_id"])
        for path in pages:
            try:
                text = self._get(path, referer=self.host + "/")
                self._add_items(self._parse_items(text))
            except Exception:
                continue
        self._index_built = True
        self._save_index()

    def _norm(self, text):
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r"[\s\-_:：·,，.。()（）\[\]【】《》/\\]+", "", text)
        return text

    def _match(self, key):
        q = self._norm(key)
        if not q:
            return []
        out = []
        for it in self._index.values():
            name = self._norm(it.get("vod_name", ""))
            actor = self._norm(it.get("vod_actor", ""))
            if q in name:
                score = 100 if name == q else (60 if name.startswith(q) else 10)
            elif actor and q in actor:
                score = 5
            else:
                continue
            out.append((score, it))
        out.sort(key=lambda x: (-x[0], -int(x[1]["vod_id"]) if x[1]["vod_id"].isdigit() else 0))
        return [it for _, it in out[:50]]

    def _deepen_for_query(self, key):
        tids = [c["type_id"] for c in self.CATEGORIES]
        for _ in range(len(tids)):
            tid = tids[self._deep_turn % len(tids)]
            self._deep_turn = (self._deep_turn + 1) % len(tids)
            if tid in self._deep_done:
                continue
            pg = self._deep_cursor.get(tid, 2)
            text = self._get("/kuihuamb/%s-0-0-0-0-%s.html" % (tid, pg), referer=self.host + "/")
            items = self._parse_items(text)
            if not items:
                self._deep_done.add(tid)
                continue
            self._add_items(items)
            self._deep_cursor[tid] = pg + 1
            if self._match(key):
                break
        self._save_index()

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            tid = c["type_id"]
            f = []
            if tid in self.FILTER_TYPES:
                opts = [{"n": "全部", "v": "0"}]
                for name in self.FILTER_TYPES[tid]:
                    opts.append({"n": name, "v": self.CLASS_MAP[tid][name]})
                f.append({"key": "class", "name": "类型", "value": opts})
            f.append({
                "key": "area", "name": "地区",
                "value": [{"n": "全部", "v": "0"}] + [{"n": k, "v": v} for k, v in self.AREA_MAP.items()],
            })
            f.append({
                "key": "year", "name": "年份",
                "value": [{"n": "全部", "v": "0"}] + [{"n": k, "v": v} for k, v in self.YEAR_MAP.items()],
            })
            f.append({
                "key": "lang", "name": "语言",
                "value": [{"n": "全部", "v": "0"}] + [{"n": k, "v": v} for k, v in self.LANG_MAP.items()],
            })
            filters[tid] = f
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            text = self._get("/", referer=self.host + "/")
            videos = self._parse_items(text)
            self._add_items(videos)
            result["list"] = videos
        except Exception:
            pass
        return result

    def _map(self, mapping, value):
        if value is None:
            return "0"
        value = str(value).strip()
        if not value or value == "全部":
            return "0"
        if value.isdigit():
            return value
        return mapping.get(value, "0")

    def _build_path(self, tid, extend, pg):
        extend = extend if isinstance(extend, dict) else {}
        c = self._map(self.CLASS_MAP.get(str(tid), {}), extend.get("class", extend.get("type", "0")))
        a = self._map(self.AREA_MAP, extend.get("area", "0"))
        y = self._map(self.YEAR_MAP, extend.get("year", "0"))
        l = self._map(self.LANG_MAP, extend.get("lang", "0"))
        return "/kuihuamb/%s-%s-%s-%s-%s-%s.html" % (tid, c, a, y, l, pg)

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        tid = str(tid)
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            text = self._get(self._build_path(tid, extend, page), referer=self.host + "/")
            videos = self._parse_items(text)
            self._add_items(videos)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            m = re.search(r'<a href="[^"]*-(\d+)\.html">下一页</a>', text)
            if m:
                result["pagecount"] = int(m.group(1))
            else:
                ms = re.findall(r'/kuihuamb/[^/]*-(\d+)\.html', text)
                if ms:
                    result["pagecount"] = max(result.get("pagecount",page), int(ms[-1]))
            self._save_index()
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}
        if not key:
            return result
        try:
            found = self._match(key)
            if not found:
                self._build_base_index()
                found = self._match(key)
            if not found:
                self._deepen_for_query(key)
                found = self._match(key)
            result["list"] = found
            result["limit"] = len(found)
            result["total"] = len(found)
        except Exception:
            pass
        return result

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid)
        m = re.search(r"(\d+)", vid)
        if m:
            vid = m.group(1)
        try:
            text = self._get(self.mhost + "/kuihuamv/%s/" % vid, referer=self.mhost + "/")
        except Exception:
            text = ""
        if not text or len(text) < 500:
            return result

        name = self._meta(text, "og:title")
        if not name:
            m = re.search(r"<h1>([^<]+)</h1>", text)
            if m:
                name = self._clean(m.group(1))
        pic = self._meta(text, "og:image")
        if not pic:
            m = re.search(r'<div class="Dimg">.*?<img[^>]+src="([^"]+)"', text, re.S)
            if m:
                pic = self._img(m.group(1))
        typ = self._meta(text, "og:video:class")
        director = self._meta(text, "og:video:director")
        actor = self._meta(text, "og:video:actor")
        area = self._meta(text, "og:video:area")
        date = self._meta(text, "og:video:date")
        year = ""
        ym = re.search(r"(\d{4})", date)
        if ym:
            year = ym.group(1)
        desc = self._meta(text, "og:description")
        if not desc:
            m = re.search(r'<div class="nrjj">.*?<span>剧情：</span>(.*?)</div>', text, re.S)
            if m:
                desc = self._clean(m.group(1))
        remark = ""
        m = re.search(r"<dd>\s*<span>状态：</span>([^<]*)</dd>", text)
        if m:
            remark = self._clean(m.group(1))

        eps = []
        seen_href = set()
        seen_label = set()
        for m in re.finditer(r'href="(/kuihuamv/%s/v[^"]+\.html)"[^>]*>([^<]+)</a>' % re.escape(vid), text):
            href = m.group(1)
            label = self._clean(m.group(2))
            if not label:
                label = "第%d集" % (len(eps) + 1)
            if label in seen_label or href in seen_href:
                continue
            if "立即播放" in label:
                continue
            seen_href.add(href)
            seen_label.add(label)
            eps.append((label, href))

        vod = {
            "vod_id": vid,
            "vod_name": name if name else vid,
            "vod_pic": pic if pic else self.DEFAULT_PIC,
            "vod_year": year,
            "vod_area": area,
            "vod_type": (typ.split(",")[0] if typ else ""),
            "vod_actor": actor,
            "vod_director": director,
            "vod_remarks": remark,
            "vod_content": self.WX_TEXT + ("\n\n" + desc if desc else ""),
        }

        if eps:
            vod["vod_play_from"] = "葵花线路"
            vod["vod_play_url"] = "#".join("%s$%s%s" % (label, self.mhost, href) for label, href in eps)
        else:
            m3u8 = self._extract_m3u8(text)
            if m3u8:
                vod["vod_play_from"] = "葵花线路"
                vod["vod_play_url"] = "播放$%s" % m3u8
            else:
                vod["vod_play_from"] = "葵花线路"
                vod["vod_play_url"] = "播放$%s/kuihuamv/%s/" % (self.mhost, vid)

        result["list"] = [vod]
        self._add_items([{
            "vod_id": vid,
            "vod_name": vod["vod_name"],
            "vod_pic": vod["vod_pic"],
            "vod_remarks": vod["vod_remarks"],
            "vod_actor": actor,
        }])
        return result

    def playerContent(self, flag, id, vipFlags):
        play_url = id or ""
        headers = {"User-Agent": self.MUA, "Referer": self.mhost + "/"}
        if not play_url:
            return {"parse": 1, "url": "", "header": json.dumps(headers)}
        if play_url.startswith("http") and ".m3u8" in play_url:
            return {"parse": 0, "url": play_url, "header": json.dumps(headers),
                    "playUrl": "", "subtitle": ""}
        if not play_url.startswith("http"):
            play_url = self.mhost + "/" + play_url.lstrip("/")
        text = self._get(play_url, referer=self.mhost + "/")
        real = self._extract_m3u8(text)
        if real:
            return {"parse": 0, "url": real, "header": json.dumps(headers),
                    "playUrl": "", "subtitle": ""}
        return {"parse": 1, "url": play_url, "header": json.dumps(headers),
                "playUrl": "", "subtitle": ""}

    def destroy(self):
        pass

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
