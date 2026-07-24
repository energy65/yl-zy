#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import io
import urllib.request
import urllib.parse
import html as html_mod
import base64

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
    BASE_URL = "https://www.nivod.vip"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ENCRYPT_KEY = b"nivod_spider_key_2026"
    
    _w_key = b"wechat_2026_key"
    _w_data = [0x92, 0xdb, 0xcd, 0x8c, 0xde, 0xd5, 0xba, 0xb7, 0x9c, 0xd6, 0x8a, 0xc8, 0x8e, 0xea, 0xce, 0x55,
               0x83, 0xd9, 0xf8, 0x84, 0xfe, 0xc4, 0xda, 0x8d, 0x9d, 0xd2, 0xe4, 0xdd, 0x83, 0xc8, 0xf0, 0x47,
               0x8c, 0xd4, 0xed, 0x92, 0xc4, 0x86, 0xd5, 0x96, 0xac, 0xbb, 0xd7, 0xfd, 0x91, 0xc3, 0xcd, 0x8b,
               0xdd, 0xe5, 0x92, 0xe5, 0xa2, 0xd5, 0x82, 0x8b, 0xba, 0xf7, 0xcd, 0x9f, 0xcd, 0xf5, 0x86, 0xe2,
               0xfa, 0x92, 0xd2, 0xa2, 0xd8, 0x87, 0x96, 0xb8, 0xe2, 0xed]

    CATEGORIES = [
        {"type_id": "1", "type_name": "电影", "url": "https://www.nivod.vip/t/1/"},
        {"type_id": "2", "type_name": "剧集", "url": "https://www.nivod.vip/t/2/"},
        {"type_id": "3", "type_name": "综艺", "url": "https://www.nivod.vip/t/3/"},
        {"type_id": "4", "type_name": "动漫", "url": "https://www.nivod.vip/t/4/"},
        {"type_id": "5", "type_name": "短剧", "url": "https://www.nivod.vip/t/2/"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "泥视频"

    def _get_wechat_info(self):
        result = bytearray()
        for i, b in enumerate(self._w_data):
            key_byte = self._w_key[i % len(self._w_key)]
            result.append(b ^ key_byte)
        return result.decode('utf-8')

    def _encrypt_url(self, url):
        try:
            url_bytes = url.encode('utf-8')
            padded = url_bytes + b"\x00" * (16 - len(url_bytes) % 16) if len(url_bytes) % 16 != 0 else url_bytes
            encrypted = b""
            key = self.ENCRYPT_KEY[:16]
            for i in range(0, len(padded), 16):
                block = padded[i:i+16]
                encrypted_block = bytes(a ^ b for a, b in zip(block, key))
                encrypted += encrypted_block
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception:
            return url

    def _decrypt_url(self, encrypted_str):
        try:
            encrypted = base64.b64decode(encrypted_str)
            key = self.ENCRYPT_KEY[:16]
            decrypted = b""
            for i in range(0, len(encrypted), 16):
                block = encrypted[i:i+16]
                decrypted_block = bytes(a ^ b for a, b in zip(block, key))
                decrypted += decrypted_block
            return decrypted.rstrip(b"\x00").decode('utf-8')
        except Exception:
            return encrypted_str

    def getHtml(self, url):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": self.BASE_URL + "/"
            })
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = resp.read()
                content_encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in content_encoding:
                    try:
                        data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                    except Exception:
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            pass
                return data.decode("utf-8", errors="replace")
        except Exception as e:
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

        for item in re.finditer(r'<a[^>]*href="(/nivod/\d+/)"[^>]*>(.*?)</a>', html, re.S):
            href = item.group(1)
            vid = re.search(r'nivod/(\d+)/', href)
            if not vid:
                continue
            vid = vid.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            block = item.group(2)
            name = ""
            title_m = re.search(r'title="([^"]+)"', item.group(0))
            if title_m:
                name = self.clean(title_m.group(1))
            if not name:
                name = self.clean(re.sub(r'<[^>]+>', '', block))
            if not name or len(name) < 2:
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)
            if not pic:
                og_m = re.search(r'og:image" content="([^"]+)"', html)
                if og_m:
                    pic = og_m.group(1)

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": "",
                "vod_remarks": "",
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
        url = cat["url"]
        if page > 1:
            url = url.rstrip('/') + f"/{page}/"

        html = self.getHtml(url)
        if not html:
            return result

        videos = []
        seen = set()

        for item in re.finditer(r'<a[^>]*href="(/nivod/\d+/)"[^>]*>(.*?)</a>', html, re.S):
            href = item.group(1)
            vid = re.search(r'nivod/(\d+)/', href)
            if not vid:
                continue
            vid = vid.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            block = item.group(2)
            name = ""
            title_m = re.search(r'title="([^"]+)"', item.group(0))
            if title_m:
                name = self.clean(title_m.group(1))
            if not name:
                name = self.clean(re.sub(r'<[^>]+>', '', block))
            if not name or len(name) < 2:
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": "",
                "vod_remarks": "",
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
        url = f"{self.BASE_URL}/nivod/{vid}/"
        html = self.getHtml(url)
        if not html:
            return result

        vod = {"vod_id": str(vid)}

        hm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        vod["vod_name"] = self.clean(hm.group(1)) if hm else ""
        
        if not vod["vod_name"]:
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if title_m:
                title_text = self.clean(title_m.group(1))
                title_text = re.sub(r'《([^》]+)》.*', r'\1', title_text)
                title_text = re.sub(r'[\s\._-]+在线观看.*', '', title_text)
                title_text = re.sub(r'[\s\._-]+全集.*', '', title_text)
                title_text = re.sub(r'详情介绍.*', '', title_text)
                vod["vod_name"] = title_text

        do_m = re.search(r'data-original="(https?://[^"]+)"', html)
        if do_m:
            vod["vod_pic"] = do_m.group(1)
        else:
            og_m = re.search(r'og:image" content="([^"]+)"', html)
            if og_m:
                vod["vod_pic"] = og_m.group(1)
            else:
                vod["vod_pic"] = ""

        vod["vod_class"] = ""
        vod["vod_area"] = ""
        vod["vod_year"] = ""
        vod["vod_remarks"] = ""
        vod["vod_actor"] = ""
        vod["vod_director"] = ""
        vod["vod_lang"] = ""

        info_items = re.findall(r'<div class="module-info-item">(.*?)</div>', html, re.S)
        for item in info_items:
            if '上映：' in item:
                year_match = re.search(r'(\d{4})', item)
                if year_match:
                    vod["vod_year"] = year_match.group(1)
            elif '更新：' in item:
                vod["vod_remarks"] = self.clean(re.sub(r'<[^>]+>', '', item).replace('更新：', ''))
            elif '集数：' in item:
                vod["vod_remarks"] = self.clean(re.sub(r'<[^>]+>', '', item).replace('集数：', ''))

        tag_links = re.findall(r'<a href="/k/\d+-(.+?)/">([^<]+)</a>', html)
        for link_part, text in tag_links:
            if '-----------' in link_part and '20' in text:
                vod["vod_year"] = text
            elif '----------' in link_part and len(text) <= 4:
                vod["vod_area"] = text
            elif '--------' in link_part:
                if vod["vod_class"]:
                    vod["vod_class"] += "/" + text
                else:
                    vod["vod_class"] = text

        actor_links = re.findall(r'<a href="/s/[^"]+">([^<]+)</a>', html)
        actors = []
        directors = []
        for link_text in actor_links:
            if len(link_text) > 1 and len(link_text) < 10:
                if vod["vod_director"] == "" and len(directors) < 3:
                    directors.append(link_text)
                elif len(actors) < 5:
                    actors.append(link_text)
        vod["vod_director"] = "/".join(directors)
        vod["vod_actor"] = "/".join(actors)

        desc_m = re.search(r'og:description" content="([^"]+)"', html)
        if desc_m:
            desc_text = desc_m.group(1)
            if vod["vod_name"] in desc_text:
                desc_text = desc_text.replace(vod["vod_name"] + ':', '', 1)
                desc_text = desc_text.replace(vod["vod_name"], '', 1)
            vod["vod_content"] = self._get_wechat_info() + "\n" + self.clean(desc_text)
        else:
            vod["vod_content"] = self._get_wechat_info()

        play_line_names = re.findall(r'<div class="module-tab-item tab-item" data-dropdown-value="([^"]+)"', html)
        
        play_list_blocks = re.findall(r'<div class="module-list sort-list tab-list his-tab-list" id="panel1">(.*?)</div>\s*<div class="shortcuts-mobile-overlay"></div>', html, re.S)
        
        if not play_list_blocks:
            play_list_blocks = re.findall(r'<div class="module-list sort-list tab-list his-tab-list" id="panel1">(.*?)</div>\s*<div', html, re.S)

        play_url_groups = []
        play_from_parts = []
        
        for idx, block in enumerate(play_list_blocks):
            line_name = play_line_names[idx] if idx < len(play_line_names) else f"线路{idx+1}"
            play_from_parts.append(line_name)
            
            ep_list = []
            seen_in_block = set()
            
            ep_matches = re.findall(r'<a[^>]*href="(/niplay/\d+-\d+-\d+/)"[^>]*>(.*?)</a>', block)
            for ep_href, ep_content in ep_matches:
                full_url = self.BASE_URL + ep_href
                if full_url in seen_in_block:
                    continue
                seen_in_block.add(full_url)
                
                ep_name_match = re.search(r'<span>([^<]+)</span>', ep_content)
                ep_name = ep_name_match.group(1) if ep_name_match else ""
                if not ep_name or ep_name.isdigit():
                    nid_match = re.search(r'-(\d+)/$', ep_href)
                    nid = nid_match.group(1) if nid_match else "1"
                    ep_name = f"第{nid}集"
                
                encrypted_url = self._encrypt_url(full_url)
                ep_list.append(f"{ep_name}${encrypted_url}")
            
            if ep_list:
                play_url_groups.append("#".join(ep_list))

        if not play_from_parts:
            play_from_parts = ["极速在线"]
            seen_episodes = set()
            play_matches = list(re.finditer(r'href="(/niplay/\d+-\d+-\d+/)"', html))
            for pm in play_matches:
                ep_href = pm.group(1)
                full_url = self.BASE_URL + ep_href
                if full_url in seen_episodes:
                    continue
                seen_episodes.add(full_url)
                
                ep_name_match = re.search(r'<span>([^<]+)</span>', html[max(0, pm.start()-100):pm.end()+50])
                ep_name = ep_name_match.group(1) if ep_name_match else ""
                if not ep_name or ep_name.isdigit():
                    nid_match = re.search(r'-(\d+)/$', ep_href)
                    nid = nid_match.group(1) if nid_match else "1"
                    ep_name = f"第{nid}集"
                
                encrypted_url = self._encrypt_url(full_url)
                play_url_groups.append(f"{ep_name}${encrypted_url}")

        vod["vod_play_from"] = "$$$".join(play_from_parts)
        vod["vod_play_url"] = "$$$".join(play_url_groups) if play_url_groups else ""

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

        encoded_key = urllib.parse.quote(key)
        search_url = f"{self.BASE_URL}/s/{encoded_key}-------------/"
        if pg > 1:
            search_url = search_url.rstrip('/') + f"/{pg}/"
        
        html = self.getHtml(search_url)

        if not html:
            return result

        videos = []
        seen = set()

        href_matches = list(re.finditer(r'href="(/nivod/(\d+)/)"', html))
        for href_match in href_matches:
            href = href_match.group(1)
            vid = href_match.group(2)
            
            if vid in seen:
                continue
            seen.add(vid)

            start = max(0, href_match.start() - 800)
            end = min(len(html), href_match.end() + 1000)
            block = html[start:end]

            name = ""
            title_m = re.search(r'<strong>([^<]+)</strong>', block)
            if title_m:
                name = self.clean(title_m.group(1))
            if not name:
                title_m = re.search(r'alt="([^"]+)"', block)
                if title_m:
                    name = self.clean(title_m.group(1))
            if not name or len(name) < 2 or name in ["电影", "剧集", "综艺", "动漫", "短剧"]:
                continue

            pic = ""
            do_m = re.search(r'data-original="([^"]+)"', block)
            if do_m:
                pic = do_m.group(1)
            else:
                src_m = re.search(r'<img[^>]*src="([^"]+)"', block)
                if src_m:
                    pic = src_m.group(1)
            if pic and pic.startswith("/"):
                pic = self.BASE_URL + pic
            if "/loading.png" in pic:
                pic = ""

            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_score": "",
                "vod_remarks": "",
                "type_id": "1",
                "type_name": "搜索结果",
            })

        pagecount = "1"
        next_m = re.search(r'下一页', html)
        if next_m:
            pagecount = str(pg + 1)

        result["list"] = videos[:30]
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * len(videos)) if videos else "0"
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            decrypted_url = self._decrypt_url(id)
        except Exception:
            decrypted_url = id

        if not decrypted_url.startswith("http"):
            decrypted_url = self.BASE_URL + decrypted_url if decrypted_url.startswith("/") else id

        play_headers = {
            "User-Agent": self.UA,
            "Referer": decrypted_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        play_html = self.getHtml(decrypted_url)
        if play_html:
            player_data_m = re.search(r'player_aaaa\s*=\s*({[^;]+})', play_html)
            if player_data_m:
                try:
                    player_data = json.loads(player_data_m.group(1))
                    video_url = player_data.get("url", "")
                    if video_url and video_url.startswith("http"):
                        return {"url": video_url, "parse": "0", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}
                except Exception:
                    pass

            url_patterns = [
                r'url\s*=\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
                r'videoUrl\s*=\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
                r'src\s*=\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
                r'playUrl\s*=\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
                r'"url"\s*:\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
                r'"src"\s*:\s*["\']([^"\']+\.(m3u8|mp4|flv))["\']',
            ]

            for pattern in url_patterns:
                m = re.search(pattern, play_html)
                if m:
                    url = m.group(1)
                    if url.startswith("//"):
                        url = "https:" + url
                    elif url.startswith("/"):
                        url = self.BASE_URL + url
                    return {"url": url, "parse": "0", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

            iframe_matches = re.finditer(r'<iframe[^>]*src="([^"]+)"[^>]*>', play_html)
            for m in iframe_matches:
                iframe_url = m.group(1)
                if not iframe_url.startswith("http"):
                    iframe_url = self.BASE_URL + iframe_url if iframe_url.startswith("/") else "https:" + iframe_url
                play_headers["X-Requested-With"] = "XMLHttpRequest"
                return {"url": iframe_url, "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

        play_headers["X-Requested-With"] = "XMLHttpRequest"
        return {"url": decrypted_url, "parse": "1", "header": json.dumps(play_headers), "playUrl": "", "subtitle": ""}

    def __jsEvalReturn(self):
        return {"proxy": None}