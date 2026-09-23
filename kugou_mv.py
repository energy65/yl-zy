# -*- coding: utf-8 -*-
"""
kugou_mv.py - 酷狗音乐 MV 本地爬虫 (DrPY type=3 蜘蛛)

以 DrPY / 影视仓 type=3 本地 python 脚本形式运行，
配置文件示例：
    {
        "key": "kugou_mv PY",
        "name": "kugou_mv丨PY",
        "api": "./kugou_mv.py",
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

数据源：
    分类/热播 -> 酷狗 MV 频道静态页
                 https://www.kugou.com/mvweb/html/index_{cateId}_{page}.html
                 https://www.kugou.com/mvweb/html/mvlist.html
    搜索      -> https://mvsearch.kugou.com/mv_search
    播放直链  -> 已采集 MV hash：https://m.kugou.com/app/i/mv.php (无需签名)
                 页面短 id ：https://wwwapi.kugou.com/play/mv   (MD5 签名)
仅用于个人学习交流。
"""
import hashlib
import html
import json
import random
import re
import sys
import time
import uuid
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

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
KUGOO_HOME = 'https://www.kugou.com/'
PAGE_SIZE = 30
# wwwapi.kugou.com/play/mv 签名盐值（来自酷狗 Web 前端）
MK_SALT = 'NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt'
# 短 id -> 播放直链 请求所带固定参数
PLAY_API_DFID = '1u0Qpt0FTdFC2BtwCF2hRvQ1'

# 频道内置分类 (cid 对应 mvweb 页面 index_{cid}_{pg}.html)
CATEGORIES = [
    {'tid': '新歌推荐', 'cid': 9,   'keyword': ''},
    {'tid': '华语精选', 'cid': 13,  'keyword': ''},
    {'tid': '日韩精选', 'cid': 17,  'keyword': ''},
    {'tid': '欧美精选', 'cid': 16,  'keyword': ''},
    {'tid': '粤语MV',   'cid': 0,   'keyword': '粤语MV'},
    {'tid': '韩语MV',   'cid': 0,   'keyword': '韩语MV'},
    {'tid': '日语MV',   'cid': 0,   'keyword': '日语MV'},
    {'tid': '经典MV',   'cid': 0,   'keyword': '经典MV'},
    {'tid': '流行MV',   'cid': 0,   'keyword': '流行MV'},
    {'tid': '摇滚MV',   'cid': 0,   'keyword': '摇滚MV'},
    {'tid': '中国风MV', 'cid': 0,   'keyword': '中国风MV'},
]

# 旧接口 mv.php 的清晰度顺序（由高到低）
HASH_QUALITIES = [
    ('超清', 'rq'),
    ('高清', 'sq'),
    ('标清', 'le'),
]

# 新接口 play/mv 的清晰度顺序（由高到低，对应 info.h264 的 *_hash 字段）
VID_QUALITIES = ['fhd', 'hd', 'qhd', 'sd', 'ld']


# ==================== HTTP 基础 ====================

def make_req_id():
    ts = format(int(time.time() * 1000), 'x').rjust(12, '0')[-12:]
    rand_hex = ''.join(random.choice('0123456789abcdef') for _ in range(16))
    return f'{ts}-{rand_hex}'


def http_get_bytes(url, headers=None, timeout=15):
    h = {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Referer': KUGOO_HOME,
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url, headers=None, timeout=15):
    raw = http_get_bytes(url, headers=headers, timeout=timeout)
    try:
        return json.loads(raw.decode('utf-8', errors='replace'))
    except Exception:
        return json.loads(raw.decode('gbk', errors='replace'))


