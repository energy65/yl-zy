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
        self.host = "https://www.china-itrade.com"
        self.name = "枫叶影视2"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Referer': f'{self.host}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def getName(self):
        return "🍁枫叶影视2"

    def init(self, extend):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "5", "type_name": "出圈短剧"},
            {"type_id": "search_tencent", "type_name": "腾讯vip"},
            {"type_id": "search_youku", "type_name": "优酷vip"},
            {"type_id": "search_bilibili", "type_name": "b站vip"},
        ]

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

        return {
            "class": classes,
            "filters": filter_dict
        }

    def homeVideoContent(self):
        return {'list': []}

    def _parse_list(self, soup):
        videos = []
        seen = set()

        items = soup.select('.movie-list-item')
        if not items:
            all_a = soup.find_all('a', href=re.compile(r'/zform/\d+\.html'))
            temp_map = {}
            for a in all_a:
                href = a.get('href', '')
                m = re.search(r'/zform/(\d+)\.html', href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                if vid not in temp_map:
                    temp_map[vid] = {'vod_id': vid, 'vod_name': '', 'vod_pic': '', 'vod_remarks': ''}

                img = a.find('img')
                if img and not temp_map[vid]['vod_pic']:
                    pic = img.get('data-src') or img.get('src') or ''
                    if pic and pic.startswith('//'):
                        pic = 'https:' + pic
                    temp_map[vid]['vod_pic'] = pic

                parent = a.parent
                if parent and 'movie-info' in ' '.join(parent.get('class', [])):
                    temp_map[vid]['vod_name'] = a.get_text(strip=True)
                else:
                    note_span = a.select_one('.pic-text b, .pic-text1 b')
                    if note_span and not temp_map[vid]['vod_remarks']:
                        temp_map[vid]['vod_remarks'] = note_span.get_text(strip=True)

            for vid, data in temp_map.items():
                if data['vod_name'] and data['vod_pic']:
                    videos.append(data)
                    seen.add(vid)
            return videos

        for item in items:
            try:
                link = item.select_one('.movie-info a[href*="/zform/"]')
                if not link:
                    all_links = item.find_all('a', href=re.compile(r'/zform/\d+\.html'))
                    for a in all_links:
                        parent = a.parent
                        if parent and 'movie-info' in ' '.join(parent.get('class', [])):
                            link = a
                            break
                    if not link and all_links:
                        link = all_links[0]
                if not link:
                    continue

                href = link.get('href', '')
                m = re.search(r'/zform/(\d+)\.html', href)
                if not m:
                    continue

                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)

                name = link.get_text(strip=True)

                pic = ''
                img = item.select_one('img.movie-post, img')
                if img:
                    pic = img.get('data-src') or img.get('src') or ''
                    if pic and pic.startswith('//'):
                        pic = 'https:' + pic

                note = ''
                note_tag = item.select_one('.pic-text b')
                if not note_tag:
                    note_tag = item.select_one('.pic-text1 b')
                if note_tag:
                    note = note_tag.get_text(strip=True)

                if not name:
                    title_div = item.select_one('.movie-title')
                    if title_div:
                        name = title_div.get_text(strip=True)

                if not name:
                    continue

                videos.append({
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": note
                })
            except Exception as e:
                print(f"[{self.name}] 错误: 列表解析失败 - {e}")
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

        if class_name:
            class_name = urllib.parse.quote(class_name)
        if area:
            area = urllib.parse.quote(area)

        if area or class_name or year or by:
            url = f"{self.host}/zform-list/{tid}-{area}-{class_name}-----{by}---{year}-{page}---.html"
        else:
            url = f"{self.host}/zform-list/{tid}--------{page}---.html"

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
                url = f"{self.host}/zform-list/{source_tid}--------{p}---.html"
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
            url = f"{self.host}/zform/{did}.html"
            res = self.session.get(url, headers=self.headers, timeout=8)
            text = res.text.lower()
            return '4k' in text or '臻' in res.text
        except:
            return False

    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else str(ids)
        try:
            url = f"{self.host}/zform/{did}.html"
            res = self.session.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            name = ""
            state = ""
            actor = ""
            director = ""
            year = ""
            area = ""
            content = ""
            pic = ""

            title_tag = soup.select_one('title')
            if title_tag:
                m = re.search(r'《(.*?)》', title_tag.get_text(strip=True))
                if m:
                    name = m.group(1)

            page_text = soup.get_text(separator='|', strip=True)
            lines = [x.strip() for x in page_text.split('|') if x.strip()]

            for i, line in enumerate(lines):
                if line.startswith('主演:') or line.startswith('主演：'):
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
                elif line.startswith('首播:') or line.startswith('首播：'):
                    m = re.search(r'(\d{4})', line)
                    if m:
                        year = m.group(1)
                    elif i + 1 < len(lines):
                        m = re.search(r'(\d{4})', lines[i + 1])
                        if m:
                            year = m.group(1)
                elif line.startswith('更新:') or line.startswith('更新：'):
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
                m = re.search(r'主演[:：]\s*(.*?)(?:\s*\|)', page_text)
                if m:
                    actor = m.group(1).strip('| ')

            if not director:
                m = re.search(r'导演[:：]\s*(.*?)(?:\s*\|)', page_text)
                if m:
                    director = m.group(1).strip('| ')

            if not year:
                m = re.search(r'首播[:：]\s*(\d{4})', page_text)
                if m:
                    year = m.group(1)

            if not state:
                m = re.search(r'更新[:：]\s*(.*?)(?:\s*\[|$)', page_text)
                if m:
                    state = m.group(1).strip('| ')

            intro_match = re.search(r'收起部分\].*?\,(.*?)\s*\[收起部分\]', page_text)
            if intro_match:
                content = intro_match.group(1).strip()
            else:
                intro_match2 = re.search(r'官方4K臻享\].*?\,(.*?)\s*\[收起部分\]', page_text)
                if intro_match2:
                    content = intro_match2.group(1).strip()

            img = soup.select_one('.movie-post, img.movie-post')
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
            tag_sources = soup.select('#tag a, .source-tab a, .playfrom a')
            for s in tag_sources:
                source_labels.append(s.get_text(strip=True))

            if not source_labels:
                m = re.findall(r'自营[tyrwl]', page_text)
                if m:
                    source_labels = list(dict.fromkeys(m))

            play_boxes = soup.select('#playsx, .play-list-box, .anthology-list-box')
            if play_boxes:
                for idx, box in enumerate(play_boxes):
                    source_name = source_labels[idx] if idx < len(source_labels) else f"线路{idx + 1}"
                    ep_tags = box.select('li a, a[href*="/itrade/"]')
                    eps = []
                    for a in ep_tags:
                        ep_name = a.get_text(strip=True)
                        ep_href = a.get('href', '')
                        if ep_href and '/itrade/' in ep_href:
                            ep_link = self.host + ep_href if ep_href.startswith('/') else ep_href
                            eps.append(f"{ep_name}${ep_link}")
                    if eps:
                        eps.reverse()
                        play_from.append(source_name)
                        play_url.append('#'.join(eps))

            if not play_url:
                play_links = soup.find_all('a', href=re.compile(r'/itrade/\d+-\d+-\d+\.html'))
                if play_links:
                    source_map = {}
                    for a in play_links:
                        href = a.get('href', '')
                        m = re.search(r'/itrade/\d+-(\d+)-(\d+)\.html', href)
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
                play_url.append(f"播放${self.host}/itrade/{did}-1-1.html")

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

                parse_map = {
                    'JD4K': 'https://fgsrg.hzqingshan.com/player/?url=',
                    'JD2K': 'https://fgsrg.hzqingshan.com/player/?url=',
                    'YYNB': 'https://zzrs.mfdyvip.com/player/?url=',
                }

                if from_flag in parse_map:
                    parse_url = parse_map[from_flag] + durl
                    return {'parse': 1, 'url': parse_url}

                return {'parse': 0, 'url': durl}

            return {'parse': 0, 'url': ''}
        except Exception as e:
            print(f"[{self.name}] 错误: 播放解析失败 - {e}")
            return {'parse': 0, 'url': ''}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
            search_url = f'{self.host}/zform-search/-------------.html'
            params = {'wd': key, 'page': page}

            res = self.session.get(search_url, params=params, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')

            videos = self._parse_list(soup)

            return {'list': videos, 'page': page, 'pagecount': page + 1 if videos else page,
                    'limit': 24, 'total': 999 if videos else 0}
        except Exception as e:
            print(f"[{self.name}] 错误: 搜索失败 - {e}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 24, 'total': 0}


if __name__ == '__main__':
    spider = Spider()
    spider.init("")

    print("=================== 分类测试 ===================")
    result = spider.categoryContent(tid="1", pg="1", filter=False, extend={})
    print(f"分类结果数量: {len(result['list'])}")
    if result['list']:
        print(json.dumps(result['list'][0], ensure_ascii=False, indent=2))

    print("\n=================== 详情页测试 ===================")
    if result['list']:
        vod_id = result['list'][0]['vod_id']
        result = spider.detailContent([vod_id])
        print(json.dumps(result, ensure_ascii=False, indent=2)[:1000] + "\n...")

    print("\n=================== 播放测试 ===================")
    if result['list']:
        v = result['list'][0]
        play_urls = v['vod_play_url'].split('$$$')
        if play_urls and play_urls[0]:
            first_ep = play_urls[0].split('#')[0]
            ep_name, ep_url = first_ep.split('$')
            print(f"测试集数: {ep_name}")
            play_result = spider.playerContent("", ep_url, [])
            print(f"播放地址: {play_result.get('url', '')[:80]}...")

    print("\n=================== 搜索测试 ===================")
    result = spider.searchContent("流浪地球", False, "1")
    print(f"搜索结果数量: {len(result['list'])}")
    if result['list']:
        print(json.dumps(result['list'][0], ensure_ascii=False, indent=2))
