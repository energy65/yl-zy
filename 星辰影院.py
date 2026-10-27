# -*- coding: utf-8 -*-
"""
目标站: 星辰影院 (xcyycn)
站点地址: https://www.xcyycn.cc  (备用 https://www.xcyycn.tv)
站点类型: 综合影视 (电影 / 电视剧 / 综艺 / 动漫 / 短剧)
模板结构: MacCMS shoutu46 模板
    /v/{tid}.html                     频道页 (56条/页)
    /v/{tid}/page/{n}.html            频道分页
    /s/{field}/{value}.html           筛选页 (field: class=类型 / 未知=地区 / year=年份)
    /s/{f1}/{v1}/{f2}/{v2}.html       组合筛选 (不同字段可叠加)
    /s/{f}/{v}/page/{n}.html          筛选分页
    /s.html?wd={关键词}&page={n}      搜索
    /d-{id}.html                      详情页
    /p/{id}-{sid}-{nid}.html          播放页 (var player_aaaa JSON, encrypt=0 明文直链)

功能 (写法参考 网飞猫.py):
    - homeContent: 一级分类 + 每类二级筛选 (类型/地区/年份)
    - 类型已细化: 电影(科幻片/战争片/爱情片/恐怖片/犯罪/悬疑...),
      电视剧(古装/都市/历史/谍战/武侠/家庭...), 综艺/动漫/短剧 同理
    - 筛选值均经站点 /s/class/{X}.html 实测验证, 组合筛选与分页可用
    - categoryContent: 无筛选走 /v/{tid}/page/{n}.html, 有筛选走 /s/ 组合筛选
    - searchContent / detailContent / playerContent
    - 播放页 player_aaaa.url 为明文 m3u8 直链, parse=0 交给 TVBox 直接播放
    - 影片简介处添加 微信公众号 "源力软件汇" (XOR 加密存储, 运行时解密)
"""
import re
import sys
import json
import time
import ssl
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

    # 镜像域名 (按顺序尝试, 失败自动切换)
    DOMAINS = [
        "https://www.xcyycn.cc",
        "https://www.xcyycn.tv",
    ]

    DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    # ==================== 微信推广文案 (XOR 加密存储) ====================
    _W_KEY = 'xingchen_wechat_2026'
    # '微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力'
    _W_FULL_DATA = [24534, 20360, 20738, 20336, 21396, 74, 28405, 21237, 36656, 20097,
                    27682, 65, 65380, 16, 32720, 110, 2, 5, 6, 3,
                    65, 91, 95, 82, 81, 20316, 38634, 26266, 22853, 20335,
                    36173, 36135, 28408, 23644, 22364, 28367, 21161]
    # '源力影视·微信公众号源力软件汇'
    _W_LINE_DATA = [28392, 21234, 24351, 35233, 212, 24518, 20356, 20738, 20296, 21376,
                    28405, 21240, 36615, 20119, 27699]

    def _w_decrypt(self, data):
        key = self._W_KEY
        try:
            return "".join(chr(v ^ ord(key[i % len(key)])) for i, v in enumerate(data))
        except Exception:
            return ""

    def _get_wechat_info(self):
        """返回完整推广文案 (运行时解密)"""
        full = self._w_decrypt(self._W_FULL_DATA)
        if not full:
            return ""
        return full

    # ==================== 一级分类 (与站点导航一致) ====================
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "5", "type_name": "短剧"},
    ]

    # ==================== 类型筛选 (站点 /s/class/{X}.html 实测有效值) ====================
    CLASS_FILTERS = {
        "1": ["科幻片", "战争片", "爱情片", "恐怖片", "纪录片", "剧情片", "动作片",
              "喜剧片", "动画片", "犯罪", "悬疑", "惊悚", "奇幻", "冒险", "西部",
              "文艺", "同性"],
        "2": ["国产剧", "港剧", "韩剧", "泰剧", "欧美剧", "古装", "都市", "历史",
              "谍战", "武侠", "言情", "家庭", "穿越", "甜虐爱情", "同性"],
        "3": ["大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "真人秀", "访谈",
              "音乐", "脱口秀", "晚会"],
        "4": ["国产动漫", "日韩动漫", "欧美动漫", "动画电影", "古装", "奇幻",
              "科幻", "冒险", "热血"],
        "5": ["女频恋爱", "反转爽剧", "现代都市", "年代穿越", "古装仙侠", "男频"],
    }

    # 地区 (站点 /s/未知/{X}.html, 与站内条目链接格式一致)
    AREA_FILTERS = ["大陆", "香港", "台湾", "美国", "英国", "法国", "德国",
                    "日本", "韩国", "泰国", "印度", "意大利", "西班牙",
                    "加拿大", "其它"]

    # 年份 (站点 /s/year/{X}.html)
    YEAR_FILTERS = ["2026", "2025", "2024", "2023", "2022", "2021", "2020",
                    "2019", "2018", "2017", "2016", "2015", "2014", "2013",
                    "2012", "2011", "2010", "2008", "2005", "2000"]

    # 详情页里代表主分类的 class 值 (提取影片类型时跳过)
    _MAIN_TYPE_NAMES = ("电影", "电视剧", "综艺", "动漫", "短剧")

    # ==================== 初始化 ====================
    def init(self, extend=""):
        self.host = self.DOMAINS[0]
        self._detect_host()

    def getName(self):
        return "星辰影院"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return [200, "text/plain", ""]

    # ==================== 域名探测 / HTTP ====================
    def _detect_host(self):
        """探测可用域名"""
        for domain in self.DOMAINS:
            html = self._fetch(domain + "/", timeout=15)
            if html and len(html) > 5000 and "<title>" in html:
                self.host = domain
                return True
        self.host = self.DOMAINS[0]
        return False

    def _switch_host(self):
        try:
            idx = self.DOMAINS.index(self.host)
        except ValueError:
            idx = 0
        self.host = self.DOMAINS[(idx + 1) % len(self.DOMAINS)]
        return self.host

    def _fetch(self, url, referer=None, timeout=20):
        """底层 HTTP GET, 返回解码后的文本"""
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
                data = resp.read()
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
            except Exception:
                data = b""
        except Exception:
            return ""
        if not data:
            return ""
        for enc in ("utf-8", "gbk", "gb2312"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _get(self, path, referer=None):
        """统一 GET, 自动故障切换域名"""
        if referer is None:
            referer = self.host + "/"
        url = path if path.startswith("http") else self.host + path
        for _ in range(len(self.DOMAINS) + 1):
            html = self._fetch(url, referer=referer)
            if html and "<title>" in html:
                return html
            self._switch_host()
            url = path if path.startswith("http") else self.host + path
            referer = self.host + "/"
        return ""

    # ==================== 工具方法 ====================
    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = text.replace("\u200b", "").replace("\ufeff", "")
        return re.sub(r"\s+", " ", text).strip()

    def _img_src(self, url):
        if not url:
            return ""
        if url.endswith(".ico"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    # ==================== 卡片解析 ====================
    def _parse_vitems(self, html):
        """解析频道/首页视频卡片 (public-list-box public-pic-b 结构)"""
        items = []
        seen = set()
        blocks = re.split(r'(?=<div class="public-list-box public-pic-b)', html)
        for b in blocks[1:]:
            # 只取卡片自身区块 (到下一个 public-list-button 之前的部分包含全部字段)
            m = re.search(
                r'class="public-list-exp"\s+href="(/d-(\d+)\.html)"\s+title="([^"]*)"', b)
            if not m:
                continue
            vid = m.group(2)
            if vid in seen:
                continue
            name = self.clean(m.group(3))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-src="([^"]+)"', b[:m.start() + 1500])
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            rm = re.search(r'<span class="public-list-prb[^"]*">([^<]*)</span>', b)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_sitems(self, html):
        """解析筛选/搜索结果卡片 (public-list-box search-box 结构)"""
        items = []
        seen = set()
        blocks = re.split(r'(?=<div class="public-list-box search-box)', html)
        for b in blocks[1:]:
            m = re.search(r'class="public-list-exp"\s+href="(/d-(\d+)\.html)"', b)
            if not m:
                continue
            vid = m.group(2)
            if vid in seen:
                continue
            name = ""
            nm = re.search(r'class="thumb-txt[^"]*">([^<]*)</div>', b)
            if nm:
                name = self.clean(nm.group(1))
            if not name:
                tm = re.search(r'title="([^"]+)"', b[:m.start() + 1500])
                if tm:
                    name = self.clean(tm.group(1))
            if not name:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-src="([^"]+)"', b[:m.start() + 2000])
            if pm:
                pic = self._img_src(pm.group(1))
            remark = ""
            rm = re.search(r'<span class="public-list-prb[^"]*">([^<]*)</span>', b)
            if rm:
                remark = self.clean(rm.group(1))
            if not remark:
                ym = re.search(r'href="/s/year/[^"]+"[^>]*>([^<]+)</a>', b)
                if ym:
                    remark = self.clean(ym.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic if pic else self.DEFAULT_PIC,
                "vod_remarks": remark,
            })
        return items

    def _parse_pagecount(self, html, page):
        """从分页链接中提取最大页码, 无分页链接时启发式判断"""
        nums = []
        for m in re.finditer(r'href="[^"]*/page/(\d+)\.html"', html):
            try:
                nums.append(int(m.group(1)))
            except Exception:
                continue
        if nums:
            return max(nums)
        return page + 1

    # ==================== 筛选器 ====================
    def _build_filters(self, tid):
        """构建某分类的全部二级筛选"""
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

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """首页: 一级分类 + 各分类全部二级筛选 + 推荐视频"""
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
            if not html:
                return result
            result["list"] = self._parse_vitems(html)
        except Exception:
            pass
        return result

    # ==================== 分类 ====================
    def _apply_filters(self, extend):
        """从 extend 提取有效筛选值, 过滤 '全部'/空值; 返回有序 [(field, value)]"""
        if not isinstance(extend, dict):
            return []
        pairs = []
        # 顺序: 类型 -> 地区 -> 年份
        class_v = str(extend.get("class") or "").strip()
        if class_v and class_v != "全部":
            pairs.append(("class", class_v))
        area_v = str(extend.get("area") or "").strip()
        if area_v and area_v != "全部":
            # 地区字段名为 "未知" (与站内条目链接 /s/未知/{area}.html 格式一致)
            pairs.append(("未知", area_v))
        year_v = str(extend.get("year") or "").strip()
        if year_v and year_v != "全部":
            pairs.append(("year", year_v))
        return pairs

    def _build_s_path(self, pairs, pg):
        """构建 /s/ 筛选路径: /s/{f1}/{v1}/{f2}/{v2}[/page/{n}].html"""
        segs = []
        for field, value in pairs:
            segs.append(urllib.parse.quote(self.clean(field)))
            segs.append(urllib.parse.quote(self.clean(value)))
        if pg > 1:
            segs.extend(["page", str(pg)])
        return "/s/" + "/".join(segs) + ".html"

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = str(tid)
        # 兼容部分 TVBox 把筛选放在 filter 参数中的情况
        if not isinstance(extend, dict):
            extend = filter if isinstance(filter, dict) else {}
        result = {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            pairs = self._apply_filters(extend)
            if pairs:
                path = self._build_s_path(pairs, page)
                html = self._get(path)
                if not html:
                    return result
                videos = self._parse_sitems(html)
                result["list"] = videos
                result["limit"] = len(videos)
                result["total"] = len(videos)
                result["pagecount"] = self._parse_pagecount(html, page)
            else:
                path = "/v/%s.html" % tid
                if page > 1:
                    path = "/v/%s/page/%d.html" % (tid, page)
                html = self._get(path)
                if not html:
                    return result
                videos = self._parse_vitems(html)
                result["list"] = videos
                result["limit"] = len(videos)
                result["total"] = len(videos)
                # 频道页分页链接由 JS 渲染, 启发式: 有数据则还有下一页
                if videos:
                    result["pagecount"] = page + 1
                else:
                    result["pagecount"] = page
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
            params = {"wd": key}
            if page > 1:
                params["page"] = str(page)
            path = "/s.html?" + urllib.parse.urlencode(params)
            html = self._get(path, referer=self.host + "/")
            if not html:
                return result
            videos = self._parse_sitems(html)
            result["list"] = videos
            result["limit"] = len(videos)
            result["total"] = len(videos)
            if videos:
                result["pagecount"] = self._parse_pagecount(html, page)
            else:
                result["pagecount"] = page
        except Exception:
            pass
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip()
        # 容错: 允许传入 /d-xxx.html 或完整 URL
        dm = re.search(r'/d-(\d+)\.html', vid)
        if dm:
            vid = dm.group(1)
        if not vid.isdigit():
            return result

        html = self._get("/d-%s.html" % vid)
        if not html or len(html) < 2000:
            return result

        vod = {"vod_id": vid}

        # 标题
        name = self._detail_name(html)
        vod["vod_name"] = name if name else vid

        # 封面
        vod["vod_pic"] = self._detail_pic(html)

        # 信息标签: 年份 / 地区 / 类型
        tags = re.findall(r'href="(/s/(?:class|year|未知)/[^"]+\.html)"[^>]*>([^<]+)</a>', html)
        vod_year, vod_area = "", ""
        class_names = []
        for href, text in tags:
            t = self.clean(text)
            if not t:
                continue
            if "/s/year/" in href:
                if not vod_year:
                    vod_year = t
            elif "/s/未知/" in href:
                if not vod_area:
                    vod_area = t
            elif "/s/class/" in href:
                if t not in class_names:
                    class_names.append(t)
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        real_classes = [c for c in class_names if c not in self._MAIN_TYPE_NAMES]
        vod["vod_type"] = real_classes[0] if real_classes else (class_names[0] if class_names else "")
        if len(class_names) > 1:
            vod["vod_class"] = ",".join(class_names)

        # 备注 (更新至xx集 / HD中字 等)
        vod["vod_remarks"] = self._detail_remarks(html)

        # 导演 / 演员
        vod["vod_director"] = self._detail_field(html, "导演")
        vod["vod_actor"] = self._detail_field(html, "演员")

        # 简介 + 推广文案 (置于最前)
        desc = self._detail_desc(html)
        wx = self._get_wechat_info()
        if wx:
            vod["vod_content"] = wx + ("\n\n" + desc if desc else "")
        else:
            vod["vod_content"] = desc

        # 播放源 + 选集
        from_arr, url_arr = self._detail_plays(html)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            vod["vod_play_from"] = "星辰影院"
            vod["vod_play_url"] = "播放$%s/p/%s-1-1.html" % (self.host, vid)

        result["list"] = [vod]
        return result

    def _detail_name(self, html):
        m = re.search(r'<h3 class="slide-info-title[^"]*">([^<]*)</h3>', html)
        if m:
            t = self.clean(m.group(1))
            if t:
                return t
        m = re.search(r'<div class="slide-info-title[^"]*">([^<]*)</div>', html)
        if m:
            t = self.clean(m.group(1))
            if t:
                return t
        m = re.search(r'<title>([^<]*)</title>', html)
        if m:
            t = self.clean(m.group(1))
            t = re.sub(r'《([^》]+)》.*', r'\1', t)
            t = re.sub(r'[-_|].*$', "", t)
            t = self.clean(t)
            if t:
                return t
        return ""

    def _detail_pic(self, html):
        m = re.search(r'<div class="detail-pic">(.*?)</div>', html, re.S)
        scope = m.group(1) if m else html[:6000]
        for attr in ("data-src", "src"):
            im = re.search(r'%s="([^"]+)"' % attr, scope)
            if im:
                s = self._img_src(im.group(1))
                if s and "img-bj-k" not in s:
                    return s
        im = re.search(r'data-src="([^"]+)"', html)
        if im:
            s = self._img_src(im.group(1))
            if s and "img-bj-k" not in s:
                return s
        return self.DEFAULT_PIC

    def _detail_remarks(self, html):
        # 第一个不含 <a> 的 slide-info-remarks 即影片备注
        for m in re.finditer(r'<span class="slide-info-remarks">([^<]*)</span>', html):
            t = self.clean(m.group(1))
            if t:
                return t
        return ""

    def _detail_field(self, html, label):
        m = re.search(
            r'<strong class="cor6 r6">\s*%s\s*[:：]</strong>(.*?)</div>' % label,
            html, re.S)
        if not m:
            return ""
        names = [self.clean(t) for t in re.findall(r'>([^<>]+)</a>', m.group(1))]
        names = [n for n in names if n]
        return ",".join(names)

    def _detail_desc(self, html):
        m = re.search(r'id="height_limit"[^>]*>(.*?)</div>', html, re.S)
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

    def _detail_plays(self, html):
        """解析线路标签与选集列表, 一一对应

        线路名在 anthology-tab 的 swiper-slide 中 (可能带集数后缀, 需去掉),
        选集块为 anthology-list-box (下载块无 /p/ 链接, 自动排除)。
        """
        # 线路名
        tab_area = re.search(
            r'<div class="anthology-tab[^"]*">(.*?)<div class="anthology-list', html, re.S)
        tab_names = []
        if tab_area:
            for t in re.findall(r'<a class="swiper-slide">(.*?)</a>', tab_area.group(1), re.S):
                name = re.sub(r'<[^>]+>', '', t)
                name = self.clean(name.replace("&nbsp;", " "))
                name = re.sub(r'\d+$', '', name).strip()
                if name:
                    tab_names.append(name)

        # 选集块 (只保留含 /p/ 播放链接的块, 排除下载块)
        blocks = re.split(r'(?=<div class=["\']anthology-list-box)', html)
        play_blocks = []
        for b in blocks[1:]:
            b = b.split('<div class="box-width', 1)[0]
            eps = re.findall(r'href="(/p/\d+-\d+-\d+\.html)"[^>]*>([^<]*)</a>', b)
            if eps:
                play_blocks.append(eps)

        if not play_blocks:
            # 兜底: 直接抓全部 /p/ 链接作为单线路
            eps = re.findall(r'href="(/p/\d+-\d+-\d+\.html)"[^>]*>([^<]*)</a>', html)
            if not eps:
                return [], []
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_path))
            return ["星辰影院"], ["#".join(lines)]

        from_arr, url_arr = [], []
        used = {}
        n = max(len(tab_names), len(play_blocks))
        for i in range(n):
            label = tab_names[i] if i < len(tab_names) else "线路%d" % (i + 1)
            eps = play_blocks[i] if i < len(play_blocks) else []
            if not eps:
                continue
            # 处理重名线路
            if label in used:
                used[label] += 1
                label = "%s%d" % (label, used[label])
            else:
                used[label] = 1
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name) or "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_path))
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
        """从播放页提取真实 m3u8/mp4 地址 (player_aaaa JSON, encrypt=0)"""
        if not html:
            return ""
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            try:
                j = json.loads(m.group(1))
                url = str(j.get("url", "")).replace("\\/", "/").strip()
                if url.startswith("//"):
                    url = "https:" + url
                if url.startswith("http"):
                    return url
            except Exception:
                pass
        # 兜底: 正则直搜
        patterns = [
            r'(https?://[^\s"\']+?\.m3u8[^\s"\']*)',
            r'(https?://[^\s"\']+?\.mp4[^\s"\']*)',
        ]
        for p in patterns:
            m = re.search(p, html)
            if m:
                return m.group(1)
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
