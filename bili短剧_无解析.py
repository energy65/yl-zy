# coding=utf-8
# 哔哩哔哩短剧(无解析) TVBox Python 爬虫
# 站点: https://www.bilibili.com/
# 分类: 短剧 (season_type=8, bilibili竖屏短剧)
# 数据: B站 PGC 短剧列表接口 + 官方视频/播放接口 (纯标准库, 无第三方解析依赖)
# 播放: 直接调用 B站 playurl 接口获取真实可播放的 MP4/DASH 地址,
#       无需任何解析器, 返回直链交由 TVBox 直接播放.
# 画质: 未登录默认360p, 填入SESSDATA可解锁1080p/4K
#       配置方式: extend 填 "SESSDATA=你的值" 或 {"SESSDATA":"你的值"}
#       获取方式: 浏览器登录bilibili.com -> F12 -> Application -> Cookies -> 复制SESSDATA值
# 关注微信公众号"源力软件汇", Q群1054592152, 伴随更多优质资源尽在源力。
import json
import re

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider(object):
        def __init__(self):
            self.extend = ''

try:
    import requests
except Exception:
    requests = None

API = 'https://api.bilibili.com'
WEB = 'https://www.bilibili.com'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': WEB + '/',
}
PLAY_HEADER = {'User-Agent': UA, 'Referer': WEB + '/'}

PROMO = '\n\n关注微信公众号"源力软件汇"，Q群1054592152，伴随更多优质资源尽在源力。'

CATES = [
    {'type_id': 'duanju', 'type_name': '短剧'},
]

ORDERS = [
    {'n': '最近更新', 'v': '0'},
    {'n': '最多播放', 'v': '2'},
]

FALLBACK_STYLE = [
    ('-1', '全部'), ('10014', '都市'), ('10016', '热血'),
    ('10017', '穿越'), ('10018', '奇幻'), ('10019', '剧情'),
    ('10020', '搞笑'), ('10021', '恋爱'), ('10024', '悬疑'),
]

QUALITY_GUEST = 16
QUALITY_LOGIN = 127
DEFAULT_SESSDATA = 'de862926%2C1804412418%2Ce3174%2A91CjBzw9Tb4NzDki8U4lHOecjbf4Fyha_bfnmNSp1I0GXxNfTlD_3mH8HrDV-nS1ft6kISVlp1dGtabEdVVWNBQW8xTlNoc2JaMkJZMTZjLXlUSVRvUm1aeUV3X1dsZ05tRTkzdkhpV2g3cnhiOVg0RHJEVkpILW5vdEUwRF9WOHV2ek9GSHNkbDZnIIEC'


def _strip(s):
    if not s:
        return ''
    return re.sub(r'<[^>]+>', '', str(s)).replace('&amp;', '&').replace('&quot;', '"').strip()


def _pic(u):
    u = u or ''
    if u.startswith('//'):
        return 'https:' + u
    return u


