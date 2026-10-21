# -*- coding: utf-8 -*-
"""
目标站: 水月影视
站点地址: https://www.atinyhiney.com
站点类型: 综合影视 (电影 / 电视剧 / 综艺 / 动漫 + 细分类型)
模板结构: MacCMS 风格
    /                                      首页
    /sy/{tid}.html                         频道页 (一级分类)
    /search.php?searchtype=5&tid={tid}     分类筛选/翻页列表
    /search.php?page={pg}&searchword={kw}&searchtype=1   关键词搜索
    /shuiyue/{id}.html                     详情页
    /play/{id}-{源}-{集}.html              播放页 (内含 m3u8 直链)

防护机制: nginx 反爬 (间歇性返回 503 + JS 刷新页), 需重试 + 携带会话 cookie
功能 (写法参考 网飞猫.py):
    - homeContent: 一级分类 + 每类全部二级筛选 (类型/年份/排序)
    - 二级筛选数据优先从站点分类页动态抓取, 抓取失败回退内置数据
    - categoryContent / searchContent / detailContent / playerContent
    - 播放解析出 m3u8 直链, parse=0 交给 TVBox 直接播放
    - 影片简介处添加 微信公众号 "源力软件汇"
"""
import re
import sys
import json
import time
import gzip
import ssl
import html as html_mod
import urllib.parse

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

# 优先使用 curl_cffi 伪装浏览器指纹绕过反爬, 缺失时回退 urllib
try:
    from curl_cffi import requests as _cc_requests
except Exception:
    _cc_requests = None


