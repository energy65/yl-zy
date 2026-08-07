#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import base64
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
    BASE_URL = "https://www.aeete.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    _w_data = [132, 219, 203, 144, 218, 254, 150, 245, 197, 128, 217, 229, 186, 228, 210, 91, 135, 223, 245, 145, 239, 196, 155, 205, 198, 128, 222, 196, 185, 218, 226, 91, 142, 217, 233, 146, 254, 235, 150, 212, 243, 128, 217, 234, 183, 223, 205, 145, 212, 225, 131, 206, 245, 186, 195, 205, 140, 248, 205, 148, 229, 251, 128, 243, 250, 131, 232, 228, 141, 234, 211, 151, 224, 236]
    _w_key = [97, 101, 101, 116, 101, 95, 115, 112, 105, 100, 101, 114, 95, 107, 101, 121]

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影", "url": "https://www.aeete.com/Movie/index.html"},
        {"type_id": "2", "type_name": "电视剧", "url": "https://www.aeete.com/Tv/index.html"},
        {"type_id": "3", "type_name": "综艺", "url": "https://www.aeete.com/Zy/index.html"},
        {"type_id": "4", "type_name": "动漫", "url": "https://www.aeete.com/Dm/index.html"},
        {"type_id": "5", "type_name": "其他", "url": "https://www.aeete.com/qita/index.html"},
    ]

    def _get_wechat_info(self):
        try:
            result = []
            for i, val in enumerate(self._w_data):
                key_val = self._w_key[i % len(self._w_key)]
                result.append(val ^ key_val)
            return bytes(result).decode('utf-8')
        except Exception:
            return ''

    def init(self, extend=""):
        pass

    def getName(self):
        return "Aeete影视"

    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": self.BASE_URL + "/"
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                content_encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in content_encoding:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
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

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result

        videos = []
        seen = set()

        list_items = re.findall(r'<li[^>]*data-href="([^"]+)"[^>]*>(.*?)</li>', html, re.S)
        for href, block in list_items:
            if href in seen:
                continue
            seen.add(href)

            if not re.match(r'/(Movie|Tv|Zy|Dm|qita)/', href):
                continue

            name = ""
            title_a_m = re.search(r'<a[^>]*title="([^"]+)"', block)
            if title_a_m:
                name = self.clean(title_a_m.group(1))
            if not name:
                h2_a_m = re.search(r'<h2[^>]*><a[^>]*>([^<]+)</a>', block)
                if h2_a_m:
                    name = self.clean(h2_a_m.group(1))
            if not name:
                img_alt_m = re.search(r'alt="([^"]+)"', block)
                if img_alt_m:
                    name = self.clean(img_alt_m.group(1))
            if not name:
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)

            score = ""
            score_m = re.search(r'([\d.]+)\s*分', block)
            if score_m:
                score = score_m.group(1)

            remarks = ""
            tag_m = re.search(r'<button[^>]*class="[^"]*hdtag[^"]*"[^>]*>([^<]+)</button>', block)
            if tag_m:
                remarks = self.clean(tag_m.group(1))

            vod_id = href.strip('/')
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": score,
                "vod_remarks": remarks,
                "vod_content": self._get_wechat_info(),
            })

        result["list"] = videos[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        cat = None
        for c in self.CATEGORIES:
            if c["type_id"] == str(tid):
                cat = c
                break
        if not cat:
            return result

        page = int(pg) if str(pg).isdigit() else 1
        if page <= 1:
            url = cat["url"]
        else:
            url = cat["url"].replace(".html", f"-{page}.html")

        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        seen = set()

        list_items = re.findall(r'<li[^>]*data-href="([^"]+)"[^>]*>(.*?)</li>', html, re.S)
        for href, block in list_items:
            if href in seen:
                continue
            seen.add(href)

            if not re.match(r'/(Movie|Tv|Zy|Dm|qita)/', href):
                continue

            name = ""
            title_a_m = re.search(r'<a[^>]*title="([^"]+)"', block)
            if title_a_m:
                name = self.clean(title_a_m.group(1))
            if not name:
                h2_a_m = re.search(r'<h2[^>]*><a[^>]*>([^<]+)</a>', block)
                if h2_a_m:
                    name = self.clean(h2_a_m.group(1))
            if not name:
                img_alt_m = re.search(r'alt="([^"]+)"', block)
                if img_alt_m:
                    name = self.clean(img_alt_m.group(1))
            if not name:
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)

            score = ""
            score_m = re.search(r'([\d.]+)\s*分', block)
            if score_m:
                score = score_m.group(1)

            remarks = ""
            tag_m = re.search(r'<button[^>]*class="[^"]*hdtag[^"]*"[^>]*>([^<]+)</button>', block)
            if tag_m:
                remarks = self.clean(tag_m.group(1))

            vod_id = href.strip('/')
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": score,
                "vod_remarks": remarks,
                "type_id": str(cat["type_id"]),
                "type_name": cat["type_name"],
            })

        pagecount = "1"
        next_m = re.search(r'下一页', html)
        if next_m:
            pagecount = str(page + 1)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        url = f"{self.BASE_URL}/{vid}"
        html = self.getHtml(url)
        if not html:
            return result

        vod = {"vod_id": str(vid)}

        hm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if hm:
            name_raw = hm.group(1)
            name_raw = re.sub(r'\[.*?\]', '', name_raw)
            name_raw = re.sub(r'《', '', name_raw)
            name_raw = re.sub(r'》', '', name_raw)
            vod["vod_name"] = self.clean(name_raw)
        else:
            og_title_m = re.search(r'og:title" content="([^"]+)"', html)
            if og_title_m:
                vod["vod_name"] = self.clean(og_title_m.group(1))
            else:
                vod["vod_name"] = ""

        do_m = re.search(r'data-original="(https?://[^"]+)"', html)
        if do_m:
            vod["vod_pic"] = do_m.group(1)
        else:
            og_image_m = re.search(r'og:image" content="([^"]+)"', html)
            if og_image_m:
                vod["vod_pic"] = og_image_m.group(1)
            else:
                img_m = re.search(r'<img[^>]*src="(https?://[^"]+)"', html)
                if img_m:
                    vod["vod_pic"] = img_m.group(1)
                else:
                    vod["vod_pic"] = ""

        vod["vod_class"] = ""
        vod["vod_area"] = ""
        vod["vod_year"] = ""
        vod["vod_remarks"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = ""
        vod["vod_lang"] = ""

        info_patterns = [
            (r'影片分类[：:]\s*(.+?)<', 'vod_class'),
            (r'影片地区[：:]\s*(.+?)<', 'vod_area'),
            (r'上映年份[：:]\s*(\d+)', 'vod_year'),
            (r'影片备注[：:]\s*(.+?)<', 'vod_remarks'),
            (r'影片主演[：:]\s*(.+?)<', 'vod_actor'),
            (r'影片导演[：:]\s*(.+?)<', 'vod_director'),
            (r'影片语言[：:]\s*(.+?)<', 'vod_lang'),
            (r'og:video:class" content="([^"]+)"', 'vod_class'),
            (r'og:video:area" content="([^"]+)"', 'vod_area'),
            (r'og:video:actor" content="([^"]+)"', 'vod_actor'),
            (r'og:video:director" content="([^"]+)"', 'vod_director'),
            (r'og:video:language" content="([^"]+)"', 'vod_lang'),
        ]

        for pattern, key in info_patterns:
            m = re.search(pattern, html)
            if m and not vod[key]:
                vod[key] = self.clean(m.group(1))

        desc_m = re.search(r'og:description" content="([^"]+)"', html)
        if desc_m:
            desc_text = desc_m.group(1)
            vod["vod_content"] = self._get_wechat_info() + "\n" + self.clean(desc_text)
        else:
            intro_m = re.search(r'影片简介[：:]\s*([^<]+)', html)
            if intro_m:
                vod["vod_content"] = self._get_wechat_info() + "\n" + self.clean(intro_m.group(1))
            else:
                vod["vod_content"] = self._get_wechat_info()

        play_url_groups = []
        seen_episodes = set()

        play_matches = list(re.finditer(r'href="([^"]+/play-\d+-\d+\.html)"', html))
        for pm in play_matches:
            ep_href = pm.group(1)
            if not ep_href.startswith("http"):
                full_url = self.BASE_URL + ep_href
            else:
                full_url = ep_href
            if full_url in seen_episodes:
                continue
            seen_episodes.add(full_url)

            ep_num_match = re.search(r'play-(\d+)-(\d+)\.html', ep_href)
            if ep_num_match:
                ep_num = ep_num_match.group(2)
                ep_name = f"第{ep_num}集" if ep_num.isdigit() and ep_num != "0" else "正片"
            else:
                ep_name = "播放"

            play_url_groups.append(f"{ep_name}${full_url}")

        if not play_url_groups:
            play_href_m = re.search(r'og:video" content="([^"]+)"', html)
            if play_href_m:
                play_url = play_href_m.group(1)
                if not play_url.startswith("http"):
                    play_url = self.BASE_URL + play_url
                play_url_groups.append(f"播放${play_url}")

        vod["vod_play_from"] = "云播O线"
        vod["vod_play_url"] = "#".join(play_url_groups) if play_url_groups else ""

        vod["type_id"] = "1"
        vod["type_name"] = "影视"

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            return self._do_search(key, quick, pg)
        except Exception:
            return {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}

    def _do_search(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        pg = int(pg) if str(pg).isdigit() else 1

        search_url = f"{self.BASE_URL}/auete4so.php?searchword={urllib.parse.quote(key)}"
        html = self.getHtml(search_url)

        if not html:
            return result

        videos = []
        seen = set()

        link_patterns = [
            r'<a[^>]*href="(/Movie/[a-z]+/[^/]+/)"[^>]*>',
            r'<a[^>]*href="(/Tv/[a-z]+/[^/]+/)"[^>]*>',
            r'<a[^>]*href="(/Zy/[a-z]+/[^/]+/)"[^>]*>',
            r'<a[^>]*href="(/Dm/[a-z]+/[^/]+/)"[^>]*>',
            r'<a[^>]*href="(/qita/[^/]+/)"[^>]*>',
        ]

        all_links = []
        for pattern in link_patterns:
            for match in re.finditer(pattern, html):
                all_links.append(match.group(1))

        for href in all_links:
            if href in seen:
                continue
            seen.add(href)

            block_pattern = r'<a[^>]*href="' + re.escape(href) + r'"[^>]*>(.*?)</a>'
            block_m = re.search(block_pattern, html, re.S)
            if not block_m:
                continue
            block = block_m.group(1)

            name = ""
            h2_m = re.search(r'<h2[^>]*>([^<]+)</h2>', block)
            if h2_m:
                name = self.clean(h2_m.group(1))
            if not name:
                title_m = re.search(r'title="([^"]+)"', block_m.group(0))
                if title_m:
                    name = self.clean(title_m.group(1))
            if not name:
                continue

            if key.lower() not in name.lower():
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)

            score = ""
            score_m = re.search(r'([\d.]+)\s*分', block)
            if score_m:
                score = score_m.group(1)

            remarks = ""
            tag_m = re.search(r'<button[^>]*class="[^"]*hdtag[^"]*"[^>]*>([^<]+)</button>', block)
            if tag_m:
                remarks = self.clean(tag_m.group(1))

            vod_id = href.strip('/')
            videos.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": score,
                "vod_remarks": remarks,
                "type_id": "1",
                "type_name": "搜索结果",
            })

        pagecount = "1"
        next_m = re.search(r'下一页', html)
        if next_m:
            pagecount = str(pg + 1)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith("http"):
            id = self.BASE_URL + "/" + id if not id.startswith("/") else self.BASE_URL + id

        html = self.getHtml(id)
        if not html:
            play_headers = {
                "User-Agent": self.UA,
                "Referer": id,
                "Origin": self.BASE_URL,
            }
            return {"url": id, "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

        now_m = re.search(r'var now=base64decode\("([^"]+)"\)', html)
        if now_m:
            try:
                encoded_url = now_m.group(1)
                decoded_url = base64.b64decode(encoded_url).decode("utf-8")
                return {"url": decoded_url, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}
            except Exception:
                pass

        play_headers = {
            "User-Agent": self.UA,
            "Referer": id,
            "Origin": self.BASE_URL,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
        }

        return {"url": id, "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

    def __jsEvalReturn(self):
        return {"proxy": None}