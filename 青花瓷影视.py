# -*- coding: utf-8 -*-
"""
青花瓷影视（https://www.cj1nym.com/）OK影视 / TVBox / FongMi 系 Python 蜘蛛

设计说明（重要）：
1. 全程只用 Python 标准库（json / re / urllib / hashlib / socket / uuid），
   顶层不 import requests、bs4、cryptography，宿主缺第三方库也不会加载失败。
2. 分类、筛选、搜索、详情、剧集地址都优先走站点自己的 /api/mw-movie JSON 接口
   （签名算法见 _api_sign），页面 RSC 数据只作为兜底：
       /anonymous/get/filer/type             全部分类
       /anonymous/v1/get/filer/list           各分类的筛选字典
       /anonymous/video/list                  分类列表（支持类型/地区/年份/语言过滤）
       /anonymous/video/searchByWordPageable  精确搜索
       /anonymous/video/detail                详情与剧集表
3. 播放入口：播放页的 RSC 里 playUrl 为 null，真实流地址由 /anonymous/v2/video/episode/url
   返回；CDN 对请求头敏感且拒绝同一地址被重复请求，因此默认把直链包成壳的本地代理
   地址，由脚本自己控制请求头（localProxy）。接口异常时再从播放页找直链，最后才
   parse=1 交给壳解析，不会抛异常。
4. 类型细化：电影显示「科幻片 / 武侠片 / 历史片 / 文艺片…」，电视剧显示
   「古装 / 都市 / 谍战 / 家庭…」；站点字典没有的标签用本地二次筛选实现。
   影片简介统一附加微信公众号「源力软件汇」。
5. 本站登录/校验用到极验（geetest），但公共页面与上述 JSON 接口未登录可访问；
   若被拦截，可注入 Cookie：改本文件里的 USER_COOKIE，或在本文件同目录放一个
   qinghuaci_cookie.txt（一行，不带 "Cookie:" 前缀）。
6. 每个入口出错时返回一张可读的“错误卡片”，而不是把异常抛给壳（壳会显示空列表）。
"""

import hashlib
import json
import os
import re
import socket
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------

BASE = "https://www.cj1nym.com"          # www 域名（手机 UA 会 301 到 m.，内容一致）

UA = ("Mozilla/5.0 (Linux; Android 12; BRP-AN80) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

# 交给壳播放器用的请求头（沙箱实测：CDN 对 urllib 默认 UA／不带 UA 的请求一律 403；
# 带播放器风格 UA 的成功率明显更高）
PLAYER_UA = ("ExoPlayerLib/2.18.6 (Linux;Android 12) ExoPlayerLib/2.18.6")
PLAYER_REFERER = "https://www.cj1nym.com/"
PLAY_PROBE_RANGE = "bytes=0-200"      # 实测带 Range 的请求命中可用节点的比例最高
MEDIA_RANGE = "bytes=0-"              # 取整段（m3u8 全文／分片）时用开区间 Range，避免被截断
MEDIA_CACHE_MB = 40                   # 取流缓存上限：同一地址只向上游请求一次（真机复取会被 CDN 403）
BUILD = "V7-filter"                 # 构建标记，写进诊断日志便于核对壳内装的是哪一版
# 真机实测：CDN 拒同一地址的第二次请求；各节点对 Range/Referer 要求不一致 → 播放不预试拉、请求头候选逐个试（见 _media_variants）。
PLAY_VIA_LOCAL_PROXY = True           # 走本地代理：请求头（含 Range）由脚本控制，且播放器的请求就是这条地址的第一次请求
MEDIA_ROUNDS = 2                      # 取流候选头轮数：每轮把候选头各试一遍，第二轮反序换节点
MEDIA_RETRY_WAIT = 0.8                # 两轮之间停顿（秒）
LOCAL_FETCH_DEADLINE = 10             # 代理单次取流预算（秒），失败后还有重取新地址的机会
M3U8_ROUNDS = 1                       # 播放列表只跑一轮候选头：全被拒就直接重取新地址（重试同一地址没意义，只会拖慢开播）

# 允许代理的域名后缀（只代理本站 CDN，避免变成开放代理）
PROXY_HOST_SUFFIXES = ("blbtgg.com", "kqgfbs.com", "cj1nym.com", "wxojcopfw.com", "3688baihuo.com")

# 诊断日志：脚本会往下面第一个能写的路径追加播放记录（手机上用 MT管理器 就能看，
# 或直接把日志内容发给我）。写不进去就静默跳过，不影响播放。
LOG_CANDIDATES = (
    "/storage/emulated/0/Download/qinghuaci_play.log",
    "/sdcard/Download/qinghuaci_play.log",
    "/sdcard/qinghuaci_play.log",
    "/storage/emulated/0/qinghuaci_play.log",
)

# 接口取不到分类时的兜底（正常情况下运行时从 /anonymous/get/filer/type 动态取全部分类）
CLASSES = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
    {"type_id": "88", "type_name": "短剧"},
    {"type_id": "7", "type_name": "体育直播"},
]

# 影片简介末尾统一附加信息
WECHAT_NAME = "源力软件汇"
WECHAT_LINE = "\n\n【微信公众号】%s" % WECHAT_NAME

PAGE_SIZE = 40                     # 分类页每页条数（站点接口 pageSize 最大 100）
LOCAL_PREFIX = "local:"            # 站点筛选字典没有的类型走本地二次筛选
LOCAL_SCAN_PAGES = 5               # 本地细化最多扫描多少页（每页 100 条，兼顾冷门类型与等待时间）
LOCAL_SCAN_TARGET = 20             # 命中足够条数即停止扫描

# 细化类型：站点筛选字典之外的常见标签（详情页/片库里确实存在，补充进筛选菜单）
EXTRA_TYPES = {
    "1": ["武侠", "历史", "文艺", "传记", "纪录片", "古装", "家庭", "悬疑", "歌舞", "运动", "短片"],
    "2": ["都市", "谍战", "悬疑", "爱情", "武侠", "科幻", "传记", "运动", "西部"],
    "3": ["真人秀", "音乐", "脱口秀", "竞技", "美食"],
    "4": ["热血", "科幻", "冒险", "运动", "战斗"],
    "88": ["逆袭", "甜宠", "虐恋", "穿越", "重生", "武侠"],
}

# 站点自带 JSON 接口（网页端 axios baseURL=/api + 服务名前缀 /mw-movie）
API_BASE = BASE + "/api"
CLIENT_TYPE = "3"                      # 网页端固定下发 client-type: 3
API_SIGN_KEY = "cb808529bae6b6be45ecfab29a4889bc"   # 网页端签名密钥，等价于 requestUseSign 的 signKey

