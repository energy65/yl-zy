#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩剧狗 TVBox Python Spider (纯标准库版)
网站地址: https://www.hanjugo.com/
仅使用Python标准库，无需安装第三方包
"""

import re
import json
import ssl
import urllib.request
import urllib.parse
import html as html_mod

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    BASE_URL = "https://www.hanjugo.com"
    WECHAT_INFO = '微信公众号"源力软件汇"'
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": 1, "type_name": "韩剧", "slug": "hanju"},
        {"type_id": 2, "type_name": "电影", "slug": "dianying"},
        {"type_id": 3, "type_name": "连续剧", "slug": "lianxuju"},
        {"type_id": 4, "type_name": "综艺", "slug": "zongyi"},
        {"type_id": 5, "type_name": "动漫", "slug": "dongman"},
        {"type_id": 6, "type_name": "短剧", "slug": "duanju"},
        {"type_id": 7, "type_name": "AI漫剧", "slug": "aimanju"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "韩剧狗"

    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={"User-Agent": self.UA})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
                return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def tag_text(self, tag_html, pattern, default=""):
        m = re.search(pattern, tag_html)
        return self.clean(m.group(1)) if m else default

    def attr_val(self, tag_html, attr):
        m = re.search(rf'{attr}\s*=\s*["\']([^"\']*)["\']', tag_html)
        return m.group(1) if m else ""

    # ===================== 首页分类 =====================
    def homeContent(self, filter):
        filters = {
            "1": [  # 韩剧
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "古装", "v": "古装"},
                        {"n": "都市", "v": "都市"},
                        {"n": "历史", "v": "历史"},
                        {"n": "谍战", "v": "谍战"},
                        {"n": "家庭", "v": "家庭"},
                        {"n": "言情", "v": "言情"},
                        {"n": "悬疑", "v": "悬疑"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "青春", "v": "青春"},
                        {"n": "校园", "v": "校园"},
                        {"n": "刑侦", "v": "刑侦"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "励志", "v": "励志"},
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "朝鲜", "v": "朝鲜"},
                    ]
                },
                {
                    "key": "year",
                    "name": "年份",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "2026", "v": "2026"},
                        {"n": "2025", "v": "2025"},
                        {"n": "2024", "v": "2024"},
                        {"n": "2023", "v": "2023"},
                        {"n": "2022", "v": "2022"},
                        {"n": "2021", "v": "2021"},
                        {"n": "2020", "v": "2020"},
                        {"n": "2019", "v": "2019"},
                        {"n": "2018", "v": "2018"},
                        {"n": "2017", "v": "2017"},
                        {"n": "2016", "v": "2016"},
                    ]
                },
            ],
            "2": [  # 电影
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "动作片", "v": "动作片"},
                        {"n": "喜剧片", "v": "喜剧片"},
                        {"n": "爱情片", "v": "爱情片"},
                        {"n": "科幻片", "v": "科幻片"},
                        {"n": "恐怖片", "v": "恐怖片"},
                        {"n": "剧情片", "v": "剧情片"},
                        {"n": "战争片", "v": "战争片"},
                        {"n": "犯罪片", "v": "犯罪片"},
                        {"n": "悬疑片", "v": "悬疑片"},
                        {"n": "奇幻片", "v": "奇幻片"},
                        {"n": "武侠片", "v": "武侠片"},
                        {"n": "历史片", "v": "历史片"},
                        {"n": "文艺片", "v": "文艺片"},
                        {"n": "冒险片", "v": "冒险片"},
                        {"n": "灾难片", "v": "灾难片"},
                        {"n": "动画片", "v": "动画片"},
                        {"n": "惊悚片", "v": "惊悚片"},
                        {"n": "伦理片", "v": "伦理片"},
                        {"n": "纪录片", "v": "纪录片"},
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "中国大陆", "v": "中国大陆"},
                        {"n": "中国香港", "v": "中国香港"},
                        {"n": "中国台湾", "v": "中国台湾"},
                        {"n": "日本", "v": "日本"},
                        {"n": "美国", "v": "美国"},
                        {"n": "英国", "v": "英国"},
                        {"n": "法国", "v": "法国"},
                        {"n": "泰国", "v": "泰国"},
                        {"n": "其他", "v": "其他"},
                    ]
                },
                {
                    "key": "year",
                    "name": "年份",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "2026", "v": "2026"},
                        {"n": "2025", "v": "2025"},
                        {"n": "2024", "v": "2024"},
                        {"n": "2023", "v": "2023"},
                        {"n": "2022", "v": "2022"},
                        {"n": "2021", "v": "2021"},
                        {"n": "2020", "v": "2020"},
                        {"n": "2019", "v": "2019"},
                        {"n": "2018", "v": "2018"},
                        {"n": "2017", "v": "2017"},
                        {"n": "2016", "v": "2016"},
                        {"n": "更早", "v": "2015"},
                    ]
                },
            ],
            "3": [  # 连续剧
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "古装", "v": "古装"},
                        {"n": "都市", "v": "都市"},
                        {"n": "历史", "v": "历史"},
                        {"n": "谍战", "v": "谍战"},
                        {"n": "家庭剧", "v": "家庭剧"},
                        {"n": "言情", "v": "言情"},
                        {"n": "武侠", "v": "武侠"},
                        {"n": "悬疑", "v": "悬疑"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "青春", "v": "青春"},
                        {"n": "校园", "v": "校园"},
                        {"n": "刑侦", "v": "刑侦"},
                        {"n": "商战", "v": "商战"},
                        {"n": "军旅", "v": "军旅"},
                        {"n": "奇幻", "v": "奇幻"},
                        {"n": "科幻", "v": "科幻"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "伦理片", "v": "伦理片"},
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "中国大陆", "v": "中国大陆"},
                        {"n": "中国香港", "v": "中国香港"},
                        {"n": "中国台湾", "v": "中国台湾"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "日本", "v": "日本"},
                        {"n": "泰国", "v": "泰国"},
                        {"n": "美国", "v": "美国"},
                        {"n": "英国", "v": "英国"},
                        {"n": "其他", "v": "其他"},
                    ]
                },
                {
                    "key": "year",
                    "name": "年份",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "2026", "v": "2026"},
                        {"n": "2025", "v": "2025"},
                        {"n": "2024", "v": "2024"},
                        {"n": "2023", "v": "2023"},
                        {"n": "2022", "v": "2022"},
                        {"n": "2021", "v": "2021"},
                        {"n": "2020", "v": "2020"},
                        {"n": "2019", "v": "2019"},
                        {"n": "2018", "v": "2018"},
                        {"n": "2017", "v": "2017"},
                        {"n": "2016", "v": "2016"},
                    ]
                },
            ],
            "4": [  # 综艺
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "真人秀", "v": "真人秀"},
                        {"n": "选秀", "v": "选秀"},
                        {"n": "脱口秀", "v": "脱口秀"},
                        {"n": "情感", "v": "情感"},
                        {"n": "访谈", "v": "访谈"},
                        {"n": "美食", "v": "美食"},
                        {"n": "旅游", "v": "旅游"},
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "中国大陆", "v": "中国大陆"},
                        {"n": "中国台湾", "v": "中国台湾"},
                        {"n": "日本", "v": "日本"},
                        {"n": "其他", "v": "其他"},
                    ]
                },
            ],
            "5": [  # 动漫
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "热血", "v": "热血"},
                        {"n": "搞笑", "v": "搞笑"},
                        {"n": "恋爱", "v": "恋爱"},
                        {"n": "科幻", "v": "科幻"},
                        {"n": "奇幻", "v": "奇幻"},
                        {"n": "冒险", "v": "冒险"},
                        {"n": "战斗", "v": "战斗"},
                        {"n": "校园", "v": "校园"},
                        {"n": "治愈", "v": "治愈"},
                        {"n": "悬疑", "v": "悬疑"},
                        {"n": "后宫", "v": "后宫"},
                        {"n": "日常", "v": "日常"},
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "日本", "v": "日本"},
                        {"n": "中国", "v": "中国"},
                        {"n": "欧美", "v": "欧美"},
                        {"n": "韩国", "v": "韩国"},
                    ]
                },
            ],
        }
        return {"class": self.CATEGORIES, "filters": filters}

    # ===================== 首页推荐 =====================
    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result
        videos = []
        for item in re.finditer(r'<li class="col-lg-8[^"]*">(.*?)</li>', html, re.S):
            block = item.group(1)
            href = self.attr_val(block, "href")
            vid = re.search(r"/k/(\d+)", href)
            if not vid:
                continue
            name = self.tag_text(block, r'title="([^"]*)"', "")
            if not name:
                name = self.tag_text(block, r'<a[^>]*>([^<]+)</a>', "")
            pic = self.attr_val(block, "data-original")
            year = ""
            tags = re.findall(r'<span class="tag"[^>]*>([^<]+)</span>', block)
            if len(tags) >= 2:
                year = self.clean(tags[1])
            remarks = self.tag_text(block, r'<span class="pic-text[^"]*">([^<]+)</span>')
            actor = ""
            am = re.search(r'主演[：:]\s*([^<]+)', block)
            if am:
                actor = self.clean(am.group(1))
            videos.append({
                "vod_id": vid.group(1),
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": year,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "vod_content": self.WECHAT_INFO,
            })
        result["list"] = videos[:30]
        return result

    # ===================== 分类列表 =====================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        cat = None
        for c in self.CATEGORIES:
            if c["type_id"] == int(tid):
                cat = c
                break
        if not cat:
            return result

        slug = cat["slug"]
        page = int(pg) if str(pg).isdigit() else 1

        # 构造筛选参数
        params = {}
        if isinstance(extend, dict):
            for k in ["class", "area", "lang", "year", "letter", "by", "state"]:
                if extend.get(k):
                    params[k] = extend.get(k)

        query_str = ""
        if params:
            # 尝试常用的筛选参数拼接方式，部分站点支持query参数
            query_str = "?" + urllib.parse.urlencode(params)

        if page <= 1:
            url = f"{self.BASE_URL}/list/{slug}.html{query_str}"
        else:
            if query_str:
                # 如果有筛选参数，尝试在分页时保留参数（部分站点可能不支持，仍会尝试请求）
                url = f"{self.BASE_URL}/list/{slug}-{page}.html{query_str}"
            else:
                url = f"{self.BASE_URL}/list/{slug}-{page}.html"

        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        for item in re.finditer(r'<li class="col-lg-8[^"]*">(.*?)</li>', html, re.S):
            block = item.group(1)
            href = self.attr_val(block, "href")
            vid = re.search(r"/k/(\d+)", href)
            if not vid:
                continue
            name = self.tag_text(block, r'title="([^"]*)"', "")
            if not name:
                name = self.tag_text(block, r'<a[^>]*>([^<]+)</a>', "")
            pic = self.attr_val(block, "data-original")
            year = ""
            score = ""
            tags = re.findall(r'<span class="tag"[^>]*>([^<]+)</span>', block)
            if len(tags) >= 1:
                score = self.clean(tags[0]).replace("分", "")
            if len(tags) >= 2:
                year = self.clean(tags[1])
            remarks = self.tag_text(block, r'<span class="pic-text[^"]*">([^<]+)</span>')
            actor = ""
            am = re.search(r'主演[：:]\s*([^<]+)', block)
            if am:
                actor = self.clean(am.group(1))
            videos.append({
                "vod_id": vid.group(1),
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": year,
                "vod_score": score,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "type_id": str(cat["type_id"]),
                "type_name": cat["type_name"],
            })

        pagecount = "1"
        vm = re.search(r'(\d+)/(\d+)</a>\s*</li>\s*<li><a[^>]*>下一页', html)
        if not vm:
            vm = re.search(r'visible-xs[^>]*><a[^>]*>(\d+)/(\d+)</a>', html)
        if vm:
            pagecount = vm.group(2)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    # ===================== 视频详情 =====================
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        url = f"{self.BASE_URL}/k/{vid}.html"
        html = self.getHtml(url)
        if not html:
            return result

        vod = {"vod_id": str(vid)}

        # 标题
        hm = re.search(r'<h1 class="title"[^>]*>([^<]+)</h1>', html)
        vod["vod_name"] = self.clean(hm.group(1)) if hm else ""

        # 图片
        pm = re.search(r'data-original="(https?://[^"]+)"', html)
        vod["vod_pic"] = pm.group(1) if pm else ""

        # 分类/地区/年份
        vod["vod_class"] = ""
        vod["vod_area"] = ""
        vod["vod_year"] = ""
        vod["vod_remarks"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = ""
        vod["vod_lang"] = ""

        for dm in re.finditer(r'<p class="data[^"]*">(.*?)</p>', html, re.S):
            block = dm.group(1)
            text = re.sub(r'<[^>]+>', '', block)
            if "分类" in text:
                cm = re.search(r'分类[：:]\s*(.+?)(?:地区|$)', text)
                if cm:
                    vod["vod_class"] = self.clean(cm.group(1))
                am = re.search(r'地区[：:]\s*(.+?)(?:年份|$)', text)
                if am:
                    vod["vod_area"] = self.clean(am.group(1))
                ym = re.search(r'年份[：:]\s*(\d+)', text)
                if ym:
                    vod["vod_year"] = ym.group(1)
            elif "更新" in text or "已完结" in text:
                if "已完结" in text:
                    vod["vod_remarks"] = "已完结"
                else:
                    rm = re.search(r'更新[：:]\s*(.+)', text)
                    if rm:
                        vod["vod_remarks"] = self.clean(rm.group(1))
            elif "主演" in text:
                vod["vod_actor"] = text.replace("主演：", "").replace("主演:", "").strip()
            elif "导演" in text:
                vod["vod_director"] = text.replace("导演：", "").replace("导演:", "").strip()

        # 简介
        desc_m = re.search(r'<span class="sketch content">(.*?)</span>', html, re.S)
        if desc_m:
            desc_text = re.sub(r'<[^>]+>', '', desc_m.group(1))
            vod["vod_content"] = self.WECHAT_INFO + "\n" + self.clean(desc_text)
        else:
            vod["vod_content"] = self.WECHAT_INFO

        # 播放源和播放列表
        play_sources = []
        play_url_groups = []

        # 方法1: tab-pane 结构
        for pm in re.finditer(r'<div[^>]*id="(playlist\d+)"[^>]*class="tab-pane[^"]*">(.*?)</div>\s*(?=<div[^>]*id="playlist|</div>)', html, re.S):
            pane_id = pm.group(1)
            pane_html = pm.group(2)
            source_name = "极速在线"
            tab_m = re.search(rf"href='#{pane_id}'[^>]*>([^<]+)</a>", html)
            if tab_m:
                source_name = self.clean(tab_m.group(1))
            episodes = []
            for am in re.finditer(r'<a[^>]*class="btn[^"]*"\s*href="([^"]+)"[^>]*>([^<]+)</a>', pane_html):
                ep_href = am.group(1)
                ep_name = self.clean(am.group(2))
                if ep_name and ep_href:
                    full_url = self.BASE_URL + ep_href if ep_href.startswith("/") else ep_href
                    episodes.append(f"{ep_name}${full_url}")
            if episodes:
                play_sources.append(source_name)
                play_url_groups.append("#".join(episodes))

        # 方法2: playlist ul
        if not play_url_groups:
            for um in re.finditer(r'<ul[^>]*class="[^"]*playlist[^"]*"[^>]*>(.*?)</ul>', html, re.S):
                ul_html = um.group(1)
                episodes = []
                for am in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', ul_html):
                    ep_href = am.group(1)
                    ep_name = self.clean(am.group(2))
                    if ep_name and ep_href:
                        full_url = self.BASE_URL + ep_href if ep_href.startswith("/") else ep_href
                        episodes.append(f"{ep_name}${full_url}")
                if episodes:
                    play_sources.append("极速在线")
                    play_url_groups.append("#".join(episodes))

        vod["vod_play_from"] = "$$$".join(play_sources) if play_sources else "极速在线"
        vod["vod_play_url"] = "$$$".join(play_url_groups) if play_url_groups else ""
        vod["type_id"] = str(tid)
        vod["type_name"] = cat["type_name"] if 'cat' in locals() and cat else vod.get("vod_class", "")

        result["list"] = [vod]
        return result

    # ===================== 搜索 =====================
    def searchContent(self, key, quick, pg="1"):
        try:
            return self._do_search(key, quick, pg)
        except Exception:
            return {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}

    def _do_search(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.BASE_URL}/s/{urllib.parse.quote(key)}-------------.html"
        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        # 搜索页 li.clearfix 结构
        for item in re.finditer(r'<li\s+class="clearfix">(.*?)</li>', html, re.S):
            block = item.group(1)
            # 提取 vod_id
            href_m = re.search(r'href="(/k/\d+\.html)"', block)
            if not href_m:
                continue
            vid_m = re.search(r'/k/(\d+)', href_m.group(1))
            if not vid_m:
                continue
            # 提取名称
            name = ""
            title_m = re.search(r'title="([^"]+)"', block)
            if title_m:
                name = self.clean(title_m.group(1))
            if not name:
                name_m = re.search(r'<a[^>]*class="searchkey"[^>]*>([^<]+)</a>', block)
                if name_m:
                    name = self.clean(name_m.group(1))
            if not name:
                name_m = re.search(r'<h4[^>]*>.*?<a[^>]*>([^<]+)</a>', block, re.S)
                if name_m:
                    name = self.clean(name_m.group(1))
            if not name:
                continue
            # 提取封面
            pic_m = re.search(r'data-original="(https?://[^"]+)"', block)
            pic = pic_m.group(1) if pic_m else ""
            # 提取年份和评分
            year = ""
            score = ""
            tags = re.findall(r'<span class="tag"[^>]*>([^<]+)</span>', block)
            if len(tags) >= 1:
                score = self.clean(tags[0]).replace("分", "")
            if len(tags) >= 2:
                year = self.clean(tags[1])
            # 提取备注
            remarks = ""
            rm = re.search(r'<span class="pic-text[^"]*">([^<]+)</span>', block)
            if rm:
                remarks = self.clean(rm.group(1))
            # 提取主演
            actor = ""
            am = re.search(r'主演[：:]\s*([^<]+)', block)
            if am:
                actor = self.clean(am.group(1))
            # 提取分类
            vod_class = ""
            cm = re.search(r'分类[：:]\s*([^<]+)', block)
            if cm:
                vod_class = self.clean(cm.group(1))

            videos.append({
                "vod_id": vid_m.group(1),
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": year,
                "vod_score": score,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "type_id": "1",
                "type_name": vod_class if vod_class else "韩剧",
            })

        pagecount = "1"
        vm = re.search(r'(\d+)/(\d+)</a>', html)
        if vm:
            pagecount = vm.group(2)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * 48) if videos else "0"
        return result

    # ===================== 播放 =====================
    def playerContent(self, flag, id, vipFlags):
        return {"url": id, "parse": "1", "header": "", "playUrl": "", "subtitle": ""}