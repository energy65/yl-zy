# -*- coding: utf-8 -*-
"""
目标站: 蓝光影视网 (M1999)
站点地址: https://m1999.sbs
站点类型: 综合影视 (电影 / 国产剧 / 日韩剧 / 美剧 / 番剧)
模板结构: MacCMS + dsn2 主题
    /index.php/ds_api/vod                                      分类列表 JSON 接口 (POST)
    /vod/show/id/{tid}.html                                    频道页
    /vod/detail/id/{id}.html                                   详情页
    /vod/play/id/{id}/sid/{线路}/nid/{集数}.html                播放页 (内含 player_aaaa)
    /vod/search/wd/{关键词}.html                                搜索
    /vod/search/wd/{关键词}/page/{页码}.html                    搜索翻页

功能:
    - homeContent: 全部分类 + 细化类型筛选 (类型/地区/语言/年份/排序)
    - categoryContent: 走 ds_api JSON 接口, 分页完整
    - searchContent / searchContentPage: 站内搜索, 支持翻页
    - detailContent: 影片信息 + 多线路选集
    - playerContent: 解析 player_aaaa 得到 m3u8 直链, parse=0 直接播放
    - 影片简介处添加 微信公众号: 源力软件汇
"""
import re
import sys
import json
import ssl
import gzip
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
        "Chrome/131.0.0.0 Safari/537.36"
    )

    # 站点主域名 (可在 TVBox 配置中用 extend 覆盖)
    BASE_URL = "https://m1999.sbs"

    # 分类列表接口
    API_LIST = "/index.php/ds_api/vod"

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # 推广文案 (写入影片简介)
    WX_TEXT = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n"
        "QQ群：1054592152"
    )

    # ==================== 一级分类 (与站点导航一致) ====================
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "国产剧"},
        {"type_id": "3", "type_name": "日韩剧"},
        {"type_id": "4", "type_name": "美剧"},
        {"type_id": "5", "type_name": "番剧"},
    ]

    # ==================== 细化类型 (显示名 -> 站点真实标签) ====================
    _TYPES = {
        "1": [
            ("科幻片", "科幻"), ("奇幻片", "奇幻"), ("战争片", "战争"), ("犯罪片", "犯罪"),
            ("武侠片", "武侠"), ("历史片", "历史"), ("文艺片", "文艺"), ("剧情片", "剧情"),
            ("喜剧片", "喜剧"), ("爱情片", "爱情"), ("动作片", "动作"), ("恐怖片", "恐怖"),
            ("惊悚片", "惊悚"), ("悬疑片", "悬疑"), ("冒险片", "冒险"), ("动画片", "动画"),
            ("灾难片", "灾难"), ("传记片", "传记"), ("家庭片", "家庭"), ("古装片", "古装"),
            ("纪录片", "纪录"), ("短片", "短片"),
        ],
        "2": [
            ("古装", "古装"), ("都市", "都市"), ("历史", "历史"), ("谍战", "谍战"),
            ("家庭", "家庭"), ("言情", "言情"), ("武侠", "武侠"), ("悬疑", "悬疑"),
            ("科幻", "科幻"), ("喜剧", "喜剧"), ("战争", "战争"), ("青春", "青春"),
            ("偶像", "偶像"), ("罪案", "罪案"), ("剧情", "剧情"), ("爱情", "爱情"),
            ("动作", "动作"), ("犯罪", "犯罪"), ("奇幻", "奇幻"), ("惊悚", "惊悚"),
        ],
        "3": [
            ("日剧", "日剧"), ("韩剧", "韩剧"), ("剧情", "剧情"), ("爱情", "爱情"),
            ("喜剧", "喜剧"), ("犯罪", "犯罪"), ("悬疑", "悬疑"), ("古装", "古装"),
            ("家庭", "家庭"), ("奇幻", "奇幻"), ("惊悚", "惊悚"), ("恐怖", "恐怖"),
            ("动作", "动作"), ("科幻", "科幻"), ("历史", "历史"),
        ],
        "4": [
            ("剧情", "剧情"), ("喜剧", "喜剧"), ("犯罪", "犯罪"), ("悬疑", "悬疑"),
            ("动作", "动作"), ("科幻", "科幻"), ("惊悚", "惊悚"), ("奇幻", "奇幻"),
            ("爱情", "爱情"), ("冒险", "冒险"), ("恐怖", "恐怖"), ("战争", "战争"),
            ("历史", "历史"), ("家庭", "家庭"), ("泰剧", "泰剧"),
        ],
        "5": [
            ("动画", "动画"), ("奇幻", "奇幻"), ("喜剧", "喜剧"), ("剧情", "剧情"),
            ("冒险", "冒险"), ("动作", "动作"), ("科幻", "科幻"), ("爱情", "爱情"),
            ("家庭", "家庭"), ("儿童", "儿童"), ("悬疑", "悬疑"), ("恐怖", "恐怖"),
            ("战争", "战争"), ("武侠", "武侠"), ("运动", "运动"), ("校园", "校园"),
            ("热血", "热血"), ("搞笑", "搞笑"), ("治愈", "治愈"),
        ],
    }

    _AREAS = {
        "1": ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国",
              "英国", "法国", "泰国", "印度"],
        "2": ["中国大陆", "中国香港", "中国台湾", "美国", "韩国", "日本"],
        "3": ["日本", "韩国", "中国香港", "美国", "中国大陆", "泰国", "英国"],
        "4": ["美国", "英国", "法国", "泰国", "印度", "中国香港"],
        "5": ["日本", "美国", "中国大陆", "韩国", "英国", "法国"],
    }

    _LANGS = {
        "1": ["国语", "英语", "粤语", "日语", "韩语"],
        "2": ["国语", "粤语", "英语", "韩语", "日语"],
        "3": ["日语", "韩语", "国语", "英语"],
        "4": ["英语", "国语"],
        "5": ["日语", "国语", "英语", "粤语", "韩语"],
    }

    _YEARS = ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019",
              "2018", "2017", "2016", "2015", "2012", "2010", "2008", "2005",
              "2000", "1995", "1990", "1980"]

    _SORTS = [("最新", "time"), ("最热", "hits"), ("评分", "score")]

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self._parse_extend(extend)
        self._cookie = ""

    def _parse_extend(self, extend):
        """允许在配置里用 extend 覆盖站点域名"""
        if not extend:
            return self.BASE_URL
        text = str(extend).strip()
        if text.startswith("http"):
            return text.rstrip("/")
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                site = data.get("site") or data.get("url") or data.get("host")
                if site:
                    return str(site).rstrip("/")
        except Exception:
            pass
        return self.BASE_URL

    def getName(self):
        return "蓝光影视网"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== HTTP ====================
    def _request(self, path, data=None, referer=None, timeout=20):
        """统一 HTTP 请求, 返回解码后的文本"""
        url = path if str(path).startswith("http") else self.host + path
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # 注意: 站点在 Accept 含 application/json 时会返回 JSON 转义过的 HTML,
        # 页面请求必须只声明 text/html, 接口请求才声明 json
        headers = {
            "User-Agent": self.UA,
            "Accept": ("application/json, text/javascript, */*; q=0.01"
                       if data is not None else
                       "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": referer or (self.host + "/"),
        }
        body = None
        if data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data).encode("utf-8")
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = data
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        try:
            quoted = urllib.parse.quote(url, safe=":/?&=%+~-._#$@!*'(),;[]")
            req = urllib.request.Request(quoted, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
            return self._decode(raw)
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
                if "gzip" in (e.headers.get("Content-Encoding") or "").lower():
                    raw = gzip.decompress(raw)
                return self._decode(raw)
            except Exception:
                return ""
        except Exception:
            return ""

    def _decode(self, raw):
        if not raw:
            return ""
        for coding in ("utf-8", "gbk", "gb2312"):
            try:
                return raw.decode(coding)
            except Exception:
                continue
        return raw.decode("utf-8", errors="replace")

    def _get(self, path, referer=None):
        html = self._request(path, referer=referer)
        if html:
            return html
        return self._request(path, referer=referer)

    def _post_api(self, data, tid="1"):
        text = self._request(
            self.API_LIST, data=data,
            referer="%s/vod/show/id/%s.html" % (self.host, tid),
        )
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    # ==================== 工具方法 ====================
    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _clean_name(self, text):
        """清洗标题: 去掉站点注入的广告 script 及残留符号"""
        if not text:
            return ""
        name = str(text)
        name = re.sub(r"<script[\s\S]*?</script>", "", name, flags=re.I)
        name = re.sub(r"<script[^>]*>", "", name, flags=re.I)
        name = re.sub(r"<[^>]+>", "", name)
        name = html_mod.unescape(name)
        for _ in range(3):
            name = re.sub(r"^[^0-9A-Za-z\u4e00-\u9fff]+", "", name)
            if name[:7].lower() == "script>":
                name = name[7:]
            else:
                break
        return re.sub(r"\s+", " ", name).strip()

    def _img_src(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("data:") or "logo_placeholder" in url or url.endswith(".ico"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    # ==================== 筛选器 ====================
    def _build_filters(self, tid):
        tid = str(tid)
        filters = []

        types = self._TYPES.get(tid, [])
        if types:
            filters.append({
                "key": "class", "name": "类型",
                "value": [{"n": "全部", "v": ""}] +
                         [{"n": n, "v": v} for n, v in types],
            })

        areas = self._AREAS.get(tid, [])
        if areas:
            filters.append({
                "key": "area", "name": "地区",
                "value": [{"n": "全部", "v": ""}] +
                         [{"n": a, "v": a} for a in areas] +
                         [{"n": "其他", "v": "其它"}],
            })

        langs = self._LANGS.get(tid, [])
        if langs:
            filters.append({
                "key": "lang", "name": "语言",
                "value": [{"n": "全部", "v": ""}] +
                         [{"n": l, "v": l} for l in langs] +
                         [{"n": "其他", "v": "其它"}],
            })

        filters.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] +
                     [{"n": y, "v": y} for y in self._YEARS],
        })
        filters.append({
            "key": "by", "name": "排序",
            "value": [{"n": n, "v": v} for n, v in self._SORTS],
        })
        return filters

    # ==================== 卡片解析 ====================
    def _parse_home_items(self, html):
        """解析首页卡片"""
        items = []
        seen = set()
        pat = r'<a[^>]*class="public-list-exp"[^>]*href="(/vod/detail/id/(\d+)\.html)"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(3)
            name = ""
            tm = re.search(r'title="([^"]*)"', m.group(0))
            if tm:
                name = self._clean_name(tm.group(1))
            if not name:
                tm = re.search(r'alt="([^"]*)"', inner)
                if tm:
                    name = self._clean_name(tm.group(1))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-src="([^"]*)"', inner)
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            rm = re.search(r'<span class="public-prt[^"]*">([^<]*)</span>', inner)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """解析搜索结果列表"""
        items = []
        seen = set()
        blocks = re.split(r'<div class="vod-detail[^"]*search-list[^"]*">', html)
        for block in blocks[1:]:
            m = re.search(r'/vod/detail/id/(\d+)\.html', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            name = ""
            nm = re.search(r'<h3 class="slide-info-title[^"]*">([\s\S]*?)</h3>', block)
            if nm:
                name = self._clean_name(nm.group(1))
            if not name:
                nm = re.search(r'alt="([^"]*)"', block)
                if nm:
                    name = self._clean_name(nm.group(1))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-src="([^"]*)"', block)
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            rm = re.search(r'<span class="slide-info-remarks[^"]*">\s*([^<]*?)\s*</span>', block)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """首页: 全部分类 + 各分类细化筛选 + 推荐视频"""
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            filters[c["type_id"]] = self._build_filters(c["type_id"])
        videos = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": videos}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self._get("/")
            if html:
                result["list"] = self._parse_home_items(html)[:60]
        except Exception:
            pass
        return result

    # ==================== 分类 ====================
    def _apply_filters(self, data, extend):
        if not isinstance(extend, dict):
            return
        for key in ("class", "area", "lang", "year", "by"):
            val = extend.get(key)
            if isinstance(val, (list, tuple)):
                val = next((x for x in val if x not in (None, "")), "")
            if val is None:
                continue
            val = str(val).strip()
            if val and val != "全部":
                data[key] = val

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        tid = str(tid)
        # 兼容部分 TVBox 把筛选放在 filter 参数中的情况
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}

        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        data = {"type": tid, "page": page, "by": "time"}
        self._apply_filters(data, extend)
        try:
            resp = self._post_api(data, tid)
            items = resp.get("list") or []
            videos = []
            for item in items:
                videos.append({
                    "vod_id": str(item.get("vod_id", "")),
                    "vod_name": self._clean_name(item.get("vod_name", "")),
                    "vod_pic": self._img_src(item.get("vod_pic", "")) or self.DEFAULT_PIC,
                    "vod_remarks": self.clean(item.get("vod_remarks", "")),
                })
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = int(resp.get("total") or len(videos))
            result["pagecount"] = int(resp.get("pagecount") or page)
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
            word = urllib.parse.quote(str(key).strip())
            if page > 1:
                path = "/vod/search/wd/%s/page/%d.html" % (word, page)
            else:
                path = "/vod/search/wd/%s.html" % word
            html = self._get(path)
            if not html:
                return result
            videos = self._parse_search_items(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            # 搜索每页 10 条, 满页则认为还有下一页
            result["pagecount"] = page + 1 if len(videos) >= 10 else page
        except Exception:
            pass
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = re.sub(r"\D", "", str(vid))
        if not vid:
            return result
        try:
            html = self._get("/vod/detail/id/%s.html" % vid)
        except Exception:
            html = ""
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": vid}

        # 标题
        name = ""
        m = re.search(r'<h3 class="slide-info-title[^"]*">([\s\S]*?)</h3>', html)
        if m:
            name = self._clean_name(m.group(1))
        if not name:
            m = re.search(r'<title>([^<]*)</title>', html)
            if m:
                name = self._clean_name(re.sub(r"[_-].*$", "", self.clean(m.group(1))))
        vod["vod_name"] = name if name else vid

        # 封面
        pic = ""
        pm = re.search(r'<div class="detail-pic">[\s\S]*?data-src="([^"]+)"', html)
        if pm:
            pic = self._img_src(pm.group(1))
        vod["vod_pic"] = pic if pic else self.DEFAULT_PIC

        # 影片参数
        infos = self._detail_infos(html)
        vod["vod_director"] = infos.get("导演", "")
        vod["vod_actor"] = infos.get("主演", "") or infos.get("演员", "")
        vod["vod_year"] = infos.get("年份", "")
        vod["vod_area"] = infos.get("地区", "")
        vod["vod_class"] = infos.get("类型", "")
        vod["vod_lang"] = infos.get("语言", "")
        vod["vod_remarks"] = infos.get("状态", "") or infos.get("更新", "")

        # 简介 + 推广文案 (置于最前)
        desc = self._detail_desc(html) or infos.get("简介", "")
        vod["vod_content"] = self.WX_TEXT + ("\n\n" + desc if desc else "")

        # 播放线路 + 选集
        from_arr, url_arr = self._detail_plays(html, vid)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            vod["vod_play_from"] = "蓝光专线"
            vod["vod_play_url"] = "正片$%s/vod/play/id/%s/sid/1/nid/1.html" % (self.host, vid)

        result["list"] = [vod]
        return result

    def _detail_infos(self, html):
        """解析 info-parameter 中的影片参数"""
        infos = {}
        block = ""
        m = re.search(r'<div class="info-parameter[^"]*">([\s\S]*?)</div></div></div>', html)
        if m:
            block = m.group(1)
        if not block:
            return infos
        for li in re.findall(r"<li[^>]*>([\s\S]*?)</li>", block):
            em = re.search(r"<em[^>]*>([\s\S]*?)</em>([\s\S]*)", li)
            if not em:
                continue
            label = self.clean(em.group(1)).rstrip("：:")
            value = re.sub(r"<[^>]+>", ",", em.group(2))
            value = self.clean(value)
            value = re.sub(r"\s*,\s*", ",", value).strip(",")
            if label and value:
                infos[label] = value
        return infos

    def _detail_desc(self, html):
        m = re.search(r'<div id="height_limit"[^>]*>([\s\S]*?)</div>', html)
        if m:
            txt = re.sub(r"<br\s*/?>", "\n", m.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt:
                return txt
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            return self.clean(m.group(1))
        return ""

    def _detail_plays(self, html, vid):
        """解析线路标签与选集列表, 一一对应"""
        tab_block = ""
        m = re.search(r'<div class="anthology-tab[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>', html)
        if m:
            tab_block = m.group(1)
        labels = []
        for a in re.findall(r"<a[^>]*>([\s\S]*?)</a>", tab_block):
            label = re.sub(r'<span class="badge[^"]*">[\s\S]*?</span>', "", a)
            label = self.clean(re.sub(r"<[^>]+>|&nbsp;", " ", label))
            labels.append(label or "线路%d" % (len(labels) + 1))

        boxes = re.findall(
            r'<div class="anthology-list-box[^"]*">\s*<div>\s*<ul[^>]*>([\s\S]*?)</ul>',
            html,
        )
        if not boxes:
            # 兜底: 直接取所有选集链接
            eps = re.findall(
                r'<a[^>]*href="(/vod/play/[^"]+)"[^>]*>([^<]*)</a>', html)
            if not eps:
                return [], []
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s%s" % (ep_name, self.host, ep_path))
            return ["蓝光专线"], ["#".join(lines)]

        from_arr, url_arr = [], []
        used = {}
        for i, box in enumerate(boxes):
            eps = re.findall(
                r'<a[^>]*href="(/vod/play/id/%s/sid/\d+/nid/\d+\.html)"[^>]*>([^<]*)</a>'
                % re.escape(vid), box)
            if not eps:
                continue
            label = labels[i] if i < len(labels) else "线路%d" % (i + 1)
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s%s" % (ep_name, self.host, ep_path))
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

        try:
            html = self._get(play_url, referer=self.host + "/")
        except Exception:
            html = ""

        real = self._extract_play_url(html)
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

    def _extract_play_url(self, html):
        """从播放页 player_aaaa 提取真实 m3u8/mp4 地址"""
        if not html:
            return ""
        data = {}
        m = re.search(r"var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>", html)
        if m:
            try:
                data = json.loads(m.group(1))
            except Exception:
                data = {}
        url = ""
        if isinstance(data, dict):
            url = str(data.get("url") or data.get("playurl") or "")
            if str(data.get("encrypt") or "0") != "0" and url:
                # MacCMS 加密线路: 一般是 urlencode 后的地址
                url = urllib.parse.unquote(url)
        if not url:
            mm = re.search(r'"url"\s*:\s*"(https?:[^"]+?\.(?:m3u8|mp4)[^"]*)"', html)
            if mm:
                url = mm.group(1)
        url = url.replace("\\/", "/").strip()
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http") and (".m3u8" in url or ".mp4" in url):
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
