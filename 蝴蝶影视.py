"""
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '蝴蝶影视',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
from urllib.parse import quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.gskfzxyy.com"
        self.backup_host = "https://www.ahshfshygzc.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.61 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }
        self.categories = {
            '1': '电影',
            '2': '电视剧',
            '3': '综艺',
            '4': '动漫',
            '20': '短剧',
            '35': '动画片',
            '36': '4K电影',
            '37': 'Netflix作品',
        }

    def getName(self):
        return '蝴蝶影视'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '20', 'type_name': '短剧'},
            {'type_id': '35', 'type_name': '动画片'},
            {'type_id': '36', 'type_name': '4K电影'},
            {'type_id': '37', 'type_name': 'Netflix作品'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/')
        items = self._parse_list(html)
        return {"list": items[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f'/vodtype/{tid}.html'
        if page > 1:
            url = f'/vodtype/{tid}_{page}.html'
        html = self._fetch(url)
        items = self._parse_list(html)
        page_count = page if len(items) < 20 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            detail_url = vid if vid.startswith('http') else self.host + vid
            html = self._fetch(detail_url if vid.startswith('http') else vid)
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if m_name:
                vod_name = m_name.group(1).strip()
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('_')[0].replace('《', '').replace('》', '').strip()

            vod_pic = ''
            m_pic = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()
            if not vod_pic:
                m_pic = re.search(r'<img[^>]+class=["\']poster["\'][^>]+src=["\']([^"\']+)["\']', html, re.I)
            if not vod_pic:
                m_pic = re.search(r'<img[^>]+src=["\']([^"\']+\.(jpg|png|webp))["\'][^>]*alt', html, re.I)
            if m_pic:
                vod_pic = m_pic.group(1).strip()
            if vod_pic and vod_pic.startswith('//'):
                vod_pic = 'https:' + vod_pic
            if vod_pic and vod_pic.startswith('/'):
                vod_pic = self.host + vod_pic

            vod_director = ''
            vod_actor = ''
            vod_year = ''
            vod_area = ''
            vod_remarks = ''
            vod_content = ''
            vod_class = ''

            info_patterns = [
                (r'<span>导演[：:]</span>\s*<a[^>]+>([^<]+)</a>', 'director'),
                (r'<span>主演[：:]</span>\s*<a[^>]+>([^<]+)</a>', 'actor'),
                (r'<span>演员[：:]</span>\s*<a[^>]+>([^<]+)</a>', 'actor'),
                (r'<span>年份[：:]</span>\s*([^<\n]+)', 'year'),
                (r'<span>上映时间[：:]</span>\s*([^<\n]+)', 'year'),
                (r'<span>地区[：:]</span>\s*<a[^>]+>([^<]+)</a>', 'area'),
                (r'<span>类型[：:]</span>\s*([^<\n]+)', 'class'),
                (r'<span>状态[：:]</span>\s*([^<\n]+)', 'remarks'),
            ]

            for pattern, field in info_patterns:
                m = re.search(pattern, html)
                if m:
                    text = m.group(1).strip()
                    text = re.sub(r'<[^>]+>', '', text)
                    text = re.sub(r'\s+', ' ', text)
                    text = text.replace('&nbsp;', ' ')
                    if field == 'director':
                        vod_director = text
                    elif field == 'actor':
                        vod_actor = text
                    elif field == 'year':
                        vod_year = text[:4] if len(text) >= 4 else text
                    elif field == 'area':
                        vod_area = text
                    elif field == 'class':
                        vod_class = text
                    elif field == 'remarks':
                        vod_remarks = text

            if not vod_actor:
                actor_links = re.findall(r'<span>主演[：:]</span>\s*(.*?)(?=<div|<ul|<p)', html, re.S)
                if actor_links:
                    actors = re.findall(r'<a[^>]+>([^<]+)</a>', actor_links[0])
                    vod_actor = ' '.join(actors)

            if not vod_class:
                type_links = re.findall(r'<span>类型[：:]</span>\s*(.*?)(?=</li|<p)', html, re.S)
                if type_links:
                    types = re.findall(r'<a[^>]+>([^<]+)</a>', type_links[0])
                    vod_class = ' '.join(types)

            m_content = re.search(r'<div[^>]*class=["\']desc["\'][^>]*>([\s\S]*?)</div>', html, re.I)
            if not m_content:
                m_content = re.search(r'剧情简介[\s\S]*?<p[^>]*>([\s\S]*?)</p>', html, re.I)
            if not m_content:
                m_content = re.search(r'剧情[：:][\s\S]*?(?=<div|<p|<h|<br)', html)
            if m_content:
                vod_content = re.sub(r'<[^>]+>', '', m_content.group(1)).strip()
                vod_content = vod_content.replace('更多', '').strip()

            vod_content = vod_content + '\n\n微信公众号：源力软件汇'

            if not vod_remarks:
                m_remarks2 = re.search(r'(更新至[^<]+|HD|BD|4K|正片|已完结|全\d+集|完结)', html)
                if m_remarks2:
                    vod_remarks = m_remarks2.group(1).strip()

            play_from_list = []
            play_url_list = []

            play_links = re.findall(r'<a[^>]+href=["\'](/vodplay/\d+-\d+-\d+\.html)["\'][^>]*>([^<]+)</a>', html)
            if play_links:
                eps = []
                for href, title in play_links[:60]:
                    eps.append(f'{title.strip()}${href}')
                if eps:
                    play_from_list.append('云播资源')
                    play_url_list.append('#'.join(eps))

            if not play_url_list:
                detail_match = re.search(r'/voddetail/(\d+)\.html', vid)
                if detail_match:
                    movie_id = detail_match.group(1)
                    play_url = f'/vodplay/{movie_id}-1-1.html'
                    play_from_list.append('云播资源')
                    play_url_list.append(f'正片${play_url}')

            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_director": vod_director,
                "vod_actor": vod_actor,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_remarks": vod_remarks,
                "vod_content": vod_content,
                "vod_class": vod_class,
                "vod_play_from": '$$$'.join(play_from_list) if play_from_list else '蝴蝶影视',
                "vod_play_url": '$$$'.join(play_url_list),
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            play_url = ''
            if id.startswith('http'):
                if '.m3u8' in id:
                    play_url = id
                else:
                    play_page = id
                    html = self._fetch(play_page)
                    if html:
                        play_url = self._extract_m3u8(html)
            elif id.startswith('/'):
                play_page = self.host + id
                html = self._fetch(play_page)
                if html:
                    play_url = self._extract_m3u8(html)
            else:
                play_page = self.host + '/' + id
                html = self._fetch(play_page)
                if html:
                    play_url = self._extract_m3u8(html)

            if play_url:
                if play_url.startswith('//'):
                    play_url = 'https:' + play_url
                if play_url.startswith('http'):
                    result["url"] = play_url
                    result["parse"] = 0

                    play_headers = {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    }
                    result["header"] = json.dumps(play_headers)
                else:
                    result["url"] = self.host + play_url if play_url.startswith('/') else play_url
                    result["parse"] = 1
        except Exception as e:
            print(f'playerContent error: {e}')
        return result

    def _extract_m3u8(self, html):
        import json
        
        idx = html.find('player_aaaa=')
        if idx != -1:
            start = idx + len('player_aaaa=')
            end = html.find('</script>', start)
            if end != -1:
                json_str = html[start:end].strip()
                json_str = json_str.rstrip(';')
                try:
                    data = json.loads(json_str)
                    url = data.get('url', '')
                    if url and url.startswith('http') and '.m3u8' in url:
                        return url
                except:
                    pass

        m3u8_patterns = [
            r'["\']url["\']\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'playUrl\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'surl\s*=\s*["\']([^"\']+)["\']',
            r'videoUrl\s*[=:]\s*["\']([^"\']+)["\']',
            r'data-video-url=["\']([^"\']+)["\']',
        ]

        for pat in m3u8_patterns:
            m = re.search(pat, html, re.I)
            if m:
                url = m.group(1).strip()
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('http'):
                    return url
                if url.startswith('/'):
                    return self.host + url

        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        m_iframe = re.search(iframe_pattern, html, re.I)
        if m_iframe:
            iframe_src = m_iframe.group(1).strip()
            if iframe_src.startswith('//'):
                iframe_src = 'https:' + iframe_src
            if iframe_src.startswith('http'):
                iframe_html = self._fetch(iframe_src)
                if iframe_html:
                    return self._extract_m3u8(iframe_html)

        return ''

    def searchContent(self, key, quick, pg="1"):
        try:
            search_url = f'/vodsearch/-------------.html?wd={quote(key)}'
            page = int(pg) if pg and str(pg).isdigit() else 1
            if page > 1:
                search_url = f'/vodsearch/-------------.html?wd={quote(key)}&page={page}'
            html = self._fetch(search_url)
            items = self._parse_search_list(html)
            page_count = page if len(items) < 20 else page + 2
            return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}
        except Exception as e:
            print(f'searchContent error: {e}')
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def localProxy(self, param=''):
        return {}

    def _fetch(self, url):
        try:
            if url.startswith('http'):
                full_url = url
            else:
                full_url = self.host + url
            headers = dict(self.headers)
            headers["Referer"] = self.host + "/"
            rsp = self.fetch(full_url, headers=headers)
            if rsp and rsp.status_code == 200:
                return rsp.text
            if self.backup_host != self.host:
                full_url = full_url.replace(self.host, self.backup_host)
                rsp = self.fetch(full_url, headers=headers)
                if rsp and rsp.status_code == 200:
                    return rsp.text
            return ''
        except Exception as e:
            print(f'_fetch error: {e}')
            return ''

    def _parse_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            vid_title_map = {}
            all_a_tags = re.findall(r'<a[^>]+href=["\'](/voddetail/\d+\.html)["\'][^>]*title=["\']([^"\']+)["\'][^>]*>', html)
            for vid, title in all_a_tags:
                if vid and title and len(title) > 2:
                    vid_title_map[vid] = title.strip()

            articles = re.findall(r'<article[^>]*class=["\'][^"\']*video-list[^"\']*["\'][^>]*>([\s\S]*?)</article>', html, re.I)

            for article in articles:
                m_href = re.search(r'<a[^>]+href=["\'](/voddetail/\d+\.html)["\']', article)
                if not m_href:
                    continue

                vid = m_href.group(1)
                if vid in seen:
                    continue
                seen.add(vid)

                title = vid_title_map.get(vid, '')
                
                if not title:
                    m_title_attr = re.search(r'<a[^>]+title=["\']([^"\']+)["\'][^>]*href=["\']/voddetail/', article)
                    if m_title_attr:
                        title = m_title_attr.group(1).strip()

                if not title:
                    a_text = re.search(r'<a[^>]+href=["\']/voddetail/\d+\.html["\'][^>]*>([\s\S]*?)</a>', article)
                    if a_text:
                        full_text = re.sub(r'<[^>]+>', '', a_text.group(1)).strip()
                        full_text = re.sub(r'\s+', ' ', full_text)
                        parts = full_text.split(' ')
                        clean_parts = []
                        for part in parts:
                            if part and part not in ['更新HD', '更新', 'HD', 'BD', '4K'] and not part.startswith('更新第'):
                                clean_parts.append(part)
                        if clean_parts:
                            title = ''.join(clean_parts)

                if not title:
                    m_voddate = re.search(r'<em[^>]*class=["\'][^"\']*voddate[^"\']*["\'][^>]*>([^<]+)</em>', article)
                    m_video_title = re.search(r'<span[^>]*class=["\'][^"\']*video-title[^"\']*["\'][^>]*>([^<]+)</span>', article)
                    voddate = m_voddate.group(1).strip() if m_voddate else ''
                    video_title = m_video_title.group(1).strip() if m_video_title else ''
                    combined = f"{voddate} {video_title}".strip()
                    if combined and len(combined) > 2:
                        title = combined

                if not title or len(title) < 2:
                    continue

                pic = ''
                m_pic = re.search(r'data-original=["\']([^"\']+)["\']', article, re.I)
                if not m_pic:
                    m_pic = re.search(r'data-src=["\']([^"\']+)["\']', article, re.I)
                if not m_pic:
                    m_pic = re.search(r'src=["\']([^"\']+)["\']', article, re.I)
                if m_pic:
                    pic = m_pic.group(1).strip()
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_video_title = re.search(r'<span[^>]*class=["\'][^"\']*video-title[^"\']*["\'][^>]*>([^<]+)</span>', article)
                if m_video_title:
                    remarks = m_video_title.group(1).strip()
                if not remarks:
                    m_voddate = re.search(r'<em[^>]*class=["\'][^"\']*voddate[^"\']*["\'][^>]*>([^<]+)</em>', article)
                    if m_voddate:
                        remarks = m_voddate.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })

        except Exception as e:
            print(f'_parse_list error: {e}')
        return videos

    def _parse_search_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            articles = re.findall(r'<article[^>]*>([\s\S]*?)</article>', html, re.I)

            for article in articles:
                m_href = re.search(r'<a[^>]+href=["\'](/voddetail/\d+\.html)["\']', article)
                if not m_href:
                    continue

                vid = m_href.group(1)
                if vid in seen:
                    continue
                seen.add(vid)

                title = ''
                m_title = re.search(r'title=["\']([^"\']+)["\']', article)
                if m_title:
                    title = m_title.group(1).strip()
                if not title:
                    m_title2 = re.search(r'<span[^>]*class=["\']entry-title["\'][^>]*>\s*<a[^>]*>([^<]+)</a>', article, re.I)
                    if m_title2:
                        title = m_title2.group(1).strip()

                if not title or len(title) < 2:
                    continue

                pic = ''
                m_pic = re.search(r'data-original=["\']([^"\']+)["\']', article, re.I)
                if not m_pic:
                    m_pic = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', article, re.I)
                if m_pic:
                    pic = m_pic.group(1).strip()
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_update = re.search(r'更新[：:]\s*([^<\n]+)', article)
                if m_update:
                    remarks = m_update.group(1).strip()[:20]
                if not remarks:
                    m_label = re.search(r'<em[^>]*class=["\']voddate[^"\']*["\'][^>]*>([^<]+)</em>', article, re.I)
                    if m_label:
                        remarks = m_label.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })

        except Exception as e:
            print(f'_parse_search_list error: {e}')
        return videos