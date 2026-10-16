# coding=utf-8
"""
光速影视（去广告）爬虫
目标站: 光速资源 (https://api.guangsuapi.com/api.php/provide/vod/from/gsm3u8/at/xml/)
模板: 影视聚合 / 苹果CMS(XML采集接口) + 内置去广告清洗
站点类型: 综合影视 (电影/电视剧/综艺/动漫/体育/短剧)

分类写法 (参考暴风去广.py):
  - 一级分类: 运行时调用 ac=list 动态获取站点分类, 只保留一级栏目(电影/电视剧/综艺/动漫/体育/短剧)
  - 二级筛选: 每个一级栏目附带筛选器 (类型/地区 + 年份), 结构为 filters[kind] 列表
      * 类型/地区: 使用该栏目下的子分类 type_id (电影/短剧/体育->类型, 电视剧/综艺/动漫->地区)
      * 年份:      附带年份筛选 (站点接口若忽略则不影响播放)
      * 站点 XML 分类为扁平结构(无 type_pid), 故内置栏目归属表, 并动态与站点分类求交集
  - 分类获取失败时回落静态内置分类, 保证壳端分类栏不空白
  - 站点未归入任何栏目的分类, 自动作为独立一级栏目, 保证"所有分类"不丢失

线路机制:
  - vod_play_from = gsm3u8 (统一改名 "光速高清"), vod_play_url 为 "集名$m3u8直链#集名$直链"
  - 播放时由本地代理清洗 m3u8 广告后交给播放器, parse=0

去广告优化 (保证 TVBox 正常播放):
  - 光速 CDN(gs.gszyi.com) 以绝对地址/相对地址两种形式分发切片, 广告以
    #EXT-X-DISCONTINUITY 包裹的独立块注入; 按 DISCONTINUITY 切块整体识别并删除
  - 多重信号: (1) adjump/ppvod-ad-injected 注释 (2) 绝对路径 TS 混入 (3) TS 计数器不连续(兜底)
  - KEY 相对地址(如 URI="enc.key")/MAP/切片统一改写为绝对地址, 播放器可直接回源解密拉流
    (此站默认 #EXT-X-KEY:METHOD=AES-128,URI="enc.key" 为相对路径, 不绝对化 TVBox 无法解密)
  - 重算 #EXT-X-TARGETDURATION, 补全 #EXTM3U / #EXT-X-VERSION / #EXT-X-PLAYLIST-TYPE / #EXT-X-ENDLIST
  - 多码率 master playlist 自动选最高带宽; 任一环节失败自动回退原播放列表
  - 单条覆盖式缓存, 换集/换源自动刷新; 无弹幕

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
    SITE_URL = "https://api.guangsuapi.com"
    API = "https://api.guangsuapi.com/api.php/provide/vod/from/gsm3u8/at/xml/"

    # 广告检测关键字 (通用 adjump / ppvod 注入标记)
    AD_KEYWORDS = ["/adjump/", "ppvod-ad-injected"]

    # 简介推广信息
    PROMO = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n\n"
    )

    # 一级栏目定义: (栏目type_id, 栏目名, 子分类属性名, [(子分类type_id, 名称), ...])
    # 站点 XML 分类为扁平结构, 此处按语义归组; 运行时与站点分类求交集, 不存在的自动忽略
    CATEGORY_TREE = [
        ("1", "电影", "类型", [
            ("6", "动作片"), ("7", "喜剧片"), ("8", "爱情片"), ("9", "科幻片"),
            ("10", "剧情片"), ("11", "恐怖片"), ("12", "战争片"),
            ("20", "动漫电影"), ("24", "纪录片"), ("25", "伦理片"),
        ]),
        ("2", "电视剧", "地区", [
            ("13", "大陆剧"), ("14", "欧美剧"), ("15", "港澳剧"), ("16", "韩剧"),
            ("21", "日剧"), ("22", "台湾剧"), ("23", "泰剧"),
        ]),
        ("3", "综艺", "地区", [
            ("37", "大陆综艺"), ("38", "日韩综艺"), ("39", "港台综艺"), ("40", "欧美综艺"),
        ]),
        ("4", "动漫", "地区", [
            ("41", "中国动漫"), ("42", "日本动漫"), ("43", "欧美动漫"),
        ]),
        ("30", "体育", "类型", [
            ("33", "足球"), ("34", "篮球"), ("35", "台球"), ("36", "其他赛事"),
        ]),
        ("31", "短剧", "类型", [
            ("44", "古装仙侠"), ("45", "现代都市"), ("46", "穿越年代"), ("47", "言情总裁"),
            ("48", "重生民国"), ("49", "反转爽剧"), ("50", "脑洞悬疑"),
            ("51", "擦边短剧"), ("52", "AI漫剧"),
        ]),
    ]

    # 需要移除的分类名 (站点原名)
    EXCLUDED_NAMES = {"预告片"}

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
        self.stream_headers = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': 'https://v.gsuus.com/',
            'Accept': '*/*',
        }

        # 年份筛选: 全部 + 近十几年
        cur_year = time.localtime().tm_year
        self.year_options = [("全部", "")] + [
            (str(y), str(y)) for y in range(cur_year + 1, 2014, -1)
        ]

        # 分类树缓存
        self._class_list = None           # 首页 class (一级栏目)
        self._filters_map = None          # 一级栏目 -> 筛选器定义
        self._children = {}               # 一级栏目 type_id -> 子分类列表

        # ---------- 去广告清洗缓存 (单条目, 覆盖式) ----------
        self.cached_url = None
        self.cached_content = None

    def getName(self):
        return "光速去广"

    # ==================== 基础请求 ====================

    def _api_text(self, params):
        """调用 XML 采集接口, 返回原始 XML 文本 (失败返回 '')"""
        try:
            resp = self.session.get(
                self.API, params=params, headers=self.headers, timeout=15, verify=False
            )
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        return ""

    def _fetch_text(self, url, timeout=15):
        """抓取文本 (m3u8 等), 带默认请求头"""
        try:
            resp = self.session.get(
                url, headers=self.stream_headers, timeout=timeout, verify=False
            )
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        return None

    # ==================== XML 解析 ====================

    @staticmethod
    def _tag_text(block, tag):
        """提取 <tag> 文本, 兼容 CDATA 包裹"""
        m = re.search(r'<%s><!\[CDATA\[(.*?)\]\]></%s>' % (tag, tag), block, re.S)
        if m:
            return m.group(1)
        m = re.search(r'<%s>(.*?)</%s>' % (tag, tag), block, re.S)
        if m:
            return m.group(1).strip()
        return ""

    def _page_meta(self, text):
        """解析 <list page=.. pagecount=.. recordcount=..> 属性"""
        meta = {"page": 1, "pagecount": 0, "limit": 20, "total": 0}
        m = re.search(r'<list\s+([^>]*)>', text or "")
        if m:
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            try:
                meta["page"] = int(attrs.get("page", 1))
                meta["pagecount"] = int(attrs.get("pagecount", 0))
                meta["limit"] = int(attrs.get("pagesize", 20))
                meta["total"] = int(attrs.get("recordcount", 0))
            except Exception:
                pass
        return meta

    def _parse_items(self, text):
        """从 XML 文本解析视频列表"""
        items = []
        if not text:
            return items
        for block in re.findall(r'<video>(.*?)</video>', text, re.S):
            items.append({
                "vod_id": self._tag_text(block, "id"),
                "vod_name": self._tag_text(block, "name"),
                "vod_pic": self._tag_text(block, "pic"),
                "vod_remarks": self._tag_text(block, "note"),
                "vod_year": self._tag_text(block, "year"),
                "vod_area": self._tag_text(block, "area"),
                "vod_type": self._tag_text(block, "type"),
                "_raw": block,
            })
        return items

    def _parse_playlist(self, block):
        """解析 <dl><dd flag="gsm3u8">集名$url#集名$url</dd></dl>

        返回 (play_from 列表, play_url 字符串)
        """
        dl = re.search(r'<dl>(.*?)</dl>', block, re.S)
        if not dl:
            return [], ""
        froms, urls = [], []
        for flag, body in re.findall(
            r'<dd flag="([^"]+)">(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</dd>', dl.group(1), re.S
        ):
            body = (body or "").strip()
            if not body:
                continue
            froms.append(flag)
            urls.append(body)
        return froms, "$$$".join(urls)

    # ==================== 分类树 (动态获取全部分类) ====================

    def _parse_classes(self, text):
        """解析 <class><ty id="1">电影</ty>...</class>"""
        classes = []
        m = re.search(r'<class>(.*?)</class>', text or "", re.S)
        if m:
            for cid, name in re.findall(r'<ty id="(\d+)">(.*?)</ty>', m.group(1), re.S):
                name = name.strip()
                if name:
                    classes.append((cid, name))
        return classes

    def _load_classes(self):
        """加载站点分类, 构建一级栏目与筛选器; 与内置归属表求交集"""
        if self._class_list is not None:
            return
        data = self._api_text({"ac": "list"})
        site_classes = self._parse_classes(data)
        site_map = dict(site_classes)

        class_list = []
        filters_map = {}
        children = {}
        used = set()

        for pid, pname, sub_name, subs in self.CATEGORY_TREE:
            # 与站点分类求交集 (站点未获取到时, 直接采用内置)
            present = [(cid, cname) for cid, cname in subs
                       if (not site_map) or (cid in site_map)]
            # 用站点真实名称覆盖 (若有)
            present = [(cid, site_map.get(cid, cname)) for cid, cname in present]
            if not present:
                continue
            # 站点明确没有该一级栏目, 且站点分类可用时, 跳过
            if site_map and pid not in site_map:
                continue
            used.add(pid)
            used.update(cid for cid, _ in present)
            children[str(pid)] = present
            class_list.append({"type_id": str(pid), "type_name": pname})
            filters_map[str(pid)] = self._build_filters(sub_name, present)

        # 站点中未被归类的分类, 作为独立一级栏目, 保证不丢失
        for cid, cname in site_classes:
            if cid in used or cname in self.EXCLUDED_NAMES:
                continue
            class_list.append({"type_id": cid, "type_name": cname})
            filters_map[cid] = [self._year_filter()]
            children[cid] = []

        # 兜底: 一个栏目都没构建出来
        if not class_list:
            for pid, pname, sub_name, subs in self.CATEGORY_TREE:
                children[str(pid)] = list(subs)
                class_list.append({"type_id": str(pid), "type_name": pname})
                filters_map[str(pid)] = self._build_filters(sub_name, list(subs))

        self._children = children
        self._class_list = class_list
        self._filters_map = filters_map

    def _build_filters(self, sub_name, child_list):
        """按一级栏目构造筛选器: 类型/地区(子分类) + 年份"""
        filters = []
        if child_list:
            filters.append({
                "key": "t",
                "name": sub_name,
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

    def _default_type(self, tid):
        """未选择子分类时, 落到该栏目的第一个子分类 (站点不支持父级聚合)"""
        tid = str(tid)
        children = self._children.get(tid) or []
        if children:
            return str(children[0][0])
        return tid

    # ==================== 卡片解析 ====================

    @staticmethod
    def _parse_item(item):
        return {
            "vod_id": item.get("vod_id", ""),
            "vod_name": item.get("vod_name", "") or "",
            "vod_pic": item.get("vod_pic", "") or "",
            "vod_remarks": item.get("vod_remarks", "") or "",
            "vod_year": str(item.get("vod_year", "") or ""),
            "vod_area": item.get("vod_area", "") or "",
            "vod_type": item.get("vod_type", "") or "",
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
        text = self._api_text({"ac": "detail", "pg": "1"})
        items = self._parse_items(text)
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

        # 年份: 站点若支持则原生生效, 不支持也不影响
        year = str(extend.get("year") or "").strip()
        if year and year != "全部":
            params["year"] = year

        text = self._api_text(params)
        items = self._parse_items(text)
        videos = [self._parse_item(it) for it in items]
        meta = self._page_meta(text)

        return {
            "list": videos,
            "page": meta["page"] if meta["page"] else page,
            "pagecount": meta["pagecount"],
            "limit": meta["limit"],
            "total": meta["total"],
        }

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        keyword = (key or "").strip()
        if not keyword:
            return {"list": [], "page": 1, "pagecount": 0, "limit": 20, "total": 0}
        params = {"ac": "detail", "wd": keyword, "pg": str(pg or "1")}
        text = self._api_text(params)
        items = self._parse_items(text)
        videos = [self._parse_item(it) for it in items]
        meta = self._page_meta(text)
        return {
            "list": videos,
            "page": meta["page"] if meta["page"] else int(pg or 1),
            "pagecount": meta["pagecount"],
            "limit": meta["limit"],
            "total": meta["total"],
        }

    # ==================== 详情 ====================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0]
        text = self._api_text({"ac": "detail", "ids": vid})
        items = self._parse_items(text)
        if not items:
            return {"list": []}
        it = items[0]
        block = it.get("_raw", "")

        content = self._tag_text(block, "des") or ""
        content = self.PROMO + content

        # 播放源改名 (gsm3u8 -> 光速高清)
        raw_from, raw_url = self._parse_playlist(block)
        play_from = [self._pretty_source(x) for x in raw_from if x]
        if not play_from:
            play_from = ["光速高清"]

        result = {
            "vod_id": vid,
            "vod_name": it.get("vod_name", "") or "",
            "vod_pic": it.get("vod_pic", "") or "",
            "vod_content": content,
            "vod_actor": self._tag_text(block, "actor"),
            "vod_director": self._tag_text(block, "director"),
            "vod_year": str(it.get("vod_year", "") or ""),
            "vod_area": it.get("vod_area", "") or "",
            "vod_type": it.get("vod_type", "") or "",
            "vod_remarks": it.get("vod_remarks", "") or "",
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": raw_url,
        }
        return {"list": [result]}

    @staticmethod
    def _pretty_source(name):
        if name.strip().lower() in ("gsm3u8", "gs", "光速"):
            return "光速高清"
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

    @staticmethod
    def _looks_abs_ts(uri):
        """站点正片 TS 为绝对地址; 相对路径 TS 多为广告残留, 复用为辅助信号"""
        u = uri.strip()
        return u.startswith("/") and not u.startswith(("//", "http://", "https://"))

    def _has_ad_marker(self, blk):
        for e in blk.get("extras", []):
            for kw in self.AD_KEYWORDS:
                if kw in e:
                    return True
        return False

    def _has_abs_path_ts(self, blk):
        for _, uri in blk["segs"]:
            if self._looks_abs_ts(uri):
                return True
        return False

    @staticmethod
    def _extract_counter(ts_name):
        """提取 TS 文件名末尾连续数字作为内容计数器"""
        name = ts_name.rstrip()
        if name.lower().endswith(".ts"):
            name = name[:-3]
        name = name.split("?", 1)[0]
        m = re.search(r"(\d+)$", name)
        return int(m.group(1)) if m else None

    def _detect_ad_blocks_counter(self, parsed):
        """基于 TS 计数器连续性检测广告块 (兜底)"""
        info = []
        for blk in parsed:
            cnts = [self._extract_counter(u.split("?", 1)[0]) for _, u in blk["segs"]]
            cnts = [c for c in cnts if c is not None]
            info.append({
                'first': cnts[0] if cnts else None,
                'last': cnts[-1] if cnts else None,
                'n': len(blk["segs"]),
                'has': len(cnts) > 0,
            })

        if len(parsed) < 2 or not all(x['has'] for x in info):
            return set()

        m = len(parsed)
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
        """删除以 #EXT-X-DISCONTINUITY 包裹的广告块, 并把相对地址绝对化

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

        # 4) 广告检测: 注释关键字 / 相对路径 TS (改版特征)
        ad_set = set()
        for idx, blk in enumerate(parsed):
            if self._has_abs_path_ts(blk) or self._has_ad_marker(blk):
                ad_set.add(idx)
        # 注释标记 "下一个块是广告"
        for idx, blk in enumerate(parsed):
            if self._has_ad_marker(blk) and idx + 1 < len(parsed):
                ad_set.add(idx + 1)
        # 主信号未命中时, 启用计数器连续性兜底
        if not ad_set and len(parsed) >= 3:
            ad_set = self._detect_ad_blocks_counter(parsed)
        # 保护: 删除比例过高视为误判
        total_dur = sum(self._seg_duration(e) for blk in parsed for e, _ in blk["segs"])
        removed_dur = sum(self._seg_duration(e) for idx in ad_set for e, _ in parsed[idx]["segs"])
        if total_dur > 0 and removed_dur / total_dur > self.MAX_REMOVE_RATIO:
            ad_set = set()

        # 5) 重建: 删除广告块, 清理多余 DISCONTINUITY, 统一改写绝对地址
        out_body = []
        maxdur = 0.0
        segment_count = 0
        first_kept = False
        removed_ad = False

        for idx, blk in enumerate(parsed):
            if idx in ad_set:
                removed_ad = True
                continue
            if not blk["segs"] and not blk["extras"]:
                continue

            if first_kept and idx > 0 and not removed_ad:
                out_body.append("#EXT-X-DISCONTINUITY")
            removed_ad = False

            for e in blk["extras"]:
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

        # 6) 无有效片段则不处理, 回退原始
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

            # 多码率变体: 自动选择最高带宽 (可嵌套)
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
