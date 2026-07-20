# -*- coding: utf-8 -*-
import json
import sys
import re
import base64
import requests
sys.path.append('yl-main')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "酷我音乐"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'Referer': 'https://m.kuwo.cn/'
        }
        self.quality_config = [
            ("无损APE", 2000, "ape"),
            ("超清320K", 320, "mp3"),
            ("高清192K", 192, "mp3"),
            ("标准128K", 128, "mp3"),
        ]
        self.DEFAULT_SONG_PIC = "https://img.kuwo.cn/star/albumcover/500/673009.jpg"
        self.classes = [
            {'type_id': 'pl_hot', 'type_name': '热门歌单'},
            {'type_id': 'pl_new', 'type_name': '新歌歌单'},
            {'type_id': 'pl_dj', 'type_name': 'DJ歌单'},
            {'type_id': 'pl_classic', 'type_name': '经典歌单'},
            {'type_id': 'artist_1', 'type_name': '华语男歌手'},
            {'type_id': 'artist_2', 'type_name': '华语女歌手'},
            {'type_id': 'artist_3', 'type_name': '华语组合'},
            {'type_id': 'artist_4', 'type_name': '日韩男歌手'},
            {'type_id': 'artist_5', 'type_name': '日韩女歌手'},
            {'type_id': 'artist_6', 'type_name': '日韩组合'},
            {'type_id': 'artist_7', 'type_name': '欧美男歌手'},
            {'type_id': 'artist_8', 'type_name': '欧美女歌手'},
            {'type_id': 'artist_9', 'type_name': '欧美组合'},
            {'type_id': 'bang_hot', 'type_name': '酷我热歌榜'},
            {'type_id': 'bang_new', 'type_name': '酷我新歌榜'},
            {'type_id': 'bang_up', 'type_name': '酷我飙升榜'},
            {'type_id': 'bang_douyin', 'type_name': '抖音热歌榜'},
            {'type_id': 'bang_classic', 'type_name': '经典怀旧榜'},
            {'type_id': 'bang_tv', 'type_name': '影视金曲榜'},
            {'type_id': 'bang_dj', 'type_name': 'DJ舞曲榜'},
        ]

    def isVideoFormat(self, url):
        return url.endswith(('.mp4', '.m3u8', '.flv', '.mkv'))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {}
        result['class'] = self.classes
        result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('pl_hot', 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
            if tid.startswith('pl_detail_'):
                pid = tid.replace('pl_detail_', '')
                return self._get_playlist_songs(pid, pg)
            elif tid.startswith('pl_'):
                return self._get_playlist_list(tid, pg)
            elif tid.startswith('artist_detail_'):
                aid = tid.replace('artist_detail_', '')
                return self._get_artist_songs(aid, pg)
            elif tid.startswith('artist_'):
                cat_id = tid.replace('artist_', '')
                return self._get_artist_list(cat_id, pg)
            elif tid.startswith('bang_detail_'):
                bid = tid.replace('bang_detail_', '')
                return self._get_bang_songs(bid, pg)
            elif tid.startswith('bang_'):
                return self._get_bang_list(tid, pg)
            else:
                return self._get_playlist_list('pl_hot', pg)
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {'list': self._default_playlists(), 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 999}

    def detailContent(self, ids):
        try:
            vid = ids[0].strip()
            if vid.startswith('song_'):
                return self._get_song_detail(vid)
            elif vid.startswith('artist_detail_'):
                artist_id = vid.replace('artist_detail_', '')
                return self._get_artist_detail(f'artist_{artist_id}')
            elif vid.startswith('artist_'):
                return self._get_artist_detail(vid)
            elif vid.startswith('pl_detail_'):
                pid = vid.replace('pl_detail_', '')
                return self._get_playlist_detail(pid)
            elif vid.startswith('bang_detail_'):
                bang_id = vid.replace('bang_detail_', '')
                return self._get_bang_detail(bang_id)
            elif vid.startswith('bang_'):
                bang_id = vid.replace('bang_', '')
                return self._get_bang_detail(bang_id)
            else:
                return self._get_playlist_detail(vid)
        except Exception as e:
            print(f"detailContent error: {e}")
            return self._get_playlist_detail('489927')

    def _get_bang_detail(self, bang_id):
        result = self._get_playlist_detail(bang_id)
        bang_name_map = {
            '489927': '酷我热歌榜',
            '489928': '酷我新歌榜',
            '489929': '酷我飙升榜',
            '490022': '抖音热歌榜',
            '530769': '经典怀旧榜',
            '530770': '影视金曲榜',
            '534778': 'DJ舞曲榜',
        }
        if result.get('list') and len(result['list']) > 0:
            bang_name = bang_name_map.get(bang_id, '酷我排行榜')
            result['list'][0]['vod_name'] = bang_name
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = raw_id
                result["header"] = self.mobile_headers
                return result

            rid = raw_id

            if '&&' in rid:
                rid = rid.split('&&')[0]

            if '$' in rid:
                parts = rid.split('$')
                for part in reversed(parts):
                    if part.startswith('http'):
                        pass
                    elif part.isdigit() or part.isnumeric():
                        rid = part
                        break
                else:
                    if len(parts) > 1:
                        rid = parts[-1]

            if rid.startswith('song_'):
                rid = rid.replace('song_', '')

            if self.isVideoFormat(rid):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = rid
                result["header"] = self.headers
                return result

            if not (rid.isdigit() or rid.isnumeric()):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                return result

            quality_map = {
                '标准128K': (128, 'mp3'),
                '高清192K': (192, 'mp3'),
                '超清320K': (320, 'mp3'),
                '无损APE': (2000, 'ape'),
            }

            unsupported_formats = ['ape']

            def get_valid_url(rid, target_bitrate, target_format):
                play_url = self._get_song_url(rid, target_bitrate)
                if play_url and play_url.startswith('http'):
                    url_lower = play_url.lower()
                    for fmt in unsupported_formats:
                        if f'.{fmt}' in url_lower or f'format${fmt}' in url_lower or f'format={fmt}' in url_lower:
                            return None
                    return play_url
                return None

            play_url = ""
            if flag and flag in quality_map:
                bitrate, fmt = quality_map[flag]
                play_url = get_valid_url(rid, bitrate, fmt)
                if not play_url:
                    for q_name, (br, f) in quality_map.items():
                        if q_name != flag:
                            play_url = get_valid_url(rid, br, f)
                            if play_url:
                                break

            if not play_url:
                for q_name, (br, f) in quality_map.items():
                    play_url = get_valid_url(rid, br, f)
                    if play_url:
                        break

            if not play_url:
                play_url = self._get_song_url_with_fallback(rid)

            if not play_url:
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                return result

            lrc = self._get_lyric(rid)

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
            result["url"] = play_url
            result["header"] = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.kuwo.cn/"
            }

        except Exception as e:
            print(f"playerContent error: {e}")
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}

        return result

    def searchContent(self, key, quick, pg="1"):
        return self._get_search_songs(key, pg)

    def searchContentPage(self, key, quick, pg):
        return self._get_search_songs(key, pg)

    def fetch(self, url, headers=None, timeout=10):
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)
        return requests.get(url, headers=req_headers, timeout=timeout, verify=False)

    def _default_playlists(self):
        default = [
            ("华语流行精选", "123456789"), ("治愈系轻音乐", "234567890"),
            ("经典老歌回忆", "345678901"), ("深夜情感电台", "456789012"),
            ("欧美经典金曲", "567890123"), ("抖音热门神曲", "678901234"),
            ("开车必听歌曲", "789012345"), ("学习工作专注", "890123456"),
            ("运动健身歌单", "901234567"), ("日系清新音乐", "012345678"),
        ]
        return [{
            'vod_id': f'pl_detail_{pid}',
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': '酷我歌单',
        } for name, pid in default]

    def _default_artists(self):
        default = [
            ("周杰伦", "336"), ("林俊杰", "1119"), ("陈奕迅", "2116"),
            ("邓紫棋", "5199"), ("薛之谦", "5781"), ("毛不易", "12138267"),
            ("李荣浩", "4292"), ("华晨宇", "8736"), ("张学友", "2117"),
            ("王菲", "9643"), ("五月天", "13193"), ("Taylor Swift", "443818"),
        ]
        return [{
            'vod_id': f'artist_detail_{aid}',
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': '歌手',
        } for name, aid in default]

    def _default_bang_list(self):
        bang_map = {
            'bang_hot': ('489927', '酷我热歌榜'),
            'bang_new': ('489928', '酷我新歌榜'),
            'bang_up': ('489929', '酷我飙升榜'),
            'bang_douyin': ('490022', '抖音热歌榜'),
            'bang_classic': ('530769', '经典怀旧榜'),
            'bang_tv': ('530770', '影视金曲榜'),
            'bang_dj': ('534778', 'DJ舞曲榜'),
        }
        vods = []
        for tid, (bid, bname) in bang_map.items():
            vods.append({
                'vod_id': f'bang_detail_{bid}',
                'vod_name': bname,
                'vod_pic': '',
                'vod_remarks': '排行榜',
            })
        return vods

    def _get_playlist_list(self, tid, pg):
        try:
            pl_map = {
                'pl_hot': 'hot',
                'pl_new': 'new',
                'pl_dj': 'dj',
                'pl_classic': 'classic',
            }
            order = pl_map.get(tid, 'hot')
            api_url = f"http://wapi.kuwo.cn/api/pc/classify/playlist/getRcmPlayList?loginUid=0&loginSid=0&appUid=76039576&rn=30&order={order}&pn={pg}"
            res = self.fetch(api_url)
            data = res.json()
            data_list = data.get('data', {}).get('data', []) or []
            vods = self._parse_playlist(data_list)
            if vods:
                total = data.get('data', {}).get('total', 999) or 999
                return {'list': vods, 'page': pg, 'pagecount': (total // 30) + 1, 'limit': 30, 'total': total}
        except Exception as e:
            print(f"_get_playlist_list error: {e}")
        return {'list': self._default_playlists(), 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 999}

    def _parse_playlist(self, data_list):
        vods = []
        for it in data_list:
            name = it.get('name', it.get('title', '未命名歌单'))
            vid = str(it.get('id', it.get('pid', '')))
            pic = it.get('img', it.get('pic', it.get('cover', '')))
            remarks = it.get('info', it.get('uname', it.get('userName', '')))

            if not vid:
                continue

            vods.append({
                'vod_name': name,
                'vod_id': f'pl_detail_{vid}',
                'vod_pic': pic,
                'vod_remarks': remarks or '酷我歌单',
            })
        return vods

    def _get_playlist_detail(self, pid):
        play_arr = []
        pic_arr = []
        vod_name = '酷我歌单'
        vod_pic = ''
        vod_content = ''

        try:
            api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={pid}&pn=0&rn=100&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
            res = self.fetch(api_url)
            d = res.json()

            vod_name = d.get('name', d.get('title', '酷我歌单'))
            vod_pic = d.get('pic', d.get('img', ''))
            vod_content = '微信公众号：源力软件汇\n' + d.get('info', d.get('desc', ''))
            total = d.get('total', 0)
            music_list = d.get('musiclist', [])

            for it in music_list:
                rid = str(it.get('id', '')) if it.get('id') is not None else ''
                song = str(it.get('name', it.get('SONGNAME', it.get('displaysongname', ''))))
                artist = str(it.get('artist', it.get('ARTIST', it.get('FARTIST', it.get('displayartistname', '')))))
                albumpic = it.get('albumpic', '')

                if rid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    play_arr.append(f"{display_name}${rid}")
                    pic_arr.append(albumpic if albumpic else self.DEFAULT_SONG_PIC)

            if total > 100:
                pages = (total + 99) // 100
                for pg in range(1, min(pages, 20)):
                    try:
                        api_url2 = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={pid}&pn={pg * 100}&rn=100&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
                        res2 = self.fetch(api_url2)
                        d2 = res2.json()
                        music_list2 = d2.get('musiclist', [])
                        if not music_list2:
                            break
                        for it in music_list2:
                            rid = str(it.get('id', '')) if it.get('id') is not None else ''
                            song = str(it.get('name', it.get('SONGNAME', it.get('displaysongname', ''))))
                            artist = str(it.get('artist', it.get('ARTIST', it.get('FARTIST', it.get('displayartistname', '')))))
                            albumpic = it.get('albumpic', '')
                            if rid and song:
                                display_name = f"{song} - {artist}" if artist else song
                                display_name = re.sub(r'[$#]', '', display_name).strip()
                                play_arr.append(f"{display_name}${rid}")
                                pic_arr.append(albumpic if albumpic else self.DEFAULT_SONG_PIC)
                    except Exception:
                        break
        except Exception as e:
            print(f"_get_playlist_detail error: {e}")

        if not play_arr:
            search_result = self._get_search_songs('热门歌曲', 1)
            for item in search_result.get('list', []):
                rid = item['vod_id'].replace('song_', '')
                play_arr.append(f"{item['vod_name']}${rid}")
                pic_arr.append(item.get('vod_pic', '') or self.DEFAULT_SONG_PIC)
            vod_name = vod_name or '热门歌曲'

        song_list = '#'.join(play_arr)
        pic_list = '#'.join(pic_arr)
        qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])
        vod_play_pic = '$$$'.join([pic_list for _ in qualities])

        vod = {
            'vod_id': pid,
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_content': vod_content,
            'vod_remarks': f"歌曲 : {len(play_arr)}首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
            'vod_play_pic': vod_play_pic,
            'vod_play_pic_ratio': 1.0,
        }

        return {'list': [vod]}

    def _get_playlist_songs(self, pid, pg):
        vods = []
        try:
            pn = (pg - 1) * 30
            api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={pid}&pn={pn}&rn=30&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
            res = self.fetch(api_url)
            d = res.json()
            music_list = d.get('musiclist', [])

            for it in music_list:
                rid = str(it.get('id', '')) if it.get('id') is not None else ''
                song = str(it.get('name', it.get('SONGNAME', '')))
                artist = str(it.get('artist', it.get('ARTIST', it.get('FARTIST', ''))))
                albumpic = it.get('albumpic', '')

                if rid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{rid}',
                        'vod_pic': albumpic,
                        'vod_remarks': '酷我音乐',
                    })
        except Exception as e:
            print(f"_get_playlist_songs error: {e}")

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_artist_list(self, cat_id, pg):
        vods = []
        try:
            api_url = f"http://wapi.kuwo.cn/api/www/artist/artistInfo?category={cat_id}&prefix=&pn={pg}&rn=30"
            res = self.fetch(api_url)
            data = res.json()
            artist_list = data.get('data', {}).get('artistList', []) or []

            for it in artist_list:
                artist_id = str(it.get('id', ''))
                name = it.get('name', '未知歌手')
                pic = it.get('pic', it.get('img', it.get('avatar', '')))

                if not artist_id:
                    continue

                vods.append({
                    'vod_name': name,
                    'vod_id': f'artist_detail_{artist_id}',
                    'vod_pic': pic,
                    'vod_remarks': it.get('country', it.get('company', '歌手')),
                })
        except Exception as e:
            print(f"_get_artist_list error: {e}")

        if not vods:
            vods = self._default_artists()
        return {
            'list': vods,
            'page': pg,
            'pagecount': 99,
            'limit': 30,
            'total': 9999
        }

    def _get_artist_detail(self, vid):
        play_arr = []
        pic_arr = []
        artist_name = ''

        try:
            artist_id = vid.replace('artist_', '')
            api_url = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={artist_id}&pn=1&rn=100"
            res = self.fetch(api_url)
            data = res.json()

            music_data = data.get('data', {})
            music_list = music_data.get('list', [])
            total = music_data.get('total', 0)

            for it in music_list:
                rid = str(it.get('rid', it.get('id', '')))
                song = str(it.get('name', ''))
                artist = str(it.get('artist', it.get('singer', '')))
                albumPic = it.get('albumPic', it.get('pic', ''))

                if not artist_name and artist:
                    artist_name = artist

                if rid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    play_arr.append(f"{display_name}${rid}")
                    pic_arr.append(albumPic if albumPic else self.DEFAULT_SONG_PIC)

            if total > 100:
                pages = (total + 99) // 100
                for pg in range(2, min(pages + 1, 50)):
                    try:
                        api_url2 = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={artist_id}&pn={pg}&rn=100"
                        res2 = self.fetch(api_url2)
                        data2 = res2.json()
                        music_data2 = data2.get('data', {})
                        music_list2 = music_data2.get('list', [])
                        if not music_list2:
                            break
                        for it in music_list2:
                            rid = str(it.get('rid', it.get('id', '')))
                            song = str(it.get('name', ''))
                            artist = str(it.get('artist', it.get('singer', '')))
                            albumPic = it.get('albumPic', it.get('pic', ''))
                            if rid and song:
                                display_name = f"{song} - {artist}" if artist else song
                                display_name = re.sub(r'[$#]', '', display_name).strip()
                                play_arr.append(f"{display_name}${rid}")
                                pic_arr.append(albumPic if albumPic else self.DEFAULT_SONG_PIC)
                    except Exception:
                        break

            if not artist_name:
                artist_name = f'歌手_{artist_id}'
        except Exception as e:
            print(f"_get_artist_detail error: {e}")

        if not play_arr:
            search_result = self._get_search_songs('周杰伦', 1)
            for item in search_result.get('list', []):
                rid = item['vod_id'].replace('song_', '')
                play_arr.append(f"{item['vod_name']}${rid}")
                pic_arr.append(item.get('vod_pic', '') or self.DEFAULT_SONG_PIC)
            artist_name = artist_name or '热门歌手'

        song_list = '#'.join(play_arr)
        pic_list = '#'.join(pic_arr)
        qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])
        vod_play_pic = '$$$'.join([pic_list for _ in qualities])

        vod = {
            'vod_id': vid,
            'vod_name': artist_name,
            'vod_pic': '',
            'vod_content': f"微信公众号：源力软件汇\n共 {len(play_arr)} 首歌曲",
            'vod_remarks': f"歌曲 : {len(play_arr)}首",
            'vod_actor': artist_name,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
            'vod_play_pic': vod_play_pic,
            'vod_play_pic_ratio': 1.0,
        }

        return {'list': [vod]}

    def _get_artist_songs(self, artist_id, pg):
        vods = []
        try:
            api_url = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={artist_id}&pn={pg}&rn=30"
            res = self.fetch(api_url)
            data = res.json()

            music_data = data.get('data', {})
            music_list = music_data.get('list', [])

            for it in music_list:
                rid = str(it.get('rid', it.get('id', '')))
                song = str(it.get('name', ''))
                artist = str(it.get('artist', it.get('singer', '')))
                albumPic = it.get('albumPic', it.get('pic', ''))

                if rid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{rid}',
                        'vod_pic': albumPic,
                        'vod_remarks': '酷我音乐',
                    })
        except Exception as e:
            print(f"_get_artist_songs error: {e}")

        if not vods:
            search_result = self._get_search_songs('周杰伦', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_bang_list(self, tid, pg):
        vods = []
        try:
            bang_map = {
                'bang_hot': ('489927', '酷我热歌榜'),
                'bang_new': ('489928', '酷我新歌榜'),
                'bang_up': ('489929', '酷我飙升榜'),
                'bang_douyin': ('490022', '抖音热歌榜'),
                'bang_classic': ('530769', '经典怀旧榜'),
                'bang_tv': ('530770', '影视金曲榜'),
                'bang_dj': ('534778', 'DJ舞曲榜'),
            }
            bang_info = bang_map.get(tid, ('489927', '酷我热歌榜'))
            bang_id = bang_info[0]
            bang_name = bang_info[1]
            api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={bang_id}&pn=0&rn=1&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
            res = self.fetch(api_url)
            d = res.json()
            pic = d.get('pic', d.get('img', ''))
            vods = [{
                'vod_name': bang_name,
                'vod_id': f'bang_detail_{bang_id}',
                'vod_pic': pic,
                'vod_remarks': '排行榜',
            }]
        except Exception as e:
            print(f"_get_bang_list error: {e}")

        if not vods:
            vods = self._default_bang_list()
        return {'list': vods, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(vods)}

    def _get_bang_songs(self, bang_id, pg):
        vods = []
        try:
            api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={bang_id}&pn={pg - 1}&rn=30&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
            res = self.fetch(api_url)
            d = res.json()
            music_list = d.get('musiclist', [])

            for it in music_list:
                rid = str(it.get('id', '')) if it.get('id') is not None else ''
                song = str(it.get('name', it.get('SONGNAME', '')))
                artist = str(it.get('artist', it.get('ARTIST', it.get('FARTIST', ''))))
                albumpic = it.get('albumpic', '')

                if rid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{rid}',
                        'vod_pic': albumpic,
                        'vod_remarks': '排行榜',
                    })
        except Exception as e:
            print(f"_get_bang_songs error: {e}")

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_song_detail(self, vid):
        result = {"list": []}
        try:
            song_id = vid.replace("song_", "")
            song_info = self._get_song_info(song_id)
            song_name = song_info.get('name', '')
            artist = song_info.get('artist', '')
            album = song_info.get('album', '')
            pic = song_info.get('pic', '') or self.DEFAULT_SONG_PIC

            if not song_name:
                song_name = f"歌曲_{song_id}"

            song_name = re.sub(r'[$#]', '', song_name).strip()
            artist = re.sub(r'[$#]', '', artist).strip() if artist else ''

            play_from_arr = []
            play_url_arr = []
            play_pic_arr = []

            for q_name, bitrate, fmt in self.quality_config:
                try:
                    play_url = self._get_song_url(song_id, bitrate)
                    if play_url:
                        display_name = f"{song_name} - {artist}" if artist else song_name
                        play_from_arr.append(q_name)
                        play_url_arr.append(f"{display_name}${song_id}")
                        play_pic_arr.append(pic)
                except Exception:
                    continue

            if not play_url_arr:
                play_from_arr.append('标准音质')
                display_name = f"{song_name} - {artist}" if artist else song_name
                play_url_arr.append(f"{display_name}${song_id}")
                play_pic_arr.append(pic)

            lrc = self._get_lyric(song_id)
            content = f"微信公众号：源力软件汇\n歌曲：{song_name}\n歌手：{artist}\n专辑：{album}\n来源：酷我音乐"
            if lrc:
                lrc_lines = lrc.split('\n')
                clean_lines = []
                for line in lrc_lines:
                    clean_line = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
                    if clean_line:
                        clean_lines.append(clean_line)
                if clean_lines:
                    content += "\n\n--- 歌词 ---\n" + '\n'.join(clean_lines)

            vod = {
                "vod_id": vid,
                "vod_name": song_name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_remarks": album or '酷我音乐',
                "vod_actor": artist,
                "vod_play_from": '$$$'.join(play_from_arr),
                "vod_play_url": '$$$'.join(play_url_arr),
            }
            if play_pic_arr:
                vod['vod_play_pic'] = '$$$'.join(play_pic_arr)
                vod['vod_play_pic_ratio'] = 1.0

            result["list"] = [vod]
        except Exception as e:
            print(f"_get_song_detail error: {e}")

        if not result.get('list'):
            song_id = vid.replace("song_", "")
            vod = {
                "vod_id": vid,
                "vod_name": f"歌曲_{song_id}",
                "vod_pic": self.DEFAULT_SONG_PIC,
                "vod_content": '微信公众号：源力软件汇',
                "vod_remarks": '酷我音乐',
                "vod_actor": '',
                "vod_play_from": '标准音质',
                "vod_play_url": f"歌曲_{song_id}${song_id}",
                "vod_play_pic": self.DEFAULT_SONG_PIC,
                "vod_play_pic_ratio": 1.0,
            }
            result["list"] = [vod]

        return result

    def _get_song_info(self, rid):
        try:
            api_url = f"https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}"
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=5)
            data = r.json()
            if data.get('data') and data['data'].get('songinfo'):
                info = data['data']['songinfo']
                return {
                    'name': info.get('songName', ''),
                    'artist': info.get('artist', ''),
                    'album': info.get('album', ''),
                    'pic': info.get('pic', ''),
                    'duration': info.get('duration', ''),
                }
        except Exception:
            pass

        try:
            search_url = f"https://search.kuwo.cn/r.s?client=kt&all=MUSIC_{rid}&pn=0&rn=1&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            res = self.fetch(search_url)
            content = res.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            json_data = json.loads(content)
            abslist = json_data.get('abslist', [])
            if abslist:
                it = abslist[0]
                return {
                    'name': it.get('SONGNAME', it.get('NAME', '')),
                    'artist': it.get('ARTIST', it.get('FARTIST', '')),
                    'album': it.get('ALBUM', ''),
                    'pic': it.get('hts_MVPIC', '') or it.get('hts_ALBUMPIC', ''),
                    'duration': it.get('DURATION', ''),
                }
        except Exception:
            pass
        return {}

    def _get_song_url_with_fallback(self, rid):
        methods = [
            self._get_song_url_v1,
            self._get_song_url_v2,
            self._get_song_url_v3,
        ]
        for method in methods:
            try:
                url = method(rid)
                if url and url.startswith('http'):
                    return url
            except Exception:
                continue
        return ''

    def _get_song_url_v1(self, rid):
        try:
            api_url = f"https://www.kuwo.cn/api/v1/www/music/playInfo?mid={rid}"
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            if data.get('data') and data['data'].get('url'):
                return data['data']['url']
        except Exception:
            pass
        return ''

    def _get_song_url_v2(self, rid):
        try:
            api_url = f"https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}"
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=8)
            data = r.json()
            if data.get('data') and data['data'].get('songinfo'):
                info = data['data']['songinfo']
                if info.get('rid'):
                    return self._get_song_url_v3(str(info['rid']))
            if data.get('data') and data['data'].get('url'):
                return data['data']['url']
        except Exception:
            pass
        return ''

    def _get_song_url_v3(self, rid):
        try:
            api_url = f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={rid}&br=320kmp3&format=mp3"
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=8)
            data = r.json()
            if data.get('data') and data['data'].get('url'):
                return data['data']['url']
        except Exception:
            pass
        return ''

    def _get_song_url(self, rid, bitrate=320):
        try:
            format_type = 'mp3'
            api_url = f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={rid}&bitrate={bitrate}&format={format_type}"
            r = self.fetch(api_url, headers=self.mobile_headers, timeout=5)
            data = r.json()
            if data.get('code') == 200 or data.get('data'):
                return data.get('data', {}).get('url', '')
        except Exception as e:
            pass
        return ''

    def _get_lyric(self, rid):
        lrc_text = ''

        try:
            lrc_api = f"https://kuwo.cn/openapi/v1/www/lyric/getlyric?musicId={rid}"
            r = self.fetch(lrc_api, timeout=8)
            d = r.json()
            if d.get('data') and d['data'].get('lrclist'):
                lrclist = d['data']['lrclist']
                if lrclist and len(lrclist) > 0:
                    lines = []
                    for item in lrclist:
                        time_val = float(item.get('time', 0))
                        minute = int(time_val // 60)
                        second = int(time_val % 60)
                        millisecond = int((time_val % 1) * 100)
                        lyric = item.get('lineLyric', '')
                        if lyric:
                            lines.append(f"[{minute:02d}:{second:02d}.{millisecond:02d}]{lyric}")
                    if lines:
                        lrc_text = '\n'.join(lines)
        except Exception:
            pass

        if not lrc_text:
            try:
                api_url = f"https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}"
                r = self.fetch(api_url, headers=self.mobile_headers, timeout=8)
                data = r.json()
                if data.get('data') and data['data'].get('lrclist'):
                    lrclist = data['data']['lrclist']
                    if lrclist and len(lrclist) > 0:
                        lines = []
                        for item in lrclist:
                            time_val = float(item.get('time', 0))
                            minute = int(time_val // 60)
                            second = int(time_val % 60)
                            millisecond = int((time_val % 1) * 100)
                            lyric = item.get('lineLyric', '')
                            if lyric:
                                lines.append(f"[{minute:02d}:{second:02d}.{millisecond:02d}]{lyric}")
                        if lines:
                            lrc_text = '\n'.join(lines)
            except Exception:
                pass

        if not lrc_text:
            try:
                lrc_api2 = f"https://www.kuwo.cn/api/v1/www/music/playInfo?mid={rid}"
                r = self.fetch(lrc_api2, timeout=8)
                d = r.json()
                if d.get('data') and d['data'].get('lrc'):
                    lrc_text = d['data']['lrc']
            except Exception:
                pass

        if lrc_text and not lrc_text.strip().startswith('['):
            lines = lrc_text.strip().split('\n')
            formatted = []
            for i, line in enumerate(lines):
                if line and not line.startswith('['):
                    t = i * 3
                    m = t // 60
                    s = t % 60
                    formatted.append(f"[{m:02d}:{s:02d}.00]{line}")
                else:
                    formatted.append(line)
            lrc_text = '\n'.join(formatted)

        return lrc_text

    def _get_search_songs(self, keyword, pg=1):
        try:
            pg = int(pg)
            search_url = f"https://search.kuwo.cn/r.s?client=kt&all={keyword}&pn={pg - 1}&rn=30&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            res = self.fetch(search_url)
            content = res.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            data = json.loads(content)
            abslist = data.get('abslist', [])

            vods = []
            for it in abslist:
                dc_target_id = it.get('DC_TARGETID')
                if dc_target_id and it.get('DC_TARGETTYPE') == 'music':
                    rid = str(dc_target_id)
                    song = str(it.get('SONGNAME', it.get('NAME', '')))
                    artist = str(it.get('ARTIST', it.get('FARTIST', '')))
                    pic_url = it.get('hts_MVPIC', '') or it.get('hts_ALBUMPIC', '')
                    album = it.get('ALBUM', '')

                    if rid and song:
                        display_name = f"{song} - {artist}" if artist else song
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        vods.append({
                            'vod_name': display_name,
                            'vod_id': f'song_{rid}',
                            'vod_pic': pic_url,
                            'vod_remarks': album or '酷我音乐',
                        })

            return {'list': vods, 'page': pg, 'pagecount': 999, 'limit': 30, 'total': 99999}
        except Exception as e:
            print(f"_get_search_songs error: {e}")
            return {'list': [], 'page': pg}

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

    def destroy(self):
        pass

    def localProxy(self, param):
        return None