class Spider(_BaseSpider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = 'bili影视_无解析'
        self.session = None
        self._cookie_ok = False
        self._conditions = None
        self._sessdata = ''

    def getName(self):
        return self.name

    def init(self, extend=''):
        self.extend = extend or ''
        if not self.session and requests:
            self.session = requests.Session()
            self.session.headers.update(HEADERS)
            try:
                from requests.adapters import HTTPAdapter
                ad = HTTPAdapter(max_retries=2, pool_connections=10, pool_maxsize=10)
                self.session.mount('http://', ad)
                self.session.mount('https://', ad)
            except Exception:
                pass
        # 解析 extend 中的 SESSDATA (支持 JSON 和纯文本两种格式)
        # 用法: extend 填 "SESSDATA=你的值" 或 {"SESSDATA":"你的值"}
        # 不填则使用内置默认SESSDATA (1080p)
        ext = str(self.extend or '').strip()
        if ext.startswith('{'):
            try:
                ej = json.loads(ext)
                ext = ej.get('SESSDATA') or ej.get('sessdata') or ''
            except Exception:
                ext = ''
        else:
            m = re.search(r'SESSDATA=([^;\"\']+)', ext)
            ext = m.group(1) if m else ''
        self._sessdata = (ext or '').strip() or DEFAULT_SESSDATA
        # 先初始化风控Cookie, 再叠加SESSDATA
        self._ensure_cookies()
        if self._sessdata:
            self._set_cookie('SESSDATA', self._sessdata)
        return None

    def _set_cookie(self, k, v):
        try:
            if self.session:
                self.session.cookies.set(k, v, domain='.bilibili.com')
        except Exception:
            pass

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass

    def _ensure_cookies(self):
        if self._cookie_ok or not self.session:
            return
        try:
            self.session.get(WEB + '/', timeout=10)
        except Exception:
            pass
        try:
            d = self.session.get(API + '/x/frontend/finger/spi', timeout=10).json() or {}
            dd = d.get('data') or {}
            if dd.get('b_3'):
                self._set_cookie('buvid3', dd['b_3'])
            if dd.get('b_4'):
                self._set_cookie('buvid4', dd['b_4'])
        except Exception:
            pass
        self._cookie_ok = True

    def _get_json(self, path, params=None):
        self._ensure_cookies()
        if self.session:
            try:
                r = self.session.get(API + path, params=params, timeout=15)
                return r.json()
            except Exception:
                pass
        try:
            import ssl
            import urllib.request
            import urllib.parse
            qs = urllib.parse.urlencode(params or {})
            url = API + path + ('?' + qs if qs else '')
            req = urllib.request.Request(url, headers=dict(HEADERS))
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return json.loads(resp.read().decode('utf-8', 'ignore'))
        except Exception:
            return {}

    def _extract_avid(self, link):
        m = re.search(r'av(\d+)', str(link or ''))
        return m.group(1) if m else ''

    def _load_conditions(self):
        if self._conditions is not None:
            return self._conditions
        out = {}
        d = self._get_json('/pgc/season/index/condition', {'season_type': 8, 'type': 1})
        data = d.get('data') if isinstance(d.get('data'), dict) else {}
        flt = []
        for f in (data.get('filter') or []):
            vals = [(str(v.get('keyword')), v.get('name')) for v in (f.get('values') or [])
                    if v.get('keyword') is not None and v.get('name')]
            if vals:
                flt.append((f.get('field'), f.get('name'), vals))
        out[8] = flt or [('style_id', '风格', FALLBACK_STYLE)]
        self._conditions = out
        return out

    def homeContent(self, filter):
        result = {'class': CATES, 'filters': {}}
        try:
            conds = self._load_conditions()
            flist = []
            for field, fname, vals in conds.get(8, []):
                if len(vals) <= 1:
                    continue
                options = [{'n': n, 'v': v} for v, n in vals[:40]]
                flist.append({'key': field, 'name': fname, 'value': options})
            flist.append({'key': 'order', 'name': '排序', 'value': ORDERS})
            result['filters']['duanju'] = flist
        except Exception:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos, seen = [], set()
        try:
            d = self._get_json('/pgc/season/index/result',
                               {'type': 1, 'season_type': 8, 'page': 1,
                                'pagesize': 20, 'order': 2, 'sort': 0})
            data = d.get('data') if isinstance(d.get('data'), dict) else {}
            for it in (data.get('list') or []):
                sid = it.get('season_id')
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                videos.append({
                    'vod_id': 'ss%s' % sid,
                    'vod_name': _strip(it.get('title')),
                    'vod_pic': _pic(it.get('cover')),
                    'vod_remarks': it.get('order') or it.get('subTitle') or '',
                })
        except Exception:
            pass
        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        pg = int(pg) if pg else 1
        if pg < 1:
            pg = 1
        if not isinstance(ext, dict):
            try:
                ext = json.loads(ext or '{}')
            except Exception:
                ext = {}
        order = str(ext.get('order', '0'))
        videos, total = [], 0
        try:
            params = {'type': 1, 'season_type': 8, 'page': pg,
                      'pagesize': 24, 'order': order, 'sort': 0}
            for k, v in (ext or {}).items():
                if k in ('order', 'sort') or v in ('-1', '', None):
                    continue
                params[k] = v
            d = self._get_json('/pgc/season/index/result', params)
            data = d.get('data') if isinstance(d.get('data'), dict) else {}
            total = int(data.get('total') or 0)
            for it in (data.get('list') or []):
                sid = it.get('season_id')
                if not sid:
                    continue
                remarks = []
                if it.get('badge'):
                    remarks.append(it['badge'])
                if it.get('order'):
                    remarks.append(it['order'])
                if it.get('subTitle'):
                    remarks.append(it['subTitle'])
                videos.append({
                    'vod_id': 'ss%s' % sid,
                    'vod_name': _strip(it.get('title')),
                    'vod_pic': _pic(it.get('cover')),
                    'vod_remarks': ' | '.join(remarks) if remarks else '',
                })
        except Exception:
            pass
        pagecount = max(1, (total + 23) // 24) if total else pg + 1
        return {
            'list': videos, 'page': pg, 'pagecount': pagecount,
            'limit': len(videos), 'total': total or 9999,
        }

    def detailContent(self, ids):
        did = str(ids[0])
        result = {}
        try:
            sid = did[2:] if did.startswith('ss') else did
            d = self._get_json('/pgc/season/index/result',
                               {'type': 1, 'season_type': 8, 'page': 1, 'pagesize': 50, 'order': 0})
            data = d.get('data') if isinstance(d.get('data'), dict) else {}
            target = None
            for it in (data.get('list') or []):
                if str(it.get('season_id')) == str(sid):
                    target = it
                    break
            if not target:
                for pg2 in range(2, 8):
                    d2 = self._get_json('/pgc/season/index/result',
                                         {'type': 1, 'season_type': 8, 'page': pg2, 'pagesize': 50, 'order': 0})
                    data2 = d2.get('data') if isinstance(d2.get('data'), dict) else {}
                    for it in (data2.get('list') or []):
                        if str(it.get('season_id')) == str(sid):
                            target = it
                            break
                    if target:
                        break
            if not target:
                raise ValueError('not found')
            link = target.get('link') or ''
            avid = self._extract_avid(link)
            if not avid:
                raise ValueError('no avid')
            vd = self._get_json('/x/web-interface/view', {'aid': avid})
            vdata = vd.get('data') or {}
            title = vdata.get('title') or _strip(target.get('title')) or ''
            cover = vdata.get('pic') or target.get('cover') or ''
            desc = _strip(vdata.get('desc') or '')
            owner = (vdata.get('owner') or {}).get('name', '')
            pubdate = vdata.get('pubdate')
            pub_time = ''
            if pubdate:
                import time
                pub_time = time.strftime('%Y-%m-%d', time.localtime(pubdate))
            stat = vdata.get('stat') or {}
            pages = vdata.get('pages') or []
            if not pages:
                pages = [{'cid': vdata.get('cid'), 'part': title}]

            info = []
            if pub_time:
                info.append('发布时间：%s' % pub_time)
            if stat.get('view'):
                info.append('播放：%s' % self._fmt(stat.get('view')))
            if stat.get('like'):
                info.append('点赞：%s' % self._fmt(stat.get('like')))
            content = ('　'.join(info) + '\n') if info else ''
            if desc:
                content += '简介：' + desc[:500] + '\n'
            content += PROMO

            play_urls = []
            for i, p in enumerate(pages):
                part = _strip(p.get('part') or p.get('title') or ('第%d集' % (i + 1)))
                part = part.replace('$', '').replace('#', '').replace('|', ' ')
                play_urls.append('%s$%s|%s' % (part, avid, p.get('cid')))

            result['list'] = [{
                'vod_id': did,
                'vod_name': title,
                'vod_pic': _pic(cover),
                'vod_actor': owner,
                'vod_director': owner,
                'vod_year': pub_time[:4] if pub_time else '',
                'vod_remarks': target.get('order') or target.get('subTitle') or '',
                'vod_content': content,
                'vod_play_from': '短剧直链[源力软件汇]',
                'vod_play_url': '#'.join(play_urls),
            }]
        except Exception:
            result['list'] = [{
                'vod_id': did, 'vod_name': '', 'vod_pic': '',
                'vod_content': '获取失败，请重试。' + PROMO.strip(),
                'vod_play_from': '短剧直链[源力软件汇]', 'vod_play_url': '',
            }]
        return result

    def _direct_mp4(self, avid, cid):
        # 获取直链: 未登录 360p, 有SESSDATA则请求1080p/4K
        try:
            qn = QUALITY_LOGIN if self._sessdata else QUALITY_GUEST
            d = self._get_json('/x/player/playurl', {
                'avid': avid, 'cid': cid, 'qn': qn,
                'fnver': 0, 'fnval': 0, 'fourk': 1})
            data = d.get('data') or {}
            durl = data.get('durl') or []
            if durl and durl[0].get('url'):
                return durl[0]['url']
            dash = data.get('dash') or {}
            if dash.get('video'):
                v = (dash.get('video') or [{}])[0]
                return v.get('baseUrl') or v.get('base_url') or ''
        except Exception:
            pass
        # 兜底: 用fnval=16请求DASH格式
        try:
            qn = QUALITY_LOGIN if self._sessdata else QUALITY_GUEST
            d = self._get_json('/x/player/playurl', {
                'avid': avid, 'cid': cid, 'qn': qn,
                'fnver': 0, 'fnval': 16, 'fourk': 1})
            data = d.get('data') or {}
            dash = data.get('dash') or {}
            if dash.get('video'):
                v = (dash.get('video') or [{}])[0]
                return v.get('baseUrl') or v.get('base_url') or ''
        except Exception:
            pass
        return ''

    def playerContent(self, flag, id, vipFlags):
        id = str(id)
        if '|' not in id:
            return {'jx': 1, 'parse': 1, 'url': WEB + '/video/' + id,
                    'header': PLAY_HEADER}
        avid, cid = id.split('|', 1)
        url = self._direct_mp4(avid, cid) if cid else ''
        if not url:
            return {'jx': 1, 'parse': 1, 'url': WEB + '/video/av' + avid,
                    'header': PLAY_HEADER}
        return {
            'jx': 0,
            'parse': 0,
            'playUrl': '',
            'url': url,
            'header': dict(PLAY_HEADER),
        }

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _search(self, keyword, page, page_size=24):
        try:
            d = self._get_json('/x/web-interface/search/type', {
                'search_type': 'video', 'keyword': keyword,
                'page': page, 'page_size': page_size})
            return ((d.get('data') or {}).get('result')) or []
        except Exception:
            return []

    @staticmethod
    def _fmt(n):
        try:
            n = int(n)
            if n >= 100000000:
                return '%.1f亿' % (n / 100000000.0)
            if n >= 10000:
                return '%.1f万' % (n / 10000.0)
            return str(n)
        except Exception:
            return str(n)

    def searchContentPage(self, key, quick, page):
        result = {'list': [], 'page': int(page or 1)}
        page = int(page or 1)
        videos = []
        seen = set()
        try:
            d = self._get_json('/x/web-interface/search/type', {
                'search_type': 'video', 'keyword': key, 'page': page})
            data = d.get('data') if isinstance(d.get('data'), dict) else {}
            for it in (data.get('result') or []):
                bvid = it.get('bvid')
                if not bvid or bvid in seen:
                    continue
                seen.add(bvid)
                play = it.get('play')
                remark = ''
                if isinstance(play, int):
                    remark = self._fmt(play) + '播放'
                elif isinstance(play, str) and play.isdigit():
                    remark = self._fmt(play) + '播放'
                elif isinstance(play, str):
                    remark = play
                up = _strip(it.get('author') or '')
                if up:
                    remark = (remark + ' · ' if remark else '') + up
                videos.append({
                    'vod_id': 'bv%s' % bvid,
                    'vod_name': _strip(it.get('title')),
                    'vod_pic': _pic(it.get('pic')),
                    'vod_remarks': remark[:40],
                })
        except Exception:
            pass
        result['list'] = videos
        result['page'] = page
        result['pagecount'] = page + 1 if videos else page
        result['limit'] = len(videos)
        result['total'] = 999999 if videos else 0
        return result

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)


if __name__ == '__main__':
    sp = Spider()
    sp.init('')