USER_COOKIE = ""                       # 需要时把整条 Cookie 贴在这里
COOKIE_FILE = "qinghuaci_cookie.txt"   # 或放在脚本同目录，一行，不带 "Cookie:" 前缀
TIMEOUT = 20                           # 单次请求超时（秒）
RETRY = 2                              # 单个 URL 的请求次数

# 标准 py 蜘蛛基类；宿主里没有 base.spider 时退化为普通 object（沙箱自测用）
try:
    from base.spider import Spider as _BaseSpider          # noqa
except Exception:
    try:
        from spider import Spider as _BaseSpider           # noqa
    except Exception:
        class _BaseSpider(object):
            pass

# ---------------------------------------------------------------------------
# 解析用的小工具
# ---------------------------------------------------------------------------

# 匹配 self.__next_f.push([1,"..."]) 里那个 JSON 字符串
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\s*\]\)', re.S)
# 可能带 JSON 数组/对象的数据键
_DATA_KEY_RE = re.compile(
    r'"(?:list|data|rows|records|videoList|searchList|items|episodeList)"\s*:\s*[\[{]')
# 播放地址候选
_MEDIA_RE = re.compile(r'https?://[^"\'<>\\\s]+?\.(?:m3u8|mp4)(?:\?[^"\'<>\\\s]*)?')


