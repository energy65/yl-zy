# -*- coding: utf-8 -*-
"""
migu_mv.py - 咪咕音乐 MV 本地爬虫 (DrPY type=3 蜘蛛)

以 DrPY / 影视仓 type=3 本地 python 脚本形式运行，
配置文件示例：
    {
        "key": "migu_mv PY",
        "name": "migu_mv丨PY",
        "api": "./migu_mv.py",
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

数据源：咪咕音乐 API（https://music.migu.cn/v5/#/musicLibrary）。
    分类/搜索 -> bmw/search/video/v1.0 搜索 MV（含 contentId、标题、歌手、封面、时长）
    MV 详情   -> MIGUM2.0/v1.0/content/resourceinfo.do（返回各清晰度 mp4 相对直链）
    播放直链  -> resourceinfo 的 rateFormats[].url 拼接 https://freevod.nf.migu.cn
仅用于个人学习交流。
"""
import json
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

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
MIGU_HOME = 'https://music.migu.cn/'
MIGU_SEARCH_API = 'https://app.c.nf.migu.cn/bmw/search/video/v1.0'
MIGU_RESOURCE_API = 'https://c.musicapp.migu.cn/MIGUM2.0/v1.0/content/resourceinfo.do'
MIGU_VOD_HOST = 'https://freevod.nf.migu.cn'
PAGE_SIZE = 20

# 分类：部分为艺人（搜索稳定），部分为曲风/类型关键词
CATEGORIES = [
    {'tid': '周杰伦MV', 'keyword': '周杰伦'},
    {'tid': '林俊杰MV', 'keyword': '林俊杰'},
    {'tid': '陈奕迅MV', 'keyword': '陈奕迅'},
    {'tid': '邓紫棋MV', 'keyword': '邓紫棋'},
    {'tid': '薛之谦MV', 'keyword': '薛之谦'},
    {'tid': '张学友MV', 'keyword': '张学友'},
    {'tid': '五月天MV', 'keyword': '五月天'},
    {'tid': '国语MV',   'keyword': '国语'},
    {'tid': '粤语MV',   'keyword': '粤语'},
    {'tid': '欧美MV',   'keyword': '欧美'},
    {'tid': '经典MV',   'keyword': '经典'},
    {'tid': '流行MV',   'keyword': '流行'},
    {'tid': '摇滚MV',   'keyword': '摇滚'},
    {'tid': '官方MV',   'keyword': '官方'},
    {'tid': '现场MV',   'keyword': '现场'},
    {'tid': '合唱MV',   'keyword': '合唱'},
    {'tid': '演唱会MV', 'keyword': '演唱会'},
    {'tid': '4KMV',     'keyword': '4K'},
]

# 音质顺序（从高到低），对应 rateFormats 的 formatType / format 编号
QUALITY_ORDER = [
    ('SQ', '1080P'),
    ('HQ', '高清'),
    ('PQ', '标清'),
]


# ==================== HTTP 基础 ====================

def http_get_json(url, headers=None, timeout=15):
    h = {
        'User-Agent': USER_AGENT,
        'Referer': MIGU_HOME,
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ('utf-8', 'gbk'):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, LookupError, ValueError):
            continue
    return json.loads(raw.decode('utf-8', errors='replace'))


# ==================== 工具函数 ====================

def _clean_title(s):
    """去除播放串分隔符，避免与 tvbox 协议冲突。"""
    return re.sub(r'[$#|]', '', str(s)).strip()


def _fix_pic(url):
    """归一封面地址。"""
    url = str(url or '').strip()
    if not url:
        return ''
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('http://'):
        url = 'https://' + url[len('http://'):]
    return url


