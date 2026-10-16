# -*- coding: utf-8 -*-
"""
星辰影院 TVBox Python Spider
网站地址: https://www.xcyycn.cc
站点系统: maccms (苹果CMS / 模板 shoutu46), HTML 站点, 无签名 API
实现方式: 标准库 urllib 直接抓取 HTML, 正则解析, 兼容任意 TVBox/影视仓 T4 壳

分类体系 (实测 2026-10):
  一级分类 (type_id): 1 电影 / 2 电视剧 / 3 综艺 / 4 动漫 / 5 短剧
  二级筛选:
    类型 class  每个一级分类不同 (动作片/国产剧/... / 女频恋爱...)
    地区 area   大陆/香港/台湾/美国/日本/韩国/... /其它
    语言 lang   国语/粤语/闽南语/英语/韩语/日语/法语/德语/其它
    年份 year   2026..2000 (短剧 2026..2021)
    排序 sort   按最新 time / 按最热 hits / 按评分 score
分类 URL 格式 (12 段, 11 个连字符, 空段留空):
  /vs/{type}-{area}-{sort}-{class}-{lang}-{letter}-{f6}-{page}-{f8}-{f9}-{f10}-{year}.html
  示例: /vs/1-----------.html            全部电影第 1 页
        /vs/1---动作片--------.html        动作片第 1 页
        /vs/1-大陆--爱情片--------.html    大陆爱情片第 1 页
        /vs/1---动作片--------2026.html    2026 年动作片第 1 页
        /vs/1---动作片-----2---.html       动作片第 2 页 (page 在第 8 段)

详情: /d-{id}.html
  播放源标签: .anthology-tab a.swiper-slide 文本
  剧集列表:   .anthology-list-play 内的 /p/{id}-{源}-{集}.html 链接
播放: /p/{id}-{源}-{集}.html 页面内含
  var player_aaaa = {"encrypt":0,"url":"https://.../index.m3u8",...}
  取 url 即为 m3u8 直链 (实测全部 encrypt=0, 可 parse=0 直出)

搜索: 第 1 页 /s.html?wd={关键词}; 第 N 页 /s{关键词}/page/{N}.html
      总页数取自 "共N条数据,当前M/K页"

影片简介处附加微信公众号「源力软件汇」。
支持: 首页推荐, 一/二级分类(类型/地区/语言/年份/排序), 分类翻页, 搜索, 详情, 播放。
"""

import re
import ssl
import json
import time
import urllib.request
import urllib.parse
import html as html_mod

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""):
            pass

        def getName(self):
            return ""


