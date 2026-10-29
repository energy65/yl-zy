# -*- coding: utf-8 -*-
"""
星辰4K TVBox Python Spider
网站: https://hqvod.com/
模板: MacCMS (theme2 HQ模板)
URL 模式:
    /fenlei/{tid}.html                 分类页 (第1页)
    /fenlei/{tid}-{page}.html          分类页 (第2+页)
    /xiangqing/{id}.html               详情页
    /bofang/{vid}-{sid}-{nid}.html     播放页
    /sousuo/-------------{key}.html    搜索 (13个短横线)

播放链路:
    player_aaaa (encrypt=0 但 url 为加密 token)
    → parse.js 加载外部解析器 xn--2p1a.bfapi.cyou/player/?url={token}
    → 外部解析器用 crypto-js (AES) 解码后返回 m3u8 播放
    → Spider 实现: playerContent 优先用 CookieJar 访问播放页提取 token 构建外部解析器 URL + parse=1
                  失败时 fallback 直接返回播放页 URL + parse=1 让 TVBox WebView 自动处理

功能:
    - homeContent: 4个主分类 + 各分类二级筛选 (类型/地区/年份)
    - homeVideoContent: 首页推荐视频
    - categoryContent: 分类列表 + 类型/地区/年份筛选
    - searchContent: 站内搜索
    - detailContent: 详情页 + 多播放源选集 (按线路名分组)
    - playerContent: 播放解析 (外部解析器 + parse=1)
    - 影片简介处添加微信公众号 (XOR 加密存储)
"""

