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
        return {"class": self.CATEGORIES, "filters": {}}

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
        if page <= 1:
            url = f"{self.BASE_URL}/list/{slug}.html"
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
        vod["type_id"] = "1"
        vod["type_name"] = "韩剧"

        result["list"] = [vod]
        return result

    # ===================== 搜索 =====================
    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        url = f"{self.BASE_URL}/s/{urllib.parse.quote(key)}-------------.html"
        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        # 搜索页用 myui-vodlist__media
        for item in re.finditer(r'<li class="clearfix">(.*?)</li>', html, re.S):
            block = item.group(1)
            href = self.attr_val(block, "href")
            vid = re.search(r"/k/(\d+)", href)
            if not vid:
                continue
            name = self.tag_text(block, r'title="([^"]*)"', "")
            if not name:
                continue
            pic = self.attr_val(block, "data-original")
            year = ""
            tags = re.findall(r'<span class="tag"[^>]*>([^<]+)</span>', block)
            if len(tags) >= 2:
                year = self.clean(tags[1])
            remarks = ""
            rm = re.search(r'<p class="text[^"]*">([^<]+)</p>', block)
            if rm:
                remarks = self.clean(rm.group(1))
            videos.append({
                "vod_id": vid.group(1),
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": year,
                "vod_remarks": remarks,
                "type_id": "1",
                "type_name": "韩剧",
            })

        pagecount = "1"
        vm = re.search(r'visible-xs[^>]*><a[^>]*>(\d+)/(\d+)</a>', html)
        if vm:
            pagecount = vm.group(2)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * 48) if videos else "0"
        return result

    # ===================== 播放 =====================
    def playerContent(self, flag, id, vipFlags):
        return {"url": id, "parse": "1", "header": "", "playUrl": "", "subtitle": ""}
