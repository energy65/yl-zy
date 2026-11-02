# -*- coding: utf-8 -*-
# QQ群：807916734 @Easy
# TVB云播(com.hktvyb.app) -> dr_py / TVBox Python 爬虫源
#
# 协议: Getapp 方案(MacCMS v10 + /api/vod/ 前缀), 写作风格对齐 getapp3.4.6.py
# 实测结论(2026-09-17, host=app.tuxianimg.com):
#   - 全部接口形如 http://<host>/api/vod/<endpoint>, 请求方式 POST(form-urlencoded)
#   - 成功响应 {"code":0,"msg":"","data":"<AES-128-CBC base64>"}, key == iv == data_key(16字节)
#   - 签名: app-api-verify-time + app-api-verify-sign(=AES(time)); init 免签, 其余接口带签
#   - 首页: init -> type_list[{type_id,type_name,type_extend,recommend_list,filter_type_list}]
#           顶层另有 recommend_list(热门) 与 banner_list
#   - 分类: typeFilterVodList(area/year/type_id/page/sort/lang/class) -> recommend_list
#   - 搜索: searchList(keywords/type_id/page) -> search_list
#   - 详情: vodDetail(vod_id) -> vod + player_source_list + vod_play_url_list[{player_code,urls:[{episode_index,name,url}]}]
#   - 播放: urls[].url 为空时用 vodParse(vod_id+player_source_id+episode_index+scene=0) 换 play_url(带 trial 试看限制)
#
# 使用前提(重要):
#   1) host/key 默认取下方类常量; 亦可在配置软链参数覆盖: host/域名、datakey/数据密钥、ua/用户代理、版本
#   2) 仅保留后缀名是 /api/vod/ 的接口代码, 其余(verify/OCR/登录/VIP)一律不引入
import sys
import re
import json
import time
import base64
import hashlib
from urllib.parse import quote

sys.path.append('..')

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except Exception:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

from base.spider import Spider



PLAY_LINE_ORDER = [
    "4K", "至臻", "臻影", "鲸宝", "爱壹帆", "玫瑰", "咖啡4K", "2K", "蓝光", "1080", "超清", "HD", "高清", "VIP", "精品", "极速", "标清", "流畅",
]

def _clean_line_name(name):
    if not name: return ""
    clean = re.sub(r'[【\[\(（].*?[】\]）)]', '', str(name))
    clean = re.sub(r'\(\d+\)$', '', clean)
    clean = re.sub(r'\s*(?:HD|VIP|备用|推荐|极速|高清|标清|蓝光|超清|试看|抢先|预告|新版|旧版)\s*$', '', clean, flags=re.I)
    return re.sub(r'\s+', ' ', clean).strip()

def _line_rank(name, play_order=PLAY_LINE_ORDER):
    clean = _clean_line_name(name)
    low = clean.lower()
    for i, kw in enumerate(play_order):
        kl = kw.lower()
        if low and (low == kl or low.startswith(kl) or kl in low):
            return i
    # 清洗后没命中名单时用原名再匹配一次: 纯画质名(如"蓝光""高清")会被
    # 清洗削空、"腾讯极速"这类会被削掉画质后缀, 原版会把它们误排到最后
    rl = str(name or "").lower()
    if rl and rl != low:
        for i, kw in enumerate(play_order):
            kl = kw.lower()
            if rl == kl or rl.startswith(kl) or kl in rl:
                return i
    if not clean: return 9999
    up = clean.upper()
    if any(x in clean for x in ('至臻', '臻影', '鲸宝', '爱壹帆')): return 100
    if '4K' in up or '4k' in clean or '2160' in clean: return 200
    if '2K' in up or '2k' in clean or '1440' in clean: return 240
    if '蓝光' in clean: return 250
    if any(x in clean for x in ('1080', '超清', 'UHD')): return 350
    if any(x in up for x in ('HD', 'VIP')) or any(x in clean for x in ('高清', '精品', '极速', '金牌')): return 400
    if '☆' in clean: return 500
    if '自营' in clean: return 600
    if any(x in clean for x in ('标清', '流畅', '普清')): return 700
    return 4000


