# -*- coding: utf-8 -*-
"""
威视TV (weishitv.xyz) TVBox 爬虫
- MacCMS (shoutu45) 模板站点
- 首页 / 全部细分类型 / 详情 / 播放 / 搜索 全功能
- 分类数据从站点实时获取，失败时使用内置完整分类兜底
- 电影、电视剧类型细分到科幻片、奇幻片、战争片、犯罪片、武侠片、历史片、文艺片、
  古装、都市、历史、谍战、家庭等
- 影片简介处显示微信公众号"源力软件汇"
- 网站地址采用多重加密(反转+base64+XOR+ROT+base64)存储，运行时解密
- 仅使用 Python 标准库，兼容 TVBox Python 环境
"""

import re
import json
import ssl
import gzip
import zlib
import time
import base64
import html as html_mod
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

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

        def fetch(self, url, headers=None):
            return ""


class Spider(BaseSpider):
    # ===== 网站地址多重加密存储 =====
    # 加密层次: 原始URL -> 反转 -> base64 -> XOR -> ROT(+7) -> base64
    _enc_url = 'GRIMTisODE4LOwciHA9rCoVWVloRRzFgQjcJZQ=='

    # ===== 微信公众号加密信息(影片简介处显示) =====
    # XOR 加密, 运行时解密: 微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力
    _w_full_data = [146, 219, 199, 151, 215, 200, 186, 242, 201, 135, 212, 246, 145, 208, 133, 18,
                    212, 140, 231, 128, 227, 232, 128, 212, 240, 147, 222, 213, 142, 208, 243, 125,
                    221, 140, 190, 71, 144, 219, 205, 66, 88, 92, 107, 66, 92, 81, 89, 84, 70, 187,
                    142, 132, 219, 172, 248, 131, 242, 199, 141, 205, 197, 147, 217, 251, 128, 213,
                    220, 183, 135, 180, 212, 140, 231, 128, 217, 206, 141, 245, 247, 145, 223, 243,
                    141, 235, 239]
    # 线路文本加密数据(线路处显示): 威视TV·微信公众号源力软件汇
    _w_line_data = [146, 205, 232, 155, 207, 239, 11, 33, 167, 212, 141, 223, 218, 187, 141, 145,
                    215, 179, 219, 129, 213, 228, 141, 230, 232, 145, 223, 243, 141, 235, 239, 183,
                    143, 159, 214, 141, 193, 131, 216, 244]
    _w_key = b"weishi_wechat_2026"

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    # 主分类
    MAIN_CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
    ]

    # 站点分类抓取失败时的完整兜底(电影)
    DEFAULT_MOVIE_CLASSES = [
        ("科幻", "科幻"), ("奇幻", "奇幻"), ("战争", "战争"), ("犯罪", "犯罪"),
        ("武侠", "武侠"), ("历史", "历史"), ("文艺", "文艺"), ("喜剧", "喜剧"),
        ("爱情", "爱情"), ("恐怖", "恐怖"), ("动作", "动作"), ("剧情", "剧情"),
        ("同性", "同性"), ("警匪", "警匪"), ("动画", "动画"), ("冒险", "冒险"),
        ("枪战", "枪战"), ("悬疑", "悬疑"), ("惊悚", "惊悚"), ("经典", "经典"),
        ("青春", "青春"), ("微电影", "微电影"), ("古装", "古装"), ("运动", "运动"),
        ("农村", "农村"), ("儿童", "儿童"), ("网络电影", "网络电影"),
    ]

    # 站点分类抓取失败时的完整兜底(电视剧)
    DEFAULT_TV_CLASSES = [
        ("古装", "古装"), ("都市", "都市"), ("历史", "历史"), ("谍战", "谍战"),
        ("家庭", "家庭"), ("战争", "战争"), ("青春偶像", "青春偶像"),
        ("喜剧", "喜剧"), ("同性", "同性"), ("犯罪", "犯罪"), ("动作", "动作"),
        ("奇幻", "奇幻"), ("剧情", "剧情"), ("经典", "经典"), ("乡村", "乡村"),
        ("情景", "情景"), ("商战", "商战"), ("网剧", "网剧"), ("其他", "其他"),
    ]

    SEARCH_PAGE_SIZE = 20
    SEARCH_LIMIT = 1000

    def init(self, extend=""):
        self.extend = extend or ""
        self.BASE_URL = self._get_base_url()
        self._classes_cache = None
        self._search_cache = {}
        self._cookie_jar = None
        self._opener = None
        try:
            self._cookie_jar = http.cookiejar.CookieJar()
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self._cookie_jar),
                urllib.request.HTTPSHandler(context=self._build_ctx())
            )
        except Exception:
            self._opener = None

    def getName(self):
        return "威视TV"

    # ---------- 网站地址多重解密 ----------
    def _get_base_url(self):
        try:
            k = self._w_key
            # 5. base64 解码
            rotated = base64.b64decode(self._enc_url.encode('ascii'))
            # 4. ROT 反位移 (-7)
            xored = [(c - 7) & 0xFF for c in rotated]
            # 3. XOR 解密
            b = bytes([xored[i] ^ k[i % len(k)] for i in range(len(xored))])
            s = b.decode('ascii')
            # 2. base64 解码
            s = base64.b64decode(s.encode('ascii')).decode('utf-8')
            # 1. 反转还原
            return s[::-1]
        except Exception:
            return "https://weishitv.xyz"

    # ---------- 加密信息解密 ----------
    def _xor_decrypt(self, data):
        try:
            key = self._w_key
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                return ''.join(chr(data[i] ^ key[i % len(key)]) for i in range(len(data)))
            except Exception:
                return ''

    def _get_wechat_info(self):
        text = self._xor_decrypt(self._w_full_data)
        return text if text and '源力软件汇' in text else '微信公众号：源力软件汇'

    def _get_line_info(self):
        text = self._xor_decrypt(self._w_line_data)
        return text if text else "威视TV"

    # ---------- HTTP ----------
    @staticmethod
    def _build_ctx():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
        except Exception:
            pass
        return ctx

    def _headers(self, url, referer=None):
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": referer or (self.BASE_URL + "/"),
        }
        if "ajax/" in url:
            headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
            headers["X-Requested-With"] = "XMLHttpRequest"
        return headers

    def getHtml(self, url, referer=None):
        """标准库 HTTP 请求，返回解码后的文本；Cloudflare 验证页或异常返回空串。
        偶发被拦截/超时时自动重试一次，提升分类与播放页成功率。"""
        for attempt in range(2):
            text = self._get_html_once(url, referer)
            if text:
                return text
            if attempt == 0:
                time.sleep(0.4)
        return ""

    def _get_html_once(self, url, referer=None):
        try:
            req = urllib.request.Request(url, headers=self._headers(url, referer))
            if self._opener is not None:
                resp = self._opener.open(req, timeout=20)
            else:
                resp = urllib.request.urlopen(req, timeout=20, context=self._build_ctx())
            try:
                data = resp.read()
                content_encoding = (resp.headers.get("Content-Encoding", "") or "").lower()
            finally:
                try:
                    resp.close()
                except Exception:
                    pass

            if "gzip" in content_encoding:
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            elif "deflate" in content_encoding:
                try:
                    data = zlib.decompress(data)
                except Exception:
                    try:
                        data = zlib.decompress(data, -15)
                    except Exception:
                        pass

            text = self._decode_html(data)
            low = text[:2000].lower()
            if "just a moment" in low or "cf-mitigated" in low or "challenge-error-text" in low:
                return ""
            return text
        except Exception:
            return ""

    @staticmethod
    def _decode_html(data):
        for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _get_json(self, url, referer=None):
        text = self.getHtml(url, referer)
        if not text:
            return None
        text = text.strip()
        if text.startswith('\ufeff'):
            text = text[1:]
        try:
            return json.loads(text)
        except Exception:
            return None

    # ---------- 字符串工具(兼容 TVBox Python 环境) ----------
    @staticmethod
    def _cut_str(s, start, end):
        try:
            i = s.find(start)
            if i == -1:
                return ""
            i += len(start)
            j = s.find(end, i)
            if j == -1:
                return s[i:]
            return s[i:j]
        except Exception:
            return ""

    @staticmethod
    def _cut_all(s, start, end):
        res = []
        try:
            i = 0
            while True:
                p = s.find(start, i)
                if p == -1:
                    break
                p += len(start)
                q = s.find(end, p)
                if q == -1:
                    break
                res.append(s[p:q])
                i = q + len(end)
        except Exception:
            pass
        return res

    @staticmethod
    def _strip_tags(text):
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    @staticmethod
    def _clean_text(text):
        if not text:
            return ""
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
        text = re.sub(r'</p\s*>', '\n', text, flags=re.I)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_mod.unescape(text)
        text = text.replace('\xa0', ' ').replace('\u3000', ' ')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text)
        return text.strip()

    @staticmethod
    def _to_int(value, default=1):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @staticmethod
    def _dedupe_pairs(pairs):
        seen = set()
        out = []
        for cls, name in pairs or []:
            cls = (cls or "").strip()
            name = (name or cls).strip()
            if not cls or cls in seen:
                continue
            seen.add(cls)
            out.append((cls, name))
        return out

    @staticmethod
    def _reorder_pairs(pairs, priority):
        data = {}
        for cls, name in pairs or []:
            data[cls] = name
        out = []
        for cls in priority or []:
            if cls in data:
                out.append((cls, data.pop(cls)))
        for cls, name in pairs or []:
            if cls in data:
                out.append((cls, data.pop(cls)))
        return out

    @staticmethod
    def _movie_label(name):
        name = (name or "").strip()
        if not name:
            return name
        if name.endswith("片") or name.endswith("电影"):
            return name
        return name + "片"

    # ---------- 分类数据 ----------
    def _parse_category_filters(self, text, tid):
        """从分类页“类型”筛选条解析 (分类值, 显示名) 列表。"""
        result = []
        if not text:
            return result

        block = text
        i = text.find('<span>类型</span>')
        if i != -1:
            j = text.find('<ul', i)
            k = text.find('</ul>', j) if j != -1 else -1
            if j != -1 and k != -1:
                block = text[j:k]

        pattern = re.compile(
            r'href="/index\.php/vod/show/class/([^/"]+)/id/' + re.escape(str(tid)) + r'\.html"[^>]*>([^<]+)</a>',
            re.S
        )
        for enc, name in pattern.findall(block):
            try:
                cls = urllib.parse.unquote(enc).strip()
            except Exception:
                cls = enc.strip()
            name = html_mod.unescape(self._strip_tags(name)).strip()
            if not cls:
                continue
            result.append((cls, name or cls))
        return self._dedupe_pairs(result)

    def _get_categories(self):
        if self._classes_cache is not None:
            return self._classes_cache

        movie = []
        tv = []
        try:
            html1 = self.getHtml(self.BASE_URL + "/index.php/vod/show/id/1.html")
            movie = self._parse_category_filters(html1, "1")
        except Exception:
            movie = []
        try:
            html2 = self.getHtml(self.BASE_URL + "/index.php/vod/show/id/2.html")
            tv = self._parse_category_filters(html2, "2")
        except Exception:
            tv = []

        movie = self._dedupe_pairs(movie) or self._dedupe_pairs(self.DEFAULT_MOVIE_CLASSES)
        tv = self._dedupe_pairs(tv) or self._dedupe_pairs(self.DEFAULT_TV_CLASSES)

        # 站点筛选条没有的类型，按用户要求补齐
        tv_cls = set([x[0] for x in tv])
        for cls, name in [("都市", "都市"), ("谍战", "谍战")]:
            if cls not in tv_cls:
                tv.append((cls, name))

        # 用户重点要求的类型排在前面
        movie = self._reorder_pairs(
            movie, ["科幻", "奇幻", "战争", "犯罪", "武侠", "历史", "文艺"]
        )
        tv = self._reorder_pairs(tv, ["古装", "都市", "历史", "谍战", "家庭"])

        cats = [dict(x) for x in self.MAIN_CATEGORIES]
        for cls, name in movie:
            label = self._movie_label(name)
            cats.append({
                "type_id": "1|" + cls,
                "type_name": "电影-" + label,
            })
        for cls, name in tv:
            cats.append({
                "type_id": "2|" + cls,
                "type_name": "电视剧-" + name,
            })

        self._classes_cache = cats
        return cats

    @staticmethod
    def _split_tid(tid):
        tid = str(tid or "1").strip()
        if "|" in tid:
            parent, cls = tid.split("|", 1)
        elif ":" in tid:
            parent, cls = tid.split(":", 1)
        else:
            parent, cls = tid, ""
        parent = parent.strip() or "1"
        if not parent.isdigit():
            parent = "1"
        try:
            cls = urllib.parse.unquote(cls).strip()
        except Exception:
            cls = cls.strip()
        return parent, cls

    def _category_url(self, parent, cls, page):
        url = "{0}/index.php/vod/show/id/{1}".format(self.BASE_URL, parent)
        if cls:
            url += "/class/" + urllib.parse.quote(cls, safe='')
        if page > 1:
            url += "/page/" + str(page)
        return url + ".html"

    def _category_query_url(self, parent, cls, page):
        url = "{0}/index.php/vod/show.html?id={1}".format(self.BASE_URL, parent)
        if cls:
            url += "&class=" + urllib.parse.quote(cls, safe='')
        if page > 1:
            url += "&page=" + str(page)
        return url

    # ---------- 列表项解析 ----------
    def _parse_list_html(self, html):
        """从分类/搜索/首页页面解析视频列表(public-list-box 结构)。"""
        videos = []
        if not html:
            return videos

        pattern = re.compile(
            r'<a[^>]*class="public-list-exp"[^>]*href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*title="([^"]*)"'
        )
        matches = list(pattern.finditer(html))
        if not matches:
            pattern = re.compile(
                r'<a[^>]*href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*class="public-list-exp"[^>]*title="([^"]*)"'
            )
            matches = list(pattern.finditer(html))

        for m in matches:
            try:
                vid = m.group(1)
                title = html_mod.unescape(m.group(2)).strip()
                title = title.replace("在线观看", "").strip()
                if not title:
                    continue

                # 封面/备注都在锚点之后的同一 public-list-box 块内
                start = m.start()
                end = min(len(html), m.end() + 900)
                win = html[start:end]

                pic = ""
                pm = re.search(r'data-src="([^"]+)"', win)
                if pm:
                    pic = pm.group(1)
                if not pic:
                    pm = re.search(r'data-original="([^"]+)"', win)
                    if pm:
                        pic = pm.group(1)
                if not pic:
                    pm = re.search(r'<img[^>]*src="([^"]+)"', win)
                    if pm and 'base64' not in pm.group(1) and 'loading' not in pm.group(1):
                        pic = pm.group(1)
                pic = html_mod.unescape(pic or "").strip()

                remarks = ""
                rm = re.search(r'class="public-list-prb[^"]*"[^>]*>\s*([^<]*)</span>', win, re.S)
                if rm:
                    remarks = html_mod.unescape(rm.group(1)).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
            except Exception:
                continue

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def _ajax_list(self, parent, page=1):
        """MacCMS ajax 数据列表，作为首页/分类的备用数据源。"""
        try:
            url = "{0}/index.php/ajax/data?mid=1&tid={1}&page={2}&limit=30".format(
                self.BASE_URL, parent, page
            )
            data = self._get_json(url)
            if not data:
                return []
            videos = []
            for item in data.get("list", []) or []:
                vid = item.get("vod_id") or item.get("id")
                name = item.get("vod_name") or item.get("name")
                if not vid or not name:
                    continue
                videos.append({
                    "vod_id": str(vid),
                    "vod_name": html_mod.unescape(str(name)).strip(),
                    "vod_pic": item.get("vod_pic") or item.get("pic") or "",
                    "vod_remarks": item.get("vod_remarks") or "",
                })
            return videos
        except Exception:
            return []

    def _parse_pagecount(self, html):
        if not html:
            return 1
        pm = re.search(r'class="rg10">\s*\d+\s*&nbsp;\s*/\s*&nbsp;\s*(\d+)\s*页', html)
        if not pm:
            pm = re.search(r'/\s*&nbsp;\s*(\d+)\s*页', html)
        if not pm:
            pm = re.search(r'共\s*(\d+)\s*页', html)
        if pm:
            return max(1, self._to_int(pm.group(1), 1))
        return 1

    # ---------- 首页 ----------
    def homeContent(self, filter):
        return {"class": self._get_categories(), "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self.getHtml(self.BASE_URL + "/")
            videos = self._parse_list_html(html)
            if not videos:
                videos = self._ajax_list("1")
            result["list"] = videos[:30]
        except Exception:
            pass
        return result

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            parent, cls = self._split_tid(tid)
            page = self._to_int(pg, 1)
            if page < 1:
                page = 1

            # 兼容 TVBox 传入 extend 筛选
            if isinstance(extend, dict):
                ext_cls = extend.get("class") or extend.get("类型")
                if ext_cls:
                    cls = str(ext_cls).strip()

            html = self.getHtml(self._category_url(parent, cls, page))
            if not html:
                html = self.getHtml(self._category_query_url(parent, cls, page))

            videos = self._parse_list_html(html)
            if not videos and cls:
                # 二次尝试：换用另一种 URL 形式，降低偶发拦截导致的空列表
                alt = self.getHtml(self._category_query_url(parent, cls, page))
                if alt:
                    alt_videos = self._parse_list_html(alt)
                    if alt_videos:
                        html = alt
                        videos = alt_videos
            if not videos and not cls:
                videos = self._ajax_list(parent, page)

            pagecount = self._parse_pagecount(html)
            if pagecount < page and videos:
                pagecount = page

            result["list"] = videos
            result["page"] = str(page)
            result["pagecount"] = str(pagecount)
            result["limit"] = str(len(videos))
            result["total"] = str(pagecount * len(videos)) if videos else "0"
            return result
        except Exception:
            return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = ids[0] if isinstance(ids, list) and ids else ids
            vid = str(vid).strip()
            if vid.startswith("http"):
                url = vid
                m = re.search(r'/id/(\d+)', vid)
                if m:
                    vid = m.group(1)
            else:
                url = "{0}/index.php/vod/detail/id/{1}.html".format(self.BASE_URL, vid)
            html = self.getHtml(url)
            if not html:
                return result

            # 标题
            title = ""
            tm = re.search(r'<div class="this-desc-title">([^<]+)</div>', html)
            if tm:
                title = tm.group(1).strip()
            if not title:
                tm = re.search(r'<title>《([^》]+)》', html)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                tm = re.search(r'<title>([^<|]+)', html)
                if tm:
                    title = tm.group(1).strip()
            title = html_mod.unescape(title)

            # 封面
            pic = ""
            pm = re.search(r'class="this-pic-bj"[^>]*background-image:\s*url\([\'"]?([^\'")]+)', html)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-original="(https?://[^"]+)"', html)
                if pm:
                    pic = pm.group(1)
            pic = html_mod.unescape(pic).strip()

            # 年份 / 地区 / 类型 / 状态
            year = ""
            area = ""
            cat_name = ""
            remarks = ""

            ym = re.search(r'<em class="cor4">年份：</em>\s*([^<]+)', html)
            if ym:
                year = self._clean_text(ym.group(1))
            am = re.search(r'<em class="cor4">地区：</em>\s*([^<]+)', html)
            if am:
                area = self._clean_text(am.group(1))
            sm = re.search(r'<em class="cor4">状态：</em>\s*(?:<span>)?([^<]+)', html)
            if sm:
                remarks = self._clean_text(sm.group(1))

            # 类型可能有多个，例如：历史 / 同性 / 剧情
            tm = re.search(r'<em class="cor4">类型：</em>(.*?)</li>', html, re.S)
            if tm:
                names = re.findall(r'>([^<]+)</a>', tm.group(1))
                names = [self._clean_text(x) for x in names if self._clean_text(x)]
                cat_name = ",".join(names)
            if not cat_name:
                cm = re.search(r'<em class="cor4">类型：</em>\s*<a[^>]*>([^<]+)</a>', html)
                if cm:
                    cat_name = self._clean_text(cm.group(1))
            if not cat_name:
                cm = re.search(r'<a[^>]*href="/index\.php/vod/show/class/[^"]+/id/\d+\.html"[^>]*>([^<]+)</a>', html)
                if cm:
                    cat_name = self._clean_text(cm.group(1))

            # 导演
            director = ""
            d_block = self._cut_str(html, '<strong class="r6">导演:</strong>', '</div>')
            if d_block:
                director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))
            if not director:
                d_block = self._cut_str(html, '<em class="cor4">导演：</em>', '</li>')
                if d_block:
                    director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))
            director = html_mod.unescape(self._strip_tags(director))

            # 主演
            actor = ""
            a_block = self._cut_str(html, '<strong class="r6">演员:</strong>', '</div>')
            if a_block:
                actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))
            if not actor:
                a_block = self._cut_str(html, '<em class="cor4">主演：</em>', '</li>')
                if a_block:
                    actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))
            actor = html_mod.unescape(self._strip_tags(actor))

            # 简介
            content = ""
            cm = re.search(r'<div id="height_limit" class="text">(.*?)</div>', html, re.S)
            if cm:
                content = self._clean_text(cm.group(1))
            if not content:
                cm = re.search(r'<em class="cor4">简介：</em>(.*?)</li>', html, re.S)
                if cm:
                    content = self._clean_text(cm.group(1))
            if not content:
                cm = re.search(r'<div class="this-desc">\s*<div[^>]*class="text"[^>]*>(.*?)</div>', html, re.S)
                if cm:
                    content = self._clean_text(cm.group(1))
            content = content.replace("简介:", "").replace("简介：", "").strip()

            # 微信公众号信息追加到简介
            wechat_info = self._get_wechat_info()
            if content:
                if '源力软件汇' not in content:
                    content = content + '\n\n' + wechat_info
            else:
                content = wechat_info

            # 播放线路名
            line_btns = re.findall(r'<a class="swiper-slide line-btn"[^>]*>(.*?)</a>', html, re.S)
            source_names = []
            for lb in line_btns:
                # 去掉集数 badge，避免“播放线路336”这种名字
                lb = re.sub(r'<span class="badge"[^>]*>.*?</span>', '', lb, flags=re.S)
                name = self._strip_tags(lb)
                name = html_mod.unescape(name).replace("\xa0", " ")
                name = re.sub(r'\s+', ' ', name).strip()
                source_names.append(name if name else "线路")

            # 每个线路的剧集块
            list_boxes = re.findall(r'<div class="anthology-list-box[^"]*"[^>]*>(.*?)</ul>', html, re.S)
            if not list_boxes:
                list_boxes = re.findall(r'<div class="anthology-list-box[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S)

            play_groups = []
            for idx, box in enumerate(list_boxes):
                src_name = source_names[idx] if idx < len(source_names) else "线路%d" % (idx + 1)
                eps = re.findall(
                    r'<a[^>]*href="([^"]*?/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>(.*?)</a>',
                    box, re.S
                )
                ep_list = []
                seen_ep = set()
                for ep_url, ep_name in eps:
                    ep_url = html_mod.unescape(ep_url).strip()
                    ep_name = self._clean_text(ep_name) or "播放"
                    if not ep_url or ep_url in seen_ep:
                        continue
                    seen_ep.add(ep_url)
                    ep_list.append("{0}${1}".format(ep_name, ep_url))
                if ep_list:
                    play_groups.append((src_name, ep_list))

            # 回退: 从详情页立即播放链接构造单集
            if not play_groups:
                pm = re.search(
                    r'href="([^"]*?/vod/play/id/{0}/sid/\d+/nid/\d+\.html)"'.format(re.escape(vid)),
                    html
                )
                if pm:
                    play_groups.append((self._get_line_info(), ["第1集$" + pm.group(1)]))

            # 线路名去重后缀，保证同名线路也能区分
            used_names = {}
            fixed_groups = []
            for src_name, ep_list in play_groups:
                base_name = src_name or "线路"
                count = used_names.get(base_name, 0)
                used_names[base_name] = count + 1
                if count > 0:
                    base_name = "%s-%d" % (base_name, count + 1)
                fixed_groups.append((base_name, ep_list))

            play_from = "$$$".join(g[0] for g in fixed_groups)
            play_url = "$$$".join("#".join(g[1]) for g in fixed_groups)

            line_info = self._get_line_info()
            if not play_from:
                play_from = line_info
                play_url = ""

            vod = {
                "vod_id": str(vid),
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": actor,
                "vod_director": director,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_content": content,
                "vod_class": cat_name,
                "type_name": cat_name,
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }
            result["list"] = [vod]
            return result
        except Exception:
            return result

    # ---------- 搜索 ----------
    def _search_all(self, key):
        """使用 ajax suggest 一次取回全部搜索结果(最多 1000 条)，再本地分页。"""
        now = time.time()
        cached = self._search_cache.get(key)
        if cached and now - cached[0] < 300:
            return cached[1]

        videos = []
        try:
            url = "{0}/index.php/ajax/suggest?mid=1&wd={1}&limit={2}".format(
                self.BASE_URL, urllib.parse.quote_plus(key), self.SEARCH_LIMIT
            )
            data = self._get_json(url)
            if data:
                for item in data.get("list", []) or []:
                    vid = item.get("id") or item.get("vod_id")
                    name = item.get("name") or item.get("vod_name")
                    if not vid or not name:
                        continue
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": html_mod.unescape(str(name)).strip(),
                        "vod_pic": item.get("pic") or item.get("vod_pic") or "",
                        "vod_remarks": item.get("vod_remarks") or "",
                    })
        except Exception:
            videos = []

        # suggest 失败时回退网页搜索
        if not videos:
            try:
                kw = urllib.parse.quote(key, safe='')
                for search_url in [
                    "{0}/index.php/vod/search.html?wd={1}".format(self.BASE_URL, urllib.parse.quote_plus(key)),
                    "{0}/index.php/vod/search/wd/{1}.html".format(self.BASE_URL, kw),
                ]:
                    html = self.getHtml(search_url)
                    if html:
                        videos = self._parse_list_html(html)
                        if videos:
                            break
            except Exception:
                videos = []

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)

        if len(self._search_cache) > 20:
            self._search_cache.clear()
        self._search_cache[key] = (now, unique)
        return unique

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            key = (key or "").strip()
            if not key:
                return result
            page = self._to_int(pg, 1)
            if page < 1:
                page = 1

            videos = self._search_all(key)
            total = len(videos)
            pagecount = max(1, (total + self.SEARCH_PAGE_SIZE - 1) // self.SEARCH_PAGE_SIZE)

            start = (page - 1) * self.SEARCH_PAGE_SIZE
            end = start + self.SEARCH_PAGE_SIZE
            result["list"] = videos[start:end]
            result["page"] = str(page)
            result["pagecount"] = str(pagecount)
            result["total"] = str(total)
            return result
        except Exception:
            return result

    # ---------- 播放 ----------
    @staticmethod
    def _js_unescape(text):
        if not text:
            return text
        try:
            text = re.sub(r'%u([0-9a-fA-F]{4})',
                          lambda m: chr(int(m.group(1), 16)), text)
            return urllib.parse.unquote(text)
        except Exception:
            return text

    @staticmethod
    def _b64_text(text):
        try:
            raw = str(text or "").strip()
            raw += "=" * (-len(raw) % 4)
            data = base64.b64decode(raw)
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    return data.decode(enc)
                except Exception:
                    continue
        except Exception:
            pass
        return ""

    def _extract_player_url(self, html):
        if not html:
            return ""

        m = re.search(r'var\s+(?:player_aaaa|player_data)\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            info = {}
            try:
                info = json.loads(m.group(1))
            except Exception:
                info = {}
            url = info.get("url", "") if isinstance(info, dict) else ""
            enc = str(info.get("encrypt", "0")) if isinstance(info, dict) else "0"
            if url:
                if enc == "1":
                    url = self._js_unescape(url)
                elif enc == "2":
                    url = self._b64_text(url)
                    url = self._js_unescape(url)
                if url:
                    return url

        # 回退: 从 player_aaaa 文本中直接抓 url
        m = re.search(r'"url"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if m:
            raw = m.group(1)
            try:
                return json.loads('"' + raw + '"')
            except Exception:
                return raw.replace('\\/', '/')

        return ""

    @staticmethod
    def _normalize_video_url(url):
        url = html_mod.unescape(url or "").replace('\\/', '/').strip()
        if url.startswith('//'):
            url = 'https:' + url
        return url

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "flag": flag or "", "header": ""}
        try:
            if not id:
                return result
            id = str(id).strip()

            # 已经是直链，直接返回
            if re.search(r'\.(m3u8|mp4|flv|ts)(\?|#|$)', id, re.I):
                video_url = self._normalize_video_url(id)
                result["parse"] = 0
                result["url"] = video_url
                result["header"] = json.dumps({
                    "User-Agent": self.UA,
                    "Referer": self.BASE_URL + "/"
                })
                return result

            # id 可能为完整路径、完整URL或纯数字视频ID
            if id.startswith("http"):
                play_url = id
            elif id.startswith("//"):
                play_url = "https:" + id
            elif id.startswith("/"):
                play_url = self.BASE_URL + id
            elif id.startswith("index.php") or id.startswith("vod/"):
                play_url = self.BASE_URL + "/" + id
            else:
                play_url = self.BASE_URL + "/index.php/vod/play/id/" + id + ".html"

            html = self.getHtml(play_url, referer=self.BASE_URL + "/")
            if not html:
                return result

            video_url = self._extract_player_url(html)

            # 回退: 直接匹配 m3u8 / mp4
            if not video_url:
                m = re.search(r'(https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*)', html)
                if m:
                    video_url = m.group(1)
            if not video_url:
                m = re.search(r'(https?://[^\s"\'<>\\]+?\.mp4[^\s"\'<>\\]*)', html)
                if m:
                    video_url = m.group(1)

            # 回退: iframe 播放页
            if not video_url:
                m = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
                if m:
                    video_url = m.group(1)

            if video_url:
                video_url = self._normalize_video_url(video_url)
                low = video_url.lower()
                direct = ('.m3u8' in low) or ('.mp4' in low) or ('.flv' in low) or ('.ts' in low)
                result["parse"] = 0 if direct else 1
                result["url"] = video_url
                result["header"] = json.dumps({
                    "User-Agent": self.UA,
                    "Referer": self.BASE_URL + "/"
                })
            return result
        except Exception:
            return result

    # ---------- 配置 ----------
    def localProxy(self, params):
        return [200, "", ""]

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
