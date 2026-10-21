#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标站: Auete影视 (aeete.com)
站点地址: https://www.aeete.com

站点结构:
    /Movie/index.html                        电影
    /Tv/index.html                           电视剧
    /Zy/index.html                           综艺
    /Dm/index.html                           动漫
    /aigcyingshi/index.html                  AIGC影视
    /qita/index.html                         其他
    /{Section}/{sub}/index.html              子分类列表
    /{Section}/{sub}/index{page}.html        列表分页
    /{Section}/{sub}/{slug}/                 详情页
    /{Section}/{sub}/{slug}/play-{src}-{ep}.html  播放页 (base64 直链 m3u8)
    /xml/rss.xml                             最新 1000 条 (搜索兜底索引)
    /auete4so.php?searchword=xxx             站内搜索 (首次弹窗输入验证码, 之后免验证)

功能:
    - homeContent: 全部一级分类 + 每个分类的全部二级类型/地区/年份筛选
    - categoryContent: 支持子分类、地区、年份筛选, 地区/年份按详情页元数据过滤
    - detailContent: 完整影片信息 + 全部线路 + 全部选集
    - playerContent: 解码 base64 得到 m3u8 直链, parse=0 交给 TVBox 直接播放
    - searchContent: 站内搜索优先, 首次弹窗输入验证码(之后免验证), 取消或无界面时用最新资源索引兜底
    - 影片简介处添加 微信公众号 "源力软件汇"
