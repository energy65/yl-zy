# -*- coding: utf-8 -*-
"""
极速追剧 TVBox Python 源（纯标准库实现，参考 网飞猫.py 的 Spider 骨架重写）

目标站: https://jisuzhuiju.com  （自定义 PHP 站，nginx，服务端渲染，无 JS 挑战）

实站逐项核对到的结构（2026-11-02 抓取确认）：
  1) 首页 /            卡片 <a href="/detail/{id}.html"><div class="vod-card">…：
                       封面 img[alt="{片名}封面图片"]、p.vod-title 片名、p.vod-subtitle 主演、
                       span.vod-badge 集数角标
  2) 频道页 /type/{slug}.html
                       slug: dianshiju 电视剧 / dianying 电影 / dongman 动漫 /
                       zongyi 综艺 / duanju 短剧；页面由若干榜单板块组成，本身没有分页
  3) 筛选与分页 /filter?channel={1-5}&type={分类id}&area={地区}&year={年份}
                       &sort={hot|time|score}&page={n}
                       这是站内唯一的分页入口，12 条/页，总页数写在
                       <div id="pageData" data-totalpages="…">
  4) 详情 /detail/{id}.html
                       ld+json @graph → Movie / TVSeries（name/description/image/datePublished/
                       genre/actor/director/countryOfOrigin/inLanguage/aggregateRating）；
                       HTML 侧 h1.detail-title、span.tag-pill、div.meta-item、
                       button.source-tab[data-target=source-N] 与
                       div.source-panel#source-N 内 a.episode-btn[href=/vodplay/{id}-{line}-{index}.html]；
                       剧情简介在 div.synopsis-content#synopsisContent
  5) 播放页 /vodplay/{id}-{line}-{index}.html  页面不含真实地址，由前端异步请求下面的接口
  6) 解析接口 GET /api/play-url?vodId={id}&playFrom={line}&index={n}
                       → {"mode":"native","code":200,"url":"…m3u8…"}（mode 也可能为 iframe）
  7) 搜索 /search?keyword={词}&field=all&page={n}&sort=hits   12 条/页，页数同样在 #pageData

频道编号: 1 电视剧 / 2 电影 / 3 动漫 / 4 综艺 / 5 短剧
播放策略: 接口返回 native 且为 m3u8/mp4 时 parse=0 直接播；iframe 或解析不到时 parse=1 交 TVBox 嗅探。
简介: 固定写入 微信公众号「源力软件汇」。
"""
import re
import sys
import json
import time
import ssl
import gzip
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

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

    # 站点地址（实站实测可达；可在配置里传 {"host":"https://新域名"} 覆盖）
    DOMAINS = ["https://jisuzhuiju.com"]

    DEFAULT_PIC = "https://jisuzhuiju.com/img/logo.png"

    # 推广文案（写入影片简介）
    WX_TEXT = "更多影视资源请关注微信公众号：源力软件汇"

    # ==================== 一级分类（与站点 /filter 的频道编号一致） ====================
    CATEGORIES = [
        {"type_id": "1", "type_name": "电视剧"},
        {"type_id": "2", "type_name": "电影"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺"},
        {"type_id": "5", "type_name": "短剧"},
    ]

    # 兼容早期版本用过拼音 slug 的 class id
    _SLUG_CHANNEL = {
        "dianshiju": "1", "dianying": "2", "dongman": "3", "zongyi": "4", "duanju": "5",
        "电视剧": "1", "电影": "2", "动漫": "3", "综艺": "4", "短剧": "5",
    }

    # ===== 站点真实筛选数据快照（2026-11-02 实站抓取；动态抓取失败时回退） =====
    _FALLBACK_TYPES = {
        "1": [("剧情", "7"), ("古装", "9"), ("战争", "10"), ("谍战", "11"), ("爱情", "12"),
              ("罪案", "13"), ("悬疑", "14"), ("家庭", "15"), ("军旅", "16"), ("喜剧", "17"),
              ("都市", "18"), ("武侠", "19"), ("言情", "20"), ("偶像", "21"), ("青春", "22"),
              ("农村", "23"), ("穿越", "24"), ("奇幻", "25"), ("历史", "26"), ("年代", "27"),
              ("科幻", "28"), ("生活", "29"), ("励志", "31"), ("婚姻", "32"), ("警匪", "33"),
              ("犯罪", "34"), ("推理", "35"), ("商战", "36"), ("宫廷", "37"), ("仙侠", "38"),
              ("神话", "39"), ("动作", "40"), ("复仇", "41"), ("惊悚", "42")],
        "2": [("动作", "43"), ("喜剧", "44"), ("爱情", "45"), ("科幻", "46"), ("恐怖", "47"),
              ("剧情", "48"), ("战争", "49"), ("犯罪", "50"), ("惊悚", "51"), ("冒险", "52"),
              ("悬疑", "53"), ("动画", "54"), ("武侠", "55"), ("古装", "56"), ("历史", "57"),
              ("传记", "58"), ("纪录片", "59")],
        "3": [("热血", "60"), ("恋爱", "61"), ("校园", "62"), ("搞笑", "63"), ("机甲", "64"),
              ("神魔", "65"), ("竞技", "66"), ("冒险", "67"), ("治愈", "68"), ("百合", "69"),
              ("萝莉", "70"), ("后宫", "71"), ("励志", "72"), ("泡面番", "73"),
              ("国产动漫", "74"), ("日本动漫", "75"), ("欧美动漫", "76")],
        "4": [("选秀", "77"), ("情感", "78"), ("访谈", "79"), ("播报", "80"), ("旅游", "81"),
              ("音乐", "82"), ("美食", "83"), ("纪实", "84"), ("曲艺", "85"), ("游戏", "86"),
              ("亲子", "87"), ("职场", "88"), ("脱口秀", "89"), ("真人秀", "90"), ("晚会", "91")],
        "5": [],
    }

    _FALLBACK_AREAS = ["大陆", "香港", "台湾", "韩国", "日本", "美国", "泰国",
                       "法国", "英国", "德国", "印度", "其他"]

    _FALLBACK_YEARS = [("2026", "2026"), ("2025", "2025"), ("2024", "2024"),
                       ("2023", "2023"), ("2022", "2022"), ("2021", "2021"),
                       ("2020", "2020"), ("2019", "2019"), ("2018", "2018"),
                       ("其他", "-1")]

    _FALLBACK_SORTS = [("热度排序", "hot"), ("上映时间", "time"), ("评分排序", "score")]

    # 电影类型细化：站点写「动作 / 科幻」，这里显示成用户要的「动作片 / 科幻片」
    _MOVIE_TYPE_ALIAS = {
        "动作": "动作片", "喜剧": "喜剧片", "爱情": "爱情片", "科幻": "科幻片",
        "恐怖": "恐怖片", "剧情": "剧情片", "战争": "战争片", "犯罪": "犯罪片",
        "惊悚": "惊悚片", "冒险": "冒险片", "悬疑": "悬疑片", "动画": "动画片",
        "武侠": "武侠片", "古装": "古装片", "历史": "历史片", "传记": "传记片",
        "纪录片": "纪录片",
    }

    # 用户点名要的细化类型；站点没有对应分类入口的用关键词检索兜底（kw: 前缀）
    _EXTRA_TYPES = {
        "2": [("科幻片", "46"), ("奇幻片", "kw:奇幻"), ("战争片", "49"), ("犯罪片", "50"),
              ("武侠片", "55"), ("历史片", "57"), ("文艺片", "kw:文艺")],
        "1": [("古装", "9"), ("都市", "18"), ("历史", "26"), ("谍战", "11"), ("家庭", "15")],
    }

    # 这些细化类型排在类型行最前（其余按站点顺序跟在后）
    _TYPE_PRIORITY = {
        "2": ["科幻片", "奇幻片", "战争片", "犯罪片", "武侠片", "历史片", "文艺片"],
        "1": ["古装", "都市", "历史", "谍战", "家庭"],
    }

    _FILTER_KEY_ORDER = {"type": 0, "area": 1, "year": 2, "sort": 3}

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.domains = list(self.DOMAINS)
        self.host = self.domains[0]
        self._extend = {}
        self._play_cache = {}
        self._play_cache_ttl = 600
        self._filters_cache = {}
        self._filters_cache_ts = {}
        self._cache_filters_ttl = 6 * 3600
        host = ""
        try:
            if isinstance(extend, dict):
                self._extend = extend
                host = extend.get("host") or extend.get("domain") or ""
            elif isinstance(extend, str) and extend.strip():
                s = extend.strip()
                if s.startswith("{"):
                    self._extend = json.loads(s)
                    host = self._extend.get("host") or self._extend.get("domain") or ""
                elif s.startswith("http"):
                    host = s
        except Exception:
            self._extend = {}
        if host:
            host = str(host).strip().rstrip("/")
            if host:
                self.domains = [host] + [d for d in self.domains if d != host]
                self.host = host
        self._detect_host()

    def getName(self):
        return "极速追剧"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def destroy(self):
        pass

    # ==================== 域名探测 / 故障切换 ====================
    def _detect_host(self):
        """探测可用域名：首页能正常返回 vod-card 的优先"""
        for domain in self.domains:
            try:
                text = self._decode(self._fetch_raw(domain + "/", timeout=12))
                if text and "vod-card" in text and "页面没找到" not in text[:2000]:
                    self.host = domain
                    return True
            except Exception:
                continue
        return False

    def _switch_host(self):
        try:
            idx = self.domains.index(self.host)
        except ValueError:
            idx = -1
        self.host = self.domains[(idx + 1) % len(self.domains)]
        return self.host

    # ==================== 请求基础 ====================
    def _fetch_raw(self, url, referer=None, timeout=20):
        """底层 HTTP GET；响应体可能被 gzip，统一在解码前还原"""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        data = b""
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
            except Exception:
                data = b""
        except Exception:
            data = b""
        if data[:2] == b"\x1f\x8b":
            try:
                data = gzip.decompress(data)
            except Exception:
                pass
        return data

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _ok_page(self, text):
        if not text:
            return False
        head = text[:3000]
        if "页面没找到" in head or "System Error" in head:
            return False
        return "<html" in text[:2000].lower() or "vod-card" in text or "detail" in text

    def _get(self, path, referer=None):
        """页面级 GET，自动处理域名故障切换"""
        for _ in range(len(self.domains) + 1):
            url = path if path.startswith("http") else (self.host + path)
            text = self._decode(self._fetch_raw(url, referer=referer or (self.host + "/")))
            if self._ok_page(text):
                return text
            if path.startswith("http"):
                return ""
            self._switch_host()
        return ""

    def _get_json(self, path, referer=None):
        """接口级 GET（/api/play-url），失败切换域名"""
        for _ in range(len(self.domains) + 1):
            url = self.host + path
            text = self._decode(self._fetch_raw(url, referer=referer or (self.host + "/"), timeout=15))
            text = text.strip()
            if text.startswith("{"):
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass
            self._switch_host()
        return {}

    # ==================== 工具方法 ====================
    def clean(self, text):
        if text is None:
            return ""
        text = html_mod.unescape(str(text))
        text = text.replace("\xa0", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _img_src(self, url):
        if not url:
            return ""
        url = str(url).strip().replace("\\/", "/")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return ""

    # ==================== 筛选器（动态抓取 + 内置回退） ====================
    def _decorate_types(self, items, tid):
        """类型候选：用户点名的细化类型在前，站点真实分类在后，去重"""
        tid = str(tid)
        alias = self._MOVIE_TYPE_ALIAS if tid == "2" else {}
        vals = []
        seen = set()
        for name, val in self._EXTRA_TYPES.get(tid, []):
            if name in seen:
                continue
            seen.add(name)
            vals.append({"n": name, "v": val})
        for name, val in items:
            name = self.clean(name)
            val = str(val or "").strip()
            if not name or not val:
                continue
            disp = alias.get(name, name)
            if disp in seen:
                continue
            seen.add(disp)
            vals.append({"n": disp, "v": val})
        pri = self._TYPE_PRIORITY.get(tid, [])
        vals.sort(key=lambda x: pri.index(x["n"]) if x["n"] in pri else len(pri))
        return [{"n": "全部", "v": ""}] + vals

    def _fallback_filters(self, tid):
        tid = str(tid)
        filters = []
        types = self._FALLBACK_TYPES.get(tid, [])
        if types or tid in self._EXTRA_TYPES:
            filters.append({
                "key": "type", "name": "类型",
                "value": self._decorate_types(types, tid),
            })
        filters.append({
            "key": "area", "name": "地区",
            "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self._FALLBACK_AREAS],
        })
        filters.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self._FALLBACK_YEARS],
        })
        filters.append({
            "key": "sort", "name": "排序",
            "value": [{"n": n, "v": v} for n, v in self._FALLBACK_SORTS],
        })
        return filters

    def _parse_filters_from_html(self, html, tid):
        """从 /filter?channel=N 动态解析 类型 / 地区 / 年份 / 排序"""
        keymap = {"类型": "type", "地区": "area", "年份": "year"}
        found = {}
        rows = re.findall(
            r'<span class="filter-label">([^<]*)</span>\s*<div class="filter-options">(.*?)</div>',
            html, re.S)
        for label, opts in rows:
            label = self.clean(label).rstrip(":：")
            key = keymap.get(label)
            if not key:
                continue
            vals = []
            for href, text in re.findall(
                    r'<a href="([^"]+)"[^>]*class="filter-btn[^"]*">([^<]*)</a>', opts):
                name = self.clean(text)
                if not name:
                    continue
                query = urllib.parse.parse_qs(
                    urllib.parse.urlparse(html_mod.unescape(href)).query)
                val = (query.get(key) or [""])[0]
                vals.append((name, val))
            if vals:
                found[key] = (label, vals)
        sorts = []
        sb = re.search(r'<div class="filter-sort-bar">(.*?)</div>', html, re.S)
        if sb:
            for href, text in re.findall(
                    r'<a href="([^"]+)"[^>]*class="sort-btn[^"]*">([^<]*)</a>', sb.group(1)):
                query = urllib.parse.parse_qs(
                    urllib.parse.urlparse(html_mod.unescape(href)).query)
                val = (query.get("sort") or [""])[0]
                if val:
                    sorts.append((self.clean(text), val))

        filters = []
        if "type" in found:
            filters.append({"key": "type", "name": "类型",
                            "value": self._decorate_types(found["type"][1], tid)})
        if "area" in found:
            filters.append({"key": "area", "name": "地区", "value":
                            [{"n": "全部", "v": ""}] +
                            [{"n": n, "v": v} for n, v in found["area"][1] if v]})
        if "year" in found:
            filters.append({"key": "year", "name": "年份", "value":
                            [{"n": "全部", "v": ""}] +
                            [{"n": n, "v": v} for n, v in found["year"][1] if v]})
        if sorts:
            filters.append({"key": "sort", "name": "排序",
                            "value": [{"n": n, "v": v} for n, v in sorts]})
        return filters

    def _get_filters(self, tid):
        """某分类的全部筛选器：先抓实站，缺失项用内置数据补齐"""
        tid = str(tid)
        now = time.time()
        if tid in self._filters_cache and \
                (now - self._filters_cache_ts.get(tid, 0)) < self._cache_filters_ttl:
            return self._filters_cache[tid]

        filters = []
        try:
            html = self._get("/filter?channel=%s" % tid)
            if html:
                filters = self._parse_filters_from_html(html, tid)
        except Exception:
            filters = []

        if not filters:
            filters = self._fallback_filters(tid)
        else:
            have = set(f["key"] for f in filters)
            for f in self._fallback_filters(tid):
                if f["key"] not in have:
                    filters.append(f)
            filters.sort(key=lambda x: self._FILTER_KEY_ORDER.get(x["key"], 9))

        self._filters_cache[tid] = filters
        self._filters_cache_ts[tid] = now
        return filters

    # ==================== 卡片解析 ====================
    def _parse_vitems(self, html):
        """首页 / 频道页 / /filter 筛选页共用的 vod-card 卡片流"""
        items = []
        seen = set()
        if not html:
            return items
        for m in re.finditer(r'<a\b[^>]*href="(/detail/(\d+)\.html)"[^>]*>(.*?)</a>',
                             html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            body = m.group(3)
            name = ""
            tm = re.search(r'class="vod-title[^"]*"[^>]*>([^<]*)<', body)
            if tm:
                name = self.clean(tm.group(1))
            if not name:
                am = re.search(r'<img\b[^>]*\balt="([^"]*)"', body)
                if am:
                    name = self.clean(am.group(1)).replace("封面图片", "").strip()
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'<img\b[^>]*\bsrc="([^"]*)"', body)
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            bm = re.search(r'class="vod-badge[^"]*"[^>]*>([^<]*)<', body)
            if bm:
                remark = self.clean(bm.group(1))
            if not remark:
                sm = re.search(r'class="vod-subtitle[^"]*"[^>]*>([^<]*)<', body)
                if sm:
                    remark = self.clean(sm.group(1))[:40]
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """搜索结果：search-item 结构（与 vod-card 不同）"""
        items = []
        seen = set()
        if not html:
            return items
        for chunk in html.split('<div class="search-item">')[1:]:
            dm = re.search(r'/detail/(\d+)\.html', chunk)
            if not dm:
                continue
            vid = dm.group(1)
            if vid in seen:
                continue
            name = ""
            tm = re.search(r'class="search-item-title[^"]*"[^>]*>([^<]*)<', chunk)
            if tm:
                name = self.clean(tm.group(1))
            if not name:
                am = re.search(r'<img\b[^>]*\balt="([^"]*)"', chunk)
                if am:
                    name = self.clean(am.group(1)).replace("封面图片", "").strip()
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'<img\b[^>]*\bsrc="([^"]*)"', chunk)
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            tm2 = re.search(r'class="search-item-type"[^>]*>([^<]*)<', chunk)
            if tm2:
                remark = self.clean(tm2.group(1))
            if not remark:
                mm = re.search(r'class="search-meta-value"[^>]*>([^<]*)<', chunk)
                if mm:
                    remark = self.clean(mm.group(1))[:40]
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_total_pages(self, html, page, has_items=True):
        """总页数：优先 #pageData[data-totalpages]，其次分页条"""
        if not html:
            return page
        m = re.search(r'data-totalpages="(\d+)"', html)
        if m:
            try:
                n = int(m.group(1))
                if n >= page:
                    return n
            except Exception:
                pass
        nums = [int(x) for x in re.findall(r'data-page="(\d+)"', html)]
        if nums:
            n = max(nums)
            if n >= page:
                return n
        return page + 1 if has_items else page

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """一级分类 + 每个分类的全部筛选（类型/地区/年份/排序）+ 首页推荐"""
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            try:
                filters[c["type_id"]] = self._get_filters(c["type_id"])
            except Exception:
                filters[c["type_id"]] = self._fallback_filters(c["type_id"])
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self._get("/")
            if html:
                result["list"] = self._parse_vitems(html)
        except Exception:
            pass
        return result

    # ==================== 分类（/filter 筛选 + 分页） ====================
    def _pick(self, extend, key):
        if not isinstance(extend, dict):
            return ""
        val = extend.get(key)
        if val is None:
            return ""
        if isinstance(val, (list, tuple)):
            val = val[0] if val else ""
        val = str(val).strip()
        if not val or val == "全部":
            return ""
        return val

    def _normalize_tid(self, tid):
        tid = str(tid or "").strip()
        return self._SLUG_CHANNEL.get(tid, tid)

    def _build_filter_path(self, tid, extend, pg):
        params = [("channel", str(tid))]
        for key in ("type", "area", "year"):
            val = self._pick(extend, key)
            if val:
                params.append((key, val))
        params.append(("sort", self._pick(extend, "sort") or "hot"))
        params.append(("page", str(pg)))
        return "/filter?" + urllib.parse.urlencode(params)

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = self._normalize_tid(tid)
        ext = extend if isinstance(extend, dict) else {}
        if not ext and isinstance(filter, dict):
            ext = filter

        if tid not in [c["type_id"] for c in self.CATEGORIES]:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            tp = self._pick(ext, "type")
            if tp.startswith("kw:"):
                # 站点没有这个细化分类，退回关键词检索，保证点进去不为空
                kw = tp[3:].strip()
                if kw:
                    sub = self._do_search(kw, page)
                    sub["page"] = page
                    return sub
            path = self._build_filter_path(tid, ext, page)
            html = self._get(path)
            if not html:
                return result
            videos = self._parse_vitems(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            result["pagecount"] = self._parse_total_pages(html, page, bool(videos))
        except Exception:
            pass
        return result

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
        if page < 1:
            page = 1
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        keyword = self.clean(key)
        if not keyword:
            return result
        try:
            params = {"keyword": keyword, "field": "all", "page": str(page), "sort": "hits"}
            path = "/search?" + urllib.parse.urlencode(params)
            html = self._get(path, referer=self.host + "/")
            if not html:
                return result
            videos = self._parse_search_items(html)
            if not videos:
                videos = self._parse_vitems(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            result["pagecount"] = self._parse_total_pages(html, page, bool(videos))
        except Exception:
            pass
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        m = re.search(r'(\d+)', str(raw or ""))
        if not m:
            return result
        vid = m.group(1)

        html = ""
        try:
            html = self._get("/detail/%s.html" % vid)
        except Exception:
            html = ""
        if not html or "detail-title" not in html:
            return result

        data = self._detail_json(html)
        vod = {"vod_id": vid}

        name = self.clean(data.get("name") or "")
        vod["vod_name"] = name or self._detail_name(html) or vid

        pic = self._img_src(data.get("image") or data.get("thumbnailUrl") or "")
        vod["vod_pic"] = pic or self._detail_pic(html)

        vod["vod_year"] = str(data.get("datePublished") or "").strip()[:4]

        area = ""
        coo = data.get("countryOfOrigin")
        if isinstance(coo, dict):
            area = self.clean(coo.get("name") or "")
        elif isinstance(coo, str):
            area = self.clean(coo)
        vod["vod_area"] = area

        actor = data.get("actor")
        if isinstance(actor, list):
            actor = ",".join(str(x) for x in actor)
        vod["vod_actor"] = self.clean(actor or "")

        director = data.get("director")
        if isinstance(director, list):
            director = ",".join(str(x) for x in director)
        vod["vod_director"] = self.clean(director or "")

        genre = data.get("genre")
        if isinstance(genre, list):
            genre = ",".join(str(x) for x in genre)
        vod["vod_type"] = self.clean(genre or "")

        vod["vod_remarks"] = ""

        def _meta(label):
            mm = re.search(
                r'<span class="meta-label">\s*%s\s*</span>\s*<span class="meta-value">(.*?)</span>'
                % re.escape(label), html, re.S)
            if not mm:
                return ""
            return self.clean(re.sub(r'<[^>]+>', ' ', mm.group(1)))

        vod["vod_actor"] = vod["vod_actor"] or _meta("主演：")
        vod["vod_director"] = vod["vod_director"] or _meta("导演：")
        vod["vod_year"] = vod["vod_year"] or _meta("年份：")
        vod["vod_area"] = vod["vod_area"] or _meta("地区：")
        vod["vod_remarks"] = _meta("备注：") or vod["vod_remarks"]
        if not vod["vod_type"]:
            tags = [self.clean(t) for t in
                    re.findall(r'<span class="tag-pill"[^>]*>([^<]*)</span>', html)]
            vod["vod_type"] = ",".join([t for t in tags if t])

        # 简介：推广文案置于最前
        desc = self._detail_desc(html)
        vod["vod_content"] = self.WX_TEXT + ("\n\n" + desc if desc else "")

        # 播放线路 + 选集
        from_arr, url_arr = self._detail_plays(html, vid)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            fb = re.search(r'href="(/vodplay/%s-\d+-\d+\.html)"' % re.escape(vid), html)
            if not fb:
                fb = re.search(r'href="(/vodplay/%s-[A-Za-z0-9_]+-\d+\.html)"' % re.escape(vid), html)
            if fb:
                vod["vod_play_from"] = "极速追剧线路"
                vod["vod_play_url"] = "播放$%s" % fb.group(1)
            else:
                return result

        result["list"] = [vod]
        return result

    def _detail_json(self, html):
        """取 ld+json 里的 Movie / TVSeries 主对象"""
        if not html:
            return {}
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                data = json.loads(m.group(1).strip())
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            cands = data.get("@graph")
            if not isinstance(cands, list):
                cands = [data]
            for obj in cands:
                if isinstance(obj, dict) and obj.get("@type") in ("Movie", "TVSeries"):
                    return obj
        return {}

    def _detail_name(self, html):
        m = re.search(r'<h1[^>]*class="[^"]*detail-title[^"]*"[^>]*>(.*?)</h1>', html, re.S)
        if m:
            name = self.clean(re.sub(r'<[^>]+>', '', m.group(1)))
            if name:
                return name
        m = re.search(r'<title>《?([^》<|_-]*)》?', html)
        if m:
            return self.clean(m.group(1))
        return ""

    def _detail_pic(self, html):
        m = re.search(r'<div class="detail-poster-wrapper">(.*?)</div>', html, re.S)
        if m:
            pm = re.search(r'<img\b[^>]*\bsrc="([^"]*)"', m.group(1))
            if pm:
                src = self._img_src(pm.group(1))
                if src:
                    return src
        pm = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html)
        if pm:
            return self._img_src(pm.group(1))
        return self.DEFAULT_PIC

    def _detail_desc(self, html):
        m = re.search(r'<div class="synopsis-content"[^>]*>(.*?)</div>', html, re.S)
        if m:
            txt = re.sub(r'<br\s*/?>', '\n', m.group(1))
            txt = re.sub(r'<[^>]+>', '', txt)
            txt = self.clean(txt)
            if txt:
                return txt
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            return self.clean(m.group(1))
        return ""

    def _detail_plays(self, html, vid):
        """线路 source-tab 与选集面板 source-panel 一一对应"""
        tabs = {}
        for m in re.finditer(r'data-target="(source-\d+)"[^>]*>([^<]*)<', html):
            tabs[m.group(1)] = self.clean(m.group(2))

        panels = []
        for m in re.finditer(r'<div\b[^>]*>', html):
            tag = m.group(0)
            if "source-panel" not in tag:
                continue
            idm = re.search(r'id="(source-\d+)"', tag)
            if idm:
                panels.append((m.start(), m.end(), idm.group(1)))

        from_arr, url_arr = [], []
        used = {}
        for k, (_start, end, pid) in enumerate(panels):
            stop = panels[k + 1][0] if k + 1 < len(panels) else len(html)
            body = html[end:stop]
            eps = []
            for am in re.finditer(r'<a\b([^>]*)>(.*?)</a>', body, re.S):
                attrs = am.group(1)
                if "episode-btn" not in attrs:
                    continue
                hm = re.search(r'href="([^"]+)"', attrs)
                if not hm:
                    continue
                em = re.search(r'/vodplay/\d+-([A-Za-z0-9_]+)-(\d+)\.html', hm.group(1))
                if not em:
                    continue
                eps.append((em.group(1), int(em.group(2)), self.clean(am.group(2))))
            if not eps:
                continue
            eps.sort(key=lambda x: x[1])
            label = tabs.get(pid) or ("线路%d" % (k + 1))
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for code, index, ep_name in eps:
                if not ep_name:
                    ep_name = "第%d集" % index
                lines.append("%s$%s" % (ep_name, "/vodplay/%s-%s-%s.html" % (vid, code, index)))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 播放 ====================
    def _api_play_url(self, vod_id, play_from, index):
        """站点解析接口 /api/play-url（前端也是走这个拿真实地址）"""
        cache_key = "%s-%s-%s" % (vod_id, play_from, index)
        now = time.time()
        hit = self._play_cache.get(cache_key)
        if hit and (now - hit[1]) < self._play_cache_ttl:
            return hit[0]
        path = "/api/play-url?" + urllib.parse.urlencode(
            {"vodId": str(vod_id), "playFrom": str(play_from), "index": str(index)})
        data = self._get_json(path, referer="%s/vodplay/%s-%s-%s.html"
                              % (self.host, vod_id, play_from, index))
        if isinstance(data, dict) and data.get("url"):
            self._play_cache[cache_key] = (data, now)
            return data
        return data if isinstance(data, dict) else {}

    def playerContent(self, flag, id, vipFlags=None):
        raw = str(id or "").strip()
        headers = {"User-Agent": self.UA, "Referer": self.host + "/"}
        if not raw:
            return {"parse": 1, "url": "", "header": ""}

        vid = pf = idx = ""
        m = re.search(r'/vodplay/(\d+)-([A-Za-z0-9_]+)-(\d+)\.html', raw)
        if not m:
            m = re.match(r'^(\d+)-([A-Za-z0-9_]+)-(\d+)$', raw)
        if m:
            vid, pf, idx = m.group(1), m.group(2), m.group(3)

        if not vid:
            url = raw if raw.startswith("http") else (self.host + "/" + raw.lstrip("/"))
            return {"parse": 1, "url": url, "header": json.dumps(headers)}

        data = self._api_play_url(vid, pf, idx)
        url = str(data.get("url") or "").strip().replace("\\/", "/")
        mode = str(data.get("mode") or "native").strip().lower()
        api_headers = data.get("headers")
        if isinstance(api_headers, dict):
            for hk, hv in api_headers.items():
                if isinstance(hk, str) and isinstance(hv, str) and hv:
                    headers[hk] = hv

        if url.startswith("//"):
            url = "https:" + url

        if url:
            direct = bool(re.search(r'\.(m3u8|mp4|flv|ts|mkv)([?#&/]|$)', url, re.I))
            if mode != "iframe" and direct:
                return {"parse": 0, "url": url, "header": json.dumps(headers),
                        "playUrl": "", "subtitle": ""}
            # iframe 线路 / 非直链：交给 TVBox 嗅探
            return {"parse": 1, "url": url, "header": json.dumps(headers),
                    "playUrl": "", "subtitle": ""}

        # 接口没给地址：把播放页交出去，让 TVBox 自己嗅探
        page = "%s/vodplay/%s-%s-%s.html" % (self.host, vid, pf, idx)
        return {"parse": 1, "url": page, "header": json.dumps(headers)}

    def __jsEvalReturn(self):
        return {"proxy": None}
