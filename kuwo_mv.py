# -*- coding: utf-8 -*-
"""
kuwo_mv.py - 酷我音乐 MV 本地爬虫 (DrPY type=3 蜘蛛)

以 DrPY / 影视仓 type=3 本地 python 脚本形式运行，
配置文件示例：
    {
        "key": "kuwo_mv PY",
        "name": "kuwo_mv丨PY",
        "api": "./kuwo_mv.py",
        "filterable": 1,
        "quickSearch": 1,
        "searchable": 1,
        "type": 3
    }

实现接口：
    homeContent(filter)        -> 首页分类
    categoryContent(tid,pg,...)-> 分类列表
    detailContent(ids)         -> 详情 + 播放地址
    searchContent(key,quick,pg)-> 搜索
    playerContent(flag,id,...) -> 直链播放

数据源：酷我 Web API（searchMvBykeyWord 搜索 MV，playUrl?type=mv 取 mp4 直链）。
仅用于个人学习交流。
"""
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    from base.spider import Spider
except ImportError:
    sys.path.append('yl-main')
    from base.spider import Spider

try:
    import requests
except ImportError:
    requests = None

# 酷我 web 端鉴权使用的 Cookie 名
HM_COOKIE_NAME = 'Hm_Iuvt_cdb524f42f23cer9b268564v7y735ewrq2324'
DEFAULT_HM_COOKIE_VALUE = 'A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
KUWO_HOME = 'https://www.kuwo.cn/'
PAGE_SIZE = 30

CATEGORIES = [
    {'tid': '华语MV',   'keyword': '华语'},
    {'tid': '粤语MV',   'keyword': '粤语'},
    {'tid': '欧美MV',   'keyword': '欧美'},
    {'tid': '韩语MV',   'keyword': '韩语'},
    {'tid': '日语MV',   'keyword': '日语'},
    {'tid': '国语MV',   'keyword': '国语'},
    {'tid': '中国风MV', 'keyword': '中国风'},
    {'tid': '经典MV',   'keyword': '经典'},
    {'tid': '流行MV',   'keyword': '流行'},
    {'tid': '摇滚MV',   'keyword': '摇滚'},
]

QUALITIES = [
    ('4K超清', 4000),
    ('蓝光1080P', 1080),
    ('高清720P', 720),
    ('标清480P', 480),
    ('流畅', 240),
]


# ==================== Cookie / Secret ====================

