"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '电影侠',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
import html as html_mod
import base64
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    # 主频道筛选数据（均取自站点筛选页 /show/ 的实际选项，已验证可用）
    # type 为类型值列表；area/lang/year/sort 为 (显示名, 值) 元组列表
    _AREAS_ALL = [('大陆', '中国大陆'), ('香港', '中国香港'), ('台湾', '中国台湾'), ('美国', '美国'),
                  ('日本', '日本'), ('韩国', '韩国'), ('英国', '英国'), ('法国', '法国'), ('德国', '德国'),
                  ('印度', '印度'), ('泰国', '泰国'), ('丹麦', '丹麦'), ('瑞典', '瑞典'), ('巴西', '巴西'),
                  ('加拿大', '加拿大'), ('俄罗斯', '俄罗斯'), ('意大利', '意大利'), ('比利时', '比利时'),
                  ('爱尔兰', '爱尔兰'), ('西班牙', '西班牙'), ('澳大利亚', '澳大利亚'), ('其他', '其他')]
    _AREAS_TV = [('大陆', '中国大陆'), ('香港', '中国香港'), ('韩国', '韩国'), ('美国', '美国'),
                 ('日本', '日本'), ('法国', '法国'), ('英国', '英国'), ('德国', '德国'),
                 ('台湾', '中国台湾'), ('泰国', '泰国'), ('印度', '印度'), ('其他', '其他')]
    _AREAS_ZY = [('大陆', '中国大陆'), ('香港', '中国香港'), ('台湾', '中国台湾'), ('美国', '美国'),
                 ('日本', '日本'), ('韩国', '韩国'), ('其他', '其他')]
    _LANGS = [('国语', '国语'), ('粤语', '粤语'), ('英语', '英语'), ('日语', '日语'),
              ('韩语', '韩语'), ('法语', '法语'), ('其他', '其他')]
    _YEARS = [(str(y), str(y)) for y in range(2026, 2019, -1)] + [
        ('10年代', '2010_2019'), ('00年代', '2000_2009'), ('90年代', '1990_1999'),
        ('80年代', '1980_1989'), ('更早', '0_1979')]
    _SORTS = [('综合', '1'), ('最新', '2'), ('最热', '3'), ('评分', '4')]
    _SORTS_DJ = [('综合', '1'), ('最新', '2'), ('最热', '3')]

    CHANNELS = [
        ('1', '电影', {
            'type': ['剧情', '喜剧', '动作', '爱情', '恐怖', '惊悚', '犯罪', '科幻',
                     '悬疑', '奇幻', '冒险', '战争', '历史', '古装', '家庭', '传记',
                     '武侠', '歌舞', '短片', '动画', '儿童', '职场'],
            'area': _AREAS_ALL, 'lang': _LANGS, 'year': _YEARS, 'sort': _SORTS,
        }),
        ('2', '连续剧', {
            'type': ['剧情', '爱情', '喜剧', '犯罪', '悬疑', '古装', '动作', '家庭',
                     '惊悚', '奇幻', '美剧', '科幻', '历史', '战争', '韩剧', '武侠',
                     '言情', '恐怖', '冒险', '都市', '职场'],
            'area': _AREAS_TV, 'lang': _LANGS, 'year': _YEARS, 'sort': _SORTS,
        }),
        ('3', '动漫', {
            'type': ['动态漫画', '剧情', '动画', '喜剧', '冒险', '动作', '奇幻', '科幻',
                     '儿童', '搞笑', '爱情', '家庭', '短片', '热血', '益智', '悬疑',
                     '经典', '校园', 'Anime', '运动', '亲子', '青春', '恋爱', '武侠', '惊悚'],
            'area': _AREAS_ALL, 'lang': _LANGS, 'year': _YEARS, 'sort': _SORTS,
        }),
        ('4', '综艺纪录', {
            'type': ['纪录', '真人秀', '记录', '脱口秀', '剧情', '历史', '喜剧', '传记',
                     '相声', '节目', '歌舞', '冒险', '运动', 'Season', '犯罪', '短片',
                     '搞笑', '晚会'],
            'area': _AREAS_ZY, 'lang': _LANGS, 'year': _YEARS, 'sort': _SORTS,
        }),
        ('6', '短剧', {
            'type': ['王爷太子', '霸道总裁', '屌丝逆袭', '赘婿系列', '重生系列', '穿越短剧',
                     '美女总裁', '娇妻系列', '龙王系列', '都市言情', '逆袭', '甜宠', '虐恋',
                     '穿越', '重生', '剧情', '科幻', '武侠', '爱情', '动作', '战争',
                     '冒险', '其它'],
            'sort': _SORTS_DJ,
        }),
    ]

    # 微信公众号信息（XOR加密存储，key=YLSOFT2026）
    # 解密后: 微信公众号“源力软件汇”，q群1054592152，更多优质资源尽在源力
    WX_INFO = ('vPL9q/n117We0uXbtsDxtrKs1IzJqdnUrumd1ImAv/3UrcbJ3Yy+R77y9352YQYFCwR'
               'oeWGg+tjUq4bT/da38968hpjag92q6d+j5I/Vrp6/9sOqzM8=')

    # 搜索token提取（token形如 QSKoFHK%2Ff5xIyO%2FNmvLD%2FQ%3D%3D，与cookie会话绑定）
    _TOKEN_RE = re.compile(r'/search\?k=[^"\'&\s]+&(?:amp;)?t=([^"\'&\s]+)')

    def init(self, extend=""):
        self.host = "https://www.dyx00.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.61 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self._encrypt_key = b'YLSOFT2026'
        self._search_token = ''
        self._opener = None

    def getName(self):
        return '电影侠'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _xor_encrypt(self, text):
        key = self._encrypt_key
        text_bytes = text.encode('utf-8')
        encrypted = bytearray()
        for i in range(len(text_bytes)):
            encrypted.append(text_bytes[i] ^ key[i % len(key)])
        return base64.b64encode(encrypted).decode('utf-8')

    def _xor_decrypt(self, encrypted_text):
        key = self._encrypt_key
        encrypted_bytes = base64.b64decode(encrypted_text)
        decrypted = bytearray()
        for i in range(len(encrypted_bytes)):
            decrypted.append(encrypted_bytes[i] ^ key[i % len(key)])
        return decrypted.decode('utf-8')

    @staticmethod
    def _type_display(ch, t):
        # 电影频道类型显示名带“片”字（如科幻->科幻片），本身以“片”结尾的不重复加
        if ch == '1' and not t.endswith('片'):
            return t + '片'
        return t

    def _build_filters(self, ch, groups):
        fl = []
        types = groups.get('type')
        if types:
            fl.append({'key': 'type', 'name': '类型',
                       'value': [{'n': '全部', 'v': ''}] + [
                           {'n': self._type_display(ch, t), 'v': t} for t in types]})
        for key, name in [('area', '地区'), ('lang', '语言'), ('year', '年份'), ('sort', '排序')]:
            vals = groups.get(key)
            if vals:
                fl.append({'key': key, 'name': name,
                           'value': [{'n': '全部', 'v': ''}] + [
                               {'n': n, 'v': v} for n, v in vals]})
        return fl

    def homeContent(self, filter):
        result = {"class": []}
        try:
            filters = {}
            for ch, name, groups in self.CHANNELS:
                # 一级只放主频道，细化类型/地区/年份等作为该分类下的筛选条件
                result["class"].append({'type_id': ch, 'type_name': name})
                if filter:
                    fl = self._build_filters(ch, groups)
                    if fl:
                        filters[ch] = fl
            if filters:
                result["filters"] = filters
        except Exception as e:
            print(f'homeContent error: {e}')
        return result

    def homeVideoContent(self):
        try:
            html = self._fetch('/')
            items = self._parse_list(html)
            return {"list": items[:30]}
        except Exception as e:
            print(f'homeVideoContent error: {e}')
            return {"list": []}

    @staticmethod
    def _parse_extend(extend):
        # TVBox 传来的筛选条件可能是 dict 或 JSON 字符串，统一转 dict
        if not extend:
            return {}
        if isinstance(extend, dict):
            return extend
        try:
            obj = json.loads(extend)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 18, "total": 0}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            ext = self._parse_extend(extend)
            if '-' in tid:
                # 兼容旧式 tid（如 1-科幻）
                ch, typ0 = tid.split('-', 1)
                if typ0 and not ext.get('type'):
                    ext['type'] = typ0
            else:
                ch = tid
            # 筛选页URL: /show/{频道}-{类型}-{地区}-{语言}-{年份}-{排序}-{页码}.html
            # 空位留空，排序默认3=最热（与站点默认一致）
            path = '/show/' + '-'.join([
                ch,
                urllib.parse.quote(ext.get('type', '') or ''),
                urllib.parse.quote(ext.get('area', '') or ''),
                urllib.parse.quote(ext.get('lang', '') or ''),
                ext.get('year', '') or '',
                ext.get('sort', '') or '3',
                str(page),
            ]) + '.html'
            html = self._fetch(path)
            items = self._parse_list(html)
            has_next = 'page-item-next' in html
            pagecount = page + 1 if (has_next and items) else page
            result = {"list": items, "page": page, "pagecount": pagecount, "limit": 18, "total": pagecount * 18}
        except Exception as e:
            print(f'categoryContent error: {e}')
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) else str(ids)
        try:
            if vid.startswith('http'):
                detail_url = vid
            elif vid.startswith('/'):
                detail_url = self.host + vid
            else:
                detail_url = f'{self.host}/detail/{vid}.html'

            html = self._fetch(detail_url)
            if not html:
                return result

            # 名称：detail-title 的偶数位 strong 为真名，奇数位为站标水印（CSS隐藏）
            vod_name = ''
            m_title = re.search(r'<div[^>]*class=["\']detail-title["\'][^>]*>([\s\S]*?)</div>', html)
            if m_title:
                for strong in re.findall(r'<strong>([^<]+)</strong>', m_title.group(1)):
                    s = strong.strip()
                    if s and '𝕜' not in s and 'kkys' not in s.lower() and 'kekys' not in s.lower() and '.com' not in s.lower():
                        vod_name = s
                        break
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('-')[0].strip()
            if not vod_name:
                m_name = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if m_name:
                    vod_name = m_name.group(1).strip()

            # 封面（排除占位图/站标/图标）
            vod_pic = ''
            for orig in re.findall(r'data-original=["\']([^"\']+)["\']', html):
                o = orig.strip()
                if o and 'placeholder' not in o.lower() and 'logo' not in o.lower() and 'icons/' not in o.lower():
                    vod_pic = o
                    break
            if not vod_pic:
                m_pic = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
                if m_pic:
                    vod_pic = m_pic.group(1).strip()
            if vod_pic and vod_pic.startswith('//'):
                vod_pic = 'https:' + vod_pic
            if vod_pic and vod_pic.startswith('/'):
                vod_pic = self.host + vod_pic

            # 类型/地区/年份：detail-tags-item 的 show 链接按位置携带
            # /show/{频道}-{类型}-{地区}-{语言}-{年份}-{排序}-{页码}.html
            vod_class_parts = []
            vod_area = ''
            vod_year = ''
            for href, text in re.findall(r'<a[^>]+href=["\'](/show/[^"\']+\.html)["\'][^>]*class=["\']detail-tags-item["\'][^>]*>([^<]+)</a>', html):
                segs = []
                m_seg = re.search(r'/show/([^/\'"]+)\.html', href)
                if m_seg:
                    segs = urllib.parse.unquote(m_seg.group(1)).split('-')
                if len(segs) >= 5:
                    if segs[1] and segs[1] not in vod_class_parts:
                        vod_class_parts.append(segs[1])
                    if segs[2]:
                        vod_area = segs[2]
                    if re.match(r'^\d{4}$', segs[4]):
                        vod_year = segs[4]
                else:
                    text = text.strip()
                    if re.match(r'^\d{4}$', text):
                        vod_year = text
                    elif text and text not in vod_class_parts:
                        vod_class_parts.append(text)
            # 去重：站点可能同时给出“剧情”与“剧情片”标签，基名相同只保留首个
            seen_base = set()
            final_parts = []
            for c in vod_class_parts:
                base = c[:-1] if c.endswith('片') and len(c) > 2 else c
                if base not in seen_base:
                    seen_base.add(base)
                    final_parts.append(c)
            vod_class_parts = final_parts

            # 导演/演员/首映/备注：detail-info-row 的 side+main 结构
            vod_director = ''
            vod_actor = ''
            vod_remarks = ''
            for label, main in re.findall(r'<div[^>]*class=["\']detail-info-row-side["\'][^>]*>([^<]*)</div>\s*<div[^>]*class=["\']detail-info-row-main["\'][^>]*>([\s\S]*?)</div>', html):
                label = label.strip().rstrip('：:')
                names = [a.strip() for a in re.findall(r'<a[^>]*>([^<]+)</a>', main) if a.strip()]
                if label == '导演':
                    vod_director = ', '.join(names) if names else self._clean_text(main)
                elif label == '演员':
                    vod_actor = ', '.join(names) if names else self._clean_text(main)
                elif label == '首映' and not vod_year:
                    m_y = re.search(r'\d{4}', main)
                    if m_y:
                        vod_year = m_y.group(0)
                elif label == '备注':
                    vod_remarks = self._clean_text(main)

            # 简介
            vod_content = ''
            m_desc = re.search(r'<div[^>]*class=["\']detail-desc["\'][^>]*>([\s\S]*?)</div>', html)
            if m_desc:
                vod_content = self._clean_text(m_desc.group(1))
            # 简介尾部追加微信公众号信息（XOR加密存储）
            try:
                wx_info = self._xor_decrypt(self.WX_INFO)
            except Exception:
                wx_info = '微信公众号“源力软件汇”'
            if vod_content:
                vod_content = vod_content + '\n\n' + wx_info
            else:
                vod_content = wx_info

            if not vod_remarks:
                m_remarks = re.search(r'(更新至[^<]{1,12}|HD|BD|4K|正片|已完结|全\d+集|完结)', html)
                if m_remarks:
                    vod_remarks = m_remarks.group(1).strip()

            # 多线路与剧集：source-item 与 episode-list 按索引一一对应
            play_from_list = []
            play_url_list = []
            source_items = re.findall(r'<a[^>]+class=["\']source-item[^"\']*["\'][^>]*>([\s\S]*?)</a>', html)
            episode_lists = re.findall(r'<div[^>]*class=["\']episode-list["\'][^>]*>([\s\S]*?)</div>', html)
            for idx, source_item in enumerate(source_items):
                if idx >= len(episode_lists):
                    break
                m_label = re.search(r'class=["\']source-item-label["\'][^>]*>([^<]+)<', source_item)
                source_name = m_label.group(1).strip() if m_label else f'线路{idx + 1}'
                eps = []
                for href, content in re.findall(r'<a[^>]+href=["\'](/play/\d+-\d+-\d+\.html)["\'][^>]*>([\s\S]*?)</a>', episode_lists[idx]):
                    title = re.sub(r'<[^>]+>', '', content).strip()
                    if title:
                        eps.append(f'{title}${href}')
                if eps:
                    if source_name in play_from_list:
                        source_name = f'{source_name}{play_from_list.count(source_name) + 1}'
                    play_from_list.append(source_name)
                    play_url_list.append('#'.join(eps))

            # 兜底：详情页“立即播放”按钮
            if not play_url_list:
                m_btn = re.search(r'<a[^>]+href=["\'](/play/\d+-\d+-\d+\.html)["\'][^>]*>\s*<button[^>]*play-btn', html)
                if m_btn:
                    play_from_list.append('默认线路')
                    play_url_list.append(f'正片${m_btn.group(1)}')

            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_director": vod_director,
                "vod_actor": vod_actor,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_remarks": vod_remarks,
                "vod_content": vod_content,
                "vod_class": ','.join(vod_class_parts),
                "vod_play_from": '$$$'.join(play_from_list) if play_from_list else '电影侠',
                "vod_play_url": '$$$'.join(play_url_list),
            }
            result['list'].append(vod)
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            play_url = id
            if play_url.startswith('enc:'):
                play_url = self._xor_decrypt(play_url[4:])
            if not play_url.startswith('http'):
                play_url = self.host + (play_url if play_url.startswith('/') else f'/play/{play_url}')
            html = self._fetch(play_url)
            play_src = self._extract_m3u8(html) if html else ''
            if play_src:
                result["url"] = play_src
                result["parse"] = 0
                result["header"] = json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.host + "/",
                })
            else:
                # 兜底：交给嗅探
                result["url"] = play_url
                result["parse"] = 1
        except Exception as e:
            print(f'playerContent error: {e}')
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 18, "total": 0}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            result["page"] = page
            items = []
            # 搜索依赖cookie会话+token：先GET首页建立会话并提取token
            token = self._get_search_token()
            if token:
                html = self._session_get(self._search_path(key, token, page))
                if html:
                    # 每次搜索响应会携带新token，更新缓存供翻页使用
                    self._update_token(html)
                    items = self._parse_search_list(html)
            if not items:
                # token/会话可能失效：强制重建会话重试一次
                token = self._get_search_token(force=True)
                if token:
                    html = self._session_get(self._search_path(key, token, page))
                    if html:
                        self._update_token(html)
                        items = self._parse_search_list(html)
            pagecount = page + 1 if len(items) >= 18 else page
            result = {"list": items, "page": page, "pagecount": pagecount, "limit": 18, "total": pagecount * 18}
        except Exception as e:
            print(f'searchContent error: {e}')
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param=''):
        return {}

    @staticmethod
    def _search_path(key, token, page):
        path = f'/search?k={urllib.parse.quote(key)}&t={token}'
        if page > 1:
            path += f'&page={page}'
        return path

    def _ensure_opener(self):
        if self._opener is None:
            cj = http.cookiejar.CookieJar()
            self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            self._opener.addheaders = [
                ('User-Agent', self.headers['User-Agent']),
                ('Accept', self.headers['Accept']),
                ('Accept-Language', self.headers['Accept-Language']),
                ('Referer', self.host + '/'),
            ]
        return self._opener

    def _session_get(self, path):
        # 带cookie会话的GET（专用于搜索：token与session cookie绑定）
        try:
            opener = self._ensure_opener()
            url = path if path.startswith('http') else self.host + path
            for attempt in range(2):
                try:
                    req = urllib.request.Request(url)
                    with opener.open(req, timeout=30) as rsp:
                        return rsp.read().decode('utf-8', 'ignore')
                except urllib.error.HTTPError:
                    return ''
                except Exception as e:
                    print(f'_session_get error({attempt + 1}): {e}')
            return ''
        except Exception as e:
            print(f'_session_get error: {e}')
            return ''

    def _get_search_token(self, force=False):
        try:
            if force:
                self._search_token = ''
                self._opener = None
            if self._search_token:
                return self._search_token
            html = self._session_get('/')
            if html:
                m = self._TOKEN_RE.search(html)
                if m:
                    self._search_token = m.group(1)
                    return self._search_token
        except Exception as e:
            print(f'_get_search_token error: {e}')
        return ''

    def _update_token(self, html):
        try:
            m = self._TOKEN_RE.search(html)
            if m:
                self._search_token = m.group(1)
        except Exception:
            pass

    @staticmethod
    def _clean_text(raw):
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = html_mod.unescape(text)
        text = text.replace('&nbsp;', ' ')
        text = re.sub(r'<br\s*/?>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _fetch(self, url):
        full_url = url if url.startswith('http') else self.host + url
        headers = dict(self.headers)
        headers["Referer"] = self.host + "/"
        # 网络波动（IncompleteRead等）自动重试一次
        for attempt in range(2):
            try:
                rsp = self.fetch(full_url, headers=headers, timeout=30)
                if rsp and rsp.status_code == 200:
                    return rsp.text
                if rsp and rsp.status_code in (403, 404):
                    return ''
            except Exception as e:
                print(f'_fetch error({attempt + 1}): {e}')
        return ''

    def _extract_m3u8(self, html):
        patterns = [
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'video\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'playUrl\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                url = m.group(1).strip()
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('http'):
                    return url
                if url.startswith('/'):
                    return self.host + url

        m_generic = re.search(r'(https?://[^\s"\'\\]+?\.m3u8[^\s"\'\\]*)', html, re.I)
        if m_generic:
            return m_generic.group(1).strip()

        m_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if m_iframe:
            iframe_src = m_iframe.group(1).strip()
            if iframe_src.startswith('//'):
                iframe_src = 'https:' + iframe_src
            if iframe_src.startswith('http'):
                iframe_html = self._fetch(iframe_src)
                if iframe_html:
                    return self._extract_m3u8(iframe_html)
        return ''

    def _parse_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos
            v_items = re.findall(r'<a[^>]+href=["\'](/detail/\d+\.html)["\'][^>]*class=["\']v-item["\'][^>]*>([\s\S]*?)</a>', html)
            for vid, content in v_items:
                if vid in seen:
                    continue
                seen.add(vid)

                title = ''
                for t in re.findall(r'<div[^>]*class=["\']v-item-title["\'][^>]*>([^<]+)</div>', content):
                    t = t.strip()
                    if t and '可可影视' not in t:
                        title = t
                        break
                if not title or len(title) < 2:
                    continue

                pic = ''
                for orig in re.findall(r'data-original=["\']([^"\']+)["\']', content):
                    o = orig.strip()
                    if o and 'placeholder' not in o.lower() and 'logo' not in o.lower():
                        pic = o
                        break
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_bottom = re.search(r'<div[^>]*class=["\']v-item-bottom["\'][^>]*>([\s\S]*?)</div>', content)
                if m_bottom:
                    remarks = re.sub(r'<[^>]+>', '', m_bottom.group(1)).strip()
                if not remarks:
                    m_score = re.search(r'<span>(豆瓣:\d+\.\d+分)</span>', content)
                    if m_score:
                        remarks = m_score.group(1).strip()

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print(f'_parse_list error: {e}')
        return videos

    def _parse_search_list(self, html):
        videos = []
        seen = set()
        try:
            if not html:
                return videos
            items = re.findall(r'<a[^>]+href=["\'](/detail/\d+\.html)["\'][^>]*class=["\']search-result-item["\'][^>]*>([\s\S]*?)</a>', html)
            for vid, item_content in items:
                if vid in seen:
                    continue
                seen.add(vid)

                title = ''
                m_title = re.search(r'<div[^>]*class=["\']title["\'][^>]*>([^<]+)</div>', item_content)
                if m_title:
                    title = m_title.group(1).strip()
                if not title:
                    m_attr = re.search(r'title=["\']([^"\']+)["\']', item_content)
                    if m_attr:
                        title = m_attr.group(1).strip()
                if not title or len(title) < 2:
                    continue

                pic = ''
                m_pic = re.search(r'data-original=["\']([^"\']+)["\']', item_content, re.I)
                if not m_pic:
                    m_pic = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', item_content, re.I)
                if m_pic:
                    pic = m_pic.group(1).strip()
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic
                if pic and pic.startswith('/'):
                    pic = self.host + pic

                remarks = ''
                m_tags = re.search(r'<div[^>]*class=["\']tags["\'][^>]*>([\s\S]*?)</div>', item_content)
                if m_tags:
                    tags_text = re.sub(r'<[^>]+>', '', m_tags.group(1)).strip()
                    parts = [p.strip() for p in tags_text.split('/') if p.strip()]
                    if parts:
                        remarks = parts[0].strip()[:20]

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print(f'_parse_search_list error: {e}')
        return videos