class Spider(BaseSpider):
    BASE_URL = "https://www.atinyhiney.com"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # 推广文案 (写入影片简介)
    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n"
        "QQ群：1054592152"
    )

    # ==================== 一级分类 (与站点导航一致) ====================
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
    ]

    # 频道页 ID -> 页面路径 (一级分类)
    _CAT_PAGE = {
        "1": "/sy/1.html",
        "2": "/sy/2.html",
        "3": "/sy/3.html",
        "4": "/sy/4.html",
    }

    # 内置二级类型 (动态抓取失败时回退)
    _FALLBACK_TYPES = {
        "1": ["动作片", "喜剧片", "爱情片", "科幻片", "恐怖片", "剧情片", "战争片", "纪录片"],
        "2": ["国产剧", "香港剧", "台湾剧", "欧美剧", "韩国剧", "日本剧", "泰国剧", "海外剧", "短剧"],
        "3": ["大陆综艺", "港台综艺", "日韩综艺", "欧美综艺"],
        "4": ["大陆动漫", "日本动漫", "欧美动漫", "海外动漫", "动画片"],
    }

    # 年份筛选 (更早 -> more)
    _YEAR_OPTIONS = [
        ("2026", "2026"), ("2025", "2025"), ("2024", "2024"), ("2023", "2023"),
        ("2022", "2022"), ("2021", "2021"), ("2020", "2020"), ("2019", "2019"),
        ("2018", "2018"), ("2017", "2017"), ("2016", "2016"), ("2015", "2015"),
        ("2014", "2014"), ("2013", "2013"), ("2012", "2012"), ("2010", "2010"),
        ("更早", "more"),
    ]

    _SORT_OPTIONS = [("时间", "time"), ("人气", "hit"), ("评分", "commend")]

    # 筛选标签 -> extend key
    _FILTER_MAP = {
        "类型": "subcat",
        "年份": "year",
        "排序": "order",
    }

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.BASE_URL
        self._session = None
        self._cookie = ""
        # 缓存
        self._filters_cache = {}          # tid -> filters list
        self._filters_cache_ts = {}
        self._cache_filters_ttl = 6 * 3600
        self._init_session()

    def _init_session(self):
        if _cc_requests is not None:
            try:
                self._session = _cc_requests.Session(impersonate="chrome124")
                self._session.get(self.host + "/", timeout=20)
                return
            except Exception:
                self._session = None

    def getName(self):
        return "水月影视"

    def isVideoFormat(self, url):
        return bool(re.search(r"\.m3u8|\.mp4", url or ""))

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== HTTP ====================
    def _decode(self, data):
        if not data:
            return ""
        if isinstance(data, str):
            return data
        for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _fetch_once(self, url, referer=None, timeout=20):
        """单次请求, 返回 (status, text)"""
        referer = referer or (self.host + "/")
        if self._session is not None:
            try:
                r = self._session.get(url, timeout=timeout, headers={"Referer": referer})
                raw = r.content
                if "gzip" in (r.headers.get("Content-Encoding") or ""):
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return r.status_code, self._decode(raw)
            except Exception:
                return 0, ""
        # urllib 回退
        try:
            import urllib.request
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": referer,
            }
            if self._cookie:
                headers["Cookie"] = self._cookie
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                if "gzip" in (resp.headers.get("Content-Encoding") or ""):
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return resp.getcode(), self._decode(raw)
        except Exception:
            return 0, ""

    def _is_challenge(self, status, text):
        """判断是否为反爬拦截页: 503 或 短小的"加载中"JS 刷新页"""
        if status != 200 or not text:
            return True
        if len(text) < 1000:
            return True
        # 反爬刷新页特征: 页头含"页面加载中,请稍候" 且为整页 (长度 < 2000)
        if "页面加载中" in text and len(text) < 2000:
            return True
        return False

    def getHtml(self, url, referer=None, tries=40):
        """带反爬重试的 GET: 遇 503 / JS 刷新页自动重试

        站点为 nginx 反爬, 会间歇性返回 503 或"加载中"JS 刷新页,
        每次请求命中概率不等, 需多次重试; 连续失败时重建会话。
        """
        for i in range(tries):
            status, text = self._fetch_once(url, referer=referer)
            if not self._is_challenge(status, text):
                return text
            # 连续多次失败后重建会话 (刷新 cookie/challenge)
            if i > 0 and i % 12 == 0:
                self._init_session()
            time.sleep(1.5)
        return ""

    def _clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _clean_intro(self, text):
        """清洗简介中的水印标记"""
        if not text:
            return ""
        text = re.sub(r"@[^@\s]{2,30}@", "", text)
        text = re.sub(r"&copy;[^&<]{0,30}", "", text)
        text = html_mod.unescape(text)
        text = re.sub(r"\.{2,}", "...", text)
        text = re.sub(r"[\u3000\s]+", " ", text).strip()
        return text

    def _img_src(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    # ==================== 卡片解析 ====================
    def _parse_vitems(self, html):
        """解析频道/首页/分类页视频卡片"""
        items = []
        seen = set()
        pat = (r'<a href="(/shuiyue/(\d+)\.html)"[^>]*class="module-item-pic"[^>]*>(.*?)</a>'
               r'\s*</div>\s*<div class="module-item-titlebox">\s*'
               r'<a href="/shuiyue/\2\.html"[^>]*class="module-item-title"[^>]*>([^<]*)</a>'
               r'\s*</div>\s*<div class="module-item-text">([^<]*)</div>')
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            inner = m.group(3)
            name = self._clean(m.group(4))
            if not name:
                continue
            pic = ""
            im = re.search(r'data-src="([^"]*)"', inner)
            if not im:
                im = re.search(r'data-original="([^"]*)"', inner)
            if im:
                pic = self._img_src(im.group(1))
            remark = self._clean(m.group(5))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """解析搜索结果 (module-search-item)"""
        items = []
        seen = set()
        for m in re.finditer(r'<div class="module-search-item">(.*?)</div>\s*</div>\s*</div>',
                             html, re.S):
            block = m.group(1)
            vm = re.search(r'href="/shuiyue/(\d+)\.html"[^>]*title="([^"]*)"', block)
            if not vm:
                vm = re.search(r'<h3><a href="/shuiyue/(\d+)\.html"[^>]*title="([^"]*)"', block)
            if not vm:
                continue
            vid = vm.group(1)
            name = self._clean(vm.group(2))
            if not name or vid in seen:
                continue
            seen.add(vid)
            pic = ""
            im = re.search(r'data-src="([^"]*)"', block)
            if im:
                pic = self._img_src(im.group(1))
            remark = ""
            rm = re.search(r'class="video-serial"[^>]*>([^<]*)</a>', block)
            if rm:
                remark = self._clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    # ==================== 筛选器 (动态抓取 + 回退) ====================
    def _fallback_filters(self, tid):
        """内置筛选数据 (站点不可用时的回退)"""
        f = []
        types = self._FALLBACK_TYPES.get(str(tid), [])
        f.append({
            "key": "subcat", "name": "类型",
            "value": [{"n": "全部", "v": ""}] + [{"n": t, "v": t} for t in types],
        })
        f.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self._YEAR_OPTIONS],
        })
        f.append({
            "key": "order", "name": "排序",
            "value": [{"n": n, "v": v} for n, v in self._SORT_OPTIONS],
        })
        return f

    def _parse_filters_from_html(self, html, tid):
        """从分类页动态解析二级筛选 (类型/年份/排序)"""
        filters = []
        seen_keys = set()
        # 类型: <a class="library-item" href="/sy/N.html">名称</a>
        type_values = []
        tm = re.search(r'<a class="library-item library-item-first[^"]*">按类型</a>\s*'
                       r'<div class="library-list">(.*?)</div>', html, re.S)
        if tm:
            for href, name in re.findall(
                    r'<a class="library-item[^"]*" href="(/sy/\d+\.html)"[^>]*>([^<]*)</a>',
                    tm.group(1)):
                name = self._clean(name)
                if name:
                    type_values.append({"n": name, "v": href})
        if type_values:
            filters.append({"key": "subcat", "name": "类型",
                            "value": [{"n": "全部", "v": ""}] + type_values})
            seen_keys.add("subcat")

        # 年份: 含 year= 的 library-item 链接 (该区块标题为"按时间")
        year_values = []
        seen_years = set()
        for href, name in re.findall(
                r'<a class="library-item[^"]*" href="([^"]*search\.php[^"]*year=[^"]*)"[^>]*title="([^"]*)"',
                html):
            mv = re.search(r'[?&]year=([^&"]+)', href)
            if not mv:
                continue
            val = mv.group(1)
            if val in seen_years:
                continue
            seen_years.add(val)
            name = self._clean(name)
            year_values.append({"n": name if name else val, "v": val})
        if year_values:
            filters.append({"key": "year", "name": "年份",
                            "value": [{"n": "全部", "v": ""}] + year_values})
            seen_keys.add("year")

        # 排序: search.php?...&order=time|hit|commend
        order_values = []
        seen_orders = set()
        for href in re.findall(r'href="([^"]*search\.php[^"]*order=[^"]*)"', html):
            mv = re.search(r'[?&]order=([^&"]+)', href)
            if not mv:
                continue
            val = mv.group(1)
            if val in seen_orders:
                continue
            seen_orders.add(val)
            name = {"time": "时间", "hit": "人气", "commend": "评分"}.get(val, val)
            order_values.append({"n": name, "v": val})
        if order_values:
            filters.append({"key": "order", "name": "排序", "value": order_values})
            seen_keys.add("order")

        return filters

    def _get_filters(self, tid):
        """获取某分类的全部筛选器 (带缓存, 失败回退内置)"""
        tid = str(tid)
        now = time.time()
        if tid in self._filters_cache and (now - self._filters_cache_ts.get(tid, 0)) < self._cache_filters_ttl:
            return self._filters_cache[tid]

        filters = []
        try:
            path = self._CAT_PAGE.get(tid)
            if path:
                html = self.getHtml(self.host + path)
                if html:
                    filters = self._parse_filters_from_html(html, tid)
        except Exception:
            filters = []

        if not filters:
            filters = self._fallback_filters(tid)
        self._filters_cache[tid] = filters
        self._filters_cache_ts[tid] = now
        return filters

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """首页: 一级分类 + 各分类全部二级筛选 + 推荐视频"""
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            filters[c["type_id"]] = self._get_filters(c["type_id"])

        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self.getHtml(self.host + "/")
            if not html:
                return result
            result["list"] = self._parse_vitems(html)
        except Exception:
            pass
        return result

    # ==================== 分类 ====================
    def _build_list_url(self, tid, extend, pg):
        """构造分类列表 URL

        - 无筛选: /sy/{tid}.html
        - 类型子分类: /sy/N.html 直接子分类频道页
        - 其他筛选(年份/排序): /search.php?searchtype=5&tid={tid}&...&page={pg}
        """
        tid = str(tid)
        ext = extend if isinstance(extend, dict) else {}

        subcat = str(ext.get("subcat", "") or "").strip()
        year = str(ext.get("year", "") or "").strip()
        order = str(ext.get("order", "") or "").strip()

        # 纯子分类 (无其他筛选): 直接用子分类频道页
        if subcat.startswith("/sy/") and not year and not order and str(pg) == "1":
            return self.host + subcat

        params = {"searchtype": "5", "tid": tid}
        # 子分类: 若是 /sy/N.html 形态, 提取其 tid
        if subcat:
            m = re.search(r"/sy/(\d+)\.html", subcat)
            if m:
                params["tid"] = m.group(1)
        if year and year != "全部":
            params["year"] = year
        if order and order != "全部":
            params["order"] = order
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page > 1:
            params["page"] = str(page)
        return self.host + "/search.php?" + urllib.parse.urlencode(params)

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        tid = str(tid)
        # 兼容部分 TVBox 把筛选放在 filter 参数中的情况
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}

        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            url = self._build_list_url(tid, extend, page)
            html = self.getHtml(url)
            if not html:
                return result
            videos = self._parse_vitems(html)
            if not videos:
                # 部分页面使用搜索卡片结构
                videos = self._parse_search_items(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            result["pagecount"] = self._parse_pagecount(html, page)
        except Exception:
            pass
        return result

    def _parse_pagecount(self, html, page):
        """根据分页信息判断总页数"""
        # 尾页链接: ?page=857&...
        m = re.search(r'href="[^"]*[?&]page=(\d+)[^"]*"[^>]*class="page-number page-next"[^>]*title="尾页"',
                      html)
        if m:
            try:
                return max(page, int(m.group(1)))
            except Exception:
                pass
        # 下一页
        nums = re.findall(r'[?&]page=(\d+)', html)
        if nums:
            try:
                nxt = max(int(n) for n in nums)
                return max(page, nxt)
            except Exception:
                pass
        return page

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        if not key:
            return result
        try:
            params = {"page": str(page), "searchword": key, "searchtype": "1"}
            url = self.host + "/search.php?" + urllib.parse.urlencode(params)
            html = self.getHtml(url, referer=self.host + "/")
            if not html:
                return result
            videos = self._parse_search_items(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            result["pagecount"] = self._parse_pagecount(html, page)
        except Exception:
            pass
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid)
        try:
            html = self.getHtml(self.host + "/shuiyue/%s.html" % vid)
        except Exception:
            html = ""
        if not html:
            return result

        vod = {"vod_id": vid}

        # 标题
        vod["vod_name"] = self._detail_name(html, vid)

        # 封面
        vod["vod_pic"] = self._detail_pic(html)

        # meta 信息
        area = self._meta(html, "og:video:area")
        vclass = self._meta(html, "og:video:class")
        director = self._meta(html, "og:video:director")
        actor = self._meta(html, "og:video:actor")
        update = self._meta(html, "og:video:update_date")

        # 年份 (从简介/更新日期提取)
        desc = self._detail_desc(html)
        year = ""
        ym = re.search(r"于(\d{4})年", desc)
        if ym:
            year = ym.group(1)
        if not year and update:
            ym2 = re.search(r"(\d{4})", update)
            if ym2:
                year = ym2.group(1)

        vod["vod_year"] = year
        vod["vod_area"] = area
        vod["vod_type"] = vclass
        vod["vod_director"] = director
        vod["vod_actor"] = actor
        vod["vod_remarks"] = ""
        vod["vod_class"] = vclass
        vod["type_name"] = vclass

        # 简介 + 推广文案 (置于最前)
        vod["vod_content"] = self.WX_TEXT + ("\n\n" + desc if desc else "")

        # 播放源 + 选集
        from_arr, url_arr = self._detail_plays(html, vid)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            vod["vod_play_from"] = "水月影视"
            vod["vod_play_url"] = "播放$" + self.host + "/play/%s-0-0.html" % vid

        result["list"] = [vod]
        return result

    def _meta(self, html, prop):
        m = re.search(r'<meta property="%s" content="([^"]*)"' % re.escape(prop), html)
        return self._clean(m.group(1)) if m else ""

    def _detail_name(self, html, vid):
        m = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        if m:
            return self._clean(m.group(1))
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            t = self._clean(re.sub(r"<[^>]*>", "", m.group(1)))
            if t:
                return t
        m = re.search(r"<title>(.*?)</title>", html)
        if m:
            return self._clean(re.sub(r"[-_|].*$", "", self._clean(m.group(1))))
        return vid

    def _detail_pic(self, html):
        m = re.search(r'<meta property="og:image" content="([^"]*)"', html)
        if m:
            return self._img_src(m.group(1))
        m = re.search(r'<img[^>]*data-src="([^"]*)"', html)
        if m:
            return self._img_src(m.group(1))
        return self.DEFAULT_PIC

    def _detail_desc(self, html):
        m = re.search(r'<meta name="description"[^>]*content="([^"]*)"', html)
        if m:
            desc = html_mod.unescape(m.group(1))
            # 去掉前缀 "《名》剧情介绍：" / "XX剧情介绍："
            desc = re.sub(r"^[^：:]{0,40}剧情介绍[：:]\s*", "", desc)
            return self._clean_intro(desc)
        return ""

    def _detail_plays(self, html, vid):
        """解析线路标签与选集列表"""
        # 线路标签
        src_labels = [self._clean(x) for x in
                      re.findall(r'data-dropdown-value="([^"]*)"', html)]
        src_labels = [s for s in src_labels if s]

        # 各线路的选集块 (sort-item 与 scroll-content 出现两份, 取 sort-item)
        blocks = re.findall(r'<div class="sort-item">(.*?)</div>', html, re.S)
        if not blocks:
            blocks = re.findall(r'<div class="module-blocklist scroll-box[^"]*">\s*'
                                r'<div class="scroll-content">(.*?)</div>', html, re.S)

        groups = []
        for b in blocks:
            eps = re.findall(r'<a title="([^"]*)" href="(/play/[^"]+)"', b)
            if not eps:
                eps = re.findall(r'<a[^>]*href="(/play/[^"]+)"[^>]*title="([^"]*)"', b)
                eps = [(t, h) for h, t in eps]
            groups.append(eps)

        if not groups:
            # 兜底: 全文抓 /play/ 链接去重
            eps = re.findall(r'<a[^>]*href="(/play/[^"]+)"[^>]*title="([^"]*)"', html)
            if eps:
                seen = set()
                lines = []
                for h, name in eps:
                    if h in seen:
                        continue
                    seen.add(h)
                    name = self._clean(name) or "播放"
                    lines.append("%s$%s" % (name, self.host + h))
                if lines:
                    return ["水月影视"], ["#".join(lines)]
            return [], []

        from_arr, url_arr = [], []
        used = {}
        n = max(len(src_labels), len(groups))
        for i in range(n):
            label = src_labels[i] if i < len(src_labels) else "线路%d" % (i + 1)
            eps = groups[i] if i < len(groups) else []
            if not eps:
                continue
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for ep_name, ep_href in eps:
                ep_name = self._clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_href))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = id or ""
        if not play_url:
            return {"parse": 1, "url": "", "header": ""}
        if not play_url.startswith("http"):
            play_url = self.host + "/" + play_url.lstrip("/")

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
        }

        html = ""
        try:
            html = self.getHtml(play_url, referer=self.host + "/")
        except Exception:
            html = ""

        real = self._extract_m3u8(html)
        if real:
            return {
                "parse": 0,
                "url": real,
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }

        # 解析失败: 交给 TVBox 嗅探播放页
        return {
            "parse": 1,
            "url": play_url,
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    def _extract_m3u8(self, html):
        """从播放页提取真实 m3u8/mp4 地址"""
        if not html:
            return ""
        patterns = [
            r'var\s+now\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'var\s+now\s*=\s*["\']([^"\']+)["\']',
            r'["\'](https?://[^"\']*?\.m3u8[^"\']*)["\']',
            r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)',
            r'["\'](https?://[^"\']*?\.mp4[^"\']*)["\']',
            r'(https?://[^\s"\']+?\.mp4[^\s"\']*)',
        ]
        for p in patterns:
            m = re.search(p, html, re.S)
            if not m:
                continue
            url = m.group(1).replace("\\/", "/").strip()
            if url.startswith("//"):
                url = "https:" + url
            if ".m3u8" in url or ".mp4" in url:
                return url
        return ""

    def __jsEvalReturn(self):
        return {"proxy": None}

    def destroy(self):
        pass

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
