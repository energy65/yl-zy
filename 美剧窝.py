# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 美剧窝 (mjwo.net)
支持: 分类栏 / 首页推荐 / 分页列表 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)

站点说明:
  美剧窝 提供美剧、电影等影视资源。播放地址通过 `edge.apiimg.com/super.php` 解析页
  返回多条 m3u8 线路, 本爬虫取第一条可直接播放的 m3u8。
  搜索接口 `/search/--{关键词}/` 受安全验证码(安全验证)保护, 自动切换为遍历
  分类列表按名称匹配的兜底方案(受限于页数, 可能命中不全, 可返回最近更新的内容)。

关键页面:
  首页        : https://www.mjwo.net/
  分类列表    : https://www.mjwo.net/type/{slug}-{pg}/
  详情页      : https://www.mjwo.net/vod/{id}/
  播放页      : https://www.mjwo.net/play/{id}-{sid}-{nid}/
  解析页      : https://edge.apiimg.com/super.php?id={base64}
"""

import re
import json
import ssl
from urllib.parse import quote, urljoin

try:
    import requests
except ImportError:
    requests = None

from base.spider import Spider

BASE_URL = 'https://www.mjwo.net'
AD_INFO = "\n\n---\n微信公众号：源力软件汇\nQQ群：1054592152\n伴随更多优质资源尽在源力"

CATEGORIES = [
    {"type_id": "dianying", "type_name": "电影", "url": "/type/dianying/"},
    {"type_id": "meiju", "type_name": "美剧", "url": "/type/meiju/"},
    {"type_id": "gangju", "type_name": "港剧", "url": "/type/gangju/"},
    {"type_id": "dongzuopian", "type_name": "动作片", "url": "/type/dongzuopian/"},
    {"type_id": "xijupian", "type_name": "喜剧片", "url": "/type/xijupian/"},
    {"type_id": "aiqingpian", "type_name": "爱情片", "url": "/type/aiqingpian/"},
    {"type_id": "kehuanpian", "type_name": "科幻片", "url": "/type/kehuanpian/"},
    {"type_id": "kongbupian", "type_name": "恐怖片", "url": "/type/kongbupian/"},
    {"type_id": "juqingpian", "type_name": "剧情片", "url": "/type/juqingpian/"},
    {"type_id": "zhanzhengpian", "type_name": "战争片", "url": "/type/zhanzhengpian/"},
    {"type_id": "donghuapian", "type_name": "动画片", "url": "/type/donghuapian/"},
]


class Spider(Spider):

    HEADERS = {
        'User-Agent': ('Mozilla/5.0 (Linux; Android 12; SM-G991B) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Mobile Safari/537.36'),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': BASE_URL + '/',
    }

    _sess = None

    # ==================== 基础 ====================

    def getName(self):
        return "美剧窝"

    def init(self, cfg=''):
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass
        if requests is not None and self.__class__._sess is None:
            self.__class__._sess = requests.Session()
            self.__class__._sess.headers.update(self.HEADERS)
            self.__class__._sess.verify = False
        return self

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return None

    # ==================== 请求 ====================

    def _get(self, url):
        sess = self.__class__._sess
        if sess is None:
            self.init()
            sess = self.__class__._sess
        if sess is None:
            return ''
        if not url.startswith('http'):
            url = urljoin(BASE_URL, url)
        try:
            resp = sess.get(url, timeout=15, allow_redirects=True)
            resp.encoding = 'utf-8'
            return resp.text if resp.status_code == 200 else ''
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

    # ==================== 列表解析 ====================

    def _parse_vods(self, html):
        vods = []
        for m in re.finditer(
                r'<a[^>]*class="myui-vodlist__thumb[^"]*"[^>]*>.*?</a>', html, re.DOTALL):
            tag = m.group(0)
            hm = re.search(r'href="(/vod/(\d+)/?)"', tag)
            if not hm:
                continue
            href = hm.group(1)
            vid = hm.group(2)
            tm = re.search(r'title="([^"]*)"', tag)
            name = self._clean(tm.group(1)) if tm else ''
            pic = ''
            pm = re.search(r'data-original="([^"]+)"', tag)
            if pm:
                pic = pm.group(1)
            if not pic:
                sm = re.search(r'style="[^"]*background:\s*url\(([^)]+)\)', tag)
                if sm:
                    pic = sm.group(1).strip("'\" ")
            vods.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        # 按列表项补副标题(更新说明等)
        lis = re.findall(r'<li class="?col-[^"]*"?>(.*?)</li>', html, re.DOTALL)
        pic_map = {v['vod_id']: i for i, v in enumerate(vods)}
        for li in lis:
            am = re.search(r'href="(/vod/(\d+)/?)[^"]*"', li)
            if not am:
                continue
            vid = am.group(2)
            if vid not in pic_map:
                continue
            idx = pic_map[vid]
            tm = re.search(r'<span class="pic-text[^"]*"[^>]*>\s*([^<]+?)\s*</span>', li)
            if tm:
                vods[idx]['vod_remarks'] = self._clean(tm.group(1))
            elif vods[idx]['vod_remarks'] == '':
                dt = re.search(r'class="text[^"]*"[^>]*>\s*(.*?)\s*</p>', li, re.DOTALL)
                if dt:
                    vods[idx]['vod_remarks'] = self._clean(dt.group(1))
        # 过滤没有 id 的空项
        vods = [v for v in vods if v['vod_id']]
        # 去重(页面含排行榜侧栏, 同一影片可能重复出现)
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
        for m in re.finditer(r'/type/[^"\']+-(\d+)/?', html):
            try:
                max_pg = max(max_pg, int(m.group(1)))
            except ValueError:
                pass
        return max_pg

    # ==================== 首页 ====================

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result = {"class": classes}
        html = self._get(BASE_URL + '/')
        result['list'] = self._parse_vods(html)[:20]
        return result

    def homeVideoContent(self):
        html = self._get(BASE_URL + '/')
        return {"list": self._parse_vods(html)}

    # ==================== 分类 ====================

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except (TypeError, ValueError):
            page = 1
        cat = next((c for c in CATEGORIES if c['type_id'] == tid), None)
        if cat is None:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        path = cat['url'].rstrip('/') if page == 1 else cat['url'].rstrip('/') + '-%d' % page
        html = self._get(path + '/')
        vods = self._parse_vods(html)
        pc = self._pagecount(html)
        pc = max(pc, page)
        limit = len(vods) if vods else 20
        return {
            "list": vods,
            "page": page,
            "pagecount": pc if pc else 1,
            "limit": limit,
            "total": pc * limit,
        }

    # ==================== 详情 ====================

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._get('/vod/%s/' % (re.match(r'[^?]*', vid).group(0),))
        if not html:
            return {"list": []}

        vod = self._parse_detail(vid, html)
        return {"list": [vod]}

    def _parse_detail(self, vid, html):
        name = ''
        nm = re.search(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', html, re.DOTALL)
        if nm:
            name = self._clean(nm.group(1))
            nm2 = re.search(r'<span class="year">\s*\((\d+)\)\s*</span>', nm.group(1))
            if nm2:
                name = name.replace('(%s)' % nm2.group(1), '').replace(nm2.group(1), '').strip()
        if not name:
            nm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
            if nm:
                name = self._clean(nm.group(1))

        pic = ''
        pm = re.search(r'<div class="myui-content__thumb">.*?<img[^>]*data-original="([^"]+)"',
                       html, re.DOTALL)
        if pm:
            pic = pm.group(1)
        if not pic:
            pm = re.search(r'<img[^>]*class="lazyload"[^>]*data-original="([^"]+)"',
                           html, re.DOTALL)
            if pm:
                pic = pm.group(1)

        remark = ''
        rm = re.search(r'<p[^>]*class="otherbox"[^>]*>(.*?)</p>', html, re.DOTALL)
        if rm:
            remark = self._clean(rm.group(1))

        year = ''
        ym = re.search(r'<h1[^>]*class="title"[^>]*>.*?<span class="year">\s*\(?(\d{4})\)?\s*</span>',
                       html, re.DOTALL)
        if ym:
            year = ym.group(1)

        area = ''
        am = re.search(r'<span class="text-muted[^"]*">地区：</span>(.*?)</p>', html, re.DOTALL)
        if am:
            area = ','.join(self._clean(a) for a in re.findall(r'>([^<>]+?)</a>', am.group(1)))
            if not area:
                area = self._clean(am.group(1))

        actor = ''
        ac = re.search(r'<span class="text-muted[^"]*">主演：</span>(.*?)</p>', html, re.DOTALL)
        if ac:
            actor = ','.join(self._clean(a) for a in re.findall(r'>([^<>]+?)</a>', ac.group(1)))
            if not actor:
                actor = self._clean(ac.group(1))

        director = ''
        dc = re.search(r'<span class="text-muted[^"]*">导演：</span>(.*?)</p>', html, re.DOTALL)
        if dc:
            director = ','.join(self._clean(a) for a in re.findall(r'>([^<>]+?)</a>', dc.group(1)))
            if not director:
                director = self._clean(dc.group(1))

        genre = ''
        gm = re.search(r'<span class="text-muted[^"]*">类型：</span>(.*?)</p>', html, re.DOTALL)
        if gm:
            genre = ','.join(self._clean(a) for a in re.findall(r'>([^<>]+?)</a>', gm.group(1)))
            if not genre:
                genre = self._clean(gm.group(1))

        content = ''
        cm = re.search(r'<div[^>]*id="desc"[^>]*>.*?<span class="data"[^>]*>(.*?)</span>',
                       html, re.DOTALL)
        if not cm:
            cm = re.search(r'<div[^>]*class="col-pd text-collapse content"[^>]*>.*?<span class="data"[^>]*>(.*?)</span>',
                           html, re.DOTALL)
        if cm:
            content = self._clean(cm.group(1))
        if not content:
            dm = re.search(r'<meta name="description" content="([^"]+)"', html)
            if dm:
                content = dm.group(1).replace('剧情:', '').strip()
        if content:
            content += AD_INFO

        # 选集
        play_list = []
        seen = set()
        for m in re.finditer(
                r'<a[^>]*class="btn[^"]*"[^>]*href="(/play/(\d+)-(\d+)-(\d+)/?)"[^>]*>'
                r'([^<]+)</a>', html):
            href = m.group(1)
            sid, nid = m.group(3), m.group(4)
            label = self._clean(m.group(5))
            key = (sid, nid)
            if key in seen:
                continue
            seen.add(key)
            play_list.append((label + ('' if label.endswith('集') else ''), self._fix_url(href)))

        vod = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': remark,
            'vod_year': year,
            'vod_area': area,
            'vod_actor': actor,
            'vod_director': director,
            'vod_class': genre,
            'vod_content': content,
            'type_name': genre,
        }
        if play_list:
            vod['vod_play_from'] = '云播'
            vod['vod_play_url'] = '#'.join('%s$%s' % (label or '播放', u) for label, u in play_list)
        else:
            vod['vod_play_from'] = ''
            vod['vod_play_url'] = ''
        return vod

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        url = '/search/--%s/' % quote(str(key), safe='')
        html = self._get(url)
        if html and '安全验证' not in html and 'verify' not in html.lower():
            return {"list": self._parse_vods(html)}
        # 搜索接口受验证码保护, 使用兜底方案
        return {"list": self._search_fallback(key, pg)}

    def _search_fallback(self, key, pg='1'):
        key = str(key).strip().lower()
        if not key:
            return []
        try:
            page = max(int(pg), 1)
        except (TypeError, ValueError):
            page = 1
        results = []
        seen = set()
        max_pages = 4
        # pg 页若为分类页则从该页开始
        start_page = page if page <= max_pages else 1
        for cat in CATEGORIES:
            for i in range(start_page, max_pages + 1):
                data = self.categoryContent(cat['type_id'], i, None, None)
                for item in data.get('list', []):
                    vid = item.get('vod_id', '')
                    nm = item.get('vod_name', '')
                    if key in nm.lower() and vid not in seen:
                        seen.add(vid)
                        results.append(item)
                if len(results) >= 30:
                    break
            if len(results) >= 30:
                break
        return results

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        play_url = self._fix_url(id)
        html = self._get(play_url)
        m3u8 = ''
        if html:
            pm = re.search(r'var player_aaaa\s*=\s*\{[^<]*?["\']url["\']\s*:\s*["\']([^"\']+)["\']', html, re.DOTALL)
            if pm:
                enc = pm.group(1)
                if enc:
                    m3u8 = self._resolve(enc)
        if not m3u8:
            m3u8 = play_url
        header = {
            'User-Agent': self.HEADERS['User-Agent'],
            'Referer': BASE_URL + '/',
        }
        return {
            'parse': 0,
            'playUrl': '',
            'url': m3u8,
            'header': json.dumps(header, ensure_ascii=False),
        }

    def _resolve(self, enc):
        resolver = 'https://edge.apiimg.com/super.php?id=%s' % quote(enc, safe='')
        sess = self.__class__._sess
        if sess is None:
            return ''
        try:
            r = sess.get(resolver, timeout=15, allow_redirects=True)
            page = r.text
        except Exception:
            return ''
        if not page:
            return resolver
        # 解析 lineList 中的 m3u8 / mp4 线路, 取第一条
        m = re.search(r'lineList\s*:\s*(\[.*?\])', page, re.DOTALL)
        if m:
            try:
                lines = json.loads(m.group(1))
            except Exception:
                lines = []
            for line in lines:
                u = line.get('url', '')
                if u and re.search(r'\.(m3u8|mp4)', u, re.I):
                    return u.replace('\\/', '/')
        for u in re.findall(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', page):
            return u.replace('\\/', '/')
        return resolver


# ==================== CLI 测试 ====================

def _cli():
    import sys
    if requests is not None:
        requests.packages.urllib3.disable_warnings()
    sp = Spider()
    sp.init()
    if len(sys.argv) < 2:
        print("用法: python 美剧窝.py home|categories|list <分类id> <页>|detail <影片ID>|play <播放页>|search <关键词>")
        return
    cmd = sys.argv[1].lower()
    if cmd == 'home':
        print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2))
    elif cmd == 'categories':
        print(json.dumps(sp.homeContent(True)['class'], ensure_ascii=False, indent=2))
    elif cmd == 'list':
        tid = sys.argv[2] if len(sys.argv) > 2 else 'dianying'
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
        print(json.dumps({'list': sp.searchContent(key, 0, pg)}, ensure_ascii=False, indent=2))
    else:
        print("未知命令")


if __name__ == '__main__':
    _cli()
