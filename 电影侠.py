"""
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '电影侠',
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
        self.host = "https://www.dyx00.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.61 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }
        self.categories = {
            '1': '电影',
            '2': '连续剧',
            '3': '动漫',
            '4': '综艺纪录',
            '6': '短剧',
        }

    def getName(self):
        return '电影侠'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '连续剧'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺纪录'},
            {'type_id': '6', 'type_name': '短剧'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/')
        items = self._parse_list(html)
        return {"list": items[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f'/channel/{tid}.html'
        if page > 1:
            url = f'/channel/{tid}_{page}.html'
        html = self._fetch(url)
        items = self._parse_list(html)
        page_count = page if len(items) < 20 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) else str(ids)
        try:
            if vid.startswith('/') or vid.startswith('http'):
                if vid.startswith('http'):
                    detail_url = vid
                else:
                    detail_url = self.host + vid
            else:
                detail_url = f'{self.host}/detail/{vid}.html'
            
            html = self._fetch(detail_url)
            if not html:
                return result

            vod_name = ''
            m_detail_title = re.search(r'<div[^>]*class=["\']detail-title["\'][^>]*>([\s\S]*?)</div>', html)
            if m_detail_title:
                title_content = m_detail_title.group(1)
                strong_tags = re.findall(r'<strong>([^<]+)</strong>', title_content)
                for tag in strong_tags:
                    tag_clean = tag.strip()
                    if tag_clean and len(tag_clean) > 2 and not (tag_clean.startswith('𝕜') or tag_clean.startswith('kkys')):
                        vod_name = tag_clean
                        break

            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('-')[0].strip()

            if not vod_name:
                m_name = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if m_name:
                    vod_name = m_name.group(1).strip()

            vod_pic = ''
            lazy_imgs = re.findall(r'<img[^>]+class=["\'][^"\']*lazy[^"\']*["\'][^>]*data-original=["\']([^"\']+)["\']', html, re.I)
            for img in lazy_imgs:
                img_clean = img.strip()
                if img_clean and 'placeholder' not in img_clean.lower() and 'logo' not in img_clean.lower():
                    vod_pic = img_clean
                    break

            if not vod_pic:
                m_pic = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
                if m_pic:
                    vod_pic = m_pic.group(1).strip()

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

            m_content = re.search(r'<div[^>]*class=["\'][^"\']*desc[^"\']*["\'][^>]*>([\s\S]*?)</div>', html, re.I)
            if not m_content:
                m_content = re.search(r'剧情简介[\s\S]*?<p[^>]*>([\s\S]*?)</p>', html, re.I)
            if not m_content:
                m_content = re.search(r'<div[^>]*class=["\'][^"\']*detail-content[^"\']*["\'][^>]*>([\s\S]*?)</div>', html, re.I)
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

            source_items = re.findall(r'<a[^>]+class=["\']source-item[^"\']*["\'][^>]*>([\s\S]*?)</a>', html)
            episode_lists = re.findall(r'<div[^>]*class=["\']episode-list["\'][^>]*>([\s\S]*?)</div>', html)

            for idx, source_item in enumerate(source_items):
                source_name = ''
                m_label = re.search(r'<span[^>]*class=["\']source-item-label["\'][^>]*>([^<]+)</span>', source_item)
                if m_label:
                    source_name = m_label.group(1).strip()
                if not source_name:
                    source_name = f'线路{idx + 1}'

                if idx < len(episode_lists):
                    episode_list = episode_lists[idx]
                    eps = []
                    ep_links = re.findall(r'<a[^>]+href=["\'](/play/\d+-\d+-\d+\.html)["\'][^>]*>([\s\S]*?)</a>', episode_list)
                    for href, content in ep_links[:60]:
                        title = re.sub(r'<[^>]+>', '', content).strip()
                        if title:
                            eps.append(f'{title}${href}')
                    if eps:
                        play_from_list.append(source_name)
                        play_url_list.append('#'.join(eps))

            if not play_url_list:
                detail_match = re.search(r'/detail/(\d+)\.html', detail_url)
                if detail_match:
                    movie_id = detail_match.group(1)
                    play_url = f'/play/{movie_id}-1-1.html'
                    play_from_list.append('默认线路')
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
                "vod_play_from": '$$$'.join(play_from_list) if play_from_list else '电影侠',
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
        patterns = [
            r'src:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'url:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'playUrl\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        for pat in patterns:
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
            search_url = f'/search?k={quote(key)}&t=KBiVyDnKlJpM7AdDjEhZPA%3D%3D'
            page = int(pg) if pg and str(pg).isdigit() else 1
            if page > 1:
                search_url = f'/search?k={quote(key)}&t=KBiVyDnKlJpM7AdDjEhZPA%3D%3D&page={page}'
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
            rsp = self.fetch(full_url, headers=headers, timeout=30)
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

            v_item_pattern = r'<a[^>]+href=["\'](/detail/\d+\.html)["\'][^>]*class=["\']v-item["\'][^>]*>([\s\S]*?)</a>'
            v_items = re.findall(v_item_pattern, html)

            for vid, content in v_items:
                if vid in seen:
                    continue
                seen.add(vid)

                title = ''
                v_title_divs = re.findall(r'<div[^>]*class=["\']v-item-title["\'][^>]*>([^<]+)</div>', content)
                for t in v_title_divs:
                    t_clean = t.strip()
                    if t_clean and '可可影视' not in t_clean:
                        title = t_clean
                        break

                if not title or len(title) < 2:
                    continue

                pic = ''
                originals = re.findall(r'data-original=["\']([^"\']+)["\']', content)
                for orig in originals:
                    orig = orig.strip()
                    if orig and 'placeholder' not in orig.lower() and 'logo' not in orig.lower():
                        pic = orig
                        break

                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_bottom = re.search(r'<div[^>]*class=["\']v-item-bottom["\'][^>]*>([\s\S]*?)</div>', content)
                if m_bottom:
                    remarks = re.sub(r'<[^>]+>', '', m_bottom.group(1)).strip()

                if not remarks:
                    m_score = re.search(r'<span>(豆瓣:\d+\.\d+分)</span>', content)
                    if m_score:
                        remarks = m_score.group(1).strip()

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

            items = re.findall(r'<a[^>]+href=["\'](/detail/\d+\.html)["\'][^>]*class=["\']search-result-item["\'][^>]*>([\s\S]*?)</a>', html)
            for vid, item_content in items:
                if vid in seen:
                    continue
                seen.add(vid)

                title = ''
                m_title = re.search(r'<div[^>]*class=["\']title["\'][^>]*>([^<]+)</div>', item_content)
                if m_title:
                    title = m_title.group(1).strip()

                if not title:
                    m_title_attr = re.search(r'title=["\']([^"\']+)["\']', item_content)
                    if m_title_attr:
                        title = m_title_attr.group(1).strip()

                if not title or len(title) < 2:
                    continue

                pic = ''
                m_pic = re.search(r'data-original=["\']([^"\']+)["\']', item_content, re.I)
                if not m_pic:
                    m_pic = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', item_content, re.I)
                if m_pic:
                    pic = m_pic.group(1).strip()
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_tags = re.search(r'<div[^>]*class=["\']tags["\'][^>]*>([\s\S]*?)</div>', item_content)
                if m_tags:
                    tags_text = re.sub(r'<[^>]+>', '', m_tags.group(1)).strip()
                    parts = tags_text.split('/')
                    if parts:
                        remarks = parts[0].strip()[:20]

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })

        except Exception as e:
            print(f'_parse_search_list error: {e}')
        return videos