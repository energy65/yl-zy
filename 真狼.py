# -*- coding: utf-8 -*-
"""
真狼影视 - TVBox Python 爬虫

站点: https://zlys9.top/
类型: Next.js 综合影视站 (电影 / 电视剧 / 综艺 / 动漫 / 儿童)

站点结构:
    /                                             首页 (服务端渲染卡片)
    /category/{alias}                             频道页
    /category/{alias}/filter?type=&area=&year=&act=&rank=&page=N   分类筛选
    /detail/{alias}/{id}                          详情页 (RSC 数据内含 sources/episodes)
    /api/search?q=&page=&size=36                  搜索 (需要加密会话)
    /api/crypto/handshake                         加密会话握手 (AES-GCM)
    /api/resolve?url=&from=                       解析第三方视频页 -> 直链 m3u8/mp4

说明:
    - 全部分类、全部二级筛选 (类型/地区/年代/演员/排序) 均从站点动态抓取
    - 电影类型细化为 "科幻片/奇幻片/战争片/犯罪片/武侠片/历史片/文艺片" 等
    - 电视剧类型细化为 "古装/都市/历史/谍战/家庭" 等
    - 影片简介处添加 微信公众号 "源力软件汇"
    - 播放优先调用站点 /api/resolve 取直链 (parse=0)，失败回退站内解析线路
    - 仅使用 Python 标准库
"""

import re
import sys
import json
import time
import ssl
import gzip
import struct
import base64
import html as html_mod
import http.cookiejar
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


# ======================================================================
# AES-GCM (纯标准库实现, 仅用于解密站点 /api/* 响应)
# ======================================================================
_SBOX = (
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
)

_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d)


def _xtime(b):
    b <<= 1
    if b & 0x100:
        b ^= 0x11b
    return b & 0xff


_M2 = [_xtime(i) for i in range(256)]
_M3 = [_M2[i] ^ i for i in range(256)]


