# -*- coding: utf-8 -*-
# 懂片帝 - TVBox / 追剧影视 通用 Python 爬虫
# 站点：https://dongpian17.com
# 接口：/v1/* REST API（HMAC-SHA256 请求签名，换行分隔）
# 分类：电影/电视剧/短剧/动漫/综艺/纪录片
# 筛选：类型（q 搜索实现）/地区/年份/排序/榜单窗口（全部实测生效）
import sys
import json
import time
import hmac
import hashlib
import os
import re
import requests
from urllib.parse import quote, urlencode

# ↓↓↓ TVBox Python 插件必需：base 包在上一级目录，这一行不能删 ↓↓↓
sys.path.append('..')

try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = None

requests.packages.urllib3.disable_warnings()

if BaseSpider is None:
    class BaseSpider(object):
        def __init__(self):
            self.extend = ''

        def init(self, extend=""):
            pass

        def getName(self):
            return ""

        def isVideoFormat(self, url):
            return False

        def manualVideoCheck(self):
            return False

        def destroy(self):
            pass

        def localProxy(self, param):
            return None

        def fetch(self, url, params=None, headers=None, cookies=None,
                  timeout=15, verify=False, encoding="utf-8", **kwargs):
            resp = requests.get(url, params=params, headers=headers,
                                cookies=cookies, timeout=timeout,
                                verify=verify, **kwargs)
            resp.encoding = encoding
            return resp


