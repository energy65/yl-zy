# -*- coding: utf-8 -*-
"""
目标站: 网飞猫 (好看吗 hhkan)
站点地址(镜像, 自动故障切换):
    https://www.hhkan0.com  https://www.hhkan1.com
    https://www.hhkan2.com  https://www.hhkan3.com
    https://www.hhkan4.com
站点类型: 综合影视 (电影 / 连续剧 / 动漫 / 综艺纪录 / 短剧)
防护机制: cdndefend JS 挑战 (SHA1 暴力求解) -> 换取 cookie
模板结构: MacCMS 风格
    /channel/{tid}.html                频道页
    /show/{tid}-{类型}-{地区}-{语言}-{年份}-{排序}-{页码}.html   分类筛选列表
    /detail/{id}.html                  详情页
    /play/{id}-{源}-{集}.html          播放页 (内含 m3u8 直链)
    /search?k={关键词}&t={token}       搜索

功能 (写法参考 懂片帝.py):
    - homeContent: 一级分类 + 每类全部二级筛选 (类型/地区/语言/年份/排序)
    - 二级筛选数据优先从站点 /show 页动态抓取, 抓取失败回退内置数据
    - categoryContent / searchContent / detailContent / playerContent
    - 播放解析出 m3u8 直链, parse=0 交给 TVBox 直接播放
    - 影片简介处添加 微信公众号 "源力软件汇"
"""
import re
import sys
import json
import time
import ssl
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import html as html_mod

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


