"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '袋鼠影视',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
from urllib.parse import quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://dsystv.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Referer": "https://dsystv.com/",
        }

    def getName(self):
        return '袋鼠影视'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/index.php')
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = f'/frim/index{tid}.html'
        else:
            url = f'/frim/index{tid}-{page}.html'
        html = self._fetch(url)
        items = self._parse_video_list(html)
        page_count = page if len(items) < 24 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 24, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            html = self._fetch(f'/movie/index{vid}.html')
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m_name:
                vod_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()

            vod_pic = ''
            m_pic = re.search(r'<a[^>]*class="[^"]*videopic[^"]*"[^>]*>.*?data-original="([^"]+)"', html, re.S)
            if m_pic:
                vod_pic = m_pic.group(1).strip()
            if not vod_pic:
                m_pic = re.search(r'<img[^>]*data-original="([^"]+)"', html)
                if m_pic:
                    vod_pic = m_pic.group(1).strip()
            if not vod_pic:
                m_pic = re.search(r'background:\s*url\(["\']?([^)"\']+)["\']?\)', html)
                if m_pic:
                    vod_pic = m_pic.group(1).strip()

            vod_director = ''
            m_dir = re.search(r'导演[：:]\s*([^<]+)</', html)
            if m_dir:
                vod_director = m_dir.group(1).strip()

            vod_actor = ''
            m_act = re.search(r'主演[：:]\s*([^<]+)</', html)
            if m_act:
                vod_actor = m_act.group(1).strip()

            vod_year = ''
            m_year = re.search(r'年份[：:]\s*([^<]+)</', html)
            if m_year:
                vod_year = m_year.group(1).strip()

            vod_area = ''
            m_area = re.search(r'地区[：:]\s*([^<]+)</', html)
            if m_area:
                vod_area = m_area.group(1).strip()

            vod_remarks = ''
            m_rem = re.search(r'class="note[^"]*">([^<]+)</span>', html)
            if m_rem:
                vod_remarks = m_rem.group(1).strip()

            vod_content = ''
            m_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
            if m_desc:
                vod_content = m_desc.group(1).strip()
            if not vod_content:
                m_plot = re.search(r'class="plot"[^>]*>(.*?)</div>', html, re.S)
                if m_plot:
                    vod_content = re.sub(r'<[^>]+>', '', m_plot.group(1)).strip()

            play_from = []
            play_url = []

            panels = re.findall(r'<div[^>]*class="panel[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S)
            if not panels:
                panels = re.findall(r'<div[^>]*class="panel[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S)

            for panel in panels:
                source_name = ''
                m_src = re.search(r'<a[^>]*class="option"[^>]*title="([^"]+)"', panel)
                if m_src:
                    source_name = m_src.group(1).strip()
                if not source_name:
                    m_src = re.search(r'<a[^>]*class="option"[^>]*>(.*?)</a>', panel, re.S)
                    if m_src:
                        source_name = re.sub(r'<[^>]+>', '', m_src.group(1)).strip().split()[0] if m_src.group(1).strip() else ''
                if not source_name:
                    continue

                eps = []
                ep_items = re.findall(r'<a[^>]*href="(/play/[^"]+\.html)"[^>]*>([^<]+)</a>', panel)
                if not ep_items:
                    ep_items = re.findall(r'href="(/play/[^"]+\.html)"[^>]*title="([^"]+)"', panel)

                for ep_href, ep_name in ep_items:
                    ep_id = ep_href.replace('/play/', '').replace('.html', '')
                    eps.append(f'{ep_name.strip()}${ep_id}')

                if eps:
                    play_from.append(source_name)
                    play_url.append('#'.join(eps))

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
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            html = self._fetch(f'/play/{id}.html')
            if html:
                m = re.search(r'var\s+now\s*=\s*"([^"]+)"', html)
                if m:
                    result["url"] = m.group(1)
                    result["parse"] = 0
        except Exception as e:
            print(f'playerContent error: {e}')
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f'/search.php?searchword={quote(key)}&page={page}'
        html = self._fetch(url)
        items = self._parse_video_list(html)
        return {"list": items, "page": page, "pagecount": 9999, "limit": 20, "total": 99999}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        try:
            if not url.startswith('http'):
                url = self.host + url
            rsp = self.fetch(url, headers=self.headers)
            return rsp.text if rsp else ''
        except:
            return ''

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            items = re.findall(
                r'<a[^>]*class="[^"]*videopic[^"]*"[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>',
                html, re.S
            )

            for href, title, rest in items:
                vid = ''
                m_vid = re.search(r'/movie/index(\d+)\.html', href)
                if m_vid:
                    vid = m_vid.group(1)
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                title = title.strip()
                if not title:
                    continue

                pic = ''
                m_pic = re.search(r'data-original="([^"]+)"', rest)
                if not m_pic:
                    m_pic = re.search(r'<img[^>]*src="([^"]+)"', rest)
                if not m_pic:
                    m_pic = re.search(r'url\(["\']?([^)"\']+)["\']?\)', rest)
                if m_pic:
                    pic = m_pic.group(1).strip()

                remarks = ''
                m_rem = re.search(r'class="note[^"]*">([^<]+)</span>', rest)
                if m_rem:
                    remarks = m_rem.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print(f'_parse_video_list error: {e}')
        return videos