class Spider(BaseSpider):

    # 请求签名密钥（硬编码于前端 movie-card-runtime，HMAC-SHA256，消息为 方法\n路径+查询\n时间戳\n随机数）
    SIGN_KEY = "8b9a908a05eac640e1ee06f52acaa741bfe4ba9e004eeffdbeb635e532e06666"

    # 分类映射：kind 参数 → 中文名（content_kind 全部实测有效）
    KINDS = [
        ("movie", "电影"),
        ("series", "电视剧"),
        ("short_drama", "短剧"),
        ("anime", "动漫"),
        ("variety", "综艺"),
        ("documentary", "纪录片"),
    ]

    # 类型细化词表（站点 genre 参数无效，实测用 q 全文搜索 + kind 过滤实现，
    # 结果均命中对应影片的 genres 标签或标题；n=显示名 v=搜索词）
    GENRES = {
        "movie": [
            ("科幻片", "科幻"), ("奇幻片", "奇幻"), ("战争片", "战争"),
            ("犯罪片", "犯罪"), ("武侠片", "武侠"), ("历史片", "历史"),
            ("文艺片", "文艺"), ("动作片", "动作"), ("喜剧片", "喜剧"),
            ("爱情片", "爱情"), ("悬疑片", "悬疑"), ("惊悚片", "惊悚"),
            ("恐怖片", "恐怖"), ("冒险片", "冒险"), ("剧情片", "剧情"),
            ("古装", "古装"), ("家庭", "家庭"), ("传记", "传记"),
            ("音乐", "音乐"), ("灾难", "灾难"), ("西部", "西部"),
            ("运动", "运动"), ("同性", "同性"),
        ],
        "series": [
            ("古装", "古装"), ("都市", "都市"), ("历史", "历史"),
            ("谍战", "谍战"), ("家庭", "家庭"), ("悬疑", "悬疑"),
            ("犯罪", "犯罪"), ("言情", "言情"), ("军旅", "军旅"),
            ("武侠", "武侠"), ("奇幻", "奇幻"), ("喜剧", "喜剧"),
            ("爱情", "爱情"), ("动作", "动作"), ("刑侦", "刑侦"),
            ("青春", "青春"), ("同性", "同性"),
        ],
        "short_drama": [
            ("现代都市", "现代都市"), ("反转爽剧", "反转爽剧"),
            ("脑洞悬疑", "脑洞悬疑"), ("言情总裁", "言情总裁"),
            ("女频恋爱", "女频恋爱"), ("现代言情", "现代言情"),
            ("古装仙侠", "古装仙侠"), ("年代穿越", "年代穿越"),
            ("重生民国", "重生民国"), ("闪婚离婚", "闪婚离婚"),
            ("霸总", "霸总"), ("AI漫剧", "AI漫剧"),
        ],
        "anime": [
            ("国产动漫", "国产动漫"), ("日韩动漫", "日韩动漫"),
            ("日本动漫", "日本动漫"), ("欧美动漫", "欧美动漫"),
            ("热血", "热血"), ("冒险", "冒险"), ("搞笑", "搞笑"),
            ("恋爱", "恋爱"), ("校园", "校园"), ("战斗", "战斗"),
            ("科幻", "科幻"), ("奇幻", "奇幻"), ("玄幻", "玄幻"),
            ("武侠", "武侠"), ("魔法", "魔法"), ("机战", "机战"),
            ("悬疑", "悬疑"), ("治愈", "治愈"), ("励志", "励志"),
            ("恐怖", "恐怖"),
        ],
        "variety": [
            ("真人秀", "真人秀"), ("音乐", "音乐"), ("脱口秀", "脱口秀"),
            ("相声", "相声"), ("晚会", "晚会"), ("旅游", "旅游"),
            ("舞蹈", "舞蹈"), ("歌舞", "歌舞"), ("竞技", "竞技"),
            ("访谈", "访谈"), ("情感", "情感"), ("文化", "文化"),
            ("生活", "生活"),
        ],
        "documentary": [
            ("历史", "历史"), ("战争", "战争"), ("犯罪", "犯罪"),
            ("传记", "传记"), ("音乐", "音乐"), ("运动", "运动"),
            ("武侠", "武侠"), ("古装", "古装"), ("悬疑", "悬疑"),
            ("灾难", "灾难"),
        ],
    }

    # 地区筛选（站点 area 参数实测生效，支持别名映射）
    AREAS = [
        ("中国大陆", "中国大陆"), ("中国香港", "中国香港"), ("中国台湾", "中国台湾"),
        ("美国", "美国"), ("韩国", "韩国"), ("日本", "日本"),
        ("英国", "英国"), ("法国", "法国"), ("泰国", "泰国"), ("印度", "印度"),
    ]

    # 年份范围（站点 year 参数实测生效）
    YEARS = [(str(y), str(y)) for y in range(2026, 2014, -1)]

    # 排序与榜单窗口（站点 sort/window 参数实测生效）
    SORTS = [
        ("热门", "trending"),
        ("最新", "newest"),
    ]
    WINDOWS = [
        ("日榜", "day"),
        ("周榜", "week"),
        ("月榜", "month"),
        ("总榜", "total"),
    ]

    # 微信公众号文案（XOR 加密存储，密钥 piandi_wechat_2026，运行时解密）
    _W_KEY = [112, 105, 97, 110, 100, 105, 95, 119, 101, 99, 104, 97, 116, 95, 50, 48, 50, 54]
    _W_DATA = [149, 215, 207, 138, 219, 200, 186, 242, 201, 135, 212, 246, 145, 208, 133, 18,
               212, 140, 224, 140, 235, 245, 140, 212, 240, 147, 222, 213, 142, 208, 243, 125,
               221, 140, 190, 208, 235, 221, 132, 202, 254, 141, 227, 239, 141, 215, 192, 137,
               193, 219, 212, 138, 162, 211, 192, 212, 132, 242, 204, 143, 229, 231, 128, 233,
               243, 135, 249, 207, 218, 133, 146, 209, 249, 225]

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = "https://dongpian17.com"
        self.name = "懂片帝"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        self.session = requests.Session()
        self.account = ""
        self.password = ""
        self.cookie_str = ""
        self._logged_in = False

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        try:
            if not extend:
                extend = getattr(self, 'extend', '')
            if isinstance(extend, str):
                try:
                    ext = json.loads(extend) if extend.strip() else {}
                except Exception:
                    ext = {}
            elif isinstance(extend, dict):
                ext = extend
            else:
                ext = {}
            self.host = ext.get("host", self.host).rstrip("/")
            self.name = ext.get("name", self.name)
            self.ua = ext.get("ua", self.ua)
            # 账号配置：官方线路需登录播放，支持 account/password 或直接给 cookie
            self.account = ext.get("account", self.account)
            self.password = ext.get("password", self.password)
            self.cookie_str = ext.get("cookie", self.cookie_str)
            if self.cookie_str:
                self._apply_cookie(self.cookie_str)
                self._logged_in = True
            print("懂片帝 init: host={}, name={}".format(self.host, self.name))
        except Exception as e:
            print("懂片帝 init error: {}".format(e))

    # ================= 微信文案（加密解密） =================

    def _get_wechat_info(self):
        try:
            kb = bytes(self._W_KEY)
            db = bytes(self._W_DATA)
            return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(db)).decode("utf-8")
        except Exception:
            return ""

    # ================= 登录会话 =================

    def _apply_cookie(self, cookie_str):
        try:
            for kv in cookie_str.split(";"):
                kv = kv.strip()
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    self.session.cookies.set(k.strip(), v.strip())
        except Exception as e:
            print("懂片帝 apply cookie error: {}".format(e))

    def _login(self):
        """账号密码登录，成功后会话cookie保存在 session 中"""
        if not self.account or not self.password:
            return False
        try:
            path = "/v1/users/password/login"
            headers = self._headers("POST", path, "")
            headers["Content-Type"] = "application/json"
            resp = self.session.post(self.host + path, headers=headers,
                                     json={"account": self.account, "password": self.password},
                                     timeout=15, verify=False)
            data = json.loads(resp.text)
            if resp.status_code == 200 and not data.get("error"):
                self._logged_in = True
                print("懂片帝 login ok: {}".format(self.account))
                return True
            print("懂片帝 login fail: {}".format(resp.text[:200]))
        except Exception as e:
            print("懂片帝 login error: {}".format(e))
        return False

    def _anonymous_login(self):
        """注册匿名(游客)会话：POST /v1/users/anonymous，服务端种 ai_movie_session cookie。
        官方线路按游客账号配额计费，有游客会话即可免登录播放。"""
        try:
            import uuid
            path = "/v1/users/anonymous"
            headers = self._headers("POST", path, "")
            headers["Content-Type"] = "application/json"
            anon_id = "web_{}".format(uuid.uuid4())
            resp = self.session.post(self.host + path, headers=headers,
                                     json={"anonymous_id": anon_id},
                                     timeout=15, verify=False)
            if resp.status_code in (200, 201):
                self._logged_in = True
                print("懂片帝 anonymous session ok: {}".format(anon_id))
                return True
            print("懂片帝 anonymous fail: {} {}".format(resp.status_code, resp.text[:200]))
        except Exception as e:
            print("懂片帝 anonymous error: {}".format(e))
        return False

    def _ensure_login(self):
        if self._logged_in:
            return True
        # 优先账号密码登录（配额更高），否则注册匿名游客会话
        if self.account and self.password:
            return self._login()
        return self._anonymous_login()

    # ================= 签名请求 =================

    def _headers(self, method, path, search):
        ts = str(int(time.time() * 1000))
        nonce = os.urandom(16).hex()
        msg = "{}\n{}{}\n{}\n{}".format(method, path, search, ts, nonce)
        sign = hmac.new(self.SIGN_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return {
            "User-Agent": self.ua,
            "Accept": "application/json",
            "x-ai-movie-client-name": "movie-search-frontend",
            "x-ai-movie-client-version": "1.0.0",
            "x-ai-movie-build-version": "dongpiandi-v2026.10.04.1-episode-resume-efd9a7f2e87e-web",
            "x-ai-movie-protocol-version": "2026-07-05.library-v2.playback-v1",
            "x-ai-movie-timestamp": ts,
            "x-ai-movie-nonce": nonce,
            "x-ai-movie-signature": sign,
        }

    def _get(self, path, search=""):
        # 实测：含中文的查询参数值必须先 URL 编码再参与签名与请求，
        # 否则服务器按编码后的查询串验签失败（返回非预期响应）
        try:
            resp = self.session.get(self.host + path + search,
                                    headers=self._headers("GET", path, search),
                                    timeout=15, verify=False)
            return json.loads(resp.text)
        except Exception as e:
            print("懂片帝 _get error {}: {}".format(path, e))
            return {}

    def _post(self, path, search, body):
        try:
            headers = self._headers("POST", path, search)
            headers["Content-Type"] = "application/json"
            resp = self.session.post(self.host + path + search, headers=headers,
                                     json=body, timeout=15, verify=False)
            return json.loads(resp.text)
        except Exception as e:
            print("懂片帝 _post error {}: {}".format(path, e))
            return {}

    def _resolve_line(self, ticket, retried=False):
        """resolve-line 二次解析，遇登录要求时自动登录重试一次"""
        d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        if d2.get("code") == "playback_user_session_required" and not retried:
            if self._ensure_login():
                d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        return d2.get("line", {}) or {}

    # ================= 查询构造 =================

    def _catalog_search(self, kind, genre, area, year, sort, window, q, page, limit=20):
        """构造 /v1/browse/catalog 查询串（参数值全部 URL 编码）

        类型筛选：站点 genre 参数无效，实测用 q=类型词 + query_mode=fast_v3 实现，
        结果按 kind 收敛到对应大类
        """
        params = [("page", str(page)), ("limit", str(limit))]
        if kind and kind != "all":
            params.append(("kind", kind))
        if genre:
            params.append(("q", genre))
            params.append(("query_mode", "fast_v3"))
            params.append(("search_fields", "all"))
        elif q:
            params.append(("q", q))
            params.append(("query_mode", "fast_v3"))
            params.append(("search_fields", "all"))
        else:
            # 默认排序：不带 sort 参数（实测可翻 1000 条/50 页）；
            # 选"热门"时走 trending 榜单并附带榜单窗口（实测仅约 200 条/10 页）
            if sort:
                params.append(("sort", sort))
                if window and sort == "trending":
                    params.append(("window", window))
        if area:
            params.append(("area", area))
        if year:
            params.append(("year", year))
        return "?" + urlencode(params)

    # ================= TVBox 接口 =================

    def homeContent(self, filter):
        classes = []
        for tid, tname in self.KINDS:
            classes.append({"type_id": tid, "type_name": tname})

        filters = {}
        if filter:
            for tid, _ in self.KINDS:
                fl = []
                genres = self.GENRES.get(tid) or []
                if genres:
                    fl.append({
                        "key": "genre",
                        "name": "类型",
                        "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in genres],
                    })
                fl.append({
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self.AREAS],
                })
                fl.append({
                    "key": "year",
                    "name": "年份",
                    "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in self.YEARS],
                })
                fl.append({
                    "key": "sort",
                    "name": "排序",
                    "value": [{"n": n, "v": v} for n, v in self.SORTS],
                })
                fl.append({
                    "key": "window",
                    "name": "榜单",
                    "value": [{"n": n, "v": v} for n, v in self.WINDOWS],
                })
                filters[tid] = fl
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        # 首页推荐：大家都在看（日榜快照）
        data = self._get("/v1/feed/home", "?scope=public&mode=preview&sections=3&cards=12")
        videos = []
        for sec in data.get("sections", []):
            if sec.get("id") == "feed_sec_everyone_watching" or sec.get("type") == "trend":
                for card in sec.get("cards", []):
                    videos.append(self._parse_card(card))
                break
        if not videos:
            for sec in data.get("sections", []):
                for card in sec.get("cards", []):
                    videos.append(self._parse_card(card))
                if videos:
                    break
        return {"list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1

        ext = extend if isinstance(extend, dict) else {}
        try:
            ext = json.loads(extend) if isinstance(extend, str) and extend.strip() else ext
        except Exception:
            pass

        genre = str(ext.get("genre") or "").strip()
        area = str(ext.get("area") or "").strip()
        year = str(ext.get("year") or "").strip()
        sort = str(ext.get("sort") or "").strip()
        window = str(ext.get("window") or "").strip()
        kind = tid if tid and tid != "all" else ""

        # 类型词映射回搜索词（TVBox 可能回传显示名）
        if genre:
            for n, v in (self.GENRES.get(tid) or []):
                if genre == n:
                    genre = v
                    break

        search = self._catalog_search(kind, genre, area, year, sort, window, "", page)
        data = self._get("/v1/browse/catalog", search)

        videos = []
        for card in data.get("cards", []):
            videos.append(self._parse_card(card))

        pagination = data.get("pagination", {}) or {}
        has_more = bool(pagination.get("has_more"))
        total = pagination.get("total")
        if not isinstance(total, int) or total <= 0:
            total = (page + 1) * 20 if has_more else page * 20
        pagecount = (total + 19) // 20
        if has_more and pagecount <= page:
            pagecount = page + 1

        return {
            "page": page,
            "pagecount": max(pagecount, page),
            "limit": 20,
            "total": total,
            "list": videos,
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        data = self._get("/v1/catalog/" + vid)
        card = data.get("card", data) if isinstance(data, dict) else {}

        episodes = card.get("episodes") or []
        # 详情内嵌剧集不全时，走剧集分页接口补齐
        episode_count = card.get("episode_count") or len(episodes)
        try:
            episode_count = int(episode_count)
        except Exception:
            episode_count = len(episodes)
        if episode_count > len(episodes):
            episodes = self._fetch_all_episodes(vid, episodes)

        play_urls = []
        for ep in episodes:
            title = ep.get("title") or ep.get("display_name") or "第{}集".format(ep.get("number", ""))
            token = ep.get("token", "")
            if token:
                play_urls.append("{}${}".format(title, token))

        vod = self._parse_card(card, detail=True)
        vod["vod_id"] = vid

        # 用第1集 token 拉取线路列表，把全部线路写到播放来源，可切换播放
        lines = []
        if episodes:
            first_token = episodes[0].get("token", "")
            if first_token:
                rdata = self._get("/v1/playback/resolve/" + first_token, "?view=compact")
                lines = rdata.get("line_options", []) or []
        lines = [ln for ln in lines if ln.get("id") and ln.get("url")]
        # 官方线路与4K线路排前面（稳定排序，其余保持接口返回顺序）
        lines.sort(key=lambda ln: (0 if self._is_official_line(ln) else 1,
                                   0 if "4K" in (ln.get("label") or "").upper() else 1))

        if lines and play_urls:
            froms = []
            urls_per_line = []
            used_names = {}
            for ln in lines:
                line_id = ln.get("id", "")
                if not line_id:
                    continue
                label = ln.get("label") or ln.get("play_from") or ln.get("provider_id") or "线路"
                label = self._short_line_name(label)
                # 同名线路去重（加序号）
                if label in used_names:
                    used_names[label] += 1
                    label = "{}{}".format(label, used_names[label])
                else:
                    used_names[label] = 1
                froms.append(label)
                eps_urls = []
                for pu in play_urls:
                    title, token = pu.split("$", 1)
                    eps_urls.append("{}${}@@{}".format(title, token, line_id))
                urls_per_line.append("#".join(eps_urls))
            if froms:
                vod["vod_play_from"] = "$$$".join(froms)
                vod["vod_play_url"] = "$$$".join(urls_per_line)
            else:
                vod["vod_play_from"] = self.name
                vod["vod_play_url"] = "#".join(play_urls)
        else:
            vod["vod_play_from"] = self.name
            vod["vod_play_url"] = "#".join(play_urls)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1

        search = self._catalog_search("", "", "", "", "", "", key, page)
        data = self._get("/v1/browse/catalog", search)
        videos = []
        for card in data.get("cards", []):
            videos.append(self._parse_card(card))

        pagination = data.get("pagination", {}) or {}
        has_more = bool(pagination.get("has_more"))
        total = pagination.get("total")
        if not isinstance(total, int) or total <= 0:
            total = (page + 1) * 20 if has_more else page * 20
        pagecount = (total + 19) // 20
        if has_more and pagecount <= page:
            pagecount = page + 1
        return {
            "page": page,
            "pagecount": max(pagecount, page),
            "limit": 20,
            "total": total,
            "list": videos,
        }

    def playerContent(self, flag, id, vipFlags):
        token = id
        line_id = ""
        # 详情页写入的格式：token@@线路ID（用于切换播放来源）
        if "@@" in id:
            token, line_id = id.split("@@", 1)
        # 兼容 "集名$token" 形式
        if "$" in token:
            token = token.split("$")[-1]

        data = self._get("/v1/playback/resolve/" + token, "?view=compact")
        lines = data.get("line_options", []) or []

        play_url = ""

        # 指定线路：按 line_id（或 flag 匹配 label）精确选中
        target = None
        if line_id:
            for ln in lines:
                if ln.get("id") == line_id:
                    target = ln
                    break
        if target is None and flag and flag != self.name:
            for ln in lines:
                if (ln.get("label") or "") == flag or (ln.get("play_from") or "") == flag \
                        or self._short_line_name(ln.get("label") or "") == flag:
                    target = ln
                    break

        if target is not None:
            if target.get("url_kind") == "m3u8" and not target.get("resolve_required") and target.get("url"):
                play_url = target["url"]
            else:
                ticket = (target.get("url") or "").replace("resolve://", "")
                if ticket:
                    line = self._resolve_line(ticket)
                    if line.get("url"):
                        play_url = line["url"]

        # 回退候选：官方线路优先，全部失败才轮到普通线路（保证能播）
        official_lines = [ln for ln in lines if self._is_official_line(ln)]
        fallback_lines = official_lines + [ln for ln in lines if ln not in official_lines]

        # 未指定线路或指定线路失败：先试官方线路 resolve-line 二次解析
        if not play_url:
            candidates = [ln for ln in fallback_lines if ln.get("selected")] or fallback_lines
            for ln in candidates:
                ticket = (ln.get("url") or "").replace("resolve://", "")
                if not ticket:
                    continue
                line = self._resolve_line(ticket)
                if line.get("url"):
                    play_url = line["url"]
                    break

        # 最后兜底：免解析的 m3u8 直链线路（普通线路，按返回顺序）
        if not play_url:
            for ln in fallback_lines:
                if ln.get("url_kind") == "m3u8" and not ln.get("resolve_required") and ln.get("url"):
                    play_url = ln["url"]
                    break

        return {
            "parse": 0,
            "playUrl": "",
            "url": play_url,
            "header": {
                "User-Agent": self.ua,
                "Referer": self.host + "/",
            },
        }

    # ↓↓↓ TVBox 框架 base.spider 抽象方法必须实现，缺失会导致实例化失败 ↓↓↓
    def getName(self):
        return self.name

    def localProxy(self, param):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ================= 工具方法 =================

    def _short_line_name(self, label):
        """线路显示名简化：'1080P-官方Z · 普通话' -> '官方Z'；
        含4K的保留4K前缀以区分（'4K海外-官方C' -> '4K官方C'）；其他原样返回"""
        if "官方" in label:
            base = label.split("·")[0].strip()
            for seg in reversed(base.split("-")):
                if "官方" in seg:
                    name = seg.strip()
                    if "4K" in base.upper() and not name.upper().startswith("4K"):
                        name = "4K" + name
                    return name
        return label

    def _is_official_line(self, ln):
        """官方线路：label含"官方"，或 provider_id 为 official-*/bytevod-*"""
        label = ln.get("label") or ""
        provider = (ln.get("provider_id") or "").lower()
        if "官方" in label:
            return True
        if provider.startswith("official") or provider.startswith("bytevod"):
            return True
        return False

    def _fetch_all_episodes(self, vid, inline_eps):
        episodes = list(inline_eps)
        try:
            offset = len(episodes)
            while True:
                data = self._get("/v1/catalog/{}/episodes".format(vid),
                                 "?limit=48&offset={}".format(offset))
                eps = data.get("episodes", []) or []
                if not eps:
                    break
                episodes.extend(eps)
                page_info = data.get("episode_pagination", {}) or {}
                if not page_info.get("has_more"):
                    break
                offset += len(eps)
        except Exception as e:
            print("懂片帝 fetch episodes error: {}".format(e))
        return episodes

    def _strip_html(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        text = text.replace("&nbsp;", " ").replace("&amp;", "&") \
                   .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        return text.strip()

    def _parse_card(self, card, detail=False):
        remarks = card.get("remarks", "") or ""
        genres = card.get("genres", []) or []
        content = card.get("content", "") or card.get("description", "") or card.get("blurb", "")
        vod = {
            "vod_id": str(card.get("id", "")),
            "vod_name": card.get("title", "") or card.get("normalized_title", ""),
            "vod_pic": card.get("poster_url", "") or card.get("backdrop_url", ""),
            "vod_remarks": remarks,
            "vod_year": str(card.get("year", "") or ""),
            "vod_area": card.get("area", "") or "",
            "vod_director": "、".join(card.get("directors", []) or []),
            "vod_actor": "、".join(card.get("actors", []) or []),
        }
        if genres:
            vod["vod_type"] = " / ".join(genres[:5])
        if detail:
            # 影片简介前置微信公众号文案（XOR 加密存储，运行时解密）
            wechat = self._get_wechat_info()
            body = self._strip_html(content)
            if wechat and body:
                vod["vod_content"] = wechat + "\n" + body
            elif wechat:
                vod["vod_content"] = wechat
            else:
                vod["vod_content"] = body
        else:
            vod["vod_content"] = self._strip_html(content)
        return vod
