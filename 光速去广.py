# coding=utf-8
"""
光速资源（去广告）爬虫
站点: 光速资源 (https://api.guangsuapi.com/api.php/provide/vod/)
模板: 苹果CMS JSON采集接口 + 内置去广告清洗
类型: 综合影视 (电影/电视剧/综艺/动漫/体育/短剧)

分类写法 (与光速资源.py 一致):
  - 36 个内置分类 (电影/电视剧/体育/综艺/动漫/短剧), SKIP_IDS 可隐藏
  - USE_LOCAL_CLASSES=False 时优先用采集接口实时分类

去广告说明 (重要):
  - 实测光速 m3u8 播放列表层面干净: 无 #EXT-X-DISCONTINUITY 广告块、
    无外部广告域名、TS 顺序编号、PCR/PTS 时间轴连续
  - 其广告是转码时物理拼接进视频流的 (如片头约 62 秒"京东健康"贴片、
    画面烧录的分销水印), 播放列表层面无任何特征, 程序无法自动识别
  - 因此提供三条线路:
      光速直连  : 原始 m3u8, 行为与光速资源.py 完全一致
      光速纯净  : 本地代理清洗播放列表 (防站点未来改为列表注入广告),
                  并统一改写绝对地址/加密KEY地址
      光速跳片头: 在纯净基础上按固定时长跳过片头贴片 (默认 62 秒,
                  可改 SKIP_OPENING_SEC; 无贴片的视频请勿用本线路, 会跳过正片)

清洗引擎 (移植自索尼去广.py, 保证 TVBox 正常播放):
  - 强信号: 块内 TS 全部命中广告关键字 / 广告注释标记同块或标记下一块
  - 弱信号: 根绝对路径 TS 混排 / 跨注册域名块 (删除占比超 30% 放弃)
  - 兜底: TS 计数器最长递增链
  - 全部片段/加密 KEY/MAP 相对地址改写绝对地址 (AES KEY 改写为绝对地址,
    否则经本地代理后播放器会解错相对路径导致解密失败)
  - 重算 #EXT-X-TARGETDURATION, 补全 #EXTM3U/#EXT-X-VERSION/#EXT-X-ENDLIST
  - 多码率 master 自动选最高带宽; 任一环节失败回退原始播放列表

支持: 首页, 分类, 搜索, 详情, 播放 (五接口齐全)
"""

