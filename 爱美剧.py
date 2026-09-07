# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 爱美剧 (m.aiyingyu.net)
支持: 分类栏 / 首页推荐 / 分页列表 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)

站点说明:
  爱美剧网 提供美剧、国产剧、韩剧、海外剧、动画番剧、综艺等影视资源。
  播放页通过 iframe 内嵌播放器，iframe src 中 url 参数为 base64 编码的 m3u8 直链，
  本爬虫解码后直接返回 m3u8 播放地址，走 parse=0 直播。
  解析失败时兜底返回 parse=1 交给内置网页解析。

关键页面:
  首页        : https://m.aiyingyu.net/
  分类列表    : https://m.aiyingyu.net/aimeiju/tiantang-14.html  (英美剧)
  分页        : /aimeiju/tiantang-14-{page}.html
  详情页      : https://m.aiyingyu.net/aimeiju/haokan-{id}.html
  播放页      : https://m.aiyingyu.net/aimeiju/zaixian-{id}-{sid}-{nid}.html
  搜索        : https://m.aiyingyu.net/aimeiju/so--------------.html?wd={keyword}
"""

import re
import json
import ssl
import base64
import urllib.parse
import urllib.request
from urllib.parse import quote, urljoin

try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass

BASE_URL = 'https://m.aiyingyu.net'
AD_INFO = "\n\n---\n微信公众号：源力软件汇\nQQ群：1054592152\n更多优质资源尽在源力"

CATEGORIES = [
    {"type_id": "14", "type_name": "英美剧"},
    {"type_id": "13", "type_name": "国产剧"},
    {"type_id": "15", "type_name": "韩剧"},
    {"type_id": "16", "type_name": "海外剧"},
    {"type_id": "3",  "type_name": "动画番剧"},
    {"type_id": "20", "type_name": "综艺"},
    {"type_id": "1",  "type_name": "影片"},
]


class Spider(BaseSpider):

    HEADERS = {
        'User-Agent': ('Mozilla/5.0 (Linux; Android 12; SM-G991B) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Mobile Safari/537.36'),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': BASE_URL + '/',
    }

    _sess = None

    def getName(self):
        return "爱美剧"

    def init(self, cfg=''):
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass
        if requests is not None and self.__class__._sess is None:
            self.__class__._sess = requests.Session()
            self.__class__._sess.headers.update(self.HEADERS)
            self.__class__._sess.verify = False
            try:
                requests.packages.urllib3.disable_warnings()
            except Exception:
                pass
        return self

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return None

    def _get(self, url):
        if not url.startswith('http'):
            url = urljoin(BASE_URL, url)
        if requests is not None:
            sess = self.__class__._sess
            if sess is None:
                self.init()
                sess = self.__class__._sess
            if sess is not None:
                try:
                    resp = sess.get(url, timeout=15, allow_redirects=True)
                    resp.encoding = 'utf-8'
                    return resp.text if resp.status_code == 200 else ''
                except Exception:
                    return ''
        try:
            req = urllib.request.Request(url, headers=self.HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _fix_url(self, u):
        if not u:
            return ''
        u = u.replace('\\/', '/').replace('&amp;', '&')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('http'):
            return u
        return urljoin(BASE_URL, u)

    def _clean(self, text):
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<') \
                   .replace('&gt;', '>').replace('&quot;', '"') \
                   .replace('&#039;', "'")
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_vods(self, html):
        vods = []
        pattern = re.compile(
            r'<li class="hl-list-item[^"]*">.*?'
            r'<a class="hl-item-thumb[^"]*" href="/aimeiju/haokan-(\d+)\.html".*?'
            r'data-src="([^"]*)"',
            re.S
        )
        for m in pattern.finditer(html):
            vid, pic = m.group(1), m.group(2)
            win = html[m.start():m.start() + 1500]
            name = ''
            nm = re.search(r'class="hl-item-title[^"]*"[^>]*><a[^>]*>([^<]+)</a>', win)
            if nm:
                name = self._clean(nm.group(1))
            if not name:
                nm2 = re.search(r'alt="([^"]+)"', win)
                if nm2:
                    name = self._clean(nm2.group(1))
            remark = ''
            rm = re.search(r'<span class="hl-lc-1 remarks">([^<]*)</span>', win)
            if rm:
                remark = self._clean(rm.group(1))
            genre = ''
            gm = re.search(r'<span class="douban">([^<]+)</span>', win)
            if gm:
                genre = self._clean(gm.group(1))
            sub = ''
            sm = re.search(r'class="hl-item-sub[^"]*">([^<]+)</div>', win)
            if sm:
                sub = self._clean(sm.group(1))
            remark_text = genre
            if remark:
                remark_text = '%s %s' % (genre, remark) if genre else remark
            elif not remark_text:
                remark_text = sub.split('/')[0].strip() if '/' in sub else sub
            vods.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': self._fix_url(pic),
                'vod_remarks': remark_text,
            })
        seen = set()
        uniq = []
        for v in vods:
            if v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            uniq.append(v)
        return uniq

    def _pagecount(self, html):
        max_pg = 1
        for mm in re.finditer(r'/aimeiju/tiantang-\d+-(\d+)\.html', html):
            try:
                max_pg = max(max_pg, int(mm.group(1)))
            except ValueError:
                pass
        return max_pg

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result = {"class": classes, "filters": {}}
        html = self._get(BASE_URL + '/')
        result['list'] = self._parse_vods(html)[:20]
        return result

    def homeVideoContent(self):
        html = self._get(BASE_URL + '/')
        return {"list": self._parse_vods(html)}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except (TypeError, ValueError):
            page = 1
        page = max(page, 1)
        if page == 1:
            path = '/aimeiju/tiantang-%s.html' % tid
        else:
            path = '/aimeiju/tiantang-%s-%d.html' % (tid, page)
        html = self._get(path)
        if not html:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        vods = self._parse_vods(html)
        pc = max(self._pagecount(html), page)
        limit = len(vods) if vods else 20
        return {
            "list": vods,
            "page": page,
            "pagecount": pc if pc else 1,
            "limit": limit,
            "total": pc * limit,
        }

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._get('/aimeiju/haokan-%s.html' % vid)
        if not html:
            return {"list": []}
        return {"list": [self._parse_detail(vid, html)]}

    def _parse_detail(self, vid, html):
        name = ''
        nm = re.search(r'<h2[^>]*class="hl-dc-title[^"]*"[^>]*>(.*?)</h2>', html, re.S)
        if nm:
            name = self._clean(nm.group(1))
        if not name:
            nm2 = re.search(r'<title>([^<]+)</title>', html)
            if nm2:
                name = self._clean(nm2.group(1).split('免费在线观看')[0].split('-')[0].strip())

        pic = ''
        pm = re.search(r'class="hl-dc-pic".*?data-src="([^"]+)"', html, re.S)
        if not pm:
            pm = re.search(r'data-src="(https?://img\.bshyw\.com[^"]+)"', html)
        if pm:
            pic = pm.group(1)

        score = ''
        sm = re.search(r'评分：</em>\s*<span[^>]*>([\d.]+)</span>', html)
        if sm:
            score = sm.group(1)
        if not score:
            sm2 = re.search(r'score"[^>]*>([\d.]+)<', html)
            if sm2:
                score = sm2.group(1)

        year = ''
        ym = re.search(r'出品：</em>\s*<a[^>]*>(\d{4})', html)
        if not ym:
            ym = re.search(r'og:video:release_date"\s*content="(\d{4})', html)
        if ym:
            year = ym.group(1)

        area = ''
        am = re.search(r'归属：</em>\s*<a[^>]*>([^<]+)</a>', html)
        if not am:
            am = re.search(r'og:video:area"\s*content="([^"]+)"', html)
        if am:
            area = self._clean(am.group(1))

        genre = ''
        gm = re.search(r'og:video:class"\s*content="([^"]+)"', html)
        if gm:
            genre = self._clean(gm.group(1).replace(',', '/'))

        actor = ''
        act_m = re.search(r'演员：</em>(.*?)</li>', html, re.S)
        if act_m:
            actor = self._clean(act_m.group(1))
        if not actor:
            act_m2 = re.search(r'og:video:actor"\s*content="([^"]+)"', html)
            if act_m2:
                actor = self._clean(act_m2.group(1))

        director = ''
        dm = re.search(r'导演：</em>(.*?)</li>', html, re.S)
        if dm:
            director = self._clean(dm.group(1))

        status = ''
        stm = re.search(r'最新：</em>\s*<span[^>]*>([^<]+)</span>', html)
        if stm:
            status = self._clean(stm.group(1))

        blurb = ''
        bm = re.search(r'class="hl-content-text"[^>]*><em>(.*?)</em>', html, re.S)
        if bm:
            blurb = self._clean(bm.group(1))
        if not blurb:
            bm2 = re.search(r'<meta name="description"\s*content="([^"]+)"', html)
            if bm2:
                blurb = self._clean(bm2.group(1))
        content = blurb if blurb else ''
        if content:
            content += AD_INFO

        froms = []
        for fm in re.finditer(r'<a[^>]*class="hl-tabs-btn[^"]*"[^>]*alt="([^"]*)"', html):
            t = self._clean(fm.group(1))
            if t:
                froms.append(t)

        groups = []
        blocks = re.findall(
            r'<ul[^>]*class="hl-plays-list[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        for i, block in enumerate(blocks):
            src = froms[i] if i < len(froms) else '线路'
            eps = []
            seen = set()
            for em in re.finditer(
                r'<a[^>]*href="/aimeiju/zaixian-(\d+)-(\d+)-(\d+)\.html"[^>]*>([^<]+)</a>', block):
                key = (em.group(2), em.group(3))
                if key in seen:
                    continue
                seen.add(key)
                label = em.group(4).strip() or '播放'
                eps.append('%s$%s-%s-%s' % (label, em.group(1), em.group(2), em.group(3)))
            if eps:
                groups.append((src, '#'.join(eps)))

        vod = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': status,
            'vod_year': year,
            'vod_area': area,
            'vod_actor': actor,
            'vod_director': director,
            'vod_class': genre,
            'vod_score': score,
            'vod_content': content,
            'type_name': genre,
            'vod_play_from': '',
            'vod_play_url': '',
        }
        if groups:
            vod['vod_play_from'] = '$$$'.join(g[0] for g in groups)
            vod['vod_play_url'] = '$$$'.join(g[1] for g in groups)

        return vod

    def searchContent(self, key, quick, pg='1'):
        if not key:
            return {"list": []}
        try:
            page = max(int(pg), 1)
        except (TypeError, ValueError):
            page = 1
        if page == 1:
            url = '/aimeiju/so--------------.html?wd=%s' % quote(str(key), safe='')
        else:
            url = '/aimeiju/so-%s----------%d---.html' % (quote(str(key), safe=''), page)
        html = self._get(url)
        if html:
            return {"list": self._parse_search(html)}
        return {"list": []}

    def _parse_search(self, html):
        vods = []
        pattern = re.compile(
            r'<li class="hl-list-item[^"]*">.*?'
            r'<a class="hl-item-thumb[^"]*" href="/aimeiju/haokan-(\d+)\.html".*?'
            r'data-src="([^"]*)"',
            re.S
        )
        for m in pattern.finditer(html):
            vid, pic = m.group(1), m.group(2)
            win = html[m.start():m.start() + 2000]
            name = ''
            nm = re.search(r'class="hl-item-title[^"]*"[^>]*><a[^>]*>([^<]+)</a>', win)
            if nm:
                name = self._clean(nm.group(1))
            if not name:
                nm2 = re.search(r'alt="([^"]+)"', win)
                if nm2:
                    name = self._clean(nm2.group(1))
            remark = ''
            rm = re.search(r'<span class="hl-lc-1 remarks">([^<]*)</span>', win)
            if rm:
                remark = self._clean(rm.group(1))
            sub = ''
            sm = re.search(r'class="hl-item-sub[^"]*"><em>([^<]+)</em>', win)
            if sm:
                sub = self._clean(sm.group(1))
            vods.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': self._fix_url(pic),
                'vod_remarks': sub if sub else remark,
            })
        seen = set()
        uniq = []
        for v in vods:
            if v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            uniq.append(v)
        return uniq

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('http'):
            play_path = id
        else:
            play_path = urljoin(BASE_URL, '/aimeiju/zaixian-%s.html' % id.strip('/'))
        html = self._get(play_path)
        m3u8 = ''
        if html:
            im = re.search(r'<iframe[^>]*src="([^"]*)"[^>]*>', html, re.S)
            if im:
                iframe_src = im.group(1)
                parsed = urllib.parse.urlparse(iframe_src)
                qs = urllib.parse.parse_qs(parsed.query)
                url_param = qs.get('url', [''])[0]
                if url_param:
                    try:
                        padded = url_param
                        rem = len(padded) % 4
                        if rem:
                            padded += '=' * (4 - rem)
                        decoded = base64.b64decode(padded).decode('utf-8', 'replace')
                        if decoded.startswith('http'):
                            m3u8 = decoded
                    except Exception:
                        pass
        header = {
            'User-Agent': self.HEADERS['User-Agent'],
            'Referer': BASE_URL + '/',
        }
        if m3u8:
            return {
                'parse': 0,
                'playUrl': '',
                'url': m3u8,
                'header': json.dumps(header, ensure_ascii=False),
            }
        return {
            'parse': 1,
            'playUrl': '',
            'url': play_path,
            'header': json.dumps(header, ensure_ascii=False),
        }


def _cli():
    import sys
    if requests is not None:
        try:
            requests.packages.urllib3.disable_warnings()
        except Exception:
            pass
    sp = Spider()
    sp.init()
    if len(sys.argv) < 2:
        print("用法: python 爱美剧.py home|categories|list <分类id> <页>|detail <影片ID>|play <播放页>|search <关键词>")
        return
    cmd = sys.argv[1].lower()
    if cmd == 'home':
        print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2))
    elif cmd == 'categories':
        print(json.dumps(sp.homeContent(True)['class'], ensure_ascii=False, indent=2))
    elif cmd == 'list':
        tid = sys.argv[2] if len(sys.argv) > 2 else '14'
        pg = sys.argv[3] if len(sys.argv) > 3 else '1'
        print(json.dumps(sp.categoryContent(tid, pg, None, None), ensure_ascii=False, indent=2))
    elif cmd == 'detail':
        vid = sys.argv[2] if len(sys.argv) > 2 else ''
        print(json.dumps(sp.detailContent([vid]), ensure_ascii=False, indent=2))
    elif cmd == 'play':
        u = sys.argv[2] if len(sys.argv) > 2 else ''
        print(json.dumps(sp.playerContent('', u, []), ensure_ascii=False, indent=2))
    elif cmd == 'search':
        key = sys.argv[2] if len(sys.argv) > 2 else ''
        pg = sys.argv[3] if len(sys.argv) > 3 else '1'
        print(json.dumps(sp.searchContent(key, 0, pg), ensure_ascii=False, indent=2))
    else:
        print("未知命令")


if __name__ == '__main__':
    _cli()
