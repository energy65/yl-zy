# -*- coding: utf-8 -*-
"""
qq_mv.py - QQ音乐 给MV 本地爬虫 (DrPY type=3 蜘蛛)

以 DrPY / 影视仓 type=3 本地 python 脚本形式运行，
配置文件示例：
    {
        "key": "qq_mv PY",
        "name": "qq_mv丨PY",
        "api": "./qq_mv.py",
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

数据源：QQ音乐 Web API（musicu.fcg。
    search_type=4 搜索 MV，MvInfoProServer 分类 MV 库，gosrf.Stream.MvUrlProxy 取 mp4 直链）。
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

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
QQ_HOME = 'https://y.qq.com/'
MUSICU_API = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
PAGE_SIZE = 30

# 分类：tid -> (area_id, version_id)，映射自 MvInfoProServer/GetAllocTag
LIB_CATEGORIES = [
    {'tid': '全部MV', 'keyword': '全部', 'area': 15, 'version': 7},
    {'tid': '内地MV', 'keyword': '内地', 'area': 16, 'version': 7},
    {'tid': '港台MV', 'keyword': '港台', 'area': 17, 'version': 7},
    {'tid': '欧美MV', 'keyword': '欧美', 'area': 18, 'version': 7},
    {'tid': '韩国MV', 'keyword': '韩国', 'area': 19, 'version': 7},
    {'tid': '日本MV', 'keyword': '日本', 'area': 20, 'version': 7},
    {'tid': '官方MV', 'keyword': '官方版', 'area': 15, 'version': 8},
    {'tid': '现场MV', 'keyword': '现场', 'area': 15, 'version': 9},
    {'tid': '翻唱MV', 'keyword': '翻唱', 'area': 15, 'version': 10},
    {'tid': '舞蹈MV', 'keyword': '舞蹈', 'area': 15, 'version': 11},
    {'tid': '影视MV', 'keyword': '影视', 'area': 15, 'version': 12},
    {'tid': '综艺MV', 'keyword': '综艺', 'area': 15, 'version': 13},
    {'tid': '儿歌MV', 'keyword': '儿歌', 'area': 15, 'version': 14},
]

# 搜索型分类（keyword 搜索）
SEARCH_CATEGORIES = [
    {'tid': '热搜MV', 'keyword': '热门MV'},
    {'tid': '新歌MV', 'keyword': '新歌'},
    {'tid': '经典MV', 'keyword': '经典'},
    {'tid': '流行MV', 'keyword': '流行'},
    {'tid': '摇滚MV', 'keyword': '摇滚'},
    {'tid': '民谣MV', 'keyword': '民谣'},
    {'tid': 'DJ舞曲MV', 'keyword': 'DJ舞曲'},
    {'tid': '韩流MV', 'keyword': '韩流'},
    {'tid': '动漫MV', 'keyword': '动漫'},
    {'tid': '4K高清MV', 'keyword': '4K'},
]

# 播放清晰度映射（filetype 由大到小为清晰度从高到低）
QUALITY_TAGS = {
    10: '标清',
    20: '高清',
    30: '高清',
    40: '超清',
    50: '超清',
}


def musicu(data, timeout=15):
    """调用 QQ 音乐聚合接口 musicu.fcg。"""
    h = {
        'User-Agent': USER_AGENT,
        'Referer': QQ_HOME,
        'Origin': 'https://y.qq.com',
        'Content-Type': 'application/json',
    }
    body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    req = urllib.request.Request(MUSICU_API, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    text = raw.decode('utf-8', errors='replace')
    return json.loads(text)


def _clean_title(s):
    """去除播放串分隔符，避免与 tvbox 协议冲突。"""
    return re.sub(r'[$#]', '', str(s)).strip()


def _format_count(num):
    """格式化播放量/点赞数。"""
    try:
        n = int(num)
        if n >= 100000000:
            return f'{n / 100000000:.1f}亿'
        if n >= 10000:
            return f'{n / 10000:.1f}万'
        return str(n)
    except Exception:
        return str(num)


def _fix_pic(url):
    url = str(url or '')
    if not url:
        return ''
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('http://'):
        url = 'https://' + url[len('http://'):]
    return url


# ==================== 业务接口 ====================

def search_mv(keyword, page=1, size=PAGE_SIZE):
    """QQ 搜索 MV (search_type=4)，返回有 v_id 可播的 MV 列表。"""
    pn = max(1, int(page))
    rn = max(1, int(size))
    data = {
        'comm': {'ct': '19', 'cv': '1845'},
        'music.search.SearchCgiService': {
            'method': 'DoSearchForQQMusicDesktop',
            'module': 'music.search.SearchCgiService',
            'param': {
                'query': keyword,
                'num_per_page': rn,
                'page_num': pn,
                'search_type': 4,
            },
        },
    }
    try:
        d = musicu(data)
    except Exception:
        d = {}
    svc = d.get('music.search.SearchCgiService') or {}
    sdata = svc.get('data') or {}
    meta = sdata.get('meta') or {}
    body = sdata.get('body') or {}
    rows = (body.get('mv') or {}).get('list') or []
    total = int(meta.get('sum') or 0)
    items = []
    for r in rows:
        vid = str(r.get('v_id') or r.get('vid') or '').strip()
        if not vid:
            continue
        name = r.get('mv_name') or ''
        artist = r.get('singer_name') or ''
        pic = _fix_pic(r.get('mv_pic_url') or '')
        duration = int(r.get('duration') or 0)
        play = _format_count(r.get('play_count') or 0)
        pub = (r.get('publish_date') or '').strip()
        items.append({
            'vid': vid,
            'name': name,
            'artist': artist,
            'pic': pic,
            'duration': duration,
            'play_count': play,
            'publish_date': pub,
        })
    return {'total': total, 'list': items}


def mv_lib(area=15, version=7, page=1, size=PAGE_SIZE):
    """QQ MV 库列表 (MvInfoProServer/GetAllocMvInfo)，按发布时间倒序。"""
    start = max(0, int(page) - 1) * max(1, int(size))
    data = {
        'comm': {'ct': 24},
        'mv_list': {
            'module': 'MvService.MvInfoProServer',
            'method': 'GetAllocMvInfo',
            'param': {
                'start': start,
                'size': max(1, int(size)),
                'version_id': int(version),
                'area_id': int(area),
                'order': 1,
            },
        },
    }
    try:
        d = musicu(data)
    except Exception:
        d = {}
    ml = d.get('mv_list') or {}
    rows = (ml.get('data') or {}).get('list') or []
    items = []
    for r in rows:
        vid = str(r.get('vid') or '').strip()
        if not vid:
            continue
        name = r.get('title') or ''
        singers = r.get('singers') or []
        artist = '、'.join([str(s.get('name') or '') for s in singers if s.get('name')])
        pic = _fix_pic(r.get('picurl') or '')
        duration = int(r.get('duration') or 0)
        play = _format_count(r.get('playcnt') or 0)
        pub = ''
        try:
            pub = time.strftime('%Y-%m-%d', time.localtime(int(r.get('pubdate') or 0)))
        except Exception:
            pass
        items.append({
            'vid': vid,
            'name': name,
            'artist': artist,
            'pic': pic,
            'duration': duration,
            'play_count': play,
            'publish_date': pub,
        })
    # 库接口不返回总数，返回 0 表示未知，让上层用 pg+1 允许继续翻页
    return {'total': 0, 'list': items}


def get_mv_play_url(vid, suggest=True):
    """获取 MV mp4 直链。vid 为 QQ MV 的 v_id。"""
    vid = str(vid).strip()
    if not vid:
        return ''
    data = {
        'comm': {'ct': 24, 'cv': 0},
        'getMVUrl': {
            'module': 'gosrf.Stream.MvUrlProxy',
            'method': 'GetMvUrls',
            'param': {'vids': [vid], 'from': 'h5.playsong'},
        },
    }
    try:
        d = musicu(data)
    except Exception:
        return ''
    node = ((d.get('getMVUrl') or {}).get('data') or {}).get(vid) or {}
    mp4s = node.get('mp4') or []
    # 从高清晰度往低清晰度挑第一个可用直链（VIP 锁定 code=1000 跳过）
    ordered = sorted(mp4s, key=lambda m: int(m.get('filetype') or 0) if _numeric(m.get('filetype')) else 0, reverse=True)
    for m in ordered:
        code = m.get('code')
        if code not in (0, '0'):
            continue
        urls = [u for u in (m.get('freeflow_url') or []) if u and str(u).lower().startswith('http')]
        best = next((u for u in urls if str(u).lower().startswith('https')), None)
        if best is None and urls:
            best = urls[0]
        if best:
            return str(best)
    return ''


def _numeric(x):
    try:
        int(x)
        return True
    except Exception:
        return False


def get_mv_quality_label(vid):
    """可选：返回可用的最高清晰度文案（用于详情备注）。"""
    vid = str(vid).strip()
    if not vid:
        return ''
    data = {
        'comm': {'ct': 24, 'cv': 0},
        'getMVUrl': {
            'module': 'gosrf.Stream.MvUrlProxy',
            'method': 'GetMvUrls',
            'param': {'vids': [vid], 'from': 'h5.playsong'},
        },
    }
    try:
        d = musicu(data)
    except Exception:
        return ''
    node = ((d.get('getMVUrl') or {}).get('data') or {}).get(vid) or {}
    mp4s = node.get('mp4') or []
    for m in sorted(mp4s, key=lambda m: int(m.get('filetype') or 0) if _numeric(m.get('filetype')) else 0, reverse=True):
        if m.get('code') not in (0, '0'):
            continue
        if m.get('freeflow_url'):
            return QUALITY_TAGS.get(int(m.get('filetype') or 0))
    return ''


def to_vod(item):
    vid = item.get('vid') or ''
    name = item.get('name') or ''
    artist = item.get('artist') or ''
    pic = item.get('pic') or ''
    title = (f'{name} - {artist}' if artist else name) or vid
    play = item.get('play_count') or ''
    remarks = play if play else ''
    if not remarks and item.get('publish_date'):
        remarks = item.get('publish_date')
    remarks = _clean_title(remarks)
    safe_name = _clean_title(name)
    safe_artist = _clean_title(artist)
    vod_id = '|'.join([vid, safe_name, safe_artist, pic])
    return {
        'vod_id': vod_id,
        'vod_name': title,
        'vod_pic': pic,
        'vod_remarks': remarks or 'QQ音乐MV',
        'vod_content': f'歌手：{artist or "未知"}\n播放：{play or "未知"}\npic: {pic}',
        'vod_actor': artist,
    }


def parse_vod_id(vod_id):
    parts = str(vod_id).split('|', 3)
    vid = parts[0] if len(parts) > 0 else ''
    name = parts[1] if len(parts) > 1 else ''
    artist = parts[2] if len(parts) > 2 else ''
    pic = parts[3] if len(parts) > 3 else ''
    return vid, name, artist, pic


# ==================== 蜘蛛类 ====================

class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = 'QQ音乐MV'
        self.host = QQ_HOME

    def getName(self):
        return 'QQ音乐MV'

    def init(self, extend=''):
        pass

    def isVideoFormat(self, url):
        low = str(url).lower().split('?')[0]
        return low.endswith(('.mp4', '.mkv', '.flv', '.m4v'))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter=False):
        result = {'class': [], 'filters': {}, 'list': []}
        classes = []
        filters = {}
        for c in LIB_CATEGORIES + SEARCH_CATEGORIES:
            classes.append({'type_id': c['tid'], 'type_name': c['tid']})
            filters[c['tid']] = []
        result['class'] = classes
        result['filters'] = filters
        # 首页推荐：最新 MV 库
        try:
            res = mv_lib(area=15, version=7, page=1)
            result['list'] = [to_vod(i) for i in res['list'][:12]]
        except Exception:
            result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('全部MV', 1, False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {'list': []}
        try:
            pg = int(pg) if pg else 1
            cat = None
            for c in LIB_CATEGORIES + SEARCH_CATEGORIES:
                if c['tid'] == str(tid):
                    cat = c
                    break
            if cat and 'area' in cat:
                res = mv_lib(area=cat['area'], version=cat['version'], page=pg)
            else:
                kw = (cat or {}).get('keyword') or str(tid)
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
            # 优先解析编码元数据 (vid|name|artist|pic)
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
                'vod_remarks': 'QQ音乐MV',
                'vod_content': f'歌手：{artist or "未知"}\nQQ音乐 MV 直链播放。',
                'vod_actor': artist,
                'vod_play_from': 'QQ音乐MV',
                'vod_play_url': 'QQ音乐MV$' + play_url,
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
                'User-Agent': USER_AGENT, 'Referer': QQ_HOME,
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
        tid = sys.argv[2] if len(sys.argv) > 2 else '全部MV'
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