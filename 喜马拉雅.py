"""
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '喜马拉雅',
  lang: 'hipy',
})
"""
# -*- coding: utf-8 -*-
import re
import json
import time
import hashlib
import random
import requests
from urllib.parse import quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://www.ximalaya.com"
        self.proxy_api = "https://apis.netstart.cn/ximalaya"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.61 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }

    def getName(self):
        return '喜马拉雅'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {"class": [
            {'type_id': 'youshengshu', 'type_name': '有声书'},
            {'type_id': 'xiangsheng', 'type_name': '相声评书'},
            {'type_id': 'yinyue', 'type_name': '音乐'},
            {'type_id': 'ertong', 'type_name': '儿童'},
            {'type_id': 'toutiao', 'type_name': '头条'},
            {'type_id': 'renwen', 'type_name': '人文'},
            {'type_id': 'qinggan', 'type_name': '情感'},
            {'type_id': 'lishi', 'type_name': '历史'},
        ]}

    def homeVideoContent(self):
        items = []
        try:
            url = f'{self.proxy_api}/rank/queryRank?clusterCode=hotplay&categoryCode=youshengshu'
            data = self._fetch_json(url)

            if data and 'data' in data:
                for item in data.get('data', {}).get('rankModuleInfoList', []):
                    album_info = item.get('albumInfo', {})
                    stat_info = item.get('statCountInfo', {})
                    album_id = str(album_info.get('id', ''))
                    title = album_info.get('title', '')
                    cover = album_info.get('cover', '')
                    track_count = stat_info.get('trackCount', 0)

                    if cover and cover.startswith('//'):
                        cover = 'https:' + cover
                    elif cover and not cover.startswith('http'):
                        cover = 'https://imagev2.xmcdn.com/' + cover

                    if album_id and title and self._is_album_free(album_id):
                        items.append({
                            "vod_id": album_id,
                            "vod_name": title,
                            "vod_pic": cover,
                            "vod_remarks": f"{track_count}集",
                        })

            if len(items) < 20:
                url2 = f'{self.proxy_api}/rank/queryRank?clusterCode=hotplay&categoryCode=xiangsheng'
                data2 = self._fetch_json(url2)
                if data2 and 'data' in data2:
                    for item in data2.get('data', {}).get('rankModuleInfoList', []):
                        album_info = item.get('albumInfo', {})
                        stat_info = item.get('statCountInfo', {})
                        album_id = str(album_info.get('id', ''))
                        title = album_info.get('title', '')
                        cover = album_info.get('cover', '')
                        track_count = stat_info.get('trackCount', 0)

                        if cover and cover.startswith('//'):
                            cover = 'https:' + cover
                        elif cover and not cover.startswith('http'):
                            cover = 'https://imagev2.xmcdn.com/' + cover

                        if album_id and title and len(items) < 30 and self._is_album_free(album_id):
                            items.append({
                                "vod_id": album_id,
                                "vod_name": title,
                                "vod_pic": cover,
                                "vod_remarks": f"{track_count}集",
                            })

        except Exception as e:
            print(f'homeVideoContent error: {e}')
        return {"list": items[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        items = []
        try:
            url = f'{self.proxy_api}/category/queryCategoryPage?categoryCode={tid}&page={page}&pageSize=20&sort=0'
            data = self._fetch_json(url)

            if data and 'data' in data:
                album_page = data.get('data', {}).get('firstPageCategoryAlbums', {})
                albums = album_page.get('albumBriefDetailInfos', [])

                for album_item in albums:
                    album_info = album_item.get('albumInfo', {})
                    stat_info = album_item.get('statCountInfo', {})
                    anchor_info = album_item.get('anchorInfo', {})
                    album_id = str(album_info.get('id', ''))
                    title = album_info.get('title', '')
                    cover = album_info.get('cover', '')
                    track_count = stat_info.get('trackCount', 0)
                    nickname = anchor_info.get('nickname', '')

                    if cover and cover.startswith('//'):
                        cover = 'https:' + cover
                    elif cover and not cover.startswith('http'):
                        cover = 'https://imagev2.xmcdn.com/' + cover

                    if album_id and title and self._is_album_free(album_id):
                        items.append({
                            "vod_id": album_id,
                            "vod_name": title,
                            "vod_pic": cover,
                            "vod_remarks": f"{nickname} | {track_count}集",
                        })

            page_count = page if len(items) < 20 else page + 2
        except Exception as e:
            print(f'categoryContent error: {e}')
            page_count = page

        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        album_id = ids[0] if isinstance(ids, list) else str(ids)
        try:
            url = f'{self.proxy_api}/album/queryAlbumPage/{album_id}'
            data = self._fetch_json(url)

            if not data or 'data' not in data:
                return result

            album = data.get('data', {})
            album_detail = album.get('albumDetailInfo', {})
            album_info = album_detail.get('albumInfo', {})
            stat_info = album_detail.get('statCountInfo', {})
            rich_info = album.get('albumRichInfo', {})

            title = album_info.get('title', '')
            cover = album_info.get('cover', '')
            short_intro = album_info.get('shortIntro', '')
            rich_intro = rich_info.get('richIntro', '')
            category_name = album_detail.get('pageUriInfo', {}).get('categoryName', '')
            track_count = stat_info.get('trackCount', 0)

            if cover and cover.startswith('//'):
                cover = 'https:' + cover
            elif cover and not cover.startswith('http'):
                cover = 'https://imagev2.xmcdn.com/' + cover

            intro = short_intro
            if not intro and rich_intro:
                intro = re.sub(r'<[^>]+>', '', rich_intro).strip()

            intro = intro + '\n\n微信公众号：源力软件汇--源力影视'

            tracks = self._get_album_tracks(album_id)

            play_urls = []
            for i, track in enumerate(tracks):
                track_title = track.get('title', f'第{i+1}章')
                track_id = track.get('trackId', '')
                play_urls.append(f"{track_title}${track_id}")

            play_url = '#'.join(play_urls)

            vod = {
                "vod_id": album_id,
                "vod_name": title,
                "vod_pic": cover,
                "vod_actor": "",
                "vod_year": "",
                "vod_remarks": f"{category_name} | {track_count}集",
                "vod_content": intro,
                "vod_play_from": '喜马拉雅',
                "vod_play_url": play_url,
            }
            result['list'].append(vod)

        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def _get_album_tracks(self, album_id, filter_paid=True):
        tracks = []
        try:
            url = f'{self.host}/revision/album/getTracksList?albumId={album_id}&pageNum=1&sort=0'
            data = self._fetch_json(url)

            if data and 'data' in data:
                page_tracks = data.get('data', {}).get('tracks', [])
                for track in page_tracks:
                    if filter_paid and track.get('isPaid', False):
                        continue
                    tracks.append({
                        'trackId': str(track.get('trackId', '')),
                        'title': track.get('title', ''),
                        'url': track.get('url', ''),
                    })

                track_total = data.get('data', {}).get('trackTotalCount', 0)
                if track_total > len(tracks):
                    page_num = 2
                    while len(tracks) < track_total and page_num <= 10:
                        url = f'{self.host}/revision/album/getTracksList?albumId={album_id}&pageNum={page_num}&sort=0'
                        data = self._fetch_json(url)
                        if not data or 'data' not in data:
                            break
                        page_tracks = data.get('data', {}).get('tracks', [])
                        if not page_tracks:
                            break
                        for track in page_tracks:
                            if filter_paid and track.get('isPaid', False):
                                continue
                            tracks.append({
                                'trackId': str(track.get('trackId', '')),
                                'title': track.get('title', ''),
                                'url': track.get('url', ''),
                            })
                        page_num += 1

        except Exception as e:
            print(f'_get_album_tracks error: {e}')
        return tracks

    def _is_album_free(self, album_id):
        try:
            url = f'{self.host}/revision/album/getTracksList?albumId={album_id}&pageNum=1&sort=0'
            data = self._fetch_json(url)
            if data and 'data' in data:
                tracks = data.get('data', {}).get('tracks', [])
                if tracks:
                    return not tracks[0].get('isPaid', False)
            return False
        except Exception as e:
            print(f'_is_album_free error: {e}')
            return False

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            parts = id.split('$')
            if len(parts) >= 2:
                track_id = parts[1].strip()
            else:
                track_id = id.strip()

            if '_' in track_id:
                album_id = track_id.split('_')[0]
                track_index = int(track_id.split('_')[1]) - 1 if len(track_id.split('_')) > 1 else 0
                tracks = self._get_album_tracks(album_id)
                if tracks and track_index < len(tracks):
                    track_id = tracks[track_index].get('trackId', '')

            track_url = f'/sound/{track_id}'
            play_url = self._get_play_url(track_id, track_url)
            if play_url:
                result["url"] = play_url
                result["parse"] = 0

                play_headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
                    "Referer": "https://m.ximalaya.com/",
                }
                result["header"] = json.dumps(play_headers)
            else:
                result["url"] = f"{self.host}{track_url}"
                result["parse"] = 1

        except Exception as e:
            print(f'playerContent error: {e}')
            result["url"] = f"{self.host}/sound/{id}"
            result["parse"] = 1
        return result

    def _get_xm_sign(self):
        try:
            url = f'{self.host}/revision/time'
            server_time = self._fetch(url).strip()
            now_time = str(round(time.time() * 1000))
            sign_str = hashlib.md5(f"himalaya-{server_time}".encode()).hexdigest()
            sign = f"{sign_str}({str(round(random.random() * 100))}){server_time}({str(round(random.random() * 100))}){now_time}"
            return sign
        except Exception as e:
            print(f'_get_xm_sign error: {e}')
            return ''

    def _get_play_url(self, track_id, track_url):
        try:
            mobile_headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
                "Referer": "https://m.ximalaya.com/",
            }
            url = f'https://m.ximalaya.com/tracks/{track_id}.json'
            r = requests.get(url, headers=mobile_headers, timeout=10, verify=False)
            if r.status_code == 200:
                data = r.json()
                play_path = data.get('play_path_64', '') or data.get('play_path', '') or data.get('play_path_32', '')
                if play_path:
                    return play_path

            if track_url:
                url2 = f'{self.host}{track_url}'
                r2 = requests.get(url2, headers=self.headers, timeout=10, verify=False)
                if r2.status_code == 200:
                    html = r2.text
                    patterns = [
                        r'"src"\s*:\s*"([^"]+\.(m4a|mp3))"',
                        r'https?://[^\s"\']+\.(m4a|mp3)',
                        r'"playUrl"\s*:\s*"([^"]+)"',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, html)
                        for m in matches:
                            if isinstance(m, tuple):
                                url_candidate = m[0]
                            else:
                                url_candidate = m
                            if '.m4a' in url_candidate or '.mp3' in url_candidate:
                                if url_candidate.startswith('//'):
                                    url_candidate = 'https:' + url_candidate
                                return url_candidate

        except Exception as e:
            print(f'_get_play_url error: {e}')
        return ''

    def searchContent(self, key, quick, pg="1"):
        items = []
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            
            url3 = f'{self.proxy_api}/search?kw={quote(key)}&core=album&page={page}&rows=20'
            data3 = self._fetch_json(url3)
            if data3 and data3.get('ret') == 0 and 'data' in data3:
                results = data3.get('data', {}).get('albums', [])
                for album in results:
                    album_id = str(album.get('id', ''))
                    title = album.get('title', '')
                    cover = album.get('cover', '')
                    track_count = album.get('trackCount', 0)

                    if cover and cover.startswith('//'):
                        cover = 'https:' + cover
                    elif cover and not cover.startswith('http'):
                        cover = 'https://imagev2.xmcdn.com/' + cover

                    if album_id and title and self._is_album_free(album_id):
                        items.append({
                            "vod_id": album_id,
                            "vod_name": title,
                            "vod_pic": cover,
                            "vod_remarks": f"{track_count}集",
                        })

            if not items:
                free_albums = [
                    {"id": "9723091", "title": "郭德纲21年相声精选", "cover": "storages/5a86-audiofreehighqps/D8/E5/GKwRIJEFfkl9AAOIigD9zcBJ.png", "tracks": 143},
                    {"id": "12208800", "title": "凡人修仙传", "cover": "", "tracks": 3000},
                    {"id": "51362648", "title": "诡秘之主", "cover": "", "tracks": 2000},
                    {"id": "2684034", "title": "雪中悍刀行", "cover": "", "tracks": 500},
                    {"id": "77980595", "title": "都市狂枭", "cover": "", "tracks": 2000},
                    {"id": "78186737", "title": "家有王妃初长成", "cover": "", "tracks": 1500},
                ]
                for album in free_albums:
                    cover = album.get('cover', '')
                    if cover and not cover.startswith('http'):
                        cover = 'https://imagev2.xmcdn.com/' + cover
                    items.append({
                        "vod_id": album['id'],
                        "vod_name": album['title'],
                        "vod_pic": cover,
                        "vod_remarks": f"{album['tracks']}集",
                    })

            page_count = page if len(items) < 20 else page + 2
        except Exception as e:
            print(f'searchContent error: {e}')
            page_count = page

        return {"list": items, "page": page, "pagecount": page_count, "limit": 20, "total": 99999}

    def localProxy(self, params):
        if params.get('type') == "media":
            return self.proxyMedia(params)
        return None

    def proxyMedia(self, params):
        action = {
            'url': params.get('url', ''),
            'header': params.get('header', {}),
            'param': params.get('param', ''),
            'type': 'media'
        }
        return action

    def _fetch(self, url):
        try:
            if url.startswith('http'):
                full_url = url
            else:
                full_url = self.host + url
            headers = dict(self.headers)
            headers["Referer"] = self.host + "/"
            rsp = self.fetch(full_url, headers=headers, timeout=30)
            if rsp and rsp.status_code == 200:
                return rsp.text
            return ''
        except Exception as e:
            print(f'_fetch error: {e}')
            return ''

    def _fetch_json(self, url):
        try:
            html = self._fetch(url)
            if html:
                return json.loads(html)
            return None
        except Exception as e:
            print(f'_fetch_json error: {e}')
            return None

    def _fetch_with_headers(self, url, custom_headers):
        try:
            if url.startswith('http'):
                full_url = url
            else:
                full_url = self.host + url
            rsp = self.fetch(full_url, headers=custom_headers, timeout=30)
            if rsp and rsp.status_code == 200:
                return rsp.text
            return ''
        except Exception as e:
            print(f'_fetch_with_headers error: {e}')
            return ''

    def _fetch_json_with_headers(self, url, custom_headers):
        try:
            html = self._fetch_with_headers(url, custom_headers)
            if html:
                return json.loads(html)
            return None
        except Exception as e:
            print(f'_fetch_json_with_headers error: {e}')
            return None
