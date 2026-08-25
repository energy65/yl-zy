#coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..') 
from base.spider import Spider
import json
import re
import requests
import base64
import time
import uuid
import hashlib
from urllib import parse
import urllib
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

WEB = 'https://www.1905.com'
PLAY_API = 'https://profile.m1905.com/mvod/getVideoinfo.php'
SIDEBAR_API = 'https://www.1905.com/api/content/?callback=&m=Vod&a=getVodSidebar&id={0}&fomat=json'
LRC_URL = 'https://8877.kstore.space/jar/yy/%E4%B8%B0.txt'

UA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
HEADERS = {
    'User-Agent': UA,
    'Referer': WEB + '/vod/list/n_1/o3p1.html',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
}
PLAY_HEADER = {
    'User-Agent': UA,
    'Referer': WEB
}
PROMO = ' (获取失败，请重试)'

CATES = {
    '电影': 'n_1',
    '微电影': 'n_1_c_922',
    '系列电影': 'n_2',
    '纪录片': 'c_927',
    '晚会': 'n_1_c_586',
    '独家': 'n_1_c_178',
    '综艺': 'n_1_c_1024'
}

ORDERS = [
    {'n': '默认(最热)', 'v': 'o3'},
    {'n': '最新', 'v': 'o1'},
    {'n': '好评', 'v': 'o4'}
]

def _strip_tags(s):
    if not s:
        return ''
    import re
    s = re.sub('<[^>]+>', '', str(s))
    s = s.replace('&', '&').replace('"', '"')
    return s

def _regex_get(text, pattern, group=1):
    m = re.search(pattern, text, re.M | re.S)
    return m.group(group) if m else ''

