# coding = utf-8
#!/usr/bin/python

from urllib.parse import unquote
from urllib.parse import quote
from base.spider import Spider
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import requests
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://api.bilibili.com"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
    'Referer': 'https://search.bilibili.com',
    'cookie': 'bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDgxODAyOTMsImlhdCI6MTc0NzkyMTAzMywicGx0IjotMX0.ZfghPjVRcNtRwu_40_NbkLYZYaZd2r5YgjGNjPy4MV8'
}
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
    'Referer': 'https://www.bilibili.com',
}


class Spider(Spider):
    global xurl
    global headerx
    global headers

    def getName(self):
        return "美食"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [
            {"type_id": "美食", "type_name": "美食"},
            {"type_id": "披萨", "type_name": "披萨"},
            {"type_id": "火锅", "type_name": "火锅"},
            {"type_id": "烧烤", "type_name": "烧烤"},
            {"type_id": "烤鱼", "type_name": "烤鱼"},
            {"type_id": "海鲜", "type_name": "海鲜"},
            {"type_id": "川菜", "type_name": "川菜"},
            {"type_id": "湘菜", "type_name": "湘菜"},
            {"type_id": "鲁菜", "type_name": "鲁菜"},
            {"type_id": "苏菜", "type_name": "苏菜"},
            {"type_id": "闽菜", "type_name": "闽菜"},
            {"type_id": "粤菜", "type_name": "粤菜"},
            {"type_id": "浙菜", "type_name": "浙菜"},
            {"type_id": "徽菜", "type_name": "徽菜"},
            {"type_id": "东北菜", "type_name": "东北菜"},
            {"type_id": "京菜", "type_name": "京菜"},
            {"type_id": "津菜", "type_name": "津菜"},
            {"type_id": "冀菜", "type_name": "冀菜"},
            {"type_id": "豫菜", "type_name": "豫菜"},
            {"type_id": "鄂菜", "type_name": "鄂菜"},
            {"type_id": "本帮菜", "type_name": "本帮菜"},
            {"type_id": "客家菜", "type_name": "客家菜"},
            {"type_id": "赣菜", "type_name": "赣菜"},
            {"type_id": "凉菜", "type_name": "凉菜"},
            {"type_id": "蒸菜", "type_name": "蒸菜"},
            {"type_id": "日料", "type_name": "日料"},
            {"type_id": "韩餐", "type_name": "韩餐"},
            {"type_id": "泰国菜", "type_name": "泰国菜"},
            {"type_id": "法国菜", "type_name": "法国菜"},
            {"type_id": "意大利菜", "type_name": "意大利菜"},
            {"type_id": "德国菜", "type_name": "德国菜"},
            {"type_id": "西班牙菜", "type_name": "西班牙菜"},
            {"type_id": "希腊菜", "type_name": "希腊菜"},
            {"type_id": "土耳其菜", "type_name": "土耳其菜"},
            {"type_id": "阿拉伯菜", "type_name": "阿拉伯菜"},
            {"type_id": "中亚菜", "type_name": "中亚菜"},
            {"type_id": "素食", "type_name": "素食"},
            {"type_id": "点心", "type_name": "点心"},
            {"type_id": "面食", "type_name": "面食"},
            {"type_id": "小吃", "type_name": "小吃"},
            {"type_id": "汉堡", "type_name": "汉堡"},
            {"type_id": "早餐", "type_name": "早餐"},
            {"type_id": "下午茶", "type_name": "下午茶"},
            {"type_id": "夜宵", "type_name": "夜宵"},
            {"type_id": "甜品", "type_name": "甜品"},
            {"type_id": "烘焙", "type_name": "烘焙"},
            {"type_id": "饮品", "type_name": "饮品"},
            {"type_id": "咖啡", "type_name": "咖啡"},
            {"type_id": "奶茶", "type_name": "奶茶"}
        ]}
        return result

    def homeVideoContent(self):
        pass

    def format_views(self, num):
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        else:
            return str(num)

    def format_number(self, num):
        try:
            num = int(num)
            if num >= 100000000:
                return f"{num / 100000000:.1f}亿"
            elif num >= 10000:
                return f"{num / 10000:.1f}万"
            else:
                return str(num)
        except:
            return str(num)

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        keyword = cid

        url = f'{xurl}/x/web-interface/wbi/search/type?search_type=video&__refresh__=true&page={pg}&page_size=42&keyword={keyword}'
        res = requests.get(url=url, headers=headers)
        res.encoding = "utf-8"
        kjson = json.loads(res.text)
        for i in kjson['data']['result']:
            if str(i['bvid']) == '':
                continue
            duration = i.get('duration', 0)
            if duration < 1800:
                continue
            id = str(i['bvid'])
            name = i['title']
            pic = i['pic']
            if 'http' not in pic:
                pic = 'http:' + pic
            else:
                pic = pic
            remark = i['play']
            num_str = str(remark).strip()

            num = float(num_str)
            if num >= 100_000_000:
                remarks = f"{num / 100_000_000:.1f}亿播放量"
            elif num >= 10_000:
                remarks = f"{num / 10_000:.1f}万播放量"
            else:
                remarks = f"{num:.1f}播放量"

            video = {
                "vod_id": id,
                "vod_name": name.replace('<em class="keyword">', '').replace('</em>', ''),
                "vod_pic": pic,
                "vod_remarks": remarks
            }
            videos.append(video)

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        result = {}
        videos = []
        did = ids[0]
        url = f'https://www.bilibili.com/video/{did}'
        res = requests.get(url=url, headers=headerx)
        res.encoding = "utf-8"
        res_text = res.text

        start_str, end_str = 'window.__INITIAL_STATE__=', '}};'
        s_idx = res_text.find(start_str)
        if s_idx > -1:
            s_idx += len(start_str)
            e_idx = res_text.find(end_str, s_idx)
            if e_idx > -1:
                kjson_text = res_text[s_idx:e_idx] + '}}'
        kjson = json.loads(kjson_text)

        video_data = kjson.get('videoData', {})
        name = video_data.get('title', '未知标题')
        remarks = video_data.get('tname', '')
        director = video_data.get('owner', {}).get('name', '未知作者')
        content = video_data.get('desc', '')

        stat = video_data.get('stat', {})
        view_count = stat.get('view', 0)
        danmaku_count = stat.get('danmaku', 0)
        reply_count = stat.get('reply', 0)
        favorite_count = stat.get('favorite', 0)
        coin_count = stat.get('coin', 0)
        share_count = stat.get('share', 0)
        like_count = stat.get('like', 0)

        pubdate = video_data.get('pubdate', 0)
        if pubdate:
            pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pubdate))
        else:
            pub_time = "未知时间"

        owner = video_data.get('owner', {})
        up_name = owner.get('name', '')
        up_face = owner.get('face', '')
        up_mid = owner.get('mid', '')

        detail_info = f"视频简介：{content}\n\n"
        detail_info += f"▷ 播放量：{self.format_number(view_count)}\n"
        detail_info += f"▷ 弹幕数：{self.format_number(danmaku_count)}\n"
        detail_info += f"▷ 点赞数：{self.format_number(like_count)}\n"
        detail_info += f"▷ 投币数：{self.format_number(coin_count)}\n"
        detail_info += f"▷ 收藏数：{self.format_number(favorite_count)}\n"
        detail_info += f"▷ 评论数：{self.format_number(reply_count)}\n"
        detail_info += f"▷ 分享数：{self.format_number(share_count)}\n"
        detail_info += f"▷ 发布时间：{pub_time}\n"
        detail_info += f"▷ UP主：{up_name}\n"
        detail_info += f"▷ 分区：{remarks}\n"

        pic_url = video_data.get('pic', '')
        if pic_url and 'http' not in pic_url:
            pic_url = 'http:' + pic_url

        play_url = ""
        available_video_list = kjson.get('availableVideoList', [])
        if available_video_list and len(available_video_list) > 0:
            for i in available_video_list[0]['list']:
                play_url += i['title'] + '$' + f'https://www.bilibili.com/video/{did}?p=' + str(i['p']) + '#'
            play_url = play_url[:-1]
        else:
            play_url = f"正片$https://www.bilibili.com/video/{did}"

        related_play_url = ""
        aid = video_data.get('aid', '')
        if aid:
            try:
                related_api = f"https://api.bilibili.com/x/web-interface/archive/related?aid={aid}"
                related_res = requests.get(related_api, headers=headerx).json()

                if related_res.get("code") == 0:
                    related_data = related_res.get("data", [])
                    for i, related_video in enumerate(related_data[:99999]):
                        related_duration = related_video.get('duration', 0)
                        if related_duration < 1800:
                            continue
                        related_title = related_video.get("title", f"相关视频{i+1}")
                        related_bvid = related_video.get("bvid", "")

                        if not related_title or related_title == f"相关视频{i+1}":
                            related_title = f"相关推荐{i+1}"

                        related_title = related_title.replace('#', '﹟').replace('$', '﹩')

                        related_stat = related_video.get('stat', {})
                        related_views = related_stat.get('view', 0)

                        if related_bvid:
                            related_video_url = f"https://www.bilibili.com/video/{related_bvid}"
                            related_play_url += f"{related_title}【{self.format_number(related_views)}】${related_video_url}#"

                    related_play_url = related_play_url.rstrip("#")

            except Exception:
                pass

        if related_play_url:
            vod_play_from = "美食$$$相关推荐"
            vod_play_url = f"{play_url}$$${related_play_url}"
        else:
            vod_play_from = '美食'
            vod_play_url = play_url

        remark_info = f"播放:{self.format_number(view_count)} · 弹幕:{self.format_number(danmaku_count)} · 点赞:{self.format_number(like_count)} · 投币:{self.format_number(coin_count)}"

        video = {
            "vod_id": did,
            "vod_name": name,
            "vod_pic": pic_url,
            "vod_actor": f"UP主：{up_name}",
            "vod_director": director,
            "vod_content": detail_info,
            "vod_remarks": remark_info,
            "vod_year": pub_time.split('-')[0] if pub_time != "未知时间" else '',
            "vod_area": remarks,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }
        videos.append(video)

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            from urllib.parse import parse_qs, urlparse

            if "bilibili.com/video/" in id:
                match = re.search(r'bilibili\.com/video/(BV[0-9A-Za-z]+)', id)
                if match:
                    bvid = match.group(1)
                else:
                    parsed = urlparse(id)
                    params = parse_qs(parsed.query)
                    if 'bvid' in params:
                        bvid = params['bvid'][0]
                    else:
                        path_parts = parsed.path.split('/')
                        for part in path_parts:
                            if part.startswith('BV'):
                                bvid = part
                                break
                        else:
                            bvid = None
            else:
                bvid = None

            cid = None
            if bvid:
                try:
                    video_api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                    video_res = requests.get(video_api, headers=headerx).json()
                    if video_res.get("code") == 0:
                        cid = video_res["data"].get("cid")
                except:
                    pass

            danmaku_url = ""
            if cid:
                danmaku_url = f"https://183933.xyz/dm/dm.php?url=https://www.bilibili.com/video/{bvid}"

            player_config = {
                'jx': 1,
                'parse': 1,
                'url': id,
                'header': headerx
            }

            if danmaku_url:
                player_config['danmaku'] = danmaku_url

            return player_config

        except Exception:
            return {'jx': 1, 'parse': 1, 'url': id, 'header': headerx}

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []
        if not page:
            page = 1
        url = f'{xurl}/x/web-interface/wbi/search/type?search_type=video&__refresh__=true&page={page}&page_size=42&keyword={key}'
        res = requests.get(url=url, headers=headers)
        res.encoding = "utf-8"
        kjson = json.loads(res.text)
        for i in kjson['data']['result']:
            if str(i['bvid']) == '':
                continue
            duration = i.get('duration', 0)
            if duration < 1800:
                continue
            id = str(i['bvid'])
            name = i['title']
            pic = i['pic']
            if 'http' not in pic:
                pic = 'http:'+pic
            else:
                pic = pic
            remark = i['play']
            num_str = str(remark).strip()

            num = float(num_str)
            if num >= 100_000_000:
                remarks = f"{num / 100_000_000:.1f}亿播放量"
            elif num >= 10_000:
                remarks = f"{num / 10_000:.1f}万播放量"
            else:
                remarks = f"{num:.1f}播放量"

            video = {
                "vod_id": id,
                "vod_name": name.replace('<em class="keyword">', '').replace('</em>', ''),
                "vod_pic": pic,
                "vod_remarks": remarks
            }
            videos.append(video)

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None