class _AES(object):
    """AES 分组加密 (支持 128/192/256 位密钥)"""

    def __init__(self, key):
        self.nk = len(key) // 4
        self.nr = self.nk + 6
        self.w = self._expand(key)

    def _expand(self, key):
        w = [list(key[4 * i:4 * i + 4]) for i in range(self.nk)]
        for i in range(self.nk, 4 * (self.nr + 1)):
            t = list(w[i - 1])
            if i % self.nk == 0:
                t = t[1:] + t[:1]
                t = [_SBOX[x] for x in t]
                t[0] ^= _RCON[i // self.nk - 1]
            elif self.nk > 6 and i % self.nk == 4:
                t = [_SBOX[x] for x in t]
            w.append([w[i - self.nk][j] ^ t[j] for j in range(4)])
        return w

    def encrypt_block(self, block):
        s = [list(block[i::4]) for i in range(4)]
        self._add(s, 0)
        for rnd in range(1, self.nr + 1):
            s = [[_SBOX[s[r][c]] for c in range(4)] for r in range(4)]
            s = [s[r][r:] + s[r][:r] for r in range(4)]
            if rnd != self.nr:
                s = [[_M2[s[r][c]] ^ _M3[s[(r + 1) % 4][c]] ^ s[(r + 2) % 4][c] ^ s[(r + 3) % 4][c]
                      for c in range(4)] for r in range(4)]
            self._add(s, rnd)
        out = bytearray(16)
        for c in range(4):
            for r in range(4):
                out[4 * c + r] = s[r][c]
        return bytes(out)

    def _add(self, s, rnd):
        for c in range(4):
            for r in range(4):
                s[r][c] ^= self.w[rnd * 4 + c][r]


def _aes_ctr(key, iv, data):
    """GCM 解密等价于 CTR(key, J0+1)"""
    aes = _AES(key)
    out = bytearray()
    counter = 2
    for off in range(0, len(data), 16):
        ks = aes.encrypt_block(iv + struct.pack(">I", counter))
        out.extend(bytes(c ^ k for c, k in zip(data[off:off + 16], ks)))
        counter += 1
    return bytes(out)


def _gcm_decrypt(key, blob):
    """blob = iv(12) + tag(16) + ciphertext"""
    if len(blob) < 29:
        return b""
    return _aes_ctr(key, blob[:12], blob[28:])


# ======================================================================
class Spider(BaseSpider):
    """真狼影视"""

    NAME = "真狼影视"
    HOST = "https://zlys9.top"
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # 推广文案 (显示在影片简介最前面)
    WX_TEXT = ("更多优质资源尽在源力\n"
               "微信公众号：源力软件汇")

    # 站内解析线路 (直链解析失败时的兜底)
    PARSE_API = "https://jx.202617.xyz/tv.php?url="

    # 站点对部分平台会返回占位视频 (非真实内容), 需回退解析线路
    BAD_STREAM_KEYS = ("json.playr.top/bot/", "/bot/stream/")

    # 一次搜索返回条数 (与站点前端一致)
    SEARCH_SIZE = 36

    # ==================== 一级分类 ====================
    CATEGORIES = [
        {"type_id": "movie", "type_name": "电影"},
        {"type_id": "tv", "type_name": "电视剧"},
        {"type_id": "variety", "type_name": "综艺"},
        {"type_id": "anime", "type_name": "动漫"},
        {"type_id": "children", "type_name": "儿童"},
    ]

    # 详情页 cat 数字 -> URL 别名
    CAT_ALIAS = {1: "movie", 2: "tv", 3: "variety", 4: "anime"}

    # ==================== 类型细化 ====================
    # 电影: 统一后缀 "片"
    MOVIE_TYPE = {
        "喜剧": "喜剧片", "爱情": "爱情片", "动作": "动作片", "恐怖": "恐怖片",
        "科幻": "科幻片", "剧情": "剧情片", "犯罪": "犯罪片", "奇幻": "奇幻片",
        "战争": "战争片", "悬疑": "悬疑片", "动画": "动画片", "文艺": "文艺片",
        "纪录": "纪录片", "传记": "传记片", "歌舞": "歌舞片", "古装": "古装片",
        "历史": "历史片", "惊悚": "惊悚片", "伦理": "伦理片", "武侠": "武侠片",
        "其他": "其他",
    }

    # 电视剧: 古装/都市/历史/谍战/家庭 ...
    TV_TYPE = {
        "家庭剧": "家庭", "青春剧": "青春", "言情": "言情", "剧情": "剧情",
        "伦理": "伦理", "喜剧": "喜剧", "悬疑": "悬疑", "都市": "都市",
        "偶像": "偶像", "古装": "古装", "军事": "军事", "警匪": "警匪",
        "历史": "历史", "励志": "励志", "神话": "神话", "谍战": "谍战",
        "动作": "动作", "情景": "情景", "武侠": "武侠", "科幻": "科幻",
        "其他": "其他",
    }

    # 内置筛选数据 (站点抓取失败时回退)
    FALLBACK_TYPES = {
        "movie": ["喜剧", "爱情", "动作", "恐怖", "科幻", "剧情", "犯罪", "奇幻",
                  "战争", "悬疑", "动画", "文艺", "纪录", "传记", "歌舞", "古装",
                  "历史", "惊悚", "伦理", "武侠", "其他"],
        "tv": ["言情", "剧情", "伦理", "喜剧", "悬疑", "都市", "偶像", "古装",
               "军事", "警匪", "历史", "励志", "神话", "谍战", "青春剧", "家庭剧",
               "动作", "情景", "武侠", "科幻", "其他"],
        "variety": ["脱口秀", "真人秀", "搞笑", "选秀", "八卦", "访谈", "情感", "生活",
                    "晚会", "音乐", "职场", "美食", "时尚", "游戏", "少儿", "体育",
                    "纪实", "科教", "曲艺", "歌舞", "财经", "汽车", "播报", "其他"],
        "anime": ["热血", "科幻", "美少女", "魔幻", "经典", "励志", "少儿", "冒险",
                  "搞笑", "推理", "恋爱", "治愈", "幻想", "校园", "动物", "机战",
                  "亲子", "儿歌", "运动", "悬疑", "怪物", "战争", "益智", "青春",
                  "童话", "竞技", "动作", "社会", "友情", "真人版", "电影版",
                  "OVA版", "TV版", "新番动画", "完结动画"],
        "children": ["热血", "科幻", "美少女", "魔幻", "经典", "励志", "少儿", "冒险",
                     "搞笑", "推理", "恋爱", "治愈", "幻想", "校园", "动物", "机战",
                     "亲子", "儿歌", "运动", "悬疑", "怪物", "战争", "益智", "青春",
                     "童话", "竞技", "动作", "社会", "友情", "真人版", "电影版",
                     "OVA版", "TV版", "新番动画", "完结动画"],
    }

    FALLBACK_AREAS = ["大陆", "香港", "台湾", "日本", "韩国", "美国", "英国",
                      "法国", "德国", "印度", "泰国", "其他"]

    FALLBACK_RANKS = [("最近热映", "rankhot"), ("最近上映", "ranklatest"), ("最受好评", "rankpoint")]

    # 筛选行标签 -> extend key
    FILTER_KEYS = {"类型": "type", "地区": "area", "年代": "year", "年份": "year",
                   "演员": "act", "明星": "act", "排序": "rank"}
    FILTER_ORDER = ["type", "area", "year", "act", "rank"]
    FILTER_NAMES = {"type": "类型", "area": "地区", "year": "年份", "act": "演员", "rank": "排序"}

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self._home_html = ""
        self._home_ts = 0
        self._filters = {}
        self._filters_ts = {}
        self._session = None
        self._opener = None
        self._init_opener()
        # 预热: 站点首访会下发 cookie (首次 403, 带 cookie 重试即正常)
        try:
            self._get_html("/", tries=5)
        except Exception:
            pass

    def _init_opener(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            https_handler = urllib.request.HTTPSHandler(context=ctx)
        except Exception:
            https_handler = urllib.request.HTTPSHandler()
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            https_handler, urllib.request.HTTPCookieProcessor(self._jar))
        self._opener.addheaders = [
            ("User-Agent", self.UA),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("Accept-Language", "zh-CN,zh;q=0.9"),
            ("Accept-Encoding", "gzip, deflate"),
            ("Connection", "keep-alive"),
        ]

    def getName(self):
        return self.NAME

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def destroy(self):
        pass

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None

    def __jsEvalReturn(self):
        return {"proxy": None}

    # ==================== HTTP ====================
    def _request(self, path, headers=None, tries=6, timeout=15):
        """返回 (status, bytes)。站点有 cookie 挑战: 403 时带 cookie 重试"""
        url = path if path.startswith("http") else self.HOST + path
        last_status, last_data = 0, b""
        for i in range(tries):
            try:
                req = urllib.request.Request(url, headers=headers or {})
                resp = self._opener.open(req, timeout=timeout)
                data = resp.read()
                if "gzip" in resp.headers.get("Content-Encoding", ""):
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                return resp.getcode(), data
            except urllib.error.HTTPError as e:
                data = b""
                try:
                    data = e.read()
                    if "gzip" in e.headers.get("Content-Encoding", ""):
                        data = gzip.decompress(data)
                except Exception:
                    pass
                last_status, last_data = e.code, data
                if e.code in (401, 403):
                    time.sleep(0.12)
                    continue
                return e.code, data
            except Exception:
                last_status = 0
                time.sleep(0.15)
                continue
        return last_status, last_data

    @staticmethod
    def _decode(data):
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _get_html(self, path, tries=6):
        st, data = self._request(path, tries=tries)
        if st != 200:
            return ""
        return self._decode(data)

    # ==================== 工具 ====================
    @staticmethod
    def clean(text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = re.sub(r"<br\s*/?>", " ", text)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _js_unescape(s):
        out = []
        i, n = 0, len(s)
        mp = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "'": "'",
              "\\": "\\", "/": "/", "b": "\b", "f": "\f"}
        while i < n:
            c = s[i]
            if c == "\\" and i + 1 < n:
                nxt = s[i + 1]
                if nxt in mp:
                    out.append(mp[nxt])
                    i += 2
                elif nxt == "u" and i + 5 < n:
                    try:
                        out.append(chr(int(s[i + 2:i + 6], 16)))
                        i += 6
                    except Exception:
                        out.append(c)
                        i += 1
                else:
                    out.append(c)
                    i += 1
            else:
                out.append(c)
                i += 1
        return "".join(out)

    def _rsc(self, html):
        """拼接 Next.js RSC 流数据"""
        if not html:
            return ""
        pushes = re.findall(r'self\.__next_f\.push\(\[\d+,"((?:[^"\\]|\\.)*)"\]\)',
                            html, re.DOTALL)
        return "".join(self._js_unescape(p) for p in pushes)

    @staticmethod
    def _json_obj_at(text, pos):
        """从 pos 处的 '{' 开始, 返回配对的 JSON 对象字符串"""
        depth, in_str, esc = 0, False, False
        for i in range(pos, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[pos:i + 1]
        return ""

    def _refine_type(self, alias, name):
        name = self.clean(name)
        if not name:
            return ""
        if name == "全部":
            return "全部"
        if alias == "movie":
            return self.MOVIE_TYPE.get(name, name if name == "其他" else name + "片")
        if alias == "tv":
            return self.TV_TYPE.get(name, name)
        return name

    def _img(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.HOST + url
        return url

    # ==================== 加密会话 / API ====================
    def _handshake(self):
        st, data = self._request("/api/crypto/handshake", tries=5)
        if st != 200 or not data:
            self._session = None
            return None
        try:
            obj = json.loads(self._decode(data))
            sess = obj.get("data") or {}
            if sess.get("token") and sess.get("key"):
                self._session = sess
                return sess
        except Exception:
            pass
        self._session = None
        return None

    def _ensure_session(self):
        sess = self._session
        if sess:
            try:
                if float(sess.get("expiresAt") or 0) - 30000 > time.time() * 1000:
                    return sess
            except Exception:
                pass
        return self._handshake()

    def _api(self, path):
        """调用加密接口, 自动握手 + AES-GCM 解密"""
        for attempt in range(2):
            sess = self._ensure_session()
            if not sess:
                return {}
            headers = {
                "X-Enc-Token": sess.get("token", ""),
                "Referer": self.HOST + "/",
                "Accept": "application/json,text/plain,*/*",
            }
            st, data = self._request(path, headers=headers, tries=4)
            if not data:
                continue
            try:
                obj = json.loads(self._decode(data))
            except Exception:
                self._handshake()
                continue
            if obj.get("enc") == "1":
                try:
                    key = base64.b64decode(sess.get("key", ""))
                    plain = _gcm_decrypt(key, base64.b64decode(obj.get("data", "")))
                    return json.loads(plain.decode("utf-8"))
                except Exception:
                    self._handshake()
                    continue
            if obj.get("errno") == 401:
                self._handshake()
                continue
            return obj
        return {}

    # ==================== 列表解析 ====================
    def _parse_cards(self, html):
        """解析服务端渲染的影片卡片"""
        videos = []
        seen = set()

        def add(href, title, pic, remark):
            if not href or "/detail/" not in href:
                return
            vod_id = href.split("/detail/", 1)[-1].strip("/")
            if not vod_id or vod_id in seen:
                return
            name = self.clean(title)
            if not name:
                return
            seen.add(vod_id)
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": self._img(pic) if pic else self.DEFAULT_PIC,
                "vod_remarks": self.clean(remark)[:40],
            })

        blocks = re.findall(r'<li[^>]*class="video-card"[^>]*>(.*?)</li>', html, re.DOTALL)
        for block in blocks:
            tm = re.search(r'<a[^>]*class="video-card__link"[^>]*>', block)
            if not tm:
                tm = re.search(r'<a[^>]*href="/detail/[^"]*"[^>]*>', block)
            tag = tm.group(0) if tm else block
            hm = re.search(r'href="(/detail/[^"]+)"', tag)
            if not hm:
                continue
            nm = re.search(r'title="([^"]*)"', tag)
            if not nm:
                nm = re.search(r'alt="([^"]*)"', block)
            pm = re.search(r'<img[^>]*class="video-card__img"[^>]*src="([^"]*)"', block)
            if not pm:
                pm = re.search(r'<img[^>]*(?:data-original|data-src|src)="([^"]*)"', block)
            mm = re.search(r'<div class="video-card__meta">([^<]*)</div>', block)
            bm = re.search(r'<span[^>]*class="video-card__badge[^"]*"[^>]*>([^<]*)</span>', block)
            remark = ""
            if bm:
                remark = bm.group(1)
            elif mm:
                remark = mm.group(1)
            add(hm.group(1), nm.group(1) if nm else "", pm.group(1) if pm else "", remark)

        if not videos:
            # 回退: 直接按锚点解析
            for m in re.finditer(r'<a[^>]*class="video-card__link"[^>]*>', html):
                tag = m.group(0)
                hm = re.search(r'href="(/detail/[^"]+)"', tag)
                nm = re.search(r'title="([^"]*)"', tag)
                if not hm:
                    continue
                window = html[m.end():m.end() + 700]
                pm = re.search(r'<img[^>]*src="([^"]*)"', window)
                mm = re.search(r'<div class="video-card__meta">([^<]*)</div>', window)
                add(hm.group(1), nm.group(1) if nm else "",
                    pm.group(1) if pm else "", mm.group(1) if mm else "")
        return videos

    def _parse_pagecount(self, html, page):
        m = re.search(r'<a[^>]*href="([^"]*page=(\d+))"[^>]*>\s*下一页\s*</a>', html)
        if m:
            try:
                return max(page, int(m.group(2)))
            except Exception:
                return page + 1
        return page

    # ==================== 筛选器 ====================
    def _refine_filter_value(self, alias, fk, name, value):
        if fk == "type":
            return self._refine_type(alias, name)
        return name

    def _parse_filters(self, alias, html):
        filters = {}
        rows = re.findall(
            r'<div class="category-filter-row">\s*'
            r'<span class="category-filter-label">(.*?)</span>\s*'
            r'<div class="category-filter-tags">(.*?)</div>',
            html, re.DOTALL)
        for label, tags in rows:
            label = self.clean(label).rstrip(":：")
            fk = self.FILTER_KEYS.get(label)
            if not fk:
                continue
            values = []
            for href, text in re.findall(
                    r'<a[^>]*class="category-filter-tag[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                    tags, re.DOTALL):
                name = self.clean(text)
                if not name:
                    continue
                val = ""
                try:
                    q = urllib.parse.parse_qs(urllib.parse.urlparse(html_mod.unescape(href)).query)
                    if q.get(fk):
                        val = q[fk][0]
                except Exception:
                    val = ""
                values.append({"n": self._refine_filter_value(alias, fk, name, val), "v": val})
            if values:
                filters[fk] = values

        # 电影类型补充站点未列出但可用的 "武侠"
        if alias == "movie":
            types = filters.get("type")
            if types and not any(v.get("v") == "武侠" for v in types):
                idx = len(types) - 1
                for i, v in enumerate(types):
                    if v.get("v") == "其他":
                        idx = i
                        break
                types.insert(idx, {"n": "武侠片", "v": "武侠"})
        return filters

    def _fallback_filters(self, alias):
        year = time.localtime().tm_year
        out = {
            "type": [{"n": "全部", "v": ""}] + [
                {"n": self._refine_type(alias, t), "v": t}
                for t in self.FALLBACK_TYPES.get(alias, [])],
            "area": [{"n": "全部", "v": ""}] + [
                {"n": a, "v": a} for a in self.FALLBACK_AREAS],
            "year": [{"n": "全部", "v": ""}] + [
                {"n": str(y), "v": str(y)} for y in range(year, 2006, -1)] + [
                {"n": "更早", "v": "lt_year"}],
            "rank": [{"n": n, "v": v} for n, v in self.FALLBACK_RANKS],
        }
        if alias == "variety" or alias == "anime" or alias == "children":
            out["rank"] = out["rank"][:2]
        return out

    def _get_filters(self, alias):
        now = time.time()
        if alias in self._filters and now - self._filters_ts.get(alias, 0) < 6 * 3600:
            return self._filters[alias]

        filters = {}
        html = self._get_html("/category/%s/filter" % alias)
        if html and "category-filter-row" in html:
            try:
                filters = self._parse_filters(alias, html)
            except Exception:
                filters = {}

        if not filters:
            filters = self._fallback_filters(alias)

        result = []
        for fk in self.FILTER_ORDER:
            if filters.get(fk):
                result.append({
                    "key": fk,
                    "name": self.FILTER_NAMES.get(fk, fk),
                    "value": filters[fk],
                })
        self._filters[alias] = result
        self._filters_ts[alias] = now
        return result

    # ==================== 首页 ====================
    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            try:
                filters[c["type_id"]] = self._get_filters(c["type_id"])
            except Exception:
                filters[c["type_id"]] = self._fallback_filters(c["type_id"])
        videos = []
        try:
            videos = self.homeVideoContent().get("list", [])
        except Exception:
            pass
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        now = time.time()
        if not self._home_html or now - self._home_ts > 600:
            html = self._get_html("/")
            if html:
                self._home_html = html
                self._home_ts = now
        if not self._home_html:
            return {"list": []}
        return {"list": self._parse_cards(self._home_html)[:60]}

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        alias = str(tid or "movie")
        if alias not in ("movie", "tv", "variety", "anime", "children"):
            alias = "movie"

        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}

        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            params = []
            for fk in ("type", "area", "year", "act", "rank"):
                val = extend.get(fk)
                if val is None:
                    continue
                val = str(val).strip()
                if val and val != "全部":
                    params.append((fk, val))
            if page > 1:
                params.append(("page", str(page)))

            path = "/category/%s/filter" % alias
            if params:
                path += "?" + urllib.parse.urlencode(params)

            html = self._get_html(path)
            if not html:
                return result
            videos = self._parse_cards(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos) if videos else 0
            result["pagecount"] = self._parse_pagecount(html, page)
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
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        if not key:
            return result
        try:
            path = "/api/search?q=%s&page=%d&size=%d" % (
                urllib.parse.quote(str(key)), page, self.SEARCH_SIZE)
            data = self._api(path)
            payload = data.get("data") or {}
            items = payload.get("items") or []
            total = payload.get("total") or 0

            videos = []
            seen = set()
            for it in items:
                try:
                    vid = str(it.get("id") or "")
                    cat = int(it.get("cat") or 0)
                except Exception:
                    continue
                alias = self.CAT_ALIAS.get(cat)
                # cat=0 / 数字旧 ID 均无法打开详情, 直接跳过
                if not alias or not vid or vid.isdigit():
                    continue
                name = self.clean(it.get("title") or "")
                if not name:
                    continue
                vod_id = "%s/%s" % (alias, vid)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                pic = it.get("cover") or ""
                if not pic and it.get("coverFallbacks"):
                    pic = it.get("coverFallbacks")[0]
                remark = self.clean(it.get("badge") or it.get("meta") or "")
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": self._img(pic) if pic else self.DEFAULT_PIC,
                    "vod_remarks": remark[:40],
                })

            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = int(total) if total else len(videos)
            if total:
                result["pagecount"] = max(page, (int(total) + self.SEARCH_SIZE - 1) // self.SEARCH_SIZE)
            elif len(videos) >= self.SEARCH_SIZE:
                result["pagecount"] = page + 1
        except Exception:
            pass
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vod_id = ids[0] if isinstance(ids, (list, tuple)) else ids
        vod_id = str(vod_id).strip().lstrip("/")
        if not vod_id:
            return result

        html = self._get_html("/detail/%s" % vod_id)
        if not html:
            return result
        rsc = self._rsc(html)
        data = {}
        pos = rsc.find('"data":{"cat":')
        if pos >= 0:
            brace = rsc.find("{", pos + 7)
            if brace >= 0:
                try:
                    data = json.loads(self._json_obj_at(rsc, brace))
                except Exception:
                    data = {}
        if not data:
            return result

        detail = data.get("detail") or {}
        try:
            cat = int(data.get("cat") or 0)
        except Exception:
            cat = 0
        alias = self.CAT_ALIAS.get(cat) or vod_id.split("/")[0]

        title = self.clean(detail.get("title") or "") or vod_id
        pic = detail.get("cdncover") or data.get("cover") or ""
        desc = self.clean(detail.get("description") or "")
        year = str(detail.get("pubdate") or "")[:4]
        areas = detail.get("area") or []
        if not isinstance(areas, list):
            areas = [areas]
        area = " ".join([self.clean(a) for a in areas if self.clean(a)])
        cats = detail.get("moviecategory") or []
        if not isinstance(cats, list):
            cats = [cats]
        types = [self._refine_type(alias, c) for c in cats if self.clean(c)]
        actors = detail.get("actor") or []
        if not isinstance(actors, list):
            actors = [actors]
        directors = detail.get("director") or []
        if not isinstance(directors, list):
            directors = [directors]
        remarks = self.clean(data.get("updateText") or detail.get("allupinfo") or "")

        # 播放源
        allep = detail.get("allepidetail") or {}
        play_from, play_url = [], []
        used = {}
        for src in (data.get("sources") or []):
            site = str(src.get("site") or "")
            sname = self.clean(src.get("name") or "") or site or "线路"
            eps = self._resolve_episodes(src.get("episodes") or [], allep)
            lines = []
            for ep in eps:
                if not isinstance(ep, dict):
                    continue
                url = str(ep.get("url") or "").strip()
                if not url:
                    continue
                name = self.clean(ep.get("name") or "")
                if not name:
                    num = str(ep.get("playlink_num") or "").strip()
                    name = "第%s集" % num if num else "正片"
                lines.append("%s$%s|%s" % (name, site, url))
            if not lines:
                continue
            if sname in used:
                used[sname] += 1
                sname = "%s%d" % (sname, used[sname])
            else:
                used[sname] = 1
            play_from.append(sname)
            play_url.append("#".join(lines))

        if not play_from:
            play_from = ["真狼影视"]
            play_url = [""]

        vod = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": self._img(pic) if pic else self.DEFAULT_PIC,
            "vod_year": year,
            "vod_area": area,
            "vod_type": " ".join(types),
            "vod_actor": " ".join([self.clean(a) for a in actors if self.clean(a)]),
            "vod_director": " ".join([self.clean(d) for d in directors if self.clean(d)]),
            "vod_remarks": remarks,
            "vod_content": self.WX_TEXT + ("\n\n" + desc if desc else ""),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }
        result["list"] = [vod]
        return result

    def _resolve_episodes(self, episodes, allep):
        """展开 RSC 引用 ($5:...:allepidetail:qiyi:0)"""
        out = []
        for ep in episodes:
            if isinstance(ep, dict):
                out.append(ep)
            elif isinstance(ep, str) and ep.startswith("$"):
                parts = ep.split(":")
                try:
                    site = parts[-2]
                    idx = int(parts[-1])
                    arr = allep.get(site) or []
                    if 0 <= idx < len(arr):
                        out.append(arr[idx])
                except Exception:
                    continue
        return out

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        raw = (id or "").strip()
        if not raw:
            return {"parse": 0, "url": "", "header": ""}

        site, url = "", raw
        if "|" in raw:
            head, tail = raw.split("|", 1)
            if head and "://" not in head and "/" not in head:
                site, url = head, tail
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            return {"parse": 0, "url": "", "header": ""}

        headers = {"User-Agent": self.UA, "Referer": url}
        # 优先: 站点解析接口 -> 直链
        try:
            path = "/api/resolve?url=" + urllib.parse.quote(url, safe="")
            if site:
                path += "&from=" + urllib.parse.quote(site, safe="")
            data = self._api(path)
            payload = data.get("data") or {}
            direct = (payload.get("url") or "").strip()
            # 未解析成功 / 返回原页面 / 占位视频 / 非媒体地址 都视为失败
            if payload.get("resolved") is False:
                direct = ""
            if direct == url:
                direct = ""
            if direct and any(k in direct for k in self.BAD_STREAM_KEYS):
                direct = ""
            if direct and not re.search(r"\.(m3u8|mp4|flv|ts)(\?|$)", direct, re.I):
                direct = ""
            if direct and direct.startswith("http"):
                return {
                    "parse": 0,
                    "url": direct,
                    "header": json.dumps(headers),
                    "playUrl": "",
                    "subtitle": "",
                }
        except Exception:
            pass

        # 兜底: 站内第三方解析线路 (TVBox WebView 嗅探)
        return {
            "parse": 1,
            "url": url,
            "playUrl": self.PARSE_API,
            "header": json.dumps({"User-Agent": self.UA, "Referer": self.HOST + "/"}),
            "subtitle": "",
        }