import sys
import re
import json
import requests
from urllib.parse import urljoin, urlparse, quote, unquote

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    # ---------- 站点常量 ----------
    SITE_URL = "https://api.guangsuapi.com"
    API = "https://api.guangsuapi.com/api.php/provide/vod/"

    # ---------- 播放线路 ----------
    FLAG_RAW = "光速直连"
    FLAG_CLEAN = "光速纯净"
    FLAG_SKIP = "光速跳片头"
    # 跳片头线路: 跳过的片头贴片秒数 (实测"京东健康"贴片约 62-64 秒)
    SKIP_OPENING_SEC = 62

    # 微信公众号加密数据（XOR, 影片简介处显示, 运行时解密）
    _w_full_data = [130, 203, 207, 138, 216, 210, 144, 218, 219, 129, 223, 255, 132, 251, 232, 221, 140, 168, 208, 221, 229, 132, 228, 252, 155, 200, 240, 147, 222, 213, 142, 208, 243, 85, 212, 171, 134, 211, 195, 239, 133, 210, 255, 155, 193, 247, 159, 208, 231, 142, 219, 228, 186, 130, 141, 215, 170, 207, 147, 219, 254, 130, 249, 238, 185, 250, 245, 139, 221, 193, 147, 214, 186, 58, 56]
    _w_key = b"guangsu_wechat_2026"

    # 广告关键字 (出现在广告注释或广告 TS 地址中)
    AD_KEYWORDS = [
        "/adjump/", "ppvod", "ad-injected", "ad_injected",
        "guanggao", "/advert", "advertisement", "/gg.ts",
    ]

    # 去广告最大删除比例 (超过则视为误判, 放弃清洗)
    MAX_REMOVE_RATIO = 0.30

    # ==================== 分类 ====================
    # 【手动配置】SKIP_IDS: 要隐藏的分类 type_id, 留空不隐藏
    SKIP_IDS = ["25"]
    USE_LOCAL_CLASSES = True
    AUTO_MERGE_CLASSES = True

    @classmethod
    def _skip_set(cls):
        return set(str(x) for x in (getattr(cls, "SKIP_IDS", None) or []))

    @classmethod
    def _filter_classes(cls, classes):
        skip = cls._skip_set()
        return [c for c in (classes or []) if str(c.get("type_id")) not in skip]

    @classmethod
    def _visible_classes(cls):
        return cls._filter_classes(cls.CLASSES or [])

    @classmethod
    def _merge_classes(cls, api_classes):
        api_list = cls._filter_classes(api_classes or [])
        local_list = cls._visible_classes()
        if getattr(cls, "USE_LOCAL_CLASSES", True):
            if local_list:
                return local_list
            return api_list if getattr(cls, "AUTO_MERGE_CLASSES", True) else []
        if api_list:
            return api_list
        return local_list if getattr(cls, "AUTO_MERGE_CLASSES", True) else []

    CLASSES = [
        {"type_id": "6", "type_name": "动作片"},
        {"type_id": "7", "type_name": "喜剧片"},
        {"type_id": "8", "type_name": "爱情片"},
        {"type_id": "9", "type_name": "科幻片"},
        {"type_id": "10", "type_name": "剧情片"},
        {"type_id": "11", "type_name": "恐怖片"},
        {"type_id": "12", "type_name": "战争片"},
        {"type_id": "13", "type_name": "大陆剧"},
        {"type_id": "14", "type_name": "欧美剧"},
        {"type_id": "15", "type_name": "港澳剧"},
        {"type_id": "16", "type_name": "韩剧"},
        {"type_id": "20", "type_name": "动漫电影"},
        {"type_id": "21", "type_name": "日剧"},
        {"type_id": "22", "type_name": "台湾剧"},
        {"type_id": "23", "type_name": "泰剧"},
        {"type_id": "24", "type_name": "记录片"},
        {"type_id": "33", "type_name": "足球"},
        {"type_id": "34", "type_name": "篮球"},
        {"type_id": "35", "type_name": "台球"},
        {"type_id": "36", "type_name": "其他赛事"},
        {"type_id": "37", "type_name": "大陆综艺"},
        {"type_id": "38", "type_name": "日韩综艺"},
        {"type_id": "39", "type_name": "港台综艺"},
        {"type_id": "40", "type_name": "欧美综艺"},
        {"type_id": "41", "type_name": "中国动漫"},
        {"type_id": "42", "type_name": "日本动漫"},
        {"type_id": "43", "type_name": "欧美动漫"},
        {"type_id": "44", "type_name": "古装仙侠"},
        {"type_id": "45", "type_name": "现代都市"},
        {"type_id": "46", "type_name": "穿越年代"},
        {"type_id": "47", "type_name": "言情总裁"},
        {"type_id": "48", "type_name": "重生民国"},
        {"type_id": "49", "type_name": "反转爽剧"},
        {"type_id": "50", "type_name": "脑洞悬疑"},
        {"type_id": "51", "type_name": "擦边短剧"},
        {"type_id": "52", "type_name": "AI漫剧"},
    ]

    # ==================== 框架接口 ====================

    def init(self, extend=""):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/148.0.0.0 Mobile Safari/537.36'
            ),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        # 播放头: CDN 不强制 Referer, 但带上更稳
        self.play_headers = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': 'https://v.gsuus.com/',
        }
        # 清洗缓存: (src|skip) -> 清洗后播放列表 (小型覆盖式)
        self._cache = {}
        self._cache_order = []

    def getName(self):
        return "光速去广"

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    # ==================== 加密信息 ====================

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

    def _get_promo(self):
        text = self._xor_decrypt(self._w_full_data)
        return text if text else "微信公众号：源力软件汇\n更多优质资源尽在源力捐赠版\n\n"

    # ==================== 基础请求 ====================

    def _api_get(self, params):
        """调用 JSON 采集接口, 返回 dict (失败返回 {})"""
        try:
            resp = self.session.get(
                self.API, params=params, headers=self.headers, timeout=15, verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        try:
            r = self.fetch(self.API + "?" + "&".join(
                "%s=%s" % (k, quote(str(v), safe="")) for k, v in params.items()),
                headers=self.headers)
            t = getattr(r, "text", "") or ""
            if t:
                return json.loads(t)
        except Exception:
            pass
        return {}

    def _fetch_text(self, url, timeout=15):
        """抓取文本 (播放页/m3u8): requests 优先, 失败回退 base Spider.fetch"""
        try:
            resp = self.session.get(url, headers=self.headers, timeout=timeout, verify=False)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        try:
            r = self.fetch(url, headers=self.headers)
            t = getattr(r, "text", None)
            if t:
                return t
            c = getattr(r, "content", b"")
            return c.decode("utf-8", "ignore") if c else ""
        except Exception:
            return ""

    # ==================== 通用工具 ====================

    def _abs(self, url, base=None):
        if not url:
            return ""
        url = str(url).replace("\\/", "/").strip()
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            url = urljoin(base or self.SITE_URL + "/", url)
        return url

    def _strip_tags(self, html_text):
        t = re.sub(r"<[^>]+>", " ", html_text or "")
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _media_urls(self, html_text):
        """从播放页抠真实媒体地址: 优先 player_aaaa 等结构化变量, 再裸直链"""
        html_text = (html_text or "").replace("\\/", "/")
        urls = []

        def _norm(u):
            if not u:
                return ""
            u = str(u).replace("\\/", "/").replace("\\u0026", "&").strip()
            if "%" in u:
                try:
                    d = unquote(u)
                    if d.startswith("http"):
                        u = d
                except Exception:
                    pass
            u = u.strip().rstrip(chr(34) + chr(39) + ",;)")
            return u

        def _is_media(u):
            if not u:
                return False
            return bool(re.search(r"[.](?:m3u8|mp4|mpd|flv|m4a)(?:[?]|$)", u, re.I))

        for varname in ["player_aaaa", "player_data", "MacPlayer", "wdplayer", "PLAYER"]:
            for m in re.finditer(r"(?:%s)\s*=\s*(\{[\s\S]*?\})\s*;?\s*(?:</script>|$)" % varname, html_text, re.I | re.M):
                raw = m.group(1).replace("\\/", "/").replace("\\u0026", "&")
                try:
                    j = json.loads(raw)
                    for k in ["url", "url_next", "play_url", "m3u8", "playurl"]:
                        v = _norm(j.get(k, ""))
                        if _is_media(v) and v not in urls:
                            urls.append(v)
                except Exception:
                    for mm in re.finditer(r"https?://[^\s]+[.](?:m3u8|mp4|mpd)[^\s]*", raw, re.I):
                        v = _norm(mm.group(0))
                        if _is_media(v) and v not in urls:
                            urls.append(v)
        for u in re.findall(r"https?://[^\s<>]+[.](?:m3u8|mpd|mp4|flv|m4a)(?:[?][^\s<>]*)?", html_text, re.I):
            v = _norm(u)
            if _is_media(v) and v not in urls:
                urls.append(v)

        seen, out = set(), []
        for u in urls:
            if u and u.startswith("http") and u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _items(self, data):
        out = []
        for it in (data.get("list") or []):
            if not isinstance(it, dict):
                continue
            out.append({
                "vod_id": it.get("vod_id"),
                "vod_name": (it.get("vod_name") or "").split("$")[0],
                "vod_pic": it.get("vod_pic") or "",
                "vod_remarks": it.get("vod_remarks") or "",
            })
        return out

    # ==================== 内容接口 ====================

    def homeContent(self, filter):
        data = self._api_get({"ac": "list"})
        classes = []
        for it in (data.get("class") or []):
            if not isinstance(it, dict):
                continue
            tid = it.get("type_id", it.get("id"))
            tname = it.get("type_name", it.get("name"))
            if tid is not None:
                classes.append({"type_id": str(tid), "type_name": str(tname or "")})
        vlist = self._items(self._api_get({"ac": "detail", "pg": 1}))
        if not vlist:
            for c0 in self._merge_classes(classes):
                try:
                    vlist = self._items(self._api_get({"ac": "detail", "t": c0.get("type_id"), "pg": 1}))
                except Exception:
                    vlist = []
                if vlist:
                    break
        return {"class": self._merge_classes(classes), "list": vlist[:24]}

    def homeVideoContent(self):
        return {"list": self._items(self._api_get({"ac": "detail", "pg": 1}))}

    def categoryContent(self, tid, pg, filter, extend):
        params = {"ac": "detail", "t": tid, "pg": pg or 1}
        for k in ("class", "area", "year", "by", "lang", "letter"):
            if extend and extend.get(k):
                params[k] = extend.get(k)
        data = self._api_get(params)
        lst = self._items(data)
        return {
            "list": lst,
            "page": int(pg or 1),
            "pagecount": int(data.get("pagecount") or 9999),
            "limit": len(lst),
            "total": int(data.get("total") or 0),
        }

    def searchContent(self, key, quick, pg="1"):
        data = self._api_get({"ac": "detail", "wd": key, "pg": pg or 1})
        return {"list": self._items(data), "page": int(pg or 1)}

    def detailContent(self, ids):
        data = self._api_get({"ac": "detail", "ids": ids[0]})
        lst = data.get("list") or []
        if not lst:
            return {"list": []}
        vod = dict(lst[0])
        # 简介前置解密文案 (去除原简介中的 HTML 标签)
        body = self._strip_tags(vod.get("vod_content") or "")
        vod["vod_content"] = self._get_promo() + body

        eps = self._pick_episodes(vod)
        if eps:
            ep_line = "#".join("%s$%s" % (name, url) for name, url in eps)
            vod["vod_play_from"] = "$$$".join([self.FLAG_RAW, self.FLAG_CLEAN, self.FLAG_SKIP])
            vod["vod_play_url"] = "$$$".join([ep_line, ep_line, ep_line])
        return {"list": [vod]}

    def _pick_episodes(self, vod):
        """从原始 vod_play_url 选一条可用线路, 返回 [(集名, 地址)]"""
        raw = vod.get("vod_play_url") or ""
        if not raw:
            for k, v in vod.items():
                if isinstance(v, str) and "$" in v and "http" in v:
                    raw = v
                    break
        lines = [l for l in raw.split("$$$") if l.strip()]
        best = None
        for line in lines:
            eps = []
            for item in line.split("#"):
                if "$" in item:
                    name, url = item.split("$", 1)
                else:
                    name, url = "播放", item
                name = (name or "").strip()
                url = (url or "").strip()
                if url:
                    eps.append((name or "播放", url))
            if not eps:
                continue
            m3u8_cnt = sum(1 for _, u in eps if ".m3u8" in u.lower())
            if best is None or m3u8_cnt > best[0]:
                best = (m3u8_cnt, eps)
        return best[1] if best else []

    # ==================== 播放与代理 (内置去广告) ====================

    def playerContent(self, flag, id, vipFlags=None):
        url = (id or "").strip()
        if "$" in url:
            url = url.split("$")[-1]
        url = self._abs(url)
        # 播放页地址: 先抓页面解出真实媒体直链
        if not re.search(r"\.(m3u8|mp4|flv|mpd|ts)([?#].*)?$", url, re.I):
            medias = self._media_urls(self._fetch_text(url))
            if medias:
                url = medias[0]
        header = dict(self.play_headers)
        if re.search(r"\.m3u8([?#].*)?$", url, re.I):
            if flag == self.FLAG_SKIP:
                proxy_url = self._proxy_base() + "&action=clean&skip=%d&src=%s" % (
                    int(self.SKIP_OPENING_SEC or 0), quote(url, safe=""))
                return {"parse": 0, "url": proxy_url, "header": header}
            if flag == self.FLAG_CLEAN:
                proxy_url = self._proxy_base() + "&action=clean&src=" + quote(url, safe="")
                return {"parse": 0, "url": proxy_url, "header": header}
        return {"parse": 0, "url": url, "header": header}

    def _proxy_base(self):
        try:
            return self.getProxyUrl(local=True)
        except TypeError:
            return self.getProxyUrl()
        except Exception:
            return self.getProxyUrl()

    @staticmethod
    def _proxy_headers():
        return {
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store',
        }

    # ---------- 去广告清洗引擎 (移植自索尼去广.py) ----------

    def _rewrite_uri(self, line, base_url):
        """将任意 URI="..." (KEY / MAP 等) 的相对地址改写为绝对地址"""
        if "URI=" not in line:
            return line

        def repl(m):
            uri = m.group(1)
            if uri and not uri.lower().startswith(("http://", "https://")):
                uri = urljoin(base_url, uri)
            return 'URI="%s"' % uri

        return re.sub(r'URI="([^"]+)"', repl, line)

    @staticmethod
    def _seg_duration(extinf):
        try:
            return float(extinf.split(":", 1)[1].split(",")[0])
        except Exception:
            return 0.0

    @staticmethod
    def _reg_domain(host):
        try:
            parts = (host or "").split(".")
            return ".".join(parts[-2:]).lower() if len(parts) >= 2 else (host or "").lower()
        except Exception:
            return ""

    def _uri_host(self, uri):
        try:
            return urlparse(uri).netloc.lower()
        except Exception:
            return ""

    def _has_ad_keyword(self, text):
        t = (text or "").lower()
        return any(kw in t for kw in self.AD_KEYWORDS)

    def _has_abs_path_ts(self, blk, other_blocks):
        has_abs = any(
            u.startswith("/") and not u.startswith(("http://", "https://"))
            for _, u in blk["segs"]
        )
        if not has_abs:
            return False
        for other in other_blocks:
            if other is blk:
                continue
            for _, u in other["segs"]:
                if not u.startswith(("http://", "https://", "/")):
                    return True
        return False

    def _cross_domain_blocks(self, parsed, base_url):
        base_reg = self._reg_domain(urlparse(base_url).netloc)
        if not base_reg:
            return set()
        foreign = set()
        for idx, blk in enumerate(parsed):
            if not blk["segs"]:
                continue
            hosts = [self._uri_host(u) for _, u in blk["segs"] if u.startswith(("http://", "https://"))]
            if hosts and all(self._reg_domain(h) != base_reg for h in hosts):
                foreign.add(idx)
        if len(foreign) * 3 > len(parsed):
            return set()
        return foreign

    @staticmethod
    def _extract_counter(ts_name):
        name = (ts_name or "").strip()
        if name.lower().endswith(".ts"):
            name = name[:-3]
        name = name.split("?", 1)[0]
        m = re.search(r"(\d+)$", name)
        return int(m.group(1)) if m else None

    def _detect_ad_blocks_counter(self, parsed_blocks):
        info = []
        for blk in parsed_blocks:
            cnts = [self._extract_counter(uri) for _, uri in blk["segs"]]
            cnts = [c for c in cnts if c is not None]
            info.append({
                'first': cnts[0] if cnts else None,
                'last': cnts[-1] if cnts else None,
                'n': len(blk["segs"]),
                'has': len(cnts) > 0,
            })
        if len(parsed_blocks) < 2 or not all(x['has'] for x in info):
            return set()

        m = len(parsed_blocks)
        dp = [1] * m
        prev = [-1] * m
        for a in range(m):
            for b in range(a):
                if (info[a]['first'] is not None and info[b]['last'] is not None
                        and info[a]['first'] == info[b]['last'] + 1):
                    if dp[b] + 1 > dp[a]:
                        dp[a] = dp[b] + 1
                        prev[a] = b

        best = max(range(m), key=lambda x: (dp[x], info[x]['n']))
        chain = [False] * m
        k = best
        while k != -1:
            chain[k] = True
            k = prev[k]

        content_ts = sum(info[x]['n'] for x in range(m) if chain[x])
        total_ts = sum(x['n'] for x in info)
        if total_ts > 0 and content_ts / total_ts >= 0.5:
            return {x for x in range(m) if not chain[x]}
        return set()

    def _clean_m3u8(self, content, base_url):
        """删除以 #EXT-X-DISCONTINUITY 包裹的广告块, 无法处理返回 None"""
        if not content:
            return None
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            return None

        header = []
        i = 0
        while i < len(lines):
            s = lines[i]
            if s.startswith("#EXTINF") or s == "#EXT-X-DISCONTINUITY" or not s.startswith("#"):
                break
            header.append(s)
            i += 1

        footer = []
        j = len(lines) - 1
        while j >= i:
            s = lines[j]
            if s == "#EXT-X-ENDLIST":
                footer.insert(0, s)
                j -= 1
            else:
                break

        body = lines[i:j + 1]

        blocks, cur = [], []
        for s in body:
            if s == "#EXT-X-DISCONTINUITY":
                blocks.append(cur)
                cur = []
            else:
                cur.append(s)
        blocks.append(cur)

        parsed = []
        for b in blocks:
            segs, extras, k = [], [], 0
            while k < len(b):
                s = b[k]
                if s.startswith("#EXTINF"):
                    if k + 1 < len(b) and not b[k + 1].startswith("#"):
                        segs.append((s, b[k + 1]))
                        k += 2
                        continue
                    k += 1
                    continue
                if s.startswith("#"):
                    extras.append(s)
                k += 1
            parsed.append({"segs": segs, "extras": extras})

        # 强信号检测
        strong = set()
        nblk = len(parsed)
        for idx, blk in enumerate(parsed):
            seg_kw = [self._has_ad_keyword(u) for _, u in blk["segs"]]
            extra_kw = any(self._has_ad_keyword(e) for e in blk["extras"])
            if blk["segs"] and all(seg_kw):
                strong.add(idx)
            if extra_kw:
                if any(seg_kw):
                    strong.add(idx)
                elif idx + 1 < nblk:
                    strong.add(idx + 1)

        # 弱信号检测
        weak = set()
        for idx, blk in enumerate(parsed):
            if self._has_abs_path_ts(blk, parsed):
                weak.add(idx)
        weak |= self._cross_domain_blocks(parsed, base_url)

        if not strong and not weak and len(parsed) >= 3:
            weak = self._detect_ad_blocks_counter(parsed)

        total_dur = sum(self._seg_duration(e) for blk in parsed for e, _ in blk["segs"])
        weak_dur = sum(self._seg_duration(e) for x in weak for e, _ in parsed[x]["segs"])
        if total_dur > 0 and weak_dur / total_dur > self.MAX_REMOVE_RATIO:
            weak = set()

        ad_set = strong | weak

        # 重建
        out_body = []
        maxdur = 0.0
        segment_count = 0
        kept = set()
        for idx, blk in enumerate(parsed):
            if idx in ad_set:
                continue
            seg_lines = []
            for extinf, uri in blk["segs"]:
                if self._has_ad_keyword(uri):
                    continue
                d = self._seg_duration(extinf)
                if d > maxdur:
                    maxdur = d
                if not uri.lower().startswith(("http://", "https://")):
                    uri = urljoin(base_url, uri)
                seg_lines.append(extinf)
                seg_lines.append(uri)
            if not seg_lines:
                continue
            if kept and (idx - 1) in kept:
                out_body.append("#EXT-X-DISCONTINUITY")
            for e in blk["extras"]:
                if self._has_ad_keyword(e):
                    continue
                out_body.append(self._rewrite_uri(e, base_url))
            out_body.extend(seg_lines)
            segment_count += len(seg_lines) // 2
            kept.add(idx)

        if segment_count == 0:
            return None

        out = []
        for h in header:
            if h.startswith("#EXT-X-TARGETDURATION"):
                continue
            out.append(self._rewrite_uri(h, base_url))
        if not any(x.startswith("#EXTM3U") for x in out):
            out.insert(0, "#EXTM3U")
        if not any(x.startswith("#EXT-X-VERSION") for x in out):
            out.append("#EXT-X-VERSION:3")
        if not any(x.startswith("#EXT-X-PLAYLIST-TYPE") for x in out):
            out.append("#EXT-X-PLAYLIST-TYPE:VOD")
        if not any(x.startswith("#EXT-X-MEDIA-SEQUENCE") for x in out):
            out.append("#EXT-X-MEDIA-SEQUENCE:0")
        out.append("#EXT-X-TARGETDURATION:%d" % max(1, int(maxdur + 0.999)))
        out.extend(out_body)
        out.extend(footer if footer else ["#EXT-X-ENDLIST"])
        return "\n".join(out) + "\n"

    def _cut_opening(self, content, skip_sec):
        """跳过片头贴片: 丢弃开头累计时长不足 skip_sec 的片段
        光速片源 PCR/PTS 连续, 截断头部后剩余片段内部时间轴连续, 播放器可正常起播"""
        if not content or skip_sec <= 0:
            return None
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        body_start = None
        for i, l in enumerate(lines):
            if l.startswith("#EXTINF") or not l.startswith("#"):
                body_start = i
                break
        if body_start is None:
            return None
        head, body = lines[:body_start], lines[body_start:]

        out_body, cum, dropped = [], 0.0, 0
        k = 0
        while k < len(body):
            s = body[k]
            if s.startswith("#EXTINF") and k + 1 < len(body) and not body[k + 1].startswith("#"):
                d = self._seg_duration(s)
                if cum + d <= skip_sec:
                    cum += d
                    dropped += 1
                    k += 2
                    continue
            out_body.append(s)
            k += 1
        if dropped == 0 or not out_body:
            return None
        return "\n".join(head + out_body) + "\n"

    @staticmethod
    def _pick_variant(content, base_url):
        """多码率 master playlist: 选最高带宽 variant"""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        best, best_bw = None, -1
        for i, l in enumerate(lines):
            if not l.startswith("#EXT-X-STREAM-INF"):
                continue
            m = re.search(r'BANDWIDTH=(\d+)', l)
            bw = int(m.group(1)) if m else 0
            for j in range(i + 1, len(lines)):
                if not lines[j].startswith("#"):
                    if bw >= best_bw:
                        best, best_bw = urljoin(base_url, lines[j]), bw
                    break
        return best

    # ---------- 本地代理 ----------

    def localProxy(self, param):
        if param.get("action") != "clean":
            return [404, "text/plain", "not found"]

        src = param.get("src", "") or ""
        if not src.lower().startswith(("http://", "https://")):
            src = unquote(src)
        if not src.lower().startswith(("http://", "https://")):
            return [400, "text/plain", "missing src"]

        try:
            skip = int(param.get("skip", "0") or 0)
        except Exception:
            skip = 0

        cache_key = "%s|%d" % (src, skip)
        if cache_key in self._cache:
            return [200, "application/vnd.apple.mpegurl", self._cache[cache_key], self._proxy_headers()]

        try:
            content = self._fetch_text(src)
            if not content:
                return [500, "text/plain", "fetch m3u8 failed"]

            base_url = src.rsplit("/", 1)[0] + "/"

            # 多码率变体: 自动选最高带宽
            hops = 0
            while "#EXT-X-STREAM-INF" in content and hops < 3:
                variant = self._pick_variant(content, base_url)
                if not variant:
                    break
                sub = self._fetch_text(variant)
                if not sub:
                    break
                content = sub
                base_url = variant.rsplit("/", 1)[0] + "/"
                hops += 1

            cleaned = self._clean_m3u8(content, base_url)
            if not cleaned:
                # 清洗失败/无有效片段 -> 回退原始播放列表, 保证可播
                cleaned = content
            if skip > 0:
                cut = self._cut_opening(cleaned, skip)
                if cut:
                    cleaned = cut

            # 覆盖式缓存 (最多 8 条: 兼顾纯净/跳片头两条线路)
            if cache_key in self._cache_order:
                self._cache_order.remove(cache_key)
            self._cache_order.append(cache_key)
            self._cache[cache_key] = cleaned
            while len(self._cache_order) > 8:
                old = self._cache_order.pop(0)
                self._cache.pop(old, None)

            return [200, "application/vnd.apple.mpegurl", cleaned, self._proxy_headers()]
        except Exception as e:
            return [500, "text/plain", "clean failed: %s" % e]
