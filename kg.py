import json
import sys
import re
import base64
import requests
sys.path.append('yl-main')
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
        self.kuwo_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.kuwo.cn/'
        }
        self.quality_config = [
            ("标准128K", "128", 128),
            ("高清192K", "192", 192),
            ("超清320K", "320", 320),
            ("无损APE", "ape", 2000),
        ]
        self.wx_gzh = "源力软件汇"
        self.artist_type_map = {
            'artist_hot': '0',
            'artist_cn': '1',
            'artist_us': '2',
            'artist_kr': '6',
            'artist_jp': '5',
            'artist_other': '4',
        }
        self.artist_sex_map = {
            'artist_hot': '0',
            'artist_cn': '0',
            'artist_us': '0',
            'artist_kr': '0',
            'artist_jp': '0',
            'artist_other': '0',
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
            {'type_id': 'artist_cn', 'type_name': '华语歌手'},
            {'type_id': 'artist_us', 'type_name': '欧美歌手'},
            {'type_id': 'artist_kr', 'type_name': '韩国歌手'},
            {'type_id': 'artist_jp', 'type_name': '日本歌手'},
            {'type_id': 'artist_other', 'type_name': '其他歌手'},
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
                artist_type = self.artist_type_map.get(type_key, '0')
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
            else:
                return self._get_song_detail(vid)
        except Exception as e:
            print("detailContent error:", e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}, "lrc": ""}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["url"] = raw_id
                result["header"] = self.mobile_headers
                return result

            hash_val = raw_id
            song_name_hint = ''
            artist_hint = ''

            if '&&' in hash_val:
                hash_val = hash_val.split('&&')[0]

            if '$' in hash_val:
                parts = hash_val.split('$')
                if len(parts) >= 2:
                    name_part = parts[0]
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

            quality_map = {
                '标准128K': (128, 'mp3'),
                '高清192K': (192, 'mp3'),
                '超清320K': (320, 'mp3'),
                '无损APE': (2000, 'ape'),
            }

            clean_flag = flag
            if flag and ' - ' in flag:
                clean_flag = flag.split(' - ')[0].strip()

            play_url = ''
            if clean_flag and clean_flag in quality_map:
                bitrate, fmt = quality_map[clean_flag]
                play_url = self._get_play_url_by_quality(hash_val, bitrate, fmt, song_name_hint, artist_hint)

            if not play_url:
                play_url = self._get_play_url(hash_val, song_name_hint, artist_hint)

            if not play_url:
                result["parse"] = 0
                result["url"] = ""
                return result

            result["url"] = play_url
            result["header"] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.kugou.com/'
            }

            lrc = self._get_lyric(hash_val)
            if lrc:
                result["lrc"] = lrc
                try:
                    ssa_lrc = self._create_ssa_subtitle(lrc)
                    ssa_base64 = base64.b64encode(ssa_lrc.encode('utf-8')).decode('utf-8')
                    ssa_url = "data:text/x-ssa;base64," + ssa_base64

                    result["subs"] = [{
                        "name": "5行歌词",
                        "url": ssa_url,
                        "format": "text/x-ssa",
                        "selected": True
                    }]
                except Exception:
                    pass

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

            info_url = "http://m.kugou.com/plist/list/" + pid + "?json=true&page=1"
            info_res = self.fetch(info_url, headers=self.mobile_headers)
            info_d = info_res.json()
            info_section = info_d.get('info', {}).get('list', {})
            if isinstance(info_section, dict):
                vod_name = info_section.get('specialname', '酷狗歌单')
                vod_pic = info_section.get('imgurl', '')
                if vod_pic and '{size}' in vod_pic:
                    vod_pic = vod_pic.replace('{size}', '400')
                vod_content = info_section.get('intro', '')

            seen_hashes = set()
            for pg in range(1, 500):
                try:
                    api_url = "http://mobilecdn.kugou.com/api/v3/special/song?specialid=" + pid + "&page=" + str(pg) + "&pagesize=100"
                    res = self.fetch(api_url, headers=self.headers)
                    data = res.json()
                    song_list = data.get('data', {}).get('info', [])
                    if not song_list:
                        break
                    new_count = 0
                    for it in song_list:
                        if not isinstance(it, dict):
                            continue
                        hash_val = str(it.get('hash', it.get('Hash', ''))).lower()
                        if hash_val in seen_hashes:
                            continue
                        seen_hashes.add(hash_val)
                        new_count += 1
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
                    if new_count == 0:
                        break
                except Exception:
                    break
        except Exception as e:
            print("_get_playlist_detail error:", e)

        if not play_arr:
            return self._get_playlist_songs_fallback(pid)

        song_list = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        vod = {
            'vod_id': pid,
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_content': '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多\n' + vod_content,
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        if play_pics:
            vod['vod_play_pic'] = '$$$'.join([play_pics[0] for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.5

        return {'list': [vod]}

    def _get_playlist_songs_fallback(self, pid):
        play_arr = []
        search_result = self._get_search_songs('热门歌曲', 1)
        for item in search_result.get('list', []):
            hash_val = item['vod_id'].replace('song_', '')
            play_arr.append(item['vod_name'] + "$" + hash_val)

        song_list = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        vod = {
            'vod_id': pid or 'hot_songs',
            'vod_name': '热门歌曲',
            'vod_pic': '',
            'vod_content': '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多\n酷狗音乐热门歌曲',
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        return {'list': [vod]}

    def _get_playlist_songs(self, pid, pg):
        vods = []
        try:
            api_url = "http://mobilecdn.kugou.com/api/v3/special/song?specialid=" + pid + "&page=" + str(pg) + "&pagesize=30"
            res = self.fetch(api_url, headers=self.headers)
            d = res.json()

            song_list = d.get('data', {}).get('info', [])

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
                        'vod_id': 'pl_detail_' + pid,
                        'vod_pic': albumpic,
                        'vod_remarks': '酷狗音乐',
                    })
        except Exception as e:
            print("_get_playlist_songs error:", e)

        if not vods:
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
                            'vod_id': 'pl_detail_' + pid,
                            'vod_pic': albumpic,
                            'vod_remarks': '酷狗音乐',
                        })
            except Exception as e2:
                print("_get_playlist_songs fallback error:", e2)

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_artist_list(self, artist_type, pg):
        vods = []
        total = 9999
        try:
            api_url = "http://m.kugou.com/singer/list?json=true&page=" + str(pg) + "&pagesize=30&type=" + str(artist_type)
            res = self.fetch(api_url, headers=self.mobile_headers)
            data = res.json()

            singers_data = data.get('singers', {})
            list_data = singers_data.get('list', {})
            if isinstance(list_data, dict):
                info_list = list_data.get('info', [])
            else:
                info_list = []

            for entry in info_list:
                if not isinstance(entry, dict):
                    continue
                singer_list = entry.get('singer', [])
                if not isinstance(singer_list, list) or not singer_list:
                    continue
                it = singer_list[0]
                singer_id = str(it.get('singerid', it.get('id', '')))
                name = it.get('singername', it.get('name', '未知歌手'))
                pic = it.get('imgurl', it.get('singer_pic', it.get('img', '')))
                if pic and not pic.startswith('http'):
                    pic = 'https://' + pic.lstrip('/')
                if pic and '{size}' in pic:
                    pic = pic.replace('{size}', '400')

                if not singer_id:
                    continue

                name = re.sub(r'<[^>]+>', '', str(name)).strip()
                songcount = it.get('songcount', '')
                remarks = str(songcount) + '首歌曲' if songcount else '歌手'
                vods.append({
                    'vod_name': name,
                    'vod_id': 'artist_detail_' + singer_id,
                    'vod_pic': pic,
                    'vod_remarks': remarks,
                    'vod_tag': 'folder'
                })

            total = singers_data.get('total', 9999) or 9999
            if total == 0:
                total = 9999
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
            ("周杰伦", "3520"), ("林俊杰", "1574"), ("陈奕迅", "3283"),
            ("邓紫棋", "4490"), ("薛之谦", "3894"), ("毛不易", "119235"),
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

            all_songs = []
            seen_hashes = set()
            for pg in range(1, 200):
                songs_result = self._get_v3_artist_songs(aid, pg, 100)
                if not songs_result:
                    break
                new_count = 0
                for it in songs_result:
                    h = str(it.get('hash', '')).lower()
                    if h and h not in seen_hashes:
                        seen_hashes.add(h)
                        all_songs.append(it)
                        new_count += 1
                if new_count == 0:
                    break

            for it in all_songs:
                hash_val = str(it.get('hash', '')).lower()
                song, artist = self._get_song_name_artist(it)
                albumpic = it.get('imgurl', it.get('album_img', it.get('pic', '')))
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if hash_val and song:
                    display_name = song + " - " + artist if artist and artist != song else song
                    if not artist and artist_name:
                        display_name = song + " - " + artist_name
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

        song_list = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        vod = {
            'vod_id': artist_id,
            'vod_name': artist_name or '歌手',
            'vod_pic': artist_pic or (play_pics[0] if play_pics else ''),
            'vod_content': "微信公众号：" + self.wx_gzh + "\n福利多多，精彩多多\n共 " + str(len(play_arr)) + " 首歌曲",
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_actor': artist_name,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        if play_pics:
            vod['vod_play_pic'] = '$$$'.join([play_pics[0] for _ in qualities])
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
                        'vod_id': 'artist_detail_' + aid,
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

        song_list = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        vod = {
            'vod_id': bang_id,
            'vod_name': bang_name,
            'vod_pic': bang_pic or (play_pics[0] if play_pics else ''),
            'vod_content': '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多',
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        if play_pics:
            vod['vod_play_pic'] = '$$$'.join([play_pics[0] for _ in qualities])
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
                        'vod_id': 'bang_detail_' + bang_id,
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

            for q_name, q_type, q_br in self.quality_config:
                play_from_arr.append(q_name + ' - ' + self.wx_gzh)
                play_url_arr.append(display_name + "$" + hash_val)

            lrc = self._get_lyric(hash_val)
            content = "微信公众号：" + self.wx_gzh + "\n福利多多，精彩多多\n歌曲：" + song_name + "\n歌手：" + artist + "\n专辑：" + album + "\n来源：酷狗音乐"
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
            if pic:
                vod['vod_play_pic'] = '$$$'.join([pic for _ in play_from_arr])
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
                "vod_content": '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多\n酷狗音乐',
                "vod_remarks": '酷狗音乐',
                "vod_actor": '',
                "vod_play_from": '$$$'.join([q[0] + ' - ' + self.wx_gzh for q in self.quality_config]),
                "vod_play_url": '$$$'.join(["歌曲_" + hash_val[:8] + "$" + hash_val for _ in self.quality_config]),
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

    def _get_play_url_by_quality(self, hash_val, bitrate, fmt, song_name_hint='', artist_hint=''):
        song_name = song_name_hint
        artist = artist_hint

        if not song_name:
            song_info = self._get_song_info(hash_val)
            song_name = song_info.get('name', '')
            artist = song_info.get('artist', '')

        if not song_name:
            return self._get_play_url(hash_val, song_name_hint, artist_hint)

        keyword = song_name
        if artist:
            keyword = artist + " " + song_name

        try:
            search_url = "https://search.kuwo.cn/r.s?client=kt&all=" + keyword + "&pn=0&rn=5&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            r = self.fetch(search_url, headers=self.kuwo_headers, timeout=8)
            content = r.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            if content.startswith('jsonp'):
                content = content.split('(', 1)[1].rsplit(')', 1)[0]

            data = json.loads(content)
            abslist = data.get('abslist', [])
            if not abslist:
                return ''

            first = abslist[0]
            rid = first.get('MUSICRID', '').replace('MUSIC_', '')
            if not rid:
                return ''

            format_type = 'flac' if bitrate >= 1000 else 'mp3'
            api_url = "https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid=" + str(rid) + "&bitrate=" + str(bitrate) + "&format=" + format_type
            r2 = self.fetch(api_url, headers=self.kuwo_headers, timeout=8)
            data2 = r2.json()
            if data2.get('code') == 200 and data2.get('data') and data2['data'].get('url'):
                return data2['data']['url']
        except Exception:
            pass

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
            r = self.fetch(search_url, headers=self.kuwo_headers, timeout=8)
            content = r.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            if content.startswith('jsonp'):
                content = content.split('(', 1)[1].rsplit(')', 1)[0]

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
                    r2 = self.fetch(api_url, headers=self.kuwo_headers, timeout=8)
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

    def _format_time(self, seconds):
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def _create_ssa_subtitle(self, lrc_text):
        lines = []
        pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)'

        for line in lrc_text.split('\n'):
            match = re.match(pattern, line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                ms_str = match.group(3)
                if len(ms_str) == 3:
                    hundredths = int(ms_str) // 10
                else:
                    hundredths = int(ms_str)
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
Style: WAITING_TOP2,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,180,1
Style: WAITING_TOP1,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,260,1
Style: PLAYING_CENTER,Roboto,60,&H0000FF00,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,2,0,0,340,1
Style: PLAYED_BOTTOM1,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,420,1
Style: PLAYED_BOTTOM2,Roboto,55,&H0000FFFF,&H00808080,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,1,2,0,0,500,1

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
            current_end = lines[i + 1]['start'] if i + 1 < len(lines) else current['start'] + 5.0

            wait2 = lines[i + 2] if i + 2 < len(lines) else None
            wait1 = lines[i + 1] if i + 1 < len(lines) else None
            played1 = lines[i - 1] if i - 1 >= 0 else None
            played2 = lines[i - 2] if i - 2 >= 0 else None

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

    def destroy(self):
        pass

    def localProxy(self, param):
        return None
