# -*- coding: utf-8 -*-
"""
大米星球 TVBox Python 源 (MacCMS / 海螺模板)

站点结构 (来自可用的旧版源, 已在文件里按此实现):
    /index/home.html                     首页
    /vodtype/{tid}.html                  分类页,  翻页 /vodtype/{tid}-{pg}.html
    /voddetail/{id}.html                 详情页
    /vodplay/{id}-{sid}-{ep}.html        播放页 (内含 player_aaaa 真实地址)
    /vodsearch/{关键词}-------------.html 搜索,  翻页加 ?page=n
    /label/netflix.html                  奈飞专区
    /api.php/provide/vod/                苹果CMS 数据接口 (有就用, 没有走 HTML)

分类 (站点一级导航): Netflix / 电影 20 / 电视剧 21 / 短剧 36 / 动漫 22 / 综艺 23
    实际运行时以站点首页导航为准, 站点加了分类会自动带出来, 不写死。

功能:
    - 获取全部分类 + 每个分类挂 类型/地区/年份 三组筛选
    - 类型细化: 电影 科幻片/奇幻片/战争片/犯罪片/武侠片/历史片/文艺片 等
                电视剧 古装/都市/历史/谍战/家庭 等
      站点有对应二级分类的直接跳该分类, 没有的自动走关键词检索, 点进去不会是空页
    - 搜索任意影片
    - 影片简介置顶 微信公众号 "源力软件汇"
    - 播放: 播放页解出 player_aaaa 的 m3u8/mp4 直链给 parse=0, 解不出才 parse=1
    - 域名轮换: dmxq40.com 起的整段域名依次探测, 换域名不用改代码
只使用 Python 标准库 (urllib / json / re / base64 / gzip / html)。
"""
import re
import sys
import json
import time
import ssl
import threading
import gzip
import base64
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


