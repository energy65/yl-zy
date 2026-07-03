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


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.session = requests.Session()
        self.session.verify = False
        self.session.mount('https://', TLSAdapter())
        self.host = "https://www.cd-zj.com"
        self.name = "枫叶4K"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def getName(self):
        return "🍁枫叶4K"

    def init(self, extend):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "5", "type_name": "热门短剧"},
        ]

        try:
            res = self.session.get(self.host, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            videos = self._parse_list(soup)

            return {
                'class': classes,
                'list': videos
            }
        except Exception as e:
            print(f"[{self.name}] 错误: 首页爬取失败 - {e}")
            return {'class': classes, 'list': []}

    def homeVideoContent(self):
        return {'list': []}

    def _parse_list(self, soup):
        videos = []
        seen = set()
        items = soup.select('.public-list-box.public-pic-b')
        if not items:
            items = soup.select('.public-list-box.search-box')
        if not items:
            items = soup.select('a[href*="/detail/"]')
            for a in items:
                href = a.get('href', '')
                m = re.search(r'/detail/(\d+)\.html', href)
                if not m:
                    continue
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)

                title = a.get('title', '').strip()
                if not title:
                    title = a.get_text(strip=True)
                if not title or len(title) < 2:
                    continue

                img = a.select_one('img')
                pic = ''
                if img:
                    pic = img.get('data-src') or img.get('src') or ''

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                })
        else:
            for item in items:
                try:
                    a = item.select_one('a[href*="/detail/"]')
                    href = a.get('href', '') if a else ''
                    m = re.search(r'/detail/(\d+)\.html', href)
                    if not m:
                        continue
                    vod_id = m.group(1)
                    if vod_id in seen:
                        continue
                    seen.add(vod_id)

                    title = a.get('title', '').strip() if a else ''
                    if not title:
                        title_a = item.select_one('.time-title')
                        if title_a:
                            title = title_a.get_text(strip=True)
                    if not title:
                        thumb_a = item.select_one('.thumb-txt a')
                        if thumb_a:
                            title = thumb_a.get_text(strip=True)

                    img = item.select_one('img')
                    pic = ''
                    if img:
                        pic = img.get('data-src') or img.get('src') or ''
                    if not pic:
                        cover = item.select_one('.cover')
                        if cover:
                            style = cover.get('style', '')
                            m2 = re.search(r'url\((.*?)\)', style)
                            if m2:
                                pic = m2.group(1).strip('\'"')

                    sub = item.select_one('.public-list-subtitle')
                    actor = ''
                    if sub:
                        actor = sub.get_text(strip=True)
                    if not actor:
                        thumb_actor = item.select_one('.thumb-actor')
                        if thumb_actor:
                            actor = thumb_actor.get_text(strip=True).replace('导演：', '').replace('主演：', '')

                    if not title:
                        continue

                    videos.append({
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_actor": actor,
                    })
                except Exception as e:
                    continue
        return videos

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)

        vip_categories = {
            'search_tencent': '2',
            'search_youku': '1',
            'search_bilibili': '4',
        }

        if tid in vip_categories:
            source_tid = vip_categories[tid]
            return self._vip_category(source_tid, page)

        extend = extend or {}
        area = extend.get('area', '')
        by = extend.get('by', '')
        class_name = extend.get('class', '')
        year = extend.get('year', '')

        if page == 1:
            url = f"{self.host}/type/{tid}.html"
        else:
            url = f"{self.host}/type/{tid}-{page}.html"

        try:
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
                if p == 1:
                    url = f"{self.host}/type/{source_tid}.html"
                else:
                    url = f"{self.host}/type/{source_tid}-{p}.html"
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
            url = f"{self.host}/detail/{did}.html"
            res = self.session.get(url, headers=self.headers, timeout=8)
            text = res.text.lower()
            return '4k' in text or '臻' in res.text
        except:
            return False

    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else str(ids)
        try:
            url = f"{self.host}/detail/{did}.html"
            res = self.session.get(url, headers=self.headers, timeout=15)
            page_text = res.text
            soup = BeautifulSoup(page_text, 'html.parser')

            name = ''
            title_tag = soup.select_one('h1')
            if title_tag:
                name = title_tag.get_text(strip=True)
            if not name:
                detail_info = soup.select_one('.detail-info')
                if detail_info:
                    name = detail_info.get_text(strip=True).split('202')[0].split('201')[0].split('类型')[0].strip()
            if not name:
                m = re.search(r'《(.*?)》', page_text)
                if m:
                    name = m.group(1)

            actor = ''
            director = ''
            content = ''
            year = ''
            area = ''
            state = ''

            detail_info = soup.select_one('.detail-info')
            if detail_info:
                info_text = detail_info.get_text(separator='\n', strip=True)
                lines = info_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('演员：') or line.startswith('演员:'):
                        actor = line[3:].strip()
                    elif line.startswith('类型：') or line.startswith('类型:'):
                        pass
                    elif line.startswith('更新'):
                        state = line[2:].strip() if len(line) > 2 else ''
                    elif re.match(r'^\d{4}', line):
                        m = re.search(r'(\d{4})', line)
                        if m:
                            year = m.group(1)

            if not actor:
                m = re.search(r'演员[：:]\s*([^\n]+)', page_text)
                if m:
                    actor = m.group(1).strip()

            if not director:
                m = re.search(r'导演[：:]\s*([^\n]+)', page_text)
                if m:
                    director = m.group(1).strip()

            if not state:
                m = re.search(r'更新至(\d+集|\d+话)', page_text)
                if m:
                    state = '更新至' + m.group(1)
                elif '已完结' in page_text:
                    state = '已完结'

            if not year:
                m = re.search(r'(\d{4})年?代?[内地上映台湾香港美国日本韩国]', page_text)
                if m:
                    year = m.group(1)

            img = soup.select_one('img.lozad, img.lazy, img[data-src*="upload"]')
            if not img:
                all_imgs = soup.find_all('img')
                for i in all_imgs:
                    src = i.get('data-src') or i.get('src') or ''
                    if 'upload/vod' in src or 'baidu.com' in src:
                        img = i
                        break

            pic = ''
            if img:
                pic = img.get('data-src') or img.get('src') or ''

            play_from, play_url = [], []

            source_labels = []
            tag_sources = soup.select('.anthology-tab .swiper-slide, .anthology-tab a')
            for s in tag_sources:
                text = s.get_text(strip=True)
                if text and not text.startswith('(') and len(text) < 20:
                    source_labels.append(text)

            if not source_labels:
                m = re.findall(r'自营[tyrwl]|至臻4k|蓝光', page_text)
                if m:
                    source_labels = list(dict.fromkeys(m))

            play_boxes = soup.select('#playsx, .play-list-box, .anthology-list-box, .anthology')
            if play_boxes:
                for idx, box in enumerate(play_boxes):
                    source_name = source_labels[idx] if idx < len(source_labels) else f"线路{idx + 1}"
                    ep_tags = box.select('li a, a[href*="/play/"]')
                    eps = []
                    for a in ep_tags:
                        ep_name = a.get_text(strip=True)
                        ep_href = a.get('href', '')
                        if ep_href and '/play/' in ep_href:
                            ep_link = self.host + ep_href if ep_href.startswith('/') else ep_href
                            eps.append(f"{ep_name}${ep_link}")
                    if eps:
                        eps.reverse()
                        play_from.append(source_name)
                        play_url.append('#'.join(eps))

            if not play_url:
                play_links = soup.find_all('a', href=re.compile(r'/play/\d+-\d+-\d+\.html'))
                if play_links:
                    source_map = {}
                    for a in play_links:
                        href = a.get('href', '')
                        m = re.search(r'/play/\d+-(\d+)-(\d+)\.html', href)
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
                play_url.append(f"播放${self.host}/play/{did}-1-1.html")

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

                if encrypt == 1:
                    durl = urllib.parse.unquote(durl)
                elif encrypt == 2:
                    durl = urllib.parse.unquote(durl)
                    durl = base64.b64decode(durl).decode('utf-8')
                    durl = urllib.parse.unquote(durl)

                play_from = player_data.get('from', '')
                if play_from in ['JD4K', 'JD2K', 'YYNB']:
                    parse_url = "https://fgsrg.hzqingshan.com/player/?url=" + durl
                    return {'parse': 1, 'url': parse_url}
                return {'parse': 0, 'url': durl}
            return {'parse': 0, 'url': ''}
        except Exception as e:
            print(f"[{self.name}] 错误: 播放解析失败 - {e}")
            return {'parse': 0, 'url': ''}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
            search_url = f'{self.host}/cupfox-search/-------------.html'
            params = {'wd': key, 'page': page}

            res = self.session.get(search_url, params=params, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            videos = self._parse_list(soup)

            return {'list': videos, 'page': page, 'pagecount': page + 1 if videos else page,
                    'limit': 24, 'total': 999 if videos else 0}
        except Exception as e:
            print(f"[{self.name}] 错误: 搜索失败 - {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 24, 'total': 0}

    def isVideo(self, content):
        return True
