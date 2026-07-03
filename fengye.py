# -*- coding: utf-8 -*-
# !/usr/bin/python
import requests
import base64
import re
import json
import sys
import urllib.parse
import ssl
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ciphers = (
            'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
            'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
            'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
            'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
        )
        context = create_urllib3_context(ciphers=ciphers)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


VIP_CATEGORIES = [
    {"type_id": "search_tencent", "type_name": "腾讯vip"},
    {"type_id": "search_youku", "type_name": "优酷vip"},
    {"type_id": "search_bilibili", "type_name": "b站vip"},
]

VIP_CATEGORY_MAP = {
    'search_tencent': '2',
    'search_youku': '1',
    'search_bilibili': '4',
}

PARSE_MAP = {
    'JD4K': 'https://fgsrg.hzqingshan.com/player/?url=',
    'JD2K': 'https://fgsrg.hzqingshan.com/player/?url=',
    'YYNB': 'https://zzrs.mfdyvip.com/player/?url=',
}


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.session = requests.Session()
        self.session.verify = False
        self.session.mount('https://', TLSAdapter())
        self.host = "https://www.cd-zj.com"
        self.name = "枫叶影视"
        self.site_type = "detail"
        self.config = {
            "name": "🍁枫叶影视",
            "list_selectors": [
                '.public-list-box.public-pic-b',
                '.public-list-box.search-box',
                '.public-list-box',
            ],
            "category_url_type": "type",
            "search_url": "/cupfox-search/-------------.html",
            "search_param": "wd",
            "has_vip": True,
            "has_parse": True,
            "ua": "pc",
        }
        self.headers = self._get_headers("pc")

    def _get_headers(self, ua_type):
        if ua_type == "mobile":
            return {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Referer': f'{self.host}/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        else:
            return {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': f'{self.host}/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }

    def getName(self):
        return self.config["name"]

    def init(self, extend):
        if extend and extend.strip():
            extend = extend.strip().strip('`').strip()
            if extend.startswith('http'):
                self.host = extend.rstrip('/')
                self._detect_site_type()
                self.headers = self._get_headers(self.config.get("ua", "pc"))
                self.headers['Referer'] = f'{self.host}/'

    def _detect_site_type(self):
        try:
            res = self.session.get(self.host, headers=self._get_headers("pc"), timeout=15)
            text = res.text
            soup = BeautifulSoup(text, 'html.parser')

            detail_patterns = [
                (r'/chabeihu/(\d+)\.html', "chabeihu"),
                (r'/zform/(\d+)\.html', "zform"),
                (r'/detail/(\d+)\.html', "detail"),
            ]

            self.site_type = "detail"
            for pattern, stype in detail_patterns:
                if re.search(pattern, text):
                    self.site_type = stype
                    break

            has_4k = '4k' in text.lower() or '臻' in text

            list_selectors = []
            if soup.select_one('.public-list-box.public-pic-b'):
                list_selectors.append('.public-list-box.public-pic-b')
            if soup.select_one('.public-list-box.search-box'):
                list_selectors.append('.public-list-box.search-box')
            if soup.select_one('.movie-list-item'):
                list_selectors.append('.movie-list-item')
            if soup.select_one('.public-list-box'):
                list_selectors.append('.public-list-box')

            category_url_type = "type"
            if re.search(r'/cupfox-list/\d+', text):
                category_url_type = "cupfox-list"
            elif re.search(r'/zform-list/\d+', text):
                category_url_type = "zform-list"
            elif re.search(r'/type/\d+', text):
                category_url_type = "type"

            search_url = "/cupfox-search/-------------.html"
            search_param = "wd"
            if re.search(r'vod-search', text):
                search_url = "/index.php"
                search_param = "wd"

            self.config = {
                "name": "🍁枫叶影视",
                "list_selectors": list_selectors if list_selectors else ['.public-list-box'],
                "category_url_type": category_url_type,
                "search_url": search_url,
                "search_param": search_param,
                "has_vip": has_4k,
                "has_parse": has_4k,
                "ua": "pc",
            }
        except Exception as e:
            print(f"[{self.name}] 站点检测失败，使用默认配置 - {e}")

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "5", "type_name": "热门短剧"},
        ]

        if self.config.get("has_vip", False):
            classes.extend(VIP_CATEGORIES)

        filter_dict = self._build_filters()

        try:
            res = self.session.get(self.host, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            videos = self._parse_list(soup)

            return {
                'class': classes,
                'filters': filter_dict,
                'list': videos
            }
        except Exception as e:
            print(f"[{self.name}] 错误: 首页爬取失败 - {e}")
            return {'class': classes, 'filters': filter_dict, 'list': []}

    def _build_filters(self):
        filter_dict = {}

        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2003, -1)]
        orders = [
            {"n": "时间", "v": ""},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"}
        ]

        movie_classes = ["动作片", "喜剧片", "恐怖片", "科幻片", "爱情片", "剧情片", "战争片", "纪录片"]
        movie_areas = ["大陆", "香港", "台湾", "美国", "韩国", "日本", "泰国", "新加坡", "马来西亚", "印度", "英国",
                       "法国", "加拿大", "西班牙", "俄罗斯", "其它"]

        tv_classes = ["国产剧", "香港剧", "台湾剧", "日本剧", "韩国剧", "欧美剧", "海外剧", "泰剧", "越南剧"]
        tv_areas = ["内地", "香港", "台湾", "日本", "韩国", "美国", "英国", "泰国", "其他"]

        comic_classes = ["国产动漫", "日本动漫", "欧美动漫", "海外动漫"]

        show_classes = ["大陆综艺", "日韩综艺", "欧美综艺", "港台综艺"]

        def create_filter(classes_list, areas_list):
            return [
                {"key": "class", "name": "类型",
                 "value": [{"n": "全部", "v": ""}] + [{"n": c, "v": c} for c in classes_list]},
                {"key": "area", "name": "地区",
                 "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in areas_list]},
                {"key": "year", "name": "年份", "value": years},
                {"key": "by", "name": "排序", "value": orders}
            ]

        filter_dict["1"] = create_filter(movie_classes, movie_areas)
        filter_dict["2"] = create_filter(tv_classes, tv_areas)
        filter_dict["4"] = create_filter(comic_classes, tv_areas)
        filter_dict["3"] = create_filter(show_classes, tv_areas)

        return filter_dict

    def homeVideoContent(self):
        return {'list': []}

    def _get_detail_id(self, href):
        patterns = [
            r'/chabeihu/(\d+)\.html',
            r'/zform/(\d+)\.html',
            r'/detail/(\d+)\.html',
        ]
        for pattern in patterns:
            m = re.search(pattern, href)
            if m:
                return m.group(1)
        return None

    def _parse_list(self, soup):
        videos = []
        seen = set()

        selectors = self.config.get("list_selectors", ['.public-list-box'])
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break

        if not items:
            all_a = soup.find_all('a', href=True)
            temp_map = {}
            for a in all_a:
                href = a.get('href', '')
                vod_id = self._get_detail_id(href)
                if not vod_id:
                    continue
                if vod_id in seen:
                    continue

                if vod_id not in temp_map:
                    temp_map[vod_id] = {'vod_id': vod_id, 'vod_name': '', 'vod_pic': '', 'vod_remarks': ''}

                img = a.find('img')
                if img and not temp_map[vod_id]['vod_pic']:
                    pic = img.get('data-src') or img.get('src') or ''
                    if pic and pic.startswith('//'):
                        pic = 'https:' + pic
                    temp_map[vod_id]['vod_pic'] = pic

                title = a.get('title', '').strip()
                if not title:
                    title = a.get_text(strip=True)

                parent = a.parent
                is_info = False
                if parent:
                    cls = ' '.join(parent.get('class', []))
                    if 'movie-info' in cls or 'info' in cls:
                        is_info = True

                if title and len(title) < 50 and is_info:
                    temp_map[vod_id]['vod_name'] = title

                note_span = a.select_one('.pic-text b, .pic-text1 b, .public-list-prb')
                if note_span and not temp_map[vod_id]['vod_remarks']:
                    temp_map[vod_id]['vod_remarks'] = note_span.get_text(strip=True)

            for vid, data in temp_map.items():
                if data['vod_name'] and data['vod_pic']:
                    videos.append(data)
                    seen.add(vid)
            return videos

        for item in items:
            try:
                a = item.select_one('a[href*="/chabeihu/"], a[href*="/zform/"], a[href*="/detail/"]')
                if not a:
                    all_links = item.find_all('a', href=True)
                    for link in all_links:
                        if self._get_detail_id(link.get('href', '')):
                            a = link
                            break
                if not a:
                    continue

                href = a.get('href', '')
                vod_id = self._get_detail_id(href)
                if not vod_id:
                    continue
                if vod_id in seen:
                    continue
                seen.add(vod_id)

                title = a.get('title', '').strip()
                if not title:
                    title_a = item.select_one('.time-title, .movie-title, .this-desc-title')
                    if title_a:
                        title = title_a.get_text(strip=True)
                if not title:
                    thumb_a = item.select_one('.thumb-txt a')
                    if thumb_a:
                        title = thumb_a.get_text(strip=True)
                if not title:
                    info_div = item.select_one('.movie-info')
                    if info_div:
                        title = info_div.get_text(strip=True)

                pic = ''
                img = item.select_one('img')
                if img:
                    pic = img.get('data-src') or img.get('src') or ''
                    if pic and pic.startswith('//'):
                        pic = 'https:' + pic
                if not pic:
                    cover = item.select_one('.cover')
                    if cover:
                        style = cover.get('style', '')
                        m2 = re.search(r'url\((.*?)\)', style)
                        if m2:
                            pic = m2.group(1).strip('\'"')

                note = ''
                note_tag = item.select_one('.pic-text b, .pic-text1 b, .public-list-prb')
                if note_tag:
                    note = note_tag.get_text(strip=True)

                actor = ''
                sub = item.select_one('.public-list-subtitle')
                if sub:
                    actor = sub.get_text(strip=True)
                if not actor:
                    thumb_actor = item.select_one('.thumb-actor')
                    if thumb_actor:
                        actor = thumb_actor.get_text(strip=True).replace('导演：', '').replace('主演：', '')

                if not title or len(title) < 2:
                    continue

                video = {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                }
                if note:
                    video["vod_remarks"] = note
                if actor:
                    video["vod_actor"] = actor

                videos.append(video)
            except Exception as e:
                print(f"[{self.name}] 错误: 列表解析失败 - {e}")
                continue

        return videos

    def _build_category_url(self, tid, page, extend):
        extend = extend or {}
        area = extend.get('area', '')
        by = extend.get('by', '')
        class_name = extend.get('class', '')
        year = extend.get('year', '')

        if class_name:
            class_name = urllib.parse.quote(class_name)
        if area:
            area = urllib.parse.quote(area)

        url_type = self.config.get("category_url_type", "type")

        if url_type == "cupfox-list":
            return f"{self.host}/cupfox-list/{tid}-{area}-{by}-{class_name}------{page}---{year}.html"
        elif url_type == "zform-list":
            if area or class_name or year or by:
                return f"{self.host}/zform-list/{tid}-{area}-{class_name}-----{by}---{year}-{page}---.html"
            else:
                return f"{self.host}/zform-list/{tid}--------{page}---.html"
        else:
            if page == 1:
                return f"{self.host}/type/{tid}.html"
            else:
                return f"{self.host}/type/{tid}-{page}.html"

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)

        if tid in VIP_CATEGORY_MAP and self.config.get("has_vip", False):
            source_tid = VIP_CATEGORY_MAP[tid]
            return self._vip_category(source_tid, page)

        try:
            url = self._build_category_url(tid, page, extend)
            res = self.session.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            videos = self._parse_list(soup)

            return {
                'list': videos,
                'page': page,
                'pagecount': page + 1 if videos else page,
                'limit': 24,
                'total': 9999 if videos else 0
            }
        except Exception as e:
            print(f"[{self.name}] 错误: 分类爬取失败 - {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 24, 'total': 0}

    def _vip_category(self, source_tid, page):
        try:
            all_videos = {}
            page_size = 24

            for p in range(1, 5):
                url = self._build_category_url(source_tid, p, {})
                res = self.session.get(url, headers=self.headers, timeout=15)
                soup = BeautifulSoup(res.text, 'html.parser')
                videos = self._parse_list(soup)
                if not videos:
                    break
                for v in videos:
                    vid = v.get('vod_id', '')
                    if vid and vid not in all_videos:
                        all_videos[vid] = v

            video_list = list(all_videos.values())
            vip_list = []
            for v in video_list:
                if self._has_4k_line(v['vod_id']):
                    vip_list.append(v)
                    if len(vip_list) >= 72:
                        break

            total = len(vip_list)
            start = (page - 1) * page_size
            end = start + page_size
            page_videos = vip_list[start:end]
            pagecount = (total + page_size - 1) // page_size if total > 0 else 1

            return {
                'list': page_videos,
                'page': page,
                'pagecount': pagecount,
                'limit': page_size,
                'total': total
            }
        except Exception as e:
            print(f"[{self.name}] 错误: VIP分类获取失败 - {e}")
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}

    def _has_4k_line(self, did):
        try:
            detail_url = self._build_detail_url(did)
            res = self.session.get(detail_url, headers=self.headers, timeout=8)
            text = res.text.lower()
            return '4k' in text or '臻' in res.text
        except:
            return False

    def _build_detail_url(self, did):
        if self.site_type == "chabeihu":
            return f"{self.host}/chabeihu/{did}.html"
        elif self.site_type == "zform":
            return f"{self.host}/zform/{did}.html"
        else:
            return f"{self.host}/detail/{did}.html"

    def _build_play_pattern(self):
        if self.site_type == "zform":
            return r'/itrade/\d+-(\d+)-(\d+)\.html'
        else:
            return r'/play/\d+-(\d+)-(\d+)\.html'

    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else str(ids)
        try:
            url = self._build_detail_url(did)
            res = self.session.get(url, headers=self.headers, timeout=15)
            page_text = res.text
            soup = BeautifulSoup(page_text, 'html.parser')

            name = ""
            state = ""
            actor = ""
            director = ""
            year = ""
            area = ""
            content = ""
            pic = ""

            title_tag = soup.select_one('h1')
            if title_tag:
                name = title_tag.get_text(strip=True)
            if not name:
                title_tag = soup.select_one('.this-desc-title')
                if title_tag:
                    name = title_tag.get_text(strip=True)
            if not name:
                title_tag = soup.select_one('title')
                if title_tag:
                    m = re.search(r'《(.*?)》', title_tag.get_text(strip=True))
                    if m:
                        name = m.group(1)
            if not name:
                detail_info = soup.select_one('.detail-info')
                if detail_info:
                    info_text = detail_info.get_text(strip=True)
                    name = info_text.split('202')[0].split('201')[0].split('类型')[0].strip()

            page_text_all = soup.get_text(separator='|', strip=True)
            lines = [x.strip() for x in page_text_all.split('|') if x.strip()]

            for i, line in enumerate(lines):
                if line.startswith('主演:') or line.startswith('主演：') or line.startswith('演员:') or line.startswith('演员：'):
                    val = line[3:].strip()
                    if val:
                        actor = val
                    elif i + 1 < len(lines) and not lines[i + 1].startswith(('导演', '首播', '更新', '地区', '总集数', '别名')):
                        actor = lines[i + 1]
                elif line.startswith('导演:') or line.startswith('导演：'):
                    val = line[3:].strip()
                    if val:
                        director = val
                    elif i + 1 < len(lines) and not lines[i + 1].startswith(('主演', '首播', '更新', '地区', '总集数', '别名')):
                        director = lines[i + 1]
                elif line.startswith('首播:') or line.startswith('首播：') or line.startswith('年份:') or line.startswith('年份：'):
                    m = re.search(r'(\d{4})', line)
                    if m:
                        year = m.group(1)
                    elif i + 1 < len(lines):
                        m = re.search(r'(\d{4})', lines[i + 1])
                        if m:
                            year = m.group(1)
                elif line.startswith('更新:') or line.startswith('更新：') or line.startswith('状态:') or line.startswith('状态：'):
                    val = line[3:].strip()
                    if val:
                        state = val
                    elif i + 1 < len(lines) and not lines[i + 1].startswith(('主演', '导演', '首播', '地区', '总集数', '别名', '[')):
                        state = lines[i + 1]
                elif line.startswith('地区:') or line.startswith('地区：'):
                    val = line[3:].strip()
                    if val:
                        area = val
                    elif i + 1 < len(lines) and not lines[i + 1].startswith(('主演', '导演', '首播', '更新', '总集数', '别名')):
                        area = lines[i + 1]

            if not actor:
                m = re.search(r'[主演演员][：:]\s*(.*?)(?:\s*\|)', page_text_all)
                if m:
                    actor = m.group(1).strip('| ')

            if not director:
                m = re.search(r'导演[：:]\s*(.*?)(?:\s*\|)', page_text_all)
                if m:
                    director = m.group(1).strip('| ')

            if not year:
                m = re.search(r'[首播年份][：:]\s*(\d{4})', page_text_all)
                if m:
                    year = m.group(1)

            if not state:
                m = re.search(r'[更新状态][：:]\s*(.*?)(?:\s*\[|$)', page_text_all)
                if m:
                    state = m.group(1).strip('| ')

            if not year:
                m = re.search(r'(\d{4})年?代?[内地上映台湾香港美国日本韩国]', page_text)
                if m:
                    year = m.group(1)

            if not state:
                m = re.search(r'更新至(\d+集|\d+话)', page_text)
                if m:
                    state = '更新至' + m.group(1)
                elif '已完结' in page_text:
                    state = '已完结'

            intro_match = re.search(r'收起部分\].*?\,(.*?)\s*\[收起部分\]', page_text_all)
            if intro_match:
                content = intro_match.group(1).strip()
            else:
                intro_match2 = re.search(r'官方4K臻享\].*?\,(.*?)\s*\[收起部分\]', page_text_all)
                if intro_match2:
                    content = intro_match2.group(1).strip()

            if not content:
                intro_tag = soup.select_one('.detail-info .content, .vod-content, .detail-desc')
                if intro_tag:
                    content = intro_tag.get_text(strip=True)

            img = soup.select_one('.detail-cover img, .vod-img img, .module-info-poster img, .movie-post')
            if not img:
                all_imgs = soup.find_all('img')
                for i in all_imgs:
                    src = i.get('data-src') or i.get('src') or ''
                    if 'upload/vod' in src or 'baidu.com' in src:
                        img = i
                        break

            if img:
                pic = img.get('data-src') or img.get('src') or ''
                if pic and pic.startswith('//'):
                    pic = 'https:' + pic

            play_from, play_url = [], []

            source_labels = []
            tag_sources = soup.select('.anthology-tab .swiper-slide, .anthology-tab a, #tag a, .source-tab a, .playfrom a')
            for s in tag_sources:
                text = s.get_text(strip=True)
                if text and not text.startswith('(') and len(text) < 20:
                    badge = s.select_one('.badge')
                    if badge:
                        badge.decompose()
                        text = s.get_text(strip=True)
                    source_labels.append(text)

            if not source_labels:
                m = re.findall(r'自营[tyrwl]|至臻4k|蓝光', page_text)
                if m:
                    source_labels = list(dict.fromkeys(m))

            play_pattern = self._build_play_pattern()
            play_path_key = '/play/' if '/play/' in play_pattern else '/itrade/'

            play_boxes = soup.select('#playsx, .play-list-box, .anthology-list-box, .anthology')
            if play_boxes:
                for idx, box in enumerate(play_boxes):
                    source_name = source_labels[idx] if idx < len(source_labels) else f"线路{idx + 1}"
                    ep_tags = box.select(f'li a, a[href*="{play_path_key}"]')
                    eps = []
                    for a in ep_tags:
                        ep_name = a.get_text(strip=True)
                        ep_href = a.get('href', '')
                        if ep_href and play_path_key in ep_href:
                            ep_link = self.host + ep_href if ep_href.startswith('/') else ep_href
                            eps.append(f"{ep_name}${ep_link}")
                    if eps:
                        eps.reverse()
                        play_from.append(source_name)
                        play_url.append('#'.join(eps))

            if not play_url:
                play_links = soup.find_all('a', href=re.compile(play_pattern))
                if play_links:
                    source_map = {}
                    for a in play_links:
                        href = a.get('href', '')
                        m = re.search(play_pattern, href)
                        if m:
                            sid = m.group(1)
                            ep_num = m.group(2)
                            ep_name = a.get_text(strip=True)
                            ep_link = self.host + href if href.startswith('/') else href
                            if sid not in source_map:
                                source_map[sid] = []
                            source_map[sid].append((ep_num, f"{ep_name}${ep_link}"))

                    for idx, sid in enumerate(sorted(source_map.keys())):
                        source_name = source_labels[idx] if idx < len(source_labels) else f"线路{idx + 1}"
                        eps = source_map[sid]
                        eps.sort(key=lambda x: int(x[0]))
                        eps.reverse()
                        play_from.append(source_name)
                        play_url.append('#'.join([ep[1] for ep in eps]))

            if not play_url:
                play_from.append("默认线路")
                default_play = f"{self.host}/play/{did}-1-1.html" if self.site_type != "zform" else f"{self.host}/itrade/{did}-1-1.html"
                play_url.append(f"播放${default_play}")

            paired = list(zip(play_from, play_url))
            paired.sort(key=lambda x: 0 if x[0].startswith('自营') else 1)
            play_from, play_url = zip(*paired) if paired else ([], [])
            play_from, play_url = list(play_from), list(play_url)

            return {'list': [{
                "vod_id": did,
                "vod_name": name,
                "vod_pic": pic,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": content,
                "vod_remarks": state,
                "vod_year": year,
                "vod_area": area,
                "vod_play_from": '$$$'.join(play_from),
                "vod_play_url": '$$$'.join(play_url)
            }]}
        except Exception as e:
            print(f"[{self.name}] 错误: 详情解析失败 - {e}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            res = self.session.get(id, headers=self.headers, timeout=15)
            text_json = re.findall(r'var player_aaaa=(.*?)</script>', res.text)
            if text_json:
                player_data = json.loads(text_json[0])

                durl = player_data.get('url', '')
                encrypt = player_data.get('encrypt', 0)
                from_flag = player_data.get('from', '')

                if encrypt == 1:
                    durl = urllib.parse.unquote(durl)
                elif encrypt == 2:
                    durl = urllib.parse.unquote(durl)
                    durl = base64.b64decode(durl).decode('utf-8')
                    durl = urllib.parse.unquote(durl)

                if self.config.get("has_parse", False) and from_flag in PARSE_MAP:
                    parse_url = PARSE_MAP[from_flag] + durl
                    return {'parse': 1, 'url': parse_url}

                return {'parse': 0, 'url': durl}

            return {'parse': 0, 'url': ''}
        except Exception as e:
            print(f"[{self.name}] 错误: 播放解析失败 - {e}")
            return {'parse': 0, 'url': ''}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
            search_url = self.config.get("search_url", "/cupfox-search/-------------.html")
            search_param = self.config.get("search_param", "wd")

            url = f"{self.host}{search_url}"
            params = {search_param: key}

            if search_url == "/index.php":
                params['m'] = 'vod-search'
                if page > 1:
                    params['page'] = page
            else:
                params['page'] = page

            res = self.session.get(url, params=params, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            videos = self._parse_list(soup)

            return {'list': videos, 'page': page, 'pagecount': page + 1 if videos else page,
                    'limit': 24, 'total': 999 if videos else 0}
        except Exception as e:
            print(f"[{self.name}] 错误: 搜索失败 - {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 24, 'total': 0}

    def isVideo(self, content):
        return True


if __name__ == '__main__':
    spider = Spider()
    spider.init("https://www.cd-zj.com")

    print("=" * 60)
    print(f"站点: {spider.host}")
    print(f"类型: {spider.site_type}")
    print(f"名称: {spider.getName()}")
    print("=" * 60)

    print("\n【首页测试】")
    result = spider.homeContent(False)
    print(f"分类数: {len(result['class'])}")
    print(f"推荐数: {len(result.get('list', []))}")
    for c in result['class']:
        print(f"  - {c['type_name']} ({c['type_id']})")

    print("\n【分类测试 - 电影】")
    result = spider.categoryContent(tid="1", pg="1", filter=False, extend={})
    print(f"结果数: {len(result['list'])}")
    if result['list']:
        v = result['list'][0]
        print(f"  第一个: {v['vod_name']} (id={v['vod_id']})")