"""
import re
import json
import ssl
import gzip
import zlib
import time
import base64
import http.cookiejar
import urllib.parse
import urllib.request
import urllib.error
import html as html_mod

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
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

        def detailContent(self, ids):
            return {}

        def searchContent(self, key, quick, pg="1"):
            return {}

        def playerContent(self, flag, id, vipFlags):
            return {}


class Spider(BaseSpider):
    BASE_URL = "https://www.aeete.com"
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇"
    )

    # ==================== 一级分类 + 全部二级类型 (与站点导航一致) ====================
    SECTIONS = {
        "1": {
            "name": "电影", "path": "Movie",
            "subs": [
                ("xjp", "喜剧片"), ("dzp", "动作片"), ("aqp", "爱情片"),
                ("khp", "科幻片"), ("kbp", "恐怖片"), ("jsp", "惊悚片"),
                ("zzp", "战争片"), ("jqp", "剧情片"),
            ],
        },
        "2": {
            "name": "电视剧", "path": "Tv",
            "subs": [
                ("neidi", "国产"), ("tvbgj", "港剧"), ("taiju", "台剧"),
                ("oumei", "美剧"), ("hanju", "韩剧"), ("riju", "日剧"),
                ("yataiju", "泰剧"), ("wangju", "网剧"), ("yingju", "英剧"),
                ("waiju", "外剧"),
            ],
        },
        "3": {
            "name": "综艺", "path": "Zy",
            "subs": [("guozong", "国综"), ("hanzong", "韩综"), ("meizong", "美综")],
        },
        "4": {
            "name": "动漫", "path": "Dm",
            "subs": [
                ("donghua", "动画"), ("riman", "日漫"), ("guoman", "国漫"),
                ("meiman", "美漫"),
            ],
        },
        "5": {
            "name": "AIGC影视", "path": "aigcyingshi",
            "subs": [
                ("aimanju", "AI漫剧"), ("aigcju", "AIGC剧"), ("aigcdianying", "AIGC电影"),
            ],
        },
        "6": {
            "name": "其他", "path": "qita",
            "subs": [
                ("Jlp", "记录片"), ("Jdp", "经典片"), ("Jdj", "经典剧"),
                ("wlp", "网大电影"), ("laodianying", "国产老电影"),
            ],
        },
    }

    # ==================== 地区 / 年份 筛选 ====================
    AREAS = [
        "中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国",
        "英国", "法国", "德国", "意大利", "西班牙", "印度", "泰国",
        "俄罗斯", "加拿大", "澳大利亚", "其他",
    ]

    YEARS = [
        ("2026", "2026"), ("2025", "2025"), ("2024", "2024"), ("2023", "2023"),
        ("2022", "2022"), ("2021", "2021"), ("2020", "2020"), ("2019", "2019"),
        ("2018", "2018"), ("2017", "2017"), ("2016", "2016"), ("2015", "2015"),
        ("2014", "2014"), ("2013", "2013"), ("2012", "2012"), ("2011", "2011"),
        ("2010", "2010"), ("00年代", "2000-2009"), ("90年代", "1990-1999"),
        ("80年代", "1980-1989"), ("更早", "更早"),
    ]

    _KNOWN_AREA_WORDS = (
        "大陆", "中国", "香港", "台湾", "美国", "日本", "韩国", "英国",
        "法国", "德国", "意大利", "西班牙", "印度", "泰国", "俄罗斯",
        "加拿大", "澳大利亚", "其它", "其他",
    )

    # 搜索验证会话跨实例保留, 避免重复弹验证码
    _shared_jar = None
    _shared_opener = None

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self._meta_cache = {}
        self._index_cache = []
        self._index_ts = 0
        self._index_ttl = 1800
        self._search_blocked = False
        self._last_search_ts = 0
        self._search_pagecount = 1

        if getattr(self, "_handler", None) is None:
            try:
                from android.os import Handler, Looper
                self._handler = Handler(Looper.getMainLooper())
            except Exception:
                self._handler = None

        if Spider._shared_jar is None:
            Spider._shared_jar = http.cookiejar.CookieJar()
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                Spider._shared_opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(Spider._shared_jar),
                    urllib.request.HTTPSHandler(context=ctx),
                )
            except Exception:
                Spider._shared_opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(Spider._shared_jar)
                )
        self._cookie_jar = Spider._shared_jar
        self._opener = Spider._shared_opener

    def getName(self):
        return "Aeete影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def destroy(self):
        pass

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None

    def __jsEvalReturn(self):
        return {"proxy": None}

    # ==================== 网络请求 ====================
    def _request(self, url, data=None, referer=None, timeout=15, raw=False):
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": referer or self.BASE_URL + "/",
        }
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with self._opener.open(req, timeout=timeout) as resp:
                content = resp.read()
                encoding = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in encoding:
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        pass
                elif "deflate" in encoding:
                    try:
                        content = zlib.decompress(content)
                    except Exception:
                        try:
                            content = zlib.decompress(content, -zlib.MAX_WBITS)
                        except Exception:
                            pass
            if raw:
                return content
            for enc in ("utf-8", "gb18030", "gbk"):
                try:
                    return content.decode(enc)
                except Exception:
                    continue
            return content.decode("utf-8", errors="replace")
        except Exception:
            return b"" if raw else ""

    def getHtml(self, url, referer=None, timeout=15):
        return self._request(url, referer=referer, timeout=timeout)

    def postHtml(self, url, data, referer=None, timeout=15):
        return self._request(url, data=data, referer=referer, timeout=timeout)

    def getBytes(self, url, referer=None, timeout=15):
        return self._request(url, referer=referer, timeout=timeout, raw=True)

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = text.replace("\u3000", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _abs_url(self, url):
        if not url:
            return ""
        url = self.clean(url)
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.BASE_URL + url
        return self.BASE_URL + "/" + url

    def _b64(self, text):
        if not text:
            return ""
        try:
            text = str(text).strip()
            text += "=" * (-len(text) % 4)
            return base64.b64decode(text).decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    # ==================== 首页分类 + 筛选 ====================
    def _filters(self, tid):
        sec = self.SECTIONS.get(str(tid))
        if not sec:
            return []
        subs = [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in sec["subs"]]
        areas = [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.AREAS]
        years = [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self.YEARS]
        return [
            {"key": "class", "name": "类型", "value": subs},
            {"key": "area", "name": "地区", "value": areas},
            {"key": "year", "name": "年份", "value": years},
        ]

    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": sec["name"]}
                   for tid, sec in self.SECTIONS.items()]
        filters = {tid: self._filters(tid) for tid in self.SECTIONS}
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/")
        if not html:
            return result
        result["list"] = self._parse_items(html)[:40]
        return result

    # ==================== 列表解析 ====================
    def _parse_items(self, html):
        items = []
        seen = set()
        if not html:
            return items
        for m in re.finditer(r'<li[^>]*data-href="([^"]+)"[^>]*>(.*?)</li>', html, re.S):
            href = m.group(1).strip()
            block = m.group(2)
            if not re.match(r"^/(Movie|Tv|Zy|Dm|aigcyingshi|qita)/", href):
                continue
            vid = href.strip("/")
            parts = vid.split("/")
            if len(parts) < 3 or parts[-1].lower().startswith("index"):
                continue
            if vid in seen:
                continue

            name = ""
            nm = re.search(r'<h2[^>]*>\s*<a[^>]*title="([^"]+)"', block)
            if nm:
                name = self.clean(nm.group(1))
            if not name:
                nm = re.search(r'<h2[^>]*>\s*<a[^>]*>([^<]+)</a>', block)
                if nm:
                    name = self.clean(nm.group(1))
            if not name:
                nm = re.search(r'<img[^>]*alt="([^"]+)"', block)
                if nm:
                    name = self.clean(nm.group(1))
            if not name:
                continue

            pic = ""
            pm = re.search(r'data-original="([^"]+)"', block)
            if not pm:
                pm = re.search(r'data-src="([^"]+)"', block)
            if not pm:
                pm = re.search(r'<img[^>]*src="([^"]+)"', block)
            if pm:
                pic = self._abs_url(pm.group(1))
            if pic and ("loading.gif" in pic or "logo" in pic):
                pic = ""

            remarks = ""
            rm = re.search(r'<span[^>]*class="hdtag"[^>]*>([^<]*)</span>', block)
            if rm:
                remarks = self.clean(rm.group(1))

            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic or self.DEFAULT_PIC,
                "vod_remarks": remarks,
            })
        return items

    def _parse_pagecount(self, html, page):
        m = re.search(r'href="([^"]+)"\s+class="page-link"[^>]*>\s*尾页', html)
        if m:
            nums = re.findall(r"index(\d+)\.html", m.group(1))
            if nums:
                try:
                    return max(page, int(nums[-1]))
                except Exception:
                    pass
        m = re.search(r'class="page-item[^"]*"><a href="([^"]+)" class="page-link">\s*下一页', html)
        if m and "index" in m.group(1):
            return page + 1
        return page

    # ==================== 详情元数据 (地区/年份过滤用) ====================
    def _detail_meta(self, vid):
        if vid in self._meta_cache:
            return self._meta_cache[vid]
        html = self.getHtml(self.BASE_URL + "/" + vid.strip("/") + "/", timeout=4)
        if not html:
            return "", ""
        area, year = "", ""
        if html:
            m = re.search(r'badge-time[^>]*>.*?(\d{4})', html, re.S)
            if m:
                year = m.group(1)
            m = re.search(r'badge-area[^>]*>(?:.*?</i>)?\s*([^<]+)</span>', html, re.S)
            if m:
                area = self.clean(m.group(1))
            if not year:
                m = re.search(r"◎\s*上映年份\s*[：:]\s*</span>\s*<b[^>]*>(.*?)</b>", html, re.S)
                if m:
                    ym = re.search(r"(\d{4})", m.group(1))
                    if ym:
                        year = ym.group(1)
            if not area:
                m = re.search(r"◎\s*影片地区\s*[：:]\s*</span>\s*<b[^>]*>([^<]+)</b>", html)
                if m:
                    area = self.clean(m.group(1))
        self._meta_cache[vid] = (area, year)
        return area, year

    def _area_ok(self, area, want):
        if not want:
            return True
        a = area or ""
        if want == "其他":
            return not any(w in a for w in self._KNOWN_AREA_WORDS)
        if want == "中国大陆":
            return ("大陆" in a) or ("内地" in a) or a in ("中国", "中国大陆")
        if want == "中国香港":
            return "香港" in a
        if want == "中国台湾":
            return "台湾" in a
        return (want in a) or (a in want)

    def _year_ok(self, year, want):
        if not want:
            return True
        if not year:
            return False
        try:
            y = int(year)
        except Exception:
            return False
        if want == "更早":
            return y < 1980
        if "-" in want:
            seg = want.split("-")
            if len(seg) == 2 and seg[0].isdigit() and seg[1].isdigit():
                return int(seg[0]) <= y <= int(seg[1])
        return str(y) == str(want)

    def _filter_items(self, items, area, year, deadline=None, limit=20):
        if not items or (not area and not year):
            return items

        def match(item):
            a, y = self._detail_meta(item["vod_id"])
            return self._area_ok(a, area) and self._year_ok(y, year)

        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            pool = ThreadPoolExecutor(max_workers=10)
            futures = {}
            for idx, item in enumerate(items):
                futures[pool.submit(match, item)] = (idx, item)
            hits = []
            try:
                for fut in as_completed(futures):
                    if deadline and time.time() > deadline:
                        break
                    idx, item = futures[fut]
                    try:
                        if fut.result():
                            hits.append((idx, item))
                    except Exception:
                        pass
                    if len(hits) >= limit:
                        break
            finally:
                for fut in futures:
                    if not fut.done():
                        fut.cancel()
                pool.shutdown(wait=False)
            hits.sort(key=lambda x: x[0])
            return [item for _, item in hits]
        except Exception:
            return [it for it in items if match(it)]

    # ==================== 分类 ====================
    def _cat_url(self, sec, sub, page):
        if sub:
            prefix = "/%s/%s/index" % (sec["path"], sub)
        else:
            prefix = "/%s/index" % sec["path"]
        if page <= 1:
            return self.BASE_URL + prefix + ".html"
        return self.BASE_URL + prefix + str(page) + ".html"

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        tid = str(tid)
        sec = self.SECTIONS.get(tid)
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        if not sec:
            return result

        ext = extend if isinstance(extend, dict) else {}
        if not ext and isinstance(filter, dict):
            ext = filter

        sub = str(ext.get("class") or "").strip()
        if sub in ("全部", "0", "None"):
            sub = ""
        if sub and sub not in [v for v, _ in sec["subs"]]:
            sub = ""

        area = str(ext.get("area") or "").strip()
        if area in ("全部", "0", "None"):
            area = ""
        year = str(ext.get("year") or "").strip()
        if year in ("全部", "0", "None"):
            year = ""

        if not area and not year:
            html = self.getHtml(self._cat_url(sec, sub, page))
            items = self._parse_items(html)
            result["list"] = items
            result["limit"] = len(items)
            result["total"] = len(items)
            result["pagecount"] = self._parse_pagecount(html, page)
            return result

        from concurrent.futures import ThreadPoolExecutor

        scan = 5
        start = (page - 1) * scan + 1
        end = start + scan - 1
        urls = [self._cat_url(sec, sub, p) for p in range(start, end + 1)]
        try:
            with ThreadPoolExecutor(max_workers=scan) as pool:
                pages = list(pool.map(self.getHtml, urls))
        except Exception:
            pages = [self.getHtml(u) for u in urls]

        site_pagecount = 0
        for i, h in enumerate(pages):
            if h:
                site_pagecount = max(site_pagecount, self._parse_pagecount(h, start + i))

        items = []
        seen = set()
        for h in pages:
            for it in self._parse_items(h):
                if it["vod_id"] not in seen:
                    seen.add(it["vod_id"])
                    items.append(it)

        items = self._filter_items(items, area, year, deadline=time.time() + 6, limit=20)

        result["list"] = items
        result["limit"] = len(items)
        result["total"] = len(items)
        if site_pagecount:
            result["pagecount"] = max(page, (site_pagecount + scan - 1) // scan)
        else:
            result["pagecount"] = page + (1 if items else 0)
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip().strip("/")
        if not vid:
            return result

        html = self.getHtml(self.BASE_URL + "/" + vid + "/")
        if not html:
            return result

        vod = {"vod_id": vid}

        name = ""
        m = re.search(r'<h1[^>]*class="detail-title"[^>]*>(.*?)</h1>', html, re.S)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1))
            name = self.clean(name).strip("《》")
        if not name:
            m = re.search(r'property=["\']og:title["\'][^>]*content="([^"]+)"', html)
            if m:
                name = self.clean(m.group(1))
        vod["vod_name"] = name

        pic = ""
        m = re.search(r'property=["\']og:image["\'][^>]*content="([^"]+)"', html)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'<div class="detail-poster">.*?<img[^>]*src="([^"]+)"', html, re.S)
            if m:
                pic = m.group(1)
        vod["vod_pic"] = self._abs_url(pic) or self.DEFAULT_PIC

        badges = {}
        for cls, key in (("badge-time", "year"), ("badge-area", "area"),
                         ("badge-type", "class"), ("badge-jqtype", "jq")):
            m = re.search(r'class="[^"]*' + cls + r'[^"]*"[^>]*>(.*?)</span>', html, re.S)
            if m:
                txt = re.sub(r"<[^>]+>", "", m.group(1))
                badges[key] = self.clean(txt)

        infos = {}
        for m in re.finditer(r'<span class="detail-label">◎\s*([^<]+?)\s*[：:]?\s*</span>\s*<b[^>]*>(.*?)</b>',
                             html, re.S):
            label = self.clean(m.group(1)).rstrip("：:")
            value = self.clean(re.sub(r"<[^>]+>", "", m.group(2)))
            if label and value:
                infos[label] = value

        vod["vod_year"] = badges.get("year", "")
        vod["vod_area"] = infos.get("影片地区", "") or badges.get("area", "")
        if not vod["vod_year"]:
            ym = re.search(r"(\d{4})", infos.get("上映年份", ""))
            if ym:
                vod["vod_year"] = ym.group(1)
        vod["vod_class"] = badges.get("class", "") or infos.get("影片分类", "")
        vod["vod_lang"] = infos.get("影片语言", "")
        vod["vod_actor"] = infos.get("影片主演", "")
        vod["vod_director"] = infos.get("影片导演", "")
        vod["vod_remarks"] = infos.get("影片备注", "") or badges.get("jq", "")

        desc = ""
        m = re.search(r'<p[^>]*class="detail-des"[^>]*>(.*?)</p>', html, re.S)
        if not m:
            m = re.search(r'<div[^>]*class="detail-des"[^>]*>(.*?)</div>', html, re.S)
        if m:
            txt = re.sub(r"<br\s*/?>", "\n", m.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = txt.replace("{self:share}", "").replace("&emsp;", " ")
            desc = self.clean(txt)
        if not desc:
            m = re.search(r'property=["\']og:description["\'][^>]*content="([^"]+)"', html)
            if m:
                desc = self.clean(m.group(1))
        vod["vod_content"] = self.WX_TEXT + ("\n" + desc if desc else "")

        from_arr, url_arr = self._parse_plays(html)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            m = re.search(r'property=["\']og:video["\'][^>]*content="([^"]+)"', html)
            if m:
                vod["vod_play_from"] = "云播"
                vod["vod_play_url"] = "播放$" + self._abs_url(m.group(1))
            else:
                vod["vod_play_from"] = "云播"
                vod["vod_play_url"] = ""

        parts = vid.split("/")
        sec_path = parts[0] if parts else ""
        type_id = "1"
        for tid, sec in self.SECTIONS.items():
            if sec["path"] == sec_path:
                type_id = tid
                break
        vod["type_id"] = type_id
        vod["type_name"] = self.SECTIONS.get(type_id, {}).get("name", "影视")

        result["list"] = [vod]
        return result

    def _parse_plays(self, html):
        from_arr = []
        url_arr = []
        used = {}

        chunks = re.split(r'<div class="card mb-3 play-card"', html)[1:]
        for idx, chunk in enumerate(chunks):
            body = chunk.split("</ul>", 1)[0]
            m = re.search(r"<b>(.*?)</b>", body, re.S)
            label = ""
            if m:
                raw = self.clean(re.sub(r"<[^>]+>", "", m.group(1)))
                if "』" in raw:
                    label = raw.split("』", 1)[1].strip()
                else:
                    label = raw.strip("『』").strip()
            if not label or label.startswith("『"):
                label = "线路%d" % (idx + 1)
            if len(label) > 30:
                label = "线路%d" % (idx + 1)
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1

            eps = []
            seen = set()
            for em in re.finditer(r'<a[^>]*title="([^"]*)"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
                href = em.group(2)
                if "play-" not in href:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                ep_name = self.clean(em.group(1)) or self.clean(em.group(3)) or "播放"
                eps.append((ep_name, href))
            if not eps:
                continue
            parts = []
            for ep_name, href in eps:
                parts.append("%s$%s" % (ep_name, self._abs_url(href)))
            from_arr.append(label)
            url_arr.append("#".join(parts))

        return from_arr, url_arr

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = id or ""
        if not play_url:
            return {"parse": 1, "url": "", "header": "", "playUrl": "", "subtitle": ""}
        play_url = self._abs_url(play_url)

        headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
        }

        html = self.getHtml(play_url)
        real = ""
        if html:
            for pat in (
                r'var\s+now\s*=\s*base64decode\("([^"]+)"\)',
                r'now\s*=\s*base64decode\(\'([^\']+)\'\)',
            ):
                m = re.search(pat, html)
                if m:
                    real = self._b64(m.group(1))
                    if real:
                        break
            if not real:
                m = re.search(r'var\s+now\s*=\s*["\']([^"\']+)["\']', html)
                if m:
                    real = self.clean(m.group(1))

        if real:
            if real.startswith("//"):
                real = "https:" + real
            elif real.startswith("/"):
                real = self.BASE_URL + real
            real = real.replace("\\/", "/")
            return {
                "parse": 0,
                "url": real,
                "header": json.dumps(headers),
                "playUrl": "",
                "subtitle": "",
            }

        return {
            "parse": 1,
            "url": play_url,
            "header": json.dumps(headers),
            "playUrl": "",
            "subtitle": "",
        }

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        try:
            return self._do_search(key, pg)
        except Exception:
            return {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

    def _do_search(self, key, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        key = (key or "").strip()
        if not key:
            return result

        items = None
        if not self._search_blocked:
            items = self._official_search(key, page)
        if items is None:
            items = self._local_search(key, page)
            result["pagecount"] = max(1, (len(items) + 19) // 20) if items else 1
            result["list"] = items[(page - 1) * 20: page * 20]
            result["total"] = result["limit"] = len(items)
            return result

        result["list"] = items
        result["pagecount"] = max(page, self._search_pagecount)
        result["total"] = result["limit"] = len(items)
        return result

    def _official_search(self, key, page):
        url = self.BASE_URL + "/auete4so.php?searchword=" + urllib.parse.quote(key)
        if page > 1:
            url += "&page=" + str(page)
        html = self.getHtml(url, timeout=12)

        if html and "搜索限制为10秒一次" in html:
            wait = 10 - (time.time() - self._last_search_ts)
            if 0 < wait <= 10:
                time.sleep(wait + 0.5)
                html = self.getHtml(url, timeout=12)

        if html and ("系统安全验证" in html or ("vdimgck" in html and len(html) < 6000)):
            html = self._solve_captcha(key, page)

        if not html:
            return None
        if "系统安全验证" in html or "验证码不正确" in html:
            return None
        if "搜索限制为10秒一次" in html:
            return None

        m = re.search(r"共\s*(\d+)\s*页", html)
        if m:
            try:
                self._search_pagecount = max(1, int(m.group(1)))
            except Exception:
                self._search_pagecount = page
        else:
            self._search_pagecount = page

        self._last_search_ts = time.time()
        items = self._parse_items(html)
        if not items:
            items = self._parse_legacy_search(html)
        return items

    # ==================== 验证码 (弹窗输入, 参考 跳验证枫叶.py) ====================
    def _activity(self):
        try:
            from java.lang import Class
            activity_thread_class = Class.forName("android.app.ActivityThread")
            activity_thread = activity_thread_class.getMethod(
                "currentActivityThread", None).invoke(None, None)
            activities_field = activity_thread_class.getDeclaredField("mActivities")
            activities_field.setAccessible(True)
            activities = activities_field.get(activity_thread)
            if activities is None:
                return None
            values = activities.values()
            try:
                records = values.toArray()
            except Exception:
                records = values.getClass().getMethod("toArray").invoke(values)
            for record in records:
                try:
                    record_class = record.getClass()
                    paused_field = record_class.getDeclaredField("paused")
                    paused_field.setAccessible(True)
                    if not paused_field.getBoolean(record):
                        activity_field = record_class.getDeclaredField("activity")
                        activity_field.setAccessible(True)
                        return activity_field.get(record)
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _ui_post(self, func):
        if getattr(self, "_handler", None) is None:
            return False
        try:
            from java import dynamic_proxy
            from java.lang import Runnable
        except Exception:
            return False
        if not hasattr(self, "_runnable_class"):
            class _Runnable(dynamic_proxy(Runnable)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def run(self):
                    self.fn()

            self._runnable_class = _Runnable
        try:
            self._handler.post(self._runnable_class(func))
            return True
        except Exception:
            return False

    def _ask_captcha(self, image_bytes):
        if not image_bytes:
            return ""
        try:
            from java import jclass, dynamic_proxy
        except Exception:
            return ""

        try:
            from android.os import Looper
            if Looper.myLooper() == Looper.getMainLooper():
                return ""
        except Exception:
            pass

        activity = self._activity()
        if activity is None:
            return ""

        try:
            ArrayBlockingQueue = jclass("java.util.concurrent.ArrayBlockingQueue")
            TimeUnit = jclass("java.util.concurrent.TimeUnit")
        except Exception:
            return ""

        box = ArrayBlockingQueue(1)
        answered = [False]

        def build():
            try:
                BitmapFactory = jclass("android.graphics.BitmapFactory")
                ImageView = jclass("android.widget.ImageView")
                EditText = jclass("android.widget.EditText")
                LinearLayout = jclass("android.widget.LinearLayout")
                AlertDialog = jclass("android.app.AlertDialog")
                OnClickListener = jclass("android.content.DialogInterface$OnClickListener")
                OnDismissListener = jclass("android.content.DialogInterface$OnDismissListener")
                Gravity = jclass("android.view.Gravity")
                ViewGroup = jclass("android.view.ViewGroup")

                bitmap = BitmapFactory.decodeByteArray(image_bytes, 0, len(image_bytes))
                image_view = ImageView(activity)
                image_view.setImageBitmap(bitmap)
                image_view.setAdjustViewBounds(True)
                image_view.setScaleType(ImageView.ScaleType.FIT_CENTER)
                image_params = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                )
                image_params.bottomMargin = 20

                input_box = EditText(activity)
                input_box.setHint("请输入验证码，例如 4+6 填 10")
                input_box.setGravity(Gravity.CENTER)

                layout = LinearLayout(activity)
                layout.setOrientation(LinearLayout.VERTICAL)
                layout.setPadding(40, 20, 40, 20)
                layout.addView(image_view, image_params)
                layout.addView(input_box)

                class PositiveListener(dynamic_proxy(OnClickListener)):
                    def onClick(self, dialog, which):
                        answered[0] = True
                        code = str(input_box.getText().toString()).strip()
                        dialog.dismiss()
                        box.offer(code)

                class NegativeListener(dynamic_proxy(OnClickListener)):
                    def onClick(self, dialog, which):
                        answered[0] = True
                        dialog.dismiss()
                        box.offer("")

                class DismissListener(dynamic_proxy(OnDismissListener)):
                    def onDismiss(self, dialog):
                        if not answered[0]:
                            answered[0] = True
                            box.offer("")

                dialog = AlertDialog.Builder(activity) \
                    .setTitle("Aeete搜索验证") \
                    .setView(layout) \
                    .setPositiveButton("确定", PositiveListener()) \
                    .setNegativeButton("取消", NegativeListener()) \
                    .create()
                dialog.setOnDismissListener(DismissListener())
                dialog.show()
            except Exception:
                if not answered[0]:
                    answered[0] = True
                    box.offer("")

        if not self._ui_post(build):
            return ""
        try:
            result = box.poll(120, TimeUnit.SECONDS)
            return str(result).strip() if result else ""
        except Exception:
            return ""

    def _solve_captcha(self, key, page):
        if getattr(self, "_handler", None) is None:
            return ""
        for _ in range(2):
            image = self.getBytes(
                self.BASE_URL + "/include/vdimgck.php?get=" + str(int(time.time() * 1000)),
                referer=self.BASE_URL + "/auete4so.php?searchword=" + urllib.parse.quote(key),
                timeout=15,
            )
            if not image:
                return ""
            code = self._ask_captcha(image)
            if not code:
                return ""

            action = (self.BASE_URL + "/auete4so.php?scheckAC=check&page=" + str(page) +
                      "&searchtype=&order=&tid=&area=&year=&letter=&yuyan=&state=&money=&ver=&jq=")
            html = self.postHtml(
                action,
                {"validate": code, "searchword": key},
                referer=self.BASE_URL + "/auete4so.php?searchword=" + urllib.parse.quote(key),
                timeout=15,
            )
            if not html:
                return ""
            if "验证码不正确" in html:
                continue
            if "搜索限制为10秒一次" in html:
                return ""
            self._last_search_ts = time.time()
            return html
        return ""

    def _parse_legacy_search(self, html):
        items = []
        seen = set()
        for m in re.finditer(r'<a[^>]*href="(/(?:Movie|Tv|Zy|Dm|aigcyingshi|qita)/[^"]+/)"[^>]*>(.*?)</a>',
                             html, re.S):
            href = m.group(1)
            vid = href.strip("/")
            if vid in seen or len(vid.split("/")) < 3:
                continue
            block = m.group(0)
            name = ""
            tm = re.search(r'title="([^"]+)"', block)
            if tm:
                name = self.clean(tm.group(1))
            if not name:
                name = self.clean(re.sub(r"<[^>]+>", "", m.group(2)))
            if not name or len(name) < 1:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self.DEFAULT_PIC,
                "vod_remarks": "",
            })
        return items

    def _local_index(self):
        now = time.time()
        if self._index_cache and (now - self._index_ts) < self._index_ttl:
            return self._index_cache

        items = []
        seen = set()

        rss = self.getHtml(self.BASE_URL + "/xml/rss.xml", timeout=25)
        if rss:
            for m in re.finditer(r"<item>(.*?)</item>", rss, re.S):
                block = m.group(1)
                tm = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
                lm = re.search(r"<link>(.*?)</link>", block, re.S)
                if not tm or not lm:
                    continue
                link = self.clean(lm.group(1))
                vid = link.replace(self.BASE_URL, "").strip("/")
                if not re.match(r"^(Movie|Tv|Zy|Dm|aigcyingshi|qita)/", vid):
                    continue
                if vid in seen:
                    continue
                name = self.clean(tm.group(1))
                if not name:
                    continue
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.DEFAULT_PIC,
                    "vod_remarks": "",
                })

        home = self.getHtml(self.BASE_URL + "/")
        if home:
            for it in self._parse_items(home):
                if it["vod_id"] not in seen:
                    seen.add(it["vod_id"])
                    items.append(it)

        self._index_cache = items
        self._index_ts = now
        return items

    def _local_search(self, key, page):
        kw = key.lower()
        hits = []
        for it in self._local_index():
            if kw in it["vod_name"].lower():
                hits.append(it)
        if not hits and len(key) > 1:
            for it in self._local_index():
                if key in it["vod_name"]:
                    hits.append(it)
        return hits
