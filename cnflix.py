# -*- coding: utf-8 -*-

import re
import json
import base64
import urllib.parse
import urllib.request
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
    BASE_URL = "https://www.cnflix.tv"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": "movies", "type_name": "电影", "url": "/type/movies/"},
        {"type_id": "tv", "type_name": "电视剧", "url": "/type/tv/"},
        {"type_id": "anime", "type_name": "动漫", "url": "/type/anime/"},
        {"type_id": "varietyshow", "type_name": "综艺", "url": "/type/varietyshow/"},
        {"type_id": "shortdrama", "type_name": "短剧", "url": "/type/shortdrama/"},
        {"type_id": "documentaries", "type_name": "纪录片", "url": "/type/documentaries/"},
        {"type_id": "krdrama", "type_name": "韩剧", "url": "/type/krdrama/"},
    ]

    _w_data = "5ru45Yu06LyB5LqR5rCgaG9uZ2d1b193ZWNoYXRfMjAyNuabtOWkmuS8mOi0qOi1hOa6kOWwveWcqOa6kOWKm+aNkOi1oOeJiA=="
    _w_key = "hongguo_wechat_2026"

    def init(self, extend=""):
        pass

    def getName(self):
        return "CNFLIX"

    def _get_wechat_info(self):
        try:
            decoded = base64.b64decode(self._w_data).decode("utf-8")
            key_idx = decoded.find(self._w_key)
            if key_idx > 0:
                encrypted_part = decoded[:key_idx]
                donate_part = decoded[key_idx + len(self._w_key):]
                decrypted = []
                for i, c in enumerate(encrypted_part):
                    key_char = self._w_key[i % len(self._w_key)]
                    decrypted.append(chr(ord(c) ^ ord(key_char)))
                wechat_name = ''.join(decrypted)
                return f"微信公众号{wechat_name}，{donate_part}"
        except Exception:
            pass
        return ""

    def getHtml(self, url):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
                "Referer": self.BASE_URL + "/",
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                for enc in ["utf-8", "gbk", "gb2312"]:
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

    def _getImgSrc(self, img_url):
        if not img_url:
            return ""
        if img_url.startswith("//"):
            return "https:" + img_url
        if img_url.startswith("/"):
            return self.BASE_URL + img_url
        if img_url.startswith("http"):
            return img_url
        return self.BASE_URL + "/" + img_url

    def _extract_vod_items(self, html):
        items = []
        seen = set()

        pattern = (
            r'<a[^>]*class="[^"]*public-list-exp[^"]*"[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>'
            r'.*?data-original="([^"]*)"'
        )

        for m in re.finditer(pattern, html, re.S):
            href = m.group(1)
            title = self.clean(m.group(2))
            img = m.group(3)

            vid = ""
            id_m = re.search(r'/detail/(\d+)/', href)
            if id_m:
                vid = id_m.group(1)
            else:
                id_m = re.search(r'/detail/(\d+)', href)
                if id_m:
                    vid = id_m.group(1)

            if not vid or vid in seen:
                continue
            seen.add(vid)

            pic = self._getImgSrc(img)

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        return items

    def _extract_search_items(self, html):
        items = []
        seen = set()

        # Search page structure:
        # <a href="/detail/{id}/" target="_blank" class="vod-link br b-b">
        #   <img src="/upload/vod/..." class="vod-img ..." />
        #   ... other spans ...
        #   <div class="vod-center">
        #     <span class="vod-title" title="...">...</span>
        #   </div>
        # </a>

        # Find all /detail/ links that have vod-link class (属性顺序不确定)
        # Use a simpler approach: find href first, then verify class
        a_pattern = r'<a[^>]*href="([^"]*/detail/(\d+)/)"[^>]*class="[^"]*vod-link[^"]*"[^>]*>(.*?)</a>'

        for m in re.finditer(a_pattern, html, re.S):
            href = m.group(1)
            vid = m.group(2)
            inner_content = m.group(3)

            if not vid or vid in seen:
                continue
            seen.add(vid)

            # Extract image src
            img = ""
            img_m = re.search(r'<img[^>]*src="([^"]*)"[^>]*class="[^"]*vod-img[^"]*"', inner_content)
            if img_m:
                img = img_m.group(1)

            # Extract title from span title attribute
            title = ""
            title_m = re.search(r'<span[^>]*class="[^"]*vod-title[^"]*"[^>]*title="([^"]*)"', inner_content)
            if title_m:
                title = self.clean(title_m.group(1))

            if not title:
                continue

            pic = self._getImgSrc(img)

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        return items

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result

        videos = self._extract_vod_items(html)
        result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            cat = None
            for c in self.CATEGORIES:
                if c["type_id"] == str(tid):
                    cat = c
                    break
            if not cat:
                return result

            url = f"{self.BASE_URL}{cat['url']}"
            if int(pg) > 1:
                url = f"{self.BASE_URL}{cat['url']}page/{pg}.html"

            html = self.getHtml(url)
            if html and len(html) > 1000:
                videos = self._extract_vod_items(html)
                if videos:
                    result["list"] = videos
                    result["pagecount"] = str(int(pg) + 1)
                    result["total"] = str(len(videos))
                    return result

            return result
        except Exception:
            return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids

        html = self.getHtml(f"{self.BASE_URL}/detail/{vid}/")
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": vid}

        name = ""
        h2_m = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.S)
        if h2_m:
            name = self.clean(re.sub(r'<[^>]+>', '', h2_m.group(1)))
        if not name:
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if title_m:
                name = self.clean(title_m.group(1))
                name = re.sub(r'\[.*?\].*$', '', name).strip()
                name = re.sub(r'_.*$', '', name).strip()
        vod["vod_name"] = name if name else vid

        pic = ""
        og_img = re.search(r'property="og:image"[^>]*content="([^"]+)"', html)
        if og_img:
            pic = og_img.group(1)
        else:
            pic_m = re.search(r'data-original="([^"]*)"', html)
            if pic_m:
                pic = self._getImgSrc(pic_m.group(1))
        vod["vod_pic"] = pic

        vod_content = ""
        desc_m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if desc_m:
            vod_content = self.clean(desc_m.group(1))
            vod_content = re.sub(r'^《.*?》剧情介绍[：:]\s*', '', vod_content)
        vod["vod_content"] = vod_content

        vod_class = ""
        class_m = re.search(r'<meta[^>]*property="og:video:tag"[^>]*content="([^"]*)"', html)
        if class_m:
            vod_class = self.clean(class_m.group(1))
        if not vod_class:
            class_m2 = re.search(r'类型[：:]</span>\s*<span[^>]*>([^<]*)</span>', html)
            if class_m2:
                vod_class = self.clean(class_m2.group(1))
        vod["vod_class"] = vod_class

        vod_year = ""
        year_m = re.search(r'(\d{4})', html[:5000])
        if year_m:
            vod_year = year_m.group(1)
        vod["vod_year"] = vod_year

        vod_area = ""
        area_m = re.search(r'地区[：:]</span>\s*<span[^>]*>([^<]*)</span>', html)
        if area_m:
            vod_area = self.clean(area_m.group(1))
        vod["vod_area"] = vod_area

        vod_actor = ""
        actor_m = re.search(r'主演[：:]</span>\s*<span[^>]*>(.*?)</span>', html, re.S)
        if actor_m:
            actor_links = re.findall(r'<a[^>]*>([^<]*)</a>', actor_m.group(1))
            if actor_links:
                vod_actor = ", ".join(self.clean(a) for a in actor_links if self.clean(a))
            else:
                vod_actor = self.clean(actor_m.group(1))
        vod["vod_actor"] = vod_actor

        vod_director = ""
        director_m = re.search(r'导演[：:]</span>\s*<span[^>]*>(.*?)</span>', html, re.S)
        if director_m:
            director_links = re.findall(r'<a[^>]*>([^<]*)</a>', director_m.group(1))
            if director_links:
                vod_director = ", ".join(self.clean(a) for a in director_links if self.clean(a))
            else:
                vod_director = self.clean(director_m.group(1))
        vod["vod_director"] = vod_director

        play_groups = []
        seen_eps = set()

        source_tabs = re.findall(r'<div[^>]*class="[^"]*play_source_tab[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        playlists = re.findall(r'<ul[^>]*class="[^"]*content_playlist[^"]*"[^>]*>(.*?)</ul>', html, re.DOTALL)

        if source_tabs and playlists:
            for si, (tab_html, list_html) in enumerate(zip(source_tabs, playlists)):
                source_name = f"线路{si + 1}"
                tab_names = re.findall(r'<a[^>]*>([^<]+)</a>', tab_html)
                if tab_names:
                    source_name = self.clean(tab_names[0])

                eps = re.findall(r'<a[^>]*href="(/play/([^"]+))"[^>]*>([^<]*)</a>', list_html)
                for ep_path, ep_id, ep_name in eps:
                    if ep_id in seen_eps:
                        continue
                    seen_eps.add(ep_id)
                    ep_name_clean = self.clean(ep_name) if ep_name.strip() else f"集{len(seen_eps)}"
                    full_url = f"{self.BASE_URL}{ep_path}"
                    play_groups.append(f"{ep_name_clean}${full_url}")

        if not play_groups:
            for m in re.finditer(r'<a[^>]*href="(/play/([^"]+))"[^>]*>([^<]*)</a>', html):
                ep_path = m.group(1)
                ep_id = m.group(2)
                ep_name = self.clean(m.group(3)) if m.group(3).strip() else f"集{len(seen_eps) + 1}"
                if ep_id in seen_eps:
                    continue
                seen_eps.add(ep_id)
                full_url = f"{self.BASE_URL}{ep_path}"
                play_groups.append(f"{ep_name}${full_url}")

        vod["vod_play_from"] = "高清线路"
        vod["vod_play_url"] = "#".join(play_groups) if play_groups else f"播放${self.BASE_URL}/play/{vid}-1-1/"

        wechat_info = self._get_wechat_info()
        if vod_content:
            vod["vod_content"] = f"{vod_content}\n\n{wechat_info}"
        else:
            vod["vod_content"] = wechat_info

        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            encoded_key = urllib.parse.quote(key)
            search_url = f"{self.BASE_URL}/vodsearch/-------------.html?wd={encoded_key}"

            html = self.getHtml(search_url)
            if html and len(html) > 500:
                videos = self._extract_search_items(html)
                if videos:
                    kw_lower = key.lower()
                    filtered = [v for v in videos if kw_lower in v.get("vod_name", "").lower()]
                    result["list"] = filtered if filtered else videos
                    result["pagecount"] = "1"
                    result["total"] = str(len(result["list"]))
                    return result

            return result
        except Exception:
            return result

    def _decode_video_url(self, encoded_url):
        try:
            b64_decoded = base64.b64decode(encoded_url)
            url_decoded = urllib.parse.unquote(b64_decoded.decode("utf-8", errors="replace"))
            return url_decoded
        except Exception:
            return None

    def playerContent(self, flag, id, vipFlags):
        play_url = id
        if not play_url.startswith("http"):
            play_url = self.BASE_URL + "/" + play_url.lstrip("/")

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        play_html = self.getHtml(play_url)

        if play_html:
            pa_m = re.search(r'var\s+player_aaaa\s*=\s*({.*?});', play_html, re.S)
            if pa_m:
                pa_str = pa_m.group(1)

                encrypt_m = re.search(r'"encrypt"\s*:\s*(\d+)', pa_str)
                encrypt_val = int(encrypt_m.group(1)) if encrypt_m else 0

                if encrypt_val == 2:
                    url_m = re.search(r'"url"\s*:\s*"([^"]*)"', pa_str)
                    if url_m:
                        encoded_url = url_m.group(1)
                        decoded_url = self._decode_video_url(encoded_url)
                        if decoded_url and (".m3u8" in decoded_url or ".mp4" in decoded_url):
                            return {
                                "url": decoded_url,
                                "parse": "0",
                                "header": json.dumps(play_headers),
                                "playUrl": "",
                                "subtitle": "",
                            }

                play_url_m = re.search(r'"vod_play_url"\s*:\s*"([^"]*)"', pa_str)
                if play_url_m:
                    play_url_str = play_url_m.group(1)
                    if "$" in play_url_str:
                        ep_part = play_url_str.split("$", 1)[1]
                        if "#" in ep_part:
                            ep_part = ep_part.split("#")[0]
                        decoded_url = self._decode_video_url(ep_part)
                        if decoded_url and (".m3u8" in decoded_url or ".mp4" in decoded_url):
                            return {
                                "url": decoded_url,
                                "parse": "0",
                                "header": json.dumps(play_headers),
                                "playUrl": "",
                                "subtitle": "",
                            }

        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    def __jsEvalReturn(self):
        return {"proxy": None}
