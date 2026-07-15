#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4K-AV TVBox Python Spider
网站地址: https://4k-av.com/
"""

import re
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
    BASE_URL = "https://4k-av.com"
    WECHAT_INFO = '微信公众号"源力软件汇"'
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": 1, "type_name": "电影", "slug": "movie"},
        {"type_id": 2, "type_name": "电视剧", "slug": "tv"},
        {"type_id": 3, "type_name": "AV", "slug": "av"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "4K-AV"

    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
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
        text = text.replace("&#183;", "·")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def attr_val(self, tag_html, attr):
        m = re.search(rf'{attr}\s*=\s*["\']([^"\']*)["\']', tag_html)
        return m.group(1) if m else ""

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result

        videos = []
        patterns = [
            r'<div class="NTMitem Main">(.*?)</div>\s*</div>\s*</div>',
            r'<div class="NTMitem">(.*?)</div>\s*</div>',
        ]
        for pattern in patterns:
            for item in re.finditer(pattern, html, re.S):
                block = item.group(1)
                href_m = re.search(r'href="(/(movie|tv)/[^"]+)"', block)
                if not href_m:
                    continue
                href = href_m.group(1)
                cat = href_m.group(2)
                
                vid = ""
                vid_match = re.search(rf'/{cat}/([^/]+)/', href)
                if vid_match:
                    vid = vid_match.group(1)

                name_m = re.search(r'<h2>([^<]+)</h2>', block)
                name = self.clean(name_m.group(1)) if name_m else ""

                if not vid or not name:
                    continue

                pic_m = re.search(r'src="(https?://[^"]+poster_nail[^"]+)"', block)
                pic = pic_m.group(1) if pic_m else ""

                resolution = ""
                res_m = re.search(r'<label title="分辨率"\s*>([^<]+)</label>', block)
                if not res_m:
                    res_m = re.search(r'<label>([^<]+)</label>', block)
                if res_m:
                    resolution = self.clean(res_m.group(1))

                year_m = re.search(r'<label title="年份">(\d+)</label>', block)
                year = year_m.group(1) if year_m else ""

                tags = []
                for tag_m in re.finditer(r'<span>([^<]+)</span>', block):
                    tags.append(self.clean(tag_m.group(1)))

                desc_m = re.search(r'<div class="videodesc">(.*?)</div>', block, re.S)
                desc = self.clean(desc_m.group(1)) if desc_m else ""

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_year": year,
                    "vod_remarks": resolution,
                    "vod_class": " ".join(tags),
                    "vod_content": desc,
                    "vod_type": cat,
                })

        result["list"] = videos[:30]
        return result

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
            url = f"{self.BASE_URL}/{slug}/"
        else:
            url = f"{self.BASE_URL}/{slug}/page-{page}.html"

        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        patterns = [
            r'<div class="NTMitem Main">(.*?)</div>\s*</div>\s*</div>',
            r'<div class="NTMitem">(.*?)</div>\s*</div>',
        ]
        for pattern in patterns:
            for item in re.finditer(pattern, html, re.S):
                block = item.group(1)
                href_m = re.search(r'href="(/(movie|tv|av)/[^"]+)"', block)
                if not href_m:
                    continue
                href = href_m.group(1)
                cat_type = href_m.group(2)
                
                vid = ""
                vid_match = re.search(rf'/{cat_type}/([^/]+)/', href)
                if vid_match:
                    vid = vid_match.group(1)

                name_m = re.search(r'<h2>([^<]+)</h2>', block)
                name = self.clean(name_m.group(1)) if name_m else ""

                if not vid or not name:
                    continue

                pic_m = re.search(r'src="(https?://[^"]+poster_nail[^"]+)"', block)
                pic = pic_m.group(1) if pic_m else ""

                resolution = ""
                res_m = re.search(r'<label title="分辨率"\s*>([^<]+)</label>', block)
                if not res_m:
                    res_m = re.search(r'<label>([^<]+)</label>', block)
                if res_m:
                    resolution = self.clean(res_m.group(1))

                year_m = re.search(r'<label title="年份">(\d+)</label>', block)
                year = year_m.group(1) if year_m else ""

                tags = []
                for tag_m in re.finditer(r'<span>([^<]+)</span>', block):
                    tags.append(self.clean(tag_m.group(1)))

                desc_m = re.search(r'<div class="videodesc">(.*?)</div>', block, re.S)
                desc = self.clean(desc_m.group(1)) if desc_m else ""

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_year": year,
                    "vod_remarks": resolution,
                    "vod_class": " ".join(tags),
                    "vod_content": desc,
                    "vod_type": cat_type,
                    "type_id": str(cat["type_id"]),
                    "type_name": cat["type_name"],
                })

        pagecount = "1"
        page_info_m = re.search(r'页次\s*(\d+)/(\d+)', html)
        if page_info_m:
            pagecount = page_info_m.group(2)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        
        urls_to_try = [
            f"{self.BASE_URL}/movie/{vid}/",
            f"{self.BASE_URL}/tv/{vid}/",
            f"{self.BASE_URL}/av/{vid}/",
        ]
        
        html = ""
        final_url = ""
        for url in urls_to_try:
            html = self.getHtml(url)
            if html and "<title>" in html:
                final_url = url
                break
        
        if not html:
            return result

        vod = {"vod_id": str(vid)}

        title_m = re.search(r'<h1 title="([^"]+)">([^<]+)</h1>', html)
        if title_m:
            vod["vod_name"] = self.clean(title_m.group(1))
        else:
            title_m2 = re.search(r'<div title="([^"]+)">([^<]+)</div>', html)
            vod["vod_name"] = self.clean(title_m2.group(1)) if title_m2 else ""

        pic_m = re.search(r'src="(https?://[^"]+poster_nail[^"]+)"', html)
        vod["vod_pic"] = pic_m.group(1) if pic_m else ""

        vod["vod_class"] = ""
        vod["vod_area"] = ""
        vod["vod_year"] = ""
        vod["vod_remarks"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = ""
        vod["vod_lang"] = ""

        resolution = ""
        res_m = re.search(r'<label>分辨率:\s*([^<]+)</label>', html)
        if not res_m:
            res_m = re.search(r'<label title="分辨率"\s*>([^<]+)</label>', html)
        if res_m:
            resolution = self.clean(res_m.group(1))
        vod["vod_remarks"] = resolution

        year_m = re.search(r'<label>年份:\s*<a[^>]*>(\d+)</a>', html)
        if year_m:
            vod["vod_year"] = year_m.group(1)

        tags = []
        for tag_m in re.finditer(r'<a href="/tag/[^"]+/">([^<]+)</a>', html):
            tags.append(self.clean(tag_m.group(1)))
        vod["vod_class"] = " ".join(tags)

        desc_m = re.search(r'<div id="MainContent_videodesc">(.*?)</div>', html, re.S)
        if desc_m:
            desc_text = self.clean(desc_m.group(1))
            vod["vod_content"] = self.WECHAT_INFO + "\n" + desc_text
        else:
            vod["vod_content"] = self.WECHAT_INFO

        play_urls = []
        source_m = re.search(r'<source\s+src="(https?://[^"]+)"', html)
        if source_m:
            play_urls.append(source_m.group(1))

        if play_urls:
            vod["vod_play_from"] = "4K-AV"
            vod["vod_play_url"] = "#".join([f"播放${url}" for url in play_urls])
        else:
            vod["vod_play_from"] = ""
            vod["vod_play_url"] = ""

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            return self._do_search(key, quick, pg)
        except Exception:
            return {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}

    def _do_search(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1
        
        url = f"{self.BASE_URL}/s?m={urllib.parse.quote(key)}"
        if page > 1:
            url = f"{self.BASE_URL}/s/page-{page}.html?m={urllib.parse.quote(key)}"

        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        patterns = [
            r'<div class="NTMitem Main">(.*?)</div>\s*</div>\s*</div>',
            r'<div class="NTMitem">(.*?)</div>\s*</div>',
        ]
        for pattern in patterns:
            for item in re.finditer(pattern, html, re.S):
                block = item.group(1)
                href_m = re.search(r'href="(/(movie|tv|av)/[^"]+)"', block)
                if not href_m:
                    continue
                href = href_m.group(1)
                cat_type = href_m.group(2)
                
                vid = ""
                vid_match = re.search(rf'/{cat_type}/([^/]+)/', href)
                if vid_match:
                    vid = vid_match.group(1)

                name_m = re.search(r'<h2>([^<]+)</h2>', block)
                name = self.clean(name_m.group(1)) if name_m else ""

                if not vid or not name:
                    continue

                pic_m = re.search(r'src="(https?://[^"]+poster_nail[^"]+)"', block)
                pic = pic_m.group(1) if pic_m else ""

                resolution = ""
                res_m = re.search(r'<label title="分辨率"\s*>([^<]+)</label>', block)
                if not res_m:
                    res_m = re.search(r'<label>([^<]+)</label>', block)
                if res_m:
                    resolution = self.clean(res_m.group(1))

                year_m = re.search(r'<label title="年份">(\d+)</label>', block)
                year = year_m.group(1) if year_m else ""

                tags = []
                for tag_m in re.finditer(r'<span>([^<]+)</span>', block):
                    tags.append(self.clean(tag_m.group(1)))

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_year": year,
                    "vod_remarks": resolution,
                    "vod_class": " ".join(tags),
                })

        pagecount = "1"
        page_info_m = re.search(r'页次\s*(\d+)/(\d+)', html)
        if page_info_m:
            pagecount = page_info_m.group(2)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id)
        if play_url.startswith("$"):
            play_url = play_url[1:]
        if "$" in play_url:
            parts = play_url.split("$")
            if len(parts) >= 2:
                play_url = parts[-1]
        if not play_url.startswith("http"):
            play_url = ""
        return {"url": play_url, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}