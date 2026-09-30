# -*- coding: utf-8 -*-
"""
好看网 / 好好看 (www.hhkan0.com ~ www.hhkan4.com) TVBox 爬虫

- 全站 5 个频道：电影、连续剧、动漫、综艺纪录、短剧，并按站点自带标签细分为数十个分类
- 自动破解 cdndefend JS 挑战，五个域名自动容灾切换
- 搜索走站点 /search 接口（带 t 令牌，令牌失效自动刷新）
- 播放页直出 m3u8，解析失败时回退嗅探
- 影片简介追加微信公众号“源力软件汇”
"""

import re
import ssl
import json
import time
import hashlib
import html as html_mod
import urllib.parse
import urllib.request
import urllib.error

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
        def searchContentPage(self, key, quick, page): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    DOMAINS = [
        "https://www.hhkan0.com",
        "https://www.hhkan1.com",
        "https://www.hhkan2.com",
        "https://www.hhkan3.com",
        "https://www.hhkan4.com",
    ]

    _CC_KEY = "cdndefend_js_cookie"

    # 影片简介推广位
    _WX_TEXT = "微信公众号“源力软件汇”，同步更新海量优质影视资源，观看体验更佳。"

    # ==================== 细分类型 ====================
    # 全部由站点 /show 页面筛选器逐项提取生成：显示名即 URL 取值，保证每个分类都有内容
    _MOVIE_TYPES = [
        ("剧情片", "剧情"), ("喜剧片", "喜剧"), ("动作片", "动作"), ("爱情片", "爱情"),
        ("恐怖片", "恐怖"), ("惊悚片", "惊悚"), ("犯罪片", "犯罪"), ("科幻片", "科幻"),
        ("悬疑片", "悬疑"), ("奇幻片", "奇幻"), ("冒险片", "冒险"), ("战争片", "战争"),
        ("历史片", "历史"), ("古装片", "古装"), ("家庭片", "家庭"), ("传记片", "传记"),
        ("武侠片", "武侠"), ("歌舞片", "歌舞"), ("短片", "短片"), ("动画片", "动画"),
        ("儿童片", "儿童"), ("职场片", "职场"),
    ]

    _TV_TYPES = [
        ("剧情剧", "剧情"), ("爱情剧", "爱情"), ("喜剧剧", "喜剧"), ("犯罪剧", "犯罪"),
        ("悬疑剧", "悬疑"), ("古装剧", "古装"), ("动作剧", "动作"), ("家庭剧", "家庭"),
        ("惊悚剧", "惊悚"), ("奇幻剧", "奇幻"), ("美剧", "美剧"), ("科幻剧", "科幻"),
        ("历史剧", "历史"), ("战争剧", "战争"), ("韩剧", "韩剧"), ("武侠剧", "武侠"),
        ("言情剧", "言情"), ("恐怖剧", "恐怖"), ("冒险剧", "冒险"), ("都市剧", "都市"),
        ("职场剧", "职场"),
    ]

    _ANIM_TYPES = [
        ("动态漫画", "动态漫画"), ("剧情", "剧情"), ("动画", "动画"), ("喜剧", "喜剧"),
        ("冒险", "冒险"), ("动作", "动作"), ("奇幻", "奇幻"), ("科幻", "科幻"),
        ("儿童", "儿童"), ("搞笑", "搞笑"), ("爱情", "爱情"), ("家庭", "家庭"),
        ("短片", "短片"), ("热血", "热血"), ("益智", "益智"), ("悬疑", "悬疑"),
        ("经典", "经典"), ("校园", "校园"), ("Anime", "Anime"), ("运动", "运动"),
        ("亲子", "亲子"), ("青春", "青春"), ("恋爱", "恋爱"), ("武侠", "武侠"),
        ("惊悚", "惊悚"),
    ]

    _ZOYI_TYPES = [
        ("纪录", "纪录"), ("真人秀", "真人秀"), ("记录", "记录"), ("脱口秀", "脱口秀"),
        ("剧情", "剧情"), ("历史", "历史"), ("喜剧", "喜剧"), ("传记", "传记"),
        ("相声", "相声"), ("节目", "节目"), ("歌舞", "歌舞"), ("冒险", "冒险"),
        ("运动", "运动"), ("Season", "Season"), ("犯罪", "犯罪"), ("短片", "短片"),
        ("搞笑", "搞笑"), ("晚会", "晚会"),
    ]

    _DUAN_TYPES = [
        ("王爷太子", "王爷太子"), ("霸道总裁", "霸道总裁"), ("屌丝逆袭", "屌丝逆袭"),
        ("赘婿系列", "赘婿系列"), ("重生系列", "重生系列"), ("穿越短剧", "穿越短剧"),
        ("美女总裁", "美女总裁"), ("娇妻系列", "娇妻系列"), ("龙王系列", "龙王系列"),
        ("都市言情", "都市言情"), ("逆袭", "逆袭"), ("甜宠", "甜宠"), ("虐恋", "虐恋"),
        ("穿越", "穿越"), ("重生", "重生"), ("剧情", "剧情"), ("科幻", "科幻"),
        ("武侠", "武侠"), ("爱情", "爱情"), ("动作", "动作"), ("战争", "战争"),
        ("冒险", "冒险"), ("其它", "其它"),
    ]

    # 频道元信息: (type_id, 频道名, tid, [细分类型])
    _CHANNELS = [
        ("1", "电影", "1", _MOVIE_TYPES),
        ("2", "连续剧", "2", _TV_TYPES),
        ("3", "动漫", "3", _ANIM_TYPES),
        ("4", "综艺纪录", "4", _ZOYI_TYPES),
        ("6", "短剧", "6", _DUAN_TYPES),
    ]

    CATEGORIES = []
    _SUBMAP = {}
    _filters = {}

    # 地区：站点显示名与 URL 取值不同（显示"大陆"，URL 传"中国大陆"）
    _AREA_PAIRS = {
        "1": [
            ("大陆", "中国大陆"), ("香港", "中国香港"), ("台湾", "中国台湾"), ("美国", "美国"),
            ("日本", "日本"), ("韩国", "韩国"), ("英国", "英国"), ("法国", "法国"),
            ("德国", "德国"), ("印度", "印度"), ("泰国", "泰国"), ("丹麦", "丹麦"),
            ("瑞典", "瑞典"), ("巴西", "巴西"), ("加拿大", "加拿大"), ("俄罗斯", "俄罗斯"),
            ("意大利", "意大利"), ("比利时", "比利时"), ("爱尔兰", "爱尔兰"),
            ("西班牙", "西班牙"), ("澳大利亚", "澳大利亚"), ("其他", "其他"),
        ],
        "2": [
            ("大陆", "中国大陆"), ("香港", "中国香港"), ("韩国", "韩国"), ("美国", "美国"),
            ("日本", "日本"), ("法国", "法国"), ("英国", "英国"), ("德国", "德国"),
            ("台湾", "中国台湾"), ("泰国", "泰国"), ("印度", "印度"), ("其他", "其他"),
        ],
        "3": [
            ("日本", "日本"), ("大陆", "中国大陆"), ("台湾", "中国台湾"), ("美国", "美国"),
            ("香港", "中国香港"), ("韩国", "韩国"), ("英国", "英国"), ("法国", "法国"),
            ("德国", "德国"), ("印度", "印度"), ("泰国", "泰国"), ("丹麦", "丹麦"),
            ("瑞典", "瑞典"), ("巴西", "巴西"), ("加拿大", "加拿大"), ("俄罗斯", "俄罗斯"),
            ("意大利", "意大利"), ("比利时", "比利时"), ("爱尔兰", "爱尔兰"),
            ("西班牙", "西班牙"), ("澳大利亚", "澳大利亚"), ("其他", "其他"),
        ],
        "4": [
            ("大陆", "中国大陆"), ("香港", "中国香港"), ("台湾", "中国台湾"), ("美国", "美国"),
            ("日本", "日本"), ("韩国", "韩国"), ("其他", "其他"),
        ],
    }

    _LANG = ["国语", "粤语", "英语", "日语", "韩语", "法语", "其他"]

    # tid -> 细分类型表
    _FILTER_SRC = {
        "1": _MOVIE_TYPES,
        "2": _TV_TYPES,
        "3": _ANIM_TYPES,
        "4": _ZOYI_TYPES,
        "6": _DUAN_TYPES,
    }

    @staticmethod
    def _year_values():
        y = time.localtime().tm_year
        vals = [{"n": "全部", "v": ""}]
        for i in range(y, y - 7, -1):
            vals.append({"n": str(i), "v": str(i)})
        vals += [
            {"n": "10年代", "v": "2010_2019"},
            {"n": "00年代", "v": "2000_2009"},
            {"n": "90年代", "v": "1990_1999"},
            {"n": "80年代", "v": "1980_1989"},
            {"n": "更早", "v": "0_1979"},
        ]
        return vals

    _SORT_ALL = [
        {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"},
        {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"},
    ]
    _SORT_DUAN = [
        {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"},
    ]

    @classmethod
    def _build(cls):
        """构建分类表 / 细分映射 / 筛选器"""
        for base_id, chan_name, tid, subs in cls._CHANNELS:
            type_list = cls._FILTER_SRC.get(tid) or []
            cls._filters[base_id] = cls._make_filter(tid, type_list, True)
            cls.CATEGORIES.append({"type_id": base_id, "type_name": chan_name})
            for i, (sub_name, sub_cls) in enumerate(subs):
                sid = "%s_s%02d" % (base_id, i)
                cls.CATEGORIES.append({"type_id": sid, "type_name": sub_name})
                cls._SUBMAP[sid] = (tid, sub_cls)
                cls._filters[sid] = cls._make_filter(tid, None, False)

    @classmethod
    def _make_filter(cls, tid, type_list, with_class):
        rows = []
        if with_class and type_list:
            rows.append({
                "key": "class", "name": "类型",
                "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in type_list],
            })
        areas = cls._AREA_PAIRS.get(tid)
        if areas:
            rows.append({
                "key": "area", "name": "地区",
                "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in areas],
            })
        if tid != "6":
            rows.append({
                "key": "lang", "name": "语言",
                "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": n} for n in cls._LANG],
            })
            rows.append({"key": "year", "name": "年份", "value": cls._year_values()})
        rows.append({
            "key": "sort", "name": "排序",
            "value": cls._SORT_DUAN if tid == "6" else cls._SORT_ALL,
        })
        return {"class": rows}

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._cookies = {}
        self._token = ""
        self._token_ts = 0
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        for domain in self.DOMAINS:
            self.host = domain
            if len(self._get("/")) > 3000:
                return
        self.host = self.DOMAINS[0]

    def getName(self):
        return "好好看"

    def _wechat_text(self):
        return self._WX_TEXT

    # ==================== HTTP ====================
    def _raw(self, url, cookie="", referer=None, timeout=12):
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
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=self._ctx) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            try:
                return e.read()
            except Exception:
                return b""
        except Exception:
            return b""

    @staticmethod
    def _decode(data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _solve_cc(self, domain):
        """访问站点首页求解 cdndefend 挑战，返回 cookie（无挑战返回空串，网络失败返回 None）"""
        return self._solve_html(self._decode(self._raw(domain + "/", "")), domain)

    def _solve_html(self, html, domain):
        """直接从挑战页 HTML 中求解 cookie，避免额外请求"""
        if not html:
            return None
        if "cdndefend" not in html[:4000]:
            self._cookies[domain] = ""
            return ""
        m = re.findall(r"'([0-9A-Fa-f]{40})'", html)
        if not m:
            return None
        c = m[0]
        n1 = int(c[0], 16)
        i = 0
        while i < 4000000:
            h = hashlib.sha1((c + str(i)).encode("utf-8")).digest()
            if h[n1] == 0xB0 and h[n1 + 1] == 0x0B:
                self._cookies[domain] = "%s=%s%d" % (self._CC_KEY, c, i)
                return self._cookies[domain]
            i += 1
        return None

    def _ensure_cookie(self, domain):
        """只在首次访问该域名时求解一次挑战，之后复用 cookie"""
        if domain not in self._cookies:
            self._solve_cc(domain)
        return self._cookies.get(domain, "")

    def _fetch_page(self, url, domain, cookie):
        return self._decode(self._raw(url, cookie, referer=domain + "/"))

    def _get(self, path, referer=None):
        """抓取页面，跨域名自动容灾；返回 html 文本"""
        if not path:
            return ""
        start = self.DOMAINS.index(self.host) if self.host in self.DOMAINS else 0
        order = self.DOMAINS[start:] + self.DOMAINS[:start]
        for domain in order:
            url = path if path.startswith("http") else domain + path
            for attempt in range(2):
                cookie = self._ensure_cookie(domain)
                html = self._fetch_page(url, domain, cookie)
                if html and "cdndefend" in html[:2000]:
                    # 挑战失效，用当前挑战页重新求解后再试一次
                    if attempt == 0 and self._solve_html(html, domain):
                        continue
                    break
                if len(html) < 800:
                    break
                self.host = domain
                return html
        return ""

    # ==================== 工具 ====================
    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"[ \t\r\f\v]+", " ", text).strip()

    @staticmethod
    def _is_ad(text):
        """广告/SEO 伪标题（含 Unicode 数学字符伪装域名、站点广告词等）"""
        if not text:
            return True
        for ch in text:
            if 0x1D400 <= ord(ch) <= 0x1D7FF:
                return True
        if "kekys" in text.lower() or "kekedy" in text.lower() or "可可" in text:
            return True
        if "." in text and not re.search(r"[\u4e00-\u9fff]", text):
            return True
        return False

    def _pick_title(self, pairs):
        """pairs: [(属性串, 标题HTML), ...]，挑出可见且非广告的真实标题"""
        vis, hidden = [], []
        for attrs, raw in pairs:
            txt = self.clean(raw)
            if not txt or self._is_ad(txt):
                continue
            if re.search(r"display\s*:\s*none", attrs or "", re.I):
                hidden.append(txt)
            else:
                vis.append(txt)
        pool = vis or hidden
        if not pool:
            return ""
        return min(pool, key=len)

    def _img(self, url):
        if not url:
            return ""
        if "logo_placeholder" in url or url.endswith(".ico"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _cover(self, inner):
        for im in re.findall(r'data-original="([^"]*)"', inner):
            s = self._img(im)
            if s:
                return s
        return ""

    # ==================== 列表解析 ====================
    def _parse_vitems(self, html):
        items = []
        seen = set()
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="v-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(3)
            pairs = re.findall(
                r'<div class="v-item-title"([^>]*)>(.*?)</div>', inner, re.S)
            name = self._pick_title(pairs)
            if not name:
                continue
            seen.add(vid)
            remark = ""
            rm = re.search(r'v-item-bottom[^>]*>\s*<span[^>]*>\s*(.*?)\s*</span>', inner, re.S)
            if rm:
                remark = self.clean(rm.group(1))
            if not remark:
                rs = re.search(r'v-item-top-right[^>]*>\s*<span[^>]*>\s*(.*?)\s*</span>', inner, re.S)
                if rs:
                    remark = self.clean(rs.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._cover(inner),
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        items = []
        seen = set()
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="search-result-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(3)
            tm = re.search(r'<div class="title">(.*?)</div>', inner, re.S)
            name = self.clean(tm.group(1)) if tm else ""
            if not name or self._is_ad(name):
                alt = re.search(r'<img[^>]*alt="([^"]+)"', inner)
                name = self.clean(alt.group(1)) if alt else ""
            if not name or self._is_ad(name):
                continue
            seen.add(vid)
            remark = ""
            head = re.search(r'search-result-item-header"[^>]*>\s*<div[^>]*>\s*(.*?)\s*</div>', inner, re.S)
            if head:
                remark = self.clean(head.group(1))
            tags_div = re.search(r'<div class="tags">(.*?)</div>', inner, re.S)
            if tags_div:
                spans = [self.clean(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", tags_div.group(1), re.S)]
                spans = [x for x in spans if x]
                if len(spans) >= 3:
                    remark = "%s/%s/%s" % (spans[0], spans[1], spans[2])
                elif spans:
                    remark = spans[0]
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._cover(inner),
                "vod_remarks": remark,
            })
        return items

    @staticmethod
    def _pagecount(html, pg):
        return str(int(pg) + 1) if "page-item-next" in html else str(pg)

    # ==================== 首页 ====================
    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": self._filters}

    def homeVideoContent(self):
        result = {"list": []}
        html = self._get("/")
        if html:
            result["list"] = self._parse_vitems(html)
        return result

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1

        tid_str = str(tid)
        cls = ""
        if tid_str in self._SUBMAP:
            real_tid, cls = self._SUBMAP[tid_str]
        elif tid_str in ("1", "2", "3", "4", "6"):
            real_tid = tid_str
        else:
            return result

        area = lang = year = ""
        sort = "3"
        if isinstance(extend, dict):
            cls = (extend.get("class") or extend.get("类型") or "") or cls
            area = extend.get("area") or extend.get("地区") or ""
            lang = extend.get("lang") or extend.get("语言") or ""
            year = extend.get("year") or extend.get("年份") or ""
            sort = (extend.get("sort") or extend.get("排序") or "") or sort

        def q(val):
            val = self.clean(val)
            return urllib.parse.quote(val) if val else ""

        path = "/show/%s-%s-%s-%s-%s-%s-%d.html" % (real_tid, q(cls), q(area), q(lang), q(year), sort, pg)
        html = self._get(path)
        if not html:
            return result

        videos = self._parse_vitems(html)
        result["list"] = videos
        result["page"] = str(pg)
        result["pagecount"] = self._pagecount(html, pg)
        result["total"] = str(len(videos))
        return result

    # ==================== 详情 ====================
    _KNOWN_AREAS = set(
        ["中国大陆", "中国香港", "中国台湾", "台湾", "香港", "大陆", "内地", "其他", "国产", "欧美"]
        + ["美国", "日本", "韩国", "英国", "法国", "德国", "印度", "泰国", "丹麦", "瑞典",
           "巴西", "加拿大", "俄罗斯", "意大利", "比利时", "爱尔兰", "西班牙", "澳大利亚",
           "捷克", "荷兰", "波兰", "挪威", "芬兰", "冰岛", "匈牙利", "奥地利", "瑞士",
           "葡萄牙", "希腊", "土耳其", "伊朗", "以色列", "墨西哥", "阿根廷", "智利",
           "哥伦比亚", "秘鲁", "南非", "埃及", "摩洛哥", "阿尔及利亚", "罗马尼亚",
           "保加利亚", "塞尔维亚", "克罗地亚", "斯洛伐克", "乌克兰", "白俄罗斯",
           "立陶宛", "拉脱维亚", "爱沙尼亚", "新西兰", "菲律宾", "越南", "马来西亚",
           "印尼", "新加坡", "蒙古", "哈萨克斯坦", "巴基斯坦", "孟加拉国", "尼泊尔",
           "黎巴嫩", "约旦", "沙特", "阿联酋", "卡塔尔", "伊拉克", "叙利亚"]
    )

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        vid = re.sub(r"[^\d]", "", str(vid))
        if not vid:
            return result
        html = self._get("/detail/%s.html" % vid)
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": vid}
        vod["vod_name"] = self._detail_name(html) or vid
        vod["vod_pic"] = self._detail_pic(html)

        year, area, vclass = "", "", ""
        tags = re.findall(
            r'<a[^>]*href="/show/[^"]*"[^>]*class="detail-tags-item"[^>]*>(.*?)</a>', html, re.S)
        for t in tags:
            t = self.clean(t)
            if not t or re.fullmatch(r"\d{4}年代?", t):
                continue
            if not year and re.match(r"^\d{4}", t):
                year = t[:4]
                continue
            if not area and t in self._KNOWN_AREAS:
                area = t
            elif not vclass and len(t) <= 8:
                vclass = t
        vod["vod_year"] = year
        vod["vod_area"] = area
        vod["vod_class"] = vclass

        desc = self._detail_desc(html)
        wechat = self._wechat_text()
        vod["vod_content"] = (desc + "\n\n" + wechat) if desc else wechat

        infos = {}
        for mm in re.finditer(
            r'<div class="detail-info-row">\s*<div class="detail-info-row-side">(.*?)</div>'
            r'\s*<div class="detail-info-row-main">(.*?)</div>', html, re.S):
            label = self.clean(mm.group(1)).rstrip(":：")
            if label:
                infos.setdefault(label, self.clean(mm.group(2)))

        vod["vod_director"] = infos.get("导演", "")
        vod["vod_actor"] = infos.get("演员", "") or infos.get("主演", "")
        if not area:
            vod["vod_area"] = infos.get("地区", "") or infos.get("制片国家/地区", "")
        if not year:
            ym = re.search(r"(\d{4})", infos.get("首映", "") or infos.get("上映", "") or "")
            if ym:
                vod["vod_year"] = ym.group(1)
        vod["vod_remarks"] = infos.get("备注", "")

        from_arr, url_arr = self._detail_plays(html)
        if from_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            m = re.search(r'href="(/play/%s-\d+-\d+\.html)"' % re.escape(vid), html)
            link = self.host + (m.group(1) if m else "/play/%s-1-1.html" % vid)
            vod["vod_play_from"] = "好看线路"
            vod["vod_play_url"] = "播放$%s" % link

        result["list"] = [vod]
        return result

    def _detail_name(self, html):
        m = re.search(r'<div class="detail-title">(.*?)</div>', html, re.S)
        if m:
            strongs = [self.clean(x) for x in re.findall(r"<strong[^>]*>(.*?)</strong>", m.group(1), re.S)]
            good = [s for s in strongs if s and not self._is_ad(s) and re.search(r"[\u4e00-\u9fff]", s)]
            if good:
                return max(good, key=len)
        t = re.search(r"<title>(.*?)</title>", html, re.S)
        if t:
            name = re.sub(r"[-_|].*$", "", self.clean(t.group(1))).strip()
            if name and not self._is_ad(name):
                return name
        return ""

    def _detail_pic(self, html):
        m = re.search(r'<div class="detail-pic">(.*?)</div>', html, re.S)
        if m:
            pic = self._cover(m.group(1))
            if pic:
                return pic
        og = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        if og:
            return self._img(og.group(1))
        return ""

    def _detail_desc(self, html):
        m = re.search(r'<div class="detail-desc">(.*?)</div>\s*<div class="detail-line"', html, re.S)
        if not m:
            m = re.search(r'<div class="detail-desc">(.*?)</div>', html, re.S)
        if m:
            txt = self.clean(m.group(1))
            if txt:
                return txt
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            return self.clean(m.group(1))
        return ""

    def _detail_plays(self, html):
        """解析播放线路与选集（线路标签与选集分组一一对应）"""
        labels = [self.clean(x) for x in re.findall(r'source-item-label[^>]*>(.*?)</span>', html, re.S)]
        labels = [x for x in labels if x]

        groups = []
        for b in re.findall(r'<div class="episode-list[^"]*"[^>]*>(.*?)</div>', html, re.S):
            eps = re.findall(
                r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>(?:<span[^>]*>)?(.*?)(?:</span>)?</a>',
                b, re.S)
            eps = [(p, self.clean(n)) for p, n in eps if p]
            if eps:
                groups.append(eps)

        if not groups:
            eps = re.findall(
                r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>(?:<span[^>]*>)?(.*?)(?:</span>)?</a>',
                html, re.S)
            eps = [(p, self.clean(n)) for p, n in eps if p]
            if not eps:
                return [], []
            lines = []
            for i, (path, name) in enumerate(eps):
                lines.append("%s$%s" % (name or ("播放%d" % (i + 1)), self.host + path))
            return ["好看线路"], ["#".join(lines)]

        from_arr, url_arr = [], []
        used = {}
        for i, eps in enumerate(groups):
            label = labels[i] if i < len(labels) else "线路%d" % (i + 1)
            if label in used:
                used[label] += 1
                label = "%s-%d" % (label, used[label])
            else:
                used[label] = 0
            lines = []
            for j, (path, name) in enumerate(eps):
                lines.append("%s$%s" % (name or ("第%d集" % (j + 1)), self.host + path))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 搜索 ====================
    def _fetch_token(self):
        html = self._get("/")
        if not html:
            return ""
        m = re.search(r'name="t"[^>]*value="([^"]*)"', html)
        token = self.clean(m.group(1)) if m else ""
        if not token:
            m2 = re.search(r"/search\?k=[^\"']*?[?&;]t=([^\"'&]+)", html)
            if m2:
                token = urllib.parse.unquote(self.clean(m2.group(1)))
        self._token = token
        self._token_ts = time.time()
        return token

    def _get_token(self):
        if self._token and (time.time() - self._token_ts) < 1800:
            return self._token
        return self._fetch_token()

    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        key = (key or "").strip()
        if not key:
            return result

        for attempt in range(2):
            token = self._get_token()
            if not token:
                return result
            url = "%s/search?k=%s&t=%s" % (self.host, urllib.parse.quote(key), urllib.parse.quote(token))
            if pg > 1:
                url += "&page=%d" % pg
            html = self._get(url, referer=self.host + "/")
            if html and 'class="search-result-item"' in html:
                videos = self._parse_search_items(html)
                result["list"] = videos
                result["page"] = str(pg)
                result["pagecount"] = self._pagecount(html, pg)
                result["total"] = str(len(videos))
                return result
            self._token = ""
            self._token_ts = 0
        return result

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = id
        if play_url.startswith("//"):
            play_url = "https:" + play_url
        elif not play_url.startswith("http"):
            play_url = self.host + "/" + play_url.lstrip("/")

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
            "Accept": "*/*",
        }

        real = ""
        html = self._get(play_url, referer=self.host + "/")
        if html:
            real = self._extract_media(html)

        if real:
            return {
                "url": real,
                "parse": "0",
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }
        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    @staticmethod
    def _extract_media(html):
        pats = [
            r'const\s+playSource\s*=\s*\{[^}]*?src:\s*["\']([^"\']+)["\']',
            r'(?:playSource|videoSource|source)\s*\.\s*src\s*=\s*["\']([^"\']+)["\']',
            r'(?:let|var|const)\s+(?:url|videoUrl|playUrl|src)\s*=\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            r'(?:let|var|const)\s+(?:url|videoUrl|playUrl|src)\s*=\s*["\'](//[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            r'["\']url["\']\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            r'(https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+?\.mp4[^\s"\'<>\\]*)',
        ]
        for pat in pats:
            m = re.search(pat, html)
            if m:
                u = html_mod.unescape(m.group(1)).strip()
                if u.startswith("//"):
                    u = "https:" + u
                if u and (".m3u8" in u or ".mp4" in u):
                    return u
        return ""

    # ==================== 兼容占位 ====================
    def isVideoFormat(self, url):
        return bool(re.search(r"\.m3u8|\.mp4", url or ""))

    def __jsEvalReturn(self):
        return {"proxy": None}

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def isVideoContent(self, ids):
        return False

    def manualVideoCheck(self):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None


Spider._build()