class Spider(_BaseSpider):
    """青花瓷影视 py 源"""

    # -- 生命周期 ---------------------------------------------------------

    def init(self, extend=""):
        self.extend = extend or ""
        self.header = self._build_header()
        self._seen = {}          # 分类跨页去重：{tid: {"pg": 页码, "ids": set()}}
        self._media_hdr_idx = None   # 取流命中过的请求头组合下标（同会话内优先复用）
        self._cache = {}             # 取流结果缓存：url -> (bytes, contentType)
        self._cache_bytes = 0
        self._last_ep = None         # (vid, nid)：播放列表失效时据此向接口重取新地址
        self._log("引擎装载 构建=%s" % BUILD)
        print("============ 青花瓷影视 spider init ============")

    def getName(self):
        return "青花瓷影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _ensure(self):
        """壳（或沙箱）可能没调用 init，这里兜底初始化。"""
        if not getattr(self, "header", None):
            self.init(getattr(self, "extend", "") or "")

    # -- 请求 -------------------------------------------------------------

    def _cookie(self):
        if USER_COOKIE.strip():
            return USER_COOKIE.strip()
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        for p in (os.path.join(here, COOKIE_FILE), COOKIE_FILE):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read().strip()
                if txt:
                    return txt[7:].strip() if txt.lower().startswith("cookie:") else txt
            except Exception:
                pass
        return ""

    def _build_header(self):
        h = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": BASE + "/",
        }
        ck = self._cookie()
        if ck:
            h["Cookie"] = ck
        return h

    def _http(self, url, referer=None):
        """最简 HTTP 取文本，纯标准库，失败重试。"""
        self._ensure()
        hdrs = dict(self.header)
        if referer:
            hdrs["Referer"] = referer
        err = None
        for _ in range(RETRY):
            try:
                req = urllib.request.Request(url, headers=hdrs)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    raw = resp.read()
                for enc in ("utf-8", "gbk"):
                    try:
                        return raw.decode(enc)
                    except Exception:
                        continue
                return raw.decode("utf-8", "replace")
            except Exception as e:      # 网络/HTTP 错误统一在这里收口
                err = e
                time.sleep(0.8)
        raise err if err else RuntimeError("请求失败: " + url)

    # -- 官方 JSON 接口（签名见说明文档） --------------------------------

    def _api_sign(self, params, ts):
        """接口签名：sha1(md5_hex("<参数按 key 排序拼 k=v&…>&key=<signKey>&t=<毫秒>"))。
        与网页端 88773 模块的 requestUseSign 等价，纯标准库实现。"""
        items = ["%s=%s" % (k, params[k]) for k in sorted(params)
                 if params[k] not in (None, "")]
        raw = "&".join(items)
        if raw:
            raw += "&"
        raw += "key=%s&t=%s" % (API_SIGN_KEY, ts)
        inner = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return hashlib.sha1(inner.encode("utf-8")).hexdigest()

    def _api(self, path, params=None):
        """调用站点自己的 /api/mw-movie 接口，自动带上签名头。"""
        self._ensure()
        params = {k: str(v) for k, v in (params or {}).items()}
        ts = int(time.time() * 1000)
        url = API_BASE + path + "?" + urllib.parse.urlencode(params)
        hdrs = dict(self.header)
        hdrs.update({
            "Accept": "application/json, text/plain, */*",
            "client-type": CLIENT_TYPE,
            "t": str(ts),
            "sign": self._api_sign(params, ts),
            "deviceId": getattr(self, "_deviceId", "") or str(uuid.uuid4()),
            "authorization": "",
        })
        self._deviceId = hdrs["deviceId"]
        err = None
        for _ in range(RETRY):
            try:
                req = urllib.request.Request(url, headers=hdrs)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    return json.loads(resp.read().decode("utf-8", "replace"))
            except Exception as e:
                err = e
                time.sleep(0.6)
        raise err if err else RuntimeError("接口请求失败: " + url)

    @staticmethod
    def _is_site_host(url):
        """地址是否属于本站域名（只有本站地址才需要带 Referer）。"""
        try:
            host = (urllib.parse.urlparse(url).hostname or "").lower()
        except Exception:
            return False
        return bool(host) and (host == "cj1nym.com" or host.endswith(".cj1nym.com"))

    def _play_header(self, url=""):
        """交给壳播放器用的请求头：默认只带 UA，地址属于本站域名时才附站点 Referer。"""
        h = {"User-Agent": PLAYER_UA}
        if url and self._is_site_host(url):
            h["Referer"] = PLAYER_REFERER
        return h

    def _media_variants(self, url):
        """取上游流地址的请求头候选（按优先级排列，逐个试，命中即用）。"""
        ua = PLAYER_UA
        cand = [
            {"User-Agent": ua, "Range": MEDIA_RANGE},
            {"User-Agent": ua, "Range": MEDIA_RANGE, "Referer": PLAYER_REFERER},
            {"User-Agent": ua},
            {"User-Agent": ua, "Referer": PLAYER_REFERER},
            {"User-Agent": ua, "Range": PLAY_PROBE_RANGE, "Referer": PLAYER_REFERER},
        ]
        out, seen = [], set()
        for h in cand:
            k = tuple(sorted(h.items()))
            if k in seen:
                continue
            seen.add(k)
            out.append(h)
        return out

    def _log(self, msg):
        """把一条诊断记录追加到手机上第一个可写的日志文件（写不了就算了）。"""
        line = "%s | %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
        for path in LOG_CANDIDATES:
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line)
                return
            except Exception:
                continue

    # -- 取流缓存：同一地址只向上游请求一次 -------------------------------

    def _cache_get(self, url):
        try:
            c = getattr(self, "_cache", None)
            if c and url in c:
                v = c.pop(url)
                c[url] = v                  # 触碰成最新（LRU）
                return v
        except Exception:
            pass
        return None

    def _cache_put(self, url, data, ctype):
        try:
            if not hasattr(self, "_cache"):
                self._cache, self._cache_bytes = {}, 0
            if isinstance(data, str):
                data = data.encode("utf-8", "replace")
            data = bytes(data)
            limit = MEDIA_CACHE_MB * 1024 * 1024
            if not data or len(data) > limit:
                return
            old = self._cache.pop(url, None)
            if old:
                self._cache_bytes -= len(old[0])
            self._cache[url] = (data, ctype or "")
            self._cache_bytes += len(data)
            while self._cache_bytes > limit and len(self._cache) > 1:
                k, v = next(iter(self._cache.items()))
                if k == url:
                    break
                self._cache.pop(k, None)
                self._cache_bytes -= len(v[0])
        except Exception:
            pass

    def _cached_fetch(self, url, deadline=None, rounds=None):
        """取流（先查缓存），返回 (data, ctype, err, 明细, 来源地址)；同一地址只向上游请求一次。"""
        hit = self._cache_get(url)
        if hit is not None:
            return hit[0], hit[1], "", "缓存命中", url
        data, ctype, err, info = self._fetch_media(url, deadline=deadline, rounds=rounds)
        if data:
            self._cache_put(url, data, ctype)
            return data, ctype, "", info, url
        return b"", "", err, info, url

    def _refresh_play_url(self, deadline=None):
        """向站点接口重取一条可用的播放地址（播放列表被拒或已失效时的兜底）。"""
        ep = getattr(self, "_last_ep", None)
        if not ep:
            return None
        try:
            data = self._api("/mw-movie/anonymous/v2/video/episode/url",
                             {"clientType": CLIENT_TYPE, "id": ep[0], "nid": ep[1]})
        except Exception as e:
            self._log("重取播放地址失败: %s" % e)
            return None
        lst = [x for x in (((data or {}).get("data") or {}).get("list") or []) if x.get("url")]

        def _rk(x):
            try:
                return int(x.get("resolution") or 0)
            except Exception:
                return 0

        for x in sorted(lst, key=_rk, reverse=True)[:3]:
            u = str(x["url"]).replace("\\/", "/")
            d, ct, err, info = self._fetch_media(u, deadline=deadline, rounds=1)
            if d:
                self._cache_put(u, d, ct)
                return (u, d, ct, info)
        return None

    # -- RSC 数据流解析 ---------------------------------------------------

    def _payload(self, html_text):
        """把页面里 self.__next_f.push 的片段拼成一段 RSC 文本。"""
        parts = []
        for m in _PUSH_RE.finditer(html_text or ""):
            try:
                parts.append(json.loads(m.group(1)))
            except Exception:
                continue
        if parts:
            return "".join(parts)
        return html_text or ""          # 兜底：没有 push 片段就用整页文本

    @staticmethod
    def _value_at(text, idx):
        """从 text[idx]（应为 { 或 [）开始，按括号配对取出一个 JSON 值。"""
        if idx < 0 or idx >= len(text) or text[idx] not in "{[":
            return None
        depth = 0
        in_str = False
        esc = False
        for i in range(idx, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in "{[":
                    depth += 1
                elif c in "}]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[idx:i + 1])
                        except Exception:
                            return None
        return None

    def _json_find(self, text, key):
        """取 "key": {...} / "key": [...] 里的那个值。"""
        if not text:
            return None
        for m in re.finditer(r'"%s"\s*:\s*' % re.escape(key), text):
            v = self._value_at(text, m.end())
            if isinstance(v, (dict, list)):
                return v
        return None

    def _walk_items(self, val, out=None, limit=300):
        """递归收紧成一个“条目字典”的列表（认 vodId 字段）。"""
        if out is None:
            out = []
        if len(out) >= limit:
            return out
        if isinstance(val, dict):
            if val.get("vodId") is not None:
                out.append(val)
                return out
            for k in ("list", "data", "rows", "records", "items"):
                if k in val:
                    self._walk_items(val[k], out, limit)
        elif isinstance(val, list):
            for it in val:
                self._walk_items(it, out, limit)
                if len(out) >= limit:
                    break
        return out

    def _collect_items(self, text, limit=300):
        """兜底：扫描整段 RSC 文本里所有像片单的数组。"""
        items = []
        seen = set()
        for m in _DATA_KEY_RE.finditer(text or ""):
            val = self._value_at(text, m.end() - 1)
            for it in self._walk_items(val, [], limit):
                vid = str(it.get("vodId"))
                if vid in seen:
                    continue
                seen.add(vid)
                items.append(it)
                if len(items) >= limit:
                    return items
        return items

    # -- 分类 / 筛选 / 文本整形 --------------------------------------------

    @staticmethod
    def _to_int(v, default=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _api_data(self, path, params=None):
        """取接口 data 字段；失败返回空值，不把异常抛给壳。"""
        try:
            d = self._api(path, params)
            if isinstance(d, dict) and d.get("code") in (200, 0, None):
                data = d.get("data")
                if isinstance(data, (dict, list)):
                    return data
        except Exception:
            pass
        return {}

    def _classes(self):
        """从站点接口取全部分类（含体育直播），失败时用内置列表兜底。"""
        cached = getattr(self, "_classes_cache", None)
        if cached:
            return [dict(c) for c in cached]
        raw = self._api_data("/mw-movie/anonymous/get/filer/type")
        arr = raw if isinstance(raw, list) else (raw.get("list") or [])
        out = []
        for it in arr:
            if not isinstance(it, dict):
                continue
            tid = str(it.get("typeId") or "").strip()
            name = str(it.get("typeName") or "").strip()
            if tid and name:
                out.append({"type_id": tid, "type_name": name})
        if not out:
            out = [dict(c) for c in CLASSES]
        self._classes_cache = out
        return [dict(c) for c in out]

    def _filter_options(self, tid, cfg):
        """把站点筛选字典转成 TVBox 的 filters 结构，并补充细化类型。"""
        cfg = cfg if isinstance(cfg, dict) else {}

        def texts(key):
            out = []
            for x in (cfg.get(key) or []):
                if not isinstance(x, dict):
                    continue
                t = str(x.get("itemText") or "").strip()
                if t and t not in out:
                    out.append(t)
            return out

        supported = texts("typeList") + texts("plotList")
        # 电影用站点的 typeList（喜剧/动作/科幻…），其它分类用 plotList（古装/家庭/历史…）
        primary = texts("typeList") if str(tid) == "1" else texts("plotList")
        if not primary:
            primary = texts("typeList") or texts("plotList")
        for t in EXTRA_TYPES.get(str(tid), []):
            if t and t not in primary:
                primary.append(t)

        values = [{"v": "", "n": "全部"}]
        for t in primary:
            v = t if t in supported else (LOCAL_PREFIX + t)
            # 电影显示成「科幻片 / 武侠片 / 历史片」，电视剧保持「古装 / 都市 / 谍战」
            n = (t if (t.endswith("片") or t in ("其他", "其它"))
                 else t + "片") if str(tid) == "1" else t
            values.append({"v": v, "n": n})
        filters = [{"key": "v_class", "name": "类型", "value": values}]

        for key, cfgkey, label in (("area", "districtList", "地区"),
                                   ("year", "yearList", "年份"),
                                   ("lang", "languageList", "语言")):
            vals = [{"v": "", "n": "全部"}]
            for x in (cfg.get(cfgkey) or []):
                if not isinstance(x, dict):
                    continue
                t = str(x.get("itemText") or "").strip()
                if t:
                    vals.append({"v": t, "n": t})
            if len(vals) > 1:
                filters.append({"key": key, "name": label, "value": vals})

        filters.append({"key": "sortBy", "name": "排序", "value": [
            {"v": "1", "n": "默认"}, {"v": "2", "n": "最近更新"},
            {"v": "3", "n": "人气优先"}, {"v": "4", "n": "评分优先"},
        ]})
        return filters

    def _filters(self):
        """分类 -> 筛选菜单，接口数据缓存到本次会话，避免每次点分类都重取。"""
        cached = getattr(self, "_filters_cache", None)
        if cached:
            return cached
        raw = self._api_data("/mw-movie/anonymous/v1/get/filer/list")
        raw = raw if isinstance(raw, dict) else {}
        out = {}
        for c in self._classes():
            tid = c.get("type_id")
            out[tid] = [] if tid == "7" else self._filter_options(tid, raw.get(tid))
        self._filters_cache = out
        return out

    @staticmethod
    def _parse_extend(extend):
        """兼容 TVBox 的 'k=v,k2=v2'、URL 编码和 JSON 三种 extend 形式。"""
        if not extend:
            return {}
        if isinstance(extend, dict):
            d = dict(extend)
        else:
            s = str(extend).strip()
            if not s:
                return {}
            d = {}
            if s.startswith("{"):
                try:
                    v = json.loads(s)
                    if isinstance(v, dict):
                        d = v
                except Exception:
                    d = {}
            else:
                for part in re.split(r"[,，&;]", s):
                    if "=" not in part:
                        continue
                    k, v = part.split("=", 1)
                    k = urllib.parse.unquote(k.strip())
                    v = urllib.parse.unquote(v.strip())
                    if k and v:
                        d[k] = v
        out = {}
        for k, v in d.items():
            k, v = str(k).strip(), str(v).strip()
            if k and v and v not in ("0", "全部", "undefined", "null"):
                out[k] = v
        return out

    @staticmethod
    def _clean_text(s):
        if not s:
            return ""
        s = str(s).replace("\\/", "/")
        s = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", s)
        s = re.sub(r"(?s)<[^>]+>", "", s)
        for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                     ("&gt;", ">"), ("&quot;", '"')):
            s = s.replace(a, b)
        s = re.sub(r"[ \t]+\n", "\n", s)
        return re.sub(r"\n{3,}", "\n\n", s).strip()

    def _with_wechat(self, text):
        text = self._clean_text(text)
        if WECHAT_NAME in text:
            return text
        return (text + WECHAT_LINE).strip()

    @staticmethod
    def _nice_type(raw, tid=None):
        """细化类型显示：电影补「片」字（科幻片/武侠片…），电视剧保持原标签。"""
        parts = [x.strip() for x in re.split(r"[,，/、]", str(raw or "")) if x.strip()]
        if not parts:
            return ""
        movie = str(tid or "") == "1"
        out = []
        for p in parts:
            if movie and not p.endswith("片") and p not in ("其他", "其它"):
                p += "片"
            out.append(p)
        return ",".join(out)

    def _local_filter_items(self, tid, tag):
        """站点接口不支持的细化类型（武侠/历史/文艺/都市/谍战…）在本地二次筛选。"""
        key = (str(tid), str(tag))
        cache = getattr(self, "_local_filter_cache", None)
        if cache is None:
            cache = self._local_filter_cache = {}
        if key in cache:
            return cache[key]
        out, seen = [], set()
        for pg in range(1, LOCAL_SCAN_PAGES + 1):
            d = self._api_data("/mw-movie/anonymous/video/list", {
                "clientType": CLIENT_TYPE, "pageNum": str(pg),
                "pageSize": "100", "type1": str(tid)})
            lst = d.get("list") or [] if isinstance(d, dict) else []
            if not lst:
                break
            for it in lst:
                cl = str(it.get("vodClass") or "")
                if tag not in cl:
                    continue
                vid = str(it.get("vodId") or "")
                if vid and vid in seen:
                    continue
                if vid:
                    seen.add(vid)
                out.append(it)
            if len(out) >= LOCAL_SCAN_TARGET:
                break
        # 片库标签里没有「都市 / 谍战 / 文艺」这类叫法时用片名搜索补充相关结果
        if len(out) < 10:
            try:
                d = self._api_data("/mw-movie/anonymous/video/searchByWordPageable", {
                    "keyword": tag, "pageNum": "1", "pageSize": "100"})
                for it in (d.get("list") or [] if isinstance(d, dict) else []):
                    if str(it.get("typeId1") or "") != str(tid):
                        continue
                    vid = str(it.get("vodId") or "")
                    if vid and vid in seen:
                        continue
                    if vid:
                        seen.add(vid)
                    out.append(it)
                    if len(out) >= LOCAL_SCAN_TARGET:
                        break
            except Exception:
                pass
        cache[key] = out
        return out

    @staticmethod
    def _match_filters(it, f):
        """本地细化时再套用地区/年份/语言条件。"""
        if f.get("area") and f["area"] not in str(it.get("vodArea") or ""):
            return False
        if f.get("lang") and f["lang"] not in str(it.get("vodLang") or ""):
            return False
        year = f.get("year") or ""
        if year:
            y = str(it.get("vodYear") or it.get("vodPubdate") or "")[:4]
            if "~" in year:
                try:
                    hi, lo = year.split("~", 1)
                    if not (int(lo[:4]) <= int(y) <= int(hi[:4])):
                        return False
                except Exception:
                    return False
            elif y != year:
                return False
        return True

    # -- 数据整形 ---------------------------------------------------------

    @staticmethod
    def _pic(url):
        """封面补绝对地址，兼容懒加载字段。"""
        if not url:
            return ""
        url = str(url).strip().replace("\\/", "/")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return BASE + url
        return url

    def _video(self, it, tid=None):
        """把站点条目字典转成 TVBox 的 video 结构。"""
        it = it if isinstance(it, dict) else {}
        vid = it.get("vodId")
        pic = self._pic(it.get("vodPic") or it.get("vodPicSlide") or it.get("bgImage"))
        remarks = (it.get("vodRemarks") or "").strip()
        if not remarks:
            ver = (it.get("vodVersion") or "").strip()
            serial = (it.get("vodSerial") or "").strip()
            remarks = (ver + (("(" + serial + ")") if serial and serial != "0" else "")).strip()
        main_type = str(tid or it.get("typeId1") or "")
        raw_type = it.get("vodClass") or it.get("typeName") or ""
        vod = {
            "vod_id": str(vid) if vid is not None else "",
            "vod_name": (it.get("vodName") or "").strip(),
            "vod_pic": pic,
            "vod_remarks": remarks,
            "type_id": str(it.get("typeId") or ""),
            "type_name": self._nice_type(raw_type, main_type),
            "vod_year": str(it.get("vodYear") or it.get("vodPubdate") or "")[:4],
            "vod_area": (it.get("vodArea") or "").strip(),
            "vod_actor": (it.get("vodActor") or "").strip(),
            "vod_content": self._with_wechat(it.get("vodBlurb") or it.get("vodContent")),
        }
        director = (it.get("vodDirector") or "").strip()
        if director:
            vod["vod_director"] = director
        score = it.get("vodScore") or it.get("vodDoubanScore")
        if score:
            vod["vod_douban_score"] = str(score)
        return vod

    @staticmethod
    def _card(title, msg):
        """可读的错误卡片：壳里会显示成一条“影片”，而不是空列表。"""
        return {
            "vod_id": "qinghuaci_error",
            "vod_name": "【青花瓷影视】" + title,
            "vod_pic": "",
            "vod_remarks": "提示",
            "type_name": "错误提示",
            "vod_year": "",
            "vod_content": msg,
        }

    # -- 首页 -------------------------------------------------------------

    def homeContent(self, filter=False):
        """全部分类 + 细化筛选菜单（均来自站点接口，接口异常时退回内置数据）。"""
        self._ensure()
        try:
            classes = self._classes()
            filters = self._filters()
        except Exception as e:
            self._log("首页分类/筛选降级: %s" % e)
            classes = [dict(c) for c in CLASSES]
            filters = {}
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        """首页推荐：从 / 的 RSC 数据里合并所有 home*PageData 片单。"""
        self._ensure()
        try:
            text = self._payload(self._http(BASE + "/", referer=BASE + "/"))
            blocks = []
            for m in re.finditer(r'"(home[A-Za-z0-9_]*PageData)"\s*:\s*', text):
                v = self._value_at(text, m.end())
                if isinstance(v, dict) and isinstance(v.get("list"), list):
                    blocks.append(v["list"])
            items = []
            seen = set()
            for blk in blocks:
                for it in blk:
                    vid = str(it.get("vodId"))
                    if vid == "None" or vid in seen:
                        continue
                    seen.add(vid)
                    items.append(it)
                    if len(items) >= 60:      # 首页给 60 条足够铺满
                        break
                if len(items) >= 60:
                    break
            if not items:                      # 首页结构变化时的兜底
                items = self._collect_items(text, 60)
            return {"list": [self._video(x) for x in items]}
        except Exception as e:
            return {"list": [self._card("首页加载失败",
                                        "原因：%s\n站点：%s\n可检查网络或稍后重试。" % (e, BASE))]}

    # -- 分类 -------------------------------------------------------------

    def _dedupe(self, tid, pg, videos):
        """分类跨页去重：只在页码往前走时丢弃上一页出现过的条目。"""
        try:
            page = int(pg)
        except Exception:
            page = 1
        state = self._seen.get(tid)
        old = state["ids"] if (state and page > state.get("pg", 0)) else set()
        out = []
        cur = set(old)
        for v in videos:
            vid = v.get("vod_id")
            if vid and vid in cur:
                continue
            if vid:
                cur.add(vid)
            out.append(v)
        self._seen[tid] = {"pg": page, "ids": cur}
        return out

    def _category_items_html(self, tid, pg):
        """接口异常时退回分类页 RSC 解析，返回 (条目列表, 分页信息)。"""
        url = "%s/vod/show/id/%s/page/%s" % (BASE, tid, pg)
        text = self._payload(self._http(url, referer=BASE + "/"))
        obj = self._json_find(text, "videoList")
        items = (obj or {}).get("list") if isinstance(obj, dict) else None
        if not items:      # 尾页/异常时换成 query 形式再试一次
            alt = "%s/vod/show/id/%s?page=%s" % (BASE, tid, pg)
            text = self._payload(self._http(alt, referer=BASE + "/"))
            obj = self._json_find(text, "videoList")
            items = (obj or {}).get("list") if isinstance(obj, dict) else None
        if not items:
            items = self._collect_items(text, 60)
        return ([x for x in (items or []) if isinstance(x, dict) and x.get("vodId") is not None],
                obj if isinstance(obj, dict) else {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        self._ensure()
        page = self._to_int(pg, 1) or 1
        f = self._parse_extend(extend)
        if str(tid) == "7":
            # 体育直播在站点是独立直播页，不是点播片单，给一张说明卡片而不是空列表
            return {"list": [{
                "vod_id": "sports_live", "vod_name": "体育直播（独立直播页）",
                "vod_pic": "", "vod_remarks": "直播", "type_name": "体育直播",
                "vod_content": "本站体育直播为赛事直播页，请用直播源观看。" + WECHAT_LINE,
            }], "page": page, "pagecount": 1, "limit": 1, "total": 1}
        try:
            vc = f.get("v_class") or ""
            if vc.startswith(LOCAL_PREFIX):
                # 站点筛选字典没有的细化类型：本地按 vodClass 二次筛选并分页
                tag = vc[len(LOCAL_PREFIX):].strip()
                items = [x for x in self._local_filter_items(tid, tag)
                         if self._match_filters(x, f)]
                total = len(items)
                pagecount = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                start = (page - 1) * PAGE_SIZE
                return {
                    "list": [self._video(x, tid) for x in items[start:start + PAGE_SIZE]],
                    "page": page, "pagecount": pagecount,
                    "limit": PAGE_SIZE, "total": total,
                }

            params = {"clientType": CLIENT_TYPE, "pageNum": str(page),
                      "pageSize": str(PAGE_SIZE), "type1": str(tid), "sort": "1"}
            for key in ("v_class", "area", "year", "lang", "sortBy"):
                if f.get(key):
                    params[key] = f[key]
            data = self._api_data("/mw-movie/anonymous/video/list", params)
            items = data.get("list") or [] if isinstance(data, dict) else []
            if not items and not f:    # 接口空数据时再试页面
                items, page_info = self._category_items_html(tid, page)
                data = page_info
            videos = self._dedupe(str(tid), page,
                                  [self._video(x, tid) for x in items if isinstance(x, dict)])
            return {
                "list": videos,
                "page": page,
                "pagecount": self._to_int(data.get("totalPage"), 9999) or 9999,
                "limit": len(videos) or PAGE_SIZE,
                "total": self._to_int(data.get("totalCount"), len(videos)) or len(videos),
            }
        except Exception as e:
            self._log("分类接口失败 tid=%s pg=%s: %s" % (tid, pg, e))
            try:
                items, info = self._category_items_html(tid, page)
                videos = self._dedupe(str(tid), page, [self._video(x, tid) for x in items])
                if videos:
                    return {"list": videos, "page": page,
                            "pagecount": self._to_int(info.get("totalPage"), 1) or 1,
                            "limit": len(videos),
                            "total": self._to_int(info.get("totalCount"), len(videos)) or len(videos)}
            except Exception:
                pass
            return {
                "list": [self._card("分类加载失败", "分类 %s 第 %s 页取不到数据。\n原因：%s" % (tid, pg, e))],
                "page": page, "pagecount": 1, "limit": 1, "total": 1,
            }

    # -- 搜索 -------------------------------------------------------------

    def searchContent(self, key, quick=False, pg="1"):
        """站内搜索：精确分页接口优先，空结果时用模糊接口兜底，可搜任意片名。"""
        self._ensure()
        page = self._to_int(pg, 1) or 1
        key = str(key or "").strip()
        if not key:
            return {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}
        out, seen, info = [], set(), {}
        try:
            d = self._api_data("/mw-movie/anonymous/video/searchByWordPageable", {
                "keyword": key, "pageNum": str(page), "pageSize": "40"})
            info = d if isinstance(d, dict) else {}
            if not out:
                for it in (info.get("list") or []):
                    vid = str(it.get("vodId") or "")
                    if vid and vid not in seen:
                        seen.add(vid)
                        out.append(self._video(it))
        except Exception as e:
            self._log("精确搜索失败: %s" % e)

        if not out and page == 1:
            # 精确接口没命中时再走一次模糊接口（它的结果在 data.result 里）
            try:
                d = self._api_data("/mw-movie/anonymous/video/searchByWord", {
                    "keyword": key, "pageNum": "1", "pageSize": "40"})
                result = d.get("result") or {} if isinstance(d, dict) else {}
                info = result or info
                for it in (result.get("list") or []):
                    vid = str(it.get("vodId") or "")
                    if vid and vid not in seen:
                        seen.add(vid)
                        out.append(self._video(it))
            except Exception as e:
                self._log("模糊搜索失败: %s" % e)

        total = self._to_int(info.get("totalCount"), len(out))
        pagecount = self._to_int(info.get("totalPage"), 1)
        return {
            "list": out, "page": page, "pagecount": pagecount or 1,
            "limit": len(out), "total": total or len(out),
        }

    # -- 详情 -------------------------------------------------------------

    def detailContent(self, ids):
        self._ensure()
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]).strip() if ids else ""
        else:
            vid = str(ids).strip()
        data, text = {}, ""
        try:
            d = self._api_data("/mw-movie/anonymous/video/detail", {"id": vid})
            if isinstance(d, dict) and d.get("vodName"):
                data = d
        except Exception as e:
            self._log("详情接口失败 %s: %s" % (vid, e))
        if not data:
            # 接口异常时用详情页 RSC 兜底
            try:
                text = self._payload(self._http(BASE + "/detail/" + vid, referer=BASE + "/"))
                obj = self._json_find(text, "playListData") or {}
                cand = obj.get("data") if isinstance(obj, dict) else None
                if not isinstance(cand, dict) or not cand.get("vodName"):
                    cand = self._json_find(text, "vodInfo") or {}
                if not cand.get("vodName"):
                    items = self._collect_items(text, 1)
                    cand = items[0] if items else {}
                data = cand if isinstance(cand, dict) else {}
            except Exception:
                data = {}
        if not data.get("vodName"):
            return {"list": [self._card("详情加载失败", "影片 ID：%s\n站点没有返回详情数据。" % vid)]}

        vod = self._video(data, data.get("typeId1"))
        vod["vod_id"] = str(data.get("vodId") or vid)
        vod["vod_content"] = self._with_wechat(data.get("vodContent") or data.get("vodBlurb"))
        vod["vod_director"] = (data.get("vodDirector") or "").strip()
        vod["vod_area"] = (data.get("vodArea") or "").strip()
        vod["vod_lang"] = (data.get("vodLang") or "").strip()
        vod["vod_year"] = str(data.get("vodYear") or data.get("vodPubdate") or "")[:4]

        play_list = []
        for i, e in enumerate(data.get("episodeList") or []):
            if not isinstance(e, dict) or e.get("nid") is None:
                continue
            raw = str(e.get("name") or "").strip()
            name = ("第%s集" % raw) if raw.isdigit() else (raw or ("第%d集" % (i + 1)))
            sid = e.get("sid") or 1
            play_list.append("%s$%s/%s/%s" % (name, vod["vod_id"], sid, e["nid"]))
        if not play_list and text:
            m = re.search(r'"nid"\s*:\s*(\d+)', text)
            if m:
                play_list.append("正片$%s/1/%s" % (vod["vod_id"], m.group(1)))
        vod["vod_play_from"] = "青花瓷"
        if play_list:
            vod["vod_play_url"] = "#".join(play_list)
        else:
            vod["vod_play_url"] = ""
            vod["vod_content"] += "\n\n【提示】没有解析到剧集数据，播放可能不可用。"
        return {"list": [vod]}

    # -- 播放 -------------------------------------------------------------

    # -- 本地代理播放 -----------------------------------------------------

    def _proxy_play_url(self, url):
        """把目标地址包成壳的本地代理地址；拿不到端口或没开代理就直接返回原地址。"""
        if not PLAY_VIA_LOCAL_PROXY:
            return url
        try:
            base = self._proxy_base()
            if not base:
                return url
            return "%s&url=%s" % (base, urllib.parse.quote(url, ""))
        except Exception as e:
            self._log("拼本地代理地址失败: %s" % e)
            return url

    def _proxy_base(self):
        """找壳的本地代理入口（结果只解析一次）：优先基类 getProxyUrl()，否则扫 9978-9998 端口。"""
        memo = getattr(self, "_proxy_cache", None)
        if memo:
            return memo
        for name in ("getProxyUrl", "get_proxy_url"):
            fn = getattr(self, name, None)
            if callable(fn):
                try:
                    v = fn()
                    if v:
                        self._proxy_cache = str(v)
                        return self._proxy_cache
                except Exception:
                    pass
        for port in range(9978, 9999):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/device" % port, timeout=0.4) as resp:
                    resp.read(64)
                self._proxy_cache = "http://127.0.0.1:%d/proxy?do=py" % port
                return self._proxy_cache
            except Exception:
                continue
        self._proxy_cache = "http://127.0.0.1:9978/proxy?do=py"
        return self._proxy_cache

    def _proxy_ok(self, url):
        """只代理本站自己的 CDN／站点地址。"""
        try:
            host = (urllib.parse.urlparse(url).hostname or "").lower()
        except Exception:
            return False
        for suf in PROXY_HOST_SUFFIXES:
            if host == suf or host.endswith("." + suf):
                return True
        return False

    def _fetch_one(self, url, hdrs, deadline=None, chunk=262144, max_rounds=40):
        """发一次上游请求；只回了部分内容（206 且未到结尾）时用开放式 Range 补齐，只在 206 且起点吻合时拼接。"""
        t0 = time.time()
        timeout = 15
        if deadline is not None:
            left = deadline - time.time()
            if left <= 0:
                raise RuntimeError("时间预算用尽")
            timeout = max(3.0, min(15.0, left))
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs),
                                    timeout=timeout) as resp:
            status = resp.getcode()
            ctype = resp.headers.get("Content-Type") or ""
            crange = resp.headers.get("Content-Range") or ""
            data = resp.read()
        total = None
        if crange and "/" in crange:
            try:
                total = int(crange.rsplit("/", 1)[1])
            except Exception:
                total = None
        rounds = 1
        if status == 206 and total and 0 <= len(data) < total:
            off = len(data)
            for _ in range(max_rounds):
                if deadline is not None and time.time() > deadline:
                    break
                h = dict(hdrs)
                h["Range"] = "bytes=%d-" % off
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                                timeout=timeout) as r2:
                        st2 = r2.getcode()
                        cr2 = r2.headers.get("Content-Range") or ""
                        more = r2.read()
                except Exception:
                    break
                start2 = -1
                if " " in cr2 and "-" in cr2:
                    try:
                        start2 = int(cr2.split(" ", 1)[1].split("-", 1)[0])
                    except Exception:
                        start2 = -1
                if st2 != 206 or start2 != off or not more:
                    break
                rounds += 1
                data += more
                off += len(more)
                if off >= total:
                    break
        return data, ctype, "HTTP %s %.1fs %d轮" % (status, time.time() - t0, rounds)

    def _fetch_media(self, url, deadline=None, rounds=None):
        """按候选请求头逐个试拉上游，返回 (bytes, contentType, err, 明细)；命中过的组合记下来供后续分片复用。"""
        variants = self._media_variants(url)
        idx0 = getattr(self, "_media_hdr_idx", None)
        if not (isinstance(idx0, int) and 0 <= idx0 < len(variants)):
            idx0 = None
        order = ([idx0] if idx0 is not None else []) +             [i for i in range(len(variants)) if i != idx0]
        last = ""
        tried = 0
        rnds = MEDIA_ROUNDS if rounds is None else max(1, int(rounds))
        for rd in range(rnds):
            seq = order if rd == 0 else list(reversed(order))   # 第二轮反序，换一批边缘节点再试
            for i in seq:
                if deadline is not None and time.time() > deadline:
                    return b"", "", last or "时间预算用尽", "超时"
                h = variants[i]
                tried += 1
                try:
                    data, ctype, info = self._fetch_one(url, h, deadline)
                except urllib.error.HTTPError as e:
                    last = "HTTP %s" % e.code
                    continue
                except Exception as e:
                    last = str(e)
                    continue
                if data:
                    if i != idx0:
                        self._media_hdr_idx = i
                        self._log("上游命中请求头#%d 第%d轮 (Range=%s Referer=%s) 明细=%s | %s" % (
                            i, rd + 1, h.get("Range") or "-", "有" if h.get("Referer") else "无",
                            info, url[:90]))
                    return data, ctype, "", "%s 头#%d" % (info, i)
            if rd + 1 < rnds:
                time.sleep(MEDIA_RETRY_WAIT)
        return b"", "", last or "请求失败", "失败(试了%d次)" % tried

    def _rewrite_m3u8(self, text, base_url):
        """把 m3u8 的分片／密钥地址改成走本代理（代理前缀与源目录只解析一次）。"""
        t0 = time.time()
        src_dir = base_url.split("?")[0].rsplit("/", 1)[0]
        pre = (self._proxy_base() or "") if PLAY_VIA_LOCAL_PROXY else ""
        quote = urllib.parse.quote
        out = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                out.append("")
                continue
            if line.startswith("#"):
                if 'URI="' in line:
                    head, _, tail = line.partition('URI="')
                    uri, _, rest = tail.partition('"')
                    if uri:
                        line = head + 'URI="' + self._to_absolute(uri, src_dir) + '"' + rest
                out.append(line)
                continue
            u = self._to_absolute(line, src_dir)
            out.append(("%s&url=%s" % (pre, quote(u, ""))) if pre else u)
        n = 0
        for l in out:
            if l and not l.startswith("#"):
                n += 1
        self._log("改写播放列表 %d 条分片 %.2fs" % (n, time.time() - t0))
        return "\n".join(out) + "\n"

    def _to_absolute(self, u, base):
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("/"):
            return urllib.parse.urlparse(base).scheme + "://" + urllib.parse.urlparse(base).netloc + u
        return base.rstrip("/") + "/" + u.lstrip("/")

    def localProxy(self, param):
        """壳的本地代理入口：所有 CDN 请求由脚本自己发并自动重试，抗住 CDN 的随机 403。"""
        try:
            if isinstance(param, dict):
                p = {}
                for k, v in param.items():
                    p[str(k)] = v[0] if isinstance(v, (list, tuple)) and v else str(v)
            else:
                p = {k: v[0] for k, v in urllib.parse.parse_qs(str(param)).items()}
            target = urllib.parse.unquote(p.get("url") or p.get("playUrl") or p.get("u") or "")
            if not target:
                return [400, "text/plain", "缺少 url 参数"]
            if not self._proxy_ok(target):
                return [403, "text/plain", "本代理只处理本站 CDN 地址"]
            is_pl = ".m3u8" in target
            data, ctype, err, info, src = self._cached_fetch(
                target, deadline=time.time() + LOCAL_FETCH_DEADLINE,
                rounds=M3U8_ROUNDS if is_pl else None)
            if not data and is_pl:
                fresh = self._refresh_play_url(               # 地址被拒/失效：向站点重取一条新地址
                    deadline=time.time() + LOCAL_FETCH_DEADLINE)
                if fresh:
                    src, data, ctype = fresh[0], fresh[1], fresh[2]
                    info = "重取新地址"
                    self._cache_put(target, data, ctype)  # 旧地址后续请求也走缓存
                    self._log("播放列表被拒后重取成功 %s" % src[:90])
            if not data:
                self._log("localProxy 上游失败 %s | %s" % (err, target[:110]))
                return [502, "text/plain", "上游请求失败: %s" % err]
            if b"#EXTM3U" in data[:200]:
                rw = getattr(self, "_rw_cache", None)
                if rw is None:
                    rw = self._rw_cache = {}
                text = rw.get(src)
                if text is None:
                    text = self._rewrite_m3u8(data.decode("utf-8", "replace"), src)
                    if len(rw) < 8:
                        rw[src] = text
                    tag = "已改写分片走代理"
                else:
                    tag = "复用已改写结果"
                self._log("localProxy 返回 m3u8（%s, %dB, %s）%s" % (
                    info, len(data), tag, target[:90]))
                # 壳子要五元组：[状态码, Content-Type, 内容, 响应头, 0]（照厂商原版写法，勿改）
                return [200, "application/vnd.apple.mpegurl", text,
                        {"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"}, 0]
            n = getattr(self, "_seg_n", 0) + 1
            self._seg_n = n
            if n <= 3 or not n % 20:
                self._log("localProxy 返回分片 第%d个 %d 字节 %s %s | %s" % (
                    n, len(data), ctype or "-", info, target[:90]))
            return [200, ctype or "application/octet-stream", data,
                    {"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"}, 0]
        except Exception as e:
            self._log("localProxy 异常: %s" % e)
            return [500, "text/plain", "代理异常: %s" % e]

    def playerContent(self, flag, id, vipFlags=None):
        """
        id 形如 "vodId/sid/nid"（详情里拼好的）。

                不试拉：只向接口要地址，把第一条包成本地代理地址交给播放器，由代理发这条地址的第一次请求。
        """
        self._ensure()
        parts = str(id).split("/")
        header = self._play_header()
        vid = parts[0] if parts and parts[0] else ""
        nid = parts[2] if len(parts) >= 3 else ""
        page = ("%s/vod/play/%s/1/%s" % (BASE, vid, nid)) if (vid and nid) else (BASE + "/vod/play")
        self._last_ep = (vid, nid) if (vid and nid) else None   # 播放列表失效时据此重取新地址
        api_err = None
        self._log("=== 播放(构建=%s) vid=%s nid=%s flag=%s UA=%s" % (
            BUILD, vid, nid, flag, header["User-Agent"]))

        if vid and nid:
            try:
                host = urllib.parse.urlparse(API_BASE).hostname
                addrs = socket.getaddrinfo(host, 443)
                self._log("站点接口解析 %s -> %s" % (host, sorted({a[4][0] for a in addrs})[:6]))
            except Exception as e:
                self._log("站点接口解析失败: %s" % e)
            _t_api = time.time()
            try:
                data = self._api("/mw-movie/anonymous/v2/video/episode/url",
                                 {"clientType": CLIENT_TYPE, "id": vid, "nid": nid})
            except Exception as e:
                api_err = e
                data = None
                self._log("接口异常: %s" % e)
            self._log("接口耗时 %.1fs" % (time.time() - _t_api))
            items = ((data or {}).get("data") or {}).get("list") or []
            self._log("接口 code=%s msg=%s 线路=%d" % (
                (data or {}).get("code"), (data or {}).get("msg"), len(items)))
            cands = [x for x in items if x.get("url")]

            def _rank(x):
                try:
                    return int(x.get("resolution") or 0)
                except Exception:
                    return 0
            cands.sort(key=_rank, reverse=True)
            for x in cands[:3]:
                self._log("  备选 %s(%s) %s" % (
                    x.get("resolutionName"), x.get("resolution"),
                    str(x.get("url")).replace("\\/", "/")[:110]))
            if cands:
                # 不试拉：试拉会提前用掉这条地址（CDN 拒同一地址的第二次请求）。
                url = str(cands[0].get("url")).replace("\\/", "/")
                ph = self._play_header(url)
                if PLAY_VIA_LOCAL_PROXY:
                    purl = self._proxy_play_url(url)
                    self._log("交给播放器：本地代理（未试拉）%s" % purl[:110])
                    return {"parse": 0, "playUrl": purl, "url": purl, "header": ph,
                            "headers": ph, "flag": flag or "",
                            "resolutionName": cands[0].get("resolutionName") or ""}
                self._log("交给播放器：直链（未试拉）%s(%s)" % (
                    cands[0].get("resolutionName"), url[:110]))
                return {"parse": 0, "playUrl": url, "url": url, "header": ph, "headers": ph,
                        "flag": flag or "",
                        "resolutionName": cands[0].get("resolutionName") or ""}

        # 兜底：直接在播放页里找直链
        best = ""
        try:
            html_text = self._http(page, referer=BASE + "/")
            payload = self._payload(html_text)
            for m in re.finditer(r'"playUrl"\s*:\s*"(https?:[^"]+)"', payload):
                cand = m.group(1).replace("\\/", "/")
                if cand and cand != "null":
                    best = cand
                    break
            if not best:
                m = _MEDIA_RE.search(html_text) or _MEDIA_RE.search(payload)
                if m:
                    best = m.group(0).replace("\\/", "/")
            if best:
                self._log("页面里找到直链: %s" % best[:110])
                return {"parse": 0, "playUrl": best, "header": header, "headers": header,
                        "url": best, "flag": flag or ""}
        except Exception as e:
            self._log("播放页找直链失败: %s" % e)

        # 都不行：把播放页交给壳自带解析
        msg = "站点接口与页面都没有取到可播直链，已交给壳解析播放页"
        if api_err is not None:
            msg += "；接口错误：%s" % api_err
        self._log("放弃，返回 parse=1 交壳解析")
        page_header = self._play_header(page)
        return {"parse": 1, "playUrl": page, "header": page_header, "headers": page_header,
                "msg": msg}