# ======================================================================
if __name__ == "__main__":
    sp = Spider()
    sp.init()

    print("=" * 60)
    print("[1] 首页分类与筛选")
    home = sp.homeContent(False)
    for c in home.get("class", []):
        print("  %s (%s)" % (c["type_name"], c["type_id"]))
    for tid, fl in (home.get("filters") or {}).items():
        info = []
        for f in fl:
            info.append("%s:%d项" % (f["name"], len(f["value"])))
        print("  筛选 %s -> %s" % (tid, ", ".join(info)))
    print("  首页影片: %d 部" % len(home.get("list", [])))
    if home.get("list"):
        print("  示例:", home["list"][0]["vod_name"], home["list"][0]["vod_id"])

    print("\n[2] 分类: 电影 / 科幻片")
    cat = sp.categoryContent("movie", "1", False, {"type": "科幻"})
    print("  第1页 %d 部, pagecount=%s" % (len(cat["list"]), cat["pagecount"]))
    for v in cat["list"][:3]:
        print("   -", v["vod_name"], "|", v["vod_remarks"])

    print("\n[3] 分类: 儿童")
    ch = sp.categoryContent("children", "1", False, {})
    print("  %d 部" % len(ch["list"]))
    for v in ch["list"][:3]:
        print("   -", v["vod_name"], v["vod_id"])

    print("\n[4] 搜索: 庆余年")
    sr = sp.searchContent("庆余年", False, "1")
    print("  %d 条, total=%s, pagecount=%s" % (len(sr["list"]), sr["total"], sr["pagecount"]))
    for v in sr["list"][:3]:
        print("   -", v["vod_name"], v["vod_id"], "|", v["vod_remarks"])

    print("\n[5] 详情")
    if sr["list"]:
        vid = sr["list"][0]["vod_id"]
        dt = sp.detailContent([vid])
        if dt.get("list"):
            vod = dt["list"][0]
            print("  标题:", vod["vod_name"])
            print("  类型:", vod["vod_type"], "年份:", vod["vod_year"], "地区:", vod["vod_area"])
            print("  简介:", vod["vod_content"][:60].replace("\n", " / "))
            print("  线路:", vod["vod_play_from"])
            first = vod["vod_play_url"].split("$$$")[0].split("#")[0]
            print("  首集:", first[:120])
            if "$" in first:
                pid = first.split("$", 1)[1]
                print("\n[6] 播放解析")
                pr = sp.playerContent("", pid, [])
                print("  parse:", pr.get("parse"))
                print("  url:", str(pr.get("url"))[:160])
        else:
            print("  详情为空")
    print("\n测试完成")