class Spider(BaseSpider):

    # ==================== 站点常量 ====================

    site_url = "https://www.xcyycn.cc"
    default_pic = "https://pic.rmb.bdstatic.com/bjh/user/default.png"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
    }

    # 推广文案 (置于简介最前, 避免被截断)
    promo_text = (
        "更多优质资源尽在源力\n"
        "微信公众号：源力软件汇\n"
        "QQ群：1054592152\n\n"
    )

    # ==================== 分类配置 ====================

    # 一级分类 (与站点导航一致)
    categories = [
        ("1", "电影"),
        ("2", "电视剧"),
        ("3", "综艺"),
        ("4", "动漫"),
        ("5", "短剧"),
    ]

    # 二级筛选: 类型 (按一级分类区分)
    class_options = {
        "1": [
            "动作片", "喜剧片", "科幻片", "恐怖片", "爱情片", "剧情片", "战争片",
            "记录片", "动画片", "惊悚", "犯罪", "悬疑", "冒险", "奇幻", "家庭",
            "历史", "传记", "古装", "音乐", "同性", "运动", "武侠", "短片",
            "歌舞", "西部", "儿童", "灾难", "戏曲", "真人秀", "青春",
        ],
        "2": [
            "国产剧", "欧美剧", "香港剧", "韩国剧", "台湾剧", "日本剧", "海外剧",
            "泰国剧", "剧情", "爱情", "喜剧", "悬疑", "犯罪", "古装", "动作",
            "奇幻", "惊悚", "家庭", "历史", "科幻", "战争", "同性", "武侠",
            "冒险", "恐怖", "纪录", "传记", "短片", "运动", "音乐", "儿童",
            "歌舞", "西部", "灾难",
        ],
        "3": [
            "大陆综艺", "港台综艺", "日韩综艺", "欧美综艺", "真人秀", "纪录片",
            "脱口秀", "音乐", "歌舞", "相声", "喜剧", "爱情", "历史", "运动",
            "冒险", "剧情", "访谈", "旅游", "悬疑", "家庭", "短片", "同性",
            "动作", "儿童", "惊悚", "美食",
        ],
        "4": [
            "国产动漫", "日韩动漫", "欧美动漫", "港台动漫", "海外动漫", "动画",
            "喜剧", "剧情", "奇幻", "冒险", "动作", "科幻", "爱情", "儿童",
            "家庭", "短片", "悬疑", "运动", "古装", "武侠", "音乐", "犯罪",
            "惊悚", "战争", "恐怖", "历史", "搞笑", "歌舞", "热血",
        ],
        "5": [
            "女频恋爱", "反转爽剧", "古装仙侠", "年代穿越", "脑洞悬疑", "现代都市",
        ],
    }

    # 二级筛选: 地区 (短剧无地区)
    area_options = [
        "大陆", "香港", "台湾", "美国", "日本", "韩国", "英国", "法国", "德国",
        "意大利", "西班牙", "俄罗斯", "加拿大", "印度", "泰国", "其它", "新加坡",
        "菲律宾", "澳大利亚", "土耳其", "瑞典", "巴西", "荷兰", "印度尼西亚",
        "挪威", "智利", "爱尔兰", "伊朗", "蒙古",
    ]

    # 二级筛选: 语言 (短剧无语言)
    lang_options = [
        "国语", "粤语", "闽南语", "英语", "韩语", "日语", "法语", "德语", "其它",
    ]

    # 二级筛选: 排序
    sort_options = [
        ("按最新", "time"),
        ("按最热", "hits"),
        ("按评分", "score"),
    ]

    # 二级筛选: 年份 (短剧仅近 6 年)
    year_options = [str(y) for y in range(2026, 1999, -1)]
    year_options_short = [str(y) for y in range(2026, 2020, -1)]

    # ==================== 初始化 ====================

    def init(self, extend=""):
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

        # 简称 -> 一级分类 id 映射 (兼容壳端传中文 type_name)
        self._name_to_tid = dict((name, tid) for tid, name in self.categories)

        # 静态 class / filters 结构 (纯本地构建, 不请求网络, 保证分类栏秒开)
        self._class_list = [
            {"type_id": tid, "type_name": name} for tid, name in self.categories
        ]
        self._filters_map = self._build_filters()

        # 简单内存缓存: 详情页抓取结果, 降低重复请求
        self._cache = {}
        self._cache_ttl = 600

    def getName(self):
        return "星辰影院"

    def _build_filters(self):
        """按一级分类构建 TVBox 标准二级筛选定义"""
        filters = {}
        for tid, _name in self.categories:
            groups = []

            cls = self.class_options.get(tid, [])
            if cls:
                groups.append({
                    "key": "class",
                    "name": "类型",
                    "value": [{"n": "全部", "v": ""}] + [{"n": c, "v": c} for c in cls],
                })

            if tid != "5":
                groups.append({
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.area_options],
                })

            years = self.year_options_short if tid == "5" else self.year_options
            groups.append({
                "key": "year",
                "name": "年份",
                "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in years],
            })

            if tid != "5":
                groups.append({
                    "key": "lang",
                    "name": "语言",
                    "value": [{"n": "全部", "v": ""}] + [{"n": l, "v": l} for l in self.lang_options],
                })

            groups.append({
                "key": "sort",
                "name": "排序",
                "value": [{"n": n, "v": v} for n, v in self.sort_options],
            })

            filters[tid] = groups
        return filters

    # ==================== 基础请求 ====================

    def getHtml(self, url, referer=None, retry=2):
        """抓取页面 HTML, 自动尝试多种编码解码"""
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        for _ in range(max(1, retry)):
            try:
                req = urllib.request.Request(url, headers=headers)
                resp = urllib.request.urlopen(req, timeout=20, context=self._ssl_ctx)
                raw = resp.read()
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        return raw.decode(enc)
                    except Exception:
                        continue
                return raw.decode("utf-8", "replace")
            except Exception:
                time.sleep(0.3)
                continue
        return ""

    def clean(self, text):
        """去除标签/实体/多余空白"""
        if not text:
            return ""
        text = str(text)
        text = text.replace("&nbsp;", " ").replace("&#183;", "\u00b7")
        text = html_mod.unescape(text)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("\xa0", " ").replace("\u3000", " ")
        return re.sub(r"\s+", " ", text).strip()

    def absurl(self, u):
        if not u:
            return ""
        u = u.strip()
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("//"):
            return "https:" + u
        return self.site_url + ("" if u.startswith("/") else "/") + u

    # ==================== 列表解析 ====================

    def _parse_list(self, text):
        """解析首页/分类/搜索页视频卡片 (.public-list-exp)

        标题优先取 a[title], 其次取 img[alt] (去掉 "封面图" 后缀);
        封面取 data-src; 备注取 .public-list-prb
        """
        items = []
        seen = set()
        if not text:
            return items

        pat = re.compile(r'<a\b([^>]*?)href="/d-(\d+)\.html"([^>]*)>(.*?)</a>', re.S)
        for m in pat.finditer(text):
            attrs = m.group(1) + " " + m.group(3)
            if "public-list-exp" not in attrs:
                continue
            vid = m.group(2)
            if vid in seen:
                continue
            inner = m.group(4)

            title = ""
            tm = re.search(r'title="([^"]*)"', attrs)
            if tm:
                title = self.clean(tm.group(1))
            if not title:
                am = re.search(r'alt="([^"]*)"', inner)
                if am:
                    title = re.sub(r"封面图$", "", self.clean(am.group(1))).strip()
            if not title:
                continue

            seen.add(vid)

            pic = ""
            pm = re.search(r'data-src="([^"]*)"', inner)
            if pm:
                pic = self.absurl(pm.group(1))
            if not pic:
                pm2 = re.search(r'src="([^"]*)"', inner)
                if pm2 and "img-bj" not in pm2.group(1):
                    pic = self.absurl(pm2.group(1))
            if not pic:
                pic = self.default_pic

            remark = ""
            rm = re.search(r'class="public-list-prb[^"]*"[^>]*>([^<]+)<', inner)
            if rm:
                remark = self.clean(rm.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    # ==================== 首页 ====================

    def homeContent(self, filter):
        """返回一级分类与二级筛选 (纯静态, 不请求网络)"""
        return {
            "class": [dict(c) for c in self._class_list],
            "list": [],
            "filters": self._filters_map,
        }

    def homeVideoContent(self):
        """首页推荐 (抓取首页各板块 /d- 卡片)"""
        html = self.getHtml(self.site_url + "/")
        return {"list": self._parse_list(html)}

    # ==================== 分类 ====================

    def _build_vs_path(self, tid, area, sort, cls, lang, year, page):
        """构建分类 /vs/ 路径 (12 段)"""
        def q(s):
            s = (s or "").strip()
            return urllib.parse.quote(s) if s else ""

        page_s = str(page) if page > 1 else ""
        fields = [
            tid,          # 0 一级分类
            q(area),      # 1 地区
            q(sort),      # 2 排序
            q(cls),       # 3 类型
            q(lang),      # 4 语言
            "",           # 5 字母
            "",           # 6 保留
            page_s,       # 7 页码
            "", "", "",   # 8-10 保留
            q(year),      # 11 年份
        ]
        return "/vs/" + "-".join(fields) + ".html"

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "limit": "56", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1

        tid_str = str(tid).strip()
        tid_str = self._name_to_tid.get(tid_str, tid_str)
        if tid_str not in self.class_options:
            tid_str = "1"

        area = cls = lang = year = sort = ""
        if isinstance(extend, dict):
            area = extend.get("area", "") or ""
            cls = extend.get("class", "") or ""
            lang = extend.get("lang", "") or ""
            year = extend.get("year", "") or ""
            sort = extend.get("sort", "") or ""

        path = self._build_vs_path(tid_str, area, sort, cls, lang, year, page)
        html = self.getHtml(self.site_url + path, referer=self.site_url + "/")

        videos = self._parse_list(html)
        pagecount = self._parse_pagecount(html, page)

        result["list"] = videos
        result["page"] = page
        result["pagecount"] = pagecount
        result["total"] = len(videos)
        return result

    def _parse_pagecount(self, text, page):
        """解析总页数: 优先 "当前页 / 总页数" 文案, 其次 "尾页" 链接"""
        if not text:
            return page
        m = re.search(r"/\s*(\d+)\s*页", text)
        if m:
            try:
                return max(int(m.group(1)), page)
            except Exception:
                pass
        m = re.search(r'href="/vs/[^"]*?-(\d+)---\.html"[^>]*>\s*尾页', text)
        if m:
            try:
                return max(int(m.group(1)), page)
            except Exception:
                pass
        if "下一页" in text:
            return page + 1
        return page

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "limit": "56", "total": "0"}
        if not key:
            return result
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1

        if page <= 1:
            url = self.site_url + "/s.html?wd=" + urllib.parse.quote(key)
        else:
            url = self.site_url + "/s" + urllib.parse.quote(key) + "/page/%d.html" % page

        html = self.getHtml(url, referer=self.site_url + "/")
        videos = self._parse_list(html)

        result["list"] = videos
        result["page"] = page
        result["pagecount"] = self._parse_search_pagecount(html, page)
        result["total"] = len(videos)
        return result

    def _parse_search_pagecount(self, text, page):
        if not text:
            return page
        m = re.search(r"当前\s*\d+\s*/\s*(\d+)\s*页", text)
        if m:
            try:
                return max(int(m.group(1)), page)
            except Exception:
                pass
        m = re.search(r'href="/s[^"]*/page/(\d+)\.html"[^>]*>\s*尾页', text)
        if m:
            try:
                return max(int(m.group(1)), page)
            except Exception:
                pass
        if "下一页" in text:
            return page + 1
        return page

    # ==================== 详情 ====================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = str(ids[0]).strip()
        if not vid:
            return {"list": []}
        if vid.startswith("http") or "/" in vid:
            m = re.search(r"(\d+)", vid)
            vid = m.group(1) if m else vid

        html = self._get_detail_html(vid)
        if not html:
            return {"list": []}

        vod = {"vod_id": vid}

        name = self._detail_name(html)
        vod["vod_name"] = name if name else vid

        pic = self._detail_pic(html)
        vod["vod_pic"] = pic if pic else self.default_pic

        vod["vod_year"] = self._grab_year(html)
        vod["vod_area"] = self._grab_label(html, "地区")
        vod["vod_type"] = self._grab_label(html, "类型")
        vod["vod_actor"] = self._grab_label(html, "主演")
        vod["vod_director"] = self._grab_label(html, "导演")
        vod["vod_remarks"] = self._grab_label(html, "状态") or self._grab_label(html, "更新")

        # 简介处附加微信公众号「源力软件汇」
        desc = self._detail_desc(html)
        vod["vod_content"] = self.promo_text + desc

        play_from, play_url = self._detail_plays(html, vid)
        if play_from and play_url:
            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join(play_url)
        else:
            vod["vod_play_from"] = "星辰影院"
            vod["vod_play_url"] = "正片$%s/p/%s-1-1.html" % (self.site_url, vid)

        result = [vod]
        return {"list": result}

    def _get_detail_html(self, vid):
        key = "detail:%s" % vid
        item = self._cache.get(key)
        if item and item[0] > time.time():
            return item[1]
        html = self.getHtml(self.site_url + "/d-%s.html" % vid, referer=self.site_url + "/")
        if html:
            self._cache[key] = (time.time() + self._cache_ttl, html)
        return html

    def _detail_name(self, html):
        m = re.search(r"<title>\s*《(.*?)》", html, re.S)
        if m:
            name = self.clean(m.group(1))
            if name:
                return name
        m = re.search(r'class="slide-info-title[^"]*"[^>]*>(.*?)<', html, re.S)
        if m:
            name = self.clean(m.group(1))
            if name:
                return name
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if m:
            return self.clean(m.group(1)).split("-")[0].split("_")[0].strip()
        return ""

    def _detail_pic(self, html):
        m = re.search(r'class="public-pic-e"[^>]*>.*?<img[^>]*?(?:data-src|src)="(https?://[^"]+)"', html, re.S)
        if m:
            return self.absurl(m.group(1))
        m = re.search(r'(?:data-src|src)="(https?://[^"]*upload/vod[^"]*)"', html)
        if m:
            return self.absurl(m.group(1))
        return ""

    def _grab_label(self, html, label):
        """从详情页信息栏提取标签值 (兼容 <em>标签：</em>值</li> 结构)"""
        m = re.search(label + r"[:：]\s*</em>\s*(.*?)</li>", html, re.S)
        if not m:
            m = re.search(label + r"[:：]\s*</span>\s*(.*?)</li>", html, re.S)
        if not m:
            return ""
        return self.clean(re.sub(r"<[^>]+>", " ", m.group(1)))

    def _grab_year(self, html):
        m = re.search(r"年份[:：]\s*</em>\s*(\d{4})", html)
        if m:
            return m.group(1)
        return self._grab_label(html, "年份")

    def _detail_desc(self, html):
        # 优先取完整简介 (height_limit)
        m = re.search(r'id="height_limit"[^>]*>(.*?)</div>', html, re.S)
        if m:
            desc = self.clean(m.group(1))
            if desc and "暂无简介" not in desc:
                return desc
        # 回退 meta description (去掉 "xxx剧情介绍：" 前缀)
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        if m:
            desc = self.clean(m.group(1))
            if "剧情介绍" in desc:
                desc = desc.split("剧情介绍", 1)[1].lstrip("：: ")
            return desc
        return ""

    def _detail_plays(self, html, vid):
        """解析播放源标签 + 各源剧集列表

        播放源名称: .anthology-tab 内 a.swiper-slide 文本
        剧集:       每个 .anthology-list-play (ul) 内的 /p/{id}-{src}-{ep}.html
        两者按出现顺序一一对应
        """
        from_names = []
        m = re.search(r'class="anthology-tab[^"]*"[^>]*>(.*?)<div class="anthology-list', html, re.S)
        if m:
            for a in re.finditer(r'<a[^>]*class="swiper-slide[^"]*"[^>]*>(.*?)</a>', m.group(1), re.S):
                nm = re.sub(r"<[^>]+>", "", a.group(1))
                nm = self.clean(nm)
                from_names.append(nm)

        blocks = re.findall(r'<ul class="anthology-list-play[^"]*"[^>]*>(.*?)</ul>', html, re.S)

        play_from = []
        play_url = []
        for i, blk in enumerate(blocks):
            eps = re.findall(r'href="/p/([^"]+)"[^>]*>([^<]*)</a>', blk)
            if not eps:
                continue
            name = from_names[i] if i < len(from_names) and from_names[i] else "\u7ebf\u8def%d" % (i + 1)
            lines = []
            for idx, (ep_path, ep_name) in enumerate(eps):
                en = self.clean(ep_name) or ("\u7b2c%d\u96c6" % (idx + 1))
                lines.append("%s$%s/p/%s" % (en, self.site_url, ep_path))
            play_from.append(name)
            play_url.append("#".join(lines))
        return play_from, play_url

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        """解析真实播放地址

        id 形如 "剧集名$https://www.xcyycn.cc/p/{id}-{源}-{集}.html"
        抓取播放页, 读取 player_aaaa.url 得到 m3u8 直链, parse=0 直出
        """
        raw = str(id)
        if "$" in raw:
            raw = raw.split("$")[-1]
        play_page = self.absurl(raw.strip())

        play_headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.site_url + "/",
        }

        if not play_page:
            return {"url": "", "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

        # 已经是直链
        if play_page.startswith("http") and (".m3u8" in play_page or ".mp4" in play_page):
            return {"url": play_page, "parse": "0", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

        html = self.getHtml(play_page, referer=self.site_url + "/")
        real = ""

        m = re.search(r"var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>", html, re.S)
        if not m:
            m = re.search(r"var\s+player_aaaa\s*=\s*(\{.*?\})\s*;", html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                u = data.get("url", "") or ""
                u = u.replace("\\/", "/")
                if u:
                    real = u
            except Exception:
                real = ""

        # 兜底: 直接正则找 m3u8
        if not real:
            m2 = re.search(r'https?://[^\s"\'\\<>]+?\.m3u8[^\s"\'\\<>]*', html)
            if m2:
                real = m2.group(0)

        if real and (".m3u8" in real or ".mp4" in real):
            return {"url": real, "parse": "0", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

        # 无法解析则交回壳端嗅探
        return {"url": play_page, "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

    # ==================== 兼容接口 ====================

    def __jsEvalReturn(self):
        return {"proxy": None}

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def isVideoContent(self, ids):
        return False

    def manualVideoCheck(self):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
