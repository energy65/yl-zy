# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 滴滴美剧 (ddmeiju.com)
支持: 分类栏 / 首页推荐 / 分页列表 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)

站点说明:
  滴滴美剧 提供美剧、电影等影视资源。本站开放了标准的 CMS JSON 接口
  (/api.php/provide/vod/), 接口直接返回各线路的 m3u8 直链。
  本爬虫全部走该接口取数, 最稳定且数据最全:
    - 分类/分页/首页/搜索 : ac=videolist
    - 详情(含简介、选集) : ac=detail
  播放地址大部分为可直接播放的 m3u8 直链 (parse=0);
  少数非直链线路(如 dytt 的 share 页)则抓取解析页提取 m3u8, 提取失败时
  交给内置网页解析 (parse=1) 兜底。

关键页面:
  接口        : https://ddmeiju.com/api.php/provide/vod/
    - 列表     : ?ac=videolist&t={type_id}&pg={page}
    - 搜索     : ?ac=videolist&wd={关键词}
    - 详情     : ?ac=detail&ids={vod_id}
  详情页      : https://ddmeiju.com/{slug}/
  播放页(示例): https://ddmeiju.com/{slug}/{nid}?sid={sid}
"""

import re
import json
import ssl
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

BASE_URL = 'https://ddmeiju.com'
AD_INFO = "\n\n---\n微信公众号：源力软件汇\nQQ群：1054592152\n伴随更多优质资源尽在源力"

# 分类 (type_id 取自接口 t 参数)
CATEGORIES = [
    {"type_id": "2",  "type_name": "电视剧",   "order": 0},
    {"type_id": "1",  "type_name": "电影",     "order": 1},
    {"type_id": "14", "type_name": "欧美剧",   "order": 2},
    {"type_id": "13", "type_name": "国产剧",   "order": 3},
    {"type_id": "3",  "type_name": "动漫片",   "order": 4},
    {"type_id": "21", "type_name": "日韩",     "order": 5},
    {"type_id": "15", "type_name": "日本剧",   "order": 6},
    {"type_id": "16", "type_name": "韩国剧",   "order": 7},
    {"type_id": "4",  "type_name": "综艺片",   "order": 8},
    {"type_id": "6",  "type_name": "动作",     "order": 9},
    {"type_id": "7",  "type_name": "喜剧",     "order": 10},
    {"type_id": "8",  "type_name": "爱情",     "order": 11},
    {"type_id": "9",  "type_name": "科幻",     "order": 12},
    {"type_id": "10", "type_name": "恐怖片",   "order": 13},
    {"type_id": "11", "type_name": "剧情",     "order": 14},
    {"type_id": "12", "type_name": "战争",     "order": 15},
]

API = BASE_URL + '/api.php/provide/vod/'


class Spider(BaseSpider):

    HEADERS = {
        'User-Agent': ('Mozilla/5.0 (Linux; Android 12; SM-G991B) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Mobile Safari/537.36'),
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': BASE_URL + '/',
    }

    _sess = None

    # ==================== 基础 ====================

    def getName(self):
        return "滴滴美剧"

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
        if requests is not None:
            sess = self.__class__._sess
            if sess is None:
                self.init()
                sess = self.__class__._sess
            if sess is not None:
                try:
                    resp = sess.get(url, timeout=20, allow_redirects=True)
                    return resp.text if resp.status_code == 200 else ''
                except Exception:
                    return ''
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=self.HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _api(self, params):
        """调用 CMS 接口, 返回解析后的 dict; 失败返回空 dict"""
        q = '&'.join('%s=%s' % (k, quote(str(v), safe='')) for k, v in params.items())
        url = API + ('&' + q if '?' in API else '?' + q)
        text = self._get(url)
        if not text:
            return {}
        try:
            data = json.loads(text)
        except Exception:
            return {}
        if not isinstance(data, dict) or not data.get('list'):
            return {}
        return data

    def _clean(self, text):
        if text is None:
            return ''
        if not isinstance(text, str):
            text = str(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<') \
                   .replace('&gt;', '>').replace('&quot;', '"') \
                   .replace('&#039;', "'").replace('&nbsp;', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _fix_url(self, u):
        if not u:
            return ''
        u = str(u).replace('\\/', '/').replace('&amp;', '&')
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('http'):
            return u
        return urljoin(BASE_URL, u)

    # ==================== 列表项映射 ====================

    def _item(self, d):
        vod_id = str(d.get('vod_id') or d.get('vod_en') or '')
        name = d.get('vod_name') or ''
        year = str(d.get('vod_year') or '')
        if year and year.isdigit() and not name.rstrip().endswith(year):
            name = name.rstrip() + ' (%s)' % year
        pic = d.get('vod_pic') or d.get('vod_pic_thumb') or ''
        remarks = d.get('vod_remarks') or ''
        score = d.get('vod_score') or ''
        if score and str(score) not in ('0', '0.0', ''):
            remarks = ('%s * %s' % (score, remarks)).strip(' *')
        return {
            'vod_id': vod_id,
            'vod_name': name,
            'vod_pic': self._fix_url(pic),
            'vod_remarks': remarks,
        }

    # ==================== 首页 ====================

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result = {"class": classes, "filters": {}}
        data = self._api({'ac': 'videolist', 'pg': 1})
        result['list'] = [self._item(d) for d in data.get('list', [])][:20]
        return result

    def homeVideoContent(self):
        data = self._api({'ac': 'videolist', 'pg': 1})
        return {"list": [self._item(d) for d in data.get('list', [])]}

    # ==================== 分类 ====================

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except (TypeError, ValueError):
            page = 1
        page = max(page, 1)
        if not str(tid).isdigit():
            tid = '2'
        data = self._api({'ac': 'videolist', 't': str(tid), 'pg': page})
        vods = [self._item(d) for d in data.get('list', [])]
        pc = 1
        try:
            pc = max(int(data.get('pagecount') or 1), page)
        except (TypeError, ValueError):
            pc = page
        limit = len(vods) if vods else 20
        try:
            total = int(data.get('total') or 0)
        except (TypeError, ValueError):
            total = 0
        return {
            "list": vods,
            "page": page,
            "pagecount": pc if pc else 1,
            "limit": limit,
            "total": total,
        }

    # ==================== 详情 ====================

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ''
        vid = re.match(r'\d+', vid)
        if not vid:
            return {"list": []}
        vid = vid.group(0)
        data = self._api({'ac': 'detail', 'ids': vid})
        if not data or not data.get('list'):
            return {"list": []}
        return {"list": [self._parse_detail(data['list'][0])]}

    def _parse_detail(self, d):
        vod_id = str(d.get('vod_id') or '')
        name = d.get('vod_name') or ''
        year = str(d.get('vod_year') or '')
        if year and year.isdigit() and not name.rstrip().endswith(year):
            name = name.rstrip() + ' (%s)' % year

        director = d.get('vod_director') or ''
        actor = d.get('vod_actor') or ''
        area = d.get('vod_area') or ''
        lang = d.get('vod_lang') or ''
        if area and lang and lang not in area:
            area = '%s/%s' % (area, lang)
        genre = d.get('vod_class') or d.get('type_name') or ''
        score = d.get('vod_score') or ''

        content = self._clean(d.get('vod_content') or d.get('vod_blurb') or '')
        if not content:
            content = d.get('vod_name') or ''
        content = (content + AD_INFO) if content else AD_INFO

        vod = {
            'vod_id': vod_id,
            'vod_name': name,
            'vod_pic': self._fix_url(d.get('vod_pic') or ''),
            'vod_remarks': d.get('vod_remarks') or '',
            'vod_year': year,
            'vod_area': area,
            'vod_actor': actor,
            'vod_director': director,
            'vod_class': genre,
            'vod_score': score,
            'vod_content': content,
            'type_name': d.get('type_name') or '',
            'vod_play_from': '',
            'vod_play_url': '',
        }

        # 选集: 多线路由 $$$ 分隔, 每线路内由 # 分隔, 格式: 名称$url
        play_from = (d.get('vod_play_from') or '').strip()
        play_url = (d.get('vod_play_url') or '').strip()
        if play_from and play_url:
            froms = [f for f in play_from.split('$$$') if f]
            groups = [g for g in play_url.split('$$$') if g]
            merged_f = []
            merged_u = []
            # 线路数一致时逐行合并; 不一致时整体作为单线路
            if len(froms) == len(groups):
                for sf, su in zip(froms, groups):
                    merged_f.append(sf)
                    merged_u.append(su)
            else:
                merged_f.append('云播')
                merged_u.append(play_url)
            vod['vod_play_from'] = '$$$'.join(merged_f)
            vod['vod_play_url'] = '$$$'.join(merged_u)

        return vod

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        if not key:
            return {"list": []}
        try:
            page = max(int(pg), 1)
        except (TypeError, ValueError):
            page = 1
        data = self._api({'ac': 'videolist', 'wd': str(key), 'pg': page})
        vods = [self._item(d) for d in data.get('list', [])]
        return {"list": vods}

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        url = self._fix_url(id)
        header = {
            'User-Agent': self.HEADERS['User-Agent'],
            'Referer': BASE_URL + '/',
        }
        # 直接可播放的直链
        if re.search(r'\.(m3u8|mp4|flv)', url, re.I):
            return {
                'parse': 0,
                'playUrl': '',
                'url': url,
                'header': json.dumps(header, ensure_ascii=False),
            }
        # 非直链(如 share 解析页): 尝试提取 m3u8/mp4
        resolved = self._resolve(url)
        if resolved:
            return {
                'parse': 0,
                'playUrl': '',
                'url': resolved,
                'header': json.dumps(header, ensure_ascii=False),
            }
        # 兜底: 交给内置网页解析
        return {
            'parse': 1,
            'playUrl': '',
            'url': url,
            'header': json.dumps(header, ensure_ascii=False),
        }

    def _resolve(self, url):
        if not url:
            return ''
        html = self._get(url)
        if not html:
            return ''
        # share 页: const url = "/xxx/index.m3u8?sign=..." (相对路径基于 share 页域名)
        m = re.search(r'(?:const|var)\s+url\s*=\s*["\']([^"\']+)["\']', html)
        if m:
            u = m.group(1).replace('\\/', '/')
            if re.search(r'\.m3u8|\.mp4', u, re.I):
                if u.startswith('http'):
                    return u
                if u.startswith('//'):
                    return 'https:' + u
                return urljoin(url, u)
        for u in re.findall(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', html):
            return u.replace('\\/', '/')
        for u in re.findall(r'"(?:url|playUrl|backup)"\s*:\s*"([^"]+)"', html):
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
        print("用法: python 滴滴美剧.py home|categories|list <分类id> <页>|detail <影片ID>|play <播放URL>|search <关键词>")
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