def http_get_text(url, headers=None, timeout=15):
    raw = http_get_bytes(url, headers=headers, timeout=timeout)
    for enc in ('utf-8', 'gbk'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def kugou_signature(params, post_data=None):
    """模拟 wwwapi.kugou.com/play/mv 的 signature 计算。"""
    kv = [f'{k}={params[k]}' for k in sorted(params.keys())]
    if post_data:
        kv.append(json.dumps(post_data, separators=(',', ':')))
    sign = MK_SALT + ''.join(kv) + MK_SALT
    return hashlib.md5(sign.encode('utf-8')).hexdigest()


def _clean_title(s):
    """去除播放串分隔符及换行，避免与 tvbox 协议冲突。"""
    return re.sub(r'([$#|]|\r|\n)', '', str(s)).strip()


def _strip_em(s):
    """去掉酷狗搜索返回里的 <em>...</em> 高亮标签。"""
    return re.sub(r'</?em>', '', str(s))


def _fix_pic(pic):
    """补齐封面 URL：相对路径/占位尺寸做归一。"""
    pic = str(pic or '').strip()
    if not pic.startswith('http'):
        return ''
    if '{size}' in pic:
        pic = pic.replace('{size}', '480')
    return pic


# ==================== 数据接口 ====================

def search_mv(keyword, page=1, size=PAGE_SIZE):
    """酷狗 MV 搜索 (mvsearch.kugou.com/mv_search)，返回 MV 列表。"""
    pn = max(1, int(page))
    rn = max(1, int(size))
    params = {
        'keyword': keyword, 'page': pn, 'pagesize': rn,
        'userid': -1, 'clientver': '', 'platform': 'WebFilter',
        'tag': 'em', 'filter': 1, 'iscorrection': 1, 'privilege_filter': 0,
    }
    qs = '&'.join(
        f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items()
    )
    url = 'https://mvsearch.kugou.com/mv_search?' + qs
    try:
        data = http_get_json(url)
    except Exception:
        data = {}
    if not isinstance(data, dict) or data.get('status') != 1:
        data = {}
    d = data.get('data') or {}
    total = int(d.get('total') or 0)
    rows = d.get('lists') or []
    items = []
    for r in rows:
        mvhash = str(r.get('MvHash') or '').strip()
        if not mvhash:
            continue
        name = _clean_title(html.unescape(_strip_em(r.get('MvName') or '')))
        singer = _clean_title(r.get('SingerName') or '')
        items.append({
            'vid': '',
            'hash': mvhash,
            'name': name,
            'singer': singer,
            'pic': _fix_pic(r.get('Pic') or ''),
            'duration': int(r.get('Duration') or 0),
        })
    return {'total': total, 'list': items}


def _parse_mv_page_items(text):
    """解析 mvweb 列表页，返回 {vid, name, singer, pic} 列表。"""
    pattern = re.compile(
        r'<a[^>]+href="https://www\.kugou\.com/mv/([0-9a-z]+)/"'
        r'[^>]*title="([^"]*)"'
        r'.*?_src="([^"]*)"',
        re.S,
    )
    items = []
    for m in pattern.finditer(text):
        vid, raw_title, pic_src = m.group(1), m.group(2), m.group(3)
        title = html.unescape(raw_title).strip()
        parts = re.split(r'\s+-\s+', title, maxsplit=1)
        if len(parts) > 1:
            singer = _clean_title(parts[0])
            name = _clean_title(parts[1])
        else:
            singer = ''
            name = _clean_title(title)
        items.append({
            'vid': vid.lower(),
            'hash': '',
            'name': name,
            'singer': singer,
            'pic': _fix_pic(html.unescape(pic_src)),
            'duration': 0,
        })
    return items


def category_mv(cid, page=1):
    """内置分类页：https://www.kugou.com/mvweb/html/index_{cid}_{page}.html"""
    pn = max(1, int(page))
    url = f'https://www.kugou.com/mvweb/html/index_{cid}_{pn}.html'
    try:
        text = http_get_text(url)
    except Exception:
        text = ''
    items = _parse_mv_page_items(text)
    pagecount = 1
    try:
        other = [int(x) for x in re.findall(rf'index_{cid}_(\d+)\.html', text)]
        if other:
            pagecount = max(other)
    except Exception:
        pass
    return {'total': len(items) * pagecount, 'list': items, 'pagecount': pagecount}


def hot_mv():
    """MV热播排行：https://www.kugou.com/mvweb/html/mvlist.html"""
    url = 'https://www.kugou.com/mvweb/html/mvlist.html'
    try:
        text = http_get_text(url)
    except Exception:
        text = ''
    items = _parse_mv_page_items(text)
    return {'total': len(items), 'list': items, 'pagecount': 1}


def get_mv_play_info(vid='', mvhash=''):
    """获取 MV 播放直链及补充信息。

    优先使用 MV hash 走旧接口 m.kugou.com（无需签名），
    否则用短 id 走新接口 wwwapi.kugou.com/play/mv（MD5 签名）。
    返回 {'url','pic','name','singer','quality'} 或 {}。
    """
    vid = str(vid or '').strip().lower()
    mvhash = str(mvhash or '').strip().upper()
    if mvhash:
        return _play_by_hash(mvhash)
    if vid:
        return _play_by_vid(vid)
    return {}


def _play_by_hash(mvhash):
    url = 'https://m.kugou.com/app/i/mv.php?cmd=100&hash=' + mvhash + '&ismp3=1&ext=mp4'
    try:
        data = http_get_json(url)
    except Exception:
        return {}
    if not isinstance(data, dict) or data.get('status') != 1:
        return {}
    mv = data.get('mvdata') or {}
    for label, q in HASH_QUALITIES:
        entry = mv.get(q) or {}
        if not entry:
            continue
        du = entry.get('downurl') or ''
        if not (isinstance(du, str) and str(du).lower().startswith('http')):
            backup = entry.get('backupdownurl') or []
            du = backup[0] if backup else ''
        if du:
            return {
                'url': str(du),
                'pic': _fix_pic(data.get('mvicon') or ''),
                'name': _clean_title(data.get('songname') or ''),
                'singer': _clean_title(data.get('singer') or ''),
                'quality': label,
            }
    return {}


def _play_by_vid(vid):
    muuid = uuid.uuid4().hex
    params = {
        'srcappid': '2919',
        'clientver': '1000',
        'clienttime': str(int(time.time() * 1000)),
        'mid': muuid,
        'uuid': muuid,
        'dfid': PLAY_API_DFID,
        'appid': '1014',
        'id': vid,
    }
    params['signature'] = kugou_signature(params)
    qs = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items())
    url = 'https://wwwapi.kugou.com/play/mv?' + qs
    try:
        data = http_get_json(url)
    except Exception:
        return {}
    if not isinstance(data, dict) or data.get('status') != 1:
        return {}
    d = data.get('data') or {}
    play = d.get('play') or {}
    h264 = (d.get('info') or {}).get('h264') or {}
    base = (d.get('info') or {}).get('base') or {}
    for qk in VID_QUALITIES:
        h = str(h264.get(qk + '_hash') or '').upper()
        if not h:
            continue
        entry = play.get(h)
        if not entry:
            entry = play.get(h.lower())
        if not entry:
            continue
        du = entry.get('downurl') or ''
        if not (isinstance(du, str) and str(du).lower().startswith('http')):
            backup = entry.get('backupdownurl') or []
            du = backup[0] if backup else ''
        if du:
            pic = base.get('hdpic') or base.get('thumb') or ''
            return {
                'url': str(du),
                'pic': _fix_pic(pic),
                'name': _clean_title(base.get('mv_name') or ''),
                'singer': _clean_title(base.get('singer') or ''),
                'quality': qk,
            }
    return {}


