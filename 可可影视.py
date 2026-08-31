# -*- coding: utf-8 -*-

import re
import json
import time
import hashlib
import urllib.parse
import urllib.request
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

    # cdndefend js challenge cookie (pre-computed, constant value)
    _CC_KEY = "cdndefend_js_cookie"
    _CC_VALUE = "8A08873270F4BD4E822CAF74997DA8E75347849E127211"

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "连续剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺纪录"},
        {"type_id": "6", "type_name": "短剧"},
    ]

    _WX_TEXT = "微信公众号\u201c源力软件汇\u201d，QQ群1054592152，伴随更多优质资源尽在源力。"

    _filters = {
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
            ],
        },
    }

    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._cookie = "%s=%s" % (self._CC_KEY, self._CC_VALUE)
        self._token = ""
        self._token_ts = 0
        self._session = {}

    def getName(self):
        return "可可影视"

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

    # ---------------- network ----------------
    def _solve_cc(self, domain=None):
        url = (domain or self.host) + "/"
        req = urllib.request.Request(url, headers={"User-Agent": self.UA})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None
        if "cdndefend" not in data:
            return self._cookie
        m = re.findall(r"'([0-9A-F]{40})'", data)
        if not m:
            return None
        c = m[0]
        i = 0
        while i < 3000000:
            h = hashlib.sha1((c + str(i)).encode("utf-8")).digest()
            if h[8] == 0xb0 and h[9] == 0xb:
                return "%s=%s%d" % (self._CC_KEY, c, i)
            i += 1
        return None

    def _get(self, path, referer=None):
        if not path.startswith("http"):
            url = self.host + path
        else:
            url = path
        headers = {
            "User-Agent": self.UA,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Cookie": self._cookie,
        }
        if referer:
            headers["Referer"] = referer
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
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
        return ""

    def _host_ok(self):
        html = self._get("/")
        if not html or "cdndefend" in html[:600]:
            return False
        return True

    # ---------------- parse helpers ----------------
    def _parse_vitems(self, html):
        items = []
        seen = set()
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="v-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            titles = re.findall(r'<div class="v-item-title"[^>]*>([^<]*)</div>', inner)
            name = ""
            if len(titles) > 1:
                name = self.clean(titles[1])
            elif titles:
                name = self.clean(titles[0])
            if not name:
                continue
            seen.add(vid)
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                s = self._img_src(im)
                if s:
                    pic = s
                    break
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
        pat = r'<a href="(/detail/(\d+)\.html)"\s+class="search-result-item"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            href, vid, inner = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            tm = re.search(r'<div class="title">([^<]*)</div>', inner)
            if not tm:
                continue
            name = self.clean(tm.group(1))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            imgs = re.findall(r'data-original="([^"]*)"', inner)
            for im in imgs:
                s = self._img_src(im)
                if s:
                    pic = s
                    break
            remark = ""
            tags = re.findall(r'<div class="tags">(.*?)</div>', inner, re.S)
            if tags:
                spans = [self.clean(x) for x in re.findall(r'<span>([^<]*)</span>', tags[0])]
                for sp in spans:
                    if sp and remark == "":
                        remark = sp
                if len(spans) >= 3:
                    remark = "%s/%s/%s" % (spans[0], spans[1], spans[2])
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
        path = "/show/%s-%s-%s--%s-3-%s.html" % (tid, cls, area, year, pg)
        html = self._get(path)
        if not html or "cdndefend" in html[:600]:
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
        if not html or "cdndefend" in html[:600] or len(html) < 1000:
            return result

        vod = {"vod_id": str(vid)}

        name = self._detail_name(html)
        vod["vod_name"] = name if name else str(vid)

        pic = self._detail_pic(html)
        vod["vod_pic"] = pic

        tags = re.findall(r'<a[^>]*href="/show/[^"]+"[^>]*class="detail-tags-item"[^>]*>([^<]*)</a>', html)
        tags = [self.clean(t) for t in tags if self.clean(t)]
        vod_class = ""
        vod_area = ""
        vod_year = ""
        for t in tags:
            if re.fullmatch(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            elif t in ("2026", "2025", "2024", "2023", "2022") or t.endswith("年代"):
                continue
            elif re.match(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            else:
                if not vod_area and t in ("中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "英国", "法国", "德国", "印度", "泰国", "丹麦", "瑞典", "巴西", "加拿大", "俄罗斯", "意大利", "比利时", "爱尔兰", "西班牙", "澳大利亚", "其他"):
                    vod_area = t
                elif not vod_class and t not in ("2026", "2025"):
                    vod_class = t
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_class"] = vod_class

        desc = self._detail_desc(html)
        wechat = self._wechat_text()
        if desc:
            vod["vod_content"] = desc + "\n\n" + wechat
        else:
            vod["vod_content"] = wechat

        infos = {}
        for mm in re.finditer(r'<div class="detail-info-row">\s*<div class="detail-info-row-side">([^<]*)</div>\s*<div class="detail-info-row-main">(.*?)</div>', html, re.S):
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

        from_arr, url_arr = self._detail_plays(html, vod)

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
            strongs = [self.clean(x) for x in re.findall(r'<strong[^>]*>([^<]*)</strong>', m.group(1))]
            if len(strongs) > 1:
                return strongs[1]
            if strongs:
                return strongs[0]
        tm = re.search(r'<title>([^<]*)</title>', html)
        if tm:
            t = self.clean(tm.group(1))
            return re.sub(r"[-_].*$", "", t).strip()
        return ""

    def _detail_pic(self, html):
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

    def _detail_plays(self, html, vod):
        # source labels in document order
        src_labels = [self.clean(x) for x in re.findall(r'source-item-label[^>]*>([^<]*)</span>', html)]
        src_labels = [s for s in src_labels if s]

        # episode-list blocks in document order
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
        url = base
        if pg > 1:
            url = base + "&page=%d" % pg
        html = self._get(url, referer=self.host + "/")
        if not html:
            return result
        if "cdndefend" in html[:600]:
            return result
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
            m = re.search(r'const\s+playSource\s*=\s*\{[^}]*?src:\s*"([^"]+)"', html, re.S)
            if m:
                real = m.group(1).strip()
            if not real:
                m2 = re.search(r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1', html)
                if m2:
                    real = m2.group(2)
            if not real:
                m3 = re.search(r'https?://[^\s"\']+?\.m3u8[^\s"\']*', html)
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