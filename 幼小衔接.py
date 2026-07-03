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
        return "幼小衔接"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [
            {"type_id": "幼小衔接拼音", "type_name": "拼音启蒙"},
            {"type_id": "幼小衔接识字", "type_name": "识字启蒙"},
            {"type_id": "幼小衔接数学", "type_name": "数学思维"},
            {"type_id": "幼小衔接英语", "type_name": "英语启蒙"},
            {"type_id": "儿童专注力训练", "type_name": "专注力训练"},
            {"type_id": "幼小衔接着图说话", "type_name": "看图说话"},
            {"type_id": "幼小衔接国学", "type_name": "国学启蒙"},
            {"type_id": "儿童好习惯养成", "type_name": "好习惯养成"},
            {"type_id": "儿童安全教育", "type_name": "安全教育"},
            {"type_id": "儿童记忆力训练", "type_name": "记忆力训练"},
            {"type_id": "儿童观察力训练", "type_name": "观察力训练"},
            {"type_id": "儿童逻辑思维训练", "type_name": "逻辑思维"},
            {"type_id": "儿童硬笔书法入门", "type_name": "硬笔书法"},
            {"type_id": "少儿口才训练", "type_name": "口才表达"},
            {"type_id": "儿童唐诗宋词", "type_name": "唐诗宋词"},
            {"type_id": "成语故事动画", "type_name": "成语故事"},
            {"type_id": "三字经幼儿启蒙", "type_name": "三字经"},
            {"type_id": "弟子规儿童版", "type_name": "弟子规"},
            {"type_id": "百家姓儿童版", "type_name": "百家姓"},
            {"type_id": "千字文儿童版", "type_name": "千字文"},
            {"type_id": "幼小衔接凑十法", "type_name": "凑十法"},
            {"type_id": "幼小衔接破十法", "type_name": "破十法"},
            {"type_id": "幼小衔接加减法", "type_name": "加减法"},
            {"type_id": "儿童乘除法启蒙", "type_name": "乘除法"},
            {"type_id": "儿童认识时间", "type_name": "认识时间"},
            {"type_id": "儿童认识人民币", "type_name": "认识人民币"},
            {"type_id": "儿童图形认知", "type_name": "图形认知"},
            {"type_id": "儿童空间思维训练", "type_name": "空间思维"},
            {"type_id": "儿童英语自然拼读", "type_name": "自然拼读"},
            {"type_id": "儿童英语字母", "type_name": "英语字母"},
            {"type_id": "儿童英语单词", "type_name": "英语单词"},
            {"type_id": "儿童英语儿歌", "type_name": "英语儿歌"},
            {"type_id": "儿童英语启蒙动画", "type_name": "英语动画"},
            {"type_id": "拼音拼读训练", "type_name": "拼音拼读"},
            {"type_id": "拼音书写教学", "type_name": "拼音书写"},
            {"type_id": "整体认读音节教学", "type_name": "整体认读音节"},
            {"type_id": "声母韵母教学", "type_name": "声母韵母"},
            {"type_id": "汉字笔画笔顺教学", "type_name": "笔画笔顺"},
            {"type_id": "汉字偏旁部首教学", "type_name": "偏旁部首"},
            {"type_id": "幼儿常用汉字", "type_name": "常用汉字"},
            {"type_id": "儿童绘本故事", "type_name": "绘本故事"},
            {"type_id": "儿童睡前故事", "type_name": "睡前故事"},
            {"type_id": "儿童科普启蒙", "type_name": "科普启蒙"},
            {"type_id": "儿童艺术启蒙", "type_name": "艺术启蒙"}
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
            vod_play_from = "幼小衔接$$$相关推荐"
            vod_play_url = f"{play_url}$$${related_play_url}"
        else:
            vod_play_from = '幼小衔接'
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