def _fmt_duration(ms):
    """时长(毫秒) -> mm:ss。"""
    try:
        sec = int(ms) // 1000 if abs(int(ms)) > 1000 else int(ms)
        if sec <= 0:
            return ''
        return '%02d:%02d' % (sec // 3600 * 60 + (sec % 3600) // 60, sec % 60)
    except Exception:
        return ''


def _is_video_url(url):
    low = str(url).lower().split('?')[0]
    return low.endswith(('.mp4', '.mkv', '.flv', '.m4v'))


def _video_extra(video):
    """从搜索项 video 对象提取公共字段。"""
    user = (video.get('user') or [{}])
    nick = ''
    for u in user:
        if isinstance(u, dict) and u.get('nickName'):
            nick = u['nickName']
            break
    return nick


# ==================== 业务接口 ====================

def search_mv(keyword, page=1, size=PAGE_SIZE):
    """咪咕 MV 搜索 (bmw/search/video/v1.0)，返回 MV 列表。"""
    pn = max(1, int(page))
    params = {
        'pageNo': pn,
        'pageSize': max(1, int(size)),
        'text': keyword,
        'typeOrder': 0,
    }
    qs = '&'.join(
        f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items()
    )
    url = MIGU_SEARCH_API + '?' + qs
    try:
        data = http_get_json(url)
    except Exception:
        data = {}
    if not isinstance(data, dict) or data.get('code') not in ('000000', 0):
        data = {}
    d = data.get('data') or {}
    rows = d.get('items') or []
    items = []
    for r in rows:
        video = (r or {}).get('video') or {}
        cid = str(video.get('contentId') or '').strip()
        if not cid:
            continue
        if video.get('isValidate') not in (1, '1', None):
            continue
        artist = _video_extra(video)
        items.append({
            'content_id': cid,
            'title': _clean_title(video.get('title') or ''),
            'artist': _clean_title(artist),
            'pic': _fix_pic(video.get('showImg') or ''),
            'duration': int(video.get('duration') or 0),
            'quality': '',
        })
    return {'list': items, 'has_next': bool(d.get('hasNext')), 'total': 0}


def get_mv_play_info(content_id):
    """获取 MV mp4 直链及补充信息。

    通过 resourceinfo.do 取详情，rateFormats 内的 url 为相对路径，
    拼接 https://freevod.nf.migu.cn 即得 mp4 直链，按清晰度由高到低选取。
    返回 {'url','pic','title','artist','quality'} 或 {}。
    """
    content_id = str(content_id or '').strip()
    if not content_id:
        return {}
    params = {
        'resourceId': content_id,
        'resourceType': 'D',
        'needSimple': '01',
    }
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    url = MIGU_RESOURCE_API + '?' + qs
    try:
        data = http_get_json(url, timeout=20)
    except Exception:
        data = {}
    if not isinstance(data, dict) or data.get('code') not in ('000000', 0):
        return {}
    res = data.get('resource') or []
    if not isinstance(res, list) or not res:
        return {}
    mv = res[0] if isinstance(res[0], dict) else {}
    imgs = mv.get('imgs') or []
    pic = ''
    for im in imgs:
        if isinstance(im, dict) and im.get('img'):
            pic = im['img']
            break
    pic = _fix_pic(pic) or None
    for label, name in QUALITY_ORDER:
        found = None
        for rf in mv.get('rateFormats') or []:
            if not isinstance(rf, dict):
                continue
            if rf.get('formatType') == label:
                found = rf
                break
        if not found:
            continue
        u = str(found.get('url') or '')
        if not u:
            continue
        if u.startswith('/'):
            u = MIGU_VOD_HOST + u
        if str(u).lower().startswith('http'):
            return {
                'url': u,
                'pic': pic or '',
                'title': _clean_title(mv.get('songName') or ''),
                'artist': _clean_title(mv.get('singer') or ''),
                'quality': name,
            }
    return {}


def to_vod(item):
    content_id = item.get('content_id') or ''
    title = item.get('title') or ''
    artist = item.get('artist') or ''
    pic = item.get('pic') or ''
    vod_name = (f'{title} - {artist}' if artist else title) or content_id
    remarks = _fmt_duration(item.get('duration') or 0) or artist
    safe_title = _clean_title(title)
    safe_artist = _clean_title(artist)
    vod_id = '|'.join([content_id, safe_title, safe_artist, pic])
    return {
        'vod_id': vod_id,
        'vod_name': vod_name,
        'vod_pic': pic,
        'vod_remarks': remarks,
        'vod_content': f'歌手：{artist or "未知"}\n咪咕音乐 MV。',
        'vod_actor': artist,
    }


def parse_vod_id(vod_id):
    parts = str(vod_id).split('|', 3)
    content_id = parts[0] if len(parts) > 0 else ''
    title = parts[1] if len(parts) > 1 else ''
    artist = parts[2] if len(parts) > 2 else ''
    pic = parts[3] if len(parts) > 3 else ''
    return content_id, title, artist, pic


# ==================== 蜘蛛类 ====================

class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = '咪咕MV'
        self.host = MIGU_HOME

    def getName(self):
        return '咪咕MV'

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
        classes.append({'type_id': '新歌MV', 'type_name': '新歌MV'})
        filters['新歌MV'] = []
        result['class'] = classes
        result['filters'] = filters
        # 首页推荐：新歌 MV
        try:
            res = search_mv('新歌', page=1)
            result['list'] = [to_vod(i) for i in res['list']]
        except Exception:
            result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('新歌MV', 1, False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {'list': []}
        try:
            pg = int(pg) if pg else 1
            tid = str(tid)
            kw = tid
            if tid == '新歌MV':
                kw = '新歌'
            else:
                for c in CATEGORIES:
                    if c['tid'] == tid:
                        kw = c['keyword']
                        break
            res = search_mv(kw, page=pg)
            vods = [to_vod(i) for i in res['list']]
            result['list'] = vods
            result['page'] = pg
            result['pagecount'] = pg + 1 if res.get('has_next') else pg
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
            # 优先解析编码元数据 (contentId|title|artist|pic)
            content_id, title, artist, pic = parse_vod_id(vid) if '|' in vid else (vid, '', '', '')
            content_id = str(content_id).strip()
            if not content_id:
                return result
            info = get_mv_play_info(content_id)
            url = info.get('url') or ''
            if not url:
                return result
            pic = pic or info.get('pic') or ''
            title = title or info.get('title') or f'MV_{content_id}'
            artist = artist or info.get('artist') or ''
            vod_name = (f'{title} - {artist}' if artist else title)
            quality = info.get('quality') or ''
            vod = {
                'vod_id': content_id,
                'vod_name': vod_name,
                'vod_pic': pic,
                'vod_remarks': '咪咕MV',
                'vod_content': f'歌手：{artist or "未知"}\n清晰度：{quality or "默认"}\n咪咕音乐 MV 直链播放。',
                'vod_actor': artist,
                'vod_play_from': '咪咕MV',
                'vod_play_url': '咪咕MV$' + url,
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
            result['total'] = len(result['list'])
        except Exception:
            result['list'] = []
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            url = str(id)
            if not url.startswith('http'):
                info = get_mv_play_info(url)
                url = info.get('url') or ''
            return {'parse': 0, 'playUrl': '', 'url': url, 'header': {
                'User-Agent': USER_AGENT, 'Referer': MIGU_HOME,
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
        tid = sys.argv[2] if len(sys.argv) > 2 else '周杰伦MV'
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