class Spider(BaseSpider):
    # 上一次探测成功的域名 (同进程内复用, 避免每次重复探测)
    _KNOWN_HOST = ""

    UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
          "Mobile/15E148 Safari/604.1")

    # 主域名 + 同系列轮换域名 (按顺序探测, 第一个通的就用)
    HOSTS = (["https://dmxq%d.com" % n for n in range(40, 50)] +
             ["https://dmxq%d.com" % n for n in range(30, 40)] +
             ["https://dmflm.com", "https://dmxq.me", "https://dmxq.info",
              "https://dmxq.fun", "https://dmvid.net"])

    API_PATH = "/api.php/provide/vod/"

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # 简介置顶文案
    WX_TEXT = "更多影视资源请关注微信公众号：源力软件汇"

    # 站点的固定分类 (首页导航解析失败时兜底)
    DEFAULT_CLASSES = [
        ("netflix", "Netflix"),
        ("20", "电影"),
        ("21", "电视剧"),
        ("36", "短剧"),
        ("22", "动漫"),
        ("23", "综艺"),
    ]

    # 细化类型候选
    TYPE_OPTIONS = {
        "电影": ["科幻片", "奇幻片", "战争片", "犯罪片", "武侠片", "历史片", "文艺片",
                 "动作片", "喜剧片", "爱情片", "恐怖片", "惊悚片", "悬疑片", "剧情片",
                 "纪录片", "动画片", "冒险片", "灾难片"],
        "电视剧": ["古装", "都市", "历史", "谍战", "家庭", "爱情", "悬疑", "犯罪",
                   "战争", "年代", "偶像", "农村", "商战", "武侠", "科幻", "喜剧"],
        "动漫": ["国漫", "日漫", "热血", "冒险", "搞笑", "科幻", "校园", "治愈",
                 "运动", "推理", "恋爱", "亲子"],
        "综艺": ["真人秀", "脱口秀", "选秀", "访谈", "搞笑", "竞技", "生活", "文化",
                 "音乐", "游戏", "亲子", "晚会"],
        "短剧": ["都市", "逆袭", "甜宠", "重生", "穿越", "战神", "总裁", "古装",
                 "悬疑", "虐恋", "豪门", "校园"],
        "Netflix": ["美剧", "英剧", "韩剧", "日剧", "电影", "纪录片", "动漫"],
    }

    # 细化类型 -> 站点可能使用的二级分类名
    TYPE_ALIAS = {
        "科幻片": ["科幻", "科幻片"], "奇幻片": ["奇幻", "奇幻片", "魔幻"],
        "战争片": ["战争", "战争片"], "犯罪片": ["犯罪", "犯罪片", "警匪"],
        "武侠片": ["武侠", "武侠片", "功夫"], "历史片": ["历史", "历史片", "年代"],
        "文艺片": ["文艺", "文艺片", "剧情"], "动作片": ["动作", "动作片"],
        "喜剧片": ["喜剧", "喜剧片"], "爱情片": ["爱情", "爱情片"],
        "恐怖片": ["恐怖", "恐怖片"], "惊悚片": ["惊悚", "惊悚片"],
        "悬疑片": ["悬疑", "悬疑片"], "剧情片": ["剧情", "剧情片"],
        "纪录片": ["纪录", "纪录片"], "动画片": ["动画", "动漫"],
        "冒险片": ["冒险"], "灾难片": ["灾难"],
        "古装": ["古装"], "都市": ["都市"], "历史": ["历史", "年代"],
        "谍战": ["谍战"], "家庭": ["家庭", "伦理"], "年代": ["年代", "历史"],
        "偶像": ["偶像"], "农村": ["农村", "乡村"], "商战": ["商战", "职场"],
        "国漫": ["国产动漫", "国漫"], "日漫": ["日本动漫", "日漫"],
        "热血": ["热血"], "治愈": ["治愈"], "推理": ["推理", "悬疑"],
        "真人秀": ["真人秀"], "脱口秀": ["脱口秀"], "选秀": ["选秀", "竞演"],
        "逆袭": ["逆袭"], "甜宠": ["甜宠"], "重生": ["重生"], "穿越": ["穿越"],
        "战神": ["战神"], "总裁": ["总裁", "霸总"], "虐恋": ["虐恋"], "豪门": ["豪门"],
    }

    AREAS = ["大陆", "香港", "台湾", "美国", "英国", "法国", "德国", "日本", "韩国",
             "泰国", "印度", "意大利", "西班牙", "俄罗斯", "加拿大", "澳大利亚", "其他"]

    YEARS = ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019",
             "2018", "2017", "2016", "2015", "更早"]

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.HOSTS[0]
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        }
        self._classes = []          # [{"id","name"}]
        self._class_map = {}
        self._sub_map = {}          # 父分类名 -> [(子分类名, id)]
        self.api_ok = None          # None=未探测
        self._filters_cache = {}
        self._alive = False
        self._apply_extend(extend)
        self._detect_host()

    def _apply_extend(self, extend):
        if not extend:
            return
        s = extend if isinstance(extend, str) else json.dumps(extend)
        s = s.strip()
        if s.startswith("{"):
            try:
                d = json.loads(s)
            except Exception:
                d = {}
            for k in ("host", "site", "url", "www", "domain"):
                v = d.get(k)
                if isinstance(v, str) and v.strip().startswith("http"):
                    v = v.strip().rstrip("/")
                    if "api.php" in v:
                        v = v.split("/api.php")[0]
                    self.HOSTS = [v] + [h for h in self.HOSTS if h != v]
                    break
        elif s.startswith("http"):
            v = s.rstrip("/")
            self.HOSTS = [v] + [h for h in self.HOSTS if h != v]
        self.host = self.HOSTS[0]

    def getName(self):
        return "大米星球"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return ".m3u8" in low or ".mp4" in low or ".flv" in low

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        pass

    # ==================== 请求 ====================
    def _fetch(self, url, referer=None, timeout=8):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = dict(self.headers)
        headers["Referer"] = referer or (self.host + "/")
        req = urllib.request.Request(url, headers=headers)
        data = b""
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
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
        return self._decode(data)

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _get(self, path, referer=None, timeout=8):
        url = path if path.startswith("http") else self.host + path
        return self._fetch(url, referer=referer, timeout=timeout)

    # ==================== 域名探测 ====================
    def _detect_host(self):
        """并发探测各镜像域名, 取顺序最靠前的可用域名 (总耗时上限 9 秒)"""
        candidates = list(self.HOSTS)
        known = Spider._KNOWN_HOST
        if known:
            candidates = [known] + [h for h in candidates if h != known]
        t0 = time.time()
        # 快路径: 首选域名通了就不再探测其它
        if candidates and self._host_alive(candidates[0]):
            self.host = candidates[0]
            Spider._KNOWN_HOST = candidates[0]
            self._alive = True
            return
        candidates = candidates[1:] or candidates
        alive = []
        lock = threading.Lock()

        def probe(h):
            try:
                if self._host_alive(h):
                    with lock:
                        alive.append(h)
            except Exception:
                pass

        try:
            threads = []
            for h in candidates[:24]:
                t = threading.Thread(target=probe, args=(h,))
                t.daemon = True
                t.start()
                threads.append(t)
            end = t0 + 8
            for t in threads:
                left = end - time.time()
                if left <= 0:
                    break
                t.join(left)
        except Exception:
            for h in candidates:
                if self._host_alive(h):
                    alive.append(h)
                    break
        for h in candidates:
            if h in alive:
                self.host = h
                Spider._KNOWN_HOST = h
                self._alive = True
                return

    def _host_alive(self, host):
        html = self._fetch(host + "/index/home.html", referer=host + "/", timeout=3)
        if not html or len(html) < 500:
            html2 = self._fetch(host + "/vodtype/20.html", referer=host + "/", timeout=3)
            if not html2 or len(html2) < 500:
                return False
            html = html2
        return ("module-poster-item" in html or "voddetail" in html or
                "module-item" in html or "stui" in html)

    # ==================== 通用解析 ====================
    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r'<[^>]+>', '', s)
        s = html_mod.unescape(s)
        return re.sub(r'\s+', ' ', s).strip()

    def _norm_name(self, name):
        return re.sub(r'\s+', '', self._clean(name)).replace("片片", "片")

    def _abs(self, url):
        if not url:
            return self.DEFAULT_PIC
        url = html_mod.unescape(url.strip())
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.DEFAULT_PIC

    def _parse_card(self, card):
        """解析单个影片卡片 (首页/分类页/搜索页通用)"""
        m = re.search(r'href="([^"]*?/voddetail/(\d+)\.html)"', card)
        if not m:
            return None
        vid = m.group(2)
        title = ""
        for pat in (r'module-poster-item-title[^>]*>([^<]+)<',
                    r'<strong>(.*?)</strong>',
                    r'title="([^"]+)"',
                    r'alt="([^"]+)"'):
            t = re.search(pat, card, re.S)
            if t and self._clean(t.group(1)):
                title = self._clean(t.group(1))
                break
        if not title:
            return None
        pic = ""
        pm = re.search(r'(?:data-original|data-src|data-echo|src)="([^"]+)"', card)
        if pm:
            pic = self._abs(pm.group(1))
        note = ""
        nm = re.search(r'class="module-item-note"[^>]*>([^<]*)<', card)
        if nm:
            note = self._clean(nm.group(1))
        if not note:
            cm = re.search(r'class="module-card-item-class"[^>]*>([^<]*)<', card)
            if cm:
                note = self._clean(cm.group(1))
        return {
            "vod_id": self.host + "/voddetail/%s.html" % vid,
            "vod_name": title,
            "vod_pic": pic or self.DEFAULT_PIC,
            "vod_remarks": note,
        }

    def _parse_list(self, html_text):
        """列表页解析: 先按卡片切块, 不够再用并行数组兜底"""
        items = []
        seen = set()
        if not html_text:
            return items
        splitter = None
        for key in ('<div class="module-card-item', '<div class="module-poster-item',
                    'class="module-poster-item', '<div class="module-item'):
            if key in html_text:
                splitter = key
                break
        if splitter:
            cards = re.split(r'(?=' + re.escape(splitter) + r')', html_text)
            for c in cards:
                it = self._parse_card(c)
                if it and it["vod_id"] not in seen:
                    seen.add(it["vod_id"])
                    items.append(it)
        if len(items) < 8:
            for it in self._parse_parallel(html_text):
                if it["vod_id"] not in seen:
                    seen.add(it["vod_id"])
                    items.append(it)
        return items

    def _parse_parallel(self, html_text):
        """并行数组解析: 该站首页/分类页的标题、海报、链接顺序一致"""
        out = []
        hrefs = re.findall(r'href="(/voddetail/\d+\.html)"', html_text)
        pics = re.findall(r'data-original="([^"]+)"', html_text)
        titles = re.findall(r'module-poster-item-title[^>]*>([^<]+)<', html_text)
        notes = re.findall(r'class="module-item-note"[^>]*>([^<]+)<', html_text)
        if not titles:
            titles = re.findall(r'title="([^"]+)"[^>]*>\s*<img', html_text)
        n = min(len(hrefs), len(pics), len(titles))
        seen = set()
        for i in range(n):
            href = hrefs[i]
            vid = re.search(r'/voddetail/(\d+)\.html', href)
            if not vid:
                continue
            vod_id = self.host + href
            if vod_id in seen:
                continue
            title = self._clean(titles[i])
            if not title:
                continue
            seen.add(vod_id)
            out.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._abs(pics[i]) if pics[i] else self.DEFAULT_PIC,
                "vod_remarks": self._clean(notes[i]) if i < len(notes) else "",
            })
        return out

    # ==================== 分类 ====================
    def _parse_classes(self, html_text):
        """从首页导航里取全部分类 (站点加分类会自动带出来)"""
        found = []
        seen = set()
        if not html_text:
            return found
        pat = (r'<a[^>]+href="(?:' + re.escape(self.host) + r')?'
               r'(?:/index\.php/vod/type/id/|/vodtype/)(\d+)\.html"[^>]*>(.*?)</a>')
        for m in re.finditer(pat, html_text, re.S):
            tid = m.group(1)
            name = self._norm_name(m.group(2))
            if not name or tid in seen or len(name) > 10:
                continue
            if name in ("首页", "全部", "更多", "排行榜", "专题", "APP"):
                continue
            seen.add(tid)
            found.append({"id": tid, "name": name})
        return found

    def _ensure_api(self):
        """探测苹果CMS 数据接口, 用来拿完整分类树 (拿不到就走 HTML)"""
        if self.api_ok is not None:
            return self.api_ok
        self.api_ok = False
        text = self._get(self.API_PATH + "?ac=list", timeout=4)
        if not text or not text.strip().startswith("{"):
            return False
        try:
            data = json.loads(text)
        except Exception:
            return False
        classes = data.get("class") or []
        if not classes:
            return False
        self.api_ok = True
        tops = []
        subs = {}
        by_id = {}
        for c in classes:
            cid = str(c.get("type_id", ""))
            name = self._norm_name(c.get("type_name", ""))
            pid = str(c.get("type_pid", 0))
            by_id[cid] = {"id": cid, "name": name, "pid": pid}
        for cid, c in by_id.items():
            if c["pid"] in ("0", "", None) or c["pid"] not in by_id:
                tops.append(c)
            else:
                subs.setdefault(c["pid"], []).append(c)
        if tops:
            self._classes = tops
        self._sub_map = subs
        return True

    def _filters_for(self, tid, name):
        key = "%s|%s" % (tid, name)
        if key in self._filters_cache:
            return self._filters_cache[key]
        # 类型: 站点二级分类优先, 没有就用关键词检索兜底
        type_vals = [{"n": "全部", "v": ""}]
        labels = self.TYPE_OPTIONS.get(name) or self.TYPE_OPTIONS.get(
            name.replace("片", "") if name else "", [])
        used = set()
        subs = self._sub_map.get(tid) or []
        sub_by_name = {}
        for s in subs:
            sub_by_name.setdefault(s["name"], s["id"])
        for lab in labels:
            if lab in used:
                continue
            used.add(lab)
            target = None
            for alias in self.TYPE_ALIAS.get(lab, [lab]):
                if alias in sub_by_name:
                    target = "tid:" + sub_by_name[alias]
                    break
            if target is None and lab in sub_by_name:
                target = "tid:" + sub_by_name[lab]
            type_vals.append({"n": lab, "v": target or ("kw:" + self._kw_of(lab))})
        # 站点其余二级分类也挂上
        for s in subs:
            if s["name"] in used or not s["name"]:
                continue
            used.add(s["name"])
            type_vals.append({"n": s["name"], "v": "tid:" + s["id"]})
        area_vals = [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.AREAS]
        year_vals = [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.YEARS]
        f = [
            {"name": "类型", "value": type_vals},
            {"name": "地区", "value": area_vals},
            {"name": "年份", "value": year_vals},
        ]
        self._filters_cache[key] = f
        return f

    def _kw_of(self, label):
        alias = self.TYPE_ALIAS.get(label)
        if alias:
            return alias[0]
        return label.replace("片", "") if label.endswith("片") else label

    # ==================== TVBox 接口 ====================
    def homeContent(self, filter=None):
        result = {"class": [], "filters": {}, "list": []}
        if not self._alive:
            # 域名全部不通时不要卡住: 4 秒试探一次, 失败就直接给分类+筛选
            html = self._get("/index/home.html", timeout=4)
            if html and len(html) >= 300:
                self._alive = True
            else:
                html = ""
                self._ensure_api()
                classes = [{"type_id": c["id"], "type_name": c["name"]}
                           for c in self._classes] or \
                          [{"type_id": cid, "type_name": nm} for cid, nm in self.DEFAULT_CLASSES]
                result["class"] = classes
                for c in classes:
                    result["filters"][c["type_id"]] = self._filters_for(c["type_id"], c["type_name"])
                return result
        else:
            html = self._get("/index/home.html")
            if not html or len(html) < 300:
                html = self._get("/")
        self._ensure_api()
        classes = []
        if self._classes:
            classes = [{"type_id": c["id"], "type_name": c["name"]} for c in self._classes]
        if not classes:
            classes = [{"type_id": c["id"], "type_name": c["name"]}
                       for c in self._parse_classes(html)] if html else []
        if not classes:
            classes = [{"type_id": cid, "type_name": nm} for cid, nm in self.DEFAULT_CLASSES]
        else:
            names = [c["type_name"] for c in classes]
            if "Netflix" not in names and ("netflix" in html or "/label/" in html):
                classes.insert(0, {"type_id": "netflix", "type_name": "Netflix"})
        result["class"] = classes
        for c in classes:
            result["filters"][c["type_id"]] = self._filters_for(c["type_id"], c["type_name"])
        result["list"] = self._parse_list(html)
        return result

    def homeVideoContent(self, *args, **kwargs):
        html = self._get("/index/home.html")
        if not html or len(html) < 300:
            html = self._get("/")
        items = self._parse_list(html)
        if not items:
            for c in self.DEFAULT_CLASSES[1:3]:
                items = self._parse_list(self._get("/vodtype/%s.html" % c[0]))
                if items:
                    break
        return items

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 9999, "limit": 90, "total": 999999}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        ext = self._norm_extend(extend)
        typev = ext.get("type", "") or ""
        area = ext.get("area", "") or ""
        year = ext.get("year", "") or ""
        kw = ""
        qtid = str(tid)
        if typev.startswith("tid:"):
            qtid = typev[4:]
        elif typev.startswith("kw:"):
            kw = typev[3:]
        try:
            if kw:
                result["list"] = self._search_by_kw(kw, pg)
            elif str(tid) == "netflix":
                result["list"] = self._netflix_list(pg)
            else:
                result["list"] = self._cat_list(qtid, area, year, pg)
        except Exception:
            result["list"] = []
        if not result["list"] and (area or year or kw):
            # 筛选条件太苛刻/站点不支持: 退回不带筛选的分类页, 保证不出空页
            try:
                result["list"] = self._cat_list(qtid, "", "", pg)
            except Exception:
                pass
        if result["list"]:
            result["pagecount"] = pg + 1 if len(result["list"]) >= 10 else pg
        return result

    def _norm_extend(self, extend):
        ext = {}
        if not extend:
            return ext
        if isinstance(extend, dict):
            for k, v in extend.items():
                if isinstance(v, (str, int)):
                    ext[str(k)] = str(v)
        elif isinstance(extend, str):
            s = extend.strip()
            if s.startswith("{"):
                try:
                    d = json.loads(s)
                    for k, v in d.items():
                        if isinstance(v, (str, int)):
                            ext[str(k)] = str(v)
                except Exception:
                    pass
        return ext

    def _netflix_list(self, pg):
        url = "/label/netflix.html" if pg <= 1 else "/label/netflix-%d.html" % pg
        items = self._parse_list(self._get(url))
        if not items and pg > 1:
            items = self._parse_list(self._get("/label/netflix.html"))
        return items

    def _cat_urls(self, tid, area, year, pg):
        urls = []
        if area or year:
            parts = [tid, "", area, "", year, "", "", str(pg)]
            urls.append("/vodshow/%s.html" % "-".join(parts))
            urls.append("/index.php/vod/show/id/%s/area/%s/year/%s/page/%s.html"
                        % (tid, urllib.parse.quote(area), urllib.parse.quote(year), pg))
            urls.append("/vodshow/%s-%s-%s-%s-%s---%s.html" % (tid, "", area, "", year, pg))
        if pg > 1:
            urls.append("/vodtype/%s-%d.html" % (tid, pg))
            urls.append("/vodtype/%s/page/%d.html" % (tid, pg))
        urls.append("/vodtype/%s.html" % tid)
        return urls

    def _cat_list(self, tid, area, year, pg):
        for u in self._cat_urls(tid, area, year, pg):
            items = self._parse_list(self._get(u))
            if items:
                return items
        return []

    def _search_by_kw(self, kw, pg):
        q = urllib.parse.quote(kw)
        urls = []
        if pg > 1:
            urls.append("/vodsearch/%s-------------.html?page=%d" % (q, pg))
        urls.append("/vodsearch/%s-------------.html" % q)
        urls.append("/index.php/vod/search.html?wd=%s" % q)
        if pg > 1:
            urls.append("/vodsearch/%s-------------.html?page=%d" % (q, pg))
        for u in urls:
            items = self._parse_list(self._get(u))
            if items:
                return items
        return []

    # ==================== 详情 ====================
    def _detail_url(self, vid):
        vid = str(vid).strip()
        if vid.startswith("http"):
            return vid
        if vid.startswith("/"):
            return self.host + vid
        m = re.search(r'(\d+)', vid)
        if m:
            return "%s/voddetail/%s.html" % (self.host, m.group(1))
        return "%s/voddetail/%s.html" % (self.host, vid)

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = self._detail_url(ids[0])
        except Exception:
            return result
        html_text = self._fetch(url, referer=self.host + "/")
        if not html_text:
            return result
        vod = {"vod_id": url}
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
        if m:
            vod["vod_name"] = self._clean(m.group(1))
        if not vod.get("vod_name"):
            m = re.search(r'<title>(.*?)</title>', html_text, re.S)
            vod["vod_name"] = self._clean(m.group(1)).split("-")[0] if m else "未知影片"
        pic = ""
        m = re.search(r'data-original="([^"]+)"[^>]*alt="([^"]+)"[^>]*class="module-item-pic"', html_text)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'<div class="module-item-pic"[^>]*>.*?<img[^>]+data-original="([^"]+)"',
                          html_text, re.S)
            if m:
                pic = m.group(1)
        if not pic:
            m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html_text)
            if m:
                pic = m.group(1)
        vod["vod_pic"] = self._abs(pic) if pic else self.DEFAULT_PIC
        # 简介 (公众号置顶)
        desc = ""
        m = re.search(r'<div class="module-info-introduction-content[^"]*"[^>]*>(.*?)</div>',
                      html_text, re.S)
        if m:
            desc = self._clean(m.group(1))
        if not desc:
            m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html_text)
            if m:
                desc = self._clean(m.group(1))
        vod["vod_content"] = self.WX_TEXT + "\n" + (desc[:800] if desc else "")
        for label, key in (("年份", "vod_year"), ("地区", "vod_area"), ("类型", "vod_type")):
            mm = re.search(label + r'[：:]\s*(?:<[^>]+>\s*)*([^<\s]{1,24})', html_text)
            if mm:
                vod[key] = self._clean(mm.group(1))
        vod["vod_remarks"] = ""
        rm = re.search(r'class="module-info-item-content"[^>]*>([^<]{1,40})<', html_text)
        if rm:
            vod["vod_remarks"] = self._clean(rm.group(1))
        # 播放列表
        eps = re.findall(r'href="(/vodplay/\d+-(\d+)-(\d+)\.html)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]+?)\s*<',
                         html_text)
        if not eps:
            eps = re.findall(r'href="(/vodplay/\d+-(\d+)-(\d+)\.html)"', html_text)
            eps = [(a, b, c, "第%s集" % d) for (a, b, c, d) in
                   [(x[0], x[1], x[2], x[2]) for x in eps]]
        names = []
        for nm in re.findall(r'data-dropdown-value="([^"]+)"', html_text):
            nm = self._clean(nm)
            if nm and nm not in names:
                names.append(nm)
        sources = {}
        order = []
        for href, sid, epid, epname in eps:
            sid = str(sid)
            if sid not in sources:
                sources[sid] = []
                order.append(sid)
            epname = self._clean(epname) or ("第%s集" % epid)
            sources[sid].append((int(epid), "%s$%s%s" % (epname, self.host, href)))
        if sources:
            froms = []
            urls = []
            for i, sid in enumerate(order):
                label = names[i] if i < len(names) else "线路%d" % (i + 1)
                froms.append(label)
                eps_list = [x[1] for x in sorted(sources[sid], key=lambda y: y[0])]
                urls.append("#".join(eps_list))
            vod["vod_play_from"] = "$$$".join(froms)
            vod["vod_play_url"] = "$$$".join(urls)
        else:
            m = re.search(r'"url"\s*:\s*"([^"]+?\.(?:m3u8|mp4)[^"]*)"', html_text)
            if m:
                vod["vod_play_from"] = "大米星球"
                vod["vod_play_url"] = "正片$" + self._abs(m.group(1))
            else:
                vod["vod_play_from"] = "大米星球"
                vod["vod_play_url"] = ""
        result["list"].append(vod)
        return result

    # ==================== 搜索 ====================
    def searchContent(self, key, quick=False, pg="1"):
        result = {"list": [], "page": int(pg) if str(pg).isdigit() else 1,
                  "pagecount": 9999, "limit": 90, "total": 999999}
        try:
            result["list"] = self._search_by_kw(key, int(result["page"]))
        except Exception:
            result["list"] = []
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 1, "playUrl": "", "url": id if str(id).startswith("http") else
                  self._detail_url(id), "header": {"Referer": self.host + "/"}}
        try:
            url = result["url"]
            if url.endswith(".m3u8") or url.endswith(".mp4"):
                result["parse"] = 0
                return result
            page = self._fetch(url, referer=self.host + "/")
            real = self._extract_play_url(page)
            if real:
                result["url"] = real
                result["parse"] = 0
                result["header"] = {"Referer": self.host + "/",
                                    "User-Agent": self.UA}
            else:
                result["parse"] = 1
        except Exception:
            result["parse"] = 1
        return result

    def _extract_play_url(self, page):
        if not page:
            return ""
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', page, re.S)
        cfg = None
        if m:
            try:
                cfg = json.loads(m.group(1))
            except Exception:
                cfg = None
        if not cfg:
            m = re.search(r'player_[a-z]*\s*=\s*(\{[^\n]*?\})\s*;?\s*</script>', page, re.S)
            if m:
                try:
                    cfg = json.loads(m.group(1))
                except Exception:
                    cfg = None
        if cfg and cfg.get("url"):
            u = cfg["url"]
            enc = str(cfg.get("encrypt", 0))
            try:
                if enc == "1":
                    u = urllib.parse.unquote(u)
                elif enc == "2":
                    u = base64.b64decode(u + "===").decode("utf-8", "ignore")
            except Exception:
                pass
            u = u.replace("\\/", "/")
            if u.startswith("//"):
                u = "https:" + u
            if u.startswith("http"):
                return u
        m = re.search(r'["\'](https?://[^"\']+?\.(?:m3u8|mp4)[^"\']*)["\']', page)
        if m:
            return m.group(1).replace("\\/", "/")
        return ""


