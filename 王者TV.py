"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '王者TV',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
from urllib.parse import quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host_list = [
            "https://zh.kingtv.vip",
            "https://www.dyrs.net",
            "https://www.dyrs.tv",
            "https://www.dyrs.app",
            "https://dyrs.net",
            "https://dyrs.tv",
            "https://dyrs.app",
        ]
        self.host = self.host_list[0]
        self.host_index = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Referer": self.host + "/",
        }

    def getName(self):
        return '王者TV'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': 'dianying', 'type_name': '电影'},
            {'type_id': 'dianshiju', 'type_name': '电视剧'},
            {'type_id': 'zongyi', 'type_name': '综艺'},
            {'type_id': 'dongman', 'type_name': '动漫'},
            {'type_id': 'duanju', 'type_name': '短剧'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/')
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = f'/{tid}.html'
        else:
            url = f'/{tid}.html?page={page}'
        html = self._fetch(url)
        items = self._parse_video_list(html)
        return {"list": items, "page": page, "pagecount": 9999, "limit": 24, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            path = vid.replace('__', '/')
            html = self._fetch(f'/{path}.html')
            if not html:
                return result

            vod_name = ''
            m_title = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html)
            if m_title:
                vod_name = m_title.group(1).strip()
                vod_name = re.sub(r'\s*\(\d+\)\s*$', '', vod_name)
            if not vod_name:
                m_title = re.search(r'<title>([^<]+)</title>', html)
                if m_title:
                    vod_name = m_title.group(1).strip()
                    vod_name = re.sub(r'[《》]', '', vod_name)
                    vod_name = vod_name.split('-')[0].strip()

            vod_pic = ''
            m_pic = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()

            vod_year = ''
            m_year = re.search(r'<meta[^>]*property="og:title"[^>]*content="[^"]*\((\d{4})\)"', html)
            if m_year:
                vod_year = m_year.group(1)

            vod_actor = ''
            vod_content = ''
            m_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
            if m_desc:
                desc = m_desc.group(1).strip()
                m_actor = re.search(r'核心主演包括([^。]+)', desc)
                if m_actor:
                    vod_actor = m_actor.group(1).strip()
                m_plot = re.search(r'精彩剧情：(.+)', desc, re.S)
                if m_plot:
                    vod_content = re.sub(r'<[^>]+>', '', m_plot.group(1)).strip()

            vod_remarks = ''
            m_rem = re.search(r'bg-\[#409EFF\][^>]*>([^<]+)<', html)
            if m_rem:
                vod_remarks = m_rem.group(1).strip()

            play_from = []
            play_url = []

            source_names = re.findall(r'data-origin="([^"]+)"', html)
            seen_sources = set()
            for src in source_names:
                if not src or src in seen_sources:
                    continue
                if not re.match(r'^[a-z0-9]+m3u8$', src, re.I):
                    continue
                seen_sources.add(src)

            if not seen_sources:
                source_matches = re.findall(r'origin=([a-z0-9]+m3u8)', html, re.I)
                for src in source_matches:
                    seen_sources.add(src)

            ep_links = re.findall(
                r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*episode-button[^"]*"[^>]*data-origin="([^"]*)"[^>]*>(.*?)</a>',
                html, re.S | re.I
            )
            if not ep_links:
                ep_links = re.findall(
                    r'<a[^>]*class="[^"]*episode-button[^"]*"[^>]*href="([^"]+)"[^>]*data-origin="([^"]*)"[^>]*>(.*?)</a>',
                    html, re.S | re.I
                )
            if not ep_links:
                ep_links = re.findall(
                    r'<a[^>]*href="([^"]*origin=[^"]*m3u8[^"]*p=\d+[^"]*)"[^>]*>(.*?)</a>',
                    html, re.S | re.I
                )
                ep_links = [(h, '', t) for h, t in ep_links]

            source_eps = {}
            for href, src_attr, text in ep_links:
                href_clean = href.replace('&amp;', '&')
                m_src = re.search(r'origin=([^&]+)', href_clean)
                m_p = re.search(r'[?&]p=(\d+)', href_clean)
                if not m_p:
                    continue
                src = src_attr if src_attr else (m_src.group(1) if m_src else 'default')
                p = m_p.group(1)
                if src not in source_eps:
                    source_eps[src] = {}
                if p not in source_eps[src]:
                    ep_name = ''
                    m_name = re.search(r'<button[^>]*>(.*?)</button>', text, re.S | re.I)
                    if m_name:
                        ep_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()
                    if not ep_name:
                        ep_name = re.sub(r'<[^>]+>', '', text).strip()
                    if not ep_name:
                        ep_name = f'第{int(p)+1}集'
                    source_eps[src][p] = ep_name

            default_source = None
            if source_eps:
                for src in source_eps:
                    if src in seen_sources:
                        default_source = src
                        break
                if not default_source:
                    default_source = list(source_eps.keys())[0]

            all_sources = []
            for src in seen_sources:
                if src not in all_sources:
                    all_sources.append(src)
            for src in source_eps:
                if src not in all_sources:
                    all_sources.append(src)

            m_num = re.search(r'wzzy-(\d+)', vid)
            m_sid = re.search(r'__([a-z0-9]+)$', vid, re.I)
            num_part = m_num.group(1) if m_num else ''
            sid_part = m_sid.group(1) if m_sid else ''

            ref_eps = source_eps.get(default_source, {}) if default_source else {}
            ref_count = len(ref_eps)

            for src in all_sources:
                eps = []
                if src in source_eps and source_eps[src]:
                    ep_dict = source_eps[src]
                    for p in sorted(ep_dict.keys(), key=lambda x: int(x)):
                        ep_id = f'{vid}__{src}__{p}'
                        eps.append(f'{ep_dict[p]}${ep_id}')
                elif ref_count > 0 and num_part and sid_part:
                    for i in range(ref_count):
                        p = str(i)
                        ep_name = f'第{i+1}集'
                        ep_id = f'{vid}__{src}__{p}'
                        eps.append(f'{ep_name}${ep_id}')
                if eps:
                    play_from.append(src.upper())
                    play_url.append('#'.join(eps))

            if not play_from and source_eps:
                for src in source_eps:
                    eps = []
                    ep_dict = source_eps[src]
                    for p in sorted(ep_dict.keys(), key=lambda x: int(x)):
                        ep_id = f'{vid}__{src}__{p}'
                        eps.append(f'{ep_dict[p]}${ep_id}')
                    if eps:
                        play_from.append(src.upper())
                        play_url.append('#'.join(eps))
                        break

            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_director": '',
                "vod_actor": vod_actor,
                "vod_year": vod_year,
                "vod_area": '',
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
            parts = id.split('__')
            if len(parts) >= 4:
                wzzy_num = parts[0]
                sid = parts[1]
                src = parts[2]
                p = parts[3]
                play_hosts = [
                    'https://dyrs1.vip',
                    'https://viprs1.cc',
                ]
                for phost in play_hosts:
                    try:
                        play_url = f'{phost}/{wzzy_num}-{sid}.html?origin={src}&p={p}'
                        html = self._fetch_external(play_url)
                        if html:
                            m = re.search(r'<link[^>]*rel="preload"[^>]*href="([^"]+\.m3u8[^"]*)"', html)
                            if m:
                                result["url"] = m.group(1)
                                result["parse"] = 0
                                return result
                    except:
                        continue
        except Exception as e:
            print(f'playerContent error: {e}')
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = f'/search.html?wd={quote(key)}&page={page}'
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
            if url.startswith('http'):
                rsp = self.fetch(url, headers=self.headers)
                return rsp.text if rsp else ''
            for i in range(len(self.host_list)):
                idx = (self.host_index + i) % len(self.host_list)
                host = self.host_list[idx]
                try:
                    full_url = host + url
                    headers = dict(self.headers)
                    headers["Referer"] = host + "/"
                    rsp = self.fetch(full_url, headers=headers)
                    if rsp and rsp.text:
                        if idx != self.host_index:
                            self.host_index = idx
                            self.host = host
                        return rsp.text
                except:
                    continue
            return ''
        except:
            return ''

    def _fetch_external(self, url):
        try:
            ext_headers = dict(self.headers)
            ext_headers["Referer"] = self.host + '/'
            rsp = self.fetch(url, headers=ext_headers)
            return rsp.text if rsp else ''
        except:
            return ''

    def _get_pic_base(self):
        return 'https://pic2.tupian.click'

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            items = re.findall(
                r'<a[^>]*href="(/wzzy-(\d+)/([a-z0-9]+)\.html)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>',
                html, re.S | re.I
            )

            for href, num, sid, title, rest in items:
                vid = f'wzzy-{num}__{sid}'
                if not num or vid in seen:
                    continue
                seen.add(vid)

                title = title.strip()
                if not title:
                    continue

                pic = ''
                m_pic = re.search(r'<img[^>]*data-src="([^"]+)"', rest)
                if not m_pic:
                    m_pic = re.search(r'<img[^>]*src="([^"]+)"', rest)
                if m_pic:
                    pic = m_pic.group(1).strip()
                    if pic.startswith('/'):
                        pic = self._get_pic_base() + pic

                remarks = ''
                m_rem = re.search(r'bg-\[#409EFF\][^>]*>([^<]+)<', rest)
                if m_rem:
                    remarks = m_rem.group(1).strip()
                if not remarks:
                    m_rem = re.search(r'class="[^"]*note[^"]*"[^>]*>([^<]+)<', rest)
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
