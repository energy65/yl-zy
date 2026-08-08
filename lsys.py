"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '绿色影视',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
import time
import base64
import urllib3
import requests
from urllib.parse import quote
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from base.spider import Spider as BaseSpider


RE_H1_TITLE = re.compile(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>', re.S)
RE_TITLE_TAG = re.compile(r'<title>([^<]+)</title>')
RE_CLEAN_TITLE = re.compile(r'\s*(HD中字|HD国语|HD粤语|高清|TS|TC|枪版|抢先版|更新至\d+集?|已完结)\s*$')
RE_TAG = re.compile(r'<[^>]+>')

RE_LAZYLOAD_PIC = re.compile(r'data-original="([^"]+)"')
RE_BG_PIC = re.compile(r'background:\s*url\(([^)]+)\)')
RE_IMG_PIC = re.compile(r'<img[^>]*src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', re.I)

RE_DIRECTOR = re.compile(r'<p[^>]*class="[^"]*data[^"]*"[^>]*>.*?<span[^>]*>导演：</span>(.*?)</p>', re.S)
RE_DIRECTOR2 = re.compile(r'导演：.*?<span>(.*?)</span>', re.S)

RE_ACTOR = re.compile(r'<p[^>]*class="[^"]*data[^"]*hidden-sm[^"]*"[^>]*>.*?<span[^>]*>主演：</span>(.*?)</p>', re.S)
RE_ACTOR2 = re.compile(r'<p[^>]*class="[^"]*data[^"]*"[^>]*>.*?<span[^>]*>主演：</span>(.*?)</p>', re.S)
RE_ACTOR3 = re.compile(r'主演：.*?<span>(.*?)</span>', re.S)
RE_A_TEXT = re.compile(r'>([^<]+)</a>')

RE_YEAR = re.compile(r'年份：</span>.*?<a[^>]*>(\d{4})', re.S)
RE_YEAR2 = re.compile(r'年份：.*?>(\d{4})<', re.S)
RE_YEAR3 = re.compile(r'(\d{4})/[^/]+/(?:电影|电视剧|综艺|动漫|短剧)')

RE_AREA = re.compile(r'地区：</span>.*?<a[^>]*>([^<]+)</a>', re.S)
RE_AREA2 = re.compile(r'地区：.*?>([^<]+)<', re.S)

RE_REMARKS = re.compile(r'<span[^>]*class="[^"]*pic-text[^"]*"[^>]*>(.*?)</span>', re.S)
RE_RATE = re.compile(r'(\d+\.\d+)\s*分')

RE_PLOT_FULL = re.compile(r'id="jq".*?<div[^>]*class="[^"]*tab-content[^"]*"[^>]*>(.*?)</div>', re.S)
RE_PLOT_JQ = re.compile(r'剧情介绍.*?<div[^>]*class="[^"]*tab-content[^"]*"[^>]*>(.*?)</div>', re.S)
RE_PLOT_DESC = re.compile(r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>.*?<span[^>]*class="[^"]*sketch[^"]*"[^>]*>(.*?)</span>', re.S)
RE_PLOT_SIMPLE = re.compile(r'简介：.*?<span[^>]*>(.*?)</span>', re.S)
RE_META_DESC = re.compile(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', re.I)

RE_PLAY_SOURCE = re.compile(r'<li><a href="#playlist(\d+)"[^>]*>([^<]+)</a></li>')
RE_SORT_LIST = re.compile(r'<ul[^>]*class="[^"]*sort-list[^"]*"[^>]*>(.*?)</ul>', re.S)
RE_EP_SIMPLE = re.compile(r'href="/play/(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>')
RE_PLAY_ALL = re.compile(r'href="/play/(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>')

RE_BASE64_URL = re.compile(r'var\s+now\s*=\s*base64decode\("([^"]+)"\)')

RE_VIDEO_BOX = re.compile(r'<div class="myui-vodlist__box">(.*?)</div>\s*</div>\s*</li>', re.S)
RE_VIDEO_BOX2 = re.compile(r'<div class="myui-vodlist__box">(.*?)</div>\s*</div>', re.S)
RE_VIDEO_HREF = re.compile(r'href="/movie/(\d+)\.html"')
RE_VIDEO_TITLE = re.compile(r'title="([^"]+)"')
RE_VIDEO_NAME = re.compile(r'<h4[^>]*class="[^"]*title[^"]*"[^>]*>.*?>([^<]+)</a>', re.S)

RE_SEARCH_ITEM = re.compile(r'<li[^>]*>.*?<a[^>]*class="[^"]*myui-vodlist__thumb[^"]*"[^>]*href="/movie/(\d+)\.html"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)".*?</li>', re.S)
RE_SEARCH_ITEM2 = re.compile(r'href="/movie/(\d+)\.html"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"')


class Spider(BaseSpider):
    def init(self, extend=""):
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=1,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.host = "https://www.lvsc168.com"
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        self._home_cache = None
        self._home_cache_time = 0

    def getName(self):
        return '绿色影视'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '26', 'type_name': '短剧'},
            {'type_id': '5', 'type_name': '动作片'},
            {'type_id': '6', 'type_name': '爱情片'},
            {'type_id': '7', 'type_name': '科幻片'},
            {'type_id': '8', 'type_name': '恐怖片'},
            {'type_id': '9', 'type_name': '战争片'},
            {'type_id': '10', 'type_name': '喜剧片'},
            {'type_id': '11', 'type_name': '纪录片'},
            {'type_id': '12', 'type_name': '剧情片'},
            {'type_id': '13', 'type_name': '大陆剧'},
            {'type_id': '14', 'type_name': '港台剧'},
            {'type_id': '15', 'type_name': '欧美剧'},
            {'type_id': '16', 'type_name': '日韩剧'},
            {'type_id': '27', 'type_name': '泰剧'},
        ]}

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and (now - self._home_cache_time) < 300:
            return self._home_cache
        html = self._fetch('/index.php')
        result = {"list": self._parse_video_list(html)}
        self._home_cache = result
        self._home_cache_time = now
        return result

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = '/frim/{}.html'.format(tid)
        else:
            url = '/frim/{}-{}.html'.format(tid, page)
        html = self._fetch(url)
        items = self._parse_video_list(html)
        page_count = page if len(items) < 20 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            html = self._fetch('/movie/{}.html'.format(vid))
            if not html:
                return result

            vod_name = ''
            m_name = RE_H1_TITLE.search(html)
            if m_name:
                vod_name = RE_TAG.sub('', m_name.group(1)).strip()
                vod_name = RE_CLEAN_TITLE.sub('', vod_name).strip()
            if not vod_name:
                m_title = RE_TITLE_TAG.search(html)
                if m_title:
                    vod_name = m_title.group(1).strip().split('-')[0].strip()
                    vod_name = RE_CLEAN_TITLE.sub('', vod_name).strip()

            vod_pic = ''
            m_pic = RE_LAZYLOAD_PIC.search(html)
            if not m_pic:
                m_pic = RE_BG_PIC.search(html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()
                if vod_pic.startswith('/'):
                    vod_pic = self.host + vod_pic
            if not vod_pic:
                pics = RE_IMG_PIC.findall(html)
                for p in pics:
                    pl = p.lower()
                    if 'logo' not in pl and 'icon' not in pl and 'load' not in pl:
                        vod_pic = p
                        if vod_pic.startswith('/'):
                            vod_pic = self.host + vod_pic
                        break

            vod_director = ''
            m_dir = RE_DIRECTOR.search(html)
            if not m_dir:
                m_dir = RE_DIRECTOR2.search(html)
            if m_dir:
                directors = RE_A_TEXT.findall(m_dir.group(1))
                directors = [d for d in directors if d and d != '..']
                if directors:
                    vod_director = ','.join(directors)

            vod_actor = ''
            m_act = RE_ACTOR.search(html)
            if not m_act:
                m_act = RE_ACTOR2.search(html)
            if not m_act:
                m_act = RE_ACTOR3.search(html)
            if m_act:
                actors = RE_A_TEXT.findall(m_act.group(1))
                actors = [a for a in actors if a and a != '..']
                if actors:
                    vod_actor = ','.join(actors)

            vod_year = ''
            m_year = RE_YEAR.search(html)
            if not m_year:
                m_year = RE_YEAR2.search(html)
            if not m_year:
                m_year = RE_YEAR3.search(html)
            if m_year:
                vod_year = m_year.group(1)

            vod_area = ''
            m_area = RE_AREA.search(html)
            if not m_area:
                m_area = RE_AREA2.search(html)
            if m_area:
                vod_area = m_area.group(1).strip()

            vod_remarks = ''
            m_remarks = RE_REMARKS.search(html)
            if m_remarks:
                vod_remarks = RE_TAG.sub('', m_remarks.group(1)).strip()
            if not vod_remarks:
                m_rate = RE_RATE.search(html)
                if m_rate:
                    vod_remarks = m_rate.group(1) + '分'

            vod_content = ''
            m_plot = RE_PLOT_FULL.search(html)
            if not m_plot:
                m_plot = RE_PLOT_JQ.search(html)
            if not m_plot:
                m_plot = RE_PLOT_DESC.search(html)
            if not m_plot:
                m_plot = RE_PLOT_SIMPLE.search(html)
            if m_plot:
                vod_content = RE_TAG.sub('', m_plot.group(1)).strip()
                vod_content = vod_content.replace('&nbsp;', ' ').strip()
                if vod_content.endswith('详情'):
                    vod_content = vod_content[:-2].strip()
            if not vod_content:
                m_desc = RE_META_DESC.search(html)
                if m_desc:
                    vod_content = m_desc.group(1).strip()

            play_from = []
            play_url = []

            source_matches = RE_PLAY_SOURCE.findall(html)

            for src_idx, src_name in source_matches:
                src_name = src_name.strip()
                playlist_id = 'playlist' + src_idx
                playlist_pattern = r'<div id="' + playlist_id + r'"[^>]*>.*?<ul[^>]*class="[^"]*sort-list[^"]*"[^>]*>(.*?)</ul>'
                m_list = re.search(playlist_pattern, html, re.S)
                if not m_list:
                    continue
                ep_matches = RE_EP_SIMPLE.findall(m_list.group(1))
                if not ep_matches:
                    continue
                eps = []
                for vid_ep, from_ep, part_ep, name_ep in ep_matches:
                    ep_name = name_ep.strip()
                    ep_id = '{}__{}__{}'.format(vid_ep, from_ep, part_ep)
                    eps.append('{}${}'.format(ep_name, ep_id))
                if eps:
                    play_from.append(src_name)
                    play_url.append('#'.join(eps))

            if not play_from:
                ep_matches = RE_PLAY_ALL.findall(html)
                if ep_matches:
                    eps = []
                    seen = set()
                    for vid_ep, from_ep, part_ep, name_ep in ep_matches:
                        key = '{}__{}__{}'.format(vid_ep, from_ep, part_ep)
                        if key in seen:
                            continue
                        seen.add(key)
                        ep_name = name_ep.strip()
                        eps.append('{}${}'.format(ep_name, key))
                    if eps:
                        play_from.append('线路一')
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
            print('detailContent error: {}'.format(e))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            parts = id.split('__')
            if len(parts) >= 3:
                vid = parts[0]
                from_ep = parts[1]
                part_ep = parts[2]
                play_html = self._fetch('/play/{}-{}-{}.html'.format(vid, from_ep, part_ep))
                if play_html:
                    m_b64 = RE_BASE64_URL.search(play_html)
                    if m_b64:
                        try:
                            play_url = base64.b64decode(m_b64.group(1)).decode('utf-8')
                            result["url"] = play_url
                            result["parse"] = 0
                            result["header"] = json.dumps({
                                "User-Agent": self.session.headers.get("User-Agent", ""),
                                "Referer": self.host + "/"
                            })
                        except Exception as e:
                            print('base64 decode error: {}'.format(e))
        except Exception as e:
            print('playerContent error: {}'.format(e))
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = '/search.php?searchword={}&page={}'.format(quote(key), page)
        html = self._fetch(url)
        items = self._parse_search_list(html) if html else []
        return {"list": items, "page": page, "pagecount": 9999, "limit": 20, "total": 99999}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        try:
            if url.startswith('http'):
                full_url = url
            else:
                full_url = self.host + url
            headers = {
                "Referer": self.host + "/",
            }
            rsp = self.session.get(full_url, headers=headers, timeout=8, verify=False)
            if rsp and rsp.text:
                if not url.startswith('http') and len(rsp.text) > 500:
                    pass
                return rsp.text
            return ''
        except:
            return ''

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            li_items = RE_VIDEO_BOX.findall(html)
            if not li_items:
                li_items = RE_VIDEO_BOX2.findall(html)

            for item in li_items:
                m_href = RE_VIDEO_HREF.search(item)
                if not m_href:
                    continue
                vid = m_href.group(1)
                if vid in seen:
                    continue
                seen.add(vid)

                m_title = RE_VIDEO_TITLE.search(item)
                vod_name = m_title.group(1).strip() if m_title else ''
                if not vod_name:
                    m_name2 = RE_VIDEO_NAME.search(item)
                    if m_name2:
                        vod_name = m_name2.group(1).strip()

                vod_pic = ''
                m_pic = RE_LAZYLOAD_PIC.search(item)
                if not m_pic:
                    m_pic = RE_BG_PIC.search(item)
                if m_pic:
                    vod_pic = m_pic.group(1).strip()
                    if vod_pic.startswith('/'):
                        vod_pic = self.host + vod_pic

                vod_remarks = ''
                m_remarks = RE_REMARKS.search(item)
                if m_remarks:
                    vod_remarks = RE_TAG.sub('', m_remarks.group(1)).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks,
                })
        except Exception as e:
            print('_parse_video_list error: {}'.format(e))
        return videos

    def _parse_search_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            li_items = RE_SEARCH_ITEM.findall(html)
            if not li_items:
                li_items = RE_SEARCH_ITEM2.findall(html)

            for item in li_items:
                if len(item) == 3:
                    vid, title, pic = item
                else:
                    continue
                if vid in seen:
                    continue
                seen.add(vid)

                vod_pic = pic.strip()
                if vod_pic.startswith('/'):
                    vod_pic = self.host + vod_pic

                videos.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": vod_pic,
                    "vod_remarks": '',
                })
        except Exception as e:
            print('_parse_search_list error: {}'.format(e))
        return videos
