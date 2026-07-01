"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'NO视频',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
from urllib.parse import quote
from base.spider import Spider as BaseSpider


def _attr(html, name):
    pat = r'{}\s*=\s*"([^"]+)"'.format(name)
    m = re.search(pat, html)
    if m:
        return m.group(1).strip()
    pat2 = r'{}\s*=\s*\'([^\']+)\''.format(name)
    m2 = re.search(pat2, html)
    if m2:
        return m2.group(1).strip()
    pat3 = r'{}\s*=\s*(\S+)'.format(name)
    m3 = re.search(pat3, html)
    if m3:
        v = m3.group(1).strip()
        if v and v[0] not in ('"', "'"):
            return v
    return ''


class Spider(BaseSpider):
    def init(self, extend=""):
        self.domains = [
            "https://www.novipnoad.ca",
            "https://novipnoad.ca",
            "https://www.novipnoad.net",
            "https://novipnoad.net",
            "https://www.novipnoad.com",
            "https://novipnoad.com",
        ]
        self.host = self.domains[0]
        self.domain_index = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        self.categories = [
            {'type_id': 'movie', 'type_name': '电影'},
            {'type_id': 'tv/hongkong', 'type_name': '港剧'},
            {'type_id': 'tv/taiwan', 'type_name': '台剧'},
            {'type_id': 'tv/western', 'type_name': '欧美剧'},
            {'type_id': 'tv/japan', 'type_name': '日剧'},
            {'type_id': 'tv/korea', 'type_name': '韩剧'},
            {'type_id': 'tv/thailand', 'type_name': '泰剧'},
            {'type_id': 'tv/turkey', 'type_name': '土耳其剧'},
            {'type_id': 'anime', 'type_name': '动画'},
            {'type_id': 'shows', 'type_name': '综艺'},
            {'type_id': 'music', 'type_name': '音乐'},
            {'type_id': 'short', 'type_name': '短片'},
            {'type_id': 'other', 'type_name': '其他'},
        ]

    def getName(self):
        return 'NO视频'

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        html = self._fetch('/')
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = '/{}/'.format(tid)
        else:
            url = '/{}/page/{}/'.format(tid, page)
        html = self._fetch(url)
        items = self._parse_video_list(html)
        page_count = page if len(items) < 16 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 16, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            path = vid
            if '/' not in vid:
                path = self._find_path(vid)
            if not path:
                return result

            html = self._fetch('/{}.html'.format(path))
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m_name:
                vod_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('_')[0].strip()

            vod_pic = ''
            m_pic = re.search(r'<meta[^>]*property=["\']?og:image["\']?[^>]*content=["\']?([^"\'\s>]+)', html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()
            if not vod_pic:
                m_pic2 = re.search(r'data-original=["\']?(https?://[^"\'\s>]+)', html)
                if m_pic2:
                    vod_pic = m_pic2.group(1).strip()

            vod_director = ''
            vod_actor = ''
            vod_year = ''
            vod_area = ''
            vod_remarks = ''

            year_m = re.search(r'[（(](\d{4})[）)]', vod_name)
            if year_m:
                vod_year = year_m.group(1)

            m_status = re.search(r'(\d+集全|更新至\d+集|连载中|已完结)', vod_name)
            if m_status:
                vod_remarks = m_status.group(1)

            vod_content = ''
            m_desc = re.search(r'<meta[^>]*name=["\']?description["\']?[^>]*content=["\']?([^"\'>]+)', html)
            if m_desc:
                vod_content = m_desc.group(1).strip()
            if not vod_content:
                m_content = re.search(r'<div[^>]*class=["\']?item-content[^>]*>\s*<p[^>]*>(.*?)</p>', html, re.S)
                if m_content:
                    content = m_content.group(1)
                    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.S)
                    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
                    content = re.sub(r'<[^>]+>', '', content).strip()
                    if len(content) > 10:
                        vod_content = content

            play_from = []
            play_url = []

            play_info_m = re.search(r'window\.playInfo\s*=\s*(\{[^}]+\})', html)
            if play_info_m:
                play_from.append('NO视频')
                play_url.append('正片${}'.format(path))

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
                "vod_play_from": '$$$'.join(play_from),
                "vod_play_url": '$$$'.join(play_url),
            }
            result['list'].append(vod)
        except Exception as e:
            print('detailContent error: {}'.format(e))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "playUrl": "", "url": "", "header": ""}
        try:
            path = id
            if not path.endswith('.html'):
                path = path + '.html'
            if not path.startswith('/'):
                path = '/' + path
            result["url"] = self.host + path
            result["parse"] = 1
            result["header"] = json.dumps({
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/"
            })
        except Exception as e:
            print('playerContent error: {}'.format(e))
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = '/?s={}'.format(quote(key))
        else:
            url = '/page/{}/?s={}'.format(page, quote(key))
        html = self._fetch(url)
        items = self._parse_video_list(html)
        return {"list": items, "page": page, "pagecount": 9999, "limit": 10, "total": 99999}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        html = ''
        for i in range(len(self.domains)):
            try:
                idx = (self.domain_index + i) % len(self.domains)
                domain = self.domains[idx]
                if url.startswith('http'):
                    full_url = url
                else:
                    full_url = domain + url
                headers = dict(self.headers)
                headers["Referer"] = domain + "/"
                rsp = self.fetch(full_url, headers=headers)
                if rsp and rsp.text:
                    text = rsp.text
                    if 'video-item' in text or 'window.playInfo' in text or '<h1' in text:
                        self.domain_index = idx
                        self.host = domain
                        return text
                    if not html and len(text) > 1000:
                        html = text
            except:
                pass
        return html

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            items = re.findall(
                r'(<div[^>]*class=["\']?[^"\'>]*video-item[^"\'>]*["\']?[^>]*>.*?)(?=<div[^>]*class=["\']?[^"\'>]*video-item|<div[^>]*class=["\']?wp-pagenavi|$)',
                html, re.S
            )
            if not items:
                items = re.findall(
                    r'<div[^>]*class=["\']?[^"\'>]*video-item[^"\'>]*["\']?[^>]*>(.*?)</div>\s*</div>\s*</div>',
                    html, re.S
                )

            for item in items:
                href = ''
                title = ''
                pic = ''

                m_h3 = re.search(r'<h\d[^>]*>\s*<a[^>]*href=["\']?([^"\'\s>]+)[^>]*>([^<]+)</a>', item)
                if m_h3:
                    href = m_h3.group(1).strip()
                    title = m_h3.group(2).strip()

                if not title:
                    m_thumb_a = re.search(r'<div[^>]*class=["\']?item-thumbnail[^>]*>\s*<a[^>]*href=["\']?([^"\'\s>]+)', item)
                    if m_thumb_a:
                        href = m_thumb_a.group(1).strip()

                if not title:
                    title = _attr(item, 'title')
                    if title and ('<h' in title or '<div' in title):
                        title = ''

                m_pic = re.search(r'data-original=["\']?([^"\'\s>]+)', item)
                if not m_pic:
                    m_pic = re.search(r'src=["\']?(https?://[^"\'\s>]+upload/[^"\'\s>]+)', item)
                if m_pic:
                    pic = m_pic.group(1).strip()

                if not pic or 'loading.png' in pic:
                    pic = ''

                path = ''
                if href and '.html' in href:
                    found_host = None
                    for d in self.domains:
                        if d in href:
                            found_host = d
                            break
                    if found_host:
                        m_path = re.search(r'{}/(.+\.html)'.format(re.escape(found_host)), href)
                        if m_path:
                            path = m_path.group(1).replace('.html', '')
                    if not path:
                        m_path = re.search(r'/{0,1}(.+\.html)', href)
                        if m_path:
                            path = m_path.group(1).replace('.html', '')

                if not path:
                    continue

                vid = path
                if vid in seen:
                    continue
                if not title or len(title) < 2:
                    continue

                seen.add(vid)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic if pic else '',
                    "vod_remarks": '',
                })
        except Exception as e:
            print('_parse_video_list error: {}'.format(e))
        return videos

    def _find_path(self, vid):
        try:
            for cat in self.categories:
                tid = cat['type_id']
                test_path = '{}/{}'.format(tid, vid)
                html = self._fetch('/{}.html'.format(test_path))
                if html and len(html) > 5000:
                    if 'window.playInfo' in html or '<h1' in html:
                        return test_path
            return vid
        except:
            return vid
