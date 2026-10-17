# coding=utf-8
"""
量子影视（去广告）爬虫
目标站: 量子资源 (http://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/at/json/)
模板: 影视聚合 / 苹果CMS(JSON采集接口) + 内置去广告清洗
站点类型: 综合影视 (电影/电视剧/动漫/综艺/短剧/体育/解说/AI漫剧; 已排除伦理/预告片栏目)

分类写法 (参考暴风去广.py):
  - 一级分类: 运行时调用 ac=list 动态获取站点全部分类树, 只保留一级栏目
  - 二级筛选: 每个一级栏目附带筛选器 (类型/地区 + 年份), 结构为 filters[kind] 列表
      * 类型/地区: 直接使用站点的子分类 type_id (电影->类型, 电视剧/动漫/综艺->地区)
      * 年份:      站点 JSON 接口原生支持 year 参数, 真实生效
  - 分类获取失败时回落静态内置分类, 保证壳端分类栏不空白

线路机制:
  - vod_play_from = lzm3u8 (统一改名 "量子高清"), vod_play_url 为 "集名$m3u8直链"
  - 播放时由本地代理清洗 m3u8 广告后交给播放器, parse=0

去广告优化 (保证 TVBox 正常播放):
  - 量子广告以 #EXT-X-DISCONTINUITY 包裹, 前置 "# ppvod-ad-injected v1" 注释标记
  - 广告 TS 片段使用绝对路径 (以 / 开头), 正片 TS 使用相对路径
  - 多信号检测: (1) ppvod-ad-injected 注释 (2) 绝对路径 TS (3) TS 计数器不连续 (兜底)
  - 按 DISCONTINUITY 切块, 整块识别并删除广告块, 同时清理因此产生的多余 DISCONTINUITY
  - 全部片段/加密 KEY/MAP 的相对地址统一改写为绝对地址, 播放器可直接回源拉流
  - 重算 #EXT-X-TARGETDURATION, 补全 #EXTM3U / #EXT-X-VERSION / #EXT-X-ENDLIST
  - 多码率 master playlist 自动选最高带宽; 任一环节失败自动回退原始播放列表
  - 单条覆盖式缓存, 换集/换源自动刷新
  - 无弹幕

支持: 首页, 一/二级分类(含筛选), 搜索, 详情, 播放 (六接口齐全)
"""

