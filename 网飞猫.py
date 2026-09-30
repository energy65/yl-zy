# -*- coding: utf-8 -*-

import re
import json
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.error
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
        def searchContentPage(self, key, quick, page): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    DOMAINS = [
        "https://www.ncat30.com",
        "https://www.ncat31.com",
        "https://www.ncat20.com",
        "https://www.ncat29.com",
        "https://www.ncat28.com",
        "https://www.ncat27.com",
        "https://www.ncat26.com",
        "https://www.ncat25.com",
        "https://www.ncat24.com",
        "https://www.ncat23.com",
        "https://www.ncat22.com",
        "https://www.ncat21.com",
    ]

    _CC_KEY = "cdndefend_js_cookie"

    # ==================== 分类配置 ====================
    # 顶层分类与网飞猫导航一致：电影、连续剧、动漫、综艺纪录、短剧
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "5", "type_name": "动作片"},
        {"type_id": "6", "type_name": "喜剧片"},
        {"type_id": "7", "type_name": "爱情片"},
        {"type_id": "8", "type_name": "科幻片"},
        {"type_id": "9", "type_name": "恐怖片"},
        {"type_id": "10", "type_name": "剧情片"},
        {"type_id": "11", "type_name": "战争片"},
        {"type_id": "12", "type_name": "奇幻片"},
        {"type_id": "13", "type_name": "武侠片"},
        {"type_id": "14", "type_name": "悬疑片"},
        {"type_id": "15", "type_name": "惊悚片"},
        {"type_id": "16", "type_name": "犯罪片"},
        {"type_id": "17", "type_name": "历史片"},
        {"type_id": "18", "type_name": "文艺片"},
        {"type_id": "19", "type_name": "冒险片"},
        {"type_id": "20", "type_name": "动画片"},
        {"type_id": "21", "type_name": "纪录片"},
        {"type_id": "22", "type_name": "传记片"},
        {"type_id": "23", "type_name": "歌舞片"},
        {"type_id": "24", "type_name": "短片"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "25", "type_name": "古装剧"},
        {"type_id": "26", "type_name": "都市剧"},
        {"type_id": "27", "type_name": "历史剧"},
        {"type_id": "28", "type_name": "谍战剧"},
        {"type_id": "29", "type_name": "家庭剧"},
        {"type_id": "30", "type_name": "年代剧"},
        {"type_id": "31", "type_name": "刑侦剧"},
        {"type_id": "32", "type_name": "军旅剧"},
        {"type_id": "33", "type_name": "青春剧"},
        {"type_id": "34", "type_name": "偶像剧"},
        {"type_id": "35", "type_name": "神话剧"},
        {"type_id": "36", "type_name": "仙侠剧"},
        {"type_id": "37", "type_name": "悬疑剧"},
        {"type_id": "38", "type_name": "喜剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺纪录"},
        {"type_id": "6", "type_name": "短剧"},
    ]

    # 推广文案
    _WX_TEXT = "微信公众号\u201c源力软件汇\u201d，QQ群1054592152，伴随更多优质资源尽在源力。"

    # ==================== 筛选器 ====================
    _filters = {
        # 电影大类 - 支持按类型/地区/年份/排序筛选
        "1": {
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
                    {"n": "动作", "v": "动作"}, {"n": "爱情", "v": "爱情"}, {"n": "恐怖", "v": "恐怖"},
                    {"n": "惊悚", "v": "惊悚"}, {"n": "犯罪", "v": "犯罪"}, {"n": "科幻", "v": "科幻"},
                    {"n": "悬疑", "v": "悬疑"}, {"n": "奇幻", "v": "奇幻"}, {"n": "冒险", "v": "冒险"},
                    {"n": "战争", "v": "战争"}, {"n": "历史", "v": "历史"}, {"n": "古装", "v": "古装"},
                    {"n": "家庭", "v": "家庭"}, {"n": "传记", "v": "传记"}, {"n": "武侠", "v": "武侠"},
                    {"n": "歌舞", "v": "歌舞"}, {"n": "短片", "v": "短片"}, {"n": "动画", "v": "动画"},
                    {"n": "儿童", "v": "儿童"}, {"n": "职场", "v": "职场"}]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"}, {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"},
                    {"n": "丹麦", "v": "丹麦"}, {"n": "瑞典", "v": "瑞典"}, {"n": "巴西", "v": "巴西"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"},
                    {"n": "比利时", "v": "比利时"}, {"n": "爱尔兰", "v": "爱尔兰"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"}, {"n": "90年代", "v": "1990_1999"},
                    {"n": "80年代", "v": "1980_1989"}, {"n": "更早", "v": "0_1979"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"}]},
            ],
        },
        # 电视剧大类 - 类型包含古装、都市、历史、谍战、家庭等细分
        "2": {
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "剧情", "v": "剧情"}, {"n": "爱情", "v": "爱情"},
                    {"n": "喜剧", "v": "喜剧"}, {"n": "犯罪", "v": "犯罪"}, {"n": "悬疑", "v": "悬疑"},
                    {"n": "古装", "v": "古装"}, {"n": "动作", "v": "动作"}, {"n": "家庭", "v": "家庭"},
                    {"n": "惊悚", "v": "惊悚"}, {"n": "奇幻", "v": "奇幻"}, {"n": "美剧", "v": "美剧"},
                    {"n": "科幻", "v": "科幻"}, {"n": "历史", "v": "历史"}, {"n": "战争", "v": "战争"},
                    {"n": "韩剧", "v": "韩剧"}, {"n": "武侠", "v": "武侠"}, {"n": "言情", "v": "言情"},
                    {"n": "恐怖", "v": "恐怖"}, {"n": "冒险", "v": "冒险"}, {"n": "都市", "v": "都市"},
                    {"n": "职场", "v": "职场"}]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"}, {"n": "90年代", "v": "1990_1999"},
                    {"n": "80年代", "v": "1980_1989"}, {"n": "更早", "v": "0_1979"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"}]},
            ],
        },
        # 动漫
        "3": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"}, {"n": "90年代", "v": "1990_1999"},
                    {"n": "80年代", "v": "1980_1989"}, {"n": "更早", "v": "0_1979"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"}]},
            ],
        },
        # 综艺纪录
        "4": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"}, {"n": "90年代", "v": "1990_1999"},
                    {"n": "80年代", "v": "1980_1989"}, {"n": "更早", "v": "0_1979"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"}]},
            ],
        },
        # 短剧
        "6": {
            "class": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "综合", "v": "1"}, {"n": "最新", "v": "2"}, {"n": "最热", "v": "3"}, {"n": "评分", "v": "4"}]},
            ],
        },
    }

    # 电影细分类型映射 (type_id -> 筛选class参数值)
    # 网飞猫show页面URL格式: /show/{tid}-{class}-{area}-{lang}-{year}-{sort}-{page}.html
    # 细分类型的tid仍为1（电影大类），但用class筛选参数来过滤子类型
    _MOVIE_SUBCLASS_MAP = {
        "5":  "动作", "6":  "喜剧", "7":  "爱情", "8":  "科幻", "9":  "恐怖",
        "10": "剧情", "11": "战争", "12": "奇幻", "13": "武侠", "14": "悬疑",
        "15": "惊悚", "16": "犯罪", "17": "历史", "18": "文艺", "19": "冒险",
        "20": "动画", "21": "纪录", "22": "传记", "23": "歌舞", "24": "短片",
    }

    # 电视剧细分类型映射
    _TV_SUBCLASS_MAP = {
        "25": "古装", "26": "都市", "27": "历史", "28": "谍战", "29": "家庭",
        "30": "年代", "31": "刑侦", "32": "军旅", "33": "青春", "34": "偶像",
        "35": "神话", "36": "仙侠", "37": "悬疑", "38": "喜剧",
    }

    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._cookie = ""
        self._token = ""
        self._token_ts = 0
        # 自动探测可用域名
        self._auto_detect_host()

    def _auto_detect_host(self):
        """探测可用的域名，选择第一个能正常访问的"""
        for domain in self.DOMAINS:
            if self._solve_cc(domain):
                html = self._get_with_cookie("/")
                if html and "cdndefend" not in html[:600] and len(html) > 5000:
                    self.host = domain
                    return True
        # 如果探测全部失败，使用第一个域名
        self.host = self.DOMAINS[0]
        return False

    def getName(self):
        return "网飞猫"

    def _wechat_text(self):
        return self._WX_TEXT

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

    # ---------------- cdndefend challenge ----------------
    def _fetch_raw(self, url, timeout=15):
        """底层HTTP GET，正确处理HTTP 850等非标准状态码"""
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": self.UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # HTTP 850 等: 响应体在异常对象中
            try:
                return e.read()
            except Exception:
                return b""
        except Exception:
            return b""

    def _solve_cc(self, domain=None):
        """破解 cdndefend JS 挑战，获取 cookie"""
        base = domain or self.host
        url = base + "/"
        data = self._fetch_raw(url)
        if not data:
            return None
        text = data.decode("utf-8", errors="replace")
        if "cdndefend" not in text:
            # 没有挑战，直接返回空cookie
            self._cookie = ""
            return True
        # 提取挑战字符串
        m = re.findall(r"'([0-9A-Fa-f]{40})'", text)
        if not m:
            return None
        c = m[0]
        # 获取第一个hex字符作为索引
        n1 = int(c[0], 16)
        # SHA1暴力搜索
        i = 0
        while i < 3000000:
            h = hashlib.sha1((c + str(i)).encode("utf-8")).digest()
            if h[n1] == 0xb0 and h[n1 + 1] == 0x0b:
                self._cookie = "%s=%s%d" % (self._CC_KEY, c, i)
                return True
            i += 1
        return None

    def _get_with_cookie(self, path, referer=None):
        """带cookie的HTTP GET请求"""
        if not path.startswith("http"):
            url = self.host + path
        else:
            url = path
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if self._cookie:
            headers["Cookie"] = self._cookie
        if referer:
            headers["Referer"] = referer
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    data = resp.read()
                    for enc in ("utf-8", "gbk", "gb2312"):
                        try:
                            return data.decode(enc)
                        except Exception:
                            continue
                    return data.decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                # HTTP 850 等: 响应体在异常对象中
                try:
                    data = e.read()
                    for enc in ("utf-8", "gbk", "gb2312"):
                        try:
                            return data.decode(enc)
                        except Exception:
                            continue
                    return data.decode("utf-8", errors="replace")
                except Exception:
                    if attempt == 0:
                        time.sleep(0.6)
                        continue
                    return ""
            except Exception:
                if attempt == 0:
                    time.sleep(0.6)
                    if not self._cookie or self._cookie == "":
                        self._solve_cc()
                    continue
                return ""
        return ""

    def _get(self, path, referer=None):
        """统一HTTP GET，自动处理cdndefend挑战"""
        html = self._get_with_cookie(path, referer)
        if not html or "cdndefend" in html[:600]:
            # 重新解决挑战
            self._solve_cc()
            html = self._get_with_cookie(path, referer)
        return html

    def _host_ok(self):
        html = self._get("/")
        if not html or "cdndefend" in html[:600]:
            return False
        return True

    # ---------------- parse helpers ----------------
    def _parse_vitems(self, html):
        """从分类/首页页面解析视频列表"""
        items = []
        seen = set()
        # 网飞猫视频卡片: <a href="/detail/xxx.html" class="v-item">...</a>
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="v-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            # 标题：v-item-title 中非hidden、非广告的那个
            titles = re.findall(r'<div class="v-item-title"[^>]*>([^<]*)</div>', inner)
            name = ""
            for t in titles:
                t = self.clean(t)
                if t and "display: none" not in t and not self._is_ad_title(t):
                    name = t
                    break
            if not name and titles:
                # 取最长的非广告标题
                real = [self.clean(t) for t in titles if self.clean(t) and not self._is_ad_title(self.clean(t))]
                if real:
                    name = max(real, key=len)
            if not name:
                continue
            seen.add(vid)
            # 封面图
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            # 备注 (正片/HD中字等)
            remark = ""
            rm = re.search(r'v-item-bottom[^>]*>\s*<span>\s*([^<]*?)\s*</span>', inner)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """从搜索结果页面解析视频列表"""
        items = []
        seen = set()
        # 搜索结果: <a href="/detail/xxx.html" class="search-result-item">...</a>
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="search-result-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            # 标题
            tm = re.search(r'<div class="title">([^<]*)</div>', inner)
            if not tm:
                # 回退：从img alt提取
                tm = re.search(r'alt="([^"]+)"', inner)
            if not tm:
                continue
            name = self.clean(tm.group(1))
            if not name:
                continue
            seen.add(vid)
            # 封面图
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            # 备注：从tags提取
            remark = ""
            tags_div = re.search(r'<div class="tags">(.*?)</div>', inner, re.S)
            if tags_div:
                spans = [self.clean(x) for x in re.findall(r'<span>([^<]*)</span>', tags_div.group(1))]
                if len(spans) >= 3:
                    remark = "%s/%s/%s" % (spans[0], spans[1], spans[2])
                elif spans:
                    remark = spans[0]
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    # ---------------- token ----------------
    def _fetch_token(self):
        """从首页获取搜索token"""
        html = self._get("/")
        if not html:
            return ""
        token = ""
        m = re.search(r'name="t"[^>]*value="([^"]*)"', html)
        if m:
            token = m.group(1).strip()
        if not token:
            m2 = re.search(r'/search\?k=[^"\']*?[?&;]?t=([^"\'\s&]+)', html)
            if m2:
                token = urllib.parse.unquote(m2.group(1).strip())
        self._token = token
        self._token_ts = time.time()
        return token

    def _get_token(self):
        if self._token and (time.time() - self._token_ts) < 3600:
            return self._token
        return self._fetch_token()

    # ---------------- home ----------------
    def homeContent(self, filter):
        result = {"class": self.CATEGORIES, "filters": self._filters}
        return result

    def homeVideoContent(self):
        result = {"list": []}
        html = self._get("/")
        if not html or "cdndefend" in html[:600]:
            return result
        videos = self._parse_vitems(html)
        result["list"] = videos
        return result

    # ---------------- category ----------------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1

        # 解析筛选参数
        cls = ""
        area = ""
        lang = ""
        year = ""
        sort = "3"  # 默认最热
        if isinstance(extend, dict):
            cls = extend.get("class", "") or extend.get("类型", "") or ""
            area = extend.get("area", "") or extend.get("地区", "") or ""
            lang = extend.get("lang", "") or extend.get("语言", "") or ""
            year = extend.get("year", "") or extend.get("年份", "") or ""
            s = extend.get("sort", "") or extend.get("排序", "") or ""
            if s:
                sort = s

        # 如果是细分类型（如动作片、古装剧等），自动设置class筛选
        tid_str = str(tid)
        if tid_str in self._MOVIE_SUBCLASS_MAP:
            cls = self._MOVIE_SUBCLASS_MAP[tid_str]
            tid_str = "1"  # 使用电影大类
        elif tid_str in self._TV_SUBCLASS_MAP:
            cls = self._TV_SUBCLASS_MAP[tid_str]
            tid_str = "2"  # 使用电视剧大类

        # URL编码
        cls_q = urllib.parse.quote(self.clean(cls)) if cls else ""
        area_q = urllib.parse.quote(self.clean(area)) if area else ""
        lang_q = urllib.parse.quote(self.clean(lang)) if lang else ""
        year_q = urllib.parse.quote(self.clean(year)) if year else ""

        # 构造URL: /show/{tid}-{class}-{area}-{lang}-{year}-{sort}-{page}.html
        path = "/show/%s-%s-%s-%s-%s-%s-%d.html" % (
            tid_str, cls_q, area_q, lang_q, year_q, sort, pg
        )
        html = self._get(path)
        if not html or "cdndefend" in html[:600]:
            return result

        videos = self._parse_vitems(html)
        if videos:
            result["list"] = videos
            # 尝试从分页提取总页数
            pagecount = self._parse_pagecount(html, tid_str)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

    def _parse_pagecount(self, html, tid):
        """从分页HTML中解析总页数"""
        # 查找分页链接中的最大页码
        pats = [
            r'/show/%s-[^"]*-(\d+)\.html' % re.escape(tid),
            r'href="/show/[^"]*-(\d+)\.html"[^>]*>[^<]*尾页',
            r'class="pagenation[^"]*"[^>]*>.*?>(\d+)</a>',
        ]
        for pat in pats:
            nums = re.findall(pat, html)
            if nums:
                try:
                    return max(int(n) for n in nums)
                except Exception:
                    continue
        return 2

    # ---------------- detail ----------------
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        html = self._get("/detail/%s.html" % vid)
        if not html or "cdndefend" in html[:600] or len(html) < 1000:
            return result

        vod = {"vod_id": str(vid)}

        # 标题
        name = self._detail_name(html)
        vod["vod_name"] = name if name else str(vid)

        # 封面
        pic = self._detail_pic(html)
        vod["vod_pic"] = pic

        # 标签 (年份/地区/类型)
        tags = re.findall(r'<a[^>]*href="/show/[^"]+"[^>]*class="detail-tags-item"[^>]*>([^<]*)</a>', html)
        tags = [self.clean(t) for t in tags if self.clean(t)]
        vod_class = ""
        vod_area = ""
        vod_year = ""
        for t in tags:
            if re.fullmatch(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            elif t.endswith("年代"):
                continue
            elif re.match(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            else:
                # 智能识别地区 vs 类型
                # 地区特征：含"中国"/国家名/或不在已知类型列表中且看起来像地名
                known_areas = ("中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国",
                              "英国", "法国", "德国", "印度", "泰国", "丹麦", "瑞典",
                              "巴西", "加拿大", "俄罗斯", "意大利", "比利时", "爱尔兰",
                              "西班牙", "澳大利亚", "捷克", "荷兰", "波兰", "挪威",
                              "芬兰", "冰岛", "匈牙利", "奥地利", "瑞士", "葡萄牙",
                              "希腊", "土耳其", "伊朗", "以色列", "墨西哥", "阿根廷",
                              "智利", "哥伦比亚", "秘鲁", "南非", "埃及", "摩洛哥",
                              "阿尔及利亚", "罗马尼亚", "保加利亚", "塞尔维亚",
                              "克罗地亚", "斯洛文尼亚", "斯洛伐克", "乌克兰",
                              "白俄罗斯", "立陶宛", "拉脱维亚", "爱沙尼亚",
                              "新西兰", "菲律宾", "越南", "马来西亚", "印尼",
                              "新加坡", "蒙古", "哈萨克斯坦", "乌兹别克斯坦",
                              "巴基斯坦", "孟加拉国", "斯里兰卡", "尼泊尔",
                              "黎巴嫩", "约旦", "沙特", "阿联酋", "卡塔尔",
                              "伊拉克", "叙利亚", "约旦", "其他", "台湾", "香港",
                              "大陆", "内地")
                known_types = ("剧情", "喜剧", "动作", "爱情", "恐怖", "惊悚", "犯罪",
                              "科幻", "悬疑", "奇幻", "冒险", "战争", "历史", "古装",
                              "家庭", "传记", "武侠", "歌舞", "短片", "动画", "儿童",
                              "职场", "美剧", "韩剧", "都市", "言情", "年代", "青春",
                              "偶像", "神话", "仙侠", "谍战", "刑侦", "军旅")
                if not vod_area and (t in known_areas or t.startswith("中国") or
                                     (t not in known_types and len(t) <= 6 and
                                      not any(k in t for k in known_types))):
                    vod_area = t
                elif not vod_class:
                    vod_class = t
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_class"] = vod_class

        # 简介添加推广信息
        desc = self._detail_desc(html)
        wechat = self._wechat_text()
        if desc:
            vod["vod_content"] = desc + "\n\n" + wechat
        else:
            vod["vod_content"] = wechat

        # 详细信息行 (导演/演员/首映/备注)
        infos = {}
        for mm in re.finditer(
            r'<div class="detail-info-row">\s*<div class="detail-info-row-side">([^<]*)</div>\s*<div class="detail-info-row-main">(.*?)</div>',
            html, re.S
        ):
            label = self.clean(mm.group(1)).rstrip(":：")
            main = mm.group(2)
            text = self.clean(re.sub(r'<[^>]+>', ' ', main))
            if label:
                infos[label] = text
        vod["vod_director"] = infos.get("导演", "") or infos.get("导演", "")
        vod["vod_actor"] = infos.get("演员", "") or infos.get("主演", "")
        if not vod["vod_area"]:
            vod["vod_area"] = infos.get("地区", "")
        if not vod["vod_year"]:
            ym = re.search(r"(\d{4})-\d{2}-\d{2}", infos.get("首映", "") or infos.get("上映", ""))
            if ym:
                vod["vod_year"] = ym.group(1)
        remark = infos.get("备注", "")
        vod["vod_remarks"] = remark

        # 播放列表
        from_arr, url_arr = self._detail_plays(html, vod)

        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            # 回退：从详情页"立即播放"链接构造单集
            fallback = re.search(r'href="(/play/%s-\d+-\d+\.html)"' % re.escape(str(vid)), html)
            if fallback:
                vod["vod_play_from"] = "网飞猫线路"
                vod["vod_play_url"] = "播放$%s" % (self.host + fallback.group(1))
            else:
                vod["vod_play_from"] = "网飞猫线路"
                vod["vod_play_url"] = "播放$%s/play/%s-1-1.html" % (self.host, vid)

        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def _is_ad_title(self, s):
        """检测是否为广告/SEO标题（Unicode数学字符伪装域名等）"""
        if not s:
            return True
        # 检测Unicode数学字符（U+1D400-U+1D7FF范围，用于伪装域名）
        for c in s:
            if 0x1D400 <= ord(c) <= 0x1D7FF:
                return True
        # 检测常见广告域名模式
        lower = s.lower()
        if "kekys" in lower or "可可" in s:
            return True
        # 纯域名格式（含.且无中文）
        if "." in s and not re.search(r"[\u4e00-\u9fff]", s):
            return True
        return False

    def _detail_name(self, html):
        """提取影片标题"""
        m = re.search(r'<div class="detail-title">(.*?)</div>', html, re.S)
        if m:
            strongs = [self.clean(x) for x in re.findall(r'<strong[^>]*>([^<]*)</strong>', m.group(1))]
            # 过滤掉广告/SEO标题，取真实标题
            for s in strongs:
                if s and not self._is_ad_title(s) and len(s) > 1:
                    return s
            # 如果全部被过滤，取最长的那个
            if strongs:
                real = [s for s in strongs if s and len(s) > 1]
                if real:
                    return max(real, key=len)
        # 回退：从title标签提取
        tm = re.search(r'<title>([^<]*)</title>', html)
        if tm:
            t = self.clean(tm.group(1))
            # 去掉常见后缀
            t = re.sub(r"[-_|].*$", "", t).strip()
            if t and not self._is_ad_title(t):
                return t
        return ""

    def _detail_pic(self, html):
        """提取封面图"""
        m = re.search(r'<div class="detail-pic">(.*?)</div>', html, re.S)
        if m:
            imgs = re.findall(r'data-original="([^"]*)"', m.group(1))
            for im in imgs:
                s = self._img_src(im)
                if s:
                    return s
        imgs = re.findall(r'data-original="([^"]*)"', html)
        for im in imgs:
            s = self._img_src(im)
            if s:
                return s
        return ""

    def _detail_desc(self, html):
        """提取影片简介"""
        m = re.search(r'<div class="detail-desc">(.*?)</div>\s*<div class="detail-line"', html, re.S)
        if not m:
            m = re.search(r'<div class="detail-desc">(.*?)</div>', html, re.S)
        if m:
            txt = re.sub(r"<br\s*/?>", "\n", m.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt:
                return txt
        # 回退：meta description
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            txt = self.clean(m.group(1))
            if txt:
                return txt
        return ""

    def _detail_plays(self, html, vod):
        """解析播放线路和选集列表"""
        # 线路标签: <span class="source-item-label">DB线路</span>
        src_labels = [self.clean(x) for x in re.findall(r'source-item-label[^>]*>([^<]*)</span>', html)]
        src_labels = [s for s in src_labels if s]

        # 选集列表块: <div class="episode-list...">...</div>
        blocks = re.findall(r'<div class="episode-list[^"]*"[^>]*>(.*?)</div>', html, re.S)

        if not blocks:
            # 回退：所有选集内联
            all_eps = re.findall(r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>(?:<span>)?([^<]*)', html)
            if all_eps:
                lines = []
                for ep_path, ep_name in all_eps:
                    ep_name = self.clean(ep_name) if self.clean(ep_name) else "第%d集" % (len(lines) + 1)
                    lines.append("%s$%s" % (ep_name, self.host + ep_path))
                return ["网飞猫线路"], ["#".join(lines)]
            return [], []

        groups = []
        for b in blocks:
            eps = re.findall(r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*><span>([^<]*)</span>', b)
            groups.append(eps)

        # 配对线路标签与选集组
        from_arr = []
        url_arr = []
        n = max(len(src_labels), len(groups))
        for i in range(n):
            label = src_labels[i] if i < len(src_labels) else "线路%d" % (i + 1)
            eps = groups[i] if i < len(groups) else []
            if not eps:
                continue
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name)
                if not ep_name:
                    ep_name = "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_path))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ---------------- search ----------------
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
        if not key:
            return result
        token = self._get_token()
        if not token:
            return result
        base = self.host + "/search?k=" + urllib.parse.quote(key) + "&t=" + urllib.parse.quote(token)
        url = base
        if pg > 1:
            url = base + "&page=%d" % pg
        html = self._get(url, referer=self.host + "/")
        if not html:
            return result
        if "cdndefend" in html[:600]:
            return result
        # 如果token过期，重新获取
        if "请输入验证码" in html or self._token_expired(html):
            self._token = ""
            self._token_ts = 0
            token = self._get_token()
            if not token:
                return result
            url = self.host + "/search?k=" + urllib.parse.quote(key) + "&t=" + urllib.parse.quote(token)
            if pg > 1:
                url = url + "&page=%d" % pg
            html = self._get(url, referer=self.host + "/")
        videos = self._parse_search_items(html)
        if videos:
            result["list"] = videos
            result["pagecount"] = str(pg + 1)
            result["total"] = str(len(videos))
        return result

    def _token_expired(self, html):
        return len(html) < 5000 or '/detail/' not in html

    # ---------------- play ----------------
    def playerContent(self, flag, id, vipFlags):
        play_url = id
        if not play_url.startswith("http"):
            play_url = self.host + "/" + play_url.lstrip("/")
        html = self._get(play_url, referer=self.host + "/")
        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
            "Accept": "*/*",
        }

        real = ""
        if html:
            # 方式1: 从playSource.src提取
            m = re.search(r'const\s+playSource\s*=\s*\{[^}]*?src:\s*"([^"]+)"', html, re.S)
            if m:
                real = m.group(1).strip()
            # 方式2: 直接搜索m3u8 URL
            if not real:
                m2 = re.search(r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1', html)
                if m2:
                    real = m2.group(2)
            if not real:
                m3 = re.search(r'https?://[^\s"\']+?\.m3u8[^\s"\']*', html)
                if m3:
                    real = m3.group(0)
            # 方式3: 从JSON url字段提取
            if not real:
                m4 = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', html)
                if m4:
                    u = m4.group(1)
                    if ".m3u8" in u or ".mp4" in u:
                        real = u
            # 方式4: 从var now/url提取
            if not real:
                m5 = re.search(r'var\s+now\s*=\s*["\']([^"\']+)["\']', html)
                if m5:
                    real = m5.group(1)
            if not real:
                m6 = re.search(r'var\s+url\s*=\s*["\']([^"\']+)["\']', html)
                if m6:
                    real = m6.group(1)
            # 方式5: 尝试从API域名获取播放地址
            if not real:
                api_domain = re.search(r'whatTMDwhatTMDApiDomain\s*=\s*["\']([^"\']+)', html)
                api_key = re.search(r'whatTMDwhatTMDKey\s*=\s*["\']([^"\']+)', html)
                api_pppp = re.search(r'whatTMDwhatTMDPPPP\s*=\s*["\']([^"\']+)', html)
                if api_domain and api_key:
                    try:
                        real = self._fetch_play_from_api(
                            api_domain.group(1),
                            api_key.group(1),
                            api_pppp.group(1) if api_pppp else "",
                            play_url
                        )
                    except Exception:
                        pass

        if real and (".m3u8" in real or ".mp4" in real):
            return {
                "url": real,
                "parse": "0",
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }

        # 无法直接解析，交给TVBox嗅探
        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    def _fetch_play_from_api(self, api_domain, api_key, pppp, play_url):
        """尝试从API获取真实播放地址"""
        # 从播放页URL提取vid, source, episode
        m = re.search(r'/play/(\d+)-(\d+)-(\d+)\.html', play_url)
        if not m:
            return ""
        vid, src, ep = m.group(1), m.group(2), m.group(3)
        # 构造API请求
        api_url = api_domain.rstrip("/") + "/api/play"
        params = {
            "key": api_key,
            "vid": vid,
            "source": src,
            "episode": ep,
        }
        if pppp:
            params["pppp"] = pppp
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            query = urllib.parse.urlencode(params)
            full_url = api_url + "?" + query
            req = urllib.request.Request(full_url, headers={
                "User-Agent": self.UA,
                "Referer": self.host + "/",
                "Origin": self.host,
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                j = json.loads(data)
                if isinstance(j, dict):
                    url = j.get("url") or j.get("data", {}).get("url", "") if isinstance(j.get("data"), dict) else ""
                    if url and (".m3u8" in url or ".mp4" in url):
                        return url
        except Exception:
            pass
        return ""

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
