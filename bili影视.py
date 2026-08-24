# coding=utf-8
# 哔哩哔哩影视 TVBox Python 爬虫 (基于 base.spider 标准)
# 站点: https://www.bilibili.com/
# 分类: 电影 / 电视剧 / 综艺 / 动漫(番剧+国创), 其余分类已过滤
# 数据: B站官方 PGC 剧集接口 + 官方搜索接口
# 播放: 与 李子柒.py 一致, 返回B站页面地址(jx=1/parse=1)交由TVBox解析器
#       解析播放, 并附带 183933.xyz 弹幕; 需在TVBox配置可用的解析或嗅探
# 进阶: 在源码 extend 中填入 B 站 Cookie SESSDATA 可解锁大会员清晰度/完整播放
#       例: "SESSDATA=xxxxxxxx"
# 关注微信公众号“源力软件汇”, Q群1054592152, 伴随更多优质资源尽在源力。
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

PROMO = '\n\n关注微信公众号“源力软件汇”，Q群1054592152，伴随更多优质资源尽在源力。'

# 仅保留 影视 相关分类, 其余分类全部过滤
CATES = [
    {'type_id': 'movie', 'type_name': '电影'},
    {'type_id': 'tv', 'type_name': '电视剧'},
    {'type_id': 'show', 'type_name': '综艺'},
    {'type_id': 'anime', 'type_name': '动漫'},
]
TYPE_MAP = {'movie': [2], 'tv': [5], 'show': [7], 'anime': [1, 4]}