# ---- 影片简介推广文案（XOR 加密存储，运行时解密；勿在代码中出现明文） ----
# 解密结果：微信公众号“源力软件汇”，更多优质资源尽在源力捐赠版
_W_KEY = "yunbo_wechat_2026"
_W_DATA = [
    24535, 20372, 20738, 20341, 21400, 8259, 28391, 21246, 36620, 20126,
    27686, 8297, 65363, 26310, 22826, 20266, 36126, 36157, 28389, 23635,
    22346, 28415, 21188, 25383, 36101, 29227,
]


def _get_wechat_info():
    """解密影片简介推广文案。"""
    try:
        key = _W_KEY
        return "".join(
            chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(_W_DATA))
    except Exception:
        return ""


class Spider(Spider):
    title = "TVB云播"
    lang = "zh"
    searchable = 2
    filterable = 1
    quickSearch = 1

    # ---- 配置 ----
    xurl = "http://app.tuxianimg.com"
    key = "MickwrKuMickwrKu"
    iv = "MickwrKuMickwrKu"
    api_path_prefix = "/api/vod"

    def __init__(self):
        self.header = {
            "User-Agent": "okhttp/4.9.3",
            "App-Os-Type": "android",
            "App-Version-Code": "585",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        self.init_data = {}

    def getName(self):
        return self.title

    # ---------------- 工具 ----------------
    def _norm16(self, s):
        b = s.encode("utf-8")
        if len(b) < 16:
            return b.ljust(16, b"\x00")
        return b[:16]

    def decrypt(self, encrypted_b64):
        key_bytes = self._norm16(self.key)
        iv_bytes = self._norm16(self.iv)
        encrypted = base64.b64decode(encrypted_b64)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
        return decrypted.decode("utf-8")

    def encrypt(self, text):
        key_bytes = self._norm16(self.key)
        iv_bytes = self._norm16(self.iv)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        ct = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
        return base64.b64encode(ct).decode("utf-8")

    def _generate_api_sign(self, timestamp):
        if not self.key:
            return ""
        key_bytes = self._norm16(self.key)
        iv_bytes = self._norm16(self.iv)
        try:
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            return base64.b64encode(
                cipher.encrypt(pad(str(timestamp).encode("utf-8"), AES.block_size))
            ).decode("utf-8")
        except Exception:
            return ""

    def _build_api_url(self, endpoint):
        prefix = self.api_path_prefix.strip()
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        if prefix.endswith("/"):
            prefix = prefix.rstrip("/")
        return f"{self.xurl}{prefix}/{endpoint}"

    def _fix_image_url(self, pic):
        if not pic:
            return ""
        if pic.startswith(("http://", "https://")):
            return pic
        if pic.startswith("/"):
            return self.xurl + pic
        return self.xurl + "/" + pic

    def _add_sign_headers(self, headers):
        ts = str(int(time.time()))
        sign = self._generate_api_sign(ts)
        if sign:
            headers["app-api-verify-time"] = ts
            headers["app-api-verify-sign"] = sign
        return headers

    def _post(self, endpoint, data=None):
        return self._request_api(endpoint, data, with_sign=True)

    def _post_no_sign(self, endpoint, data=None):
        return self._request_api(endpoint, data, with_sign=False)

    def _request_api(self, endpoint, data=None, with_sign=True):
        """统一 API 请求入口, 站点限流严格, 失败自动重试 3 次。"""
        url = self._build_api_url(endpoint)
        payload = data or {}
        for attempt in range(3):
            headers = self._add_sign_headers(self.header.copy()) if with_sign else self.header.copy()
            try:
                resp = self.post(url, headers=headers, data=payload, timeout=15)
                if resp.status_code != 200:
                    continue
                j = resp.json()
                if not isinstance(j, dict) or j.get("code") != 0:
                    return None
                enc = j.get("data")
                if not enc:
                    return j
                return json.loads(self.decrypt(enc))
            except Exception as e:
                print(f"TVB请求失败 [{endpoint}] 第{attempt + 1}次: {e}")
                if attempt < 2:
                    time.sleep(1.2)
        return None

    # ---------------- init ----------------
    def init(self, extend=""):
        if extend:
            try:
                ext = json.loads(extend.strip())
            except Exception:
                ext = {}
            host = ext.get("host") or ext.get("域名")
            if host:
                self.xurl = host.rstrip("/")
            key = ext.get("datakey") or ext.get("数据密钥")
            if key:
                self.key = key
                self.iv = key

        data = self._post_no_sign("init", {})
        if data:
            self.init_data = data

    # ---------------- 首页 ----------------
    # 筛选参数 -> 中文名
    FILTER_NAME_MAP = {"class": "类型", "area": "地区", "lang": "语言", "year": "年份", "sort": "排序"}
    # 电影分类(1)的类型筛选按"XX片"风格展示(科幻->科幻片), 传参仍用站点原名
    MOVIE_TYPE_IDS = ("1",)

    def _class_display(self, tid, val):
        if not val or val == "全部":
            return "全部"
        if tid in self.MOVIE_TYPE_IDS and not val.endswith(("片", "电影")):
            return val + "片"
        return val

    def _dedup(self, values):
        out = []
        for v in values:
            v = str(v).strip()
            if v and v not in out:
                out.append(v)
        return out

    def _build_filter_items(self, tid, fmap):
        items = []
        for key in ("class", "area", "lang", "year", "sort"):
            values = fmap.get(key)
            if not values:
                continue
            if key == "class":
                display = [{"n": self._class_display(tid, v), "v": v} for v in values]
            else:
                display = [{"n": v, "v": v} for v in values]
            items.append({"key": key, "name": self.FILTER_NAME_MAP.get(key, key), "value": display})
        if not any(it["key"] == "sort" for it in items):
            items.append({"key": "sort", "name": "排序", "value": [
                {"n": "最新", "v": "最新"}, {"n": "最热", "v": "最热"}, {"n": "最赞", "v": "最赞"}]})
        return items

    def _build_all_filter_items(self, classes, years):
        items = []
        if classes:
            items.append({"key": "class", "name": "类型", "value":
                [{"n": "全部", "v": "全部"}] + [{"n": v, "v": v} for v in classes]})
        if years:
            items.append({"key": "year", "name": "年份", "value":
                [{"n": "全部", "v": "全部"}] + [{"n": v, "v": v} for v in years]})
        items.append({"key": "sort", "name": "排序", "value": [
            {"n": "最新", "v": "最新"}, {"n": "最热", "v": "最热"}, {"n": "最赞", "v": "最赞"},
            {"n": "日榜", "v": "日榜"}, {"n": "周榜", "v": "周榜"}, {"n": "月榜", "v": "月榜"}]})
        return items

    def homeContent(self, filter):
        if not self.init_data:
            self.init("")
        data = self.init_data
        result = {"class": [], "filters": {}}

        all_classes = []
        all_years = []
        for t in data.get("type_list") or []:
            tid = str(t.get("type_id"))
            result["class"].append({"type_id": tid, "type_name": t.get("type_name", "")})

            fmap = {}
            for f in t.get("filter_type_list") or []:
                fname = str(f.get("name") or "")
                values = self._dedup(f.get("list") or [])
                if values:
                    fmap[fname] = values

            for v in fmap.get("class") or []:
                if v != "全部" and v not in all_classes:
                    all_classes.append(v)
            for v in fmap.get("year") or []:
                if v != "全部" and v not in all_years:
                    all_years.append(v)

            filter_items = self._build_filter_items(tid, fmap)
            if filter_items:
                result["filters"][tid] = filter_items

        # "全部"分类: 汇总各分类的细化类型/年份, 服务端支持 type_id=0 联合筛选
        if any(c["type_id"] == "0" for c in result["class"]):
            result["filters"]["0"] = self._build_all_filter_items(all_classes, all_years)

        return result

    def homeVideoContent(self):
        if not self.init_data:
            self.init("")
        data = self.init_data
        videos = []
        seen = set()

        def add(v):
            vid = v.get("vod_id")
            if not vid or vid in seen:
                return
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": v.get("vod_name", ""),
                "vod_pic": self._fix_image_url(v.get("vod_pic", "")),
                "vod_remarks": v.get("vod_remarks", ""),
            })

        for item in data.get("banner_list") or []:
            add(item)
        for item in data.get("recommend_list") or []:
            add(item)
        for t in data.get("type_list") or []:
            for item in t.get("recommend_list") or []:
                add(item)
        return {"list": videos}

    def homeVod(self):
        try:
            return self.homeVideoContent()
        except Exception:
            return {"list": []}

    # ---------------- 分类 ----------------
    def categoryContent(self, cid, pg, filter, ext):
        ext = ext or {}
        body = {
            "area": ext.get("area") or "全部",
            "year": ext.get("year") or "全部",
            "type_id": cid,
            "page": str(pg),
            "sort": ext.get("sort") or "最新",
            "lang": ext.get("lang") or "全部",
            "class": ext.get("class") or "全部",
        }
        data = self._post("typeFilterVodList", body)
        if not data:
            return {"list": [], "page": pg, "pagecount": 9999, "limit": 90, "total": 999999}

        videos = []
        for item in data.get("recommend_list") or []:
            videos.append({
                "vod_id": item.get("vod_id"),
                "vod_name": item.get("vod_name", ""),
                "vod_pic": self._fix_image_url(item.get("vod_pic", "")),
                "vod_remarks": item.get("vod_remarks", ""),
            })
        total = data.get("total") or 0
        return {"list": videos, "page": pg, "pagecount": 9999, "limit": 90, "total": total or 999999}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg=1):
        videos = []
        payload = {"keywords": key, "type_id": "0", "page": str(pg)}
        data = self._post("searchList", payload)
        if data:
            for i in data.get("search_list") or []:
                remarks = i.get("vod_remarks") or (f"{i.get('vod_year', '')} {i.get('vod_class', '')}").strip()
                videos.append({
                    "vod_id": i.get("vod_id"),
                    "vod_name": i.get("vod_name", ""),
                    "vod_pic": self._fix_image_url(i.get("vod_pic", "")),
                    "vod_remarks": remarks,
                })
        return {"list": videos, "page": pg, "pagecount": 9999, "limit": 90, "total": 999999}

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else ids
        body = {"vod_id": did}
        data = self._post("vodDetail", body)
        if not data:
            return {"list": []}

        vod = data.get("vod") or {}
        player_info_map = {}
        for p in data.get("player_source_list") or []:
            player_info_map[p.get("player_code")] = p

        vod_play_url_list = data.get("vod_play_url_list") or []

        play_from = []
        play_url = []
        name_count = {}

        for itt in vod_play_url_list:
            player_code = itt.get("player_code", "")
            pinfo = player_info_map.get(player_code, {})
            player_name = pinfo.get("player_name") or player_code

            if any(kw in player_name for kw in ("防走丢", "群", "防失群", "官网")):
                player_name = f"线路{len(name_count) + 1}"

            cnt = name_count.get(player_name, 0) + 1
            name_count[player_name] = cnt
            if cnt > 1:
                player_name = f"{player_name}{cnt}"

            play_from.append(player_name)

            kurls = []
            for idx, it in enumerate(itt.get("urls") or []):
                parse_api = (it.get("parse_api_url") or "").replace(it.get("url") or "", "") or pinfo.get("parse_api") or ""
                play_data = {
                    "url": it.get("url", ""),
                    "parse_api": parse_api,
                    "token": it.get("token", ""),
                    "vod_id": did,
                    "player_source_id": pinfo.get("id", ""),
                    "episode_index": it.get("episode_index") if it.get("episode_index") is not None else idx,
                    "parse_type": str(pinfo.get("player_parse_type", "1")),
                    "user_agent": pinfo.get("user_agent", ""),
                    "headers": pinfo.get("headers") or {},
                }
                kurls.append(f"{it.get('name', '')}${base64.b64encode(json.dumps(play_data, ensure_ascii=False).encode()).decode()}")
            if kurls:
                play_url.append("#".join(kurls))

        paired = sorted(zip(play_from, play_url), key=lambda item: _line_rank(item[0], PLAY_LINE_ORDER))
        if paired:
            play_from, play_url = [x[0] for x in paired], [x[1] for x in paired]

        # 简介: 去HTML标签后前置推广文案(运行时解密)
        wx = _get_wechat_info()
        content = str(vod.get("vod_content") or vod.get("vod_blurb") or "")
        content = re.sub(r"<[^>]+>", "", content).strip()
        full_content = (wx + "\n" + content) if wx else content

        return {"list": [{
            "vod_id": did,
            "vod_name": vod.get("vod_name", ""),
            "vod_pic": self._fix_image_url(vod.get("vod_pic", "")),
            "vod_actor": str(vod.get("vod_actor", "")).replace("演员", ""),
            "vod_director": str(vod.get("vod_director", "")).replace("导演", ""),
            "vod_content": full_content,
            "vod_remarks": vod.get("vod_remarks", ""),
            "vod_class": vod.get("vod_class", ""),
            "vod_year": f"{vod['vod_year']}年" if vod.get("vod_year") else "",
            "vod_area": vod.get("vod_area", ""),
            "vod_lang": vod.get("vod_lang", ""),
            "vod_score": str(vod.get("vod_score") or ""),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }]}

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        try:
            play_data = json.loads(base64.b64decode(id.encode()).decode())
        except Exception:
            return {"parse": 0, "url": id, "header": {}}

        h = {"User-Agent": play_data.get("user_agent") or "okhttp/4.9.3"}
        pd_headers = play_data.get("headers") or {}
        if isinstance(pd_headers, dict):
            for k, v in pd_headers.items():
                if not v:
                    continue
                if k.lower() == "user-agent" and not play_data.get("user_agent"):
                    h["User-Agent"] = v
                elif k.lower() == "referer":
                    if "Referer" not in h:
                        h["Referer"] = v
                else:
                    h[k] = v

        url = play_data.get("url", "")
        parse_api = play_data.get("parse_api", "")
        token = play_data.get("token", "")
        parse_type = play_data.get("parse_type", "1")
        vod_id = play_data.get("vod_id", "")
        player_source_id = play_data.get("player_source_id", "")
        episode_index = play_data.get("episode_index", 0)

        try:
            # 1) 外置解析
            if parse_api and "url=" in parse_api and parse_api.startswith("http"):
                try:
                    resp = self.get(parse_api + url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
                    play = resp.get("url")
                    if not play and isinstance(resp.get("data"), dict):
                        play = resp["data"].get("url")
                    if play:
                        return {"parse": 0, "url": play, "header": h}
                except Exception:
                    pass
                return {"parse": 1, "url": parse_api, "header": h}

            # 2) 自带解析器 vodParse
            if parse_api and url:
                body = f"parse_api={quote(parse_api)}&url={quote(self.encrypt(url))}&player_parse_type={parse_type}&token={token}&scene=0"
                resp = self._post("vodParse", body)
                if resp:
                    parsejson = resp
                    play = parsejson.get("url")
                    if not play and "json" in parsejson:
                        try:
                            play = json.loads(parsejson["json"]).get("url")
                        except Exception:
                            pass
                    if play:
                        return {"parse": 0, "url": play, "header": h}
                return {"parse": 1, "url": "", "header": h}

            # 3) url 为空, 用 vodParse 换地址
            if vod_id and not url:
                body = f"vod_id={vod_id}&player_source_id={player_source_id}&episode_index={episode_index}&scene=0"
                resp = self._post("vodParse", body)
                if not resp:
                    return {"parse": 1, "url": "", "header": h}
                trial = resp.get("trial")
                if trial and not trial.get("current_episode_allowed", False):
                    return {"parse": 1, "url": "", "header": h, "msg": "试看限制"}
                play = resp.get("play_url") or resp.get("url")
                if play:
                    return {"parse": 0, "url": play, "header": h}
                return {"parse": 1, "url": "", "header": h}

            # 4) 直链
            if url:
                return {"parse": 0, "url": url, "header": h}
            return {"parse": 1, "url": "", "header": h}
        except Exception as e:
            print(f"TVB播放失败: {e}")
            return {"parse": 1, "url": "", "header": h}

    def isVideoFormat(self, url):
        return any(url.lower().endswith(fmt) for fmt in [".m3u8", ".mp4", ".avi", ".mkv", ".flv", ".ts"])

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        if params.get("type") == "m3u8":
            return {
                "url": params.get("url", ""),
                "header": params.get("header", {}),
                "param": params.get("param", ""),
                "type": "m3u8",
            }
        return None


if __name__ == "__main__":
    pass
