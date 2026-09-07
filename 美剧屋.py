# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 程序美剧屋 (mjwu.cc)
支持: 分类栏 / 首页推荐 / 分页列表 / 筛选 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)

站点说明:
  美剧屋 提供美剧、电影等影视资源。播放地址通过 `edge.apiimg.com/super.php` 解析页
  返回多条 m3u8 线路 (lineList), 本爬虫取第一条可直接播放的 m3u8 直链返回, 播放走 parse=0。
  解析失败时兜底返回 parse=1 交给内置网页解析。

关键页面:
  首页        : https://www.mjwu.cc/
  分类列表    : https://www.mjwu.cc/type/meiju/  (筛选: /show/meiju/class/../area/../year/../)
  分页        : /type/meiju/page/{n}/
  详情页      : https://www.mjwu.cc/vod/{id}/
  播放页      : https://www.mjwu.cc/play/{id}-{sid}-{nid}/
  解析页      : https://edge.apiimg.com/super.php?id={token}
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

BASE_URL = 'https://www.mjwu.cc'
AD_INFO = "\n\n---\n微信公众号：源力软件汇\nQQ群：1054592152\n更多优质资源尽在源力"

CATEGORIES = [
    {"type_id": "meiju", "type_name": "美剧", "url": "/type/meiju/"},
    {"type_id": "dianying", "type_name": "电影", "url": "/type/dianying/"},
]

