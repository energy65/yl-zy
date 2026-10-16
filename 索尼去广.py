# coding=utf-8
"""
索尼影视（去广告）爬虫
目标站: 索尼资源 (https://suoniapi.com/api.php/provide/vod/from/snm3u8/at/xml)
模板: 影视聚合 / 苹果CMS(JSON采集接口) + 内置去广告清洗
站点类型: 综合影视 (电影/电视剧/综艺/动漫/体育/短剧/伦理/预告解说/科普)

分类写法 (参考暴风去广.py / 量子去广.py):
  - 一级分类: 运行时调用 ac=list 动态获取站点全部分类名
  - 该采集接口 class 不返回 type_pid, 父子关系通过详情接口的 type_id_1
    实测得出, 固化在 CHILDREN 映射中 (9 个一级栏目)
  - 二级筛选: 每个一级栏目附带筛选器 (类型/地区 + 年份), 结构为 filters[kind] 列表
      * 类型/地区: 直接使用站点子分类 type_id (电影->类型, 电视剧/动漫/综艺->地区)
      * 年份: 该采集接口不支持 year 参数 (实测被忽略), 采用本地过滤:
              游标缓存顺序扫描分类页, 按 vod_year 精确过滤, 换页自动续扫
  - 分类获取失败时回落静态内置分类, 保证壳端分类栏不空白

搜索机制:
  - 采集接口已关闭 wd 搜索 ("暂不支持搜索")
  - 改用主站搜索建议接口 /index.php/ajax/suggest.html?mid=1 取视频 id,
    再回采集接口批量拉详情, 得到完整卡片

线路机制:
  - vod_play_from = snm3u8 (统一改名 "索尼高清"), vod_play_url 为 "集名$m3u8直链"
  - 播放时由本地代理清洗 m3u8 广告后交给播放器, parse=0

去广告优化 (保证 TVBox 正常播放):
  - 广告以 #EXT-X-DISCONTINUITY 包裹的独立块插入正片 (片头/片中/片尾)
  - 多信号检测:
      强信号: (1) 块内 TS 全部命中广告关键字 (/adjump/ ppvod guanggao 等)
              (2) 广告注释标记 (同块带广告 TS -> 删本块, 独占正片块尾 -> 删下一块)
      弱信号: (3) 绝对路径 TS 与相对路径 TS 混排 (注入广告典型特征)
              (4) 跨注册域名 TS 块 (正片在 rstu6.com, 广告在其它域名)
      兜底:  (5) TS 计数器不连续最长递增链
  - 按 DISCONTINUITY 切块, 整块识别并删除广告块, 同时清理多余 DISCONTINUITY
  - 块内若仅混入单条广告 TS 则逐条剔除, 不误伤同块正片
  - 弱信号删除比例超 30% 判定为误判, 放弃该组清洗 (强信号为明确关键字, 不受限)
  - 全部片段/加密 KEY/MAP 的相对地址统一改写为绝对地址, 播放器可直接回源拉流
  - 重算 #EXT-X-TARGETDURATION, 补全 #EXTM3U / #EXT-X-VERSION / #EXT-X-ENDLIST
  - 多码率 master playlist 自动选最高带宽; 任一环节失败自动回退原播放列表
  - 单条覆盖式缓存, 换集/换源自动刷新
  - 无弹幕

支持: 首页, 一/二级分类(含筛选), 搜索, 详情, 播放 (六接口齐全)
"""