class CookieJar:
    """缓存酷我首页下发的 Hm_Iuvt_* Cookie，用于 Secret 计算。"""
    _value = None
    _last_refresh = 0.0

    @classmethod
    def get(cls):
        now = time.time()
        if cls._value and now - cls._last_refresh < 600:
            return cls._value
        val = cls._refresh_from_home() or DEFAULT_HM_COOKIE_VALUE
        cls._value = val
        cls._last_refresh = now
        return val

    @classmethod
    def _refresh_from_home(cls):
        try:
            req = urllib.request.Request(KUWO_HOME, headers={
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                cookies = resp.headers.get_all('Set-Cookie') or []
            for c in cookies:
                if c.startswith(HM_COOKIE_NAME + '='):
                    val = c.split('=', 1)[1].split(';', 1)[0].strip()
                    if val:
                        return val
        except Exception:
            return None
        return None


def _js_parse_int(s):
    """模拟 JS parseInt：只解析前导数字字符（与 JS 一致，不识别科学计数法）。"""
    s = str(s)
    if not s:
        return 0.0
    i = 0
    sign = 1.0
    if i < len(s) and s[i] in '+-':
        if s[i] == '-':
            sign = -1.0
        i += 1
    digits = ''
    while i < len(s) and s[i].isdigit():
        digits += s[i]
        i += 1
    if not digits:
        return 0.0
    try:
        f = float(digits)
    except (ValueError, OverflowError):
        return 0.0
    if f in (float('inf'), float('-inf')):
        return 0.0
    return sign * f


def _js_num_to_str(x):
    """模拟 JS Number.toString()，整数不带 '.0'。"""
    if isinstance(x, int):
        return str(x)
    if x != x:
        return 'NaN'
    if x in (float('inf'), float('-inf')):
        return 'Infinity' if x > 0 else '-Infinity'
    if x == 0:
        return '0'
    abs_x = abs(x)
    if abs_x < 1e-6 or abs_x >= 1e21:
        return repr(x)
    if x.is_integer():
        return str(int(x))
    return repr(x)


def kuwo_secret(t, _d=None):
    """酷我 web 端 _getSecret() 的 Python 实现。"""
    e = HM_COOKIE_NAME
    if not e or not t:
        return ''
    n = ''.join(str(ord(ch)) for ch in e)
    o = len(n) // 5

    def _at(s, idx):
        return s[idx] if 0 <= idx < len(s) else ''

    r_raw = _at(n, o) + _at(n, 2 * o) + _at(n, 3 * o) + _at(n, 4 * o) + _at(n, 5 * o)
    r = _js_parse_int(r_raw)
    c = -(-len(e) // 2)
    l = (2 ** 31) - 1
    if r < 2:
        return ''
    d = _d if _d is not None else (int(round(1e9 * random.random())) % 100000000)
    n = n + str(d)
    while len(n) > 10:
        a = _js_parse_int(n[:10])
        b = _js_parse_int(n[10:])
        n = _js_num_to_str(a + b)
    n = (r * _js_parse_int(n) + c) % l
    h = ''
    for i in range(len(t)):
        xor_val = ord(t[i]) ^ int((n / l) * 255)
        h += ('0' + format(xor_val, 'x')) if xor_val < 16 else format(xor_val, 'x')
        n = (r * n + c) % l
    d_hex = format(d, 'x').rjust(8, '0')
    return h + d_hex


def make_req_id():
    ts = format(int(time.time() * 1000), 'x').rjust(12, '0')[-12:]
    rand_hex = ''.join(random.choice('0123456789abcdef') for _ in range(20))
    return f'{ts}-{rand_hex[:4]}-{rand_hex[4:8]}-{rand_hex[8:12]}-{rand_hex[12:]}'


def http_get_json(url, headers=None, timeout=15):
    h = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Referer': KUWO_HOME,
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or 'utf-8'
        raw = resp.read()
    try:
        text = raw.decode(charset, errors='replace')
    except LookupError:
        text = raw.decode('utf-8', errors='replace')
    return json.loads(text)


def http_get_text(url, headers=None, timeout=15):
    h = {'User-Agent': USER_AGENT, 'Referer': KUWO_HOME}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or 'utf-8'
        return resp.read().decode(charset, errors='replace').strip()


def kuwo_api_get(path, params=None, timeout=15):
    qs = ''
    if params:
        qs = '?' + '&'.join(
            f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items()
        )
    url = 'https://www.kuwo.cn' + path + qs
    cookie_val = CookieJar.get()
    secret = kuwo_secret(cookie_val)
    headers = {
        'Secret': secret,
        'Cookie': f'{HM_COOKIE_NAME}={cookie_val}',
        'csrf': cookie_val,
    }
    return http_get_json(url, headers=headers, timeout=timeout)


def _clean_title(s):
    """去除播放串分隔符，避免与 tvbox 协议冲突。"""
    return re.sub(r'[$#]', '', str(s)).strip()


def _unesc(s):
    """处理酷我返回中未解码的 \\uXXXX 转义序列（如 \\u0026）。"""
    if not isinstance(s, str) or '\\u' not in s:
        return s
    try:
        return json.loads('"' + s.replace('"', '\\"') + '"')
    except Exception:
        return s


# ==================== 业务接口 ====================

def search_mv(keyword, page=1, size=PAGE_SIZE):
    """酷我 MV 搜索 (searchMvBykeyWord)，返回有 MP4 直链的 MV 列表。"""
    pn = max(1, int(page))
    rn = max(1, int(size))
    params = {
        'key': keyword, 'pn': pn - 1, 'rn': rn,
        'httpsStatus': 1, 'reqId': make_req_id(),
    }
    try:
        data = kuwo_api_get('/api/www/search/searchMvBykeyWord', params)
    except Exception:
        data = {}
    if not isinstance(data, dict) or data.get('code') not in (200, '200'):
        data = {}
    d = data.get('data') or {}
    total = int(d.get('total') or 0)
    rows = d.get('mvlist') or []
    items = []
    for r in rows:
        mid = str(r.get('id') or '').strip()
        if not mid:
            continue
        name = _unesc(r.get('name') or '')
        artist = _unesc(r.get('artist') or '')
        pic = r.get('pic') or ''
        if pic and not pic.startswith('http'):
            pic = 'https://img1.kuwo.cn' + pic if pic.startswith('/') else pic
        items.append({
            'mvid': mid,
            'name': name,
            'artist': artist,
            'pic': pic,
            'duration': r.get('duration') or '',
        })
    return {'total': total, 'list': items}


def get_mv_play_url(mvid, quality=None):
    """获取 MV mp4 直链。mvid 为酷我 MV id (searchMvBykeyWord 返回的 id)。"""
    mvid = str(mvid).replace('MV_', '').strip()
    if not mvid:
        return ''
    br = int(quality) if quality else None
    candidates = []
    if br:
        candidates.append(br)
    else:
        candidates = [q for _, q in QUALITIES]
    tried = set()
    for b in candidates:
        if b in tried:
            continue
        tried.add(b)
        params = {
            'mid': mvid, 'type': 'mv', 'httpsStatus': 1,
            'reqId': make_req_id(), 'plat': 'web_www', 'br': b,
        }
        try:
            data = kuwo_api_get('/api/v1/www/music/playUrl', params)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if data.get('code') not in (200, '200') and data.get('success') is not True:
            continue
        url = (data.get('data') or {}).get('url') or ''
        if url and str(url).lower().startswith('http') and _is_video_url(url):
            return str(url)
    return ''


def _is_video_url(url):
    low = str(url).lower().split('?')[0]
    return low.endswith(('.mp4', '.mkv', '.flv', '.m4v'))


def to_vod(item):
    mvid = item.get('mvid') or ''
    name = item.get('name') or ''
    artist = item.get('artist') or ''
    pic = item.get('pic') or ''
    title = (f'{name} - {artist}' if artist else name) or mvid
    duration = item.get('duration') or ''
    remarks = ''
    try:
        remarks = _clean_title('%02d:%02d' % (int(duration) // 60, int(duration) % 60))
    except Exception:
        remarks = artist
    # 用 | 编码元数据，详情页可还原名称与海报
    safe_name = _clean_title(name)
    safe_artist = _clean_title(artist)
    vod_id = '|'.join([mvid, safe_name, safe_artist, pic])
    return {
        'vod_id': vod_id,
        'vod_name': title,
        'vod_pic': pic,
        'vod_remarks': remarks or artist,
        'vod_content': f'歌手：{artist or "未知"}\npic: {pic}',
        'vod_actor': artist,
    }


def parse_vod_id(vod_id):
    parts = str(vod_id).split('|', 3)
    mvid = parts[0] if len(parts) > 0 else ''
    name = parts[1] if len(parts) > 1 else ''
    artist = parts[2] if len(parts) > 2 else ''
    pic = parts[3] if len(parts) > 3 else ''
    return mvid, name, artist, pic


# ==================== 蜘蛛类 ====================

class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = '酷我MV'
        self.host = KUWO_HOME

    def getName(self):
        return '酷我MV'

    def init(self, extend=''):
        pass

    def isVideoFormat(self, url):
        return _is_video_url(url)

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter=False):
        result = {'class': [], 'filters': {}, 'list': []}
        classes = []
        filters = {}
        for c in CATEGORIES:
            classes.append({'type_id': c['tid'], 'type_name': c['tid']})
            filters[c['tid']] = []
        classes.append({'type_id': '热搜MV', 'type_name': '热搜MV'})
        filters['热搜MV'] = []
        result['class'] = classes
        result['filters'] = filters
        # 首页推荐：热门 MV
        try:
            res = search_mv('热门MV', page=1)
            result['list'] = [to_vod(i) for i in res['list']]
        except Exception:
            result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('热搜MV', 1, False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {'list': []}
        try:
            pg = int(pg) if pg else 1
            keyword = self._tid_to_keyword(tid)
            kw = keyword or '华语'
            if tid == '热搜MV':
                kw = '热门MV'
            res = search_mv(kw, page=pg)
            vods = [to_vod(i) for i in res['list']]
            result['list'] = vods
            result['page'] = pg
            total = res.get('total') or 0
            result['pagecount'] = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE) if total else pg + 1
            result['limit'] = PAGE_SIZE
            result['total'] = total
        except Exception as e:
            result['list'] = []
            result['page'] = pg
            result['pagecount'] = 1
            result['limit'] = PAGE_SIZE
            result['total'] = 0
        return result

    def detailContent(self, ids):
        result = {'list': []}
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            vid = str(vid).strip()
            if not vid:
                return result
            # 优先解析编码元数据 (mvid|name|artist|pic)
            mvid, name, artist, pic = parse_vod_id(vid) if '|' in vid else (vid, '', '', '')
            mvid = str(mvid).strip()
            if not mvid:
                return result
            title = (f'{name} - {artist}' if artist else name) or f'MV_{mvid}'
            play_url = get_mv_play_url(mvid)
            vod = {
                'vod_id': mvid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '酷我MV',
                'vod_content': f'歌手：{artist or "未知"}\n酷我音乐 MV 直链播放。',
                'vod_actor': artist,
                'vod_play_from': '酷我MV',
                'vod_play_url': '酷我MV$' + play_url,
            }
            result['list'] = [vod]
        except Exception:
            result['list'] = []
        return result

    def searchContent(self, key, quick, pg='1'):
        result = {'list': []}
        try:
            res = search_mv(key, page=pg)
            result['list'] = [to_vod(i) for i in res['list']]
            result['page'] = int(pg) if pg else 1
            result['pagecount'] = 1
            result['limit'] = len(result['list'])
            result['total'] = res.get('total') or 0
        except Exception:
            result['list'] = []
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            url = str(id)
            if not url.startswith('http'):
                url = get_mv_play_url(id)
            return {'parse': 0, 'playUrl': '', 'url': url, 'header': {
                'User-Agent': USER_AGENT, 'Referer': KUWO_HOME,
            }}
        except Exception:
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': {}}

    def _tid_to_keyword(self, tid):
        tid = str(tid)
        for c in CATEGORIES:
            if c['tid'] == tid:
                return c['keyword']
        return tid

    def destroy(self):
        pass

    def localProxy(self, param):
        return None


# ==================== 本地自测 ====================

if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sp = Spider()
    sp.init('')
    action = sys.argv[1] if len(sys.argv) > 1 else 'home'
    if action == 'home':
        print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2))
    elif action == 'list':
        tid = sys.argv[2] if len(sys.argv) > 2 else '华语MV'
        pg = sys.argv[3] if len(sys.argv) > 3 else '1'
        print(json.dumps(sp.categoryContent(tid, pg, False, {}), ensure_ascii=False, indent=2))
    elif action == 'detail':
        vid = sys.argv[2] if len(sys.argv) > 2 else ''
        print(json.dumps(sp.detailContent([vid]), ensure_ascii=False, indent=2))
    elif action == 'search':
        key = sys.argv[2] if len(sys.argv) > 2 else '周杰伦'
        print(json.dumps(sp.searchContent(key, False, '1'), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(sp.homeContent(True), ensure_ascii=False, indent=2))