class Spider(BaseSpider):
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # 镜像域名 (按顺序尝试, 失败自动切换)
    DOMAINS = [
        "https://www.hhkan0.com",
        "https://www.hhkan1.com",
        "https://www.hhkan2.com",
        "https://www.hhkan3.com",
        "https://www.hhkan4.com",
    ]

    CC_KEY = "cdndefend_js_cookie"

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
        {"type_id": "2", "type_name": "连续剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺纪录"},
        {"type_id": "6", "type_name": "短剧"},
    ]

    # ==================== 内置筛选数据 (动态抓取失败时回退) ====================
    _FALLBACK_TYPES = {
        "1": ["剧情", "喜剧", "动作", "爱情", "恐怖", "惊悚", "犯罪", "科幻", "悬疑",
              "奇幻", "冒险", "战争", "历史", "古装", "家庭", "传记", "武侠", "歌舞",
              "短片", "动画", "儿童", "职场"],
        "2": ["剧情", "爱情", "喜剧", "犯罪", "悬疑", "古装", "动作", "家庭", "惊悚",
              "奇幻", "美剧", "科幻", "历史", "战争", "韩剧", "武侠", "言情", "恐怖",
              "冒险", "都市", "职场"],
        "3": ["动态漫画", "剧情", "动画", "喜剧", "冒险", "动作", "奇幻", "科幻", "儿童",
              "搞笑", "爱情", "家庭", "短片", "热血", "益智", "悬疑", "经典", "校园",
              "Anime", "运动", "亲子", "青春", "恋爱", "武侠", "惊悚"],
        "4": ["纪录", "真人秀", "记录", "脱口秀", "剧情", "历史", "喜剧", "传记", "相声",
              "节目", "歌舞", "冒险", "运动", "Season", "犯罪", "短片", "搞笑", "晚会"],
        "6": ["王爷太子", "霸道总裁", "屌丝逆袭", "赘婿系列", "重生系列", "穿越短剧",
              "美女总裁", "娇妻系列", "龙王系列", "都市言情", "逆袭", "甜宠", "虐恋",
              "穿越", "重生", "剧情", "科幻", "武侠", "爱情", "动作", "战争", "冒险", "其它"],
    }

    _FALLBACK_AREAS = {
        "1": ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "英国", "法国",
              "德国", "印度", "泰国", "丹麦", "瑞典", "巴西", "加拿大", "俄罗斯", "意大利",
              "比利时", "爱尔兰", "西班牙", "澳大利亚", "其他"],
        "2": ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "英国", "法国",
              "德国", "泰国", "印度", "其他"],
        "3": ["日本", "中国大陆", "中国台湾", "美国", "中国香港", "韩国", "其他"],
        "4": ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "其他"],
        "6": ["中国大陆", "其他"],
    }

    _FALLBACK_LANGS = {
        "4": ["国语", "粤语", "英语", "日语", "韩语", "其他"],
    }

    _YEAR_OPTIONS = [
        ("2026", "2026"), ("2025", "2025"), ("2024", "2024"), ("2023", "2023"),
        ("2022", "2022"), ("2021", "2021"), ("2020", "2020"),
        ("10年代", "2010_2019"), ("00年代", "2000_2009"), ("90年代", "1990_1999"),
        ("80年代", "1980_1989"), ("更早", "0_1979"),
    ]

    _SORT_OPTIONS = [("综合", "1"), ("最新", "2"), ("最热", "3"), ("评分", "4")]

    # 筛选标签 -> (extend key, 在 /show URL 中的位置, 默认值)
    _FILTER_MAP = {
        "类型": ("class", 1, ""),
        "地区": ("area", 2, ""),
        "语言": ("lang", 3, ""),
        "年份": ("year", 4, ""),
        "排序": ("sort", 5, "3"),
    }

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._cookie = ""
        self._token = ""
        self._token_ts = 0
        # 缓存
        self._filters_cache = {}          # tid -> filters list
        self._filters_cache_ts = {}
        self._cache_filters_ttl = 6 * 3600
        self._detect_host()

    def getName(self):
        return "网飞猫"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== 域名 / 挑战 ====================
    def _detect_host(self):
        """探测可用域名: 能通过挑战并返回正常首页的优先"""
        for domain in self.DOMAINS:
            try:
                if self._solve_cc(domain) is None:
                    continue
                html = self._get_with_cookie("/", host=domain)
                if html and "cdndefend" not in html[:600] and len(html) > 2000:
                    self.host = domain
                    return True
            except Exception:
                continue
        self.host = self.DOMAINS[0]
        return False

    def _switch_host(self):
        """切换到下一个镜像域名"""
        try:
            idx = self.DOMAINS.index(self.host)
        except ValueError:
            idx = 0
        self.host = self.DOMAINS[(idx + 1) % len(self.DOMAINS)]
        self._cookie = ""
        return self.host

    def _fetch_raw(self, url, cookie=None, referer=None, timeout=20):
        """底层 HTTP GET, 正确处理 HTTP 850 等非标准状态码"""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if cookie:
            headers["Cookie"] = cookie
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # HTTP 850: 响应体在异常对象中
            try:
                return e.read()
            except Exception:
                return b""
        except Exception:
            return b""

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _solve_cc(self, domain=None):
        """破解 cdndefend JS 挑战, 计算 cookie

        挑战串为 40 位 hex, 取首字符十六进制值 n1,
        暴力搜索 i 使 SHA1(challenge + str(i)) 的第 n1、n1+1 字节为 0xb0 0x0b
        """
        base = domain or self.host
        data = self._fetch_raw(base + "/")
        text = self._decode(data)
        if "cdndefend" not in text:
            # 无挑战
            if text:
                self._cookie = ""
                return True
            return None
        m = re.findall(r"'([0-9A-Fa-f]{40})'", text)
        if not m:
            return None
        c = m[0]
        n1 = int(c[0], 16)
        i = 0
        while i < 5000000:
            h = hashlib.sha1((c + str(i)).encode("utf-8")).digest()
            if h[n1] == 0xb0 and h[n1 + 1] == 0x0b:
                self._cookie = "%s=%s%d" % (self.CC_KEY, c, i)
                return True
            i += 1
        return None

    def _get_with_cookie(self, path, referer=None, host=None):
        """带 cookie 的 HTTP GET, 返回解码后的文本"""
        base = host or self.host
        url = path if path.startswith("http") else base + path
        if referer is None:
            referer = base + "/"
        data = self._fetch_raw(url, cookie=self._cookie, referer=referer)
        return self._decode(data)

    def _get(self, path, referer=None):
        """统一 GET, 自动处理挑战与域名故障切换"""
        for _ in range(len(self.DOMAINS) + 1):
            html = self._get_with_cookie(path, referer=referer)
            if html and "cdndefend" not in html[:600]:
                return html
            # 挑战失效, 重新求解; 仍失败则切换域名
            if self._solve_cc() is not None:
                html = self._get_with_cookie(path, referer=referer)
                if html and "cdndefend" not in html[:600]:
                    return html
            self._switch_host()
        return ""

    # ==================== 工具方法 ====================
    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _img_src(self, url):
        if not url:
            return ""
        if "logo_placeholder" in url or url.endswith(".ico"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    def _is_ad_title(self, s):
        """过滤广告/SEO 标题 (Unicode 数学字符伪装域名等)"""
        if not s:
            return True
        for ch in s:
            if 0x1D400 <= ord(ch) <= 0x1D7FF:
                return True
        low = s.lower()
        if "kekys" in low or "可可" in s:
            return True
        if "." in s and not re.search(r"[\u4e00-\u9fff]", s):
            return True
        return False

    # ==================== 筛选器 (动态抓取 + 回退) ====================
    def _fallback_filters(self, tid):
        """内置筛选数据 (站点不可用时的回退)"""
        f = []
        types = self._FALLBACK_TYPES.get(tid, [])
        f.append({
            "key": "class", "name": "类型",
            "value": [{"n": "全部", "v": ""}] + [{"n": t, "v": t} for t in types],
        })
        areas = self._FALLBACK_AREAS.get(tid, [])
        f.append({
            "key": "area", "name": "地区",
            "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in areas],
        })
        langs = self._FALLBACK_LANGS.get(tid, [])
        if langs:
            f.append({
                "key": "lang", "name": "语言",
                "value": [{"n": "全部", "v": ""}] + [{"n": l, "v": l} for l in langs],
            })
        f.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self._YEAR_OPTIONS],
        })
        sorts = self._SORT_OPTIONS if tid != "6" else self._SORT_OPTIONS[:3]
        f.append({
            "key": "sort", "name": "排序",
            "value": [{"n": n, "v": v} for n, v in sorts],
        })
        return f

    def _parse_filters_from_html(self, html, tid):
        """从 /show 页动态解析全部筛选 (类型/地区/语言/年份/排序)"""
        filters = []
        rows = re.findall(
            r'<div class="filter-row-side">\s*<strong>(.*?)</strong>\s*</div>\s*'
            r'<div class="filter-row-main">(.*?)</div>',
            html, re.S
        )
        for label, main in rows:
            label = self.clean(label).rstrip(":：")
            if label not in self._FILTER_MAP:
                continue
            key, pos, default = self._FILTER_MAP[label]
            values = []
            for href, text in re.findall(
                    r'<a href="([^"]+)"[^>]*class="filter-item[^"]*">([^<]*)</a>', main, re.S):
                name = self.clean(text)
                if not name:
                    continue
                seg = href.split("/show/", 1)[-1]
                if seg.endswith(".html"):
                    seg = seg[:-5]
                parts = seg.split("-")
                val = ""
                if pos < len(parts):
                    val = urllib.parse.unquote(parts[pos])
                values.append({"n": name, "v": val})
            if values:
                filters.append({"key": key, "name": label, "value": values})
        return filters

    def _get_filters(self, tid):
        """获取某分类的全部筛选器 (带缓存, 失败回退内置)"""
        tid = str(tid)
        now = time.time()
        if tid in self._filters_cache and (now - self._filters_cache_ts.get(tid, 0)) < self._cache_filters_ttl:
            return self._filters_cache[tid]

        filters = []
        try:
            html = self._get("/show/%s------.html" % tid)
            if html and "cdndefend" not in html[:600]:
                filters = self._parse_filters_from_html(html, tid)
        except Exception:
            filters = []

        if not filters:
            filters = self._fallback_filters(tid)
        self._filters_cache[tid] = filters
        self._filters_cache_ts[tid] = now
        return filters

    # ==================== 卡片解析 ====================
    def _parse_vitems(self, html):
        """解析频道/首页/分类页视频卡片"""
        items = []
        seen = set()
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="v-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(3)
            # 标题: 取非隐藏非广告的 v-item-title
            name = ""
            titles = [self.clean(t) for t in
                      re.findall(r'<div class="v-item-title"[^>]*>([^<]*)</div>', inner)]
            for t in titles:
                if t and not self._is_ad_title(t):
                    name = t
                    break
            if not name:
                valid = [t for t in titles if t and not self._is_ad_title(t)]
                if valid:
                    name = max(valid, key=len)
            if not name:
                continue
            seen.add(vid)
            # 封面
            pic = ""
            for im in re.findall(r'data-original="([^"]*)"', inner):
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            # 备注
            remark = ""
            rm = re.search(r'v-item-bottom[^>]*>\s*<span>\s*([^<]*?)\s*</span>', inner, re.S)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """解析搜索结果"""
        items = []
        seen = set()
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="search-result-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(3)
            tm = re.search(r'<div class="title">([^<]*)</div>', inner)
            if not tm:
                tm = re.search(r'alt="([^"]+)"', inner)
            if not tm:
                continue
            name = self.clean(tm.group(1))
            if not name or self._is_ad_title(name):
                continue
            seen.add(vid)
            pic = ""
            for im in re.findall(r'data-original="([^"]*)"', inner):
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            remark = ""
            tags_div = re.search(r'<div class="tags">(.*?)</div>', inner, re.S)
            if tags_div:
                spans = [self.clean(x) for x in
                         re.findall(r'<span>([^<]*)</span>', tags_div.group(1))]
                spans = [s for s in spans if s]
                if spans:
                    remark = " / ".join(spans[:3])
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

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
            html = self._get("/")
            if not html or "cdndefend" in html[:600]:
                return result
            result["list"] = self._parse_vitems(html)
        except Exception:
            pass
        return result

    # ==================== 分类 ====================
    def _apply_filters(self, params, extend):
        """从 extend 提取有效筛选值, 过滤 '全部'/空值"""
        if not isinstance(extend, dict):
            return
        for fk in ("class", "area", "lang", "year", "sort"):
            fv = extend.get(fk)
            if fv is None:
                continue
            fv = str(fv).strip()
            if fv and fv != "全部":
                params[fk] = fv

    def _build_show_path(self, tid, extend, pg):
        params = {"class": "", "area": "", "lang": "", "year": "", "sort": "3"}
        self._apply_filters(params, extend)
        return "/show/{0}-{1}-{2}-{3}-{4}-{5}-{6}.html".format(
            tid,
            urllib.parse.quote(self.clean(params["class"])),
            urllib.parse.quote(self.clean(params["area"])),
            urllib.parse.quote(self.clean(params["lang"])),
            urllib.parse.quote(self.clean(params["year"])),
            params["sort"],
            pg,
        )

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
            path = self._build_show_path(tid, extend, page)
            html = self._get(path)
            if not html or "cdndefend" in html[:600]:
                return result
            videos = self._parse_vitems(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            result["pagecount"] = self._parse_pagecount(html, page)
        except Exception:
            pass
        return result

    def _parse_pagecount(self, html, page):
        """根据'下一页'链接判断是否还有更多页"""
        m = re.search(r'<a href="([^"]+)"\s+class="page-item-next"', html)
        if not m:
            return page
        nums = re.findall(r'-(\d+)\.html', m.group(1))
        if nums:
            try:
                nxt = int(nums[-1])
                return max(page + 1, nxt)
            except Exception:
                pass
        return page + 1

    # ==================== 搜索 ====================
    def _fetch_token(self):
        """从首页获取搜索 token"""
        html = self._get("/")
        if not html:
            return ""
        token = ""
        m = re.search(r'name="t"[^>]*value="([^"]*)"', html)
        if m:
            token = self.clean(m.group(1))
        if not token:
            m2 = re.search(r'/search\?k=[^"\']*?[?&;]?t=([^"\'\s&]+)', html)
            if m2:
                token = urllib.parse.unquote(m2.group(1))
        self._token = token
        self._token_ts = time.time()
        return token

    def _get_token(self):
        if self._token and (time.time() - self._token_ts) < 300:
            return self._token
        return self._fetch_token()

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
            token = self._get_token()
            params = {"k": key}
            if page > 1:
                params["page"] = str(page)
            if token:
                params["t"] = token
            path = "/search?" + urllib.parse.urlencode(params)
            html = self._get(path, referer=self.host + "/")
            # token 失效则重取一次
            if not html or "/detail/" not in html:
                self._token = ""
                self._token_ts = 0
                token = self._get_token()
                if token:
                    params["t"] = token
                    path = "/search?" + urllib.parse.urlencode(params)
                    html = self._get(path, referer=self.host + "/")
            if not html or "cdndefend" in html[:600]:
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
            html = self._get("/detail/%s.html" % vid)
        except Exception:
            html = ""
        if not html or "cdndefend" in html[:600] or len(html) < 1000:
            return result

        vod = {"vod_id": vid}

        # 标题
        name = self._detail_name(html)
        vod["vod_name"] = name if name else vid

        # 封面
        vod["vod_pic"] = self._detail_pic(html)

        # 标签: 年份 / 地区 / 类型
        tags = [self.clean(t) for t in
                re.findall(r'<a[^>]*class="detail-tags-item"[^>]*>([^<]*)</a>', html)]
        tags = [t for t in tags if t]
        vod_year, vod_area, vod_class = "", "", ""
        known_areas = (
            "中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "英国", "法国",
            "德国", "意大利", "西班牙", "印度", "泰国", "丹麦", "瑞典", "巴西",
            "加拿大", "俄罗斯", "比利时", "爱尔兰", "澳大利亚", "台湾", "香港",
            "大陆", "内地", "其他",
        )
        for t in tags:
            if re.fullmatch(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            elif t.endswith("年代"):
                continue
            elif not vod_area and (t in known_areas or t.startswith("中国")):
                vod_area = t
            elif not vod_class and len(t) <= 8:
                vod_class = t
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_type"] = vod_class

        # 简介 + 推广文案 (置于最前)
        desc = self._detail_desc(html)
        vod["vod_content"] = self.WX_TEXT + ("\n\n" + desc if desc else "")

        # 详情信息行 (导演/演员/首映/备注)
        infos = {}
        for mm in re.finditer(
            r'<div class="detail-info-row">\s*<div class="detail-info-row-side">(.*?)</div>\s*'
            r'<div class="detail-info-row-main">(.*?)</div>', html, re.S
        ):
            label = self.clean(mm.group(1)).rstrip(":：")
            main = re.sub(r'<[^>]+>', ' ', mm.group(2))
            text = self.clean(main)
            if label and text:
                infos[label] = text
        vod["vod_director"] = infos.get("导演", "")
        vod["vod_actor"] = infos.get("演员", "") or infos.get("主演", "")
        if not vod["vod_area"]:
            vod["vod_area"] = infos.get("地区", "")
        if not vod["vod_year"]:
            ym = re.search(r"(\d{4})", infos.get("首映", "") or infos.get("上映", "") or "")
            if ym:
                vod["vod_year"] = ym.group(1)
        vod["vod_remarks"] = infos.get("备注", "") or infos.get("状态", "")

        # 播放源 + 选集
        from_arr, url_arr = self._detail_plays(html, vid)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            fallback = re.search(r'href="(/play/%s-\d+-\d+\.html)"' % re.escape(vid), html)
            if fallback:
                vod["vod_play_from"] = "网飞猫线路"
                vod["vod_play_url"] = "播放$%s" % (self.host + fallback.group(1))
            else:
                vod["vod_play_from"] = "网飞猫线路"
                vod["vod_play_url"] = "播放$%s/play/%s-1-1.html" % (self.host, vid)

        result["list"] = [vod]
        return result

    def _detail_name(self, html):
        m = re.search(r'<div class="detail-title">(.*?)</div>', html, re.S)
        if m:
            strongs = [self.clean(x) for x in
                       re.findall(r'<strong[^>]*>([^<]*)</strong>', m.group(1))]
            for s in strongs:
                if s and len(s) > 1 and not self._is_ad_title(s):
                    return s
            real = [s for s in strongs if s and len(s) > 1]
            if real:
                return max(real, key=len)
        tm = re.search(r'<title>([^<]*)</title>', html)
        if tm:
            t = self.clean(re.sub(r"[-_|].*$", "", self.clean(tm.group(1))))
            if t and not self._is_ad_title(t):
                return t
        return ""

    def _detail_pic(self, html):
        m = re.search(r'<div class="detail-pic">(.*?)</div>', html, re.S)
        if m:
            for im in re.findall(r'data-original="([^"]*)"', m.group(1)):
                s = self._img_src(im)
                if s:
                    return s
        for im in re.findall(r'data-original="([^"]*)"', html):
            s = self._img_src(im)
            if s:
                return s
        return self.DEFAULT_PIC

    def _detail_desc(self, html):
        m = re.search(r'<div class="detail-desc">(.*?)</div>\s*<div class="detail-line"', html, re.S)
        if not m:
            m = re.search(r'<div class="detail-desc">(.*?)</div>', html, re.S)
        if m:
            txt = re.sub(r"<br\s*/?>", "\n", m.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt:
                return txt
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            return self.clean(m.group(1))
        return ""

    def _detail_plays(self, html, vid):
        """解析线路标签与选集列表, 一一对应"""
        src_labels = [self.clean(x) for x in
                      re.findall(r'source-item-label[^>]*>([^<]*)</span>', html)]
        src_labels = [s for s in src_labels if s]

        blocks = re.findall(r'<div class="episode-list[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if not blocks:
            eps = re.findall(
                r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>(?:<span>)?([^<]*)',
                html)
            if eps:
                lines = []
                for ep_path, ep_name in eps:
                    ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                    lines.append("%s$%s" % (ep_name, self.host + ep_path))
                return ["网飞猫线路"], ["#".join(lines)]
            return [], []

        groups = []
        for b in blocks:
            eps = re.findall(
                r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*><span>([^<]*)</span>', b)
            groups.append(eps)

        from_arr, url_arr = [], []
        used = {}
        n = max(len(src_labels), len(groups))
        for i in range(n):
            label = src_labels[i] if i < len(src_labels) else "线路%d" % (i + 1)
            eps = groups[i] if i < len(groups) else []
            if not eps:
                continue
            # 处理重名线路
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_path))
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
            html = self._get(play_url, referer=self.host + "/")
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
            r'const\s+playSource\s*=\s*\{[^}]*?src:\s*"([^"]+)"',
            r'"src"\s*:\s*"(https?://[^"]+?)"',
            r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1',
            r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)',
            r'(["\'])(https?://[^"\']*?\.mp4[^"\']*)\1',
            r'(https?://[^\s"\']+?\.mp4[^\s"\']*)',
            r'var\s+now\s*=\s*["\']([^"\']+)["\']',
            r'var\s+url\s*=\s*["\']([^"\']+)["\']',
        ]
        for p in patterns:
            m = re.search(p, html, re.S)
            if not m:
                continue
            url = m.group(m.lastindex) if m.lastindex else m.group(1)
            url = url.replace("\\/", "/").strip()
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
