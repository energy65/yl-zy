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
        return "宇宙太空"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [
            {"type_id": "宇宙太空科普纪录片", "type_name": "🌌 全部宇宙纪录片"},
            {"type_id": "宇宙的奇迹纪录片", "type_name": "宇宙的奇迹"},
            {"type_id": "宇宙时空之旅", "type_name": "宇宙时空之旅"},
            {"type_id": "宇宙有道理", "type_name": "宇宙有道理"},
            {"type_id": "了解宇宙是如何运行的", "type_name": "了解宇宙如何运行"},
            {"type_id": "行星纪录片", "type_name": "行星 The Planets"},
            {"type_id": "太阳系的奇迹", "type_name": "太阳系的奇迹"},
            {"type_id": "星际旅行指南", "type_name": "星际旅行指南"},
            {"type_id": "宇宙千年", "type_name": "宇宙千年"},
            {"type_id": "与摩根弗里曼一起穿越虫洞", "type_name": "穿越虫洞"},
            {"type_id": "霍金宇宙", "type_name": "霍金宇宙"},
            {"type_id": "哈勃的宇宙", "type_name": "哈勃的宇宙"},
            {"type_id": "BBC宇宙纪录片", "type_name": "BBC宇宙系列"},
            {"type_id": "国家地理宇宙纪录片", "type_name": "国家地理宇宙"},
            {"type_id": "Discovery宇宙纪录片", "type_name": "探索频道宇宙"},
            {"type_id": "太阳系八大行星", "type_name": "☀️ 太阳系八大行星"},
            {"type_id": "太阳纪录片", "type_name": "太阳"},
            {"type_id": "水星纪录片", "type_name": "水星"},
            {"type_id": "金星纪录片", "type_name": "金星"},
            {"type_id": "地球纪录片", "type_name": "地球"},
            {"type_id": "火星纪录片", "type_name": "🚀 火星"},
            {"type_id": "木星纪录片", "type_name": "木星"},
            {"type_id": "土星纪录片", "type_name": "🪐 土星"},
            {"type_id": "天王星海王星", "type_name": "天王星·海王星"},
            {"type_id": "冥王星纪录片", "type_name": "冥王星"},
            {"type_id": "月球纪录片", "type_name": "🌙 月球"},
            {"type_id": "小行星彗星", "type_name": "☄️ 小行星彗星"},
            {"type_id": "星系纪录片", "type_name": "🌠 星系与星云"},
            {"type_id": "银河系纪录片", "type_name": "银河系"},
            {"type_id": "仙女座星系", "type_name": "仙女座星系"},
            {"type_id": "星云纪录片", "type_name": "星云"},
            {"type_id": "黑洞纪录片", "type_name": "⚫ 黑洞"},
            {"type_id": "虫洞纪录片", "type_name": "虫洞"},
            {"type_id": "暗物质暗能量", "type_name": "暗物质·暗能量"},
            {"type_id": "宇宙大爆炸纪录片", "type_name": "💥 宇宙起源"},
            {"type_id": "宇宙演化纪录片", "type_name": "宇宙演化"},
            {"type_id": "平行宇宙纪录片", "type_name": "平行宇宙"},
            {"type_id": "中国航天纪录片", "type_name": "🇨🇳 中国航天"},
            {"type_id": "中国空间站", "type_name": "中国空间站"},
            {"type_id": "神舟飞船纪录片", "type_name": "神舟飞船"},
            {"type_id": "嫦娥探月工程", "type_name": "嫦娥探月"},
            {"type_id": "天问一号火星", "type_name": "天问火星"},
            {"type_id": "北斗导航系统", "type_name": "北斗导航"},
            {"type_id": "国际空间站纪录片", "type_name": "国际空间站"},
            {"type_id": "SpaceX星舰", "type_name": "SpaceX星舰"},
            {"type_id": "哈勃望远镜纪录片", "type_name": "哈勃望远镜"},
            {"type_id": "詹姆斯韦伯望远镜", "type_name": "詹姆斯韦伯"},
            {"type_id": "中国天眼FAST", "type_name": "天眼FAST"},
            {"type_id": "外星生命UFO", "type_name": "👽 外星生命UFO"},
            {"type_id": "费米悖论", "type_name": "费米悖论"}
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

    def parse_duration(self, duration):
        try:
            if isinstance(duration, (int, float)):
                return int(duration)
            if isinstance(duration, str):
                parts = duration.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except:
            return 0

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
            duration = self.parse_duration(i.get('duration', 0))
            if duration < 600:
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
                        related_duration = self.parse_duration(related_video.get('duration', 0))
                        if related_duration < 600:
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
            vod_play_from = "宇宙太空$$$相关推荐"
            vod_play_url = f"{play_url}$$${related_play_url}"
        else:
            vod_play_from = '宇宙太空'
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
            duration = self.parse_duration(i.get('duration', 0))
            if duration < 600:
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
