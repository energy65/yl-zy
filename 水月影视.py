# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import html as html_mod
import urllib.parse
import urllib.request

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
    BASE_URL = "https://www.atinyhiney.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    _w_data = [141, 209, 192, 131, 216, 212, 138, 218, 219, 129, 223, 255, 132, 251, 232, 16, 214, 136, 166, 141, 229, 245, 143, 218, 218, 139, 228, 193, 131, 210, 239, 67, 155, 227, 190, 65, 213, 136, 204, 94, 94, 82, 83, 64, 86, 109, 70, 80, 81, 140, 221, 192, 182, 168, 191, 212, 173, 220, 138, 202, 253, 131, 201, 247, 183, 195, 205, 139, 221, 229, 146, 229, 162, 213, 130, 139, 141, 243, 198, 129, 221, 229, 138, 213, 236]
    _w_line_data = [142, 223, 218, 129, 251, 253, 138, 226, 198, 141, 196, 238]
    _w_key = b"hongguo_wechat_2026"

    CATEGORIES = [
        {"type_id": "sy1", "type_name": "电影", "url": "/sy/1.html"},
        {"type_id": "sy2", "type_name": "电视剧", "url": "/sy/2.html"},
        {"type_id": "sy3", "type_name": "综艺", "url": "/sy/3.html"},
        {"type_id": "sy4", "type_name": "动漫", "url": "/sy/4.html"},
        {"type_id": "sy5", "type_name": "动作片", "url": "/sy/5.html"},
        {"type_id": "sy6", "type_name": "喜剧片", "url": "/sy/6.html"},
        {"type_id": "sy7", "type_name": "爱情片", "url": "/sy/7.html"},
        {"type_id": "sy8", "type_name": "科幻片", "url": "/sy/8.html"},
        {"type_id": "sy9", "type_name": "恐怖片", "url": "/sy/9.html"},
        {"type_id": "sy10", "type_name": "剧情片", "url": "/sy/10.html"},
        {"type_id": "sy11", "type_name": "战争片", "url": "/sy/11.html"},
        {"type_id": "sy12", "type_name": "纪录片", "url": "/sy/12.html"},
        {"type_id": "sy13", "type_name": "国产剧", "url": "/sy/13.html"},
        {"type_id": "sy14", "type_name": "香港剧", "url": "/sy/14.html"},
        {"type_id": "sy15", "type_name": "台湾剧", "url": "/sy/15.html"},
        {"type_id": "sy16", "type_name": "欧美剧", "url": "/sy/16.html"},
        {"type_id": "sy25", "type_name": "韩国剧", "url": "/sy/25.html"},
        {"type_id": "sy26", "type_name": "日本剧", "url": "/sy/26.html"},
        {"type_id": "sy27", "type_name": "泰国剧", "url": "/sy/27.html"},
        {"type_id": "sy28", "type_name": "海外剧", "url": "/sy/28.html"},
        {"type_id": "sy29", "type_name": "短剧", "url": "/sy/29.html"},
        {"type_id": "sy30", "type_name": "大陆综艺", "url": "/sy/30.html"},
        {"type_id": "sy31", "type_name": "港台综艺", "url": "/sy/31.html"},
        {"type_id": "sy32", "type_name": "日韩综艺", "url": "/sy/32.html"},
        {"type_id": "sy33", "type_name": "欧美综艺", "url": "/sy/33.html"},
        {"type_id": "sy34", "type_name": "大陆动漫", "url": "/sy/34.html"},
        {"type_id": "sy35", "type_name": "日本动漫", "url": "/sy/35.html"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "水月影视"

    def _get_wechat_info(self):
        try:
            key = self._w_key
            data = self._w_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                data = self._w_data
                result = []
                for i in range(len(data)):
                    result.append(chr(data[i] ^ key[i % len(key)]))
                return ''.join(result)
            except Exception:
                return ''

    def _get_line_info(self):
        try:
            key = self._w_key
            data = self._w_line_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                data = self._w_line_data
                result = []
                for i in range(len(data)):
                    result.append(chr(data[i] ^ key[i % len(key)]))
                return ''.join(result)
            except Exception:
                return '水月影视'

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
                "Referer": self.BASE_URL + "/",
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

    def _clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r'\s+', ' ', text).strip()

    def _clean_intro(self, text):
        """Clean intro text, remove inline junk markers like @xxx@ and &copy; etc."""
        if not text:
            return ""
        # Remove @xxx@ inline watermark markers
        text = re.sub(r'@[^@\s]{2,30}@', '', text)
        # Remove &copy; copyright markers
        text = re.sub(r'&copy;[^&<]{0,30}', '', text)
        # Remove &xxxx; HTML entities that aren't decoded properly
        text = html_mod.unescape(text)
        # Remove double periods/ellipsis artifacts
        text = re.sub(r'\.{2,}', '...', text)
        # Clean extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _parse_vod_items(self, html):
        items = []
        seen = set()

        main_m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
        search_area = main_m.group(1) if main_m else html

        for m in re.finditer(
            r'<a\s+[^>]*href=["\'](/shuiyue/(\d+)\.html)["\']([^>]*)>(.*?)</a>',
            search_area, re.DOTALL | re.IGNORECASE
        ):
            href = m.group(1)
            vid = m.group(2)
            rest_attrs = m.group(3)
            inner = m.group(4)

            if vid in seen:
                continue
            seen.add(vid)

            title = ""
            title_m = re.search(r'title=["\']([^"\']*)["\']', rest_attrs)
            if title_m:
                title = title_m.group(1).strip()
            if not title:
                title_m = re.search(r'title=["\']([^"\']*)["\']', inner)
                if title_m:
                    title = title_m.group(1).strip()
            if not title:
                alt_m = re.search(r'alt=["\']([^"\']*)["\']', inner)
                if alt_m:
                    title = alt_m.group(1).strip()
            if not title:
                title = self._clean(re.sub(r'<[^>]*>', '', inner))

            img = ""
            img_m = re.search(r'data-src=["\']([^"\']*)["\']', inner)
            if img_m:
                img = img_m.group(1).strip()
            if not img:
                img_m = re.search(r'src=["\']([^"\']*)["\']', inner)
                if img_m:
                    img = img_m.group(1).strip()
            if not img:
                img_m = re.search(r'data-original=["\']([^"\']*)["\']', inner)
                if img_m:
                    img = img_m.group(1).strip()

            remarks = ""
            text_blocks = re.findall(r'>([^<]+)<', inner)
            for tb in text_blocks:
                tb = self._clean(tb)
                if tb and len(tb) > 1 and tb != title and not tb.startswith('http'):
                    remarks = tb
                    break

            if title and not title.startswith('更多'):
                items.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": img,
                    "vod_remarks": remarks,
                    "vod_class": "",
                })

        return items

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/")
        if not html:
            return result

        videos = self._parse_vod_items(html)
        wechat_info = self._get_wechat_info()
        for v in videos[:30]:
            if wechat_info:
                v["vod_content"] = wechat_info

        result["list"] = videos[:30]
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

            url = self.BASE_URL + cat["url"]
            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_vod_items(html)
            wechat_info = self._get_wechat_info()

            for v in videos:
                if wechat_info:
                    v["vod_content"] = wechat_info
                v["vod_class"] = cat["type_name"]

            page_size = 30
            page = int(pg) if pg and str(pg).isdigit() else 1
            total = len(videos)
            total_pages = max(1, (total + page_size - 1) // page_size)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_videos = videos[start_idx:end_idx]

            result["list"] = paged_videos
            result["pagecount"] = str(total_pages)
            result["total"] = str(total)
            return result
        except Exception:
            return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids

        url = self.BASE_URL + "/shuiyue/" + str(vid) + ".html"
        html = self.getHtml(url)
        if not html:
            return result

        title = ""
        h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if h1_m:
            title = self._clean(re.sub(r'<[^>]*>', '', h1_m.group(1)))
        if not title:
            title_m = re.search(r'<title>(.*?)</title>', html)
            if title_m:
                title = self._clean(title_m.group(1).split('-')[0].strip())
        if not title:
            title = str(vid)

        pic = ""
        pic_candidates = re.findall(
            r'(?:data-src|src|data-original)=["\'](https?://[^"\']+(?:\.jpg|\.jpeg|\.png|\.webp|\.gif))["\']',
            html
        )
        for pc in pic_candidates:
            if 'upload/vod' in pc or 'yzzyimg' in pc or 'liangzipic' in pc or 'lzipic' in pc:
                pic = pc
                break
        if not pic and pic_candidates:
            pic = pic_candidates[0]

        intro = ""
        meta_desc = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
        if meta_desc:
            desc_text = html_mod.unescape(meta_desc.group(1))
            intro = self._clean_intro(re.sub(r'<[^>]*>', '', desc_text))

        director = ""
        cast = ""
        year = ""
        area = ""
        cat_name = ""

        if meta_desc:
            desc_text = html_mod.unescape(meta_desc.group(1))
            director_m = re.search(r'由(.+?)执导', desc_text)
            if director_m:
                director = self._clean(director_m.group(1))

            cast_m = re.search(r'主演(.+?)等人', desc_text)
            if cast_m:
                cast = self._clean(cast_m.group(1))
            else:
                cast_m2 = re.search(r'执导[，,](.+?)等人主演', desc_text)
                if cast_m2:
                    cast = self._clean(cast_m2.group(1))

            year_m = re.search(r'于(\d+)年', desc_text)
            if year_m:
                year = year_m.group(1)

            area_m = re.search(r'该(.+?)(?:讲述|剧|电影|综艺|动漫)', desc_text)
            if area_m:
                area = self._clean(area_m.group(1))

        meta_kw = re.search(
            r'<meta[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
        if meta_kw:
            kw_text = html_mod.unescape(meta_kw.group(1))
            kw_parts = [k.strip() for k in kw_text.split(',') if k.strip()]
            if kw_parts:
                filtered_kw = [k for k in kw_parts[1:] if k not in ('在线观看', '全集', '手机在线观看', '追剧', '免费', '高清', '剧情', '演员表', '资讯')]
                cat_name = ', '.join(filtered_kw[:2]) if filtered_kw else (kw_parts[1] if len(kw_parts) > 1 else '')

        wechat_info = self._get_wechat_info()
        if wechat_info:
            intro = (intro + '\n\n' + wechat_info) if intro else wechat_info

        play_groups = []
        ep_pattern = re.compile(
            r'href=["\'](/play/\d+-\d+-(\d+)\.html)["\'][^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )

        seen_eps = set()
        for ep_m in ep_pattern.finditer(html):
            ep_href = ep_m.group(1)
            ep_num = ep_m.group(2)
            ep_text = self._clean(re.sub(r'<[^>]*>', '', ep_m.group(3)))

            if ep_num in seen_eps:
                continue
            seen_eps.add(ep_num)

            if not ep_text or ep_text in ('立即播放', '播放', ''):
                ep_text = "第" + str(int(ep_num) + 1) + "集"

            play_groups.append(ep_text + "$" + ep_href)

        if not play_groups:
            play_groups.append("播放$" + "/play/" + str(vid) + "-0-0.html")

        line_info = self._get_line_info()

        vod = {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pic,
            "vod_actor": cast,
            "vod_director": director,
            "vod_year": year,
            "vod_area": area,
            "vod_remarks": "",
            "vod_content": intro,
            "vod_class": cat_name,
            "type_name": cat_name,
            "vod_play_from": line_info,
            "vod_play_url": "#".join(play_groups),
        }

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            kw_lower = key.lower()
            page = int(pg) if pg and str(pg).isdigit() else 1
            page_size = 30

            all_items = []
            seen_ids = set()

            search_cats = self.CATEGORIES
            max_cats = len(search_cats) if quick else min(len(search_cats), 27)

            for cat in search_cats[:max_cats]:
                url = self.BASE_URL + cat["url"]
                html = self.getHtml(url)
                if html:
                    items = self._parse_vod_items(html)
                    for item in items:
                        vid = item["vod_id"]
                        if vid not in seen_ids:
                            seen_ids.add(vid)
                            item["_cat"] = cat["type_name"]
                            item["vod_class"] = cat["type_name"]
                            all_items.append(item)

            def score_match(item):
                name = item.get("vod_name", "").lower()
                kw = kw_lower
                score = 0
                if kw == name:
                    score += 100
                elif kw in name:
                    score += 50
                cat = item.get("_cat", "").lower()
                if kw and kw in cat:
                    score += 30
                remarks = item.get("vod_remarks", "").lower()
                if kw and kw in remarks:
                    score += 15
                cat_boost = {
                    "天文": ["纪录片", "大陆综艺"],
                    "地理": ["纪录片"],
                    "纪录片": ["纪录片"],
                    "科教": ["纪录片", "大陆动漫"],
                    "自然": ["纪录片"],
                    "历史": ["纪录片", "剧情片"],
                    "科学": ["纪录片", "科幻片"],
                    "宇宙": ["纪录片", "科幻片"],
                    "地球": ["纪录片"],
                    "海洋": ["纪录片"],
                    "动物": ["纪录片"],
                    "探险": ["纪录片"],
                }
                if kw in cat_boost:
                    relevant_cats = cat_boost[kw]
                    if cat in [c.lower() for c in relevant_cats]:
                        score += 20
                if score == 0:
                    kw_chars = [kw[i:i+2] for i in range(len(kw)-1)]
                    for chunk in kw_chars:
                        if chunk in name:
                            score += 1
                return score

            scored_items = []
            for item in all_items:
                s = score_match(item)
                if s > 0:
                    scored_items.append((s, item))

            scored_items.sort(key=lambda x: x[0], reverse=True)
            filtered = [item for (s, item) in scored_items]

            videos = []
            wechat_info = self._get_wechat_info()
            for item in filtered:
                v = {
                    "vod_id": item["vod_id"],
                    "vod_name": item["vod_name"],
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "vod_class": item.get("vod_class", ""),
                }
                if wechat_info:
                    v["vod_content"] = wechat_info
                videos.append(v)

            if not videos:
                for item in all_items[:50]:
                    v = {
                        "vod_id": item["vod_id"],
                        "vod_name": item["vod_name"],
                        "vod_pic": item.get("vod_pic", ""),
                        "vod_remarks": item.get("vod_remarks", ""),
                        "vod_class": item.get("vod_class", ""),
                    }
                    if wechat_info:
                        v["vod_content"] = wechat_info
                    videos.append(v)

            if videos:
                total = len(videos)
                total_pages = max(1, (total + page_size - 1) // page_size)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paged_results = videos[start_idx:end_idx]

                result["list"] = paged_results
                result["pagecount"] = str(total_pages)
                result["total"] = str(total)

            return result
        except Exception:
            return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "url": "", "header": "", "playUrl": "", "subtitle": "", "proxy": ""}
        try:
            if not id:
                return result

            play_url = id if id.startswith("http") else self.BASE_URL + id
            html = self.getHtml(play_url)
            if not html:
                return result

            m3u8_m = re.search(
                r'var\s+now\s*=\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                html, re.IGNORECASE
            )
            if not m3u8_m:
                m3u8_m = re.search(
                    r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)',
                    html, re.IGNORECASE
                )

            if m3u8_m:
                result["url"] = m3u8_m.group(1)
                result["parse"] = 0
                result["header"] = json.dumps({
                    "Referer": self.BASE_URL + "/",
                    "Origin": self.BASE_URL,
                    "User-Agent": self.UA,
                })
            return result
        except Exception:
            return result