# -*- coding: utf-8 -*-
"""
目标站: 秒看电影 (miaokan.cc)
站点地址: https://miaokan.cc/
站点类型: 综合影视 (电影 / 连续剧 / 综艺 / 动漫 / 短剧 / 影视解说)
模板结构: 苹果CMS (MacCMS) + ewave 模板

    /                                   首页
    /mk/{slug}/                         频道页 (含子分类)
    /mk-kan/{类型}-{地区}-{排序}-{类型细分}-{语言}-{}-{}-{}-{页码}-{}-{}-{年份}/  列表页
    /miaokan/{id}/                      详情页
    /mkvod/{id}-{源}-{集}/               播放页 (内含 m3u8 直链)
    /ajax/suggest/?mid=1&wd={关键词}     搜索接口 (JSON, 免验证码)

URL 段位说明 (共 12 段, 以 "-" 分隔):
    0=频道/子分类  1=地区  2=排序  3=类型(剧情)  4=语言  8=页码  11=年份

功能 (写法参考 网飞猫.py):
    - homeContent: 一级分类 + 每类全部二级筛选 (分类/类型/地区/语言/年份/排序)
    - 二级筛选优先从站点 /mk-kan/ 页动态抓取, 抓取失败回退内置数据
    - 影视类型细化: 电影(科幻片/奇幻片/战争片/犯罪片/武侠片/历史片/文艺片...)
                     电视剧(古装剧/都市剧/历史剧/谍战剧/家庭剧...)
      (站点菜单里"科幻片""爱情片"等写法实际查不到数据, 已按实测结果换成真实取值)
    - categoryContent / searchContent / detailContent / playerContent
    - 播放解析出 m3u8 直链, parse=0 交给 TVBox 直接播放
    - 影片简介处添加 微信公众号 "源力软件汇"
"""
import re
import sys
import json
import time
import ssl
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
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # 域名 (按顺序尝试, 失败自动切换)
    DOMAINS = [
        "https://miaokan.cc",
        "https://www.miaokan.cc",
    ]

    HOST = DOMAINS[0]

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # 推广文案 (写入影片简介)
    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n"
        "QQ群：1054592152"
    )

    # ==================== 一级分类 (与站点导航一致) ====================
    CATEGORIES = [
        {"type_id": "dianying", "type_name": "电影"},
        {"type_id": "lianxuju", "type_name": "连续剧"},
        {"type_id": "zongyi", "type_name": "综艺"},
        {"type_id": "dongman", "type_name": "动漫"},
        {"type_id": "duanju", "type_name": "短剧"},
        {"type_id": "yingshijieshuo", "type_name": "影视解说"},
    ]

    # ==================== 子分类 (站点导航二级, 写在 URL 第 0 段) ====================
    SUB_TYPES = {
        "dianying": [
            ("dongzuopian", "动作片"), ("xijupian", "喜剧片"), ("aiqingpian", "爱情片"),
            ("kehuanpian", "科幻片"), ("kongbupian", "恐怖片"), ("juqingpian", "剧情片"),
            ("jilupian", "纪录片"), ("zhanzhengpian", "战争片"),
            ("xuanyipian", "悬疑片"),
            # 站点导航里的 "奇幻片"(qihuanpian) 实测无数据, 改由类型筛选里的"奇幻片"覆盖
        ],
        "lianxuju": [
            ("guochanju", "国产剧"), ("gangtaiju", "港台剧"), ("rihanju", "日韩剧"),
            ("oumeiju", "欧美剧"), ("haiwaiju", "海外剧"),
        ],
        "zongyi": [
            ("daluzongyi", "大陆综艺"), ("rihanzongyi", "日韩综艺"),
            ("gangtaizongyi", "港台综艺"), ("oumeizongyi", "欧美综艺"),
            # 站点导航里的 "海外综艺"(haiwaizongyi) 实测无数据, 已移除
        ],
        "dongman": [
            ("guochandongman", "国产动漫"), ("rihandongman", "日韩动漫"),
            ("gangtaidongman", "港台动漫"), ("oumeidongman", "欧美动漫"),
            ("haiwaidongman", "海外动漫"), ("donghuapian", "动画"),
        ],
        "duanju": [
            ("nvpinlianai", "女频恋爱"), ("fanzhuanshuangju", "反转爽剧"),
            ("guzhuangxianxia", "古装仙侠"), ("niandaichuanyue", "年代穿越"),
            ("naodongxuanyi", "脑洞悬疑"), ("xiandaidushi", "现代都市"),
        ],
        "yingshijieshuo": [],
    }

    # ==================== URL 段位 ====================
    SEG_TYPE = 0     # 频道 / 子分类
    SEG_AREA = 1     # 地区
    SEG_SORT = 2     # 排序
    SEG_CLASS = 3    # 类型(剧情)
    SEG_LANG = 4     # 语言
    SEG_PAGE = 8     # 页码
    SEG_YEAR = 11    # 年份
    SEG_COUNT = 12   # 段位总数

    # ==================== 类型(剧情)筛选项 ====================
    # (展示名, 站点真实 class 取值) —— 全部经过线上实测, 保证每项都有数据
    # 站点菜单里的 "科幻片""爱情片""网络电影" 等写法实际查不到数据, 这里统一换成真实取值
    _CLASS_TABLE = {
        "dianying": [
            ("剧情片", "剧情"), ("喜剧片", "喜剧"), ("动作片", "动作"),
            ("恐怖片", "恐怖"), ("爱情片", "爱情"), ("纪录片", "记录"),
            ("惊悚片", "惊悚"), ("科幻片", "科幻"), ("悬疑片", "悬疑"),
            ("犯罪片", "犯罪"), ("战争片", "战争"), ("冒险片", "冒险"),
            ("古装片", "古装"), ("奇幻片", "奇幻"), ("历史片", "历史"),
            ("青春片", "青春"), ("武侠片", "武侠"), ("家庭剧", "家庭"),
            ("儿童片", "儿童"), ("情感片", "情感"), ("美食", "美食"),
            ("动画", "动画"), ("校园", "校园"), ("热血", "热血"),
            ("励志片", "励志"), ("乡村剧", "农村"), ("警匪片", "警匪"),
            ("运动片", "运动"), ("搞笑", "搞笑"), ("穿越", "穿越"),
            ("重生", "重生"), ("复仇", "复仇"), ("推理", "推理"),
            ("枪战片", "枪战"), ("谍战片", "谍战"), ("经典", "经典"),
            ("都市剧", "都市"), ("微电影", "微电影"),
        ],
        "lianxuju": [
            ("剧情剧", "剧情"), ("爱情剧", "爱情"), ("喜剧", "喜剧"),
            ("犯罪剧", "犯罪"), ("悬疑剧", "悬疑"), ("古装剧", "古装"),
            ("家庭剧", "家庭"), ("惊悚剧", "惊悚"), ("动作剧", "动作"),
            ("历史剧", "历史"), ("战争剧", "战争"), ("奇幻剧", "奇幻"),
            ("科幻剧", "科幻"), ("武侠剧", "武侠"), ("青春", "青春"),
            ("恐怖", "恐怖"), ("都市剧", "都市"), ("复仇", "复仇"),
            ("情感", "情感"), ("美食", "美食"), ("校园", "校园"),
            ("穿越", "穿越"), ("热血", "热血"), ("乡村剧", "乡村"),
            ("警匪", "警匪"), ("网剧", "网剧"), ("推理", "推理"),
            ("儿童", "儿童"), ("逆袭", "逆袭"), ("经典", "经典"),
            ("重生", "重生"), ("搞笑", "搞笑"), ("冒险", "冒险"),
            ("谍战剧", "谍战"), ("励志", "励志"), ("纪录片", "记录"),
            ("商战", "商战"), ("赘婿", "赘婿"), ("运动", "运动"),
            # 地区型分类(详情页取到的真实取值)
            ("国产剧", "国产"), ("欧美剧", "欧美"), ("海外剧", "海外"),
        ],
        "zongyi": [
            ("大陆综艺", "大陆综艺"), ("日韩综艺", "日韩综艺"),
            ("港台综艺", "港台综艺"), ("欧美综艺", "欧美综艺"),
            ("音乐", "音乐"), ("生活", "生活"), ("美食", "美食"),
            ("青春", "青春"), ("喜剧", "喜剧"), ("爱情", "爱情"),
            ("推理", "推理"), ("运动", "运动"), ("情感", "情感"),
            ("剧情", "剧情"), ("旅游", "旅游"), ("家庭", "家庭"),
            ("经典", "经典"), ("访谈", "访谈"), ("纪实", "纪实"),
            ("励志", "励志"), ("热血", "热血"), ("文艺", "文艺"),
            ("战争", "战争"), ("冒险", "冒险"), ("历史", "历史"),
            ("选秀", "选秀"), ("乡村", "乡村"), ("记录", "记录"),
            ("搞笑", "搞笑"), ("原创", "原创"), ("穿越", "穿越"),
            ("亲子", "亲子"), ("播报", "播报"), ("曲艺", "曲艺"),
            ("财经", "财经"), ("求职", "求职"), ("纪录片", "纪录片"),
        ],
        "dongman": [
            ("日韩动漫", "日韩动漫"), ("国产动漫", "国产动漫"),
            ("动画", "动画"), ("欧美动漫", "欧美动漫"),
            ("海外动漫", "海外动漫"), ("港台动漫", "港台动漫"),
            ("冒险", "冒险"), ("少女", "少女"), ("剧情", "剧情"),
            ("少年", "少年"), ("动作", "动作"), ("科幻", "科幻"),
            ("爱情", "爱情"), ("搞笑", "搞笑"), ("奇幻", "奇幻"),
            ("喜剧", "喜剧"), ("生活", "生活"), ("重生", "重生"),
            ("热血", "热血"), ("家庭", "家庭"), ("都市", "都市"),
            ("逆袭", "逆袭"), ("音乐", "音乐"), ("经典", "经典"),
            ("青春", "青春"), ("穿越", "穿越"), ("战争", "战争"),
            ("复仇", "复仇"), ("恐怖", "恐怖"), ("儿童", "儿童"),
            ("犯罪", "犯罪"), ("校园", "校园"), ("历史", "历史"),
            ("美食", "美食"), ("赘婿", "赘婿"), ("悬疑", "悬疑"),
            ("运动", "运动"), ("萝莉", "萝莉"), ("推理", "推理"),
            ("情感", "情感"), ("励志", "励志"), ("益智", "益智"),
            ("武侠", "武侠"), ("亲子", "亲子"),
        ],
        "duanju": [
            ("都市", "都市"), ("穿越", "穿越"), ("古装", "古装"),
            ("重生", "重生"), ("言情", "言情"), ("逆袭", "逆袭"),
            ("悬疑", "悬疑"), ("剧情", "剧情"), ("家庭", "家庭"),
            ("情感", "情感"), ("赘婿", "赘婿"), ("复仇", "复仇"),
            ("爱情", "爱情"), ("神豪", "神豪"), ("少年", "少年"),
            ("商战", "商战"), ("励志", "励志"), ("生活", "生活"),
            ("乡村", "乡村"), ("少女", "少女"), ("青春", "青春"),
            ("奇幻", "奇幻"), ("农村", "农村"), ("美食", "美食"),
            ("校园", "校园"), ("热血", "热血"), ("亲子", "亲子"),
            ("搞笑", "搞笑"), ("虐恋", "虐恋"), ("犯罪", "犯罪"),
            ("恐怖", "恐怖"), ("动画", "动画"), ("音乐", "音乐"),
            ("武侠", "武侠"), ("冒险", "冒险"), ("经典", "经典"),
            ("记录", "记录"), ("萝莉", "萝莉"), ("社会", "社会"),
            ("战争", "战争"), ("历史", "历史"),
        ],
        "yingshijieshuo": [
            ("恐怖", "恐怖"), ("生活", "生活"), ("复仇", "复仇"),
            ("爱情", "爱情"), ("少年", "少年"), ("少女", "少女"),
            ("剧情", "剧情"), ("犯罪", "犯罪"), ("战争", "战争"),
            ("惊悚", "惊悚"), ("社会", "社会"), ("家庭", "家庭"),
            ("青春", "青春"), ("冒险", "冒险"), ("音乐", "音乐"),
            ("都市", "都市"), ("奇幻", "奇幻"), ("校园", "校园"),
            ("重生", "重生"), ("动作", "动作"), ("喜剧", "喜剧"),
            ("穿越", "穿越"), ("运动", "运动"), ("警匪", "警匪"),
            ("热血", "热血"), ("记录", "记录"), ("纪录片", "纪录片"),
        ],
    }

    # 站点菜单里存在但实测查不到数据的类型 (直接丢弃)
    _CLASS_DEAD = {
        "dianying": {"网络电影"},
        "lianxuju": {"港台剧", "日韩剧", "青春偶像"},
        "zongyi": {"海外综艺", "游戏互动"},
        "dongman": {"其他"},
        "duanju": {"其他", "情景", "网剧", "推理", "机战", "原创", "益智",
                   "访谈", "纪实", "曲艺", "游戏互动", "财经", "动作", "枪战"},
        "yingshijieshuo": {"古装", "青春偶像"},
    }

    # ==================== 内置筛选数据 (动态抓取失败时回退) ====================
    _FB_AREA = {
        "dianying": ["大陆", "香港", "台湾", "美国", "法国", "英国", "日本", "韩国",
                     "德国", "泰国", "印度", "意大利", "西班牙", "加拿大", "其他"],
        "lianxuju": ["内地", "韩国", "香港", "台湾", "日本", "美国",
                     "泰国", "英国", "新加坡", "其他"],
        "zongyi": ["内地", "港台", "日韩", "欧美"],
        "dongman": ["国产", "日本", "欧美", "其他"],
        "duanju": ["中国大陆", "中国香港", "中国台湾", "其他"],
        "yingshijieshuo": ["大陆", "香港", "台湾", "美国"],
    }

    _FB_LANG = {
        "dianying": ["国语", "英语", "粤语", "闽南语", "韩语", "日语", "法语", "德语", "其它"],
        "lianxuju": ["国语", "英语", "粤语", "闽南语", "韩语", "日语", "其它"],
        "zongyi": ["国语", "英语", "粤语", "闽南语", "韩语", "日语", "其它"],
        "dongman": ["国语", "英语", "粤语", "闽南语", "韩语", "日语", "其它"],
        "duanju": ["国语", "英语", "粤语", "闽南语", "韩语", "日语", "法语", "德语", "其它"],
        "yingshijieshuo": ["国语", "英语", "粤语"],
    }

    _FB_SORT = [("最近更新", "time"), ("最多播放", "hits"), ("最好评", "score")]

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.HOST
        self._filters_cache = {}          # tid -> filters list
        self._filters_cache_ts = {}
        self._cache_filters_ttl = 6 * 3600
        self._search_cache = {}            # key -> (ts, list)
        self._search_ttl = 300
        self._detect_host()

    def getName(self):
        return "秒看"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== 域名 / 请求 ====================
    def _detect_host(self):
        """探测可用域名"""
        for domain in self.DOMAINS:
            try:
                html = self._fetch("/", host=domain)
                if html and len(html) > 2000:
                    self.host = domain
                    return True
            except Exception:
                continue
        self.host = self.DOMAINS[0]
        return False

    def _switch_host(self):
        """切换到下一个镜像域名"""
        try:
            idx = self.DOMAINS.index(self.host)
        except ValueError:
            idx = 0
        self.host = self.DOMAINS[(idx + 1) % len(self.DOMAINS)]
        return self.host

    def _fetch_raw(self, url, referer=None, timeout=20):
        """底层 HTTP GET"""
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
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            try:
                return e.read()
            except Exception:
                return b""
        except Exception:
            return b""

    def _decode(self, data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _fetch(self, path, referer=None, host=None, raw=False):
        """统一 GET, 失败自动切换域名"""
        base = host or self.host
        url = path if path.startswith("http") else base + path
        for _ in range(len(self.DOMAINS) + 1):
            data = self._fetch_raw(url, referer=referer or (base + "/"))
            if data:
                if raw:
                    return data
                return self._decode(data)
            self._switch_host()
            base = self.host
            url = path if path.startswith("http") else base + path
        return b"" if raw else ""

    def _get(self, path, referer=None):
        return self._fetch(path, referer=referer)

    # ==================== 工具方法 ====================
    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"[ \t\r\f\v]+", " ", text).strip()

    def _img_src(self, url):
        if not url:
            return ""
        url = url.strip()
        if "logo_placeholder" in url or url.endswith(".ico"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    # ==================== 筛选器 ====================
    def _build_path(self, tid, extend, pg):
        """按 TVBox extend 拼出 /mk-kan/ 列表 URL"""
        seg = [""] * self.SEG_COUNT
        seg[self.SEG_TYPE] = tid
        if not isinstance(extend, dict):
            extend = {}
        for key, pos in (("area", self.SEG_AREA), ("sort", self.SEG_SORT),
                         ("class", self.SEG_CLASS), ("lang", self.SEG_LANG),
                         ("year", self.SEG_YEAR)):
            val = extend.get(key)
            if val is None:
                continue
            val = str(val).strip()
            if val and val != "全部":
                seg[pos] = val
        sub = extend.get("sub")
        if sub:
            sub = str(sub).strip()
            if sub and sub != "全部":
                seg[self.SEG_TYPE] = sub
        seg[self.SEG_PAGE] = str(pg)
        return "/mk-kan/" + "-".join(
            urllib.parse.quote(s) if s else "" for s in seg) + "/"

    def _base_parts(self, tid):
        """基准 (无筛选) URL 的段位数组"""
        parts = [""] * self.SEG_COUNT
        parts[self.SEG_TYPE] = tid
        return parts

    def _parse_filter_options(self, html, tid):
        """从 /mk-kan/ 页解析全部筛选项, 返回 {段位: [(展示名, 取值)]}

        每个筛选项的链接本身就是带该条件的 URL,
        与基准 URL 逐段比较即可得知它设置的是第几段, 以及真实取值。
        """
        base = self._base_parts(tid)
        groups = {}
        for m in re.finditer(
                r'<dl class="clearfix">\s*<dt><span>([^<]*)</span></dt>(.*?)</dl>',
                html, re.S):
            body = m.group(2)
            opts = re.findall(
                r'<a class="swiper-slide[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]*)</a>',
                body)
            for href, text in opts:
                name = self.clean(text)
                if not name:
                    continue
                pos, value = self._option_pos(href, base)
                if pos is None:
                    continue
                groups.setdefault(pos, [])
                groups[pos].append((name, value))
        return groups

    def _option_pos(self, href, base):
        """由筛选项链接推断它设置的是第几段及真实取值

        与基准 URL 逐段比较, 只有一段不同时该段即为筛选段位;
        第 0 段是频道(切换分类)与"全部"选项, 均不作为筛选项。
        """
        if "/mk-kan/" not in href:
            return None, ""
        seg = href.split("/mk-kan/", 1)[1].strip("/").split("/")[0]
        parts = seg.split("-")
        if len(parts) != self.SEG_COUNT:
            return None, ""
        diff = [i for i in range(self.SEG_COUNT) if parts[i] != base[i]]
        if len(diff) != 1:
            return None, ""
        pos = diff[0]
        if pos == self.SEG_TYPE:
            return None, ""
        value = urllib.parse.unquote(parts[pos])
        if not value:
            return None, ""
        return pos, value

    def _refine_class(self, tid, dynamic=None):
        """类型筛选项: 以实测表为准, 再补充站点新增的类型"""
        table = self._CLASS_TABLE.get(tid, [])
        dead = self._CLASS_DEAD.get(tid, set())
        table_values = set(v for _, v in table)
        result = []
        used_v = set()
        used_n = set()

        def add(display, value):
            if not display or not value:
                return
            if value in used_v or display in used_n:
                return
            used_v.add(value)
            used_n.add(display)
            result.append((display, value))

        for display, value in table:
            add(display, value)

        for name, value in (dynamic or []):
            if not name or not value:
                continue
            if name in dead or value in dead:
                continue
            if value in used_v or name in used_n:
                continue
            base = value
            while base and base[-1] in "片剧":
                base = base[:-1]
            if base in table_values:
                # 站点写法带"片/剧"后缀且查不到数据, 表内已有正确取值
                continue
            add(name, value)
        return result

    def _fallback_filters(self, tid):
        """内置筛选数据 (站点不可用时的回退)"""
        f = []
        subs = self.SUB_TYPES.get(tid, [])
        if subs:
            f.append({
                "key": "sub", "name": "分类",
                "value": [{"n": "全部", "v": ""}] +
                        [{"n": n, "v": v} for v, n in subs],
            })
        classes = self._refine_class(tid)
        if classes:
            f.append({
                "key": "class", "name": "类型",
                "value": [{"n": "全部", "v": ""}] +
                        [{"n": n, "v": v} for n, v in classes],
            })
        areas = self._FB_AREA.get(tid, [])
        if areas:
            f.append({
                "key": "area", "name": "地区",
                "value": [{"n": "全部", "v": ""}] +
                        [{"n": a, "v": a} for a in areas],
            })
        langs = self._FB_LANG.get(tid, [])
        if langs:
            f.append({
                "key": "lang", "name": "语言",
                "value": [{"n": "全部", "v": ""}] +
                        [{"n": l, "v": l} for l in langs],
            })
        f.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] +
                    [{"n": str(y), "v": str(y)} for y in range(2026, 1999, -1)],
        })
        f.append({
            "key": "sort", "name": "排序",
            "value": [{"n": n, "v": v} for n, v in self._FB_SORT],
        })
        return f

    def _get_filters(self, tid):
        """获取某分类的全部筛选器 (带缓存, 失败回退内置)"""
        tid = str(tid)
        now = time.time()
        if tid in self._filters_cache and \
                (now - self._filters_cache_ts.get(tid, 0)) < self._cache_filters_ttl:
            return self._filters_cache[tid]

        filters = []
        try:
            html = self._get("/mk-kan/%s-----------/" % tid)
            if html and len(html) > 3000:
                groups = self._parse_filter_options(html, tid)
                # 分类(子分类)组
                subs = self.SUB_TYPES.get(tid, [])
                if subs:
                    filters.append({
                        "key": "sub", "name": "分类",
                        "value": [{"n": "全部", "v": ""}] +
                                [{"n": n, "v": v} for v, n in subs],
                    })
                # 类型组
                classes = self._refine_class(tid, groups.get(self.SEG_CLASS, []))
                if classes:
                    filters.append({
                        "key": "class", "name": "类型",
                        "value": [{"n": "全部", "v": ""}] +
                                [{"n": n, "v": v} for n, v in classes],
                    })
                # 地区组
                areas = groups.get(self.SEG_AREA, [])
                if areas:
                    filters.append({
                        "key": "area", "name": "地区",
                        "value": [{"n": "全部", "v": ""}] +
                                [{"n": n, "v": v} for n, v in areas],
                    })
                # 语言组
                langs = groups.get(self.SEG_LANG, [])
                if langs:
                    filters.append({
                        "key": "lang", "name": "语言",
                        "value": [{"n": "全部", "v": ""}] +
                                [{"n": n, "v": v} for n, v in langs],
                    })
                # 年份组
                years = groups.get(self.SEG_YEAR, [])
                if years:
                    filters.append({
                        "key": "year", "name": "年份",
                        "value": [{"n": "全部", "v": ""}] +
                                [{"n": n, "v": v} for n, v in years],
                    })
                # 排序组
                sorts = groups.get(self.SEG_SORT, [])
                if sorts:
                    filters.append({
                        "key": "sort", "name": "排序",
                        "value": [{"n": n, "v": v} for n, v in sorts],
                    })
        except Exception:
            filters = []

        if not filters:
            filters = self._fallback_filters(tid)
        self._filters_cache[tid] = filters
        self._filters_cache_ts[tid] = now
        return filters

    # ==================== 卡片解析 ====================
    def _parse_cards(self, html):
        """解析视频卡片列表"""
        items = []
        seen = set()
        for m in re.finditer(r'<li class="col-xs-4[^"]*">(.*?)</li>', html, re.S):
            block = m.group(1)
            dm = re.search(r'href="(/miaokan/(\d+)/)"[^>]*title="([^"]*)"', block)
            if not dm:
                continue
            vid = dm.group(2)
            if vid in seen:
                continue
            name = self.clean(dm.group(3))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-original="([^"]*)"', block)
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            rm = re.search(r'item-status[^>]*>([^<]*)<', block)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_total(self, html):
        """解析结果总数"""
        m = re.search(r'\$\("\.ewave-total"\)\.text\((\d+)\)', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        m = re.search(r'ewave-total">(\d+)</span>', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        return 0

    def _parse_pagecount(self, html, page):
        """解析总页数"""
        m = re.search(r'class="num">\s*(\d+)\s*/\s*(\d+)\s*</span>', html)
        if m:
            try:
                return int(m.group(2))
            except Exception:
                pass
        total = self._parse_total(html)
        if total:
            return max(1, (total + 35) // 36)
        return page

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """首页: 一级分类 + 各分类全部二级筛选 + 推荐视频"""
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            filters[c["type_id"]] = self._get_filters(c["type_id"])
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self._get("/")
            if not html:
                return result
            # 热门推荐区块
            start = html.find('id="index-box"')
            if start >= 0:
                end = html.find('id="index-vod-', start + 10)
                if end < 0:
                    end = len(html)
                result["list"] = self._parse_cards(html[start:end])
            if not result["list"]:
                result["list"] = self._parse_cards(html)
        except Exception:
            pass
        return result

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        tid = str(tid)
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            path = self._build_path(tid, extend, page)
            html = self._get(path)
            if not html or len(html) < 2000:
                return result
            videos = self._parse_cards(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = self._parse_total(html)
            result["pagecount"] = self._parse_pagecount(html, page)
        except Exception:
            pass
        return result

    # ==================== 搜索 ====================
    def _fetch_suggest(self, key):
        """调用站点搜索接口 (JSON, 免验证码)"""
        url = "/ajax/suggest/?mid=1&wd=%s&limit=200" % urllib.parse.quote(key)
        data = self._fetch(url, raw=True)
        if not data:
            return []
        try:
            j = json.loads(self._decode(data))
        except Exception:
            return []
        if not isinstance(j, dict) or j.get("code") != 1:
            return []
        out = []
        for it in j.get("list") or []:
            vid = it.get("id")
            name = self.clean(it.get("name"))
            if not vid or not name:
                continue
            out.append({
                "vod_id": str(vid),
                "vod_name": name,
                "vod_pic": self._img_src(it.get("pic")) or self.DEFAULT_PIC,
                "vod_remarks": "",
            })
        return out

    def _search_all(self, key):
        """搜索结果缓存"""
        now = time.time()
        hit = self._search_cache.get(key)
        if hit and (now - hit[0]) < self._search_ttl:
            return hit[1]
        items = self._fetch_suggest(key)
        self._search_cache[key] = (now, items)
        return items

    def _do_search(self, key, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        if not key:
            return result
        try:
            items = self._search_all(key)
        except Exception:
            items = []
        total = len(items)
        size = 30
        pagecount = max(1, (total + size - 1) // size)
        start = (page - 1) * size
        chunk = items[start:start + size]
        result["list"] = chunk
        result["limit"] = len(chunk)
        result["total"] = total
        result["pagecount"] = pagecount
        return result

    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip()
        if not vid:
            return result
        try:
            html = self._get("/miaokan/%s/" % vid)
        except Exception:
            html = ""
        if not html or len(html) < 2000:
            return result

        vod = {"vod_id": vid}

        # 标题
        name = ""
        m = re.search(r'<div class="vod-info[^"]*">.*?<div class="info">\s*<h3>(.*?)</h3>',
                      html, re.S)
        if m:
            name = self.clean(m.group(1))
        if not name:
            m = re.search(r'<title>([^<]*)</title>', html)
            if m:
                name = self.clean(re.sub(r"[-_|].*$", "", self.clean(m.group(1))))
        vod["vod_name"] = name if name else vid

        # 封面
        pic = ""
        m = re.search(r'<div class="vod-info[^"]*">.*?<div class="pic">(.*?)</div>',
                      html, re.S)
        if m:
            pm = re.search(r'data-original="([^"]*)"', m.group(1))
            if pm:
                pic = self._img_src(pm.group(1))
        if not pic:
            pm = re.search(r'data-original="([^"]*)"', html)
            if pm:
                pic = self._img_src(pm.group(1))
        vod["vod_pic"] = pic if pic else self.DEFAULT_PIC

        # 信息行: 分类/地区/年份/导演/主演/状态
        info = {}
        m = re.search(r'<div class="info">(.*?)<div class="btn-box">', html, re.S)
        if m:
            for sm in re.finditer(r'<span class="[^"]*">([^：:]{1,6})[：:](.*?)</span>',
                                  m.group(1), re.S):
                label = self.clean(sm.group(1))
                body = sm.group(2)
                links = re.findall(r'<a[^>]*>(.*?)</a>', body, re.S)
                if links:
                    texts = [self.clean(x) for x in links]
                    texts = [t for t in texts if t]
                    value = ",".join(texts) if texts else self.clean(body)
                else:
                    value = self.clean(body)
                if label and value:
                    info.setdefault(label, value)

        vod["vod_area"] = info.get("地区", "")
        vod["vod_year"] = info.get("年份", "")
        vod["vod_director"] = info.get("导演", "")
        vod["vod_actor"] = info.get("主演", "").replace(",", ", ")
        vod["vod_remarks"] = info.get("状态", "")

        # 类型: 分类栏最后一个链接才是真实 class 取值
        tid, vod_class = self._parse_detail_class(html)
        if not vod_class:
            vod_class = info.get("分类", "")
        vod["vod_type"] = self._type_display(vod_class, tid)

        # 简介 + 推广文案 (置于最前)
        desc = self._detail_desc(html)
        vod["vod_content"] = self.WX_TEXT + ("\n\n" + desc if desc else "")

        # 播放源 + 选集
        from_arr, url_arr = self._detail_plays(html)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            m = re.search(r'href="(/mkvod/%s-\d+-\d+/)"' % re.escape(vid), html)
            vod["vod_play_from"] = "秒看线路"
            vod["vod_play_url"] = "播放$%s%s" % (
                self.host, m.group(1) if m else "/mkvod/%s-1-1/" % vid)

        result["list"] = [vod]
        return result

    def _channel_of(self, slug):
        """slug (频道或子分类) -> 一级分类 id"""
        slug = (slug or "").strip()
        if not slug:
            return ""
        for c in self.CATEGORIES:
            if c["type_id"] == slug:
                return c["type_id"]
        for tid, subs in self.SUB_TYPES.items():
            for s, _n in subs:
                if s == slug:
                    return tid
        return ""

    def _parse_detail_class(self, html):
        """从详情页分类栏解析 (一级分类, 真实 class 取值)"""
        tid = ""
        value = ""
        m = re.search(r'<span class="[^"]*">分类[：:](.*?)</span>', html, re.S)
        if not m:
            return tid, value
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', m.group(1), re.S)
        links = [(h, self.clean(t)) for h, t in links]
        links = [(h, t) for h, t in links if t]
        if not links:
            return tid, value
        # 第一个链接指向频道/子分类页
        ms = re.search(r'/mk/([^/]+)/', links[0][0])
        if ms:
            tid = self._channel_of(ms.group(1))
        # 最后一个链接的 URL 第 3 段是真实 class 取值
        for href, text in reversed(links):
            if "/mk-kan/" in href:
                seg = href.split("/mk-kan/", 1)[1].strip("/").split("/")[0]
                parts = seg.split("-")
                if len(parts) == self.SEG_COUNT and parts[self.SEG_CLASS]:
                    value = urllib.parse.unquote(parts[self.SEG_CLASS])
                    break
        if not value:
            value = links[-1][1]
        return tid, value

    def _type_display(self, name, tid=""):
        """把真实 class 取值转成细化后的展示名"""
        if not name:
            return ""
        table = self._CLASS_TABLE.get(tid or "", [])
        for display, value in table:
            if value == name:
                return display
        base = name
        while base and base[-1] in "片剧":
            base = base[:-1]
        for display, value in table:
            if value == base:
                return display
        return name

    def _detail_desc(self, html):
        """影片简介 (优先取"内容简介"完整版)"""
        m = re.search(r'<div class="vod-list[^"]*">\s*<h2>[^<]*内容简介[^<]*</h2>'
                      r'\s*<div class="more-box">(.*?)</div>', html, re.S)
        if not m:
            m = re.search(r'<div class="text text-row[^"]*">简介[：:](.*?)</div>',
                          html, re.S)
        if not m:
            m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
            if m:
                return self.clean(m.group(1))
            return ""
        txt = m.group(1)
        txt = re.sub(r"<br\s*/?>", "\n", txt)
        txt = re.sub(r"<[^>]+>", "", txt)
        txt = self.clean(txt)
        return txt

    def _detail_plays(self, html):
        """解析线路标签与选集列表 (按 data-target 一一对应)"""
        tabs = re.findall(
            r'<li class="swiper-slide ewave-tab[^"]*"[^>]*data-target="#ewave-playlist-(\d+)"[^>]*>'
            r'\s*([^<]*?)\s*<em>', html, re.S)
        if not tabs:
            tabs = re.findall(
                r'data-target="#ewave-playlist-(\d+)"[^>]*>\s*([^<]*?)\s*<em>', html, re.S)
        lists = {}
        for m in re.finditer(
                r'<ul class="row ewave-tab-content[^"]*" id="ewave-playlist-(\d+)"[^>]*>(.*?)</ul>',
                html, re.S):
            lists[m.group(1)] = m.group(2)
        if not lists:
            # 兜底: 扫描所有选集链接
            eps = re.findall(r'href="(/mkvod/[^"]+)"[^>]*>([^<]*)<', html)
            if not eps:
                return [], []
            lines = []
            for path, ep in eps:
                lines.append("%s$%s%s" % (self.clean(ep) or "正片", self.host, path))
            return ["秒看线路"], ["#".join(lines)]

        from_arr, url_arr = [], []
        used = {}
        for pid, label in tabs:
            body = lists.get(pid)
            if body is None:
                continue
            eps = re.findall(r'href="(/mkvod/[^"]+)"[^>]*>([^<]*)<', body)
            if not eps:
                continue
            label = self.clean(label) or "线路%s" % (len(from_arr) + 1)
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for path, ep in eps:
                ep_name = self.clean(ep) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s%s" % (ep_name, self.host, path))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = id or ""
        if not play_url:
            return {"parse": 1, "url": "", "header": ""}
        if not play_url.startswith("http"):
            play_url = self.host + "/" + play_url.lstrip("/")

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
        }

        html = ""
        try:
            html = self._get(play_url, referer=self.host + "/")
        except Exception:
            html = ""

        real = self._extract_player(html)
        if real:
            return {
                "parse": 0,
                "url": real,
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }

        # 解析失败: 交给 TVBox 嗅探播放页
        return {
            "parse": 1,
            "url": play_url,
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    def _extract_player(self, html):
        """从播放页提取真实 m3u8 地址"""
        if not html:
            return ""
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if not m:
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*)', html, re.S)
        if m:
            raw = m.group(1)
            raw = raw.split("</script>")[0].strip().rstrip(";")
            try:
                j = json.loads(raw)
            except Exception:
                j = None
            if isinstance(j, dict):
                url = j.get("url") or ""
                encrypt = str(j.get("encrypt") or "0")
                if url:
                    if encrypt == "1":
                        url = urllib.parse.unquote(url)
                    elif encrypt == "2":
                        try:
                            url = base64.b64decode(
                                urllib.parse.unquote(url)).decode("utf-8", "replace")
                        except Exception:
                            pass
                    if url.startswith("//"):
                        url = "https:" + url
                    if url:
                        return url
        # 兜底: 正则抓 m3u8
        for p in (r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1',
                  r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)'):
            mm = re.search(p, html, re.S)
            if mm:
                url = mm.group(mm.lastindex) if mm.lastindex else mm.group(1)
                url = url.replace("\\/", "/").strip()
                if url.startswith("//"):
                    url = "https:" + url
                if url:
                    return url
        return ""

    def __jsEvalReturn(self):
        return {"proxy": None}

    def destroy(self):
        pass

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
