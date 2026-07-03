from base.spider import Spider
import requests
import json
import re
import sys
import base64
import time
import hashlib
from urllib.parse import quote, urlencode

APPID = "16073360"
SECRET = "0b50b02fd0d73a9c4c8c3a781c30845f"
BASE_URL = "https://music.91q.com"

ARTIST_PREFIX = "artist_"
PLAYLIST_PREFIX = "pl_"
PLAYLIST_CAT_PREFIX = "plcat_"

class Spider(Spider):
    def getName(self):
        return "千千音乐"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def _generate_sign(self, params):
        sorted_keys = sorted(params.keys())
        param_str = "&".join([f"{k}={params[k]}" for k in sorted_keys])
        sign_str = param_str + SECRET
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    def _make_request(self, path, params=None):
        if params is None:
            params = {}
        params['appid'] = APPID
        params['timestamp'] = str(int(time.time()))
        params['sign'] = self._generate_sign(params)
        
        url = f"{BASE_URL}{path}?{urlencode(params)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://music.91q.com/',
            'From': 'web'
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            return r.json()
        except Exception as e:
            return None

    def homeContent(self, filter):
        result = {}
        cateId = []
        
        playlist_categories = self._get_playlist_categories()
        if playlist_categories:
            for cat in playlist_categories:
                cat_name = cat.get('categoryName', '')
                cat_id = cat.get('id', '')
                if cat_name and cat_id:
                    cateId.append({
                        "type_name": cat_name,
                        "type_id": f"{PLAYLIST_CAT_PREFIX}{cat_id}"
                    })
        
        cateId.append({
            "type_name": "歌手列表",
            "type_id": f"{ARTIST_PREFIX}all"
        })
        
        result['class'] = cateId
        return result

    def _get_playlist_categories(self):
        try:
            data = self._make_request('/v1/tracklist/category', {})
            if data and data.get('state') and data.get('data'):
                return data['data']
        except Exception:
            pass
        return []

    def homeVideoContent(self):
        playlist_categories = self._get_playlist_categories()
        first_cat_id = ""
        if playlist_categories:
            first_cat_id = playlist_categories[0].get('id', '')
        if first_cat_id:
            result = self.categoryContent(f"{PLAYLIST_CAT_PREFIX}{first_cat_id}", 1, False, {})
        else:
            result = self.categoryContent(f"{PLAYLIST_PREFIX}all", 1, False, {})
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        
        if tid.startswith(PLAYLIST_CAT_PREFIX):
            big_cat_id = tid[len(PLAYLIST_CAT_PREFIX):]
            result = self._get_playlist_list_by_big_cat(big_cat_id, pg)
        elif tid.startswith(PLAYLIST_PREFIX):
            category_id = tid[len(PLAYLIST_PREFIX):]
            result = self._get_playlist_list(category_id, pg)
        elif tid.startswith(ARTIST_PREFIX):
            result = self._get_artist_list(pg)
        
        return result

    def _get_playlist_list(self, category_id, pg):
        result = {}
        videos = []
        
        params = {
            'pageSize': 48,
            'pageNo': str(pg)
        }
        if category_id and category_id != 'all' and category_id != 'hot':
            params['subCateId'] = category_id
        
        data = self._make_request('/v1/tracklist/list', params)
        
        if data and data.get('state') and data.get('data'):
            playlist_list = data['data'].get('result', [])
            for item in playlist_list:
                video = {
                    "vod_id": f"{PLAYLIST_PREFIX}{item.get('id', '')}",
                    "vod_name": item.get('title', ''),
                    "vod_pic": item.get('pic', ''),
                    "vod_remarks": f"{item.get('trackCount', 0)}首"
                }
                videos.append(video)
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 48
        result['total'] = 999999
        
        return result

    def _get_playlist_list_by_big_cat(self, big_cat_id, pg):
        result = {}
        videos = []
        
        categories = self._get_playlist_categories()
        sub_cats = []
        
        for cat in categories:
            if str(cat.get('id', '')) == str(big_cat_id):
                sub_cats = cat.get('subCate', [])
                break
        
        if not sub_cats:
            result['list'] = []
            result['page'] = pg
            result['pagecount'] = 0
            result['limit'] = 48
            result['total'] = 0
            return result
        
        page_size_per_cat = max(48 // len(sub_cats), 8)
        seen_ids = set()
        
        for sub in sub_cats[:8]:
            sub_id = sub.get('id', '')
            if not sub_id:
                continue
            
            params = {
                'pageSize': page_size_per_cat,
                'pageNo': str(pg),
                'subCateId': sub_id
            }
            
            data = self._make_request('/v1/tracklist/list', params)
            
            if data and data.get('state') and data.get('data'):
                playlist_list = data['data'].get('result', [])
                for item in playlist_list:
                    pl_id = item.get('id', '')
                    if pl_id and pl_id not in seen_ids:
                        seen_ids.add(pl_id)
                        video = {
                            "vod_id": f"{PLAYLIST_PREFIX}{pl_id}",
                            "vod_name": item.get('title', ''),
                            "vod_pic": item.get('pic', ''),
                            "vod_remarks": f"{item.get('trackCount', 0)}首"
                        }
                        videos.append(video)
                        if len(videos) >= 48:
                            break
            
            if len(videos) >= 48:
                break
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 48
        result['total'] = 999999
        
        return result

    def _get_artist_list(self, pg):
        result = {}
        videos = []
        
        params = {
            'pageSize': 48,
            'pageNo': str(pg)
        }
        
        data = self._make_request('/v1/artist/list', params)
        
        if data and data.get('state') and data.get('data'):
            artist_list = data['data'].get('result', [])
            for item in artist_list:
                video = {
                    "vod_id": f"{ARTIST_PREFIX}{item.get('artistCode', '')}",
                    "vod_name": item.get('name', ''),
                    "vod_pic": item.get('pic', ''),
                    "vod_remarks": f"粉丝: {item.get('favoriteCount', 0)}"
                }
                videos.append(video)
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 48
        result['total'] = 999999
        
        return result

    def detailContent(self, ids):
        rid = ids[0]
        result = {}
        
        if rid.startswith(PLAYLIST_PREFIX):
            playlist_id = rid[len(PLAYLIST_PREFIX):]
            result = self._get_playlist_detail(playlist_id, rid)
        elif rid.startswith(ARTIST_PREFIX):
            artist_code = rid[len(ARTIST_PREFIX):]
            result = self._get_artist_detail(artist_code, rid)
        
        return result

    def _get_playlist_detail(self, playlist_id, vod_id):
        result = {}
        
        try:
            all_songs = []
            page = 1
            max_pages = 10
            
            while page <= max_pages:
                data = self._make_request('/v1/tracklist/info', {
                    'id': playlist_id,
                    'pageSize': 50,
                    'pageNo': str(page)
                })
                
                if data and data.get('state') and data.get('data'):
                    d = data['data']
                    if page == 1:
                        playlist_title = d.get('title', '')
                        playlist_pic = d.get('pic', '')
                        playlist_desc = d.get('desc', '')
                        track_count = d.get('trackCount', 0)
                    
                    track_list = d.get('trackList', [])
                    if not track_list:
                        break
                    
                    for song in track_list:
                        song_name = song.get('title', '').strip()
                        if song_name:
                            all_songs.append(song)
                    
                    if len(all_songs) >= 300:
                        all_songs = all_songs[:300]
                        break
                    
                    have_more = d.get('haveMore', False)
                    if not have_more:
                        break
                
                page += 1
            
            max_songs = 300
            if len(all_songs) > max_songs:
                all_songs = all_songs[:max_songs]
            
            play_arr = []
            for song in all_songs:
                name = re.sub(r'[$#]', '', song.get('title', '')).strip()
                song_id = song.get('TSID', '') or song.get('assetId', '') or song.get('id', '')
                
                artist_list = song.get('artist', [])
                artist_name = artist_list[0].get('name', '') if artist_list else ''
                
                album = song.get('albumTitle', '')
                
                if not name or not song_id:
                    continue
                
                search_key = f"{name} {artist_name}" if artist_name else name
                encoded_key = base64.b64encode(search_key.encode('utf-8')).decode('utf-8')
                full_id = f"{encoded_key}|{song_id}"
                
                if artist_name and album:
                    play_arr.append(f"{name} - {artist_name} - {album}${full_id}")
                elif artist_name:
                    play_arr.append(f"{name} - {artist_name}${full_id}")
                else:
                    play_arr.append(f"{name}${full_id}")
            
            vod = {
                "vod_id": vod_id,
                "vod_name": playlist_title,
                "vod_pic": playlist_pic,
                "vod_content": playlist_desc if playlist_desc else "暂无歌单介绍",
                "vod_remarks": f"歌曲 :   {len(all_songs)}首",
                "vod_actor": "千千音乐",
                "vod_play_from": "千千音乐",
                "vod_play_url": "#".join(play_arr)
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            vod = {
                "vod_id": vod_id,
                "vod_name": "加载失败",
                "vod_content": f"加载歌单信息失败: {str(e)}",
                "vod_remarks": "加载失败",
                "vod_actor": "未知",
                "vod_play_from": "千千音乐",
                "vod_play_url": ""
            }
            result['list'] = [vod]
        
        return result

    def _get_artist_detail(self, artist_code, vod_id):
        result = {}
        
        try:
            info_data = self._make_request('/v1/artist/info', {'artistCode': artist_code})
            artist_name = ""
            artist_pic = ""
            artist_intro = ""
            
            if info_data and info_data.get('state') and info_data.get('data'):
                d = info_data['data']
                artist_name = d.get('name', '')
                artist_pic = d.get('pic', '')
                artist_intro = d.get('introduce', '')
                if artist_intro:
                    artist_intro = re.sub(r'<[^>]+>', '', artist_intro)
                    artist_intro = artist_intro.replace('&nbsp;', ' ').strip()
            
            all_songs = self._get_artist_songs(artist_code)
            
            max_songs = 300
            if len(all_songs) > max_songs:
                all_songs = all_songs[:max_songs]
            
            play_arr = []
            for song in all_songs:
                name = re.sub(r'[$#]', '', song.get('title', '')).strip()
                song_id = song.get('TSID', '') or song.get('assetId', '') or song.get('id', '')
                album = song.get('albumTitle', '')
                
                if not name or not song_id:
                    continue
                
                search_key = f"{name} {artist_name}"
                encoded_key = base64.b64encode(search_key.encode('utf-8')).decode('utf-8')
                full_id = f"{encoded_key}|{song_id}"
                
                if album:
                    play_arr.append(f"{name} - {album}${full_id}")
                else:
                    play_arr.append(f"{name}${full_id}")
            
            vod = {
                "vod_id": vod_id,
                "vod_name": artist_name,
                "vod_pic": artist_pic,
                "vod_content": artist_intro if artist_intro else "暂无歌手简介",
                "vod_remarks": f"歌曲 :   {len(all_songs)}首",
                "vod_actor": artist_name,
                "vod_play_from": "千千音乐",
                "vod_play_url": "#".join(play_arr)
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            vod = {
                "vod_id": vod_id,
                "vod_name": "加载失败",
                "vod_content": f"加载歌手信息失败: {str(e)}",
                "vod_remarks": "加载失败",
                "vod_actor": "未知",
                "vod_play_from": "千千音乐",
                "vod_play_url": ""
            }
            result['list'] = [vod]
        
        return result

    def _get_artist_songs(self, artist_code):
        songs = []
        max_pages = 10
        
        for page in range(1, max_pages + 1):
            try:
                params = {
                    'artistCode': artist_code,
                    'pageSize': 50,
                    'pageNo': str(page)
                }
                data = self._make_request('/v1/artist/song', params)
                
                if data and data.get('state') and data.get('data'):
                    song_list = data['data'].get('result', [])
                    
                    if not song_list:
                        break
                    
                    for song in song_list:
                        song_name = song.get('title', '').strip()
                        if song_name:
                            songs.append(song)
                    
                    if len(songs) >= 300:
                        songs = songs[:300]
                        break
                        
            except Exception:
                continue
        
        return songs

    def playerContent(self, flag, id, vipFlags):
        result = {}
        
        search_keyword = ""
        tsid = id
        
        if '|' in id:
            parts = id.split('|', 1)
            try:
                search_keyword = base64.b64decode(parts[0]).decode('utf-8')
            except Exception:
                search_keyword = ""
            tsid = parts[1]
        
        quality_list = [
            ("无损FLAC", "3000", "flac"),
            ("高品质320K", "320", "mp3"),
            ("标准128K", "128", "mp3")
        ]
        
        song_info = None
        lrc_url = ""
        
        qualities = []
        
        for quality_name, rate, format_type in quality_list:
            try:
                track_data = self._make_request('/v1/song/tracklink', {
                    'TSID': tsid,
                    'rate': rate,
                    'format': format_type
                })
                if track_data and track_data.get('state') and track_data.get('data'):
                    path = track_data['data'].get('path', '')
                    if path:
                        if not path.startswith('http'):
                            path = "https://zhangmenshiting.baidu.com" + path
                        qualities.append((quality_name, path))
            except Exception:
                continue
        
        if not qualities and search_keyword:
            try:
                search_data = self._make_request('/v1/search', {
                    'word': search_keyword,
                    'type': 1,
                    'pageSize': 1
                })
                if search_data and search_data.get('state') and search_data.get('data'):
                    tracks = search_data['data'].get('typeTrack', [])
                    if tracks:
                        song_info = tracks[0]
                        new_tsid = song_info.get('TSID', '')
                        lrc_url = song_info.get('lyric', '')
                        
                        if new_tsid and new_tsid != tsid:
                            for quality_name, rate, format_type in quality_list:
                                try:
                                    track_data = self._make_request('/v1/song/tracklink', {
                                        'TSID': new_tsid,
                                        'rate': rate,
                                        'format': format_type
                                    })
                                    if track_data and track_data.get('state') and track_data.get('data'):
                                        path = track_data['data'].get('path', '')
                                        if path:
                                            if not path.startswith('http'):
                                                path = "https://zhangmenshiting.baidu.com" + path
                                            qualities.append((quality_name, path))
                                except Exception:
                                    continue
            except Exception:
                pass
        
        if not qualities and song_info:
            try:
                if song_info.get('eq_rate_128') and song_info['eq_rate_128'].get('path'):
                    path = song_info['eq_rate_128']['path']
                    if not path.startswith('http'):
                        path = "https://zhangmenshiting.baidu.com" + path
                    qualities.append(("标准128K", path))
            except Exception:
                pass
        
        if not qualities:
            result["parse"] = 0
            result["playUrl"] = ""
            result["url"] = ""
            result["header"] = {}
            return result
        
        urls = []
        for quality_name, quality_url in qualities:
            urls.append(quality_name)
            urls.append(quality_url)
        
        if not lrc_url and search_keyword:
            try:
                search_data = self._make_request('/v1/search', {
                    'word': search_keyword,
                    'type': 1,
                    'pageSize': 1
                })
                if search_data and search_data.get('state') and search_data.get('data'):
                    tracks = search_data['data'].get('typeTrack', [])
                    if tracks:
                        lrc_url = tracks[0].get('lyric', '')
            except Exception:
                pass
        
        lrc = ""
        if lrc_url:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://music.91q.com/'
                }
                lr = requests.get(lrc_url, headers=headers, timeout=5)
                if lr.status_code == 200:
                    lrc = lr.text
            except Exception:
                pass
        
        if lrc:
            try:
                ssa_lrc = self._create_ssa_subtitle(lrc)
                ssa_base64 = base64.b64encode(ssa_lrc.encode('utf-8')).decode('utf-8')
                ssa_url = f"data:text/x-ssa;base64,{ssa_base64}"
                
                result["subs"] = [{
                    "name": "5行歌词",
                    "url": ssa_url,
                    "format": "text/x-ssa",
                    "selected": True
                }]
            except Exception:
                pass
        
        result["parse"] = 0
        result["playUrl"] = ""
        result["url"] = urls
        result["header"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://music.91q.com/"
        }
        
        return result

    def _format_time(self, seconds):
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def _create_ssa_subtitle(self, lrc_text):
        lines = []
        pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)'
        
        for line in lrc_text.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                hundredths_str = match.group(3)
                if len(hundredths_str) == 3:
                    hundredths = int(hundredths_str) // 10
                else:
                    hundredths = int(hundredths_str)
                text = match.group(4).strip()
                
                total_seconds = minutes * 60 + seconds + hundredths / 100.0
                if text:
                    lines.append({
                        'start': total_seconds,
                        'text': text
                    })
        
        if not lines:
            return ""
        
        ssa_header = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1280
PlayResY: 720
Timer: 100.0000
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: WAITING_TOP2,Roboto,50,&H00FFFF00,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,160,1
Style: WAITING_TOP1,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,240,1
Style: PLAYING_CENTER,Roboto,65,&H0000FF00,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,2,0,0,340,1
Style: PLAYED_BOTTOM1,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,440,1
Style: PLAYED_BOTTOM2,Roboto,50,&H00FFFF00,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        def format_ssa_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds * 100) % 100)
            return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        
        events = []
        
        for i in range(len(lines)):
            current = lines[i]
            current_end = lines[i+1]['start'] if i+1 < len(lines) else current['start'] + 5.0
            
            wait2 = lines[i+2] if i+2 < len(lines) else None
            wait1 = lines[i+1] if i+1 < len(lines) else None
            played1 = lines[i-1] if i-1 >= 0 else None
            played2 = lines[i-2] if i-2 >= 0 else None
            
            start_str = format_ssa_time(current['start'])
            end_str = format_ssa_time(current_end)
            
            if wait2:
                events.append(f"Dialogue: 1,{start_str},{end_str},WAITING_TOP2,,0,0,0,,{wait2['text']}")
            
            if wait1:
                events.append(f"Dialogue: 2,{start_str},{end_str},WAITING_TOP1,,0,0,0,,{wait1['text']}")
            
            events.append(f"Dialogue: 3,{start_str},{end_str},PLAYING_CENTER,,0,0,0,,{current['text']}")
            
            if played1:
                events.append(f"Dialogue: 4,{start_str},{end_str},PLAYED_BOTTOM1,,0,0,0,,{played1['text']}")
            
            if played2:
                events.append(f"Dialogue: 5,{start_str},{end_str},PLAYED_BOTTOM2,,0,0,0,,{played2['text']}")
        
        return ssa_header + "\n".join(events)

    def searchContent(self, key, quick, pg=1):
        result = {}
        page_num = int(pg)
        
        data = self._make_request('/v1/search', {
            'word': key,
            'type': 1,
            'pageSize': 30,
            'pageNo': str(page_num)
        })
        
        videos = []
        seen_artists = set()
        
        if data and data.get('state') and data.get('data'):
            tracks = data['data'].get('typeTrack', [])
            for item in tracks:
                artist_list = item.get('artist', [])
                artist_name = artist_list[0].get('name', '') if artist_list else ''
                artist_code = artist_list[0].get('artistCode', '') if artist_list else ''
                
                if artist_code and artist_code not in seen_artists:
                    seen_artists.add(artist_code)
                    video = {
                        "vod_id": f"{ARTIST_PREFIX}{artist_code}",
                        "vod_name": artist_name,
                        "vod_pic": item.get('pic', ''),
                        "vod_remarks": f"歌手"
                    }
                    videos.append(video)
                
                if len(videos) >= 30:
                    break
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 30
        result['total'] = 999999
        
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        return None
