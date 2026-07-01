"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'LIBVIO',
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
        self.host_list = [
            "https://libvio.host",
            "https://www.libvios.com",
            "https://www.libhd.com",
            "https://libviobd.com",
            "https://www.libvio.pw",
        ]
        self.host = self.host_list[0]
        self.host_index = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Referer": self.host + "/",
        }

    def getName(self):
        return 'LIBVIO'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '剧集'},
            {'type_id': '4', 'type_name': '番剧'},
            {'type_id': '15', 'type_name': '日韩'},
            {'type_id': '16', 'type_name': '欧美'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/')
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        if page <= 1:
            url = '/type/{}.html'.format(tid)
        else:
            url = '/type/{}-{}.html'.format(tid, page)
        html = self._fetch(url)
        items = self._parse_video_list(html)
        page_count = page if len(items) < 24 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 24, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            html = self._fetch('/detail/{}.html'.format(vid))
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', html, re.S)
            if m_name:
                vod_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('-')[0].strip()

            vod_pic = ''
            m_pic = re.search(r'data-original="([^"]+)"[^>]*id="js-poster-img"', html)
            if not m_pic:
                m_pic = re.search(r'<img[^>]*data-original="([^"]+)"', html)
            if not m_pic:
                m_pic = re.search(r'vod-poster__backdrop[^>]*data-src="([^"]+)"', html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()

            vod_director = ''
            m_dir = re.search(r'导演[：:]\s*<[^>]*>([^<]+)</', html)
            if not m_dir:
                m_dir = re.search(r'导演[：:]\s*([^<]+)<', html)
            if m_dir:
                vod_director = re.sub(r'<[^>]+>', '', m_dir.group(1)).strip()

            vod_actor = ''
            m_act = re.search(r'主演[：:]\s*(.*?)</', html, re.S)
            if m_act:
                vod_actor = re.sub(r'<[^>]+>', '', m_act.group(1)).strip()

            vod_year = ''
            m_year = re.search(r'<span[^>]*class="meta-item"[^>]*>(\d{4})</span>', html)
            if not m_year:
                m_year = re.search(r'年份[：:]\s*(\d{4})', html)
            if m_year:
                vod_year = m_year.group(1)

            vod_area = ''
            m_area = re.findall(r'<span[^>]*class="meta-item"[^>]*>([^<\d][^<]*)</span>', html)
            if m_area:
                areas = [a.strip() for a in m_area if a.strip() and not a.strip().isdigit() and len(a.strip()) < 10]
                if areas:
                    vod_area = areas[0] if len(areas[0]) < 10 else ''

            vod_remarks = ''
            m_rem = re.search(r'<span[^>]*class="pic-text[^"]*"[^>]*>([^<]+)</span>', html)
            if m_rem:
                vod_remarks = m_rem.group(1).strip()

            vod_content = ''
            m_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
            if m_desc:
                vod_content = m_desc.group(1).strip()
            if not vod_content:
                m_plot = re.search(r'class="detail-sketch"[^>]*>(.*?)</span>', html, re.S)
                if m_plot:
                    vod_content = re.sub(r'<[^>]+>', '', m_plot.group(1)).strip()
            if not vod_content:
                m_plot = re.search(r'简介[：:]\s*(.*?)</p>', html, re.S)
                if m_plot:
                    vod_content = re.sub(r'<[^>]+>', '', m_plot.group(1)).strip()

            play_from = []
            play_url = []

            panels = re.findall(
                r'<div[^>]*class="playlist-panel"[^>]*>(.*?)</div>\s*</div>\s*</div>',
                html, re.S
            )
            if not panels:
                panels = re.findall(
                    r'<div[^>]*class="playlist-panel[^"]*"[^>]*>(.*?)</ul>\s*</div>',
                    html, re.S
                )

            for panel in panels:
                source_name = ''
                m_src = re.search(r'<h3>([^<]+)</h3>', panel)
                if m_src:
                    source_name = m_src.group(1).strip()
                if not source_name:
                    continue

                eps = []
                ep_items = re.findall(
                    r'<li[^>]*>\s*<a[^>]*href="(/w/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>\s*</li>',
                    panel, re.S
                )
                if not ep_items:
                    ep_items = re.findall(
                        r'href="(/w/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>',
                        panel
                    )

                for ep_href, ep_name in ep_items:
                    ep_name = ep_name.strip()
                    if not ep_name:
                        continue
                    m_ep = re.search(r'/w/(\d+)-(\d+)-(\d+)\.html', ep_href)
                    if m_ep:
                        ep_id = '{}__{}__{}'.format(m_ep.group(1), m_ep.group(2), m_ep.group(3))
                        eps.append('{}${}'.format(ep_name, ep_id))

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
            print('detailContent error: {}'.format(e))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            parts = id.split('__')
            if len(parts) >= 3:
                vid = parts[0]
                sid = parts[1]
                nid = parts[2]
                html = self._fetch('/w/{}-{}-{}.html'.format(vid, sid, nid))
                if html:
                    m = re.search(r'player_aaaa\s*=\s*({.*?})\s*</script>', html, re.S)
                    if m:
                        player_json = m.group(1)
                        try:
                            player_data = json.loads(player_json)
                            play_url = player_data.get('url', '')
                            from_src = player_data.get('from', '')
                            if play_url:
                                result["url"] = play_url
                                result["parse"] = 0
                                if from_src and from_src not in ['kuake', 'xunlei']:
                                    result["header"] = json.dumps({
                                        "User-Agent": self.headers["User-Agent"],
                                        "Referer": self.host + "/"
                                    })
                        except:
                            m_url = re.search(r'"url"\s*:\s*"([^"]+)"', player_json)
                            if m_url:
                                url_val = m_url.group(1).replace('\\/', '/')
                                result["url"] = url_val
                                result["parse"] = 0
        except Exception as e:
            print('playerContent error: {}'.format(e))
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = '/search/-------------.html?wd={}&page={}'.format(quote(key), page)
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
                headers = dict(self.headers)
                rsp = self.fetch(url, headers=headers)
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

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            items = re.findall(
                r'<a[^>]*class="[^"]*stui-vodlist__thumb[^"]*"[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>(.*?)</a>',
                html, re.S
            )

            for href, title, pic, rest in items:
                vid = ''
                m_vid = re.search(r'/detail/(\d+)\.html', href)
                if m_vid:
                    vid = m_vid.group(1)
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                title = title.strip()
                if not title:
                    continue

                remarks = ''
                m_rem = re.search(r'class="pic-text[^"]*"[^>]*>([^<]+)</span>', rest)
                if m_rem:
                    remarks = m_rem.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic.strip() if pic else '',
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print('_parse_video_list error: {}'.format(e))
        return videos
