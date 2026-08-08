"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '开心影院',
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
            "https://www.kxyy1.cc",
            "https://www.kxyy5.cc",
            "https://www.kxyy7.cc",
            "https://www.kxyy8.cc",
            "https://www.kxyy9.cc",
            "https://www.kxyy.me",
        ]
        self.host = self.host_list[0]
        self.host_index = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36",
            "Referer": self.host + "/",
        }

    def getName(self):
        return '开心影院'

    def homeContent(self, filter):
        return {"class": [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '4', 'type_name': '短剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '5', 'type_name': '动漫'},
        ]}

    def homeVideoContent(self):
        html = self._fetch('/')
        return {"list": self._parse_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        items = []
        cat_map = {
            '1': 'dianying',
            '2': 'dianshiju',
            '4': 'duanju',
            '3': 'zongyi',
            '5': 'dongman',
        }
        slug = cat_map.get(tid, 'dianying')
        urls = []
        if page <= 1:
            urls = [
                '/vodtype/{}.html'.format(slug),
                '/vodshow/{}-----------.html'.format(tid),
            ]
        else:
            urls = [
                '/vodtype/{}-{}.html'.format(slug, page),
                '/vodshow/{}-----------{}.html'.format(tid, page),
            ]
        for url in urls:
            html = self._fetch(url)
            if html:
                items = self._parse_list(html)
                if items:
                    break
        page_count = page if len(items) < 24 else page + 2
        return {"list": items, "page": page, "pagecount": page_count, "limit": 24, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        try:
            html = self._fetch('/voddetail/{}.html'.format(vid))
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m_name:
                vod_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('-')[0].strip()

            vod_pic = ''
            pics = re.findall(r'data-src="(https?://[^"]+)"', html)
            for p in pics:
                if 'qpic' in p or 'ykimg' in p or 'douban' in p or 'pic' in p:
                    vod_pic = p
                    break
            if not vod_pic and pics:
                vod_pic = pics[0]

            vod_director = ''
            vod_actor = ''
            vod_year = ''
            vod_area = ''
            vod_content = ''
            vod_remarks = ''

            m_player = re.search(r'var player_data\s*=\s*({.*?})\s*;', html, re.S)
            if m_player:
                try:
                    pd = json.loads(m_player.group(1))
                    vod_data = pd.get('vod_data', {})
                    if isinstance(vod_data, dict):
                        if not vod_name:
                            vod_name = vod_data.get('vod_name', '')
                        if not vod_pic:
                            vod_pic = vod_data.get('vod_pic', '')
                        vod_director = vod_data.get('vod_director', '')
                        vod_actor = vod_data.get('vod_actor', '')
                        vod_year = vod_data.get('vod_year', '')
                        vod_area = vod_data.get('vod_area', '')
                        vod_content = vod_data.get('vod_content', '')
                        vod_remarks = vod_data.get('vod_remarks', '')
                except:
                    pass

            if not vod_content:
                m_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
                if m_desc:
                    vod_content = m_desc.group(1).strip()

            if not vod_remarks:
                m_rem = re.search(r'class="badge[^"]*"[^>]*>([^<]+)</span>', html)
                if m_rem:
                    vod_remarks = m_rem.group(1).strip()

            play_from = []
            play_url = []

            line_order = []
            line_map = {}
            all_tab_links = re.findall(
                r'<a[^>]*href="#tabs-home-(\d+)"([^>]*)>(.*?)</a>',
                html, re.S | re.I
            )
            for sid, attrs, content in all_tab_links:
                if 'nav-link' not in attrs:
                    continue
                name = re.sub(r'<[^>]+>', '', content).strip()
                name = name.replace('&nbsp;', '').strip()
                if name and len(name) < 30:
                    line_map[sid] = name
                    if sid not in line_order:
                        line_order.append(sid)

            eps_all = re.findall(
                r'href="/vodplay/(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>',
                html, re.I
            )
            groups = {}
            if eps_all:
                for vid_m, sid, nid, name in eps_all:
                    if sid not in groups:
                        groups[sid] = []
                    name = name.strip()
                    if name:
                        ep_id = '{}__{}__{}'.format(vid_m, sid, nid)
                        groups[sid].append('{}${}'.format(name, ep_id))

            if groups:
                ordered_sids = [sid for sid in line_order if sid in groups]
                remaining_sids = [sid for sid in sorted(groups.keys(), key=lambda x: int(x)) if sid not in ordered_sids]
                for sid in ordered_sids + remaining_sids:
                    lname = line_map.get(sid, '线路{}'.format(sid))
                    play_from.append(lname)
                    play_url.append('#'.join(groups[sid]))

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
                html = self._fetch('/vodplay/{}-{}-{}.html'.format(vid, sid, nid))
                if html:
                    play_url = ''
                    
                    var_patterns = [
                        r'var player_data\s*=\s*({.*?})\s*;',
                        r'var player_aaaa\s*=\s*({.*?})\s*</script>',
                        r'var player_config\s*=\s*({.*?})\s*;',
                        r'window\.player_data\s*=\s*({.*?})\s*;',
                        r'player_data\s*=\s*({.*?})\s*;',
                        r'let player_data\s*=\s*({.*?})\s*;',
                        r'const player_data\s*=\s*({.*?})\s*;',
                    ]
                    
                    for pat in var_patterns:
                        m = re.search(pat, html, re.S)
                        if m:
                            try:
                                pd = json.loads(m.group(1))
                                url = pd.get('url', '')
                                if not url:
                                    url = pd.get('video_url', '')
                                if not url:
                                    vd = pd.get('vod_data', {})
                                    if isinstance(vd, dict):
                                        url = vd.get('url', '')
                                if not url:
                                    url = pd.get('src', '')
                                if not url:
                                    pdata = pd.get('data', {})
                                    if isinstance(pdata, dict):
                                        url = pdata.get('url', '')
                                if url:
                                    play_url = url
                                    break
                            except:
                                m_url = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(1))
                                if m_url:
                                    play_url = m_url.group(1).replace('\\/', '/')
                                    break
                    
                    if not play_url:
                        url_patterns = [
                            r'(https?://[^"\']+\.m3u8[^"\']*)',
                            r'(https?://[^"\']+\.mp4[^"\']*)',
                            r'(https?://[^"\']+\.m3u[^"\']*)',
                            r'"url"\s*:\s*"([^"]+)"',
                            r'"video"\s*:\s*"([^"]+)"',
                            r'"src"\s*:\s*"([^"]+)"',
                        ]
                        for pat in url_patterns:
                            m = re.search(pat, html, re.I)
                            if m:
                                u = m.group(1)
                                if u and u.startswith('http'):
                                    play_url = u
                                    break
                    
                    if not play_url:
                        m_iframe = re.search(r'<iframe[^>]*src="([^"]+)"', html, re.I)
                        if m_iframe:
                            iframe_url = m_iframe.group(1)
                            if iframe_url.startswith('//'):
                                iframe_url = 'https:' + iframe_url
                            if iframe_url.startswith('http'):
                                play_url = iframe_url
                                result["parse"] = 1
                    
                    if play_url:
                        if play_url.startswith('//'):
                            play_url = 'https:' + play_url
                        result["url"] = play_url
                        result["parse"] = 0
                        
                        if re.search(r'(youku|iqiyi|qq\.com|mgtv|bilibili)', play_url, re.I):
                            result["parse"] = 1
                        
                        play_headers = {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": self.host + "/",
                        }
                        result["header"] = json.dumps(play_headers)
        except Exception as e:
            print('playerContent error: {}'.format(e))
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        items = []
        search_urls = [
            '/vodsearch/-------------.html?wd={}&page={}'.format(quote(key), page),
            '/index.php/vod/search/wd/{}.html'.format(quote(key)),
            '/vodsearch/wd/{}.html'.format(quote(key)),
            '/search.html?wd={}'.format(quote(key)),
        ]
        for url in search_urls:
            html = self._fetch(url)
            if html:
                items = self._parse_list(html)
                if items:
                    break
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
                    if rsp and rsp.text and len(rsp.text) > 1000:
                        if idx != self.host_index:
                            self.host_index = idx
                            self.host = host
                        return rsp.text
                except:
                    continue
            return ''
        except:
            return ''

    def _parse_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos

            items = re.findall(
                r'<a[^>]*?href="/voddetail/(\d+)\.html"[^>]*?>(.*?)</a>',
                html, re.S | re.I
            )

            for vid, content in items:
                if vid in seen:
                    continue
                
                a_tag = re.search(
                    r'<a[^>]*?href="/voddetail/' + re.escape(vid) + r'\.html"[^>]*?>',
                    html, re.I
                )
                title = ''
                if a_tag:
                    m_t = re.search(r'title="([^"]+)"', a_tag.group(0))
                    if m_t:
                        title = m_t.group(1).strip()
                if not title:
                    m_alt = re.search(r'alt="([^"]+)"', content, re.I)
                    if m_alt:
                        title = m_alt.group(1).strip()
                if not title:
                    m_h3 = re.search(r'<h\d[^>]*>(.*?)</h\d>', content, re.S | re.I)
                    if m_h3:
                        title = re.sub(r'<[^>]+>', '', m_h3.group(1)).strip()
                
                if not title or len(title) < 2:
                    continue

                pic = ''
                m_pic = re.search(r'data-src="(https?://[^"]+)"', content, re.I)
                if not m_pic:
                    m_pic = re.search(r'src="(https?://[^"]+)"', content, re.I)
                if m_pic:
                    pic = m_pic.group(1).strip()

                if not pic or 'svg' in pic.lower() or 'icon' in pic.lower() or 'logo' in pic.lower():
                    continue

                seen.add(vid)
                remarks = ''
                m_badge = re.search(r'<span[^>]*class="[^"]*badge[^"]*"[^>]*>([^<]+)</span>', content, re.I)
                if m_badge:
                    remarks = m_badge.group(1).strip()
                if not remarks:
                    m_ribbon = re.search(r'<div[^>]*class="[^"]*ribbon[^"]*"[^>]*>([^<]+)</div>', content, re.I)
                    if m_ribbon:
                        remarks = m_ribbon.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print('_parse_list error: {}'.format(e))
        return videos
