# coding=utf-8
#!/usr/bin/python
# by @嗷呜模板-熊修
import random
import sys
from base64 import b64encode, b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode
import json
import re

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.did = self.random_str(32)
        pass

    def getName(self):
        return "爱奇艺"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    rhost = 'https://www.iqiyi.com'
    hhost = 'https://mesh.if.iqiyi.com'
    dhost = 'https://miniapp.iqiyi.com'
    api_host = 'https://pcw-api.iqiyi.com'

    headers = {
        'Origin': rhost,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Referer': f'{rhost}/',
    }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "1",
            "电视剧": "2", 
            "纪录片": "3",
            "动漫": "4",
            "综艺": "6",
            "音乐": "5",
            "网络电影": "16"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        
        # 构建筛选条件
        filters = {
            "1": self.getMovieFilters(),
            "2": self.getTvFilters(), 
            "3": self.getDocFilters(),
            "4": self.getCartoonFilters(),
            "6": self.getShowFilters(),
            "5": self.getMusicFilters(),
            "16": self.getWebMovieFilters()
        }
        
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        # 使用推荐接口
        url = f'{self.api_host}/search/recommend/list?channel_id=1&data_type=1&page_id=1&ret_num=20'
        try:
            data = self.fetch(url, headers=self.headers).json()
        except:
            return {'list': []}
        
        vlist = []
        for item in data.get('data', {}).get('list', []):
            vod_id = f"{item.get('channelId', '1')}${item.get('albumId', '')}"
            vlist.append({
                'vod_id': vod_id,
                'vod_name': item.get('name', ''),
                'vod_pic': item.get('imageUrl', '').replace('.jpg', '_390_520.jpg?caplist=jpg,webp'),
                'vod_remarks': self.getVideoDesc(item)
            })
        return {'list': vlist}

    def categoryContent(self, tid, pg, filter, extend):
        # 构建请求URL
        base_url = f'{self.api_host}/search/recommend/list?channel_id={tid}&data_type=1&page_id={pg}&ret_num=48'
        
        # 特殊处理网络电影
        if tid == "16":
            base_url = base_url.replace("channel_id=16", "channel_id=1")
            base_url = base_url.split("three_category_id")[0] + "three_category_id=27401"
        # 特殊处理音乐
        elif tid == "5":
            base_url = base_url.replace("data_type=1", "data_type=2")
        
        # 添加筛选参数
        filter_params = []
        for key, value in extend.items():
            if value:
                if key == 'year' and '_' in value:
                    # 处理年份范围
                    filter_params.append(f'market_release_date_level={value}')
                else:
                    filter_params.append(f'{key}={value}')
        
        if filter_params:
            base_url += '&' + '&'.join(filter_params)
        
        try:
            data = self.fetch(base_url, headers=self.headers).json()
            # 如果返回错误，尝试使用PC UA
            if data.get('code') == "A00003":
                pc_headers = self.headers.copy()
                pc_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                data = self.fetch(base_url, headers=pc_headers).json()
        except:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 48, 'total': 0}
        
        videos = []
        for item in data.get('data', {}).get('list', []):
            vod_id = f"{item.get('channelId', tid)}${item.get('albumId', '')}"
            videos.append({
                'vod_id': vod_id,
                'vod_name': item.get('name', ''),
                'vod_pic': item.get('imageUrl', '').replace('.jpg', '_390_520.jpg?caplist=jpg,webp'),
                'vod_remarks': self.getVideoDesc(item)
            })
        
        result = {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 48,
            'total': 999999
        }
        return result

    def detailContent(self, ids):
        if not ids or not ids[0]:
            return {'list': []}
            
        try:
            tid, album_id = ids[0].split('$')
        except:
            return {'list': []}
        
        # 获取详情信息 - 使用JS规则中的接口
        detail_url = f'{self.api_host}/video/video/videoinfowithuser/{album_id}?agent_type=1&authcookie=&subkey={album_id}&subscribe=1'
        try:
            detail_data = self.fetch(detail_url, headers=self.headers).json()
            data = detail_data.get('data', {})
            
            # 如果详情接口没有数据，尝试使用专辑接口
            if not data:
                album_url = f'{self.api_host}/albums/album/ainfo?aid={album_id}'
                album_data = self.fetch(album_url, headers=self.headers).json()
                data = album_data.get('data', {})
                
        except Exception as e:
            print(f"获取详情错误: {e}")
            return {'list': []}
        
        # 构建播放列表
        play_list = self.getPlayList(tid, album_id, data)
        
        vod = {
            'vod_id': ids[0],
            'vod_name': data.get('name', ''),
            'vod_pic': self.getDetailImage(data),
            'vod_year': data.get('publishDate', '').split('-')[0] if data.get('publishDate') else '',
            'vod_remarks': self.getDetailDesc(data),
            'vod_actor': self.getActors(data),
            'vod_director': self.getDirectors(data),
            'vod_area': self.getAreaInfo(data),
            'vod_content': data.get('description', ''),
            'vod_play_from': '爱奇艺',
            'vod_play_url': play_list
        }
        
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        search_url = f'https://search.video.iqiyi.com/o?if=html5&key={key}&pageNum={pg}&pos=1&pageSize=24&site=iqiyi'
        try:
            data = self.fetch(search_url, headers=self.headers).json()
        except:
            return {'list': [], 'page': 1}
        
        videos = []
        for item in data.get('data', {}).get('docinfos', []):
            album_info = item.get('albumDocInfo', {})
            if album_info:
                vod_id = f"{album_info.get('channelId', '1')}${album_info.get('albumId', '')}"
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': album_info.get('albumTitle', ''),
                    'vod_pic': album_info.get('albumVImage', ''),
                    'vod_remarks': album_info.get('tvFocus', '') or album_info.get('channel', '')
                })
        
        return {'list': videos, 'page': int(pg)}

    def playerContent(self, flag, id, vipFlags):
        """
        播放内容解析 - 按照JS规则设置解析参数
        """
        return {
            'parse': 0,      # 0=使用外部解析器
            'jx': 1,         # 1=需要解析
            'url': id,       # 原始视频URL
            'header': self.getPlayerHeaders()
        }

    def getPlayerHeaders(self):
        """获取播放器headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Referer': 'https://www.iqiyi.com/',
            'Origin': 'https://www.iqiyi.com'
        }

    def localProxy(self, param):
        pass

    # 辅助方法
    def getVideoDesc(self, item):
        """获取视频描述信息"""
        channel_id = item.get('channelId', 1)
        desc = ""
        
        if channel_id == 1:  # 电影
            if item.get('score'):
                desc = f"{item['score']}分"
        elif channel_id in [2, 4]:  # 电视剧、动漫
            latest_order = item.get('latestOrder', 0)
            video_count = item.get('videoCount', 0)
            score = f"{item.get('score', '')}分\t" if item.get('score') else ""
            
            if latest_order == video_count:
                desc = f"{score}{latest_order}集全"
            else:
                if video_count:
                    desc = f"{score}{latest_order}/{video_count}集"
                else:
                    desc = f"更新至 {latest_order}集"
        elif channel_id == 6:  # 综艺
            desc = item.get('period', '') + "期"
        elif channel_id == 5:  # 音乐
            desc = item.get('focus', '')
        else:
            if item.get('latestOrder'):
                desc = f"更新至 第{item['latestOrder']}期"
            elif item.get('period'):
                desc = item.get('period', '')
            else:
                desc = item.get('focus', '')
        
        return desc

    def getDetailImage(self, data):
        """获取详情页图片"""
        image_url = data.get('imageUrl', '')
        if not image_url:
            return ""
        
        # 按照JS规则处理图片尺寸
        try:
            image_size = data.get('imageSize', {})
            if isinstance(image_size, dict):
                vsize = image_size.get('12', '579_772')
            else:
                vsize = '579_772'
        except:
            vsize = '579_772'
            
        return image_url.replace('.jpg', f'_{vsize}.jpg?caplist=jpg,webp')

    def getDetailDesc(self, data):
        """获取详情页描述"""
        try:
            categories = data.get('categories', [])
            category_names = []
            for cat in categories[:3]:
                if isinstance(cat, dict) and cat.get('name'):
                    category_names.append(cat['name'])
            
            category_str = "\t".join(category_names)
            score = data.get('score', '')
            latest_order = data.get('latestOrder', 0)
            video_count = data.get('videoCount', 0)
            
            desc_parts = []
            if category_str:
                desc_parts.append(f"类型: {category_str}")
            if score:
                desc_parts.append(f"评分: {score}")
            if latest_order:
                if video_count:
                    desc_parts.append(f"更新: {latest_order}/{video_count}集")
                else:
                    desc_parts.append(f"更新: {latest_order}集")
                    
            return "\t".join(desc_parts)
        except:
            return data.get('subtitle', data.get('focus', ''))

    def getAreaInfo(self, data):
        """获取地区信息"""
        try:
            focus = data.get('focus', '')
            pay_mark = data.get('payMark', 0)
            pay_status = "VIP" if pay_mark == 1 else "免费"
            
            areas = data.get('areas', [])
            area_names = []
            for area in areas:
                if isinstance(area, dict) and area.get('name'):
                    area_names.append(area['name'])
                elif isinstance(area, str):
                    area_names.append(area)
            
            area_str = " ".join(area_names) if area_names else ""
            
            info_parts = []
            if focus:
                info_parts.append(focus)
            info_parts.append(f"资费: {pay_status}")
            if area_str:
                info_parts.append(f"地区: {area_str}")
                
            return "\n".join(info_parts)
        except:
            return ""

    def getActors(self, data):
        """获取演员信息"""
        try:
            actors = []
            people = data.get('people', {})
            if people and isinstance(people, dict):
                # 尝试多种可能的演员字段
                for field in ['main_charactor', 'main_actor', 'actor', 'starring']:
                    if field in people and isinstance(people[field], list):
                        for actor in people[field]:
                            if isinstance(actor, dict) and actor.get('name'):
                                actors.append(actor['name'])
                            elif isinstance(actor, str):
                                actors.append(actor)
            
            # 去重并返回
            return ','.join(list(dict.fromkeys(actors)))
        except:
            return ''

    def getDirectors(self, data):
        """获取导演信息"""
        try:
            directors = []
            people = data.get('people', {})
            if people and isinstance(people, dict):
                # 尝试多种可能的导演字段
                for field in ['director', 'directors']:
                    if field in people and isinstance(people[field], list):
                        for director in people[field]:
                            if isinstance(director, dict) and director.get('name'):
                                directors.append(director['name'])
                            elif isinstance(director, str):
                                directors.append(director)
            
            # 去重并返回
            return ','.join(list(dict.fromkeys(directors)))
        except:
            return ''

    def getPlayList(self, tid, album_id, data):
        """获取播放列表 - 修复播放URL获取"""
        play_list = []
        channel_id = int(tid)
        
        try:
            if channel_id in [1, 5]:  # 电影、音乐
                play_url = data.get('playUrl', '')
                if play_url:
                    title = data.get('shortTitle', '正片')
                    # 确保URL是完整的
                    if not play_url.startswith('http'):
                        play_url = f'https:{play_url}' if play_url.startswith('//') else f'https://www.iqiyi.com{play_url}'
                    play_list.append(f"{title}${play_url}")
                else:
                    # 如果没有playUrl，使用默认的播放页
                    default_url = f'https://www.iqiyi.com/{album_id}.html'
                    play_list.append(f"正片${default_url}")
                    
            elif channel_id == 6:  # 综艺
                period = data.get('period', '').split('-')[0] if data.get('period') else '1'
                list_url = f'{self.api_host}/album/source/svlistinfo?cid=6&sourceid={album_id}&timelist={period}'
                play_data = self.fetch(list_url, headers=self.headers).json()
                
                episodes = play_data.get('data', {}).get(period, [])
                for item in episodes:
                    title = item.get('shortTitle', f"第{item.get('order', '')}期")
                    play_url = item.get('playUrl', '')
                    if play_url:
                        if not play_url.startswith('http'):
                            play_url = f'https:{play_url}' if play_url.startswith('//') else f'https://www.iqiyi.com{play_url}'
                        play_list.append(f"{title}${play_url}")
                        
            else:  # 电视剧、动漫等
                # 使用JS规则中的接口获取剧集列表
                list_url = f'{self.api_host}/albums/album/avlistinfo?aid={album_id}&size=200&page=1'
                episode_data = self.fetch(list_url, headers=self.headers).json()
                episodes = episode_data.get('data', {}).get('epsodelist', [])
                
                # 获取总集数
                total = episode_data.get('data', {}).get('total', len(episodes))
                
                # 如果集数超过200，获取剩余集数
                if total > 200:
                    for page in range(2, (total // 200) + 2):
                        page_url = f'{self.api_host}/albums/album/avlistinfo?aid={album_id}&size=200&page={page}'
                        page_data = self.fetch(page_url, headers=self.headers).json()
                        page_episodes = page_data.get('data', {}).get('epsodelist', [])
                        episodes.extend(page_episodes)
                        if len(episodes) >= total:
                            break
                
                for episode in episodes:
                    title = episode.get('shortTitle', f"第{episode.get('order', '')}集")
                    play_url = episode.get('playUrl', '')
                    if play_url:
                        if not play_url.startswith('http'):
                            play_url = f'https:{play_url}' if play_url.startswith('//') else f'https://www.iqiyi.com{play_url}'
                        play_list.append(f"{title}${play_url}")
        
        except Exception as e:
            print(f"获取播放列表错误: {e}")
            # 如果获取失败，提供默认播放页
            default_url = f'https://www.iqiyi.com/{album_id}.html'
            play_list.append(f"正片${default_url}")
        
        return '#'.join(play_list)

    # 筛选条件配置
    def getMovieFilters(self):
        return [
            {
                'key': 'mode',
                'name': '综合排序',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '热播榜', 'v': '11'},
                    {'n': '好评榜', 'v': '8'},
                    {'n': '新上线', 'v': '4'}
                ]
            },
            {
                'key': 'year', 
                'name': '全部年份',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '2025', 'v': '2025'},
                    {'n': '2024', 'v': '2024'},
                    {'n': '2023', 'v': '2023'},
                    {'n': '2022', 'v': '2022'},
                    {'n': '2021', 'v': '2021'},
                    {'n': '2020', 'v': '2020'},
                    {'n': '2019', 'v': '2019'},
                    {'n': '2018', 'v': '2018'},
                    {'n': '2017', 'v': '2017'},
                    {'n': '2016-2011', 'v': '2011_2016'},
                    {'n': '2010-2000', 'v': '2000_2010'},
                    {'n': '90年代', 'v': '1990_1999'},
                    {'n': '80年代', 'v': '1980_1989'},
                    {'n': '更早', 'v': '1964_1979'}
                ]
            },
            {
                'key': 'is_purchase',
                'name': '全部资费', 
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '免费', 'v': '0'},
                    {'n': '会员', 'v': '1'},
                    {'n': '付费', 'v': '2'}
                ]
            }
        ]

    def getTvFilters(self):
        return self.getMovieFilters()

    def getDocFilters(self):
        return self.getMovieFilters()

    def getCartoonFilters(self):
        return self.getMovieFilters()

    def getShowFilters(self):
        return self.getMovieFilters()

    def getMusicFilters(self):
        return self.getMovieFilters()

    def getWebMovieFilters(self):
        return self.getMovieFilters()

    def random_str(self, length=16):
        hex_chars = '0123456789abcdef'
        return ''.join(random.choice(hex_chars) for _ in range(length))