def _fmt_duration(sec):
    try:
        sec = int(sec)
        if sec <= 0:
            return ''
        return '%02d:%02d' % (sec // 60, sec % 60)
    except Exception:
        return ''


def to_vod(item):
    vid = str(item.get('vid') or '').strip()
    mvhash = str(item.get('hash') or '').strip()
    name = str(item.get('name') or '')
    singer = str(item.get('singer') or '')
    pic = str(item.get('pic') or '')
    title = (f'{singer} - {name}' if singer else name) or (vid or mvhash)
    remarks = _fmt_duration(item.get('duration') or 0) or singer
    vod_id = '|'.join([vid, mvhash, name, singer, pic])
    return {
        'vod_id': vod_id,
        'vod_name': title,
        'vod_pic': pic,
        'vod_remarks': remarks,
        'vod_content': f'歌手：{singer or "未知"}\npic: {pic}',
        'vod_actor': singer,
    }


def parse_vod_id(vod_id):
    parts = str(vod_id).split('|', 4)
    pad = ['', '', '', '', ''] + parts
    vid, mvhash, name, singer, pic = pad[-5:]
    return vid, mvhash, name, singer, pic


# ==================== 蜘蛛类 ====================

class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = '酷狗MV'
        self.host = KUGOO_HOME

    def getName(self):
        return '酷狗MV'

    def init(self, extend=''):
        pass

    def isVideoFormat(self, url):
        return self.isVideoFormatHelper(url)

    @staticmethod
    def isVideoFormatHelper(url):
        low = str(url).lower()
        if 'kugou.com' in low:
            return True
        for ext in ('.mp4', '.mkv', '.flv', '.m4v'):
            if low.split('?')[0].endswith(ext):
                return True
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter=False):
        result = {'class': [], 'filters': {}, 'list': []}
        classes = []
        filters = {}
        for c in CATEGORIES:
            classes.append({'type_id': c['tid'], 'type_name': c['tid']})
            filters[c['tid']] = []
        classes.append({'type_id': '热播MV', 'type_name': '热播MV'})
        filters['热播MV'] = []
        classes.append({'type_id': '热搜MV', 'type_name': '热搜MV'})
        filters['热搜MV'] = []
        result['class'] = classes
        result['filters'] = filters
        try:
            res = hot_mv()
            result['list'] = [to_vod(i) for i in res['list']]
        except Exception:
            result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('热播MV', 1, False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {'list': []}
        try:
            pg = int(pg) if pg else 1
            tid = str(tid)
            if tid == '热播MV':
                res = hot_mv()
            elif tid == '热搜MV':
                res = search_mv('热门MV', page=pg)
            else:
                cid = 0
                keyword = ''
                for c in CATEGORIES:
                    if c['tid'] == tid:
                        cid = c['cid']
                        keyword = c['keyword']
                        break
                if cid:
                    res = category_mv(cid, page=pg)
                else:
                    res = search_mv(keyword or tid, page=pg)
            result['list'] = [to_vod(i) for i in res['list']]
            result['page'] = pg
            pagecount = res.get('pagecount') or 0
            if pagecount:
                result['pagecount'] = pagecount
            else:
                total = res.get('total') or 0
                result['pagecount'] = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE) if total else pg + 1
            result['limit'] = PAGE_SIZE
            result['total'] = res.get('total') or 0
        except Exception:
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
            mv_id, mvhash, name, singer, pic = parse_vod_id(vid)
            info = get_mv_play_info(mv_id, mvhash)
            url = info.get('url') or ''
            if not url:
                return result
            pic = pic or info.get('pic') or ''
            name = name or info.get('name') or mv_id
            singer = singer or info.get('singer') or ''
            title = (f'{singer} - {name}' if singer else name) or mv_id
            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '酷狗MV',
                'vod_content': f'歌手：{singer or "未知"}\n清晰度：{info.get("quality") or "默认"}\n酷狗音乐 MV 直链播放。',
                'vod_actor': singer,
                'vod_play_from': '酷狗MV',
                'vod_play_url': '酷狗MV$' + url,
            }
            result['list'] = [vod]
        except Exception:
            result['list'] = []
        return result

    def searchContent(self, key, quick, pg='1'):
        result = {'list': []}
        try:
            res = search_mv(key, page=int(pg) if pg else 1)
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
                mv_id, mvhash = parse_vod_id(url)[:2]
                info = get_mv_play_info(mv_id, mvhash)
                url = info.get('url') or ''
            return {'parse': 0, 'playUrl': '', 'url': url, 'header': {
                'User-Agent': USER_AGENT, 'Referer': KUGOO_HOME,
            }}
        except Exception:
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': {}}

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
        tid = sys.argv[2] if len(sys.argv) > 2 else '新歌推荐'
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