import re
import ssl
import json
import urllib.request
import urllib.parse
import http.cookiejar
import html as html_mod

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    BASE_URL = "https://hqvod.com"
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36")

    # ==================== 微信推广文案 (XOR 加密) ====================
    _W_KEY = 'xingchen4k_wechat_2026'
    _W_FULL_DATA = [24534, 20360, 20738, 20336, 21396, 74, 28405, 21237, 36699, 20125,
                    27672, 85, 65385, 26263, 22898, 20345, 36188, 36123, 28322, 23565,
                    22298, 28326, 21219, 25401, 36110, 29231]
    _W_LINE_DATA = [28392, 21234, 24351, 35233, 212, 24518, 20356, 20738, 20259, 21404,
                    28367, 21228, 36618, 20117, 27695]

    def _w_decrypt(self, data):
        try:
            return "".join(chr(v ^ ord(self._W_KEY[i % len(self._W_KEY)])) for i, v in enumerate(data))
        except Exception:
            return ""

    def _get_wechat_info(self):
        return self._w_decrypt(self._W_FULL_DATA)

    # ==================== 初始化 ====================
    def init(self, extend=""):
        pass

    def getName(self):
        return "星辰4K"

    # ==================== 一级分类 ====================
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺"},
    ]

    # ==================== 类型筛选 (细化分类) ====================
    CLASS_FILTERS = {
        "1": ["科幻片", "奇幻片", "战争片", "犯罪片", "武侠片", "历史片", "文艺片",
              "喜剧片", "爱情片", "恐怖片", "悬疑片", "惊悚片", "冒险片", "动作片",
              "动画片", "纪录片", "西部片", "同性"],
        "2": ["古装", "都市", "历史", "谍战", "武侠", "家庭", "言情", "青春", "悬疑",
              "恐怖", "喜剧", "爱情", "战争", "犯罪", "科幻", "奇幻", "同性"],
        "3": ["国产动漫", "日韩动漫", "欧美动漫", "动画电影", "古装", "奇幻",
              "科幻", "冒险", "热血", "机甲"],
        "4": ["大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "真人秀", "访谈",
              "音乐", "脱口秀", "晚会"],
    }

    AREA_FILTERS = ["大陆", "香港", "台湾", "美国", "英国", "法国", "德国",
                    "日本", "韩国", "泰国", "印度", "意大利", "西班牙", "加拿大", "其它"]

    YEAR_FILTERS = ["2026", "2025", "2024", "2023", "2022", "2021", "2020",
                    "2019", "2018", "2017", "2016", "2015", "2014", "2013",
                    "2012", "2011", "2010", "2008", "2005", "2000"]

    _MAIN_TYPES = ("电影", "电视剧", "动漫", "综艺", "短剧")

    # ==================== HTTP 工具 ====================
    def _build_opener(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPCookieProcessor(cj)
        )
        return opener

    def _http_get(self, url, referer=None, opener=None):
        """HTTP GET 返回解码后的文本, CookieJar 维持会话"""
        if opener is None:
            opener = self._build_opener()
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = opener.open(req, timeout=20)
            data = resp.read()
        except Exception:
            return "", opener
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc), opener
            except Exception:
                continue
        return data.decode("utf-8", errors="replace"), opener

    def _clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = text.replace("\u200b", "").replace("\ufeff", "")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _absurl(self, u):
        if not u:
            return ""
        if u.startswith("http"):
            return u
        if u.startswith("//"):
            return "https:" + u
        return self.BASE_URL + ("" if u.startswith("/") else "/") + u

    def _img_src(self, url):
        if not url:
            return ""
        if url.endswith(".ico"):
            return ""
        return self._absurl(url)

    # ==================== 视频卡片解析 ====================
    def _parse_video_cards(self, html):
        """解析列表页的视频卡片 (public-list-exp 结构)"""
        items = []
        seen = set()
        # 视频卡片链接: /xiangqing/{id}.html 带 title
        for m in re.finditer(
                r'<a[^>]*class="public-list-exp"[^>]*href="(/xiangqing/(\d+)\.html)"[^>]*title="([^"]*)"',
                html):
            href, vid, name = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            name = self._clean(name)
            if not name:
                continue
            # 图片: 在匹配位置附近找 data-src
            block_start = m.start()
            block_end = min(block_start + 2000, len(html))
            block = html[block_start:block_end]
            pic = ""
            # data-src 优先
            pm = re.search(r'data-src="([^"]+)"', block)
            if pm:
                pic = pm.group(1)
            else:
                pm = re.search(r'<img[^>]+src="([^"]+)"', block)
                if pm:
                    pic = pm.group(1)
            if pic and ("s3plus" in pic.lower() or "favicon" in pic.lower()):
                pic = ""
            # 备注
            remark = ""
            rm = re.search(r'<span class="public-list-prb[^"]*">([^<]*)</span>', block)
            if rm:
                remark = self._clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._img_src(pic),
                "vod_remarks": remark,
            })
        return items

    def _parse_pagecount(self, html, page):
        """从分页链接提取最大页码"""
        nums = []
        for m in re.finditer(r'href="[^"]*/(\d+)\.html"[^>]*>(\d+)</a>', html):
            try:
                n = int(m.group(2))
                if n > 1:
                    nums.append(n)
            except Exception:
                continue
        if nums:
            return max(nums)
        return page + 1

    # ==================== 首页 ====================
    def _build_filters(self, tid):
        tid = str(tid)
        f = []
        classes = self.CLASS_FILTERS.get(tid, [])
        if classes:
            f.append({
                "key": "class", "name": "类型",
                "value": [{"n": "全部", "v": ""}] + [{"n": c, "v": c} for c in classes],
            })
        f.append({
            "key": "area", "name": "地区",
            "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.AREA_FILTERS],
        })
        f.append({
            "key": "year", "name": "年份",
            "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.YEAR_FILTERS],
        })
        return f

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in self.CATEGORIES]
        filters = {}
        for c in self.CATEGORIES:
            filters[c["type_id"]] = self._build_filters(c["type_id"])
        # 首页视频
        list_data = self.homeVideoContent().get("list", [])
        return {"class": classes, "filters": filters, "list": list_data}

    def homeVideoContent(self):
        result = {"list": []}
        html, _ = self._http_get(self.BASE_URL + "/")
        if not html:
            return result
        result["list"] = self._parse_video_cards(html)[:30]
        return result

    # ==================== 分类 ====================
    def _apply_filters(self, extend):
        """从 extend 提取筛选值"""
        if not isinstance(extend, dict):
            return {}
        out = {}
        for k in ("class", "area", "year"):
            v = str(extend.get(k) or "").strip()
            if v and v != "全部":
                out[k] = v
        return out

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = str(tid)
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

        # 无筛选 → 直接分类页
        filters = self._apply_filters(extend)
        if not filters:
            path = f"/fenlei/{tid}.html" if page == 1 else f"/fenlei/{tid}-{page}.html"
            html, _ = self._http_get(self.BASE_URL + path)
            if not html:
                return result
            result["list"] = self._parse_video_cards(html)
            result["pagecount"] = self._parse_pagecount(html, page)
            result["limit"] = len(result["list"])
            result["total"] = len(result["list"])
            return result

        # 有筛选 → MacCMS /s/ 组合筛选
        segs = []
        for field, value in filters.items():
            # 地区字段 MacCMS 标准是 "未知"
            if field == "area":
                field = "未知"
            segs.append(urllib.parse.quote(field))
            segs.append(urllib.parse.quote(value))
        if page > 1:
            segs.extend(["page", str(page)])
        path = "/s/" + "/".join(segs) + ".html"
        html, _ = self._http_get(self.BASE_URL + path)
        if html:
            result["list"] = self._parse_video_cards(html)
            result["pagecount"] = self._parse_pagecount(html, page)
            result["limit"] = len(result["list"])
            result["total"] = len(result["list"])
        return result

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        if not key:
            return result
        kw_enc = urllib.parse.quote(key)
        # 13个短横线 (MacCMS 标准)
        dashes = "-" * 13
        if page == 1:
            path = f"/sousuo/{dashes}{kw_enc}.html"
        else:
            path = f"/sousuo/{dashes}{kw_enc}-{page}.html"
        html, _ = self._http_get(self.BASE_URL + path)
        if not html:
            return result
        result["list"] = self._parse_video_cards(html)
        result["pagecount"] = self._parse_pagecount(html, page)
        result["limit"] = len(result["list"])
        result["total"] = len(result["list"])
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip()
        dm = re.search(r'/xiangqing/(\d+)\.html', vid)
        if dm:
            vid = dm.group(1)
        if not vid.isdigit():
            return result

        html, opener = self._http_get(self.BASE_URL + f"/xiangqing/{vid}.html")
        if not html or len(html) < 2000:
            return result

        vod = {"vod_id": vid}

        # --- 标题 ---
        title = ""
        tm = re.search(r'<title>(.*?)</title>', html, re.S)
        if tm:
            mm = re.search(r'《(.+?)》', tm.group(1))
            title = mm.group(1) if mm else tm.group(1).split("_")[0].split("-")[0].strip()
        if not title:
            for m in re.finditer(
                    r'class="[^"]*(?:vod-name|slide-info-title|detail-title|title)[^"]*"[^>]*>([^<]+)', html):
                t = self._clean(m.group(1))
                if t and len(t) >= 2:
                    title = t
                    break
        vod["vod_name"] = title if title else vid

        # --- 封面 ---
        pic = ""
        # background-image 优先 (站点用 CSS 背景图)
        for m in re.finditer(r'background-image\s*:\s*url\([\'"]?([^\'")]+)[\'"]?\)', html):
            src = m.group(1)
            if "s3plus" in src or "logo" in src.lower() or "favicon" in src.lower():
                continue
            pic = src
            break
        if not pic:
            for m in re.finditer(r'(?:data-src|src)="([^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I):
                src = m.group(1)
                if any(bad in src.lower() for bad in ["s3plus", "favicon", "logo", "icon", "loading", "img-bj"]):
                    continue
                pic = src
                break
        vod["vod_pic"] = self._img_src(pic)

        # --- 元信息: 类型/地区/年份/导演/演员 ---
        # hqvod 详情页用特殊结构:
        #   this-desc-info: <span>2026</span><span>大陆</span><span>第22集</span>
        #   this-desc-tags: <span>国产</span>
        vod_year = ""
        vod_area = ""
        # 从 this-desc-info 提取
        info_m = re.search(r'class="this-desc-info"[^>]*>(.*?)</div>', html, re.S)
        if info_m:
            spans = re.findall(r'<span[^>]*>([^<]+)</span>', info_m.group(1))
            for s in spans:
                s = self._clean(s)
                if not s:
                    continue
                if re.match(r'^\d{4}$', s) and not vod_year:
                    vod_year = s
                elif s in self.AREA_FILTERS and not vod_area:
                    vod_area = s
        # 从 this-desc-tags 提取类型
        class_names = []
        tags_m = re.search(r'class="this-desc-tags"[^>]*>(.*?)</div>', html, re.S)
        if tags_m:
            spans = re.findall(r'<span[^>]*>([^<]+)</span>', tags_m.group(1))
            class_names = [self._clean(s) for s in spans if self._clean(s)]
        # 兜底: 尝试 MacCMS /s/class/xxx.html 链接
        if not class_names:
            for m in re.finditer(r'href="(/s/class/[^"]+\.html)"[^>]*>([^<]+)</a>', html):
                t = self._clean(m.group(2))
                if t and t not in class_names:
                    class_names.append(t)

        real_classes = [c for c in class_names if c not in self._MAIN_TYPES]
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_type"] = real_classes[0] if real_classes else (class_names[0] if class_names else "")
        if len(class_names) > 1:
            vod["vod_class"] = ",".join(class_names)

        # 导演 / 演员
        vod["vod_director"] = self._detail_field(html, "导演")
        vod["vod_actor"] = self._detail_field(html, "演员")

        # 备注
        vod["vod_remarks"] = self._detail_remarks(html)

        # --- 简介 ---
        desc = ""
        dm_desc = re.search(r'id="height_limit"[^>]*>(.*?)</div>', html, re.S)
        if dm_desc:
            desc = re.sub(r"<br\s*/?>", "\n", dm_desc.group(1))
            desc = re.sub(r"<[^>]+>", "", desc)
            desc = self._clean(desc)
            # 去掉开头的 "描述:" 标签
            if desc.startswith("描述"):
                desc = re.sub(r"^描述[:：]?\s*", "", desc)
        if not desc:
            dm_desc2 = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
            if dm_desc2:
                desc = self._clean(dm_desc2.group(1))
        wx = self._get_wechat_info()
        if wx:
            vod["vod_content"] = wx + ("\n\n" + desc if desc else "")
        else:
            vod["vod_content"] = desc

        # --- 播放源 + 选集 ---
        from_arr, url_arr = self._detail_plays(html, vid, opener)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            vod["vod_play_from"] = "星辰4K"
            vod["vod_play_url"] = f"播放${self.BASE_URL}/bofang/{vid}-1-1.html"

        result["list"] = [vod]
        return result

    def _detail_field(self, html, label):
        """从详情页提取 'label: 值' 格式的字段 (hqvod 结构: <strong>label:</strong><a>值</a>)"""
        # 优先匹配 hqvod 特殊格式: <strong class="r6">导演:</strong><a...>值</a>
        pat1 = (r'<strong[^>]*>\s*' + re.escape(label) + r'\s*[:：]\s*</strong>(.*?)(?=<strong|<div[^>]*class="this-info|</div>)')
        m = re.search(pat1, html, re.S)
        if m:
            content = m.group(1)
            names = re.findall(r'>([^<>]+)</a>', content)
            if names:
                return ",".join(self._clean(n) for n in names if self._clean(n))
            text = self._clean(content)
            if text:
                text = re.sub(r'[，,]\s*$', '', text)
                return text
        # 兜底: 通用 label: 值 格式
        pat2 = label + r'[:：]\s*((?:<a[^>]*>[^<]+</a>[，,]?\s*)+)'
        m2 = re.search(pat2, html, re.S)
        if m2:
            names = re.findall(r'>([^<>]+)</a>', m2.group(1))
            if names:
                return ",".join(self._clean(n) for n in names if self._clean(n))
        pat3 = label + r'[:：]\s*([^<，,]{1,200})'
        m3 = re.search(pat3, html)
        if m3:
            return self._clean(m3.group(1))
        return ""

    def _detail_remarks(self, html):
        for m in re.finditer(r'<span[^>]*class="[^"]*remarks[^"]*"[^>]*>([^<]+)</span>', html):
            t = self._clean(m.group(1))
            if t:
                return t
        for m in re.finditer(r'更新[:：]\s*([^<]+)', html):
            t = self._clean(m.group(1))
            if t:
                return t
        return ""

    def _detail_plays(self, html, vid, opener):
        """解析详情页的线路名 + 选集列表"""
        # 1. 提取线路 tab 名 (anthology-tab > swiper-slide)
        tab_names = []
        tab_area = re.search(
            r'<div[^>]*class="anthology-tab[^"]*"[^>]*>(.*?)<div[^>]*class="anthology-list',
            html, re.S)
        if tab_area:
            for m in re.finditer(r'<a[^>]*class="swiper-slide"[^>]*>(.*?)</a>', tab_area.group(1), re.S):
                name = re.sub(r'<[^>]+>', '', m.group(1))
                name = html_mod.unescape(name).replace("&nbsp;", " ").strip()
                # 去掉尾部集数徽章 (如 "21", "41")
                name = re.sub(r'\d+$', '', name).strip()
                # 清理特殊符号
                name = re.sub(r'[\u2460-\u24FF]', '', name).strip()
                if name:
                    tab_names.append(name)

        # 2. 提取选集块 (anthology-list-play)
        # 每个块包含某一线路的所有选集链接
        blocks = re.split(r'(?=<ul[^>]*class="anthology-list-play)', html)
        play_blocks = []
        for b in blocks[1:]:
            # 截断到下一个大块
            b_truncated = b.split('<div class="box-width', 1)[0]
            eps = re.findall(
                r'href="(/bofang/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>',
                b_truncated)
            if eps:
                play_blocks.append(eps)

        if not play_blocks:
            # 兜底: 直接抓所有 /bofang/ 链接作为单线路
            eps = re.findall(r'href="(/bofang/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>', html)
            if not eps:
                return [], []
            lines = []
            for href, v, s, n, ep_name in eps:
                ep_name = self._clean(ep_name) or f"第{n}集"
                lines.append(f"{ep_name}${self.BASE_URL}{href}")
            return ["默认"], ["#".join(lines)]

        # 3. 线路名 ↔ 选集块 对应
        from_arr, url_arr = [], []
        n = max(len(tab_names), len(play_blocks))
        used_names = {}
        for i in range(n):
            label = tab_names[i] if i < len(tab_names) else f"线路{i+1}"
            eps = play_blocks[i] if i < len(play_blocks) else []
            if not eps:
                continue
            if label in used_names:
                used_names[label] += 1
                label = f"{label}{used_names[label]}"
            else:
                used_names[label] = 1
            lines = []
            for href, v, s, nid, ep_name in eps:
                ep_name = self._clean(ep_name) or f"第{nid}集"
                lines.append(f"{ep_name}${self.BASE_URL}{href}")
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = str(id)
        # 清理 "名称$url" 格式
        if "$" in play_url and not play_url.startswith("http"):
            parts = play_url.split("$", 1)
            if len(parts) == 2:
                play_url = parts[1]

        if not play_url.startswith("http"):
            play_url = self._absurl(play_url)

        headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
        }

        # 优先: 尝试访问播放页提取 player_aaaa.url 构建外部解析器
        try:
            opener = self._build_opener()
            # 先访问详情页建立 cookie
            vid_m = re.search(r'/bofang/(\d+)-', play_url)
            if vid_m:
                self._http_get(self.BASE_URL + f"/xiangqing/{vid_m.group(1)}.html", opener=opener)

            html, _ = self._http_get(play_url, opener=opener)
            if html and len(html) > 5000:
                # 提取 player_aaaa JSON
                idx = html.find('player_aaaa')
                if idx > 0:
                    brace_idx = html.find('{', idx)
                    if brace_idx > 0:
                        decoder = json.JSONDecoder()
                        data, _ = decoder.raw_decode(html[brace_idx:].replace("\\/", "/"))
                        token = data.get("url", "")
                        from_val = data.get("from", "")
                        if token and not token.startswith("http"):
                            # 构建外部解析器 URL
                            # 所有线路都用这个外部解析器
                            external_url = (
                                f"https://xn--2p1a.bfapi.cyou/player/"
                                f"?url={urllib.parse.quote(token)}"
                            )
                            return {
                                "url": external_url,
                                "parse": 1,
                                "header": json.dumps(headers),
                                "playUrl": "",
                                "subtitle": "",
                            }
        except Exception:
            pass

        # Fallback: 直接返回播放页 URL + parse=1 让 TVBox WebView 自动处理
        return {
            "url": play_url,
            "parse": 1,
            "header": json.dumps(headers),
            "playUrl": "",
            "subtitle": "",
        }

    # ==================== TVBox 规范 ====================
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

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]
