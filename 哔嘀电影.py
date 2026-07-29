# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
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
    BASE_URL = "https://fuddj.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": "dianying", "type_name": "电影", "url": "/type/dianying.html"},
        {"type_id": "lianxuju", "type_name": "电视剧", "url": "/type/lianxuju.html"},
        {"type_id": "dongman", "type_name": "动漫", "url": "/type/dongman.html"},
        {"type_id": "zongyi", "type_name": "综艺", "url": "/type/zongyi.html"},
        {"type_id": "duanju", "type_name": "短剧", "url": "/show/duanju-----------.html"},
    ]

    _homepage_cache = None

    def init(self, extend=""):
        pass

    def getName(self):
        return "哔嘀电影"

    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
            except Exception:
                pass
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": self.BASE_URL + "/"
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
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

    def _extract_nested_tag_content(self, html, start_pos, tag_name="div"):
        depth = 1
        pos = start_pos
        open_pat = "<" + tag_name + r'\b'
        close_pat = "</" + tag_name + r"\s*>"
        while pos < len(html) and depth > 0:
            next_open = re.search(open_pat, html[pos:], re.I)
            next_close = re.search(close_pat, html[pos:], re.I)
            if not next_close:
                break
            close_abs = pos + next_close.start()
            if next_open and (pos + next_open.start()) < close_abs:
                depth += 1
                pos = pos + next_open.end()
            else:
                depth -= 1
                if depth == 0:
                    return html[start_pos:close_abs]
                pos = close_abs + len(next_close.group())
        return ""

    def _find_video_container(self, html):
        if not html:
            return html
        class_candidates = [
            "vodlist", "search_list", "video_list", "movie-list",
            "video-list", "list-content", "balist", "content-list",
            "vod_list", "videoList", "dianying-list", "search-list",
            "content", "list", "main-content", "wrap-content",
            "page-content", "body-content", "main", "vod", "video",
        ]
        for tag in ("div", "ul", "ol"):
            for kw in class_candidates:
                pattern = r'<' + tag + r'\b[^>]*class\s*=\s*["\']([^"\']*' + re.escape(kw) + r'[^"\']*)["\'][^>]*>'
                for m in re.finditer(pattern, html, re.I):
                    inner = self._extract_nested_tag_content(html, m.end(), tag)
                    if inner and len(re.findall(r'href="/subject/', inner)) >= 2:
                        return inner
        main_m = re.search(r'<main\b[^>]*>', html, re.I)
        if main_m:
            inner = self._extract_nested_tag_content(html, main_m.end(), "main")
            if inner and len(re.findall(r'href="/subject/', inner)) >= 2:
                return inner
        return html

    def _extract_vod_items(self, html, container_only=True):
        items = []
        seen = set()

        search_area = self._find_video_container(html) if container_only else html

        skip_names = ["上一页", "下一页", "末页"]
        id_pattern = r'href="/subject/([^"]+)\.html"'
        for m in re.finditer(id_pattern, search_area):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            start = max(0, m.start() - 500)
            end = min(len(search_area), m.end() + 200)
            block = search_area[start:end]

            name = ""
            title_m = re.search(r'title="([^"]+)"', block)
            if title_m:
                name = self.clean(title_m.group(1))
            if not name:
                name = vid
            if name in skip_names:
                continue

            pic = ""
            pic_m = re.search(r'background-image:\s*url\(["\']?([^"\'\)]+)["\']?\)', block)
            if pic_m:
                pic = pic_m.group(1)
            if not pic:
                pic_m = re.search(r'data-original="([^"]+)"', block)
                if pic_m:
                    pic = pic_m.group(1)

            remarks = ""
            rem_m = re.search(r'<span[^>]*class="[^"]*pic_text[^"]*"[^>]*>([^<]+)</span>', block)
            if rem_m:
                remarks = self.clean(rem_m.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
            })

        if not items and container_only:
            items = self._extract_vod_items(html, container_only=False)

        return items

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result

        videos = self._extract_vod_items(html)
        self._homepage_cache = videos
        result["list"] = videos
        return result

    def _extract_page_count(self, html):
        if not html:
            return 1
        page_links = re.findall(r'href="[^"]*?(\d+)---\.html"[^>]*>', html)
        if page_links:
            return max(int(p) for p in page_links)
        page_nums = re.findall(r'class="[^"]*page_num[^"]*"[^>]*>\s*(\d+)', html)
        if page_nums:
            return max(int(p) for p in page_nums)
        return 1

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
                base_url = cat['url']
                if '/show/' in base_url:
                    slug = base_url.replace('-----------', '--------').replace('.html', '')
                    url = f"{self.BASE_URL}{slug}{pg}---.html"
                else:
                    slug = base_url.replace('.html', '')
                    url = f"{self.BASE_URL}{slug}/page/{pg}.html"

            html = self.getHtml(url)
            if html and len(html) > 1000:
                videos = self._extract_vod_items(html, container_only=True)

                if not videos:
                    videos = self._extract_vod_items(html, container_only=False)

                if videos:
                    page_count = self._extract_page_count(html)
                    if page_count < int(pg) + 1:
                        page_count = int(pg) + 1
                    result["list"] = videos
                    result["pagecount"] = str(page_count)
                    result["total"] = str(len(videos))
                    return result

            return result
        except Exception:
            return result

    def _extract_info_field(self, html, label):
        span_pat = r'<span[^>]*>' + re.escape(label) + r'[：:]</span>\s*((?:<a[^>]*>[^<]*</a>&nbsp;?)+)'
        m = re.search(span_pat, html, re.S)
        if m:
            vals = re.findall(r'<a[^>]*>([^<]*)</a>', m.group(1))
            if vals:
                return ", ".join(self.clean(v) for v in vals if self.clean(v))
        span_pat2 = r'<span[^>]*>' + re.escape(label) + r'[：:]</span>\s*<span[^>]*>([^<]*)</span>'
        m2 = re.search(span_pat2, html, re.S)
        if m2:
            return self.clean(m2.group(1))
        simple_pat = r'<span[^>]*>' + re.escape(label) + r'[：:]</span>\s*<a[^>]*>([^<]*)</a>'
        m3 = re.search(simple_pat, html, re.S)
        if m3:
            return self.clean(m3.group(1))
        text_pat = r'<span[^>]*>' + re.escape(label) + r'[：:]</span>\s*([^<]+)'
        m4 = re.search(text_pat, html, re.S)
        if m4:
            return self.clean(m4.group(1))
        return ""

    def _extract_desc_field(self, html):
        pattern = r'简介[：:]\s*</span>\s*([^<]+)'
        m = re.search(pattern, html, re.S)
        if m:
            return self.clean(m.group(1))
        return ""

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids

        html = self.getHtml(f"{self.BASE_URL}/subject/{vid}.html")
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
                name = re.sub(r'_哔嘀电影.*', '', name).strip()
                name = re.sub(r'[﹛﹜{}]', '', name).strip()
        vod["vod_name"] = name if name else vid

        pic = ""
        pic_m = re.search(r'property="og:image"[^>]*content="([^"]+)"', html)
        if not pic_m:
            pic_m = re.search(r'data-original="([^"]+)"', html)
        if not pic_m:
            pic_m = re.search(r'background-image:\s*url\(["\']?([^"\'\)]+)["\']?\)', html)
        if pic_m:
            pic = pic_m.group(1)
        vod["vod_pic"] = pic

        vod["vod_class"] = self._extract_info_field(html, "类型")
        vod["vod_area"] = self._extract_info_field(html, "地区")
        vod["vod_year"] = self._extract_info_field(html, "年份")
        vod["vod_actor"] = self._extract_info_field(html, "主演")
        vod["vod_director"] = self._extract_info_field(html, "导演")
        vod["vod_lang"] = self._extract_info_field(html, "语言")
        vod["vod_remarks"] = self._extract_info_field(html, "状态")

        if not vod["vod_year"]:
            year_m = re.search(r'<a[^>]*href="/show/[^"]+-(\d{4})\.html"', html)
            if year_m:
                vod["vod_year"] = year_m.group(1)

        vod["vod_content"] = self._extract_desc_field(html)

        play_groups = []
        seen_eps = set()

        source_tabs = re.findall(r'<div[^>]*class="[^"]*play_source_tab[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        playlists = re.findall(r'<ul[^>]*class="[^"]*content_playlist[^"]*"[^>]*>(.*?)</ul>', html, re.DOTALL)

        if source_tabs and playlists:
            for si, (tab_html, list_html) in enumerate(zip(source_tabs, playlists)):
                source_name = f"线路{si+1}"
                tab_names = re.findall(r'<a[^>]*>([^<]+)</a>', tab_html)
                if tab_names:
                    source_name = self.clean(tab_names[0])
                else:
                    source_name = f"线路{si+1}"

                eps = re.findall(r'<a[^>]*href="/start/([^"]+)"[^>]*>([^<]*)</a>', list_html)
                for ep_url, ep_name in eps:
                    if ep_url in seen_eps:
                        continue
                    seen_eps.add(ep_url)
                    ep_name_clean = self.clean(ep_name) if ep_name.strip() else f"集{len(seen_eps)}"
                    full_url = f"{self.BASE_URL}/start/{ep_url}"
                    play_groups.append(f"{ep_name_clean}${full_url}")

        if not play_groups:
            for m in re.finditer(r'<a[^>]*href="/start/([^"]+)"[^>]*>([^<]*)</a>', html):
                ep_url = m.group(1)
                ep_name = self.clean(m.group(2)) if m.group(2).strip() else f"集{len(seen_eps)+1}"
                if ep_url in seen_eps:
                    continue
                seen_eps.add(ep_url)
                full_url = f"{self.BASE_URL}/start/{ep_url}"
                play_groups.append(f"{ep_name}${full_url}")

        vod["vod_play_from"] = "高清线路"
        vod["vod_play_url"] = "#".join(play_groups) if play_groups else f"播放${self.BASE_URL}/start/{vid}-1-1.html"
        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            encoded_key = urllib.parse.quote(key)
            search_url = f"{self.BASE_URL}/vod/search/wd/{encoded_key}.html"

            html = self.getHtml(search_url)
            if html and len(html) > 500 and "404" not in html[:500]:
                videos = self._extract_vod_items(html, container_only=True)
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

    def _extract_player_data(self, html):
        pd_idx = html.find('player_data=')
        if pd_idx < 0:
            pd_idx = html.find('player_data =')
        if pd_idx < 0:
            return None

        start = html.find('{', pd_idx)
        if start < 0:
            return None

        brace_count = 0
        end = -1
        for i in range(start, len(html)):
            if html[i] == '{':
                brace_count += 1
            elif html[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        if end < 0:
            return None

        return html[start:end]

    def _try_get_video_url(self, html):
        try:
            pd_str = self._extract_player_data(html)
            if not pd_str:
                return None

            url_m = re.search(r'"url"\s*:\s*"([^"]*)"', pd_str)
            from_m = re.search(r'"from"\s*:\s*"([^"]*)"', pd_str)
            encrypt_m = re.search(r'"encrypt"\s*:\s*"?(\d+)"?', pd_str)

            if not url_m:
                return None

            video_url = url_m.group(1)
            from_val = from_m.group(1) if from_m else ""
            encrypt_val = encrypt_m.group(1) if encrypt_m else "0"

            cache_val = ""
            if "&cache=" in video_url:
                video_url, cache_val = video_url.split("&cache=", 1)

            decoded_url = ""
            if encrypt_val == "1":
                decoded_url = urllib.parse.unquote(video_url)
            elif encrypt_val == "2":
                try:
                    decoded = base64.b64decode(video_url)
                    decoded_url = urllib.parse.unquote(decoded.decode('utf-8', errors='replace'))
                except Exception:
                    pass
            else:
                clean = video_url.replace('yMcA', '')
                padded = clean
                missing = len(padded) % 4
                if missing:
                    padded += '=' * (4 - missing)
                try:
                    decoded = base64.b64decode(padded)
                    decoded_url = decoded.decode('utf-8', errors='replace')
                except Exception:
                    pass

                if not decoded_url or not (".m3u8" in decoded_url or ".mp4" in decoded_url):
                    try:
                        raw_bytes = base64.b64decode(video_url)
                        decoded_url = raw_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        pass

            if cache_val and decoded_url:
                decoded_url += "&cache=" + cache_val

            if decoded_url and (".m3u8" in decoded_url or ".mp4" in decoded_url or decoded_url.startswith("http")):
                return decoded_url

            wz_cache = ""
            cache_m = re.search(r'"cache"\s*:\s*"([^"]*)"', html)
            if cache_m:
                wz_cache = cache_m.group(1)
            if not wz_cache:
                cache_m = re.search(r'wz\.cache\s*=\s*"([^"]*)"', html)
                if cache_m:
                    wz_cache = cache_m.group(1)

            if wz_cache and from_val:
                iframe_url = f"{wz_cache}p/d.html?p={from_val}&u={video_url}"
                if cache_val:
                    iframe_url += "&cache=" + cache_val
                return iframe_url

            return None
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
            direct_url = self._try_get_video_url(play_html)
            if direct_url:
                if direct_url.startswith("//"):
                    direct_url = "https:" + direct_url
                is_direct = direct_url.endswith(".m3u8") or direct_url.endswith(".mp4")
                return {
                    "url": direct_url,
                    "parse": "0" if is_direct else "1",
                    "header": json.dumps(play_headers),
                    "playUrl": "",
                    "subtitle": ""
                }

        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": ""
        }

    def __jsEvalReturn(self):
        return {"proxy": None}