FILTER_OPTIONS = [
    {"key": "class", "name": "类型", "value": [
        {"n": "全部", "v": ""},
        {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
        {"n": "动作", "v": "动作"}, {"n": "爱情", "v": "爱情"},
        {"n": "科幻", "v": "科幻"}, {"n": "悬疑", "v": "悬疑"},
        {"n": "惊悚", "v": "惊悚"}, {"n": "恐怖", "v": "恐怖"},
        {"n": "犯罪", "v": "犯罪"}, {"n": "冒险", "v": "冒险"},
        {"n": "奇幻", "v": "奇幻"}, {"n": "战争", "v": "战争"},
        {"n": "历史", "v": "历史"}, {"n": "家庭", "v": "家庭"},
        {"n": "纪录片", "v": "纪录"}, {"n": "动画", "v": "动画"},
    ]},
    {"key": "area", "name": "地区", "value": [
        {"n": "全部", "v": ""},
        {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"},
        {"n": "加拿大", "v": "加拿大"}, {"n": "法国", "v": "法国"},
        {"n": "德国", "v": "德国"}, {"n": "澳大利亚", "v": "澳大利亚"},
        {"n": "西班牙", "v": "西班牙"}, {"n": "意大利", "v": "意大利"},
        {"n": "巴西", "v": "巴西"}, {"n": "墨西哥", "v": "墨西哥"},
        {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "其它", "v": "其它"},
    ]},
    {"key": "year", "name": "年份", "value": [
        {"n": "全部", "v": ""},
        {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
        {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"},
        {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"},
        {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
        {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"},
    ]},
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

    # ==================== 基础 ====================

    def getName(self):
        return "程序美剧屋"

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

    # ==================== 请求 ====================

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

    # ==================== 列表解析 ====================

    def _parse_vods(self, html):
        vods = []
        pattern = re.compile(
            r'<li class="hl-list-item[^"]*">.*?'
            r'<a class="hl-item-thumb[^"]*" href="/vod/(\d+)/" title="([^"]*)" '
            r'data-original="([^"]*)"',
            re.S
        )
        for m in pattern.finditer(html):
            vid, name, pic = m.group(1), m.group(2), m.group(3)
            win = html[m.start():m.start() + 700]
            remark = ''
            rm = re.search(r'<span class="hl-lc-1 remarks">([^<]*)</span>', win)
            if rm:
                remark = rm.group(1).strip()
            score = ''
            sm = re.search(r'<span class="hl-text-conch score">([^<]*)</span>', win)
            if sm:
                score = sm.group(1).strip()
            if score:
                remark_text = ('%s * %s' % (score, remark)).strip(' *')
            else:
                remark_text = remark
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
        m = re.search(r'(\d+)\s*&nbsp;\s*/\s*&nbsp;\s*(\d+)\s*页', html)
        if m:
            try:
                max_pg = max(max_pg, int(m.group(2)))
            except ValueError:
                pass
        for mm in re.finditer(r'page/(\d+)/', html):
            try:
                max_pg = max(max_pg, int(mm.group(1)))
            except ValueError:
                pass
        return max_pg

    # ==================== 首页 ====================

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result = {"class": classes}
        filters = {str(c["type_id"]): FILTER_OPTIONS for c in CATEGORIES}
        result["filters"] = filters
        html = self._get(BASE_URL + '/')
        result['list'] = self._parse_vods(html)[:20]
        return result

    def homeVideoContent(self):
        html = self._get(BASE_URL + '/')
        return {"list": self._parse_vods(html)}

    # ==================== 分类 / 筛选 ====================

    def _collect_filters(self, filter, extend):
        opts = {}

        def absorb(src):
            if isinstance(src, dict):
                for k, v in src.items():
                    if k in ('class', 'area', 'year') and v:
                        if isinstance(v, dict):
                            v = v.get('value') or v.get('v') or v.get('n') or ''
                            if isinstance(v, dict):
                                v = v.get('v') or ''
                        if str(v):
                            opts[k] = str(v)
            elif isinstance(src, list):
                for it in src:
                    if not isinstance(it, dict):
                        continue
                    k = it.get('key') or it.get('name')
                    v = it.get('value') or it.get('v')
                    if k in ('class', 'area', 'year') and v:
                        if isinstance(v, dict):
                            v = v.get('v') or ''
                        if str(v):
                            opts[k] = str(v)

        absorb(extend)
        absorb(filter)
        return opts

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except (TypeError, ValueError):
            page = 1
        page = max(page, 1)
        cat = next((c for c in CATEGORIES if c['type_id'] == tid), None)
        if cat is None:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

        slug = tid
        pref = '/type/%s/' % slug
        opts = self._collect_filters(filter, extend)
        if opts:
            pref = '/show/%s/' % slug
            for seg in ('class', 'area', 'year'):
                if seg in opts:
                    pref += '%s/%s/' % (seg, quote(str(opts[seg]), safe=''))
        path = pref.rstrip('/')
        if page > 1:
            path += '/page/%d' % page
        path += '/'

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

    # ==================== 详情 ====================

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._get('/vod/%s/' % (re.match(r'[^?]*', vid).group(0),))
        if not html:
            return {"list": []}
        return {"list": [self._parse_detail(vid, html)]}

    def _parse_detail(self, vid, html):
        name = ''
        nm = re.search(r'<h2[^>]*class="hl-dc-title[^"]*"[^>]*>(.*?)</h2>', html, re.S)
        if nm:
            name = self._clean(nm.group(1))
            ym = re.search(r'[（(]?(\d{4})[）)]?$', name)
            if ym:
                name = name[:ym.start()].strip()
        if not name:
            nm2 = re.search(r'<title>([^<]+)</title>', html)
            if nm2:
                name = self._clean(nm2.group(1))

        pic = ''
        pm = re.search(r'data-original="(https?://[^"]+)"', html)
        if pm:
            pic = pm.group(1)

        score = ''
        sm = re.search(r'hl-score-nums[^>]*>\s*<span>([\d.]+)</span>', html)
        if sm:
            score = sm.group(1)

        year = ''
        ym = re.search(r'年份：</em>\s*(\d{4})', html)
        if ym:
            year = ym.group(1)

        def _em_block(label):
            m = re.search(label + r'：</em>(.*?)</li>', html, re.S)
            if not m:
                return ''
            t = self._clean(m.group(1))
            t = t.replace('/', '')
            return re.sub(r'\s+', ' ', t).strip()

        area = _em_block('地区')
        genre = _em_block('类型')
        actor = _em_block('主演')
        director = _em_block('导演')

        status = ''
        stm = re.search(r'状态：</em>\s*<span[^>]*>([^<]+)</span>', html)
        if stm:
            status = stm.group(1).strip()

        blurb = ''
        bm = re.search(r'简介：</em>(.*?)</li>', html, re.S)
        if bm:
            blurb = self._clean(bm.group(1))

        content = blurb or ''
        if content:
            content += AD_INFO
        else:
            dm = re.search(r'<meta name="description" content="([^"]+)"', html)
            if dm:
                content = dm.group(1).replace('剧情:', '').strip() + AD_INFO

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

        # 选集
        froms = [f for f in re.findall(
            r'<a[^>]*class="hl-tabs-btn[^"]*"[^>]*alt="([^"]*)"', html)]
        blocks = re.findall(
            r'<div class="hl-tabs-box[^"]*"[^>]*>\s*<div class="row">.*?'
            r'<ul[^>]*class="hl-plays-list[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        if not blocks:
            blocks = re.findall(r'<div class="hl-tabs-box[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        if not blocks:
            blocks = [html]

        groups = []
        for i, block in enumerate(blocks):
            src = froms[i] if i < len(froms) and froms[i] else '云播'
            eps = []
            seen = set()
            for m in re.finditer(r'<a[^>]*href="/play/(\d+)-(\d+)-(\d+)/"[^>]*>([^<]+)</a>', block):
                key = (m.group(2), m.group(3))
                if key in seen:
                    continue
                seen.add(key)
                label = m.group(4).strip() or '播放'
                eps.append('%s$%s-%s-%s' % (label, m.group(1), m.group(2), m.group(3)))
            if eps:
                groups.append((src, '#'.join(eps)))

        if groups:
            vod['vod_play_from'] = '$$$'.join(g[0] for g in groups)
            vod['vod_play_url'] = '$$$'.join(g[1] for g in groups)

        return vod

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        if not key:
            return {"list": []}
        try:
            page = max(int(pg), 1)
        except (TypeError, ValueError):
            page = 1
        url = '/search/--/wd=%s/' % quote(str(key), safe='')
        if page > 1:
            url = url.rstrip('/') + '/page/%d/' % page
        html = self._get(url)
        if html and '安全验证' not in html and 'verify' not in html.lower():
            return {"list": self._parse_vods(html)}
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
        if id.startswith('http'):
            play_path = id
        else:
            play_path = urljoin(BASE_URL, '/play/%s/' % id.strip('/'))
        html = self._get(play_path)
        enc = ''
        raw_enc = ''
        m3u8 = ''
        if html:
            pm = re.search(r'var player_aaaa\s*=\s*(\{.*?\})\s*;?\s*<', html, re.S)
            if pm:
                try:
                    data = json.loads(pm.group(1))
                    enc = data.get('url') or ''
                    raw_enc = enc
                    en = int(data.get('encrypt') or 0)
                    if en == 2:
                        try:
                            enc = urllib.parse.unquote(
                                base64.b64decode(enc).decode('utf-8', 'replace'))
                        except Exception:
                            enc = ''
                    elif en == 1:
                        enc = urllib.parse.unquote(enc)
                    frm = data.get('from') or ''
                    if frm == 'juhe' and enc:
                        m3u8 = self._resolve(enc)
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
        # 兜底: 交给内置网页解析
        resolver = play_path
        if enc:
            resolver = 'https://edge.apiimg.com/super.php?id=%s' % quote(
                raw_enc or enc, safe='')
        return {
            'parse': 1,
            'playUrl': '',
            'url': resolver,
            'header': json.dumps(header, ensure_ascii=False),
        }

    def _resolve(self, enc):
        if not enc:
            return ''
        resolver = 'https://edge.apiimg.com/super.php?id=%s' % quote(enc, safe='')
        page = self._get(resolver)
        if not page:
            return ''
        m = re.search(r'lineList\s*:\s*(\[.*?\])', page, re.S)
        if m:
            try:
                lines = json.loads(m.group(1))
            except Exception:
                lines = []
            for line in lines:
                if not isinstance(line, dict):
                    continue
                u = line.get('url', '') or ''
                if u and re.search(r'\.(m3u8|mp4)', u, re.I):
                    return u.replace('\\/', '/')
        for u in re.findall(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', page):
            return u.replace('\\/', '/')
        for u in re.findall(r'"(?:url|playUrl|backup)"\s*:\s*"([^"]+)"', page):
            if '.m3u8' in u or '.mp4' in u:
                return u.replace('\\/', '/')
        return ''


# ==================== CLI 测试 ====================

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
        print("用法: python 程序美剧屋.py home|categories|list <分类id> <页>|detail <影片ID>|play <播放页>|search <关键词>")
        return
    cmd = sys.argv[1].lower()
    if cmd == 'home':
        print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2))
    elif cmd == 'categories':
        print(json.dumps(sp.homeContent(True)['class'], ensure_ascii=False, indent=2))
    elif cmd == 'list':
        tid = sys.argv[2] if len(sys.argv) > 2 else 'meiju'
        pg = sys.argv[3] if len(sys.argv) > 3 else '1'
        print(json.dumps(sp.categoryContent(tid, pg, None, None), ensure_ascii=False, indent=2))
    elif cmd == 'filter':
        tid = sys.argv[2] if len(sys.argv) > 2 else 'meiju'
        ext = sys.argv[3] if len(sys.argv) > 3 else 'year:2026'
        ed = {}
        for pair in ext.replace('&', ';').split(';'):
            if ':' in pair:
                k, v = pair.split(':', 1)
                ed[k.strip()] = v.strip()
        print(json.dumps(sp.categoryContent(tid, '1', None, ed), ensure_ascii=False, indent=2))
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