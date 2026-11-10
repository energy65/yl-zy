# -*- coding: utf-8 -*-
"""
目标站: 洛雪TV (https://tv.lxyy.club/)
站点类型: 综合影视 (电影 / 电视剧 / 动漫), 聚合 8 个采集源
接口: JSON API (纯 Python 标准库即可访问)
    /api/proxy.php?action=home     首页推荐 (categories 字典)
    /api/proxy.php?action=search   搜索 (wd=关键词)
    /api/proxy.php?action=detail   详情 (source=源&id=影片id) -> episodes 播放列表
    /api/tmdb.php?path=...         TMDB 透传 (discover/movie, discover/tv)
                                   用于「类型细化」分类浏览

功能 (写法参考 网飞猫.py):
    - homeContent: 一级分类 (电影/电视剧/动漫) + 各分类二级筛选 (类型/地区/年份/排序)
    - 类型细化: 电影->科幻片/奇幻片/战争片/犯罪片/武侠片/历史片/文艺片/动作片/喜剧片/
                爱情片/悬疑片/恐怖片/动画片/纪录片/剧情片
                电视剧->古装/都市/历史/谍战/家庭/战争/犯罪/悬疑/科幻奇幻/爱情/喜剧/动作冒险/动画/纪录
    - categoryContent: 通过 TMDB discover 按类型/地区/年份/排序筛选出片单
    - searchContent: 直接搜索站点采集库 (任意影片)
    - detailContent: 按片名聚合 8 个采集源, 输出多线路播放列表
    - playerContent: m3u8 直链 parse=0 直接播放; 官方网页 parse=1 交 TVBox 解析
    - 影片简介处添加 微信公众号 "源力软件汇"

网络注意 (TVBox 端不出数据的核心修复):
    - 多策略自适应请求, 按顺序尝试, 首个成功策略被记忆, 失败自动轮换:
      1) urllib.urlopen + 宽松 SSL 上下文 (TVBox 安卓运行时实测可用, 写法同 网飞猫.py)
      2) build_opener + TLS1.2 + ALPN http/1.1 (Windows / 部分 TLS1.3 EOF 环境)
      3) requests (运行环境提供时)
    - init() 时用小请求预热探测可用策略, 避免 homeContent 超时
    - 全部传输失败后 30 秒内快速失败, 避免每个页面都长时间卡顿
    - 响应体自动识别并解压 gzip
    - 需绕过系统代理 (部分环境有 127.0.0.1:3067 代理会失败)
    - 偶发 502 (Cloudflare origin), 请求失败自动重试
"""
import re
import sys
import io
import json
import time
import ssl
import gzip
import base64
import urllib.parse
import urllib.request
import urllib.error

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

try:
    import warnings
    warnings.filterwarnings("ignore")
except Exception:
    pass