def _pic(u):
    if not u:
        return ''
    if u.startswith('//'):
        return 'https:' + u
    return u

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = '1905电影'
        self.session = None

    def _get_text(self, url, headers=None):
        if self.session is None:
            self.session = requests.Session()
        if headers is None:
            headers = HEADERS
        try:
            r = self.session.get(url, headers=headers, timeout=15)
            r.encoding = 'utf-8'
            return r.text
        except:
            try:
                req = urllib.request.Request(url=url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode('utf-8', 'ignore')
            except:
                return ''

    def _nodes(self, doc, expr):
        try:
            return doc.xpath(expr)
        except:
            return []

    def _parse_anchors(self, doc, expr, skip_vip=True):
        videos = []
        for a in self._nodes(doc, expr):
            try:
                img = a.xpath('./img/@src')[0]
                title = _strip_tags(a.xpath('./img/@alt')[0])
                url = a.xpath('./@href')[0]
                if skip_vip and 'vip.1905' in url:
                    continue
                if 'play' in url:
                    pid = url
                else:
                    pid = _regex_get(url, r'play/(.*?)\.sh')
                videos.append({
                    'vod_id': '{0}###{1}###{2}'.format(pid, title, _pic(img)),
                    'vod_name': title,
                    'vod_pic': _pic(img),
                    'vod_remarks': ''
                })
            except:
                pass
        return videos

    def _parse_search(self, doc):
        videos = []
        for a in self._nodes(doc, '//div[@class="main clearfix"]'):
            try:
                img = a.xpath('./div[@class="movie-pic"]/a[@class="img-a"]/img/@src')[0]
                title = _strip_tags(a.xpath('./div[@class="movie-pic"]/a[@class="img-a"]/img/@alt')[0])
                urls = a.xpath('./ul[@class="cont"]/li[@class="spec paly-tab-icon position-icon"]/a/@href')
                if urls:
                    url = urls[0]
                else:
                    url = a.xpath('./div[@class="movie-pic"]/a[@class="img-a"]/@href')[0]
                if 'vip.1905' in url:
                    url = a.xpath('./div[@class="movie-pic"]/a[@class="img-a"]/@href')[0]
                if 'play' in url:
                    pid = url
                else:
                    pid = _regex_get(url, r'play/(.*?)\.sh')
                videos.append({
                    'vod_id': '{0}###{1}###{2}'.format(pid, title, _pic(img)),
                    'vod_name': title,
                    'vod_pic': _pic(img),
                    'vod_remarks': ''
                })
            except:
                pass
        return videos

    def getName(self):
        return '1905电影'

    def init(self, extend=''):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {'class': []}
        for k, v in CATES.items():
            result['class'].append({'type_name': k, 'type_id': v})
        if filter:
            result['filters'] = {}
            for c in CATES:
                result['filters'][CATES[c]] = [{'key': 'by', 'name': '排序:', 'value': ORDERS}]
        return result

    def homeVideoContent(self):
        url = WEB + '/vod/cctv6/lst/'
        doc = self.html(self._get_text(url))
        videos = self._parse_anchors(doc, "//div[@class='grid-2x']/a")
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        if not pg:
            pg = 1
        pg = int(pg)
        if pg < 1:
            pg = 1
        if isinstance(extend, dict):
            pass
        elif isinstance(extend, str):
            try:
                import json
                extend = json.loads(extend)
            except:
                extend = {}
        else:
            extend = {}
        by = extend.get('by', 'o3')
        url = '%s/vod/list/%s/%sp%d.html' % (WEB, tid, by, pg)
        expr = "//section[contains(@class,'search-list')]/div/a"
        if tid == 'n_2':
            expr = "//div[@class='mod']/div[1]/a"
        doc = self.html(self._get_text(url))
        videos = self._parse_anchors(doc, expr)
        limit = len(videos)
        return {
            'list': videos,
            'page': pg,
            'pagecount': 100,
            'limit': limit,
            'total': 100 * limit
        }

    def detailContent(self, ids):
        did = str(ids[0])
        parts = did.split('###')
        aid = parts[0]
        title = parts[1] if len(parts) > 1 else ''
        pic = parts[2] if len(parts) > 2 else ''
        remark = ''
        actor = ''
        director = ''
        content = ''
        play_from = '播放线路'
        playlists = []
        if not aid.isdigit():
            cur = self._get_text(aid)
            url = _regex_get(cur, r'<a class="iconBanner-playBtn icon-banner btn-play"\s*href="(.+?)"')
            if not url:
                url = _regex_get(cur, r'property="og:url"\scontent="(.+?)"')
            if _regex_get(url, r'/(film)/'):
                cur = self._get_text(aid + 'video')
                url = _regex_get(cur, r'<li class="video-position-icon\s{0,1}">\r*\n*\s*<a href="(.+?)"\s{1,4}class="online-list-positive other-vedio-url"')
                if not url:
                    url = _regex_get(cur, r'(https*://[a-z0-9.]*1905\.com/vod/play/\d+\.shtml)')
            if len(_regex_get(url, r'(vip.1905)')) > 3:
                play_from = '播放线路(需要vip解析)'
                aid = url
                title = _strip_tags(_regex_get(cur, r'<div class="container-right">\s*\r*\n*\t*<h1>(.+?)<')).replace(' ', '')
                if not title:
                    title = _strip_tags(_regex_get(cur, r'property="og:title"\s*content="(.+?)"'))
                pic = _regex_get(cur, r'<img class="poster" src="(.+?)"')
                if not pic:
                    pic = _regex_get(cur, r'property="og:image"\s*content="(.+?)"')
                c = _regex_get(cur, r'<p>(.+?)</p>')
                if c:
                    content = _strip_tags(c)
                else:
                    content = _strip_tags(_regex_get(cur, r'property="og:description"\s*content="(.+?)"'))
                playlists.append(title + '$' + aid)
            else:
                aid = _regex_get(url, r'play/(.*?)\.sh')
        if not aid:
            return {'list': []}
        elif aid.isdigit() and 'vip解析' not in play_from:
            try:
                html = self._get_text(SIDEBAR_API.format(aid))
                root = json.loads(html)
                title = root.get('title', title)
                pic = root.get('thumb', pic)
                remark = root.get('commendreason', '')
                content = root.get('description', content)
                actor = root.get('starring', '')
                director = root.get('direct', '')
                items = [title + '$' + aid]
                for ser in root.get('info', {}).get('series_data', []):
                    items.append(ser.get('title', '') + '$' + ser.get('contentid', ''))
                playlists.append('#'.join(items))
            except:
                playlists.append(title + '$' + aid)
        vod = {
            'vod_id': did,
            'vod_name': title,
            'vod_pic': _pic(pic),
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': remark,
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': content + PROMO,
            'vod_play_from': play_from,
            'vod_play_url': '$$$'.join(playlists)
        }
        return {'list': [vod]}

    def searchContentPage(self, key, quick, page):
        if not page:
            page = 1
        page = int(page)
        if page < 1:
            page = 1
        seg = 'p' if page == 1 else 'p%d' % page
        url = '%s/search/index-%s-type-film-q-%s.html?envod=1&year=0&score=0&order=0' % (WEB, seg, parse.quote(key))
        doc = self.html(self._get_text(url))
        videos = self._parse_search(doc)
        return {
            'list': videos,
            'page': page,
            'pagecount': 999999 if videos else 0,
            'limit': len(videos),
            'total': len(videos)
        }

    def searchContent(self, key, quick, pg=1):
        return self.searchContentPage(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        id = str(id)
        conf = {'jx': 0, 'parse': 0, 'playUrl': '', 'url': '', 'header': {}}
        if 'vip解析' in flag:
            conf['parse'] = 1
            conf['jx'] = 1
            conf['url'] = id
        else:
            nonce = int(round(time.time() * 1000))
            expiretime = nonce + 600
            uid = str(uuid.uuid4())
            playerid = uid.replace('-', '')[5:20]
            raw = 'cid={0}&expiretime={1}&nonce={2}&page=https%3A%2F%2Fwww.1905.com%2Fvod%2Fplay%2F{3}.shtml&playerid={4}&type=hls&uuid={5}.dde3d61a0411511d'.format(id, expiretime, nonce, id, playerid, uid)
            signature = hashlib.sha1(raw.encode()).hexdigest()
            api = PLAY_API + '?nonce={0}&expiretime={1}&cid={2}&uuid={3}&playerid={4}&page=https%3A%2F%2Fwww.1905.com%2Fvod%2Fplay%2F{5}.shtml&type=hls&signature={6}&callback='.format(nonce, expiretime, id, uid, playerid, id, signature)
            try:
                txt = self._get_text(api, PLAY_HEADER).replace('(', '').replace(')', '')
                jo = json.loads(txt)
                data = jo.get('data', {})
                signs = data.get('sign', {})
                quality = ''
                for q in ('uhd', 'hd', 'sd'):
                    if q in signs:
                        quality = q
                        break
                if quality:
                    host = data.get('quality', {}).get(quality, {}).get('host', '')
                    path = data.get('path', {}).get(quality, {}).get('path', '')
                    sign = signs.get(quality, {}).get('sign', '')
                    conf['url'] = host + sign + path
                    conf['header'] = PLAY_HEADER
            except:
                pass
        try:
            r = requests.get(LRC_URL, timeout=5)
            conf['lrc'] = base64.b64decode(r.text).decode('utf-8')
        except:
            pass
        return conf

    def localProxy(self, param):
        return [200, 'video/MP2T', b'', '']