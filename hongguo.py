# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
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
    BASE_URL = "https://hongguoduanju.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 微信公众号加密数据（完整版本）
    _w_full_data = [141, 209, 192, 131, 216, 212, 138, 218, 219, 129, 223, 255, 132, 251, 232, 16, 214, 136, 166, 141, 229, 245, 143, 218, 218, 139, 228, 193, 131, 210, 239, 67, 155, 227, 190, 65, 213, 136, 204, 94, 94, 82, 83, 64, 86, 109, 70, 80, 81, 140, 221, 192, 182, 168, 191, 212, 173, 220, 138, 202, 253, 131, 201, 247, 183, 195, 205, 139, 221, 229, 146, 229, 162, 213, 130, 139, 141, 243, 198, 129, 221, 229, 138, 213, 236, 128, 222, 217, 137, 211, 217]
    # 线路文本加密数据
    _w_line_data = [142, 213, 254, 130, 237, 238, 135, 226, 216, 129, 216, 222, 135, 197, 216, 18, 65, 213, 136, 204, 94, 94, 82, 83, 64, 86, 109, 70, 80, 81, 72, 135, 206, 207, 215, 186, 169, 211, 213, 222, 134, 192, 225]
    _w_key = b"hongguo_wechat_2026"

    # 分类配置（完整版本）
    CATEGORIES = [
        # 背景分类
        {"type_id": "bg_modern", "type_name": "现代", "url": "/category?background=cate_757"},
        {"type_id": "bg_city", "type_name": "都市", "url": "/category?background=cate_1"},
        {"type_id": "bg_ancient", "type_name": "古代", "url": "/category?background=cate_758"},
        {"type_id": "bg_countryside", "type_name": "乡村", "url": "/category?background=cate_11"},
        {"type_id": "bg_era", "type_name": "年代", "url": "/category?background=cate_79"},
        {"type_id": "bg_fantasy", "type_name": "架空", "url": "/category?background=cate_452"},
        {"type_id": "bg_office", "type_name": "职场", "url": "/category?background=cate_127"},
        {"type_id": "bg_Republic", "type_name": "民国", "url": "/category?background=cate_390"},
        {"type_id": "bg_campus", "type_name": "校园", "url": "/category?background=cate_4"},
        {"type_id": "bg_palace", "type_name": "宫廷", "url": "/category?background=cate_1153"},
        {"type_id": "bg_desert", "type_name": "荒岛", "url": "/category?background=cate_1162"},
        # 主题分类
        {"type_id": "topic_romance", "type_name": "现言", "url": "/category?topic=cate_1021"},
        {"type_id": "topic_growth", "type_name": "女性成长", "url": "/category?topic=cate_1048"},
        {"type_id": "topic_brainhole", "type_name": "脑洞", "url": "/category?topic=cate_262"},
        {"type_id": "topic_fantasy", "type_name": "奇幻", "url": "/category?topic=cate_1020"},
        {"type_id": "topic_xuanhuan", "type_name": "玄幻", "url": "/category?topic=cate_1019"},
        {"type_id": "topic_guyan", "type_name": "古言", "url": "/category?topic=cate_439"},
        {"type_id": "topic_zhanshen", "type_name": "战神", "url": "/category?topic=cate_1038"},
        {"type_id": "topic_gongdou", "type_name": "宫斗", "url": "/category?topic=cate_246"},
        {"type_id": "topic_xianxia", "type_name": "仙侠", "url": "/category?topic=cate_1013"},
        {"type_id": "topic_political", "type_name": "权谋", "url": "/category?topic=cate_1047"},
        {"type_id": "topic_zhongtian", "type_name": "种田", "url": "/category?topic=cate_1180"},
        {"type_id": "topic_era_love", "type_name": "年代爱情", "url": "/category?topic=cate_1022"},
        {"type_id": "topic_suspense", "type_name": "悬疑", "url": "/category?topic=cate_165"},
        {"type_id": "topic_comedy", "type_name": "喜剧", "url": "/category?topic=cate_303"},
        {"type_id": "topic_youth", "type_name": "青春", "url": "/category?topic=cate_297"},
        {"type_id": "topic_republic_love", "type_name": "民国爱情", "url": "/category?topic=cate_1025"},
        {"type_id": "topic_zhiguai", "type_name": "志怪", "url": "/category?topic=cate_1027"},
        {"type_id": "topic_horror", "type_name": "灵异", "url": "/category?topic=cate_751"},
        {"type_id": "topic_patriotism", "type_name": "家国情怀", "url": "/category?topic=cate_1235"},
        {"type_id": "topic_law", "type_name": "法律", "url": "/category?topic=cate_1136"},
        {"type_id": "topic_crime", "type_name": "刑侦", "url": "/category?topic=cate_1148"},
        {"type_id": "topic_antiwar", "type_name": "抗战", "url": "/category?topic=cate_504"},
        {"type_id": "topic_martial", "type_name": "武侠", "url": "/category?topic=cate_1172"},
        {"type_id": "topic_legend", "type_name": "民国传奇", "url": "/category?topic=cate_1240"},
        {"type_id": "topic_survival", "type_name": "求生", "url": "/category?topic=cate_1168"},
        {"type_id": "topic_action", "type_name": "动作", "url": "/category?topic=cate_302"},
        {"type_id": "topic_scifi", "type_name": "科幻", "url": "/category?topic=cate_1092"},
        {"type_id": "topic_terror", "type_name": "恐怖", "url": "/category?topic=cate_1219"},
        {"type_id": "topic_business", "type_name": "商战", "url": "/category?topic=cate_1225"},
        # 设定分类
        {"type_id": "setting_revenge", "type_name": "打脸虐渣", "url": "/category?setting=cate_1051"},
        {"type_id": "setting_bigmale", "type_name": "大男主", "url": "/category?setting=cate_1207"},
        {"type_id": "setting_bigboss", "type_name": "大女主", "url": "/category?setting=cate_760"},
        {"type_id": "setting_majia", "type_name": "马甲", "url": "/category?setting=cate_266"},
        {"type_id": "setting_rebirth", "type_name": "重生", "url": "/category?setting=cate_36"},
        {"type_id": "setting_transmigration", "type_name": "穿越", "url": "/category?setting=cate_37"},
        {"type_id": "setting_system", "type_name": "系统", "url": "/category?setting=cate_19"},
        {"type_id": "setting_fakemarr", "type_name": "先婚后爱", "url": "/category?setting=cate_265"},
        {"type_id": "setting_family", "type_name": "家长里短", "url": "/category?setting=cate_862"},
        {"type_id": "setting_underdog", "type_name": "小人物", "url": "/category?setting=cate_1010"},
        {"type_id": "setting_reunion", "type_name": "破镜重圆", "url": "/category?setting=cate_475"},
        {"type_id": "setting_wealthy", "type_name": "豪门", "url": "/category?setting=cate_936"},
        {"type_id": "setting_return", "type_name": "强者回归", "url": "/category?setting=cate_1045"},
        {"type_id": "setting_superpower", "type_name": "异能", "url": "/category?setting=cate_598"},
        {"type_id": "setting_angst", "type_name": "虐恋", "url": "/category?setting=cate_1008"},
        {"type_id": "setting_inherit", "type_name": "传承觉醒", "url": "/category?setting=cate_1007"},
        {"type_id": "setting_doctor", "type_name": "医生", "url": "/category?setting=cate_487"},
        {"type_id": "setting_team", "type_name": "强强联合", "url": "/category?setting=cate_1049"},
        {"type_id": "setting_soninlaw", "type_name": "赘婿逆袭", "url": "/category?setting=cate_1044"},
        {"type_id": "setting_sweet", "type_name": "甜宠", "url": "/category?setting=cate_96"},
        {"type_id": "setting_entertainment", "type_name": "娱乐圈", "url": "/category?setting=cate_43"},
        {"type_id": "setting_miracle", "type_name": "神医", "url": "/category?setting=cate_26"},
        {"type_id": "setting_childhood", "type_name": "青梅竹马", "url": "/category?setting=cate_387"},
        {"type_id": "setting_elder", "type_name": "姐弟恋", "url": "/category?setting=cate_762"},
        {"type_id": "setting_mystic", "type_name": "玄学", "url": "/category?setting=cate_929"},
        {"type_id": "setting_chasewife", "type_name": "追妻火葬场", "url": "/category?setting=cate_616"},
        {"type_id": "setting_expert", "type_name": "业界精英", "url": "/category?setting=cate_1293"},
        {"type_id": "setting_loveatfirst", "type_name": "一见钟情", "url": "/category?setting=cate_477"},
        {"type_id": "setting_fortune", "type_name": "暴富", "url": "/category?setting=cate_1191"},
        # 受众分类
        {"type_id": "gender_male", "type_name": "男频", "url": "/category?gender=1"},
        {"type_id": "gender_female", "type_name": "女频", "url": "/category?gender=0"},
        # 时间分类
        {"type_id": "time_7d", "type_name": "7天内上新", "url": "/category?time=1"},
        {"type_id": "time_14d", "type_name": "14天内上新", "url": "/category?time=2"},
        {"type_id": "time_30d", "type_name": "30天内上新", "url": "/category?time=3"},
        {"type_id": "time_90d", "type_name": "90天内上新", "url": "/category?time=4"},
        # 排序
        {"type_id": "sort_hot", "type_name": "最热", "url": "/category?sort_type=1"},
        {"type_id": "sort_new", "type_name": "最新", "url": "/category?sort_type=2"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "红果短剧"

    def _get_wechat_info(self):
        try:
            # XOR decrypt
            key = self._w_key
            data = self._w_full_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception as e:
            # Fallback: try alternative method
            try:
                key = self._w_key
                data = self._w_full_data
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
                return '红果短剧'

    def _decompress(self, data, content_encoding):
        """Decompress according to Content-Encoding. Returns raw bytes."""
        if not content_encoding:
            return data
        ce = content_encoding.lower()
        if "gzip" in ce:
            try:
                return gzip.decompress(data)
            except Exception:
                pass
        elif "br" in ce:
            try:
                import brotli
                return brotli.decompress(data)
            except Exception:
                pass
        elif "zstd" in ce:
            try:
                import zstandard
                return zstandard.ZstdDecompressor().decompress(data)
            except Exception:
                try:
                    import zstd
                    return zstd.decompress(data)
                except Exception:
                    pass
        return data

    def _decode_bytes(self, data):
        for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _serve_error(self, text):
        # The server intermittently returns a JSON error instead of the page.
        return (not text) or '"error_code"' in text[:200] or 'function_initialize_failed' in text[:300]

    def getHtml(self, url):
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            # Only request gzip: the server then reliably replies with gzip.
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": self.BASE_URL + "/",
        }

        import time as _time

        for attempt in range(3):
            # --- primary: urllib with relaxed SSL ---
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                try:
                    ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
                except Exception:
                    pass
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    data = self._decompress(resp.read(), resp.headers.get("Content-Encoding", ""))
                text = self._decode_bytes(data)
                if not self._serve_error(text):
                    return text
            except Exception:
                pass

            # --- fallback: requests (verify disabled) ---
            try:
                import requests
                r = requests.get(url, headers=headers, timeout=20, verify=False)
                raw = r.content
                if isinstance(raw, bytes) and r.headers.get("Content-Encoding"):
                    raw = self._decompress(raw, r.headers.get("Content-Encoding"))
                text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else r.text
                if not self._serve_error(text):
                    return text
            except Exception:
                pass

            # transient server error / block -> back off a little and retry
            _time.sleep(0.5 + attempt * 0.5)

        return ""

    def _extract_ssr_data(self, html):
        patterns = [
            r'_ROUTER_DATA\s*=\s*',
            r'window\._ROUTER_DATA\s*=\s*',
            r'window\.__INITIAL_STATE__\s*=\s*',
            r'window\.__NUXT__\s*=\s*',
            r'window\.__DATA__\s*=\s*',
        ]
        decoder = json.JSONDecoder()
        for pat in patterns:
            m = re.search(pat, html)
            if not m:
                continue
            # Skip to the start of the JSON value
            sub = html[m.end():].lstrip()
            try:
                obj, _ = decoder.raw_decode(sub)
                return obj
            except Exception:
                # Fallback: brace matching for values not starting with '{'
                json_start = m.end()
                if json_start >= len(html) or html[json_start] != '{':
                    json_start = html.find('{', m.end())
                if json_start < 0:
                    continue
                brace_count = 0
                end = -1
                max_len = min(len(html), json_start + 200000)
                for i in range(json_start, max_len):
                    if html[i] == '{':
                        brace_count += 1
                    elif html[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                if end > 0:
                    try:
                        return json.loads(html[json_start:end])
                    except Exception:
                        continue
        return None

    def _parse_video_item(self, item):
        """Parse a video item from recommendList"""
        if not item:
            return None
        try:
            # Try series_id, fall back to id or other possible keys
            series_id = item.get('series_id') or item.get('id') or item.get('series_id_v2', '')
            series_id = str(series_id) if series_id else ''
            if not series_id:
                # Try to get any numeric ID from the item
                for key in item:
                    val = str(item[key])
                    if val.isdigit():
                        series_id = val
                        break
            if not series_id:
                return None

            # Try multiple possible field names
            name = item.get('series_name') or item.get('name') or item.get('title', '')
            pic = item.get('series_cover') or item.get('pic') or item.get('cover', '')
            intro = item.get('series_intro') or item.get('description') or item.get('intro', '')
            tags = item.get('tags') or item.get('genre') or item.get('keywords', [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            episode_cnt = item.get('episode_cnt') or item.get('episode_count') or item.get('episode', 0)
            episode_right_text = item.get('episode_right_text') or item.get('status', '') or ''

            # Build remarks
            remarks = episode_right_text if episode_right_text else (f"共{episode_cnt}集" if episode_cnt else '')

            # Add WeChat info to description
            wechat_info = self._get_wechat_info()
            if wechat_info:
                intro = (intro + '\n\n' + wechat_info) if intro else wechat_info

            return {
                "vod_id": series_id,
                "vod_name": name or series_id,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "vod_content": intro,
                "vod_class": ', '.join(tags[:3]) if tags else '',
            }
        except Exception:
            return None

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/category?sort_type=1")
        if not html:
            return result

        data = self._extract_ssr_data(html)
        if not data:
            return result

        loader = data.get('loaderData', {})
        cat_page = loader.get('category_page', {})
        recommend_list = cat_page.get('recommendList', [])

        videos = []
        for item in recommend_list[:30]:
            v = self._parse_video_item(item)
            if v:
                videos.append(v)

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

            url = self.BASE_URL + cat['url']
            html = self.getHtml(url)
            if not html:
                return result

            data = self._extract_ssr_data(html)
            if not data:
                return result

            loader = data.get('loaderData', {})
            cat_page = loader.get('category_page', {})
            recommend_list = cat_page.get('recommendList', [])

            videos = []
            for item in recommend_list:
                v = self._parse_video_item(item)
                if v:
                    videos.append(v)

            if videos:
                # Implement pagination
                page_size = 30
                page = int(pg) if pg and str(pg).isdigit() else 1
                total = len(videos)
                total_pages = (total + page_size - 1) // page_size
                
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

        html = self.getHtml(f"{self.BASE_URL}/detail?series_id={vid}")
        if not html:
            return result

        data = self._extract_ssr_data(html)
        if not data:
            return result

        loader = data.get('loaderData', {})
        detail_page = loader.get('detail_page', {})
        series_detail = detail_page.get('seriesDetail', {})

        if not series_detail:
            return result

        series_id = str(series_detail.get('series_id', ''))
        series_name = series_detail.get('series_name', '')
        series_cover = series_detail.get('series_cover', '')
        series_intro = series_detail.get('series_intro', '')
        tags = series_detail.get('tags', [])
        episode_cnt = series_detail.get('episode_cnt', 0)
        episode_right_text = series_detail.get('episode_right_text', '')
        vid_list = series_detail.get('vid_list', [])
        celebrities = series_detail.get('celebrities', [])

        if not series_name:
            return result

        # Build play list
        play_groups = []
        for i, ep_vid in enumerate(vid_list):
            ep_name = f"第{i+1}集"
            play_link = f"{self.BASE_URL}/player/{series_id}/{ep_vid}"
            play_groups.append(f"{ep_name}${play_link}")

        if not play_groups:
            play_groups.append(f"第1集${self.BASE_URL}/player/{series_id}")

        # Build actor/director info
        actor_names = []
        for celeb in celebrities:
            nickname = celeb.get('nickname', '')
            if nickname:
                actor_names.append(nickname)

        # Add WeChat info to description
        wechat_info = self._get_wechat_info()
        desc = series_intro + '\n\n' + wechat_info

        # Get line info
        line_info = self._get_line_info()

        vod = {
            "vod_id": series_id,
            "vod_name": series_name,
            "vod_pic": series_cover,
            "vod_actor": ', '.join(actor_names[:10]) if actor_names else '',
            "vod_director": '',
            "vod_year": '',
            "vod_area": '',
            "vod_remarks": episode_right_text or f"共{episode_cnt}集",
            "vod_content": desc,
            "vod_class": ', '.join(tags[:3]) if tags else '',
            "type_name": ', '.join(tags[:3]) if tags else '',
            "vod_play_from": line_info,
            "vod_play_url": '#'.join(play_groups),
        }

        result['list'] = [vod]
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            kw_lower = key.lower()
            page = int(pg) if pg and str(pg).isdigit() else 1
            page_size = 30

            # Search URLs - start with most relevant, expand if needed
            # Primary: hot + latest
            search_urls = [
                f"{self.BASE_URL}/category?sort_type=1",
                f"{self.BASE_URL}/category?sort_type=2",
            ]

            # Fetch primary pages first
            all_items = []
            seen_ids = set()

            def process_list(recommend_list):
                for item in recommend_list:
                    sid = str(item.get('series_id', ''))
                    if sid and sid not in seen_ids:
                        seen_ids.add(sid)
                        all_items.append(item)

            for url in search_urls:
                html = self.getHtml(url)
                if html:
                    data = self._extract_ssr_data(html)
                    if data:
                        loader = data.get('loaderData', {})
                        cat_page = loader.get('category_page', {})
                        rl = cat_page.get('recommendList', [])
                        process_list(rl)

            # Filter results by keyword with relevance scoring
            def score_match(item):
                name = item.get('series_name', '').lower()
                intro = item.get('series_intro', '').lower()
                tags = [t.lower() for t in item.get('tags', [])]
                kw = kw_lower
                score = 0
                if kw == name:
                    score += 100  # Exact title match
                elif kw in name:
                    score += 50   # Partial title match
                for t in tags:
                    if kw == t:
                        score += 30  # Exact tag match
                    elif kw in t:
                        score += 15  # Partial tag match
                if kw in intro:
                    score += 5    # Intro match
                # Also check for partial keyword (e.g., "修仙小妖怪" -> "修仙" or "小妖怪")
                if score == 0:
                    kw_chars = [kw[i:i+2] for i in range(len(kw)-1)]
                    for chunk in kw_chars:
                        if chunk in name:
                            score += 1
                        if any(chunk in t for t in tags):
                            score += 0.5
                return score

            scored_items = []
            for item in all_items:
                s = score_match(item)
                if s > 0:
                    scored_items.append((s, item))

            # Sort by score descending
            scored_items.sort(key=lambda x: x[0], reverse=True)
            filtered = [item for (s, item) in scored_items]

            # If not enough results, search additional categories
            if len(filtered) < 20:
                extra_urls = [
                    # Topic categories
                    f"{self.BASE_URL}/category?topic=cate_1019",  # 玄幻
                    f"{self.BASE_URL}/category?topic=cate_1013",  # 仙侠
                    f"{self.BASE_URL}/category?topic=cate_1020",  # 奇幻
                    f"{self.BASE_URL}/category?topic=cate_439",   # 古言
                    f"{self.BASE_URL}/category?topic=cate_1038",  # 战神
                    f"{self.BASE_URL}/category?topic=cate_246",   # 宫斗
                    f"{self.BASE_URL}/category?topic=cate_1047",  # 权谋
                    f"{self.BASE_URL}/category?topic=cate_1092",  # 科幻
                    f"{self.BASE_URL}/category?topic=cate_165",   # 悬疑
                    f"{self.BASE_URL}/category?topic=cate_751",   # 灵异
                    f"{self.BASE_URL}/category?topic=cate_1219",  # 恐怖
                    f"{self.BASE_URL}/category?topic=cate_1021",  # 现言
                    f"{self.BASE_URL}/category?topic=cate_303",   # 喜剧
                    f"{self.BASE_URL}/category?topic=cate_1172",  # 武侠
                    f"{self.BASE_URL}/category?topic=cate_302",   # 动作
                    # Background categories
                    f"{self.BASE_URL}/category?background=cate_1",    # 都市
                    f"{self.BASE_URL}/category?background=cate_758",  # 古代
                    f"{self.BASE_URL}/category?background=cate_757",  # 现代
                    f"{self.BASE_URL}/category?background=cate_452",  # 架空
                    # Setting categories
                    f"{self.BASE_URL}/category?setting=cate_36",   # 重生
                    f"{self.BASE_URL}/category?setting=cate_37",   # 穿越
                    f"{self.BASE_URL}/category?setting=cate_19",   # 系统
                    f"{self.BASE_URL}/category?setting=cate_1207", # 大男主
                ]
                for url in extra_urls:
                    html = self.getHtml(url)
                    if html:
                        data = self._extract_ssr_data(html)
                        if data:
                            loader = data.get('loaderData', {})
                            cat_page = loader.get('category_page', {})
                            rl = cat_page.get('recommendList', [])
                            process_list(rl)
                            # Re-filter after adding new data with scoring
                            for item in rl:
                                sid = str(item.get('series_id', ''))
                                existing_ids = [str(f.get('series_id','')) for f in filtered]
                                s = score_match(item)
                                if s > 0 and sid not in existing_ids:
                                    # Insert at correct position based on score
                                    filtered.append(item)
                            if len(filtered) >= 50:
                                break

            # Convert to video items
            videos = []
            for item in filtered:
                v = self._parse_video_item(item)
                if v:
                    videos.append(v)

            # If no results from categories, try search engine fallback
            if not videos:
                engine_results = self._search_via_engine(key, page, page_size)
                if engine_results:
                    result["list"] = engine_results["list"]
                    result["pagecount"] = engine_results["pagecount"]
                    result["total"] = engine_results["total"]
                    return result

            # If still no results, return popular videos as fallback
            if not videos and all_items:
                for item in all_items[:50]:
                    v = self._parse_video_item(item)
                    if v:
                        videos.append(v)

            if videos:
                total = len(videos)
                total_pages = (total + page_size - 1) // page_size
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paged_results = videos[start_idx:end_idx]

                result["list"] = paged_results
                result["pagecount"] = str(total_pages)
                result["total"] = str(total)

            return result
        except Exception:
            return result

    def _search_via_engine(self, key, page, page_size):
        """Search via sitemap with multi-threading when category search finds nothing."""
        result = {"list": [], "pagecount": "1", "total": "0"}
        try:
            # Get all series_ids from sitemap (cached)
            all_ids = self._get_sitemap_ids()
            if not all_ids:
                return result

            kw_lower = key.lower()

            # Use threading to search in parallel
            import threading
            found_results = []
            found_scores = []
            found_lock = threading.Lock()
            searched = [0]
            max_search = 800  # Limit search count
            stop_flag = [False]
            found_sids = set()

            def search_batch(start_idx):
                for i in range(start_idx, min(start_idx + 200, len(all_ids))):
                    if stop_flag[0] or len(found_results) >= 10:
                        return
                    sid = all_ids[i]
                    try:
                        detail_url = f"{self.BASE_URL}/detail?series_id={sid}"
                        detail_html = self.getHtml(detail_url)
                        if detail_html:
                            data = self._extract_ssr_data(detail_html)
                            if data:
                                loader = data.get('loaderData', {})
                                detail_page = loader.get('detail_page', {})
                                sd = detail_page.get('seriesDetail', {})
                                name = sd.get('series_name', '')
                                intro = sd.get('series_intro', '')
                                tags = sd.get('tags', [])
                                name_lower = name.lower()
                                intro_lower = intro.lower()
                                tags_lower = [t.lower() for t in tags]

                                # Scoring for engine search
                                score = 0
                                if kw_lower == name_lower:
                                    score = 100
                                elif kw_lower in name_lower:
                                    score = 50
                                elif any(kw_lower in t for t in tags_lower):
                                    score = 15
                                elif kw_lower in intro_lower:
                                    score = 5
                                # Partial keyword matching
                                if score == 0 and name:
                                    kw_chars = [kw_lower[i:i+2] for i in range(len(kw_lower)-1)]
                                    for chunk in kw_chars:
                                        if chunk in name_lower:
                                            score += 1

                                if name and score > 0:
                                    intro = sd.get('series_intro', '')
                                    tags = sd.get('tags', [])
                                    wechat_info = self._get_wechat_info()
                                    line_info = self._get_line_info()
                                    desc = intro + '\n\n' + wechat_info if wechat_info else intro
                                    episode_cnt = sd.get('episode_cnt', 0)
                                    episode_right_text = sd.get('episode_right_text', '')
                                    remarks = episode_right_text if episode_right_text else f"共{episode_cnt}集"

                                    # Build play url
                                    video_list = detail_page.get('videoList', [])
                                    vid_list = sd.get('vid_list', [])
                                    play_eps = []
                                    if video_list:
                                        for ep in video_list:
                                            ep_vid = str(ep.get('vid', ''))
                                            ep_title = ep.get('title', f'第{ep.get("episode", 1)}集')
                                            play_eps.append(f"{ep_title}${ep_vid}")
                                    elif vid_list:
                                        for i2, vid in enumerate(vid_list):
                                            play_eps.append(f"第{i2+1}集${vid}")

                                    vod = {
                                        "vod_id": str(sid),
                                        "vod_name": name,
                                        "vod_pic": sd.get('series_cover', ''),
                                        "vod_remarks": remarks,
                                        "vod_content": desc,
                                        "vod_class": ', '.join(tags[:3]) if tags else '',
                                        "vod_play_from": line_info,
                                        "vod_play_url": '#'.join(play_eps) if play_eps else str(sid),
                                    }
                                    with found_lock:
                                        if sid not in found_sids:
                                            found_sids.add(sid)
                                            found_results.append(vod)
                                            found_scores.append(score)
                                            if score >= 50:  # High confidence match
                                                stop_flag[0] = True
                    except Exception:
                        pass
                    with found_lock:
                        searched[0] += 1

            # Launch threads
            threads = []
            batch_size = 200
            for start in range(0, min(max_search, len(all_ids)), batch_size):
                t = threading.Thread(target=search_batch, args=(start,))
                threads.append(t)
                t.start()
                if len(threads) >= 4:  # Max 4 concurrent threads
                    for t2 in threads:
                        t2.join(timeout=60)
                    threads = []
                    if found_results or stop_flag[0]:
                        break

            for t in threads:
                t.join(timeout=60)

            if found_results:
                # Sort by score descending (higher score = better match)
                paired = list(zip(found_scores, found_results))
                paired.sort(key=lambda x: x[0], reverse=True)
                found_results = [r for (s, r) in paired]

                total = len(found_results)
                total_pages = (total + page_size - 1) // page_size
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paged = found_results[start_idx:end_idx]
                result["list"] = paged
                result["pagecount"] = str(total_pages)
                result["total"] = str(total)

            return result
        except Exception:
            return result

    _sitemap_ids_cache = None

    def _get_sitemap_ids(self):
        """Get all series_ids from sitemap (cached)."""
        if self._sitemap_ids_cache is not None:
            return self._sitemap_ids_cache
        try:
            all_ids = []
            for i in [1, 2, 3]:
                url = f"{self.BASE_URL}/sitemap/hongguoduanju/index{i}.xml"
                html = self.getHtml(url)
                if html:
                    ids = re.findall(r'/detail\?series_id=(\d+)', html)
                    if not ids:
                        ids = re.findall(r'/player/(\d+)', html)
                    all_ids.extend(ids)
            all_ids = list(set(all_ids))
            self._sitemap_ids_cache = all_ids
            return all_ids
        except Exception:
            return []

    def playerContent(self, flag, id, vipFlags):
        # Handle id that may contain episode name (e.g., "第1集$URL")
        play_url = id
        if '$' in play_url:
            play_url = play_url.split('$', 1)[1]
        if not play_url.startswith("http"):
            play_url = self.BASE_URL + "/" + play_url.lstrip("/")

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        html = self.getHtml(play_url)
        if html:
            data = self._extract_ssr_data(html)
            if data:
                loader = data.get('loaderData', {})

                # Find the player page key
                player_page = None
                for key in loader:
                    if 'page' in key.lower() and 'player' in key.lower():
                        player_page = loader[key]
                        break

                if player_page:
                    video_player_info = player_page.get('video_player_info', {})
                    main_url = video_player_info.get('main_url', '')

                    if main_url:
                        if main_url.startswith("//"):
                            main_url = "https:" + main_url
                        # Check if it's a direct video URL (check path without query params)
                        parsed = urllib.parse.urlparse(main_url)
                        path_lower = parsed.path.lower()
                        is_direct = path_lower.endswith(".mp4") or path_lower.endswith(".m3u8")
                        # Also check if URL contains video markers
                        if not is_direct and ("video" in path_lower or "tos" in path_lower):
                            is_direct = True
                        return {
                            "url": main_url,
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