if __name__ == "__main__":
    sp = Spider()
    sp.init(sys.argv[1] if len(sys.argv) > 1 else "")
    print("域名: %s" % sp.host)
    home = sp.homeContent(True)
    print("分类: %s" % [(c["type_id"], c["type_name"]) for c in home["class"]])
    for c in home["class"]:
        fs = home["filters"].get(c["type_id"]) or []
        print("  %s -> %s" % (c["type_name"], [(f["name"], len(f["value"])) for f in fs]))
    print("首页推荐: %d" % len(home["list"]))
    if home["class"]:
        tid = home["class"][1]["type_id"] if len(home["class"]) > 1 else home["class"][0]["type_id"]
        r = sp.categoryContent(tid, "1", True, {})
        print("分类 %s 第1页: %d" % (tid, len(r["list"])))
        r2 = sp.categoryContent(tid, "1", True, {"type": "kw:科幻", "area": "日本"})
        print("分类 %s 筛选: %d" % (tid, len(r2["list"])))
        if r["list"]:
            d = sp.detailContent([r["list"][0]["vod_id"]])
            if d["list"]:
                v = d["list"][0]
                print("详情: %s | 线路: %s" % (v.get("vod_name"), v.get("vod_play_from")))
                print("简介: %s" % v.get("vod_content", "")[:40].replace("\n", " "))
                purl = (v.get("vod_play_url") or "").split("$")[-1]
                if purl:
                    p = sp.playerContent("", purl, None)
                    print("播放: parse=%s url=%s" % (p["parse"], p["url"]))
    s = sp.searchContent("星际", False, "1")
    print("搜索: %d" % len(s["list"]))