import sys
import re
import time
import requests
from urllib.parse import urljoin, urlparse, quote, unquote, parse_qs, urlencode, urlunparse

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    # ---------- 站点常量 ----------
    SITE_URL = "http://cj.lziapi.com"
    API = "http://cj.lziapi.com/api.php/provide/vod/from/lzm3u8/at/json/"

    # 广告检测关键字 (量子广告注释标记 + 通用 adjump 兼容)
    AD_KEYWORDS = ["ppvod-ad-injected", "/adjump/"]

    # 简介推广信息
    PROMO = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n\n"
    )

    # 一级栏目 name -> 展示名 (覆盖常见栏目, 其余用站点原名)
    CATEGORY_NAMES = {
        "电影片": "电影", "连续剧": "电视剧", "动漫片": "动漫",
        "综艺片": "综艺", "电影解说": "电影解说", "体育": "体育",
        "短剧": "短剧", "演员": "演员", "新闻资讯": "新闻资讯",
        "AI漫剧": "AI漫剧",
    }

    # 需要移除的一级栏目关键字 (按站点原名包含匹配, 兼容 "伦理片"/"预告片"/"预告" 等命名)
    EXCLUDED_CATEGORY_KEYWORDS = ("伦理", "预告")

    # 分类获取失败时的静态兜底 (type_id, 展示名)
    FALLBACK_CLASSES = [
        ("1", "电影"), ("2", "电视剧"), ("3", "综艺"), ("4", "动漫"),
        ("35", "电影解说"), ("36", "体育"), ("46", "短剧"),
        ("52", "AI漫剧"),
    ]

    # 去广告最大删除比例 (超过则视为误判, 放弃清洗)
    MAX_REMOVE_RATIO = 0.25

    def init(self, extend=""):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        # 年份筛选: 全部 + 近十几年
        cur_year = time.localtime().tm_year
        self.year_options = [("全部", "")] + [
            (str(y), str(y)) for y in range(cur_year + 1, 2014, -1)
        ]

        # 分类树缓存
        self._all_classes = None          # 全部 class 原始列表
        self._class_list = None           # 首页 class (一级栏目)
        self._filters_map = None         # 一级栏目 -> 筛选器定义
        self._children = {}              # parent_type_id -> 子分类列表

        # ---------- 去广告清洗缓存 (单条目, 覆盖式) ----------
        self.cached_url = None
        self.cached_content = None

    def getName(self):
        return "量子去广"

    # ==================== 基础请求 ====================

    def _api_get(self, params):
        """调用 JSON 采集接口, 返回解析后的 dict (失败返回 {})"""
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
        return {}

    def _fetch_text(self, url, timeout=15):
        """抓取文本 (m3u8 等), 带默认请求头"""
        try:
            resp = self.session.get(url, headers=self.headers, timeout=timeout, verify=False)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        return None

    # ==================== 分类树 (动态获取全部分类) ====================

    def _load_classes(self):
        """加载站点全部分类, 构建一级栏目与筛选器"""
        if self._class_list is not None:
            return
        data = self._api_get({"ac": "list"})
        classes = data.get("class") or []
        self._all_classes = classes

        children = {}
        tops = []
        for c in classes:
            try:
                cid = str(c.get("type_id"))
            except Exception:
                continue
            pid = str(c.get("type_pid", 0))
            name = c.get("type_name", "") or ""
            # 跳过排除栏目 (伦理/预告片), 一级栏目及其子分类均不展示
            if any(kw in name for kw in self.EXCLUDED_CATEGORY_KEYWORDS):
                continue
            if pid == "0" or pid == "":
                tops.append((cid, name))
            children.setdefault(pid, []).append((cid, name))
        self._children = children

        if not tops:
            # 兜底
            self._class_list = [{"type_id": t, "type_name": n} for t, n in self.FALLBACK_CLASSES]
            self._filters_map = {t: self._year_filter() for t, _ in self.FALLBACK_CLASSES}
            return

        class_list = []
        filters_map = {}
        for cid, name in tops:
            display = self.CATEGORY_NAMES.get(name, name)
            class_list.append({"type_id": cid, "type_name": display})
            filters_map[cid] = self._build_filters(name, children.get(cid, []))
        self._class_list = class_list
        self._filters_map = filters_map

    def _build_filters(self, parent_name, child_list):
        """按一级栏目构造筛选器: 类型/地区(子分类) + 年份"""
        filters = []
        if child_list:
            filters.append({
                "key": "t",
                "name": self._filter_name(parent_name),
                "value": [{"n": n, "v": str(t)} for t, n in child_list],
            })
        filters.append(self._year_filter())
        return filters

    def _year_filter(self):
        return {
            "key": "year",
            "name": "年份",
            "value": [{"n": n, "v": v} for n, v in self.year_options],
        }

    @staticmethod
    def _filter_name(parent_name):
        """子分类的语义: 电影/短剧/体育/AI漫剧 的子类=类型, 剧/动漫/综艺 的子类=地区"""
        if "短剧" in parent_name or "AI漫剧" in parent_name:
            return "类型"
        if "体育" in parent_name:
            return "类型"
        if "动漫" in parent_name:
            return "地区"
        if "综艺" in parent_name:
            return "地区"
        if "电影" in parent_name:
            return "类型"
        if "剧" in parent_name:
            return "地区"
        if "资讯" in parent_name or "新闻" in parent_name:
            return "类型"
        return "分类"

    def _default_type(self, tid):
        """当未选择子分类时, 落到该栏目的第一个子分类 (站点接口不支持父级聚合)"""
        tid = str(tid)
        children = self._children.get(tid) or []
        if children:
            return str(children[0][0])
        return tid

    # ==================== 卡片解析 ====================

    def _parse_item(self, item):
        return {
            "vod_id": item.get("vod_id", ""),
            "vod_name": item.get("vod_name", "") or "",
            "vod_pic": item.get("vod_pic", "") or "",
            "vod_remarks": item.get("vod_remarks", "") or "",
            "vod_year": str(item.get("vod_year", "") or ""),
            "vod_area": item.get("vod_area", "") or "",
            "vod_type": item.get("vod_class", "") or "",
        }

    # ==================== 首页 ====================

    def homeContent(self, filter):
        """一级分类 (动态获取) + 二级筛选器"""
        self._load_classes()
        return {
            "class": [dict(c) for c in self._class_list],
            "filters": {k: [dict(f) for f in v] for k, v in self._filters_map.items()},
            "list": [],
        }

    def homeVideoContent(self):
        """首页推荐: 最新入库"""
        data = self._api_get({"ac": "detail", "pg": "1"})
        items = data.get("list") or []
        return {"list": [self._parse_item(it) for it in items]}

    # ==================== 分类(含筛选) ====================

    def categoryContent(self, tid, pg, filter, extend):
        self._load_classes()
        page = int(pg) if pg else 1
        extend = extend or {}

        # 子分类 (类型/地区): 未选择时落到第一个子分类
        t = str(extend.get("t") or "").strip()
        if not t:
            t = self._default_type(tid)

        params = {"ac": "detail", "t": t, "pg": str(page)}

        # 年份: 站点原生支持, 真实生效
        year = str(extend.get("year") or "").strip()
        if year and year != "全部":
            params["year"] = year

        data = self._api_get(params)
        items = data.get("list") or []
        videos = [self._parse_item(it) for it in items]

        return {
            "list": videos,
            "page": data.get("page", page),
            "pagecount": data.get("pagecount", 0),
            "limit": data.get("limit", 20),
            "total": data.get("total", 0),
        }

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        keyword = (key or "").strip()
        if not keyword:
            return {"list": [], "page": 1, "pagecount": 0, "limit": 20, "total": 0}
        params = {"ac": "detail", "wd": keyword, "pg": str(pg or "1")}
        data = self._api_get(params)
        items = data.get("list") or []
        videos = [self._parse_item(it) for it in items]
        return {
            "list": videos,
            "page": data.get("page", int(pg or 1)),
            "pagecount": data.get("pagecount", 0),
            "limit": data.get("limit", 20),
            "total": data.get("total", 0),
        }

    # ==================== 详情 ====================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0]
        data = self._api_get({"ac": "detail", "ids": vid})
        items = data.get("list") or []
        if not items:
            return {"list": []}
        it = items[0]

        content = it.get("vod_content", "") or it.get("vod_blurb", "") or ""
        content = self.PROMO + content

        # 播放源改名 (lzm3u8 -> 量子高清), 保持与 vod_play_url 的源数量一致
        raw_from = it.get("vod_play_from", "") or "lzm3u8"
        raw_url = it.get("vod_play_url", "") or ""
        play_from = [self._pretty_source(x) for x in raw_from.split("$$$") if x]
        if not play_from:
            play_from = ["量子高清"]

        result = {
            "vod_id": vid,
            "vod_name": it.get("vod_name", "") or "",
            "vod_pic": it.get("vod_pic", "") or "",
            "vod_content": content,
            "vod_actor": it.get("vod_actor", "") or "",
            "vod_director": it.get("vod_director", "") or "",
            "vod_year": str(it.get("vod_year", "") or ""),
            "vod_area": it.get("vod_area", "") or "",
            "vod_type": it.get("vod_class", "") or "",
            "vod_remarks": it.get("vod_remarks", "") or "",
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": raw_url,
        }
        return {"list": [result]}

    @staticmethod
    def _pretty_source(name):
        if name.strip().lower() in ("lzm3u8", "lz", "量子"):
            return "量子高清"
        return name

    # ==================== 播放与代理 (内置去广告) ====================

    def playerContent(self, flag, id, vipFlags=None):
        url = (id or "").strip()
        if not url:
            return {"parse": 1, "url": url, "header": self.headers}

        # m3u8 走本地代理清洗广告; mp4 等直链直接返回
        if "m3u8" in url.lower() and url.lower().startswith(("http://", "https://")):
            proxy_url = self._proxy_base() + "&action=clean&src=" + quote(url, safe="")
            return {"parse": 0, "url": proxy_url, "header": {}}
        return {"parse": 0, "url": url, "header": {}}

    def _proxy_base(self):
        try:
            return self.getProxyUrl(local=True)
        except TypeError:
            return self.getProxyUrl()
        except Exception:
            return self.getProxyUrl()

    # ---------- URL 规范化 (提高缓存命中) ----------

    @staticmethod
    def _normalize_url(url):
        try:
            parsed = urlparse(url)
            q = parse_qs(parsed.query)
            for p in ('_', 't', 'timestamp', 'rand', 'v', 'cb', 'callback'):
                q.pop(p, None)
            return urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
        except Exception:
            return url

    @staticmethod
    def _proxy_headers():
        return {
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store',
        }

    # ---------- 去广告清洗引擎 ----------

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

    def _has_ad_marker(self, blk):
        """检测块内是否含 ppvod-ad-injected / adjump 等广告注释关键字

        量子 CDN 的广告注释出现在广告块前一个正片块的末尾 (作为 extra),
        因此该注释标记的是"下一个块是广告", 而非当前块。
        """
        for e in blk.get("extras", []):
            for kw in self.AD_KEYWORDS:
                if kw in e:
                    return True
        return False

    def _has_abs_path_ts(self, blk):
        """检测块内 TS 是否使用绝对路径 (以 / 开头, 量子广告特征)"""
        for _, uri in blk["segs"]:
            if uri.startswith("/") and not uri.startswith(("http://", "https://")):
                return True
        return False

    def _extract_counter(self, ts_name):
        """提取 TS 文件名末尾的连续数字作为内容计数器 (十进制)"""
        name = ts_name.rstrip()
        if name.lower().endswith(".ts"):
            name = name[:-3]
        name = name.split("?", 1)[0]
        m = re.search(r"(\d+)$", name)
        return int(m.group(1)) if m else None

    def _detect_ad_blocks_counter(self, parsed_blocks):
        """基于 TS 计数器连续性检测广告块 (兜底方案)

        当主检测信号 (绝对路径/注释关键字) 未识别到广告时, 使用 TS 文件名末尾数字的
        连续性作为补充检测: 不在最长连续递增链上的块即为广告块。
        """
        info = []
        for blk in parsed_blocks:
            cnts = [self._extract_counter(uri.split("?", 1)[0]) for _, uri in blk["segs"]]
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
        """删除以 #EXT-X-DISCONTINUITY 包裹的广告块

        检测信号: (1) ppvod-ad-injected 注释 (2) 绝对路径 TS (3) 计数器不连续 (兜底)
        返回清洗后的播放列表; 无法处理时返回 None (由调用方回退原始内容)。
        """
        if not content:
            return None
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            return None

        # 1) 拆出 header (媒体片段之前) 与 footer (#EXT-X-ENDLIST)
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

        # 2) 按 DISCONTINUITY 切块
        blocks, cur = [], []
        for s in body:
            if s == "#EXT-X-DISCONTINUITY":
                blocks.append(cur)
                cur = []
            else:
                cur.append(s)
        blocks.append(cur)

        # 3) 解析每块为 (片段列表, 其它标签)
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

        # 4) 广告检测:
        #    主信号: 绝对路径 TS (量子广告 TS 以 / 开头)
        #    辅助信号: ppvod-ad-injected 注释出现在广告块前一个正片块末尾,
        #              标记"下一个块是广告"
        #    兜底: 主信号未检测到时, 启用 TS 计数器连续性检测
        ad_set = set()
        for idx, blk in enumerate(parsed):
            if self._has_abs_path_ts(blk):
                ad_set.add(idx)

        # 辅助: ppvod-ad-injected 注释标记下一个块为广告
        for idx, blk in enumerate(parsed):
            if self._has_ad_marker(blk) and idx + 1 < len(parsed):
                ad_set.add(idx + 1)

        # 主信号未检测到广告时, 启用计数器连续性兜底
        if not ad_set and len(parsed) >= 3:
            ad_set = self._detect_ad_blocks_counter(parsed)

        # 保护: 删除比例过高则放弃
        total_dur = sum(self._seg_duration(extinf) for blk in parsed for extinf, _ in blk["segs"])
        removed_dur = sum(self._seg_duration(extinf) for idx in ad_set for extinf, _ in parsed[idx]["segs"])
        if total_dur > 0 and removed_dur / total_dur > self.MAX_REMOVE_RATIO:
            ad_set = set()

        # 5) 重建: 删除广告块, 清理多余 DISCONTINUITY, 统一改写绝对地址
        out_body = []
        maxdur = 0.0
        segment_count = 0
        first_kept = False
        removed_ad = False

        for idx, blk in enumerate(parsed):
            is_ad = idx in ad_set
            if is_ad:
                removed_ad = True
                continue
            if not blk["segs"] and not blk["extras"]:
                continue

            # 两个真实正片块之间原本的 DISCONTINUITY 予以保留;
            # 若中间删除了广告块, 则该 DISCONTINUITY 属于广告分隔, 一并去除。
            if first_kept and idx > 0 and not removed_ad:
                out_body.append("#EXT-X-DISCONTINUITY")
            removed_ad = False

            for e in blk["extras"]:
                # 跳过广告注释标记行 (ppvod-ad-injected / adjump)
                if any(kw in e for kw in self.AD_KEYWORDS):
                    continue
                out_body.append(self._rewrite_uri(e, base_url))
            for extinf, uri in blk["segs"]:
                d = self._seg_duration(extinf)
                if d > maxdur:
                    maxdur = d
                segment_count += 1
                if not uri.lower().startswith(("http://", "https://")):
                    uri = urljoin(base_url, uri)
                out_body.append(extinf)
                out_body.append(uri)
            first_kept = True

        # 6) 无有效正片片段则不处理, 回退原始
        if segment_count == 0:
            return None

        # 7) 组装 header / TARGETDURATION / body / footer
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
            return [400, "text/plain", "缺少有效的 src 参数"]

        norm_url = self._normalize_url(src)

        # 命中缓存
        if self.cached_url == norm_url and self.cached_content is not None:
            return [200, "application/vnd.apple.mpegurl", self.cached_content, self._proxy_headers()]

        try:
            content = self._fetch_text(src)
            if not content:
                return [500, "text/plain", "获取 m3u8 失败"]

            base_url = src.rsplit("/", 1)[0] + "/"

            # 多码率变体: 自动选择最高带宽
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

            # 覆盖缓存
            self.cached_url = norm_url
            self.cached_content = cleaned

            return [200, "application/vnd.apple.mpegurl", cleaned, self._proxy_headers()]
        except Exception as e:
            return [500, "text/plain", "清洗失败: %s" % e]

    # ==================== 框架接口 ====================

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
