#!/usr/bin/python
# -*- coding: utf-8 -*-
from urllib.parse import quote

from pyquery import PyQuery as pq
from base.spider import Spider
import requests
import re


class Spider(Spider):
    def getName(self):
        return "4K-AV"

    def init(self, extend=""):
        self.name = "4K-AV"
        self.host = "https://www.4k-av.com"
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.8 Mobile/15E148 Safari/604.1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        try:
            import json
            ex = json.loads(extend) if extend and extend.startswith('{') else {}
            if isinstance(ex, dict):
                p = ex.get('proxy') or (ex.get('extend', {}).get('proxy') if isinstance(ex.get('extend', {}), dict) else None)
                if p:
                    self.session.proxies = {'http': p, 'https': p}
        except Exception:
            pass

    def _get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, proxies=self.session.proxies or None)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        except Exception:
            return ''

    def _fix(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host + url
        return url

    def getpq(self, path=''):
        html = self._get(self.host + path)
        return pq(html) if html else pq('')

    def getlist(self, data, y='.resyear label[title="分辨率"]'):
        videos = []
        for i in data.items():
            if not i('.title a').attr('href'):
                continue
            ns = i('.title h2').text().split(' ')
            videos.append({
                'vod_id': i('.title a').attr('href'),
                'vod_name': ns[0] if ns else '',
                'vod_pic': i('.poster img').attr('src') or '',
                'vod_remarks': ns[-1] if len(ns) > 1 else '',
                'vod_year': i(y).text()
            })
        return videos

    def homeContent(self, filter):
        data = self.getpq('/')
        result = {}
        classes = []
        for k in list(data('#category ul li').items())[:-1]:
            a = k('a')
            if a.attr('href'):
                classes.append({
                    'type_name': k.text(),
                    'type_id': a.attr('href')
                })
        result['class'] = classes
        result['list'] = self.getlist(data('#MainContent_newestlist .virow .NTMitem'))
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        data = self.getpq('/')
        items = self.getlist(data('#MainContent_scrollul ul li') + data('#MainContent_newestlist .virow .NTMitem'))
        seen = set()
        out = []
        for v in items:
            if v.get('vod_id') and v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                out.append(v)
        return {'list': out}

    def categoryContent(self, tid, pg, filter, extend):
        tid = tid.rstrip('/') if tid else '/movie'
        data = self.getpq(f"{tid}/page-{pg}.html")
        result = {}
        result['list'] = self.getlist(data('#MainContent_newestlist .virow .NTMitem'))
        result['page'] = int(pg) if str(pg).isdigit() else 1
        m = re.search(r'页次\s*\d+\s*/\s*(\d+)', data('#MainContent_header_nav').text())
        result['pagecount'] = int(m.group(1)) if m else result['page']
        result['limit'] = len(result['list']) or 24
        result['total'] = 0
        return result

    def detailContent(self, ids):
        vid = ids[0]
        data = self.getpq(vid)
        v = data('#videoinfo')
        vod = {
            'vod_id': vid,
            'vod_name': data('#tophead h1').text().split(' ')[0],
            'type_name': v('#MainContent_tags.tags a').text(),
            'vod_year': v('#MainContent_videodetail.videodetail a').text(),
            'vod_remarks': v('#MainContent_titleh12 h2').text(),
            'vod_content': v('p.cnline').text(),
            'vod_play_from': '4K-AV',
            'vod_play_url': ''
        }
        vlist = data('#rtlist li')
        if vlist:
            jn = f"{vod['vod_name']}_" if 'EP0' in vlist.eq(0)('span').text() else ''
            c = [f"{jn}{i('span').text()}${i('a').attr('href')}" for i in list(vlist.items())[1:] if i('a').attr('href')]
            c.insert(0, f"{jn}{vlist.eq(0)('span').text()}${vid}")
            vod['vod_play_url'] = '#'.join(c)
        else:
            vod['vod_play_url'] = f"{vod['vod_name']}${vid}"
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f"/s?x={quote(key)}")
        return {'list': self.getlist(data('#MainContent_newestlist .virow .NTMitem.Main')), 'page': int(pg) if str(pg).isdigit() else 1}

    def playerContent(self, flag, id, vipFlags):
        try:
            data = self.getpq(id)
            p, url = 0, data('#MainContent_videowindow source').attr('src')
            if not url:
                raise Exception('未找到播放地址')
        except Exception:
            p, url = 1, f"{self.host}{id}"
        headers = {
            'origin': 'https://www.4k-av.com',
            'referer': 'https://www.4k-av.com/',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.8 Mobile/15E148 Safari/604.1'
        }
        return {'parse': p, 'url': url, 'header': headers}