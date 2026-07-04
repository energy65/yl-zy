import json
import sys
import re
import base64
import requests
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "酷狗音乐"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.kugou.com/'
        }
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://m.kugou.com/'
        }
        self.quality_config = [
            ("无损", "flac", 1400),
            ("320k", "320", 320),
            ("128k", "128", 128),
        ]
        self.artist_type_map = {
            'artist_hot': '-1',
            'artist_man': '1',
            'artist_woman': '2',
            'artist_team': '3',
            'artist_jp_man': '4',
            'artist_jp_woman': '5',
            'artist_jp_team': '6',
            'artist_us_man': '7',
            'artist_us_woman': '8',
            'artist_us_team': '9',
        }
        self.classes = [
            {'type_id': 'bang_8888', 'type_name': '酷狗TOP500'},
            {'type_id': 'bang_100530', 'type_name': '视频号热歌榜'},
            {'type_id': 'bang_85897', 'type_name': '国潮音乐榜'},
            {'type_id': 'bang_51341', 'type_name': '民谣榜'},
            {'type_id': 'bang_59900', 'type_name': '纯音乐榜'},
            {'type_id': 'pl_hot', 'type_name': '热门歌单'},
            {'type_id': 'pl_new', 'type_name': '新歌速递'},
            {'type_id': 'pl_classic', 'type_name': '经典老歌'},
            {'type_id': 'pl_dj', 'type_name': 'DJ舞曲'},
            {'type_id': 'artist_hot', 'type_name': '热门歌手'},
            {'type_id': 'artist_man', 'type_name': '华语男歌手'},
            {'type_id': 'artist_woman', 'type_name': '华语女歌手'},
            {'type_id': 'artist_team', 'type_name': '华语组合'},
            {'type_id': 'artist_jp_man', 'type_name': '日韩男歌手'},
            {'type_id': 'artist_jp_woman', 'type_name': '日韩女歌手'},
            {'type_id': 'artist_jp_team', 'type_name': '日韩组合'},
            {'type_id': 'artist_us_man', 'type_name': '欧美男歌手'},
            {'type_id': 'artist_us_woman', 'type_name': '欧美女歌手'},
            {'type_id': 'artist_us_team', 'type_name': '欧美组合'},
        ]

    def isVideoFormat(self, url):
        return url.endswith(('.mp4', '.m3u8', '.flv', '.mkv', '.mov'))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {}
        result['class'] = self.classes
        result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('bang_8888', 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg else 1
            if tid.startswith('pl_detail_'):
                pid = tid.replace('pl_detail_', '')
                return self._get_playlist_songs(pid, pg)
            elif tid.startswith('pl_'):
                return self._get_playlist_list(tid, pg)
            elif tid.startswith('artist_detail_'):
                aid = tid.replace('artist_detail_', '')
                return self._get_artist_songs(aid, pg)
            elif tid.startswith('artist_'):
                type_key = tid
                artist_type = self.artist_type_map.get(type_key, '-1')
                return self._get_artist_list(artist_type, pg)
            elif tid.startswith('bang_detail_'):
                bid = tid.replace('bang_detail_', '')
                return self._get_bang_songs(bid, pg)
            elif tid.startswith('bang_'):
                bang_id = tid.replace('bang_', '')
                if bang_id.isdigit():
                    return self._get_bang_songs(bang_id, pg)
                else:
                    return self._get_bang_list(pg)
            elif tid.startswith('mv_detail_'):
                mvid = tid.replace('mv_detail_', '')
                return self._get_mv_detail(mvid, pg)
            elif tid.startswith('mv_'):
                return self._get_mv_list(tid, pg)
            else:
                return self._get_bang_songs('8888', pg)
        except Exception as e:
            print("categoryContent error:", e)
            return {'list': self._default_songs(), 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 999}

    def detailContent(self, ids):
        try:
            vid = ids[0].strip()
            if vid.startswith('song_'):
                return self._get_song_detail(vid)
            elif vid.startswith('artist_detail_'):
                artist_id = vid.replace('artist_detail_', '')
                return self._get_artist_detail(artist_id)
            elif vid.startswith('pl_detail_'):
                pid = vid.replace('pl_detail_', '')
                return self._get_playlist_detail(pid)
            elif vid.startswith('bang_detail_'):
                bang_id = vid.replace('bang_detail_', '')
                return self._get_bang_detail(bang_id)
            elif vid.startswith('mv_detail_'):
                mvid = vid.replace('mv_detail_', '')
                return self._get_mv_video_detail(mvid)
            else:
                return self._get_song_detail(vid)
        except Exception as e:
            print("detailContent error:", e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["url"] = raw_id
                result["header"] = self.mobile_headers
                return result

            hash_val = raw_id
            song_name_hint = ''
            artist_hint = ''
            is_mv = False

            if '&&' in hash_val:
                hash_val = hash_val.split('&&')[0]

            if '$' in hash_val:
                parts = hash_val.split('$')
                if len(parts) >= 2:
                    name_part = parts[0]
                    if 'MV' in name_part or 'mv' in name_part:
                        is_mv = True
                    if ' - ' in name_part:
                        np = name_part.split(' - ', 1)
                        artist_hint = np[0].strip()
                        song_name_hint = np[1].strip()
                    else:
                        song_name_hint = name_part.strip()
                for part in reversed(parts):
                    if part.startswith('http'):
                        result["url"] = part
                        result["header"] = self.headers
                        return result
                    elif len(part) == 32 and all(c in '0123456789abcdefABCDEF' for c in part):
                        hash_val = part
                        break
                else:
                    if len(parts) > 1:
                        hash_val = parts[-1]

            if hash_val.startswith('song_'):
                hash_val = hash_val.replace('song_', '')

            if self.isVideoFormat(hash_val):
                result["url"] = hash_val
                result["header"] = self.headers
                return result

            if not (len(hash_val) == 32 and all(c in '0123456789abcdefABCDEF' for c in hash_val)):
                result["parse"] = 0
                result["url"] = ""
                return result

            if is_mv:
                play_url = self._get_mv_play_url(hash_val)
                result["url"] = play_url
                result["header"] = self.mobile_headers
            else:
                play_url = self._get_play_url(hash_val, song_name_hint, artist_hint)
                result["url"] = play_url
                result["header"] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.kugou.com/'
                }

                lrc = self._get_lyric(hash_val)
                if lrc:
                    result["lrc"] = lrc

        except Exception as e:
            print("playerContent error:", e)

        return result

    def searchContent(self, key, quick, pg="1"):
        return self._get_search_songs(key, pg)

    def searchContentPage(self, key, quick, pg):
        return self._get_search_songs(key, pg)

    def fetch(self, url, headers=None, timeout=10):
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)
        return requests.get(url, headers=req_headers, timeout=timeout)

    def _default_songs(self):
        return [{
            'vod_id': 'song_b3a52a7a958bf0aed0ebfba2e9a818b7',
            'vod_name': '晴天 - 周杰伦',
            'vod_pic': '',
            'vod_remarks': '酷狗音乐',
        }]

    def _get_song_name_artist(self, it):
        song = ''
        artist = ''
        
        song = it.get('songname') or it.get('SongName') or it.get('audio_name') or it.get('name') or ''
        
        artist = it.get('singername') or it.get('SingerName') or it.get('author_name') or it.get('artist') or ''
        
        if (not song or not artist) and it.get('filename'):
            filename = str(it.get('filename', ''))
            if ' - ' in filename:
                parts = filename.split(' - ', 1)
                if not artist:
                    artist = parts[0].strip()
                if not song:
                    song = parts[1].strip()
        
        if not artist and it.get('authors'):
            authors = it['authors']
            if isinstance(authors, list) and len(authors) > 0:
                if isinstance(authors[0], dict):
                    artist = authors[0].get('author_name', authors[0].get('name', ''))
                elif isinstance(authors[0], str):
                    artist = authors[0]
        
        if not artist and it.get('h5_author_name'):
            artist = it['h5_author_name']
        
        if not artist and isinstance(song, str) and ' - ' in song:
            parts = song.split(' - ', 1)
            if len(parts) == 2:
                artist = parts[0]
                song = parts[1]
        
        return str(song).strip(), str(artist).strip()

    def _get_playlist_list(self, tid, pg):
        try:
            pl_map = {
                'pl_hot': '5',
                'pl_new': '7',
                'pl_classic': '6',
                'pl_dj': '6',
                'pl_emo': '5',
            }
            sort_id = pl_map.get(tid, '5')
            api_url = "http://m.kugou.com/plist/index?json=true&page=" + str(pg) + "&pagesize=30&sortid=" + sort_id
            res = self.fetch(api_url, headers=self.mobile_headers)
            data = res.json()
            
            plist_data = data.get('plist', {})
            if isinstance(plist_data, dict):
                plist_list = plist_data.get('list', [])
            else:
                plist_list = []
            
            if isinstance(plist_list, list) and plist_list:
                vods = self._parse_playlist(plist_list)
                if vods:
                    total = plist_data.get('total', 999) or 999
                    return {'list': vods, 'page': pg, 'pagecount': (total // 30) + 1, 'limit': 30, 'total': total}
        except Exception as e:
            print("_get_playlist_list error:", e)
        
        return self._get_bang_list(pg)

    def _parse_playlist(self, data_list):
        vods = []
        for it in data_list:
            if not isinstance(it, dict):
                continue
            name = it.get('specialname', it.get('name', it.get('title', '未命名歌单')))
            vid = str(it.get('specialid', it.get('id', it.get('pid', ''))))
            pic = it.get('imgurl', it.get('img', it.get('pic', it.get('cover', ''))))
            if pic and not pic.startswith('http'):
                pic = 'https://' + pic.lstrip('/')
            if pic and '{size}' in pic:
                pic = pic.replace('{size}', '400')
            remarks = it.get('intro', it.get('info', it.get('nickname', '')))

            if not vid:
                continue

            name = re.sub(r'<[^>]+>', '', str(name)).strip()
            vods.append({
                'vod_name': name,
                'vod_id': 'pl_detail_' + vid,
                'vod_pic': pic,
                'vod_remarks': remarks or '酷狗歌单',
                'vod_tag': 'folder'
            })
        return vods

    def _get_playlist_detail(self, pid):
        play_arr = []
        play_pics = []
        vod_name = '酷狗歌单'
        vod_pic = ''
        vod_content = ''

        try:
            if not pid or not pid.isdigit():
                return self._get_playlist_songs_fallback(pid)

            api_url = "http://m.kugou.com/plist/list/" + pid + "?json=true"
            res = self.fetch(api_url, headers=self.mobile_headers)
            d = res.json()

            list_data = d.get('list', d.get('data', {}))
            info = list_data.get('info', list_data)
            song_list = list_data.get('list', list_data.get('songs', []))

            if isinstance(info, dict):
                vod_name = info.get('specialname', info.get('name', '酷狗歌单'))
                vod_pic = info.get('imgurl', info.get('img', info.get('pic', '')))
                if vod_pic and '{size}' in vod_pic:
                    vod_pic = vod_pic.replace('{size}', '400')
                vod_content = info.get('intro', info.get('info', ''))

            for it in song_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    play_arr.append(display_name + "$" + hash_val)
                    play_pics.append(albumpic)
        except Exception as e:
            print("_get_playlist_detail error:", e)

        if not play_arr:
            return self._get_playlist_songs_fallback(pid)

        vod = {
            'vod_id': pid,
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_content': vod_content,
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': '酷狗音乐',
            'vod_play_url': '#'.join(play_arr),
        }
        if play_pics:
            vod['vod_play_pic'] = '#'.join(play_pics)
            vod['vod_play_pic_ratio'] = 1.5

        return {'list': [vod]}

    def _get_playlist_songs_fallback(self, pid):
        play_arr = []
        play_pics = []
        search_result = self._get_search_songs('热门歌曲', 1)
        for item in search_result.get('list', []):
            hash_val = item['vod_id'].replace('song_', '')
            play_arr.append(item['vod_name'] + "$" + hash_val)
            play_pics.append(item.get('vod_pic', ''))
        vod = {
            'vod_id': pid or 'hot_songs',
            'vod_name': '热门歌曲',
            'vod_pic': play_pics[0] if play_pics else '',
            'vod_content': '酷狗音乐热门歌曲',
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': '酷狗音乐',
            'vod_play_url': '#'.join(play_arr),
        }
        if play_pics:
            vod['vod_play_pic'] = '#'.join(play_pics)
            vod['vod_play_pic_ratio'] = 1.5
        return {'list': [vod]}

    def _get_playlist_songs(self, pid, pg):
        vods = []
        try:
            api_url = "http://m.kugou.com/plist/list/" + pid + "?json=true&page=" + str(pg)
            res = self.fetch(api_url, headers=self.mobile_headers)
            d = res.json()

            list_data = d.get('list', d.get('data', {}))
            song_list = list_data.get('list', list_data.get('songs', []))

            for it in song_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'song_' + hash_val,
                        'vod_pic': albumpic,
                        'vod_remarks': '酷狗音乐',
                    })
        except Exception as e:
            print("_get_playlist_songs error:", e)

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_artist_list(self, artist_type, pg):
        vods = []
        try:
            api_url = "http://mobilecdn.kugou.com/api/v3/singer/list?type=" + str(artist_type) + "&page=" + str(pg) + "&pagesize=30"
            res = self.fetch(api_url, headers=self.headers)
            data = res.json()
            
            info_list = data.get('data', {}).get('info', [])
            total = data.get('data', {}).get('total', 999) or 999
            
            for it in info_list:
                if not isinstance(it, dict):
                    continue
                singer_id = str(it.get('singerid', it.get('singer_id', it.get('id', ''))))
                name = it.get('singername', it.get('singer_name', it.get('name', '未知歌手')))
                pic = it.get('imgurl', it.get('singer_pic', it.get('img', it.get('avatar', it.get('pic', '')))))
                if pic and not pic.startswith('http'):
                    pic = 'https://' + pic.lstrip('/')
                if pic and '{size}' in pic:
                    pic = pic.replace('{size}', '400')

                if not singer_id:
                    continue

                name = re.sub(r'<[^>]+>', '', str(name)).strip()
                vods.append({
                    'vod_name': name,
                    'vod_id': 'artist_detail_' + singer_id,
                    'vod_pic': pic,
                    'vod_remarks': it.get('country', it.get('company', '歌手')),
                    'vod_tag': 'folder'
                })
        except Exception as e:
            print("_get_artist_list error:", e)

        if not vods:
            vods = self._default_artists()
        return {
            'list': vods,
            'page': pg,
            'pagecount': (total // 30) + 1 if isinstance(total, int) else 99,
            'limit': 30,
            'total': total if isinstance(total, int) else 9999
        }

    def _default_artists(self):
        default = [
            ("周杰伦", "3520"), ("林俊杰", "3359"), ("陈奕迅", "3283"),
            ("邓紫棋", "5182"), ("薛之谦", "3894"), ("毛不易", "119235"),
            ("李荣浩", "3754"), ("华晨宇", "5267"), ("张学友", "3282"),
            ("王菲", "3285"), ("五月天", "3281"), ("Taylor Swift", "4497"),
        ]
        return [{
            'vod_id': 'artist_detail_' + aid,
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': '歌手',
            'vod_tag': 'folder'
        } for name, aid in default]

    def _get_artist_detail(self, artist_id):
        play_arr = []
        play_pics = []
        artist_name = ''
        artist_pic = ''

        try:
            aid = artist_id.replace('artist_detail_', '').replace('artist_', '')
            
            info = self._get_artist_info(aid)
            artist_name = info.get('name', '')
            artist_pic = info.get('pic', '')
            
            songs_result = self._get_v3_artist_songs(aid, 1, 50)
            for it in songs_result:
                hash_val = str(it.get('hash', '')).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    play_arr.append(display_name + "$" + hash_val)
                    play_pics.append(albumpic)
        except Exception as e:
            print("_get_artist_detail error:", e)

        if not play_arr:
            search_result = self._get_search_songs(artist_name or '热门歌曲', 1)
            for item in search_result.get('list', []):
                hash_val = item['vod_id'].replace('song_', '')
                play_arr.append(item['vod_name'] + "$" + hash_val)
                play_pics.append(item.get('vod_pic', ''))
            if not artist_name:
                artist_name = '热门歌手'

        vod = {
            'vod_id': artist_id,
            'vod_name': artist_name or '歌手',
            'vod_pic': artist_pic or (play_pics[0] if play_pics else ''),
            'vod_content': "共 " + str(len(play_arr)) + " 首歌曲",
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_actor': artist_name,
            'vod_play_from': '酷狗音乐',
            'vod_play_url': '#'.join(play_arr),
        }
        if play_pics:
            vod['vod_play_pic'] = '#'.join(play_pics)
            vod['vod_play_pic_ratio'] = 1.5

        return {'list': [vod]}

    def _get_artist_info(self, singerid):
        info = {'name': '', 'pic': '', 'intro': ''}
        try:
            api_url = "http://m.kugou.com/singer/info/" + str(singerid) + "?json=true"
            res = self.fetch(api_url, headers=self.mobile_headers)
            data = res.json()
            info_data = data.get('info', {})
            if isinstance(info_data, dict):
                info['name'] = info_data.get('singername', info_data.get('name', ''))
                info['pic'] = info_data.get('imgurl', info_data.get('img', info_data.get('pic', '')))
                info['intro'] = info_data.get('intro', info_data.get('info', ''))
                if info['pic'] and not info['pic'].startswith('http'):
                    info['pic'] = 'https://' + info['pic'].lstrip('/')
                if info['pic'] and '{size}' in info['pic']:
                    info['pic'] = info['pic'].replace('{size}', '400')
        except Exception:
            pass
        return info

    def _get_v3_artist_songs(self, singerid, pg=1, pagesize=30):
        songs = []
        try:
            api_url = "http://mobilecdn.kugou.com/api/v3/singer/song?singerid=" + str(singerid) + "&page=" + str(pg) + "&pagesize=" + str(pagesize)
            res = self.fetch(api_url, headers=self.headers)
            data = res.json()
            info = data.get('data', {}).get('info', [])
            if isinstance(info, list):
                songs = info
        except Exception as e:
            print("_get_v3_artist_songs error:", e)
        return songs

    def _get_artist_songs(self, artist_id, pg):
        vods = []
        try:
            aid = artist_id.replace('artist_detail_', '').replace('artist_', '')
            
            song_list = self._get_v3_artist_songs(aid, pg, 30)
            
            artist_info = self._get_artist_info(aid)
            artist_name = artist_info.get('name', '')
            
            for it in song_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if not albumpic:
                    album_info = it.get('album_info', {})
                    if isinstance(album_info, dict):
                        albumpic = album_info.get('cover', '')
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    if not artist and artist_name:
                        display_name = song + " - " + artist_name
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'song_' + hash_val,
                        'vod_pic': albumpic,
                        'vod_remarks': '酷狗音乐',
                    })
        except Exception as e:
            print("_get_artist_songs error:", e)

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_bang_list(self, pg):
        vods = []
        try:
            api_url = "http://m.kugou.com/rank/list?json=true"
            res = self.fetch(api_url, headers=self.mobile_headers)
            data = res.json()

            rank_list = data.get('rank', data.get('list', []))
            if isinstance(rank_list, dict):
                rank_list = rank_list.get('list', [])

            for it in rank_list:
                if not isinstance(it, dict):
                    continue
                rank_id = str(it.get('rankid', it.get('id', '')))
                rank_name = it.get('rankname', it.get('name', '排行榜'))
                pic = it.get('imgurl', it.get('img', it.get('pic', '')))
                if pic and not pic.startswith('http'):
                    pic = 'https://' + pic.lstrip('/')
                if pic and '{size}' in pic:
                    pic = pic.replace('{size}', '400')

                if not rank_id:
                    continue

                rank_name = re.sub(r'<[^>]+>', '', str(rank_name)).strip()
                vods.append({
                    'vod_name': rank_name,
                    'vod_id': 'bang_detail_' + rank_id,
                    'vod_pic': pic,
                    'vod_remarks': '排行榜',
                    'vod_tag': 'folder'
                })
        except Exception as e:
            print("_get_bang_list error:", e)

        if not vods:
            vods = self._default_bang_list()
        return {'list': vods, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(vods)}

    def _default_bang_list(self):
        bang_map = [
            ('8888', '酷狗TOP500'),
            ('85897', '国潮音乐榜'),
            ('51341', '民谣榜'),
            ('59900', '纯音乐榜'),
        ]
        vods = []
        for bid, bname in bang_map:
            vods.append({
                'vod_id': 'bang_detail_' + bid,
                'vod_name': bname,
                'vod_pic': '',
                'vod_remarks': '排行榜',
                'vod_tag': 'folder'
            })
        return vods

    def _get_bang_detail(self, bang_id):
        play_arr = []
        play_pics = []
        bang_name = '酷狗排行榜'
        bang_pic = ''

        try:
            api_url = "http://m.kugou.com/rank/info/?rankid=" + bang_id + "&page=1&json=true"
            res = self.fetch(api_url, headers=self.mobile_headers)
            d = res.json()

            info = d.get('info', {})
            if isinstance(info, dict):
                bang_name = info.get('rankname', info.get('name', bang_name))
                bang_pic = info.get('imgurl', info.get('pic', ''))
                if bang_pic and not bang_pic.startswith('http'):
                    bang_pic = 'https://' + bang_pic.lstrip('/')
                if bang_pic and '{size}' in bang_pic:
                    bang_pic = bang_pic.replace('{size}', '400')

            songs_data = d.get('songs', d.get('list', {}))
            if isinstance(songs_data, dict):
                song_list = songs_data.get('list', [])
            else:
                song_list = songs_data if isinstance(songs_data, list) else []

            for it in song_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    play_arr.append(display_name + "$" + hash_val)
                    play_pics.append(albumpic)
        except Exception as e:
            print("_get_bang_detail error:", e)

        if not play_arr:
            search_result = self._get_search_songs('热门歌曲', 1)
            for item in search_result.get('list', []):
                hash_val = item['vod_id'].replace('song_', '')
                play_arr.append(item['vod_name'] + "$" + hash_val)
                play_pics.append(item.get('vod_pic', ''))
            bang_name = bang_name or '热门歌曲'

        vod = {
            'vod_id': bang_id,
            'vod_name': bang_name,
            'vod_pic': bang_pic or (play_pics[0] if play_pics else ''),
            'vod_content': '',
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': '酷狗音乐',
            'vod_play_url': '#'.join(play_arr),
        }
        if play_pics:
            vod['vod_play_pic'] = '#'.join(play_pics)
            vod['vod_play_pic_ratio'] = 1.5

        return {'list': [vod]}

    def _get_bang_songs(self, bang_id, pg):
        vods = []
        try:
            api_url = "http://m.kugou.com/rank/info/?rankid=" + bang_id + "&page=" + str(pg) + "&json=true"
            res = self.fetch(api_url, headers=self.mobile_headers)
            d = res.json()

            songs_data = d.get('songs', d.get('list', {}))
            song_list = []
            if isinstance(songs_data, dict):
                song_list = songs_data.get('list', [])
            elif isinstance(songs_data, list):
                song_list = songs_data

            for it in song_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'song_' + hash_val,
                        'vod_pic': albumpic,
                        'vod_remarks': '排行榜',
                    })
        except Exception as e:
            print("_get_bang_songs error:", e)

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_song_detail(self, vid):
        result = {"list": []}
        try:
            hash_val = vid.replace("song_", "")
            song_info = self._get_song_info(hash_val)
            song_name = song_info.get('name', '')
            artist = song_info.get('artist', '')
            album = song_info.get('album', '')
            pic = song_info.get('pic', '')

            if not song_name:
                song_name = "歌曲_" + hash_val[:8]

            song_name = re.sub(r'[$#]', '', song_name).strip()
            artist = re.sub(r'[$#]', '', artist).strip() if artist else ''

            display_name = song_name + " - " + artist if artist else song_name

            play_from_arr = []
            play_url_arr = []
            play_pic_arr = []

            for q_name, q_type, q_br in self.quality_config:
                play_from_arr.append(q_name)
                play_url_arr.append(display_name + "$" + hash_val)
                play_pic_arr.append(pic)

            lrc = self._get_lyric(hash_val)
            content = "歌曲：" + song_name + "\n歌手：" + artist + "\n专辑：" + album + "\n来源：酷狗音乐"
            if lrc:
                lrc_lines = lrc.split('\n')
                clean_lines = []
                for line in lrc_lines:
                    clean_line = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
                    if clean_line and not clean_line.startswith('['):
                        clean_lines.append(clean_line)
                if clean_lines:
                    content += "\n\n--- 歌词 ---\n" + '\n'.join(clean_lines[:30])

            vod = {
                "vod_id": vid,
                "vod_name": song_name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_remarks": album or '酷狗音乐',
                "vod_actor": artist,
                "vod_play_from": '$$$'.join(play_from_arr),
                "vod_play_url": '$$$'.join(play_url_arr),
            }
            if play_pic_arr:
                vod['vod_play_pic'] = '$$$'.join(play_pic_arr)
                vod['vod_play_pic_ratio'] = 1.0

            result["list"] = [vod]
        except Exception as e:
            print("_get_song_detail error:", e)

        if not result.get('list'):
            hash_val = vid.replace("song_", "")
            vod = {
                "vod_id": vid,
                "vod_name": "歌曲_" + hash_val[:8],
                "vod_pic": '',
                "vod_content": '酷狗音乐',
                "vod_remarks": '酷狗音乐',
                "vod_actor": '',
                "vod_play_from": '标准音质',
                "vod_play_url": "歌曲_" + hash_val[:8] + "$" + hash_val,
            }
            result["list"] = [vod]

        return result

    def _get_song_info(self, hash_val):
        info = {'name': '', 'artist': '', 'album': '', 'pic': '', 'duration': ''}
        try:
            api_url = "http://mobilecdn.kugou.com/api/v3/song/info?hash=" + hash_val.lower()
            r = self.fetch(api_url, timeout=5)
            data = r.json()
            if data.get('status') == 1 and data.get('data'):
                d = data['data']
                info['name'] = d.get('songname', '')
                info['artist'] = d.get('singername', '')
                info['pic'] = d.get('imgurl', '')
                info['duration'] = d.get('duration', '')
                album_list = d.get('album', [])
                if album_list and isinstance(album_list, list) and len(album_list) > 0:
                    if isinstance(album_list[0], dict):
                        info['album'] = album_list[0].get('album_name', '')
                if info['pic'] and not info['pic'].startswith('http'):
                    info['pic'] = 'https://' + info['pic'].lstrip('/')
                if info['pic'] and '{size}' in info['pic']:
                    info['pic'] = info['pic'].replace('{size}', '400')
        except Exception:
            pass

        if not info.get('name'):
            try:
                api_url = "http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash=" + hash_val.upper()
                r = self.fetch(api_url, headers=self.mobile_headers, timeout=5)
                data = r.json()
                if data:
                    info['name'] = data.get('songName', data.get('songname', ''))
                    info['artist'] = data.get('singerName', data.get('singername', data.get('author_name', '')))
                    info['album'] = data.get('album_name', data.get('albumName', ''))
                    info['pic'] = data.get('album_img', data.get('albumImg', data.get('imgUrl', '')))
                    info['duration'] = data.get('duration', '')
                    if info['pic'] and not info['pic'].startswith('http'):
                        info['pic'] = 'https://' + info['pic'].lstrip('/')
                    if info['pic'] and '{size}' in info['pic']:
                        info['pic'] = info['pic'].replace('{size}', '400')
            except Exception:
                pass

        if not info.get('name'):
            try:
                search_url = "http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword=" + hash_val + "&page=1&pagesize=1&showtype=1"
                res = self.fetch(search_url)
                data = res.json()
                info_list = data.get('data', {}).get('info', [])
                if info_list:
                    it = info_list[0]
                    info['name'] = it.get('songname', '')
                    info['artist'] = it.get('singername', '')
                    info['album'] = it.get('album_name', '')
                    info['duration'] = it.get('duration', '')
            except Exception:
                pass

        return info

    def _get_play_url(self, hash_val, song_name_hint='', artist_hint=''):
        try:
            api_url = "https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash=" + hash_val.upper()
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            if data.get('status') == 1 and data.get('data'):
                play_data = data['data']
                if play_data.get('play_url'):
                    return play_data.get('play_url', '')
                if play_data.get('play_backup_url'):
                    return play_data.get('play_backup_url', '')
        except Exception:
            pass

        try:
            api_url = "http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash=" + hash_val.upper()
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=5)
            data = r.json()
            url = data.get('url', '')
            if url and url.startswith('http'):
                return url
            backup_url = data.get('backup_url', '')
            if backup_url and backup_url.startswith('http'):
                return backup_url
        except Exception:
            pass

        kuwo_url = self._get_kuwo_play_url(hash_val, song_name_hint, artist_hint)
        if kuwo_url:
            return kuwo_url

        return ''

    def _get_kuwo_play_url(self, hash_val, song_name_hint='', artist_hint=''):
        try:
            song_name = song_name_hint
            artist = artist_hint
            
            if not song_name:
                song_info = self._get_song_info(hash_val)
                song_name = song_info.get('name', '')
                artist = song_info.get('artist', '')
            
            if not song_name:
                return ''
            
            keyword = song_name
            if artist:
                keyword = artist + " " + song_name
            
            search_url = "https://search.kuwo.cn/r.s?client=kt&all=" + keyword + "&pn=0&rn=5&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            kuwo_headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
                'Referer': 'https://www.kuwo.cn/'
            }
            r = self.fetch(search_url, headers=kuwo_headers, timeout=8)
            content = r.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            if content.startswith('jsonp'):
                content = content.split('(', 1)[1].rsplit(')', 1)[0]
            
            import json
            data = json.loads(content)
            abslist = data.get('abslist', [])
            if not abslist:
                return ''
            
            first = abslist[0]
            rid = first.get('MUSICRID', '').replace('MUSIC_', '')
            if not rid:
                return ''
            
            quality_list = [320, 128]
            for bitrate in quality_list:
                format_type = 'flac' if bitrate >= 1000 else 'mp3'
                api_url = "https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid=" + str(rid) + "&bitrate=" + str(bitrate) + "&format=" + format_type
                try:
                    r2 = self.fetch(api_url, headers=kuwo_headers, timeout=8)
                    data2 = r2.json()
                    if data2.get('code') == 200 and data2.get('data') and data2['data'].get('url'):
                        return data2['data']['url']
                except Exception:
                    continue
        except Exception as e:
            print("_get_kuwo_play_url error:", e)
        
        return ''

    def _get_lyric(self, hash_val):
        lrc_text = ''

        try:
            song_info = self._get_song_info(hash_val)
            keyword = song_info.get('name', '')
            if song_info.get('artist'):
                keyword = song_info.get('artist', '') + " - " + song_info.get('name', '')
            duration = song_info.get('duration', 0)
            try:
                duration_ms = int(float(duration)) * 1000 if duration else 0
            except:
                duration_ms = 0

            search_url = "http://lyrics.kugou.com/search?ver=1&man=yes&client=mobi&keyword=" + keyword + "&duration=" + str(duration_ms) + "&hash=" + hash_val
            lr = self.fetch(search_url, timeout=5)
            ld = lr.json()
            candidates = ld.get('candidates', [])
            if candidates:
                c = candidates[0]
                lid = c.get('id', '')
                accesskey = c.get('accesskey', '')
                if lid and accesskey:
                    download_url = "http://lyrics.kugou.com/download?ver=1&client=mobi&id=" + str(lid) + "&accesskey=" + accesskey + "&fmt=lrc&charset=utf8"
                    dr = self.fetch(download_url, timeout=5)
                    dd = dr.json()
                    content = dd.get('content', '')
                    if content:
                        try:
                            decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                            lrc_text = decoded
                        except:
                            lrc_text = content
        except Exception as e:
            print("_get_lyric search error:", e)

        if not lrc_text:
            try:
                song_info = self._get_song_info(hash_val)
                keyword = song_info.get('name', '')
                if song_info.get('artist'):
                    keyword = song_info.get('artist', '') + " - " + song_info.get('name', '')
                lrc_api2 = "http://m.kugou.com/app/i/krc.php?cmd=100&keyword=" + keyword + "&hash=" + hash_val.upper() + "&timelength=0"
                lr2 = self.fetch(lrc_api2, headers=self.mobile_headers, timeout=5)
                if lr2.text and '[00:' in lr2.text:
                    lrc_text = lr2.text
            except Exception:
                pass

        if lrc_text and lrc_text.strip() and not lrc_text.strip().startswith('['):
            lines = lrc_text.strip().split('\n')
            formatted = []
            for i, line in enumerate(lines):
                if line and not line.startswith('['):
                    t = i * 3
                    m = t // 60
                    s = t % 60
                    formatted.append("[" + str(m).zfill(2) + ":" + str(s).zfill(2) + ".00]" + line)
                else:
                    formatted.append(line)
            lrc_text = '\n'.join(formatted)

        return lrc_text

    def _get_search_songs(self, keyword, pg=1):
        try:
            pg = int(pg) if pg else 1
            search_url = "http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword=" + keyword + "&page=" + str(pg) + "&pagesize=30&showtype=1"
            res = self.fetch(search_url)
            data = res.json()
            info_list = data.get('data', {}).get('info', [])

            vods = []
            for it in info_list:
                if not isinstance(it, dict):
                    continue
                hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                song, artist = self._get_song_name_artist(it)
                album = it.get('album_name', it.get('albumName', ''))

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    display_name = re.sub(r'<[^>]+>', '', display_name)
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    pic = it.get('album_img', it.get('imgUrl', ''))
                    if pic and not pic.startswith('http'):
                        pic = 'https://' + pic.lstrip('/')
                    if pic and '{size}' in pic:
                        pic = pic.replace('{size}', '400')
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'song_' + hash_val,
                        'vod_pic': pic,
                        'vod_remarks': album or '酷狗音乐',
                    })

            total = data.get('data', {}).get('total', 9999) or 9999
            return {'list': vods, 'page': pg, 'pagecount': (total // 30) + 1, 'limit': 30, 'total': total}
        except Exception as e:
            print("_get_search_songs error:", e)
            return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 30, 'total': 0}

    def _get_mv_list(self, tid, pg):
        vods = []
        try:
            mv_keyword_map = {
                'mv_hot': '热门MV',
                'mv_cn': '华语MV',
                'mv_jp': '日韩MV',
                'mv_us': '欧美MV',
            }
            keyword = mv_keyword_map.get(tid, 'MV')
            search_url = "http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword=" + keyword + "&page=" + str(pg) + "&pagesize=30&showtype=1"
            res = self.fetch(search_url)
            data = res.json()
            info_list = data.get('data', {}).get('info', [])

            for it in info_list:
                if not isinstance(it, dict):
                    continue
                mvhash = it.get('mvhash', it.get('mvHash', ''))
                if not mvhash:
                    continue
                song, artist = self._get_song_name_artist(it)
                pic = it.get('album_img', it.get('imgUrl', ''))
                if pic and not pic.startswith('http'):
                    pic = 'https://' + pic.lstrip('/')
                if pic and '{size}' in pic:
                    pic = pic.replace('{size}', '400')

                display_name = song + " - " + artist if artist else song
                display_name = re.sub(r'<[^>]+>', '', display_name)
                display_name = re.sub(r'[$#]', '', display_name).strip()
                vods.append({
                    'vod_name': display_name + ' [MV]',
                    'vod_id': 'mv_detail_' + mvhash,
                    'vod_pic': pic,
                    'vod_remarks': 'MV',
                    'vod_tag': 'folder'
                })
        except Exception as e:
            print("_get_mv_list error:", e)

        if not vods:
            vods = self._get_default_mv_list()
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_default_mv_list(self):
        default = [
            ("晴天 - 周杰伦 [MV]", "92b86da2e11c3c84de3a944ed12d97f1"),
            ("稻香 - 周杰伦 [MV]", "fa30dad34632aaff8ac33bcf24acc241"),
            ("夜曲 - 周杰伦 [MV]", "14f783ab3068b2cfb40b64f7a79763c8"),
            ("青花瓷 - 周杰伦 [MV]", "dc602a8579c0ac1e2895543ffc2c7daf"),
        ]
        return [{
            'vod_id': 'mv_detail_' + mid,
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': 'MV',
            'vod_tag': 'folder'
        } for name, mid in default]

    def _get_mv_detail(self, mvid, pg):
        return self._get_mv_list('mv_hot', pg)

    def _get_mv_video_detail(self, mvid):
        result = {"list": []}
        try:
            mv_hash = mvid.replace('mv_detail_', '').replace('mv_', '')
            
            song_info = {'name': 'MV', 'artist': ''}
            try:
                search_url = "http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword=" + mv_hash + "&page=1&pagesize=1&showtype=1"
                res = self.fetch(search_url)
                data = res.json()
                info_list = data.get('data', {}).get('info', [])
                if info_list:
                    it = info_list[0]
                    song, artist = self._get_song_name_artist(it)
                    song_info['name'] = song
                    song_info['artist'] = artist
            except:
                pass
            
            mv_name = song_info['name'] + " - " + song_info['artist'] + " [MV]" if song_info['artist'] else song_info['name'] + " [MV]"
            
            mv_play_url = self._get_mv_play_url(mv_hash)
            
            vod = {
                'vod_id': mvid,
                'vod_name': mv_name,
                'vod_pic': '',
                'vod_content': '酷狗音乐MV',
                'vod_remarks': 'MV',
                'vod_play_from': '酷狗MV',
                'vod_play_url': "MV播放$" + mv_hash,
            }
            result['list'] = [vod]
        except Exception as e:
            print("_get_mv_video_detail error:", e)
        return result

    def _get_mv_play_url(self, mvhash):
        try:
            api_url = "https://wwwapi.kugou.com/yy/index.php?r=play/getdata&mvhash=" + mvhash + "&hash=&album_id=&mid=123"
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            if data.get('status') == 1 and data.get('data'):
                d = data['data']
                for k in ['mv_url', 'mp4', 'url', 'hdUrl', 'sdUrl']:
                    v = d.get(k, '')
                    if v and v.startswith('http'):
                        return v
        except Exception:
            pass

        try:
            api_url = "http://m.kugou.com/app/i/mv.php?cmd=100&hash=" + mvhash
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=10)
            data = r.json()
            if data.get('status') == 1 and data.get('mvdata'):
                mvdata = data['mvdata']
                quality_order = ['hd', 'sd', 'sq', 'rq']
                for q in quality_order:
                    q_data = mvdata.get(q, {})
                    if isinstance(q_data, dict):
                        downurl = q_data.get('downurl', '')
                        if downurl and downurl.startswith('http'):
                            return downurl
                        backup = q_data.get('backupdownurl', [])
                        if isinstance(backup, list) and len(backup) > 0:
                            for bu in backup:
                                if bu and bu.startswith('http'):
                                    return bu
        except Exception as e:
            print("_get_mv_play_url m.kugou error:", e)

        return ''

    def destroy(self):
        pass

    def localProxy(self, param):
        return None