import sys
import re
import html
import time
import requests
from urllib.parse import urljoin, urlparse, quote, unquote, parse_qs, urlencode, urlunparse

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    # ---------- 站点常量 ----------
    SITE_URL = "https://suoniapi.com"
    API = "https://suoniapi.com/api.php/provide/vod/from/snm3u8/at/json"
    SUGGEST = "https://suoniapi.com/index.php/ajax/suggest.html"

    # 微信公众号加密数据（XOR, 影片简介处显示, 运行时解密)
    _w_full_data = [150, 203, 193, 138, 214, 254, 146, 224, 207, 140, 221, 227, 186, 189, 135, 221, 138, 233, 147, 213, 254, 140, 213, 236, 141, 222, 199, 133, 207, 233, 212, 129, 181, 60, 149, 238, 219, 139, 205, 197, 147, 217, 251, 128, 213, 220, 183, 135, 180, 212, 140, 227, 144, 223, 211, 140, 195, 223, 131, 217, 248, 132, 254, 196, 212, 189, 162, 222, 198, 213, 136, 231, 225, 85, 125]
    _w_key = b"suoni_wechat_2026"

    # 广告关键字 (出现在广告注释或广告 TS 地址中)
    AD_KEYWORDS = [
        "/adjump/", "ppvod", "ad-injected", "ad_injected",
        "guanggao", "/advert", "advertisement", "/gg.ts",
    ]

    # 一级栏目顺序 (type_id), 实测自详情接口 type_id_1
    TOP_ORDER = [1, 2, 3, 4, 48, 54, 55, 74, 75]

    # 父分类 -> 子分类有序映射 (class 接口无 type_pid, 由 type_id_1 实测)
    CHILDREN = {
        1: [6, 7, 8, 9, 10, 11, 12, 20, 39, 62, 70, 71],
        2: [13, 14, 15, 16, 17, 18, 19, 23, 72],
        3: [25, 26, 27, 28, 47, 77],
        4: [29, 30, 31, 44, 45],
        48: [49, 50, 52],
        54: [63, 64, 65, 66, 67, 68, 69, 73, 76],
        55: [56, 57, 58, 59, 60, 61],
        74: [51, 53],
        75: [],
    }

    # 全部分类静态名 (接口异常时兜底, 也用于补全动态 class 缺名)
    STATIC_NAMES = {
        1: "电影", 2: "电视剧", 3: "综艺", 4: "动漫",
        6: "动作片", 7: "喜剧片", 8: "爱情片", 9: "科幻片", 10: "恐怖片",
        11: "剧情片", 12: "战争片", 13: "国产剧", 14: "欧美剧", 15: "韩剧",
        16: "日剧", 17: "港剧", 18: "台剧", 19: "泰剧", 20: "纪录片",
        23: "海外剧", 25: "大陆综艺", 26: "日韩综艺", 27: "港台综艺",
        28: "欧美综艺", 29: "国产动漫", 30: "日韩动漫", 31: "欧美动漫",
        39: "动画片", 44: "港台动漫", 45: "海外动漫", 47: "演唱会",
        48: "体育赛事", 49: "篮球", 50: "足球", 51: "预告片", 52: "斯诺克",
        53: "影视解说", 54: "爽文短剧", 55: "伦理", 56: "港台三级",
        57: "韩国伦理", 58: "西方伦理", 59: "日本伦理", 60: "两性课堂",
        61: "写真热舞", 62: "4K电影", 63: "有声动漫", 64: "女频恋爱",
        65: "反转爽剧", 66: "古装仙侠", 67: "年代穿越", 68: "脑洞悬疑",
        69: "现代都市", 70: "邵氏电影", 71: "Netflix电影",
        72: "Netflix自制剧", 73: "擦边短剧", 74: "预告解说", 75: "科普学习",
        76: "漫剧", 77: "儿童儿歌",
    }

    # 分类获取失败时的静态兜底 (type_id, 展示名)
    FALLBACK_CLASSES = [
        ("1", "电影"), ("2", "电视剧"), ("3", "综艺"), ("4", "动漫"),
        ("48", "体育赛事"), ("54", "爽文短剧"), ("55", "伦理"),
        ("74", "预告解说"), ("75", "科普学习"),
    ]

    # 去广告最大删除比例 (超过则视为误判, 放弃清洗)
    MAX_REMOVE_RATIO = 0.30
    # 年份本地过滤每次调用最多向前扫描的 API 页数
    YEAR_SCAN_PAGES = 10

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

        # 年份筛选: 全部 + 2000 至今 (邵氏/老片也能筛)
        cur_year = time.localtime().tm_year
        self.year_options = [("全部", "")] + [
            (str(y), str(y)) for y in range(cur_year + 1, 1999, -1)
        ]

        # 分类树缓存
        self._class_list = None           # 首页 class (一级栏目)
        self._filters_map = None          # 一级栏目 -> 筛选器定义
        self._name_map = dict(self.STATIC_NAMES)

        # 年份本地过滤游标缓存: (t, year) -> 扫描状态
        self._year_cache = {}

        # ---------- 去广告清洗缓存 (单条目, 覆盖式) ----------
        self.cached_url = None
        self.cached_content = None

    def getName(self):
        return "索尼去广"

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
        return text if text else (
            "微信公众号：源力软件汇\n更多优质资源尽在源力捐赠版\n\n"
        )

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
        """抓取文本 (m3u8 等): requests 优先, 失败回退 base Spider.fetch"""
        try:
            resp = self.session.get(url, headers=self.headers, timeout=timeout, verify=False)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception:
            pass
        try:
            resp = self.fetch(url, headers=self.headers, timeout=timeout)
            if resp is not None and getattr(resp, "status_code", 0) == 200:
                return resp.text
        except Exception:
            pass
        return None

    # ==================== 分类树 ====================

    def _load_classes(self):
        """加载站点分类名, 结合静态父子映射构建一级栏目与筛选器"""
        if self._class_list is not None:
            return

        name_map = dict(self.STATIC_NAMES)
        data = self._api_get({"ac": "list"})
        for c in (data.get("class") or []):
            try:
                cid = int(c.get("type_id"))
                nm = (c.get("type_name") or "").strip()
                if nm:
                    name_map[cid] = nm
            except Exception:
                continue
        self._name_map = name_map

        class_list = []
        filters_map = {}
        for tid in self.TOP_ORDER:
            tname = name_map.get(tid, str(tid))
            class_list.append({"type_id": str(tid), "type_name": tname})
            filters_map[str(tid)] = self._build_filters(tid, tname, name_map)

        self._class_list = class_list
        self._filters_map = filters_map

    def _build_filters(self, tid, parent_name, name_map):
        """按一级栏目构造筛选器: 类型/地区(子分类) + 年份"""
        filters = []
        child_ids = self.CHILDREN.get(tid, [])
        if child_ids:
            filters.append({
                "key": "t",
                "name": self._filter_name(parent_name),
                "value": [
                    {"n": name_map.get(cid, str(cid)), "v": str(cid)}
                    for cid in child_ids
                ],
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
        """子分类的语义: 短剧/体育/电影/伦理 等子类=类型, 剧/动漫/综艺=地区"""
        if "短剧" in parent_name or "体育" in parent_name:
            return "类型"
        if "动漫" in parent_name or "综艺" in parent_name:
            return "地区"
        if "电影" in parent_name:
            return "类型"
        if "剧" in parent_name:
            return "地区"
        return "类型"

    @staticmethod
    def _clean_name(name):
        """MacCMS 数据中 name 可能带 "$别名" 后缀, 展示只取主名"""
        name = (name or "").split("$", 1)[0].strip()
        return name

    def _default_child(self, tid):
        """父栏目自身不出片 (接口不支持父级聚合), 落到第一个子分类"""
        tid = int(str(tid))
        children = self.CHILDREN.get(tid) or []
        if children:
            return str(children[0])
        return str(tid)

    # ==================== 卡片解析 ====================

    def _parse_item(self, item):
        return {
            "vod_id": item.get("vod_id", ""),
            "vod_name": self._clean_name(item.get("vod_name", "")),
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
            t = self._default_child(tid)

        # 年份: 采集接口不支持, 走本地过滤
        year = str(extend.get("year") or "").strip()
        if year and year != "全部":
            return self._category_by_year(t, year, page)

        data = self._api_get({"ac": "detail", "t": t, "pg": str(page)})
        items = data.get("list") or []
        videos = [self._parse_item(it) for it in items]

        return {
            "list": videos,
            "page": self._to_int(data.get("page"), page),
            "pagecount": self._to_int(data.get("pagecount"), 0),
            "limit": self._to_int(data.get("limit"), 20),
            "total": self._to_int(data.get("total"), 0),
        }

    def _category_by_year(self, t, year, page):
        """本地年份过滤: 游标缓存顺序扫描分类页, 按 vod_year 精确过滤

        每次 TVBox 翻页从缓存弹出 20 条; 缓存不足时继续向后扫描,
        扫描到 API 末页仍无更多结果则结束分页。
        """
        key = (str(t), str(year))
        st = self._year_cache.get(key)
        if st is None:
            st = {
                "matches": [],      # 已匹配待消费的卡片 (dict)
                "next_pg": 1,       # 下一个待扫描 API 页
                "api_pages": None,  # API 总页数
                "done": False,
                "served": 0,        # 已交付给 TVBox 的页数
                "seen": set(),      # 去重 vod_id
            }
            self._year_cache[key] = st
        # 只保留当前 (t,year) 的缓存, 避免长时间占用
        if len(self._year_cache) > 4:
            for k in list(self._year_cache.keys()):
                if k != key:
                    self._year_cache.pop(k, None)

        scans = 0
        while len(st["matches"]) < 20 and not st["done"] and scans < self.YEAR_SCAN_PAGES:
            data = self._api_get({"ac": "detail", "t": str(t), "pg": str(st["next_pg"])})
            items = data.get("list") or []
            if st["api_pages"] is None:
                st["api_pages"] = self._to_int(data.get("pagecount"), 0)
            if not items:
                st["done"] = True
                break
            for it in items:
                vid = it.get("vod_id")
                if vid in st["seen"]:
                    continue
                if str(it.get("vod_year", "") or "") == str(year):
                    st["seen"].add(vid)
                    st["matches"].append(self._parse_item(it))
            scans += 1
            if st["api_pages"] and st["next_pg"] >= st["api_pages"]:
                st["done"] = True
            st["next_pg"] += 1

        videos = st["matches"][:20]
        st["matches"] = st["matches"][20:]
        st["served"] += 1

        pagecount = st["served"] if st["done"] else st["served"] + 100
        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
        }

    @staticmethod
    def _to_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    # ==================== 搜索 (suggest -> 批量详情) ====================

    def searchContent(self, key, quick, pg="1"):
        keyword = (key or "").strip()
        empty = {"list": [], "page": 1, "pagecount": 0, "limit": 20, "total": 0}
        if not keyword:
            return empty

        ids = []
        try:
            resp = self.session.get(
                self.SUGGEST,
                params={"mid": "1", "wd": keyword},
                headers={
                    'User-Agent': self.headers['User-Agent'],
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': self.SITE_URL + "/",
                },
                timeout=15,
                verify=False,
            )
            if resp.status_code == 200:
                sj = resp.json()
                for it in (sj.get("list") or []):
                    vid = it.get("id")
                    if vid is not None and str(vid) not in ids:
                        ids.append(str(vid))
        except Exception:
            return empty

        if not ids:
            return empty

        data = self._api_get({"ac": "detail", "ids": ",".join(ids[:20])})
        items = data.get("list") or []
        if items:
            # 按 suggest 返回顺序排序 (suggest 相关性更高)
            order = {vid: i for i, vid in enumerate(ids)}
            items.sort(key=lambda x: order.get(str(x.get("vod_id")), 999))
            videos = [self._parse_item(it) for it in items]
        else:
            # 详情批量拉取失败时, 退回 suggest 简卡, 保证搜索有结果
            videos = [{
                "vod_id": it.get("id", ""),
                "vod_name": (it.get("name", "") or "").split("$")[0],
                "vod_pic": it.get("pic", "") or "",
                "vod_remarks": "",
                "vod_year": "",
                "vod_area": "",
                "vod_type": "",
            } for it in sj.get("list", [])]

        return {
            "list": videos,
            "page": 1,
            "pagecount": 1,
            "limit": 20,
            "total": len(videos),
        }

    # ==================== 详情 ====================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0]
        data = self._api_get({"ac": "detail", "ids": str(vid)})
        items = data.get("list") or []
        if not items:
            return {"list": []}
        it = items[0]

        content = it.get("vod_content", "") or it.get("vod_blurb", "") or ""
        content = self._strip_html(content)
        content = self._get_promo() + content

        # 播放源改名 (snm3u8 -> 索尼高清)
        raw_from = it.get("vod_play_from", "") or "snm3u8"
        raw_url = it.get("vod_play_url", "") or ""
        play_from = [self._pretty_source(x) for x in raw_from.split("$$$") if x]
        if not play_from:
            play_from = ["索尼高清"]

        result = {
            "vod_id": vid,
            "vod_name": self._clean_name(it.get("vod_name", "")),
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
        if name.strip().lower() in ("snm3u8", "sn", "索尼", "索尼资源"):
            return "索尼高清"
        return name

    @staticmethod
    def _strip_html(text):
        """简介去 HTML 标签/实体"""
        if not text:
            return ""
        text = re.sub(r'(?i)<br\s*/?>', "\n", text)
        text = re.sub(r'(?is)</p\s*>', "\n", text)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        return text.strip()

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
    def _reg_domain(host):
        """取注册域名 (末两段), 用于跨域广告块判定"""
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
        """块内 TS 使用根绝对路径 (以 / 开头), 且其它块存在相对路径 TS"""
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
        """TS 注册域名与播放列表主域名不一致的块 (注入广告常托管在外部域名)"""
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
        # 仅当域外块为少数时才认定, 避免主域名整体跳转造成的误判
        if len(foreign) * 3 > len(parsed):
            return set()
        return foreign

    @staticmethod
    def _extract_counter(ts_name):
        """提取 TS 文件名末尾的连续数字作为内容计数器"""
        name = (ts_name or "").strip()
        if name.lower().endswith(".ts"):
            name = name[:-3]
        name = name.split("?", 1)[0]
        m = re.search(r"(\d+)$", name)
        return int(m.group(1)) if m else None

    def _detect_ad_blocks_counter(self, parsed_blocks):
        """基于 TS 计数器连续性检测广告块 (兜底方案)

        取跨块计数器的最长严格递增链作为正片, 链外块即广告块;
        正片占比不足一半则放弃检测。
        """
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
        """删除以 #EXT-X-DISCONTINUITY 包裹的广告块

        多信号检测 + 删除比例保护; 返回清洗后的播放列表,
        无法处理时返回 None (由调用方回退原始内容)。
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

        # 4) 多信号广告块检测
        # 强信号 (高精度):
        #   a) 块内 TS 全部命中广告关键字 -> 纯广告块, 整块删除
        #   b) 广告注释标记与广告 TS 同块 -> 整块删除
        #   c) 广告注释标记单独出现在正片块末尾 -> 标记的下一块为广告
        #   (块内仅个别 TS 命中时不删整块, 重建阶段逐条剔除)
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

        # 弱信号 (启发式): 根绝对路径 TS 混排 / 跨注册域名块
        weak = set()
        for idx, blk in enumerate(parsed):
            if self._has_abs_path_ts(blk, parsed):
                weak.add(idx)
        weak |= self._cross_domain_blocks(parsed, base_url)

        # 兜底: 强/弱信号都未命中时, 用 TS 计数器最长递增链
        if not strong and not weak and len(parsed) >= 3:
            weak = self._detect_ad_blocks_counter(parsed)

        # 删除比例保护只约束弱信号 (强信号为明确广告关键字, 不参与比例判断);
        # 弱信号删除占比超阈值则整组放弃, 避免误删正片
        total_dur = sum(self._seg_duration(e) for blk in parsed for e, _ in blk["segs"])
        weak_dur = sum(self._seg_duration(e) for x in weak for e, _ in parsed[x]["segs"])
        if total_dur > 0 and weak_dur / total_dur > self.MAX_REMOVE_RATIO:
            weak = set()

        ad_set = strong | weak

        # 5) 重建: 删除广告块, 清理多余 DISCONTINUITY, 统一改写绝对地址
        out_body = []
        maxdur = 0.0
        segment_count = 0
        kept = set()   # 实际输出了片段的块下标

        for idx, blk in enumerate(parsed):
            if idx in ad_set:
                continue

            seg_lines = []
            for extinf, uri in blk["segs"]:
                # 块内逐条广告 TS 过滤 (强信号块未整块删除时仍生效)
                if self._has_ad_keyword(uri):
                    continue
                d = self._seg_duration(extinf)
                if d > maxdur:
                    maxdur = d
                if not uri.lower().startswith(("http://", "https://")):
                    uri = urljoin(base_url, uri)
                seg_lines.append(extinf)
                seg_lines.append(uri)

            if not seg_lines and not blk["extras"]:
                continue
            if not seg_lines:
                continue

            # 仅当与上一个实际输出块直接相邻时, 保留二者原有的 DISCONTINUITY;
            # 中间删除了广告块/空块则该分隔符一并去除, 杜绝重复/首尾 DISC
            if kept and (idx - 1) in kept:
                out_body.append("#EXT-X-DISCONTINUITY")

            for e in blk["extras"]:
                if self._has_ad_keyword(e):
                    continue
                out_body.append(self._rewrite_uri(e, base_url))
            out_body.extend(seg_lines)
            segment_count += len(seg_lines) // 2
            kept.add(idx)

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
