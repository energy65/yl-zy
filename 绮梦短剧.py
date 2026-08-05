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
    BASE_URL = "https://seeshorttv.cc/webpc"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 简介处加密信息（XOR 加密，运行时解密，源码无明文）
    _w_full_data = [148, 215, 195, 129, 209, 198, 186, 183, 156, 214, 138, 200, 142, 234, 206, 147, 233, 241, 131, 212, 247, 186, 184, 171, 218, 139, 240, 143, 222, 207, 151, 216, 234, 135, 238, 250, 176, 142, 188, 67, 209, 225, 207, 84, 73, 68, 93, 88, 92, 92, 86, 106, 0, 212, 142, 130, 182, 241, 234, 159, 234, 221, 136, 193, 244, 131, 227, 170, 216, 134, 158, 183, 222, 225, 159, 203, 249, 136, 213, 211, 130, 195, 154, 214, 136, 166, 186, 225, 254]
    # 线路处加密信息
    _w_line_data = [150, 210, 195, 131, 204, 193, 184, 173, 157, 215, 191, 248, 169, 210, 156, 207, 199, 137, 218, 207, 130, 218, 158, 212, 142, 161, 186, 228, 210, 159, 203, 249, 136, 239, 245, 143, 226, 157, 212, 137, 128, 185, 218, 226]
    _w_key = b"qimeng_2026_key"

    # 分类配置（Next.js SSR 站点，每页约30条，不支持服务端分页）
    CATEGORIES = [
        {"type_id": "short-drama", "type_name": "短剧"},
        {"type_id": "series", "type_name": "电视剧"},
        {"type_id": "movie", "type_name": "电影"},
        {"type_id": "variety", "type_name": "综艺"},
        {"type_id": "anime", "type_name": "动漫"},
        {"type_id": "home", "type_name": "首页推荐"},
    ]

    # contentKind 映射
    _KIND_MAP = {
        "SHORT_DRAMA": "短剧",
        "SERIES": "电视剧",
        "MOVIE": "电影",
        "VARIETY": "综艺",
        "ANIME": "动漫",
    }

    def init(self, extend=""):
        pass

    def getName(self):
        return "绮梦短剧"

    def _get_wechat_info(self):
        try:
            key = self._w_key
            data = self._w_full_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
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
                return '绮梦短剧'

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
                "Referer": self.BASE_URL
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

    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = html_mod.unescape(text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_flight(self, html):
        """提取 Next.js RSC flight data 并反转义"""
        if not html:
            return ''
        m = re.search(r'self\.__next_f\.push\(\[\d+,"(.*?)"\]\)', html, re.DOTALL)
        if not m:
            return ''
        payload = m.group(1)
        # RSC flight data 反转义
        return payload.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n').replace('\\t', '\t')

    def _parse_video_items(self, flight):
        """从 RSC flight data 提取视频列表"""
        videos = []
        seen_ids = set()
        if not flight:
            return videos
        # 视频对象模式：id, slug, title, subtitle, description, cover, poster, trailerUrl, status, releaseStatus
        pattern = re.compile(
            r'"id":"(cm[a-zA-Z0-9]+)","slug":"([^"]*)","title":"([^"]*)",'
            r'"subtitle":(null|"[^"]*"),'
            r'"description":"((?:[^"\\]|\\.)*)",'
            r'"cover":"([^"]*)","poster":"([^"]*)",'
            r'"trailerUrl":(null|"[^"]*"),'
            r'"status":"([^"]*)","releaseStatus":"([^"]*)"'
        )
        for m in pattern.finditer(flight):
            vid = m.group(1)
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            title = m.group(3)
            desc = m.group(5).replace('\\n', '\n').replace('\\"', '"')
            cover = m.group(6)
            release_status = m.group(10)
            # 在匹配位置之后查找 totalEpisodes 和 contentKind
            after = flight[m.end():m.end() + 1200]
            m_te = re.search(r'"totalEpisodes":(\d+)', after)
            m_ck = re.search(r'"contentKind":"([^"]*)"', after)
            total_eps = int(m_te.group(1)) if m_te else 0
            content_kind = m_ck.group(1) if m_ck else ''
            # 备注
            if total_eps > 0:
                remarks = f"{total_eps}集"
            else:
                remarks = "连载中" if release_status == "ONGOING" else "完结"
            # 分类名
            type_name = self._KIND_MAP.get(content_kind, '')
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_remarks": remarks,
                "vod_content": desc,
                "vod_class": type_name,
                "type_name": type_name,
            })
        return videos

    def _parse_video_links_from_html(self, html):
        """从 HTML <a> 标签提取视频链接和标题（补充 flight data 未覆盖的项）"""
        videos = []
        seen_ids = set()
        if not html:
            return videos
        pattern = re.compile(r'<a[^>]*href="/webpc/d/(cm[a-z0-9]+)"[^>]*>(.*?)</a>', re.DOTALL)
        for m in pattern.finditer(html):
            vid = m.group(1)
            if vid in seen_ids:
                continue
            content = m.group(2)
            # 提取标题：优先 <h3> 标签
            title = ''
            m_h3 = re.search(r'<h3[^>]*>(.*?)</h3>', content, re.DOTALL)
            if m_h3:
                title = self._clean_text(m_h3.group(1))
            if not title:
                # 备用：清理 HTML 标签后找 "播放{title}打开即看"
                text = re.sub(r'<[^>]+>', '', content).strip()
                m_play = re.search(r'播放(.+?)打开即看', text)
                if m_play:
                    title = m_play.group(1).strip()
                else:
                    text = re.sub(r'\d+集原创\s*', '', text)
                    text = re.sub(r'\d+集\s*', '', text)
                    text = re.sub(r'^播放\s*', '', text)
                    text = re.sub(r'打开即看[，，].*?绿色内容\s*', '', text)
                    text = re.sub(r'精选[\d.]+万\s*热度\s*$', '', text)
                    text = re.sub(r'查看详情\s*$', '', text)
                    text = re.sub(r'^[\d.]+万\s*热度\s*$', '', text)
                    text = text.strip()
                    if text and len(text) > 1 and text not in ('查看详情', '打开即看', '精选'):
                        title = text
            if title:
                seen_ids.add(vid)
                # 封面图
                m_img = re.search(r'<img[^>]+src="([^"]+)"', content)
                pic = m_img.group(1) if m_img else ''
                # 集数
                m_eps = re.search(r'(\d+)集', content)
                remarks = f"{m_eps.group(1)}集" if m_eps else ''
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                    "vod_content": "",
                    "vod_class": "",
                    "type_name": "",
                })
        return videos

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result
        flight = self._get_flight(html)
        videos = self._parse_video_items(flight)
        # 补充 HTML 链接中的项
        if len(videos) < 20:
            link_vids = self._parse_video_links_from_html(html)
            seen = set(v['vod_id'] for v in videos)
            for v in link_vids:
                if v['vod_id'] not in seen:
                    videos.append(v)
                    seen.add(v['vod_id'])
        result["list"] = videos[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            cid = str(tid)
            page = int(pg) if pg and str(pg).isdigit() else 1
            if page > 1:
                # 站点不支持服务端分页，第2页返回空
                return result

            if cid == "home":
                url = self.BASE_URL
            else:
                url = f"{self.BASE_URL}/category/{cid}"

            html = self.getHtml(url)
            if not html:
                return result

            flight = self._get_flight(html)
            videos = self._parse_video_items(flight)
            result["list"] = videos
            result["total"] = str(len(videos))
            result["pagecount"] = "1"
            return result
        except Exception:
            return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        try:
            url = f"{self.BASE_URL}/d/{vid}"
            html = self.getHtml(url)
            if not html:
                return result

            flight = self._get_flight(html)

            # 标题：优先 <h1>，其次 og:title
            title = ''
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
            if m:
                title = self._clean_text(m.group(1))
            if not title:
                m = re.search(r'"property":"og:title","content":"([^"]+)"', flight)
                if m:
                    title = m.group(1)
            if not title:
                m = re.search(r'<title>(.*?)\s*·\s*绮梦短剧', html)
                if m:
                    title = m.group(1)

            # 封面：og:image
            pic = ''
            m = re.search(r'"property":"og:image","content":"([^"]+)"', flight)
            if m:
                pic = m.group(1)
            if not pic:
                m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
                if m:
                    pic = m.group(1)

            # 简介：从 flight data 提取（className 含 mt-6 max-w-3xl 的 <p> children）
            intro = ''
            m = re.search(r'"className":"mt-6 max-w-3xl[^"]*","children":"((?:[^"\\]|\\.)*)"', flight)
            if m:
                intro = m.group(1).replace('\\n', '\n').replace('\\"', '"')
            if not intro:
                # 备用：从 HTML 提取长文本 <p>
                for m_p in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.DOTALL):
                    txt = self._clean_text(m_p.group(1))
                    if len(txt) > 30:
                        intro = txt
                        break

            # 集数：从 watch 链接提取
            eps = re.findall(r'/webpc/watch/' + re.escape(str(vid)) + r'/(\d+)', html)
            ep_nums = sorted(set(eps), key=int)

            # 总集数：从"共 X 集"提取
            total_eps = len(ep_nums)
            m = re.search(r'共\s*(\d+)\s*集', html)
            if m:
                total_eps = int(m.group(1))

            # 状态/备注
            remarks = f"共{total_eps}集" if total_eps > 0 else ''

            # 标签：从 HTML <span> 提取（全站免费/adult-movie/ChineseLanguage 等）
            tags = re.findall(r'<span[^>]*>(全站免费|adult-[a-z]+|ChineseLanguage|Ongoing|HookOpening|Romance|FantasyDrama|FemaleLead|RevengeDrama|PolyRelationship|SchoolLife|Love|Xuanhuan|Anthology|sensitive-subject|RomanceAngst|连载|完结)</span>', html)
            vod_class = ' '.join(list(set(tags))[:6]) if tags else ''

            # contentKind 映射
            m_ck = re.search(r'"contentKind":"([^"]*)"', flight)
            if m_ck:
                kind_name = self._KIND_MAP.get(m_ck.group(1), '')
                if kind_name:
                    if vod_class:
                        vod_class = kind_name + ' ' + vod_class
                    else:
                        vod_class = kind_name

            # 年份/地区（通常为"未知"）
            year = ''
            area = ''
            m = re.search(r'"children":"年份([^"]*)"', flight)
            if m:
                year = m.group(1).strip()
            m = re.search(r'"children":"地区([^"]*)"', flight)
            if m:
                area = m.group(1).strip()

            # 添加加密微信信息到简介
            wechat_info = self._get_wechat_info()
            if wechat_info:
                intro = (intro + '\n\n' + wechat_info) if intro else wechat_info

            # 线路信息
            line_info = self._get_line_info()

            # 播放列表
            play_groups = []
            if ep_nums:
                for ep_num in ep_nums:
                    play_groups.append(f"第{ep_num}集$/webpc/watch/{vid}/{ep_num}")
            else:
                play_groups.append(f"第1集$/webpc/watch/{vid}/1")

            vod = {
                "vod_id": str(vid),
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": "内详",
                "vod_director": "内详",
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_content": intro,
                "vod_class": vod_class,
                "type_name": vod_class,
                "vod_language": "",
                "vod_play_from": line_info,
                "vod_play_url": '#'.join(play_groups),
            }

            result['list'] = [vod]
            return result
        except Exception:
            return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            kw = (key or '').strip()
            if not kw:
                return result
            kw_lower = kw.lower()
            page = int(pg) if pg and str(pg).isdigit() else 1
            page_size = 30

            # 站内搜索不支持服务端渲染，改用分类页抓取 + 标题过滤
            all_items = []
            seen_ids = set()

            def add_videos(videos):
                for v in videos:
                    vid = v.get('vod_id', '')
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        all_items.append(v)

            # 抓取首页 + 所有分类页
            urls = [self.BASE_URL]
            for cid in ['short-drama', 'series', 'movie', 'variety', 'anime']:
                urls.append(f"{self.BASE_URL}/category/{cid}")

            for url in urls:
                html = self.getHtml(url)
                if not html:
                    continue
                flight = self._get_flight(html)
                vids = self._parse_video_items(flight)
                add_videos(vids)
                # 补充 HTML 链接中的项（覆盖 flight data 未展开的 RSC 引用）
                link_vids = self._parse_video_links_from_html(html)
                add_videos(link_vids)

            # 关键词匹配评分（5级）
            def score_match(item):
                name = (item.get('vod_name') or '').lower()
                desc = (item.get('vod_content') or '').lower()
                vclass = (item.get('vod_class') or '').lower()
                score = 0
                if not name:
                    return 0
                # 1. 标题完全匹配
                if kw_lower == name:
                    score += 100
                # 2. 标题部分匹配
                elif kw_lower in name:
                    score += 50
                # 3. 分类匹配
                if kw_lower in vclass:
                    score += 30
                # 4. 简介匹配
                if kw_lower in desc:
                    score += 15
                # 5. 字词片段匹配
                if score == 0:
                    kw_chars = [kw_lower[i:i + 2] for i in range(max(1, len(kw_lower) - 1))]
                    for chunk in kw_chars:
                        if chunk and chunk in name:
                            score += 1
                return score

            scored = []
            for v in all_items:
                s = score_match(v)
                if s > 0:
                    scored.append((s, v))

            scored.sort(key=lambda x: x[0], reverse=True)
            filtered = [v for (s, v) in scored]

            # 无匹配时返回热门内容作为兜底
            if not filtered and all_items:
                filtered = all_items[:page_size]

            if filtered:
                total = len(filtered)
                total_pages = (total + page_size - 1) // page_size
                start = (page - 1) * page_size
                end = start + page_size
                paged = filtered[start:end]
                result["list"] = paged
                result["pagecount"] = str(total_pages)
                result["total"] = str(total)

            return result
        except Exception:
            return result

    def playerContent(self, flag, id, vipFlags):
        play_url = id
        if '$' in play_url:
            play_url = play_url.split('$', 1)[1]
        if not play_url.startswith("http"):
            if play_url.startswith("/"):
                play_url = "https://seeshorttv.cc" + play_url
            else:
                play_url = "https://seeshorttv.cc/" + play_url

        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL,
            "Origin": "https://seeshorttv.cc",
            "Accept": "*/*",
        }

        try:
            html = self.getHtml(play_url)
            if html:
                flight = self._get_flight(html)
                # 从 flight data 提取 hlsUrl（mp4/m3u8 直链）
                m = re.search(r'"hlsUrl":"([^"]+)"', flight)
                if m:
                    video_url = m.group(1)
                    if video_url.startswith("//"):
                        video_url = "https:" + video_url
                    is_direct = ('.mp4' in video_url.lower()) or ('.m3u8' in video_url.lower())
                    return {
                        "url": video_url,
                        "parse": "0" if is_direct else "1",
                        "header": json.dumps(play_headers),
                        "playUrl": "",
                        "subtitle": ""
                    }
                # 备用：从原始 HTML 搜索 mp4/m3u8 链接
                m = re.search(r'(https?://[^\s"\\]+\.mp4[^\s"\\]*)', html)
                if m:
                    return {
                        "url": m.group(1),
                        "parse": "0",
                        "header": json.dumps(play_headers),
                        "playUrl": "",
                        "subtitle": ""
                    }
        except Exception:
            pass

        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": ""
        }

    def __jsEvalReturn(self):
        return {"proxy": None}
