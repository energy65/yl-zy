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
        return "B站MV"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [
            {"type_id": "热门MV", "type_name": "热门MV"},
            {"type_id": "MV4K", "type_name": "4K超清MV"},
            {"type_id": "华语MV", "type_name": "华语MV"},
            {"type_id": "欧美MV", "type_name": "欧美MV"},
            {"type_id": "日韩MV", "type_name": "日韩MV"},
            {"type_id": "韩国女团MV", "type_name": "韩国女团"},
            {"type_id": "粤语MV", "type_name": "粤语MV"},
            {"type_id": "古风MV", "type_name": "古风MV"},
            {"type_id": "经典老歌MV", "type_name": "经典老歌"},
            {"type_id": "网红翻唱MV", "type_name": "网红翻唱"},
            {"type_id": "DJ舞曲MV", "type_name": "DJ舞曲"},
            {"type_id": "钢琴MV", "type_name": "钢琴曲"},
            {"type_id": "酷我音乐MV", "type_name": "酷我MV"},
            {"type_id": "酷狗音乐MV", "type_name": "酷狗MV"},
            {"type_id": "QQ音乐MV", "type_name": "QQ MV"},
            {"type_id": "咪咕音乐MV", "type_name": "咪咕MV"},
            {"type_id": "网易云音乐MV", "type_name": "网易云MV"},
            {"type_id": "artist_mv", "type_name": "歌手MV"},
            {"type_id": "KTV必点", "type_name": "KTV必点"},
        ]}
        return result

    def homeVideoContent(self):
        pass

    artist_list = [
        {'name': '周杰伦', 'keyword': '周杰伦MV4K', 'pic': 'https://i2.hdslb.com/bfs/face/74e791d80b3d44c5f2a9f1b6b8a6f3c2d1e0a9b.jpg'},
        {'name': '林俊杰', 'keyword': '林俊杰MV4K', 'pic': ''},
        {'name': '陈奕迅', 'keyword': '陈奕迅MV4K', 'pic': ''},
        {'name': '张学友', 'keyword': '张学友MV4K', 'pic': ''},
        {'name': '邓紫棋', 'keyword': '邓紫棋MV4K', 'pic': ''},
        {'name': '王菲', 'keyword': '王菲MV4K', 'pic': ''},
        {'name': '刘德华', 'keyword': '刘德华MV4K', 'pic': ''},
        {'name': '周深', 'keyword': '周深MV4K', 'pic': ''},
        {'name': '薛之谦', 'keyword': '薛之谦MV4K', 'pic': ''},
        {'name': '毛不易', 'keyword': '毛不易MV4K', 'pic': ''},
        {'name': '邓丽君', 'keyword': '邓丽君MV4K', 'pic': ''},
        {'name': '张国荣', 'keyword': '张国荣MV4K', 'pic': ''},
        {'name': 'Beyond', 'keyword': 'BeyondMV4K', 'pic': ''},
        {'name': 'Taylor Swift', 'keyword': 'TaylorSwiftMV4K', 'pic': ''},
        {'name': 'Adele', 'keyword': 'AdeleMV4K', 'pic': ''},
        {'name': '迈克尔杰克逊', 'keyword': 'MichaelJacksonMV4K', 'pic': ''},
        {'name': 'Blackpink', 'keyword': 'BlackpinkMV4K', 'pic': ''},
        {'name': '初音未来', 'keyword': '初音未来MV4K', 'pic': ''},
        {'name': '洛天依', 'keyword': '洛天依MV4K', 'pic': ''},
        {'name': '中岛美雪', 'keyword': '中岛美雪MV4K', 'pic': ''},
        {'name': '坂井泉水', 'keyword': '坂井泉水MV4K', 'pic': ''},
        {'name': '许嵩', 'keyword': '许嵩MV4K', 'pic': ''},
        {'name': '李荣浩', 'keyword': '李荣浩MV4K', 'pic': ''},
        {'name': '张靓颖', 'keyword': '张靓颖MV4K', 'pic': ''},
        {'name': '张惠妹', 'keyword': '张惠妹MV4K', 'pic': ''},
        {'name': '刘若英', 'keyword': '刘若英MV4K', 'pic': ''},
        {'name': '孙燕姿', 'keyword': '孙燕姿MV4K', 'pic': ''},
        {'name': '五月天', 'keyword': '五月天MV4K', 'pic': ''},
        {'name': '汪峰', 'keyword': '汪峰MV4K', 'pic': ''},
        {'name': '韩红', 'keyword': '韩红MV4K', 'pic': ''},
        {'name': '杨坤', 'keyword': '杨坤MV4K', 'pic': ''},
        {'name': '朴树', 'keyword': '朴树MV4K', 'pic': ''},
        {'name': '许巍', 'keyword': '许巍MV4K', 'pic': ''},
        {'name': '王力宏', 'keyword': '王力宏MV4K', 'pic': ''},
        {'name': '陶喆', 'keyword': '陶喆MV4K', 'pic': ''},
        {'name': '谢霆锋', 'keyword': '谢霆锋MV4K', 'pic': ''},
        {'name': 'Twins', 'keyword': 'TwinsMV4K', 'pic': ''},
        {'name': 'S.H.E', 'keyword': 'S.H.EMV4K', 'pic': ''},
        {'name': '任贤齐', 'keyword': '任贤齐MV4K', 'pic': ''},
        {'name': '梁静茹', 'keyword': '梁静茹MV4K', 'pic': ''},
        {'name': '张韶涵', 'keyword': '张韶涵MV4K', 'pic': ''},
        {'name': '蔡依林', 'keyword': '蔡依林MV4K', 'pic': ''},
        {'name': '罗志祥', 'keyword': '罗志祥MV4K', 'pic': ''},
        {'name': '周杰伦', 'keyword': '周杰伦MV', 'pic': ''},
        {'name': 'BTS', 'keyword': 'BTSMV4K', 'pic': ''},
        {'name': 'BigBang', 'keyword': 'BigBangMV4K', 'pic': ''},
        {'name': 'EXO', 'keyword': 'EXOMV4K', 'pic': ''},
        {'name': 'IU', 'keyword': 'IUMV4K', 'pic': ''},
        {'name': '李知恩', 'keyword': '李知恩MV4K', 'pic': ''},
        {'name': 'NCT', 'keyword': 'NCTMV4K', 'pic': ''},
        {'name': 'Red Velvet', 'keyword': 'RedVelvetMV4K', 'pic': ''},
        {'name': '少女时代', 'keyword': '少女时代MV4K', 'pic': ''},
        {'name': 'F(x)', 'keyword': 'f(x)MV4K', 'pic': ''},
        {'name': '2NE1', 'keyword': '2NE1MV4K', 'pic': ''},
        {'name': 'Wonder Girls', 'keyword': 'WonderGirlsMV4K', 'pic': ''},
        {'name': 'AKB48', 'keyword': 'AKB48MV4K', 'pic': ''},
        {'name': '乃木坂46', 'keyword': '乃木坂46MV4K', 'pic': ''},
        {'name': 'LiSA', 'keyword': 'LiSAMV4K', 'pic': ''},
        {'name': 'YOASOBI', 'keyword': 'YOASOBIMV4K', 'pic': ''},
        {'name': '米津玄师', 'keyword': '米津玄师MV4K', 'pic': ''},
        {'name': '宇多田光', 'keyword': '宇多田光MV4K', 'pic': ''},
        {'name': '滨崎步', 'keyword': '滨崎步MV4K', 'pic': ''},
        {'name': '仓木麻衣', 'keyword': '仓木麻衣MV4K', 'pic': ''},
        {'name': 'Avril Lavigne', 'keyword': 'AvrilLavigneMV4K', 'pic': ''},
        {'name': 'Lady Gaga', 'keyword': 'LadyGagaMV4K', 'pic': ''},
        {'name': 'Britney Spears', 'keyword': 'BritneySpearsMV4K', 'pic': ''},
        {'name': 'Justin Bieber', 'keyword': 'JustinBieberMV4K', 'pic': ''},
        {'name': 'Ed Sheeran', 'keyword': 'EdSheeranMV4K', 'pic': ''},
        {'name': 'Ariana Grande', 'keyword': 'ArianaGrandeMV4K', 'pic': ''},
        {'name': 'Billie Eilish', 'keyword': 'BillieEilishMV4K', 'pic': ''},
        {'name': 'Dua Lipa', 'keyword': 'DuaLipaMV4K', 'pic': ''},
        {'name': 'Coldplay', 'keyword': 'ColdplayMV4K', 'pic': ''},
        {'name': 'Maroon 5', 'keyword': 'Maroon5MV4K', 'pic': ''},
        {'name': 'Linkin Park', 'keyword': 'LinkinParkMV4K', 'pic': ''},
        {'name': 'Queen', 'keyword': 'QueenMV4K', 'pic': ''},
        {'name': 'Elvis Presley', 'keyword': 'ElvisPresleyMV4K', 'pic': ''},
        {'name': 'Madonna', 'keyword': 'MadonnaMV4K', 'pic': ''},
        {'name': 'Rihanna', 'keyword': 'RihannaMV4K', 'pic': ''},
        {'name': 'Katy Perry', 'keyword': 'KatyPerryMV4K', 'pic': ''},
        {'name': 'Shakira', 'keyword': 'ShakiraMV4K', 'pic': ''},
        {'name': 'Bruno Mars', 'keyword': 'BrunoMarsMV4K', 'pic': ''},
        {'name': 'Charlie Puth', 'keyword': 'CharliePuthMV4K', 'pic': ''},
        {'name': 'Post Malone', 'keyword': 'PostMaloneMV4K', 'pic': ''},
        {'name': 'Doja Cat', 'keyword': 'DojaCatMV4K', 'pic': ''},
    ]

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

        if cid == 'artist_mv':
            artists = []
            for idx, artist in enumerate(self.artist_list):
                vod = {
                    "vod_id": f"artist_{artist['keyword']}",
                    "vod_name": artist['name'],
                    "vod_pic": artist['pic'] if artist['pic'] else "https://i0.hdslb.com/bfs/face/member/noface.jpg",
                    "vod_remarks": "点击查看",
                    "vod_tag": "folder",
                }
                artists.append(vod)
            result['list'] = artists
            result['page'] = 1
            result['pagecount'] = 1
            result['limit'] = len(artists)
            result['total'] = len(artists)
            return result

        if cid.startswith('artist_'):
            keyword = cid.replace('artist_', '', 1)
            pg = int(pg) if pg else 1
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
                    "vod_id": f"{cid}|{id}",
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
                "vod_id": f"{cid}|{id}",
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

        category_keyword = ""
        bvid = did
        if '|' in did:
            parts = did.split('|', 1)
            category_keyword = parts[0]
            bvid = parts[1]

        url = f'https://www.bilibili.com/video/{bvid}'
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
                play_url += i['title'] + '$' + f'https://www.bilibili.com/video/{bvid}?p=' + str(i['p']) + '#'
            play_url = play_url[:-1]
        else:
            play_url = f"正片$https://www.bilibili.com/video/{bvid}"

        category_videos_url = ""
        if category_keyword:
            try:
                keyword = category_keyword.replace('artist_', '', 1) if category_keyword.startswith('artist_') else category_keyword
                keyword = keyword.replace('search_', '', 1) if keyword.startswith('search_') else keyword
                category_api = f'{xurl}/x/web-interface/wbi/search/type?search_type=video&__refresh__=true&page=1&page_size=100&keyword={keyword}'
                category_res = requests.get(url=category_api, headers=headers)
                category_res.encoding = "utf-8"
                category_kjson = json.loads(category_res.text)

                seen_bvids = set()
                for item in category_kjson.get('data', {}).get('result', []):
                    item_bvid = str(item.get('bvid', ''))
                    if not item_bvid or item_bvid in seen_bvids:
                        continue
                    seen_bvids.add(item_bvid)

                    item_title = item.get('title', '未知视频').replace('<em class="keyword">', '').replace('</em>', '')
                    item_title = item_title.replace('#', '﹟').replace('$', '﹩')
                    item_play = item.get('play', 0)
                    item_url = f"https://www.bilibili.com/video/{item_bvid}"

                    if item_bvid == bvid:
                        category_videos_url = f"{item_title}【{self.format_number(item_play)}】${item_url}#" + category_videos_url
                    else:
                        category_videos_url += f"{item_title}【{self.format_number(item_play)}】${item_url}#"

                category_videos_url = category_videos_url.rstrip("#")

            except Exception as e:
                category_videos_url = ""

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
                        related_bvid_item = related_video.get("bvid", "")

                        if not related_title or related_title == f"相关视频{i+1}":
                            related_title = f"相关推荐{i+1}"

                        related_title = related_title.replace('#', '﹟').replace('$', '﹩')

                        related_stat = related_video.get('stat', {})
                        related_views = related_stat.get('view', 0)

                        if related_bvid_item:
                            related_video_url = f"https://www.bilibili.com/video/{related_bvid_item}"
                            related_play_url += f"{related_title}【{self.format_number(related_views)}】${related_video_url}#"

                    related_play_url = related_play_url.rstrip("#")

            except Exception:
                pass

        if category_videos_url and related_play_url:
            vod_play_from = "当前分类[源力软件汇]$$$相关推荐"
            vod_play_url = f"{category_videos_url}$$$${related_play_url}"
        elif category_videos_url:
            vod_play_from = '当前分类[源力软件汇]'
            vod_play_url = category_videos_url
        elif related_play_url:
            vod_play_from = "相关推荐[源力软件汇]"
            vod_play_url = related_play_url
        else:
            vod_play_from = 'B站MV[源力软件汇]'
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
                "vod_id": f"search_{key}|{id}",
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