class Spider(BaseSpider):
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    HOST = "https://tv.lxyy.club"

    DEFAULT_PIC = ""

    # 传输层整体连续失败后的快速失败窗口 (秒), 避免卡界面
    DEAD_WINDOW = 30

    # 单次请求超时 (秒)
    REQ_TIMEOUT = 10

    # 推广文案 (写入影片简介)
    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇"
    )

    # 采集源优先级 (m3u8 直链源靠前, 官方网页源靠后)
    SOURCE_ORDER = ["mj", "jl", "360zy", "dytt", "ik", "md", "qilin", "fy"]

    # 详情最多聚合的采集源数量 (控制请求耗时)
    MAX_SOURCES = 8

    # 首页数据缓存时间 (秒), homeContent/homeVideoContent 共用
    HOME_CACHE_TTL = 300

    # ==================== 一级分类 ====================
    GROUPS = [
        ("movie", "电影"),
        ("tv", "电视剧"),
        ("anime", "动漫"),
    ]

    # ==================== 类型细化 (TMDB genre/地区 映射) ====================
    # 每个类型 -> 追加的 TMDB discover 参数
    TYPE_PARAMS = {
        "movie": {
            "科幻片": {"with_genres": "878"},
            "奇幻片": {"with_genres": "14"},
            "战争片": {"with_genres": "10752"},
            "犯罪片": {"with_genres": "80"},
            "武侠片": {"with_genres": "28", "with_origin_country": "CN|HK"},
            "历史片": {"with_genres": "36"},
            "文艺片": {"with_genres": "18", "vote_average_gte": "7.5", "vote_count_gte": "300"},
            "动作片": {"with_genres": "28"},
            "喜剧片": {"with_genres": "35"},
            "爱情片": {"with_genres": "10749"},
            "悬疑片": {"with_genres": "9648"},
            "恐怖片": {"with_genres": "27"},
            "动画片": {"with_genres": "16"},
            "纪录片": {"with_genres": "99"},
            "剧情片": {"with_genres": "18"},
        },
        "tv": {
            "古装": {"with_genres": "10768", "with_origin_country": "CN"},
            "都市": {"with_genres": "18", "with_origin_country": "CN", "without_genres": "16,35,10766"},
            "历史": {"with_genres": "36"},
            "谍战": {"with_genres": "9648", "with_origin_country": "CN"},
            "家庭": {"with_genres": "10751", "with_origin_country": "CN"},
            "战争": {"with_genres": "10768"},
            "犯罪": {"with_genres": "80"},
            "悬疑": {"with_genres": "9648"},
            "科幻奇幻": {"with_genres": "10765"},
            "爱情": {"with_genres": "10749"},
            "喜剧": {"with_genres": "35"},
            "动作冒险": {"with_genres": "10759"},
            "动画": {"with_genres": "16"},
            "纪录": {"with_genres": "99"},
        },
        "anime": {
            "国漫": {"endpoint": "discover/tv", "with_genres": "16", "with_origin_country": "CN"},
            "日漫": {"endpoint": "discover/tv", "with_genres": "16", "with_origin_country": "JP"},
            "欧美动画": {"endpoint": "discover/tv", "with_genres": "16", "with_original_language": "en"},
            "动画电影": {"endpoint": "discover/movie", "with_genres": "16"},
            "动画剧集": {"endpoint": "discover/tv", "with_genres": "16"},
        },
    }

    # 地区 -> TMDB 参数
    AREA_PARAMS = {
        "大陆": {"with_origin_country": "CN"},
        "香港": {"with_origin_country": "HK"},
        "台湾": {"with_origin_country": "TW"},
        "港台": {"with_origin_country": "HK|TW"},
        "日韩": {"with_origin_country": "JP|KR"},
        "日本": {"with_origin_country": "JP"},
        "韩国": {"with_origin_country": "KR"},
        "欧美": {"with_original_language": "en"},
    }

    _YEAR_OPTIONS = [
        ("全部", ""), ("2026", "2026"), ("2025", "2025"), ("2024", "2024"),
        ("2023", "2023"), ("2022", "2022"), ("2021", "2021"), ("2020", "2020"),
        ("10年代", "2010_2019"), ("00年代", "2000_2009"), ("90年代", "1990_1999"),
        ("80年代", "1980_1989"), ("更早", "1900_1979"),
    ]

    _SORT_OPTIONS = [("热门", ""), ("最新", "最新"), ("高分", "高分")]

    # TMDB 默认基础参数
    _BASE_PARAMS = {
        "movie": {"endpoint": "discover/movie",
                  "params": {"sort_by": "popularity.desc", "include_adult": "false",
                              "include_video": "false", "primary_release_date_lte": "today"}},
        "tv": {"endpoint": "discover/tv",
               "params": {"sort_by": "popularity.desc", "include_adult": "false",
                          "include_null_first_air_dates": "false", "first_air_date_lte": "today"}},
        "anime": {"endpoint": "discover/tv",
                  "params": {"sort_by": "popularity.desc", "include_adult": "false",
                             "with_genres": "16"}},
    }

    # ==================== 初始化 ====================
    def __init__(self):
        self._reset_net()

    def init(self, extend=""):
        # ext 可选: {"host": "https://..."} 覆盖站点地址
        try:
            if extend:
                cfg = json.loads(extend) if isinstance(extend, str) else extend
                if isinstance(cfg, dict) and cfg.get("host"):
                    host = str(cfg["host"]).rstrip("/")
                    if host.startswith("http"):
                        self.HOST = host
        except Exception:
            pass
        self._reset_net()
        self._warmup()

    def _reset_net(self):
        self._strategies = None      # [(name, fn)] 惰性构建
        self._si = 0                 # 当前可用策略下标
        self._dead_until = 0         # 传输层整体失败后的快速失败截止时间
        self._home_cache = None      # 首页数据缓存
        self._home_cache_ts = 0

    def getName(self):
        return "洛雪TV"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== SSL 上下文 ====================
    @staticmethod
    def _make_ctx(pinned=False):
        """宽松 SSL 上下文 (不校验证书); pinned=True 时锁定 TLS1.2 + ALPN http/1.1"""
        ctx = None
        for maker in (lambda: ssl.create_default_context(),
                      lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
                      lambda: ssl.SSLContext(ssl.PROTOCOL_TLS)):
            try:
                ctx = maker()
                break
            except Exception:
                continue
        if ctx is None:
            return None
        try:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        except Exception:
            pass
        if pinned:
            try:
                ctx.maximum_version = ssl.TLSVersion.TLSv1_2
                ctx.set_alpn_protocols(["http/1.1"])
            except Exception:
                pass
        return ctx

    # ==================== 网络请求 (多策略自适应) ====================
    def _ensure_net(self):
        """惰性构建请求策略列表 (任何一步失败都不影响其余策略)"""
        if self._strategies is not None:
            return
        # 绕过系统代理 (部分环境有本地代理会导致失败)
        try:
            import os
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                      "ALL_PROXY", "all_proxy"):
                os.environ.pop(k, None)
        except Exception:
            pass

        strategies = []

        # 策略1: urlopen + 宽松上下文 (TVBox 安卓运行时实测可用, 写法同 网飞猫.py)
        def s_plain(url, headers, timeout):
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=self._make_ctx()) as resp:
                return resp.read()
        strategies.append(("urlopen", s_plain))

        # 策略2: opener + TLS1.2 + ALPN http/1.1 (部分 TLS1.3 EOF 环境需要)
        try:
            ctx = self._make_ctx(pinned=True)
            if ctx is not None:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    urllib.request.HTTPSHandler(context=ctx),
                )

                def s_tls12(url, headers, timeout):
                    req = urllib.request.Request(url, headers=headers)
                    with opener.open(req, timeout=timeout) as resp:
                        return resp.read()
                strategies.append(("tls12", s_tls12))
        except Exception:
            pass

        # 策略3: requests (运行环境提供时)
        try:
            import requests as _rq

            def s_requests(url, headers, timeout):
                r = _rq.get(url, headers=headers, timeout=timeout,
                            verify=False, allow_redirects=True)
                if r.status_code >= 400:
                    raise urllib.error.HTTPError(
                        url, r.status_code, "HTTP %d" % r.status_code, None, None)
                return r.content
            strategies.append(("requests", s_requests))
        except Exception:
            pass

        self._strategies = strategies

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    @staticmethod
    def _decode_body(body):
        """bytes -> str, 自动解压 gzip"""
        if isinstance(body, str):
            return body
        if not body:
            return ""
        if body[:2] == b"\x1f\x8b":
            try:
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
            except Exception:
                pass
        try:
            return body.decode("utf-8", "replace")
        except Exception:
            return ""

    def _try_fetch(self, url, timeout=None):
        """轮换策略请求一次
        返回 (body文本, ok, transport_ok):
          ok=True          -> 拿到 HTTP 响应 (body 可能为空, 如 4xx)
          ok=False + transport_ok=True  -> 5xx, 可重试
          ok=False + transport_ok=False -> 传输层全失败
        """
        if timeout is None:
            timeout = self.REQ_TIMEOUT
        self._ensure_net()
        strategies = self._strategies or []
        if not strategies:
            return "", False, False
        n = len(strategies)
        for k in range(n):
            idx = (self._si + k) % n
            name, fn = strategies[idx]
            try:
                body = fn(url, self._headers(), timeout)
                self._si = idx
                return self._decode_body(body), True, True
            except urllib.error.HTTPError as e:
                # 能收到 HTTPError 说明传输层 (DNS/TLS/HTTP) 正常
                self._si = idx
                if 500 <= e.code <= 599:
                    return "", False, True     # 源站/网关偶发错误 -> 外层重试
                return "", True, True          # 4xx: 接口正常但无数据
            except Exception:
                continue                       # 该策略不可用 -> 换下一个
        return "", False, False

    def _warmup(self):
        """init 阶段探测可用传输策略 (小请求, 不拉数据)"""
        try:
            body, ok, tp = self._try_fetch(self.HOST + "/favicon.ico", timeout=8)
            return bool(ok or tp)
        except Exception:
            return False

    def _get(self, path, tries=2):
        """GET 请求, 5xx/传输失败自动重试; 传输层整体失败后短时间内快速失败"""
        if time.time() < self._dead_until:
            return ""
        url = self.HOST + path
        transport = False
        for i in range(max(1, tries)):
            body, ok, tp = self._try_fetch(url)
            if ok:
                return body
            transport = transport or tp
            time.sleep(0.5)
        if not transport:
            # 全部策略连传输都失败: 30 秒内快速失败, 避免每个页面都卡
            self._dead_until = time.time() + self.DEAD_WINDOW
        return ""

    def _get_json(self, path, tries=2):
        raw = self._get(path, tries)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    # ==================== vid 编解码 (片名 -> 可搜索的 id) ====================
    def _encode_vid(self, title, media_type):
        payload = json.dumps({"t": title, "m": media_type}, ensure_ascii=False)
        b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
        # 去掉 = 填充, 避免个别 TVBox 端对 vod_id 做额外处理时出问题
        return "lx_" + b64.replace("=", "")

    def _decode_vid(self, vid):
        if not isinstance(vid, str) or not vid.startswith("lx_"):
            return None, None
        try:
            raw = vid[3:]
            pad = "=" * (-len(raw) % 4)
            data = json.loads(
                base64.urlsafe_b64decode((raw + pad).encode("ascii")).decode("utf-8"))
            return data.get("t"), data.get("m")
        except Exception:
            return None, None

    # ==================== 站点搜索 / 详情 ====================
    def _search(self, key):
        """调用站点搜索, 返回 [{source,id,name,pic,remarks,type,year,area}]"""
        if not key:
            return []
        path = "/api/proxy.php?action=search&wd=" + urllib.parse.quote(key)
        data = self._get_json(path)
        results = data.get("results") or []
        out = []
        for r in results:
            if not isinstance(r, dict):
                continue
            out.append({
                "source": r.get("source") or "",
                "id": r.get("id"),
                "name": r.get("name") or "",
                "pic": r.get("pic") or "",
                "remarks": r.get("remarks") or "",
                "type": r.get("type") or "",
                "year": r.get("year") or "",
                "area": r.get("area") or "",
            })
        return out

    def _detail(self, source, vid):
        """调用站点详情, 返回单个 details 条目 (dict) 或 None"""
        if not source or vid is None:
            return None
        path = ("/api/proxy.php?action=detail&source=%s&id=%s"
                % (urllib.parse.quote(str(source)), urllib.parse.quote(str(vid))))
        data = self._get_json(path)
        details = data.get("details") or []
        if details and isinstance(details[0], dict):
            return details[0]
        return None

    def _order_rows(self, rows):
        """按 SOURCE_ORDER 排序搜索结果 (m3u8 直链源优先)"""
        order = {s: i for i, s in enumerate(self.SOURCE_ORDER)}
        return sorted(rows, key=lambda r: order.get(r.get("source"), 99))

    @staticmethod
    def _norm(s):
        """归一化片名: 去全部空白 (应对部分源片名带尾随空格/全角空格)"""
        return re.sub(r"\s+", "", str(s or "")).strip()

    def _select_best_rows(self, title, rows):
        """每源选取一个与片名精确匹配的行 (避免混入续集/解说等不同影片)"""
        t = self._norm(title)
        if not t:
            return self._order_rows(rows)[:self.MAX_SOURCES]
        exact = {}
        for r in rows:
            src = r.get("source") or ""
            if not src:
                continue
            if src in exact:
                continue
            if self._norm(r.get("name")) == t:
                exact[src] = r
        if exact:
            return self._order_rows(list(exact.values()))
        # 无精确匹配: 回退到按源去重的全部结果
        fallback = {}
        for r in rows:
            src = r.get("source") or ""
            if src and src not in fallback:
                fallback[src] = r
        return self._order_rows(list(fallback.values()))[:self.MAX_SOURCES]

    # ==================== 首页 ====================
    def homeContent(self, filter):
        classes = [{"type_id": g, "type_name": n} for g, n in self.GROUPS]
        filters = {}
        for g, _ in self.GROUPS:
            filters[g] = [
                self._type_filter(g),
                self._area_filter(),
                self._year_filter(),
                self._sort_filter(),
            ]
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            now = time.time()
            if self._home_cache is not None and now - self._home_cache_ts < self.HOME_CACHE_TTL:
                return {"list": self._home_cache}
            data = self._get_json("/api/proxy.php?action=home")
            cats = data.get("categories") or {}
            if not isinstance(cats, dict):
                cats = {}
            seen = set()
            items = []
            for _cname, arr in cats.items():
                for it in (arr or []):
                    if not isinstance(it, dict):
                        continue
                    name = it.get("name") or ""
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    remark = it.get("remarks") or ""
                    if not remark and it.get("year"):
                        remark = str(it.get("year"))
                    items.append({
                        "vod_id": self._encode_vid(name, "auto"),
                        "vod_name": name,
                        "vod_pic": it.get("pic") or self.DEFAULT_PIC,
                        "vod_remarks": remark,
                    })
            if items:
                self._home_cache = items
                self._home_cache_ts = now
            result["list"] = items
        except Exception:
            pass
        return result

    def _type_filter(self, tid):
        vals = [{"n": "全部", "v": ""}]
        vals += [{"n": t, "v": t} for t in self.TYPE_PARAMS.get(tid, {})]
        return {"key": "type", "name": "类型", "value": vals}

    def _area_filter(self):
        vals = [{"n": "全部", "v": ""}]
        vals += [{"n": a, "v": a} for a in self.AREA_PARAMS]
        return {"key": "area", "name": "地区", "value": vals}

    def _year_filter(self):
        vals = [{"n": n, "v": v} for n, v in self._YEAR_OPTIONS]
        return {"key": "year", "name": "年份", "value": vals}

    def _sort_filter(self):
        vals = [{"n": n, "v": v} for n, v in self._SORT_OPTIONS]
        return {"key": "sort", "name": "排序", "value": vals}

    # ==================== 分类 (TMDB discover) ====================
    def _year_params(self, year, tid):
        if re.fullmatch(r"\d{4}", year):
            key = "primary_release_year" if tid == "movie" else "first_air_date_year"
            return {key: year}
        m = re.match(r"(\d{4})_(\d{4})", year)
        if m:
            gte, lte = m.group(1), m.group(2)
            key = "primary_release_date" if tid == "movie" else "first_air_date"
            return {key + ".gte": gte + "-01-01", key + ".lte": lte + "-12-31"}
        return {}

    def _sort_params(self, sort, tid):
        if sort == "最新":
            return {"sort_by": "primary_release_date.desc" if tid == "movie" else "first_air_date.desc"}
        if sort == "高分":
            return {"sort_by": "vote_average.desc", "vote_count_gte": "200"}
        return {}

    def _tmdb_url(self, endpoint, params):
        parts = ["path=" + endpoint]
        for k, v in params.items():
            parts.append("%s=%s" % (k, urllib.parse.quote(str(v), safe="|,.-")))
        return "/api/tmdb.php?" + "&".join(parts)

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = str(tid)
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

        base = self._BASE_PARAMS.get(tid)
        if not base:
            return result

        endpoint = base["endpoint"]
        params = dict(base["params"])

        # 类型
        typ = str(extend.get("type") or extend.get("class") or "").strip()
        if typ and typ != "全部" and typ in self.TYPE_PARAMS.get(tid, {}):
            tp = self.TYPE_PARAMS[tid][typ]
            if "endpoint" in tp:
                endpoint = tp["endpoint"]
            params.update({k: v for k, v in tp.items() if k != "endpoint"})

        # 地区
        area = str(extend.get("area") or "").strip()
        if area and area != "全部" and area in self.AREA_PARAMS:
            params.update(self.AREA_PARAMS[area])

        # 年份
        year = str(extend.get("year") or "").strip()
        if year:
            params.update(self._year_params(year, tid))

        # 排序
        sort = str(extend.get("sort") or "").strip()
        if sort:
            params.update(self._sort_params(sort, tid))

        params["page"] = str(page)

        try:
            data = self._get_json(self._tmdb_url(endpoint, params))
            rows = data.get("results") or []
            items = []
            seen = set()
            for r in rows:
                if not isinstance(r, dict):
                    continue
                name = r.get("title") or r.get("name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                poster = r.get("poster_path") or ""
                pic = ("https://image.tmdb.org/t/p/w342" + poster) if poster else self.DEFAULT_PIC
                yr = (r.get("release_date") or r.get("first_air_date") or "")[:4]
                score = r.get("vote_average") or 0
                remark = " ".join([x for x in (yr, "%.1f分" % score) if x and x != "0.0分"])
                items.append({
                    "vod_id": self._encode_vid(name, "movie" if endpoint == "discover/movie" else "tv"),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })
            result["list"] = items
            result["limit"] = len(items)
            result["total"] = data.get("total_results") or len(items)
            tp = data.get("total_pages")
            result["pagecount"] = int(tp) if tp else page
        except Exception:
            pass
        return result

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key)

    def _do_search(self, key):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}
        if not key:
            return result
        try:
            rows = self._search(key)
            items = []
            seen = set()
            for r in rows:
                name = r.get("name") or ""
                if not name or name in seen:
                    continue
                seen.add(name)
                remark = r.get("remarks") or ""
                if not remark:
                    remark = " ".join([x for x in (str(r.get("type") or ""),
                                                   str(r.get("year") or ""),
                                                   str(r.get("area") or "")) if x])
                items.append({
                    "vod_id": self._encode_vid(name, "auto"),
                    "vod_name": name,
                    "vod_pic": r.get("pic") or self.DEFAULT_PIC,
                    "vod_remarks": remark,
                })
            # 精确匹配片名优先 (避免"原著解读之《庆余年》"排在"庆余年"前)
            k = self._norm(key)
            items.sort(key=lambda x: 0 if self._norm(x.get("vod_name")) == k else 1)
            result["list"] = items
            result["limit"] = len(items)
            result["total"] = len(items)
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

        title, _mtype = self._decode_vid(vid)
        if not title:
            title = vid

        # 按片名搜索站点采集库, 每源选最佳匹配
        rows = self._select_best_rows(title, self._search(title))
        if not rows:
            return result

        details = []
        for row in rows:
            d = self._detail(row.get("source"), row.get("id"))
            if d:
                details.append(d)

        if not details:
            return result

        first = details[0]
        content = first.get("content") or ""
        vod = {
            "vod_id": vid,
            "vod_name": first.get("name") or title,
            "vod_pic": first.get("pic") or self.DEFAULT_PIC,
            "vod_year": str(first.get("year") or ""),
            "vod_area": first.get("area") or "",
            "vod_type": first.get("type") or "",
            "vod_director": first.get("director") or "",
            "vod_actor": first.get("actor") or "",
            "vod_remarks": first.get("remarks") or "",
            "vod_content": self.WX_TEXT + (("\n\n" + content) if content else ""),
        }

        from_arr, url_arr = self._aggregate_plays(details)
        if from_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)

        result["list"] = [vod]
        return result

    def _uniq_label(self, label, used):
        if label in used:
            used[label] += 1
            return "%s%d" % (label, used[label])
        used[label] = 1
        return label

    @staticmethod
    def _clean_ep_name(name):
        """去掉集名里的 $ # 分隔符, 避免破坏 TVBox 的播放串格式"""
        return str(name or "").replace("$", " ").replace("#", " ").strip()

    @staticmethod
    def _clean_ep_url(url):
        """去掉播放地址里的 # (fragment), 避免被 TVBox 当作集数分隔符"""
        return str(url or "").split("#", 1)[0].strip()

    def _aggregate_plays(self, details):
        """把多采集源 -> 多线路 (from_arr / url_arr)"""
        from_arr = []
        url_arr = []
        used = {}
        for det in details:
            if not isinstance(det, dict):
                continue
            src_name = det.get("source_name") or det.get("source") or "线路"
            groups = det.get("episodes") or []
            if not isinstance(groups, list) or not groups:
                continue
            # 单组: 线路名用源名; 多组: 源名·组名
            for grp in groups:
                if not isinstance(grp, dict):
                    continue
                gname = grp.get("group") or ""
                eps = grp.get("episodes") or []
                lines = []
                for i, ep in enumerate(eps):
                    if not isinstance(ep, dict):
                        continue
                    url = self._clean_ep_url(ep.get("url"))
                    if not url:
                        continue
                    name = self._clean_ep_name(ep.get("name")) or ("第%d集" % (i + 1))
                    lines.append("%s$%s" % (name, url))
                if not lines:
                    continue
                if len(groups) <= 1:
                    label = self._uniq_label(src_name, used)
                else:
                    label = self._uniq_label(
                        src_name + (("·" + gname) if gname else ""), used)
                from_arr.append(label)
                url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        url = id or ""
        if not url:
            return {"parse": 1, "url": "", "header": ""}
        headers = json.dumps({
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
        })
        # m3u8/mp4 直链: 直接交给 TVBox 播放
        if ".m3u8" in url or ".mp4" in url:
            return {
                "parse": 0,
                "url": url,
                "header": headers,
                "playUrl": "",
                "subtitle": "",
            }
        # 官方网页 (腾讯/优酷/B站) 或需解析短链: 交 TVBox 解析
        return {
            "parse": 1,
            "url": url,
            "header": headers,
            "playUrl": "",
            "subtitle": "",
        }

    def destroy(self):
        pass