ORDERS = [
    {'n': '最近更新', 'v': '0'},
    {'n': '播放数量', 'v': '2'},
    {'n': '追剧人数', 'v': '3'},
    {'n': '最高评分', 'v': '4'},
    {'n': '开播时间', 'v': '5'},
    {'n': '上映时间', 'v': '6'},
]
# 条件接口异常时的兜底筛选(与线上数据一致的常用项)
FALLBACK_CONDITIONS = {
    1: [('season_version', '类型', [('-1', '全部'), ('1', '正片'), ('2', '电影'), ('3', '其他')]),
        ('spoken_language_type', '配音', [('-1', '全部'), ('1', '原声'), ('2', '中文配音')]),
        ('area', '地区', [('-1', '全部'), ('1', '中国大陆'), ('2', '日本'), ('-6,7', '中国港台')]),
        ('is_finish', '状态', [('-1', '全部'), ('1', '完结'), ('0', '连载')]),
        ('year', '年份', [('-1', '全部'), ('[2026,2027)', '2026'), ('[2025,2026)', '2025'),
                          ('[2024,2025)', '2024'), ('[2020,2024)', '2020-2023'),
                          ('[2010,2020)', '2010-2019'), ('[2000,2010)', '2000-2009'),
                          ('[,2000)', '90年代及以前')]),
        ('style_id', '风格', [('-1', '全部'), ('10010', '原创'), ('10011', '漫画改编'), ('10012', '小说改编'),
                              ('10013', '游戏改编'), ('10014', '特摄'), ('10015', '布袋戏'),
                              ('10016', '热血'), ('10017', '穿越'), ('10018', '奇幻'), ('10019', '剧情'),
                              ('10020', '搞笑'), ('10021', '恋爱'), ('10022', '日常'), ('10023', '科幻'),
                              ('10024', '悬疑'), ('10025', '神魔'), ('10026', '竞技'), ('10027', '治愈')]),
        ('season_status', '付费', [('-1', '全部'), ('1', '免费'), ('2,6', '付费'), ('4,6', '大会员')])],
    2: [('area', '地区', [('-1', '全部'), ('1', '中国大陆'), ('6,7', '中国港台'), ('3', '美国'),
                          ('2', '日本'), ('8', '韩国'), ('9', '法国'), ('4', '英国'), ('15', '德国'),
                          ('10', '泰国'), ('35', '意大利'), ('13', '西班牙')]),
        ('release_date', '年份', [('-1', '全部'), ('[2026-01-01 00:00:00,2027-01-01 00:00:00)', '2026'),
                                  ('[2025-01-01 00:00:00,2026-01-01 00:00:00)', '2025'),
                                  ('[2024-01-01 00:00:00,2025-01-01 00:00:00)', '2024'),
                                  ('[2020-01-01 00:00:00,2024-01-01 00:00:00)', '2020-2023'),
                                  ('[2010-01-01 00:00:00,2020-01-01 00:00:00)', '2010-2019'),
                                  ('[2000-01-01 00:00:00,2010-01-01 00:00:00)', '2000-2009'),
                                  ('[,2000-01-01 00:00:00)', '更早')]),
        ('style_id', '风格', [('-1', '全部'), ('10104', '爱情'), ('10050', '剧情'), ('10051', '喜剧'),
                              ('10052', '动作'), ('10053', '犯罪'), ('10054', '恐怖'), ('10055', '战争'),
                              ('10056', '历史'), ('10057', '传记'), ('10058', '灾难'), ('10059', '歌舞'),
                              ('10060', '情色'), ('10061', '家庭'), ('10062', '武侠'), ('10063', '西部'),
                              ('10064', '惊悚'), ('10018', '奇幻'), ('10032', '冒险'), ('10033', '科幻')]),
        ('season_status', '付费', [('-1', '全部'), ('1', '免费'), ('2,6', '付费'), ('4,6', '大会员')])],
    4: [('area', '地区', [('-1', '全部'), ('1', '中国大陆'), ('6,7', '中国港台'), ('2', '日本')]),
        ('is_finish', '状态', [('-1', '全部'), ('1', '完结'), ('0', '连载')]),
        ('year', '年份', [('-1', '全部'), ('[2026,2027)', '2026'), ('[2025,2026)', '2025'),
                          ('[2024,2025)', '2024'), ('[2020,2024)', '2020-2023'),
                          ('[2010,2020)', '2010-2019'), ('[2000,2010)', '2000-2009'),
                          ('[,2000)', '90年代及以前')]),
        ('style_id', '风格', [('-1', '全部'), ('10010', '原创'), ('10011', '漫画改编'), ('10012', '小说改编'),
                              ('10016', '热血'), ('10017', '穿越'), ('10018', '奇幻'), ('10023', '科幻'),
                              ('10024', '悬疑'), ('10030', '古风'), ('10031', '都市')]),
        ('season_status', '付费', [('-1', '全部'), ('1', '免费'), ('2,6', '付费'), ('4,6', '大会员')])],
    5: [('area', '地区', [('-1', '全部'), ('1', '中国大陆'), ('6,7', '中国港台'), ('8', '韩国'),
                          ('3', '美国'), ('2', '日本'), ('4', '英国')]),
        ('release_date', '年份', [('-1', '全部'), ('[2026-01-01 00:00:00,2027-01-01 00:00:00)', '2026'),
                                  ('[2025-01-01 00:00:00,2026-01-01 00:00:00)', '2025'),
                                  ('[2024-01-01 00:00:00,2025-01-01 00:00:00)', '2024'),
                                  ('[2020-01-01 00:00:00,2024-01-01 00:00:00)', '2020-2023'),
                                  ('[2010-01-01 00:00:00,2020-01-01 00:00:00)', '2010-2019'),
                                  ('[2000-01-01 00:00:00,2010-01-01 00:00:00)', '2000-2009'),
                                  ('[,2000-01-01 00:00:00)', '更早')]),
        ('style_id', '风格', [('-1', '全部'), ('10010', '宫廷'), ('10011', '谍战'), ('10012', '悬疑'),
                              ('10013', '偶像'), ('10014', '都市'), ('10015', '家庭'), ('10016', '军旅'),
                              ('10017', '武侠'), ('10018', '奇幻'), ('10019', '年代')]),
        ('season_status', '付费', [('-1', '全部'), ('1', '免费'), ('2,6', '付费'), ('4,6', '大会员')])],
    7: [('style_id', '风格', [('-1', '全部'), ('10010', '真人秀'), ('10011', '脱口秀'), ('10012', '音乐'),
                              ('10013', '访谈'), ('10014', '美食'), ('10015', '旅游'), ('10016', '职场'),
                              ('10017', '亲子'), ('10018', '文化'), ('10019', '萌宠')]),
        ('season_status', '付费', [('-1', '全部'), ('1', '免费'), ('2,6', '付费')])],
}


