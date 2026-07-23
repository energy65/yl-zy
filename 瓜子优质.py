#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import ssl
import json
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
    BASE_URL = "https://www.guaziys.net"
    WECHAT_INFO = '微信公众号"源力软件汇"'
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "21", "type_name": "短剧"},
        {"type_id": "22", "type_name": "AI漫剧"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "瓜子优质"

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
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def parse_video_items(self, html):
        videos = []

        patterns = [
            r'<div\s+class=["\']myui-vodbox-content["\'][^>]*>(.*?)</div>\s*</a>\s*</div>',
            r'<a\s+href=["\']/index\.php/vod/detail/id/(\d+)\.html["\'][^>]*>(.*?)</a>',
        ]

        for pattern in patterns:
            for item in re.finditer(pattern, html, re.S):
                block = item.group(0)

                href_m = re.search(r'href=["\'](/index\.php/vod/detail/id/\d+\.html)["\']', block)
                if not href_m:
                    continue
                href = href_m.group(1)

                vid_match = re.search(r'/index\.php/vod/detail/id/(\d+)\.html', href)
                vid = vid_match.group(1) if vid_match else ""

                if not vid:
                    continue

                title_m = re.search(r'<div\s+class=["\']title["\'][^>]*>([^<]+)</div>', block)
                if not title_m:
                    title_m = re.search(r'alt=["\']([^"\']+)["\']', block)
                if not title_m:
                    title_m = re.search(r'title=["\']([^"\']+)["\']', block)
                name = self.clean(title_m.group(1)) if title_m else ""

                pic_m = re.search(r'src=["\'](https?://[^\s"\']+)["\']', block)
                if not pic_m:
                    pic_m = re.search(r'style=["\']background-image:\s*url\(["\']([^\s"\']+)["\']\)', block)
                pic = pic_m.group(1) if pic_m else ""

                remark_m = re.search(r'<div\s+class=["\']tag\s+text-overflow["\'][^>]*>([^<]+)</div>', block)
                if not remark_m:
                    remark_m = re.search(r'<span\s+class=["\']tag["\'][^>]*>([^<]+)</span>', block)
                remark = self.clean(remark_m.group(1)) if remark_m else ""

                score_m = re.search(r'<div\s+class=["\']score["\'][^>]*>([\d.]+)</div>', block)
                if not score_m:
                    score_m = re.search(r'<span\s+class=["\']score["\'][^>]*>([\d.]+)</span>', block)
                score = score_m.group(1) if score_m else ""

                if name:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": remark,
                        "vod_score": score,
                    })

        seen = set()
        unique_videos = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique_videos.append(v)

        return unique_videos

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result

        videos = self.parse_video_items(html)
        result["list"] = videos[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        page = int(pg) if str(pg).isdigit() else 1

        url = f"{self.BASE_URL}/index.php/vod/type/id/{tid}.html"
        if page > 1:
            url = f"{self.BASE_URL}/index.php/vod/type/id/{tid}/page/{page}.html"

        html = self.getHtml(url)
        if not html:
            return result

        videos = self.parse_video_items(html)

        pagecount = "1"
        page_info_m = re.search(r'页次\s*(\d+)/(\d+)', html)
        if page_info_m:
            pagecount = page_info_m.group(2)
        else:
            page_info_m = re.search(r'<a[^>]*>下一页</a>', html)
            if page_info_m:
                pagecount = str(page + 1)

        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids

        url = f"{self.BASE_URL}/index.php/vod/detail/id/{vid}.html"
        html = self.getHtml(url)
        if not html:
            return result

        vod = {"vod_id": str(vid)}

        title_m = re.search(r'<h1[^>]*>\s*([^<]+)\s*</h1>', html)
        if not title_m:
            title_m = re.search(r'<title>([^<]+)</title>', html)
        if title_m:
            vod["vod_name"] = self.clean(title_m.group(1))
            vod["vod_name"] = re.sub(r'[-_《》【】].*', '', vod["vod_name"])
        else:
            vod["vod_name"] = ""

        pic_m = re.search(r'<img\s+src=["\'](https?://[^\s"\']+)["\'][^>]*', html)
        if not pic_m:
            pic_m = re.search(r'data-original=["\']([^"\']+)["\']', html)
        if not pic_m:
            pic_m = re.search(r'og:image["\']\s+content=["\']([^"\']+)["\']', html)
        vod["vod_pic"] = pic_m.group(1) if pic_m else ""
        if vod["vod_pic"] and not vod["vod_pic"].startswith("http"):
            vod["vod_pic"] = self.BASE_URL + vod["vod_pic"] if vod["vod_pic"].startswith("/") else vod["vod_pic"]

        vod["vod_class"] = ""
        vod["vod_area"] = ""
        vod["vod_year"] = ""
        vod["vod_remarks"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = ""
        vod["vod_lang"] = ""

        type_m = re.search(r'类型[：:]\s*([^<]+)', html)
        if not type_m:
            type_m = re.search(r'vod_class["\']\s*:\s*["\']([^"\']+)["\']', html)
        if type_m:
            vod["vod_class"] = self.clean(type_m.group(1))

        area_m = re.search(r'地区[：:]\s*([^<]+)', html)
        if area_m:
            vod["vod_area"] = self.clean(area_m.group(1))

        year_m = re.search(r'年份[：:]\s*([^<]+)', html)
        if year_m:
            vod["vod_year"] = self.clean(year_m.group(1))

        lang_m = re.search(r'语言[：:]\s*([^<]+)', html)
        if lang_m:
            vod["vod_lang"] = self.clean(lang_m.group(1))

        status_m = re.search(r'状态[：:]\s*([^<]+)', html)
        if status_m:
            vod["vod_remarks"] = self.clean(status_m.group(1))

        actor_m = re.search(r'主演[：:]\s*([^<]+)', html)
        if not actor_m:
            actor_m = re.search(r'vod_actor["\']\s*:\s*["\']([^"\']+)["\']', html)
        if actor_m:
            vod["vod_actor"] = self.clean(actor_m.group(1))

        director_m = re.search(r'导演[：:]\s*([^<]+)', html)
        if not director_m:
            director_m = re.search(r'vod_director["\']\s*:\s*["\']([^"\']+)["\']', html)
        if director_m:
            vod["vod_director"] = self.clean(director_m.group(1))

        desc_m = re.search(r'<div\s+class=["\'][^"\']*info-intro[^"\']*["\'][^>]*>\s*简介[：:]\s*<p[^>]*>([^<]+)</p>', html)
        if not desc_m:
            desc_m = re.search(r'简介[：:]\s*<p[^>]*>([^<]+)</p>', html)
        if not desc_m:
            desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html)
        if desc_m:
            desc_text = self.clean(desc_m.group(1))
            vod["vod_content"] = self.WECHAT_INFO + "\n" + desc_text
        else:
            vod["vod_content"] = self.WECHAT_INFO

        play_groups = {}
        link_pattern = r'<a[^>]*href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]+)</a>'
        for item in re.finditer(link_pattern, html):
            href = item.group(1)
            episode_name = self.clean(item.group(2))
            full_url = self.BASE_URL + href
            sid_match = re.search(r'/sid/(\d+)', href)
            sid = sid_match.group(1) if sid_match else "1"
            if f"线路{sid}" not in play_groups:
                play_groups[f"线路{sid}"] = []
            play_groups[f"线路{sid}"].append(f"{episode_name}${full_url}")

        if not play_groups:
            link_pattern = r'<a[^>]*href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>'
            for item in re.finditer(link_pattern, html):
                href = item.group(1)
                full_url = self.BASE_URL + href
                sid_match = re.search(r'/sid/(\d+)', href)
                sid = sid_match.group(1) if sid_match else "1"
                episode_match = re.search(r'/nid/(\d+)\.html', href)
                ep_num = episode_match.group(1) if episode_match else "1"
                if f"线路{sid}" not in play_groups:
                    play_groups[f"线路{sid}"] = []
                play_groups[f"线路{sid}"].append(f"第{ep_num}集${full_url}")

        if play_groups:
            vod["vod_play_from"] = "$$$".join(play_groups.keys())
            vod["vod_play_url"] = "$$$".join(["#".join(eps) for eps in play_groups.values()])
        else:
            vod["vod_play_from"] = "云播资源"
            vod["vod_play_url"] = f"播放${self.BASE_URL}/index.php/vod/play/id/{vid}/sid/1/nid/1.html"

        cat_name = ""
        for c in self.CATEGORIES:
            if f'/type/id/{c["type_id"]}' in html:
                cat_name = c["type_name"]
                break
        vod["type_id"] = "1"
        vod["type_name"] = cat_name or "影视"

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

        url = f"{self.BASE_URL}/index.php/vod/search.html?wd={urllib.parse.quote(key)}"
        if page > 1:
            url = f"{self.BASE_URL}/index.php/vod/search/wd/{urllib.parse.quote(key)}/page/{page}.html"

        html = self.getHtml(url)
        if not html:
            return result

        videos = self.parse_video_items(html)

        pagecount = "1"
        page_info_m = re.search(r'页次\s*(\d+)/(\d+)', html)
        if not page_info_m:
            page_info_m = re.search(r'<a[^>]*>下一页</a>', html)
            if page_info_m:
                pagecount = str(page + 1)

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
            play_url = f"{self.BASE_URL}{play_url}" if play_url.startswith("/") else ""

        if play_url:
            html = self.getHtml(play_url)
            if html:
                player_m = re.search(r'player_aaaa=(\{.*?\})</script>', html, re.S)
                if player_m:
                    try:
                        player_data = json.loads(player_m.group(1))
                        video_url = player_data.get("url", "")
                        if video_url:
                            video_url = video_url.replace("\\/", "/")
                            if video_url.startswith("//"):
                                video_url = "https:" + video_url
                            return {"url": video_url, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}
                    except Exception:
                        pass

                url_match = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', html)
                if url_match:
                    video_url = url_match.group(1).replace("\\/", "/")
                    if video_url.startswith("//"):
                        video_url = "https:" + video_url
                    return {"url": video_url, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}

                m3u8_match = re.search(r'(https?://[^\s"\'\\]+?\.m3u8)', html)
                if m3u8_match:
                    video_url = m3u8_match.group(1).replace("\\/", "/")
                    if video_url.startswith("//"):
                        video_url = "https:" + video_url
                    return {"url": video_url, "parse": "0", "header": "", "playUrl": "", "subtitle": ""}

        return {"url": play_url, "parse": "1", "header": "", "playUrl": "", "subtitle": ""}