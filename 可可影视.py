# -*- coding: utf-8 -*-

import re
import json
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import ssl
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
        "https://www.kkys01.com",
        "https://www.kkys02.com",
        "https://www.kkys03.com",
        "https://www.kkys04.com",
        "https://www.kkys05.com",
        "https://www.kkys06.com",
        "https://www.kkys07.com",
        "https://www.kkys08.com",
        "https://www.kkys09.com",
        "https://www.kkys10.com",
        "https://www.kkys11.com",
        "https://www.kkys12.com",
        "https://www.kkys13.com",
        "https://www.kkys14.com",
        "https://www.kkys15.com",
    ]

    _CC_KEY = "cdndefend_js_cookie"

    # XOR encrypted wechat text: 微信公众号"源力软件汇"，QQ群1054592152，伴随更多优质资源尽在源力。
    _WX_DATA = [191, 228, 244, 190, 229, 251, 191, 223, 246, 190, 230, 205, 191, 213, 237, 120, 188, 224, 202, 191, 208, 193, 178, 231, 245, 190, 225, 236, 188, 235, 221, 120, 181, 230, 214, 11, 11, 189, 228, 254, 107, 106, 111, 110, 111, 99, 104, 107, 111, 104, 181, 230, 214, 190, 230, 238, 179, 192, 213, 188, 193, 238, 191, 254, 192, 190, 230, 194, 178, 238, 242, 178, 239, 222, 188, 224, 202, 191, 234, 231, 191, 198, 242, 188, 224, 202, 191, 208, 193, 185, 218, 216]
    _WX_KEY = 0x5A

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "连续剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺"},
        {"type_id": "6", "type_name": "短剧"},
    ]

    # 分类筛选器 - 每个分类独立的类型/地区/年份
    _filters = {
        "1": {  # 电影
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "剧情片", "v": "剧情"}, {"n": "喜剧片", "v": "喜剧"},
                    {"n": "动作片", "v": "动作"}, {"n": "爱情片", "v": "爱情"},
                    {"n": "恐怖片", "v": "恐怖"}, {"n": "惊悚片", "v": "惊悚"},
                    {"n": "犯罪片", "v": "犯罪"}, {"n": "科幻片", "v": "科幻"},
                    {"n": "悬疑片", "v": "悬疑"}, {"n": "奇幻片", "v": "奇幻"},
                    {"n": "冒险片", "v": "冒险"}, {"n": "战争片", "v": "战争"},
                    {"n": "历史片", "v": "历史"}, {"n": "古装片", "v": "古装"},
                    {"n": "家庭片", "v": "家庭"}, {"n": "传记片", "v": "传记"},
                    {"n": "武侠片", "v": "武侠"}, {"n": "歌舞片", "v": "歌舞"},
                    {"n": "短片", "v": "短片"}, {"n": "动画片", "v": "动画"},
                    {"n": "儿童片", "v": "儿童"}, {"n": "职场片", "v": "职场"},
                    {"n": "文艺片", "v": "文艺"}, {"n": "运动片", "v": "运动"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"},
                    {"n": "香港", "v": "中国香港"}, {"n": "台湾", "v": "中国台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                    {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"},
                    {"n": "丹麦", "v": "丹麦"}, {"n": "瑞典", "v": "瑞典"},
                    {"n": "巴西", "v": "巴西"}, {"n": "加拿大", "v": "加拿大"},
                    {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "意大利", "v": "意大利"},
                    {"n": "西班牙", "v": "西班牙"}, {"n": "澳大利亚", "v": "澳大利亚"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"},
                    {"n": "90年代", "v": "1990_1999"},
                    {"n": "80年代", "v": "1980_1989"},
                    {"n": "更早", "v": "0_1979"}]},
            ],
        },
        "2": {  # 连续剧
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "古装", "v": "古装"}, {"n": "都市", "v": "都市"},
                    {"n": "历史", "v": "历史"}, {"n": "谍战", "v": "谍战"},
                    {"n": "家庭", "v": "家庭"}, {"n": "爱情", "v": "爱情"},
                    {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
                    {"n": "动作", "v": "动作"}, {"n": "犯罪", "v": "犯罪"},
                    {"n": "悬疑", "v": "悬疑"}, {"n": "科幻", "v": "科幻"},
                    {"n": "奇幻", "v": "奇幻"}, {"n": "武侠", "v": "武侠"},
                    {"n": "战争", "v": "战争"}, {"n": "职场", "v": "职场"},
                    {"n": "惊悚", "v": "惊悚"}, {"n": "恐怖", "v": "恐怖"},
                    {"n": "冒险", "v": "冒险"}, {"n": "传记", "v": "传记"},
                    {"n": "青春", "v": "青春"}, {"n": "偶像", "v": "偶像"},
                    {"n": "言情", "v": "言情"}, {"n": "农村", "v": "农村"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"},
                    {"n": "香港", "v": "中国香港"}, {"n": "台湾", "v": "中国台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"},
                    {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"},
                    {"n": "90年代", "v": "1990_1999"},
                    {"n": "更早", "v": "0_1979"}]},
            ],
        },
        "3": {  # 动漫
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "热血", "v": "热血"}, {"n": "搞笑", "v": "搞笑"},
                    {"n": "冒险", "v": "冒险"}, {"n": "动作", "v": "动作"},
                    {"n": "科幻", "v": "科幻"}, {"n": "奇幻", "v": "奇幻"},
                    {"n": "爱情", "v": "爱情"}, {"n": "悬疑", "v": "悬疑"},
                    {"n": "校园", "v": "校园"}, {"n": "运动", "v": "运动"},
                    {"n": "机甲", "v": "机甲"}, {"n": "战争", "v": "战争"},
                    {"n": "儿童", "v": "儿童"}, {"n": "益智", "v": "益智"},
                    {"n": "经典", "v": "经典"}, {"n": "剧情", "v": "剧情"},
                    {"n": "恐怖", "v": "恐怖"}, {"n": "魔法", "v": "魔法"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "日本", "v": "日本"},
                    {"n": "大陆", "v": "中国大陆"}, {"n": "台湾", "v": "中国台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"},
                    {"n": "00年代", "v": "2000_2009"},
                    {"n": "更早", "v": "0_1999"}]},
            ],
        },
        "4": {  # 综艺
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "真人秀", "v": "真人秀"}, {"n": "脱口秀", "v": "脱口秀"},
                    {"n": "访谈", "v": "访谈"}, {"n": "音乐", "v": "歌舞"},
                    {"n": "喜剧", "v": "喜剧"}, {"n": "相亲", "v": "相亲"},
                    {"n": "纪实", "v": "纪录"}, {"n": "军事", "v": "军事"},
                    {"n": "体育", "v": "运动"}, {"n": "晚会", "v": "晚会"},
                    {"n": "搞笑", "v": "搞笑"}, {"n": "选秀", "v": "选秀"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"},
                    {"n": "香港", "v": "中国香港"}, {"n": "台湾", "v": "中国台湾"},
                    {"n": "韩国", "v": "韩国"}, {"n": "美国", "v": "美国"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"},
                    {"n": "更早", "v": "0_2009"}]},
            ],
        },
        "6": {  # 短剧
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "甜宠", "v": "甜宠"}, {"n": "虐恋", "v": "虐恋"},
                    {"n": "逆袭", "v": "逆袭"}, {"n": "穿越", "v": "穿越"},
                    {"n": "重生", "v": "重生"}, {"n": "霸总", "v": "霸总"},
                    {"n": "战神", "v": "战神"}, {"n": "悬疑", "v": "悬疑"},
                    {"n": "喜剧", "v": "喜剧"}, {"n": "都市", "v": "都市"},
                    {"n": "古装", "v": "古装"}, {"n": "奇幻", "v": "奇幻"},
                    {"n": "武侠", "v": "武侠"}, {"n": "科幻", "v": "科幻"},
                    {"n": "爱情", "v": "爱情"}, {"n": "动作", "v": "动作"},
                    {"n": "家庭", "v": "家庭"}, {"n": "其他", "v": "剧情"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "更早", "v": "0_2022"}]},
            ],
        },
    }

    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._token = ""
        self._token_ts = 0
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        try:
            self._ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
        except Exception:
            pass

    def getName(self):
        return "可可影视"

    def _get_wechat_info(self):
        """解密XOR加密的微信公众号文本"""
        try:
            return bytes([b ^ self._WX_KEY for b in self._WX_DATA]).decode("utf-8")
        except Exception:
            return ""

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

    # ---------------- network (atomic solve+fetch) ----------------
    def _urllib_req(self, url, cookie=None, referer=None):
        """单次urllib请求，返回 (html_text, is_challenge)"""
        headers = {
            "User-Agent": self.UA,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if cookie:
            headers["Cookie"] = cookie
        if referer:
            headers["Referer"] = referer
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20, context=self._ctx) as resp:
                data = resp.read()
                html = self._decode(data)
                return html, ("cdndefend" in html[:2000])
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
                html = self._decode(data)
                return html, ("cdndefend" in html[:2000])
            except Exception:
                return "", False
        except Exception:
            return "", False

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _solve_cc(self, challenge_html):
        """从挑战页面求解cookie字符串"""
        cc_match = re.search(r"['\"]([0-9A-Fa-f]{40})['\"]", challenge_html)
        if not cc_match:
            return None
        cc_key = cc_match.group(1)
        n1 = int(cc_key[0], 16)
        i = 0
        while i < 5000000:
            h = hashlib.sha1((cc_key + str(i)).encode("utf-8")).digest()
            if h[n1] == 0xb0 and h[n1 + 1] == 0x0b:
                return "%s=%s%s" % (self._CC_KEY, cc_key, i)
            i += 1
        return None

    def _get(self, path, referer=None):
        """
        原子获取：尝试带cookie直接请求 → 如果收到challenge则解cookie后重请求目标。
        不缓存cookie，每次请求独立完成。
        """
        if not path.startswith("http"):
            url = self.host + path
        else:
            url = path

        # 先不带cookie试一次（有些请求可能不需要挑战）
        html, is_challenge = self._urllib_req(url, cookie=None, referer=referer)
        if html and not is_challenge:
            return html

        # 收到challenge，求解cookie后立即请求同一个URL
        if html and is_challenge:
            cookie = self._solve_cc(html)
            if cookie:
                html2, is_challenge2 = self._urllib_req(url, cookie=cookie, referer=referer)
                if html2 and not is_challenge2:
                    return html2
                # 如果还是challenge，说明cookie又过期了——再试一次
                if html2 and is_challenge2:
                    cookie2 = self._solve_cc(html2)
                    if cookie2:
                        html3, is_challenge3 = self._urllib_req(url, cookie=cookie2, referer=referer)
                        if html3 and not is_challenge3:
                            return html3

        # 如果单域名不行，换域名
        current_host = self.host
        for d in self.DOMAINS:
            if d == current_host:
                continue
            self.host = d
            alt_url = d + path if not path.startswith("http") else path
            html, is_challenge = self._urllib_req(alt_url, cookie=None, referer=referer)
            if not html:
                continue
            if not is_challenge:
                return html
            cookie = self._solve_cc(html)
            if cookie:
                html2, is_challenge2 = self._urllib_req(alt_url, cookie=cookie, referer=referer)
                if html2 and not is_challenge2:
                    return html2
        return html or ""

    # ---------------- parse helpers ----------------
    def _parse_vitems(self, html):
        items = []
        seen = set()
        # 首页和分类页使用 class="v-item"
        pat = r'<a\s+href="(/detail/(\d+)\.html)"\s+class="v-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            # 提取标题 - 取没有 display:none 的 v-item-title
            name = ""
            titles = re.findall(r'<div class="v-item-title"([^>]*)>(.*?)</div>', inner, re.S)
            for attrs, text in titles:
                if "display: none" not in attrs:
                    # 这是实际显示的标题
                    name = self.clean(re.sub(r'<[^>]+>', '', text))
                    break
            if not name:
                # fallback: 取所有v-item-title中不含站点名的
                all_titles = [self.clean(re.sub(r'<[^>]+>', '', t)) for _, t in titles]
                for t in all_titles:
                    if t and "可可" not in t and "kkys" not in t.lower() and "kekys" not in t.lower():
                        name = t
                        break
            if not name:
                continue
            # 提取图片 - 跳过logo_placeholder
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                if "logo_placeholder" in im:
                    continue
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            # 提取备注
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
        items = []
        seen = set()
        # 搜索页使用 class="search-result-item" (不是 search-result-item-header)
        pat = r'<a\s+href="(/detail/(\d+)\.html)"\s+class="search-result-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            # 提取标题 - 在 <div class="title"> 里
            name = ""
            tm = re.search(r'<div class="title"[^>]*>(.*?)</div>', inner, re.S)
            if tm:
                name = self.clean(re.sub(r'<[^>]+>', '', tm.group(1)))
            if not name:
                # fallback: 尝试strong标签（过滤站点名）
                strongs = re.findall(r'<strong[^>]*>(.*?)</strong>', inner, re.S)
                for s in strongs:
                    s_clean = self.clean(re.sub(r'<[^>]+>', '', s))
                    if s_clean and not any(x in s_clean.lower() for x in ["kkys", "可可", "kekys"]):
                        name = s_clean
                        break
            if not name:
                name = f"详情{vid}"
            # 提取图片 - 跳过logo_placeholder
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                if "logo_placeholder" in im:
                    continue
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            # 提取备注/标签
            remark = ""
            tags_divs = re.findall(r'class="tags"[^>]*>(.*?)</div>', inner, re.S)
            if tags_divs:
                spans = [self.clean(x) for x in re.findall(r'<span[^>]*>([^<]*)</span>', tags_divs[0])]
                spans = [s for s in spans if s]
                if len(spans) >= 3:
                    remark = "/".join(spans[:3])
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
        html = self._get("/")
        if not html:
            return ""
        token = ""
        m = re.search(r'<input[^>]*name="t"[^>]*value="([^"]*)"', html)
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
        if not html:
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

        cls = ""
        area = ""
        year = ""
        if isinstance(extend, dict):
            cls = extend.get("class", "") or extend.get("类型", "") or ""
            area = extend.get("area", "") or extend.get("地区", "") or ""
            year = extend.get("year", "") or extend.get("年份", "") or ""
        cls = urllib.parse.quote(self.clean(cls))
        area = urllib.parse.quote(self.clean(area))
        year = urllib.parse.quote(self.clean(year))

        # URL格式: /show/{tid}-{class}-{area}--{year}-3-{pg}.html
        path = "/show/%s-%s-%s--%s-3-%s.html" % (tid, cls, area, year, pg)
        html = self._get(path)
        if not html:
            return result

        videos = self._parse_vitems(html)
        if videos:
            result["list"] = videos
            result["pagecount"] = str(pg + 1)
            result["total"] = str(len(videos))
        return result

    # ---------------- detail ----------------
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        html = self._get("/detail/%s.html" % vid)
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": str(vid)}

        # 名称
        vod["vod_name"] = self._detail_name(html) or str(vid)

        # 图片
        vod["vod_pic"] = self._detail_pic(html)

        # 标签/类型/地区/年份
        tags = re.findall(r'<a[^>]*href="/show/[^"]+"[^>]*class="detail-tags-item"[^>]*>([^<]*)</a>', html)
        tags = [self.clean(t) for t in tags if self.clean(t)]
        vod_class = ""
        vod_area = ""
        vod_year = ""
        area_list = ("中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "英国",
                     "法国", "德国", "印度", "泰国", "丹麦", "瑞典", "巴西", "加拿大",
                     "俄罗斯", "意大利", "比利时", "爱尔兰", "西班牙", "澳大利亚", "其他")
        for t in tags:
            if re.fullmatch(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            elif t in area_list:
                if not vod_area:
                    vod_area = t
            elif not vod_class:
                vod_class = t
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_class"] = vod_class

        # 简介 + 微信公众号
        desc = self._detail_desc(html)
        wechat = self._get_wechat_info()
        if desc and wechat:
            vod["vod_content"] = desc + "\n\n" + wechat
        elif desc:
            vod["vod_content"] = desc
        elif wechat:
            vod["vod_content"] = wechat
        else:
            vod["vod_content"] = ""

        # 详情信息行
        infos = {}
        for mm in re.finditer(
                r'<div class="detail-info-row">\s*<div class="detail-info-row-side">([^<]*)</div>\s*<div class="detail-info-row-main">(.*?)</div>',
                html, re.S):
            label = self.clean(mm.group(1)).rstrip("：:")
            main = mm.group(2)
            text = self.clean(re.sub(r'<[^>]+>', ' ', main))
            if label:
                infos[label] = text
        vod["vod_director"] = infos.get("导演", "")
        vod["vod_actor"] = infos.get("演员", "")
        if not vod["vod_area"]:
            vod["vod_area"] = infos.get("地区", "")
        if not vod["vod_year"]:
            ym = re.search(r"(\d{4})-\d{2}-\d{2}", infos.get("上映", ""))
            if ym:
                vod["vod_year"] = ym.group(1)
        remark = infos.get("备注", "")
        vod["vod_remarks"] = remark

        # 播放列表
        from_arr, url_arr = self._detail_plays(html)

        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            fallback = re.search(r'href="(/play/%s-\d+-\d+\.html)"' % re.escape(str(vid)), html)
            if fallback:
                vod["vod_play_from"] = "默认线路"
                vod["vod_play_url"] = "播放$%s" % (self.host + fallback.group(1))
            else:
                vod["vod_play_from"] = "默认线路"
                vod["vod_play_url"] = "播放$%s/play/%s-1-1.html" % (self.host, vid)

        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def _detail_name(self, html):
        m = re.search(r'<div class="detail-title">(.*?)</div>', html, re.S)
        if m:
            title_html = m.group(1)
            strongs_raw = re.findall(r'<strong[^>]*>(.*?)</strong>', title_html, re.S)
            # 过滤站点名称（包含特殊Unicode黑板字符 或 kkys/kekys/可可）
            real_names = []
            for s in strongs_raw:
                s_clean = self.clean(re.sub(r'<[^>]+>', '', s))
                if not s_clean:
                    continue
                low = s_clean.lower()
                # 检查是否为站点名
                is_site = (
                    "kkys" in low or "kekys" in low or "可可" in s_clean
                    or "𝕜" in s_clean or "𝕪" in s_clean  # Unicode黑板粗体
                    or "数学" in s_clean
                )
                if not is_site:
                    real_names.append(s_clean)
            if real_names:
                return real_names[0]
            # fallback: 取中间的strong（跳过前后站点名）
            if strongs_raw:
                mid = len(strongs_raw) // 2
                return self.clean(re.sub(r'<[^>]+>', '', strongs_raw[mid]))
        tm = re.search(r'<title>([^<]*)</title>', html)
        if tm:
            t = self.clean(tm.group(1))
            t = re.sub(r"[-_\s]*[-_\s].*$", "", t).strip()
            return t
        return ""

    def _detail_pic(self, html):
        m = re.search(r'<div class="detail-pic">(.*?)</div>', html, re.S)
        if m:
            imgs = re.findall(r'data-original="([^"]*)"', m.group(1))
            for im in imgs:
                if "logo_placeholder" in im:
                    continue
                s = self._img_src(im)
                if s:
                    return s
        imgs = re.findall(r'data-original="([^"]*)"', html)
        for im in imgs:
            if "logo_placeholder" in im:
                continue
            s = self._img_src(im)
            if s:
                return s
        return ""

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
            txt = self.clean(m.group(1))
            if txt:
                return txt
        return ""

    def _detail_plays(self, html):
        # source labels in document order
        src_labels = [self.clean(x) for x in re.findall(r'source-item-label[^>]*>([^<]*)</span>', html)]
        src_labels = [s for s in src_labels if s]

        # episode-list-box blocks in document order
        blocks = re.findall(r'<div class="episode-list-box[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if not blocks:
            blocks = re.findall(r'<div class="episode-list[^"]*"[^>]*>(.*?)</div>', html, re.S)

        if not blocks:
            # maybe all episodes inline
            all_eps = re.findall(r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>(?:<span>)?([^<]*)', html)
            if all_eps:
                lines = []
                for ep_path, ep_name in all_eps:
                    ep_name = self.clean(ep_name) if self.clean(ep_name) else "第%d集" % (len(lines) + 1)
                    lines.append("%s$%s" % (ep_name, self.host + ep_path))
                return ["默认线路"], ["#".join(lines)]
            return [], []

        groups = []
        for b in blocks:
            eps = re.findall(r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*><span>([^<]*)</span>', b)
            if not eps:
                eps = re.findall(r'<a href="(/play/[^"]+)"[^>]*class="episode-item"[^>]*>([^<]*)', b)
            groups.append(eps)

        # pair source labels with groups
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
        if pg > 1:
            url = base + "&page=%d" % pg
        else:
            url = base
        html = self._get(url, referer=self.host + "/")
        if not html:
            return result

        # 检查token是否过期
        if "请输入验证码" in html or len(html) < 3000 or '/detail/' not in html:
            self._token = ""
            self._token_ts = 0
            token = self._get_token()
            if not token:
                return result
            base = self.host + "/search?k=" + urllib.parse.quote(key) + "&t=" + urllib.parse.quote(token)
            if pg > 1:
                url = base + "&page=%d" % pg
            else:
                url = base
            html = self._get(url, referer=self.host + "/")
            if not html:
                return result

        videos = self._parse_search_items(html)
        if videos:
            result["list"] = videos
            result["pagecount"] = str(pg + 1)
            result["total"] = str(len(videos))
        return result

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
            # 优先匹配 playSource.src
            m = re.search(r'playSource\s*=\s*\{[^}]*?src\s*:\s*["\'](https?://[^"\']+)["\']', html, re.S)
            if m:
                real = m.group(1).strip()

            if not real:
                m2 = re.search(r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1', html)
                if m2:
                    real = m2.group(2)

            if not real:
                m3 = re.search(r'https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*', html)
                if m3:
                    real = m3.group(0)

            if not real:
                m4 = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', html)
                if m4:
                    u = m4.group(1)
                    if ".m3u8" in u or ".mp4" in u:
                        real = u

        if real and (".m3u8" in real or ".mp4" in real):
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

    def __jsEvalReturn(self):
        return {"proxy": None}