def _strip_tags(s):
    if not s:
        return ''
    return re.sub(r'<[^>]+>', '', str(s)).replace('&amp;', '&').replace('&quot;', '"')


def _pic(u):
    u = u or ''
    if u.startswith('//'):
        return 'https:' + u
    return u


def _names(v):
    # 兼容字符串("喜剧/动作")与对象数组([{name:xx}])两种返回
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                out.append(str(x.get('name') or ''))
            else:
                out.append(str(x))
        return '/'.join(x for x in out if x)
    return ''


class Spider(_BaseSpider):
    def __init__(self):
        super(Spider, self).__init__()
        self.name = '哔哩影视'
        self.session = None
        self._cookie_ok = False
        self._conditions = None

    # ---------- 基础 ----------
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
        extend = str(self.extend or '').strip()
        if extend.startswith('{'):
            try:
                ext = json.loads(extend)
                extend = (ext.get('SESSDATA') or ext.get('sessdata') or '')
            except Exception:
                extend = ''
        else:
            m = re.search(r'SESSDATA=([^;\"\']+)', extend)
            extend = m.group(1) if m else ''
        if extend:
            self._set_cookie('SESSDATA', extend)
        return None

    def _set_cookie(self, k, v):
        try:
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
        # 获取 buvid3/buvid4 风控Cookie, 保证搜索可用
        if self._cookie_ok or not self.session:
            return
        try:
            self.session.get(WEB + '/', timeout=10)
        except Exception:
            pass
        try:
            d = self.session.get(API + '/x/frontend/finger/spi', timeout=10).json() or {}
            d = d.get('data') or {}
            if d.get('b_3'):
                self._set_cookie('buvid3', d['b_3'])
            if d.get('b_4'):
                self._set_cookie('buvid4', d['b_4'])
        except Exception:
            pass
        self._cookie_ok = True

    def _get_json(self, path, params=None):
        self._ensure_cookies()
        try:
            r = self.session.get(API + path, params=params, timeout=15)
            return r.json()
        except Exception:
            pass
        try:
            import urllib.request
            q = '&'.join('%s=%s' % (k, v) for k, v in (params or {}).items())
            req = urllib.request.Request(API + path + ('?' + q if q else ''), headers=dict(HEADERS))
            ctx_ok = True
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            except Exception:
                ctx_ok = False
            with urllib.request.urlopen(req, timeout=15, context=ctx if ctx_ok else None) as resp:
                return json.loads(resp.read().decode('utf-8', 'ignore'))
        except Exception:
            return {}

    # ---------- 分类筛选 ----------
    def _load_conditions(self):
        if self._conditions is not None:
            return self._conditions
        out = {}
        for st in (1, 2, 4, 5, 7):
            d = self._get_json('/pgc/season/index/condition', {'season_type': st, 'type': 1})
            data = d.get('data') if isinstance(d.get('data'), dict) else {}
            flt = []
            for f in (data.get('filter') or []):
                vals = [(str(v.get('keyword')), v.get('name')) for v in (f.get('values') or [])
                        if v.get('keyword') is not None and v.get('name')]
                if vals:
                    flt.append((f.get('field'), f.get('name'), vals))
            out[st] = flt or FALLBACK_CONDITIONS.get(st, [])
        self._conditions = out
        return out

    @staticmethod
    def _build_filters(conds):
        filters = []
        for field, fname, vals in conds:
            if len(vals) <= 1:
                continue
            options = [{'n': n, 'v': v} for v, n in vals[:40]]
            filters.append({'key': field, 'name': fname, 'value': options})
        return filters

    # ---------- TVBox 标准方法 ----------
    def homeContent(self, filter):
        result = {'class': CATES, 'filters': {}}
        try:
            conds = self._load_conditions()
            for cid, sts in TYPE_MAP.items():
                flist = []
                if len(sts) > 1:
                    for st in sts:
                        for f in self._build_filters(conds.get(st, [])):
                            f['key'] = '%d_%s' % (st, f['key'])
                            flist.append(f)
                    flist.insert(0, {'key': 'ban', 'name': '板块',
                                     'value': [{'n': '全部', 'v': 'all'}, {'n': '番剧', 'v': '1'},
                                               {'n': '国创', 'v': '4'}]})
                else:
                    flist = self._build_filters(conds.get(sts[0], []))
                flist.append({'key': 'order', 'name': '排序', 'value': ORDERS})
                result['filters'][cid] = flist
        except Exception:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos, seen = [], set()
        try:
            for st in (2, 5, 7, 1, 4):
                d = self._get_json('/pgc/season/index/result',
                                   {'type': 1, 'season_type': st, 'page': 1,
                                    'pagesize': 6, 'order': 2, 'sort': 0})
                data = d.get('data') if isinstance(d.get('data'), dict) else {}
                for it in (data.get('list') or []):
                    sid = it.get('season_id')
                    if not sid or sid in seen:
                        continue
                    seen.add(sid)
                    videos.append({
                        'vod_id': 'ss%s' % sid,
                        'vod_name': _strip_tags(it.get('title')),
                        'vod_pic': _pic(it.get('cover')),
                        'vod_remarks': it.get('index_show') or ((it.get('score') or '') + '分' if it.get('score') else ''),
                    })
        except Exception:
            pass
        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        pg = int(pg) if pg else 1
        if pg < 1:
            pg = 1
        sts = TYPE_MAP.get(cid, [2])
        if not isinstance(ext, dict):
            try:
                ext = json.loads(ext or '{}')
            except Exception:
                ext = {}
        order = str(ext.get('order', '0'))
        ban = str(ext.get('ban', 'all'))
        if cid == 'anime' and ban in ('1', '4'):
            sts = [int(ban)]
        videos, total = [], 0
        try:
            for st in sts:
                params = {'type': 1, 'season_type': st, 'page': pg,
                          'pagesize': 24, 'order': order, 'sort': 0}
                prefix = '%d_' % st if cid == 'anime' else ''
                for k, v in (ext or {}).items():
                    key = k[len(prefix):] if prefix and k.startswith(prefix) else k
                    if key in ('order', 'sort', 'ban') or v in ('-1', '', None):
                        continue
                    params[key] = v
                d = self._get_json('/pgc/season/index/result', params)
                data = d.get('data') if isinstance(d.get('data'), dict) else {}
                total += int(data.get('total') or 0)
                for it in (data.get('list') or []):
                    sid = it.get('season_id')
                    if not sid:
                        continue
                    remarks = []
                    if it.get('badge'):
                        remarks.append(it['badge'])
                    if it.get('score'):
                        remarks.append(it['score'] + '分')
                    elif it.get('order'):
                        remarks.append(str(it['order']))
                    if it.get('index_show'):
                        remarks.append(it['index_show'])
                    videos.append({
                        'vod_id': 'ss%s' % sid,
                        'vod_name': _strip_tags(it.get('title')),
                        'vod_pic': _pic(it.get('cover')),
                        'vod_remarks': ' | '.join(remarks),
                    })
        except Exception:
            pass
        pagecount = max(1, (total + 23) // 24) if total else pg + 1
        result.update({'list': videos, 'page': pg, 'pagecount': pagecount,
                       'limit': len(videos), 'total': total or 9999})
        return result

    def detailContent(self, ids):
        did = str(ids[0])
        if did.startswith('bv'):
            return self._detail_video(did[2:])
        result = {}
        try:
            d = self._get_json('/pgc/view/web/season', {'season_id': did[2:]})
            res = d.get('result') if isinstance(d.get('result'), dict) else {}
            if not res:
                raise ValueError('empty')
            title = res.get('title', '')
            cover = res.get('cover', '')
            areas = _names(res.get('areas'))
            styles = _names(res.get('styles'))
            actors = _strip_tags(res.get('actors') or '')[:220]
            staff = _strip_tags(res.get('staff') or '')
            director = ''
            if staff:
                director = re.split(r'[\n]', staff)[0].replace('导演：', '').replace('导演:', '')[:60]
            cv = _strip_tags(res.get('cv') or '')[:220]
            if cv and not actors:
                actors = cv
            content = _strip_tags(res.get('evaluate') or '')
            alias = res.get('alias') or ''
            rating = ((res.get('rating') or {}).get('score')) or ''
            stat = res.get('stat') or {}
            pub = res.get('publish') or {}
            year_m = re.search(r'(\d{4})', str(pub.get('pub_time') or pub.get('pub_date') or ''))
            year = year_m.group(1) if year_m else ''

            info = []
            if rating:
                info.append('评分：%s' % rating)
            if areas:
                info.append('地区：%s' % areas)
            if styles:
                info.append('风格：%s' % styles)
            if year:
                info.append('年份：%s' % year)
            new_ep = res.get('new_ep') or {}
            if new_ep.get('desc'):
                info.append('进度：%s' % new_ep['desc'])
            if alias:
                info.append('别名：%s' % alias)

            detail = '　'.join(x for x in info if x) + '\n'
            if content:
                detail += '简介：' + content + '\n'
            if staff:
                detail += '制作：' + staff[:180] + '\n'
            detail += PROMO

            eps = res.get('episodes') or []
            play_urls = []
            for i, e in enumerate(eps):
                t = _strip_tags(e.get('title') or '').strip()
                lt = _strip_tags(e.get('long_title') or '').strip()
                label = lt
                if t.isdigit() and lt:
                    label = '%s %s' % (t, lt)
                elif lt and t and t != lt:
                    label = '%s %s' % (t, lt)
                label = label or ('第%02d集' % (i + 1))
                badge = e.get('badge') or ''
                if badge:
                    label += ' [%s]' % badge
                label = label.replace('$', '').replace('#', '')
                play_urls.append('%s$%s_%s' % (label, e.get('id'), e.get('cid')))
            sections = res.get('section') or []
            sec_urls = []
            for sec in sections:
                if str(sec.get('title') or '') in ('正片', ''):
                    continue
                for e in (sec.get('episodes') or []):
                    label = _strip_tags(e.get('title') or e.get('long_title') or '花絮')
                    label = label.replace('$', '').replace('#', '')
                    sec_urls.append('%s$%s_%s' % (label, e.get('id'), e.get('cid')))

            play_from = '正版高清[源力软件汇]'
            play_url = '#'.join(play_urls)
            if sec_urls:
                play_from += '$$$花絮PV[源力软件汇]'
                play_url += '$$$' + '#'.join(sec_urls)

            result['list'] = [{
                'vod_id': did,
                'vod_name': title,
                'vod_pic': _pic(cover),
                'vod_year': year,
                'vod_area': areas,
                'vod_remarks': new_ep.get('desc') or ('共%d集' % len(eps)),
                'vod_actor': actors,
                'vod_director': director,
                'vod_content': detail,
                'vod_play_from': play_from,
                'vod_play_url': play_url,
            }]
        except Exception:
            result['list'] = [{
                'vod_id': did, 'vod_name': '', 'vod_pic': '',
                'vod_content': '获取失败，请重试。' + PROMO.strip(),
                'vod_play_from': '正版高清[源力软件汇]', 'vod_play_url': '',
            }]
        return result

    def _detail_video(self, bvid):
        result = {}
        try:
            d = self._get_json('/x/web-interface/view', {'bvid': bvid})
            data = d.get('data') or {}
            pages = data.get('pages') or [{'cid': data.get('cid')}]
            play_urls = []
            for p in pages:
                part = p.get('part') or p.get('title') or '正片'
                play_urls.append('%s$%s_%s' % (_strip_tags(part).replace('$', '').replace('#', ''),
                                               bvid, p.get('cid')))
            desc = _strip_tags(data.get('desc') or '')
            owner = (data.get('owner') or {}).get('name', '')
            result['list'] = [{
                'vod_id': 'bv' + bvid,
                'vod_name': data.get('title', ''),
                'vod_pic': _pic(data.get('pic')),
                'vod_actor': owner,
                'vod_director': owner,
                'vod_area': (data.get('tname') or ''),
                'vod_content': (desc + PROMO)[:1500],
                'vod_play_from': 'B站视频[源力软件汇]',
                'vod_play_url': '#'.join(play_urls),
            }]
        except Exception:
            result['list'] = [{
                'vod_id': 'bv' + bvid, 'vod_name': '', 'vod_pic': '',
                'vod_content': '获取失败，请重试。' + PROMO.strip(),
                'vod_play_from': 'B站视频[源力软件汇]', 'vod_play_url': '',
            }]
        return result

    def _video_page(self, bvid, cid):
        # 多P视频按cid定位页码p(与李子柒.py的 ?p=N 格式一致)
        try:
            d = self._get_json('/x/web-interface/view', {'bvid': bvid})
            pages = ((d.get('data') or {}).get('pages')) or []
            for i, p in enumerate(pages):
                if str(p.get('cid')) == str(cid):
                    return '%s/video/%s?p=%d' % (WEB, bvid, i + 1)
        except Exception:
            pass
        if cid and cid.isdigit():
            try:
                d = self._get_json('/x/player/pagelist', {'bvid': bvid})
                for i, p in enumerate(d.get('data') or []):
                    if str(p.get('cid')) == str(cid):
                        return '%s/video/%s?p=%d' % (WEB, bvid, i + 1)
            except Exception:
                pass
        return '%s/video/%s' % (WEB, bvid)

    def playerContent(self, flag, id, vipFlags):
        # 与 李子柒.py 相同的播放方式: 交由TVBox解析器解析B站页面播放
        id = str(id)
        header = dict(PLAY_HEADER)
        if '_' not in id:
            page = id
        else:
            left, cid = id.rsplit('_', 1)
            if left.startswith('BV'):
                page = self._video_page(left, cid)
            else:
                page = '%s/bangumi/play/ep%s' % (WEB, left)
        conf = {'jx': 1, 'parse': 1, 'playUrl': '', 'url': page, 'header': header}
        try:
            conf['danmaku'] = 'https://183933.xyz/dm/dm.php?url=' + page
        except Exception:
            pass
        return conf

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    # ---------- 搜索 ----------
    def searchContentPage(self, key, quick, page):
        result = {'list': [], 'page': int(page or 1)}
        page = int(page or 1)
        videos = []
        seen = set()
        try:
            for st in ('media_bangumi', 'media_ft'):
                d = self._get_json('/x/web-interface/search/type',
                                   {'search_type': st, 'keyword': key, 'page': page})
                data = d.get('data') if isinstance(d.get('data'), dict) else {}
                for it in (data.get('result') or []):
                    sid = it.get('season_id')
                    stype = it.get('season_type')
                    if not sid or sid in seen or stype not in (1, 2, 4, 5, 7):
                        continue
                    seen.add(sid)
                    badges = it.get('badges') or []
                    badge = badges[0].get('text') if badges and isinstance(badges[0], dict) else ''
                    idx = it.get('index') or ''
                    if not idx:
                        ep = it.get('eps')
                        idx = ('全%s集' % ep) if isinstance(ep, int) and ep > 0 else ''
                    remarks = ' '.join(x for x in (badge, idx) if x)
                    videos.append({
                        'vod_id': 'ss%s' % sid,
                        'vod_name': _strip_tags(it.get('title')),
                        'vod_pic': _pic(it.get('cover')),
                        'vod_remarks': remarks,
                    })
            # 普通投稿视频兜底
            if not videos:
                d = self._get_json('/x/web-interface/search/type',
                                   {'search_type': 'video', 'keyword': key, 'page': page})
                data = d.get('data') if isinstance(d.get('data'), dict) else {}
                for it in (data.get('result') or []):
                    bvid = it.get('bvid')
                    if not bvid:
                        continue
                    videos.append({
                        'vod_id': 'bv%s' % bvid,
                        'vod_name': _strip_tags(it.get('title')),
                        'vod_pic': _pic(it.get('pic')),
                        'vod_remarks': _strip_tags(it.get('author', '')),
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
