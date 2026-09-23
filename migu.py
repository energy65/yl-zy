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
        return "咪咕音乐"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://music.migu.cn/'
        }
        self.api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://h5.nf.migu.cn',
            'Referer': 'https://h5.nf.migu.cn/',
            'birth': 'h5page',
            'signature': '1',
            'ua': 'Android_migu',
            'version': '6.8.8',
            'channel': '014021I',
            'subchannel': '014021I',
        }
        self.search_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'ua': 'Android_migu',
            'version': '5.0.1',
            'Referer': 'https://m.music.migu.cn/'
        }
        self.MAGIC = b"\xab\xcd\x01"
        self.MIGU_KEY = b"Jk8qzuePiJ1qE3mDYhLQ3T73DtDoAhLP"
        self.quality_config = [
            ("高清320K", "hq", "mp3"),
            ("标准128K", "pq", "mp3"),
        ]
        self.DEFAULT_SONG_PIC = "https://d.musicapp.migu.cn/data/oss/resource/00/4t/9y/679feb591df148ddbc1e98110cd108de.webp"
        self.SEARCH_API = "https://pd.musicapp.migu.cn/MIGUM2.0/v1.0/content/search_all.do"
        self.RESOURCEINFO_API = "https://c.musicapp.migu.cn/MIGUM2.0/v1.0/content/resourceinfo.do"
        self.LISTEN_API = "https://c.musicapp.migu.cn/strategy/listen-url/h5/v2.4"
        self.PLAYLIST_SONG_API = "https://app.c.nf.migu.cn/MIGUM3.0/resource/playlist/song/v2.0"
        self.RANK_API = "https://app.c.nf.migu.cn/bmw/rank/rank-info/v1.0"

        self.classes = [
            {'type_id': 'bang_27186466', 'type_name': '咪咕热歌榜'},
            {'type_id': 'bang_27553319', 'type_name': '咪咕新歌榜'},
            {'type_id': 'bang_27553408', 'type_name': '咪咕原创榜'},
            {'type_id': 'bang_23189399', 'type_name': '内地榜'},
            {'type_id': 'bang_23189800', 'type_name': '港台榜'},
            {'type_id': 'pl_华语', 'type_name': '华语歌单'},
            {'type_id': 'pl_欧美', 'type_name': '欧美歌单'},
            {'type_id': 'pl_粤语', 'type_name': '粤语歌单'},
            {'type_id': 'pl_日语', 'type_name': '日语歌单'},
            {'type_id': 'pl_韩语', 'type_name': '韩语歌单'},
            {'type_id': 'pl_流行', 'type_name': '流行歌单'},
            {'type_id': 'pl_轻音乐', 'type_name': '轻音乐歌单'},
            {'type_id': 'pl_车载', 'type_name': '车载歌单'},
            {'type_id': 'pl_民谣', 'type_name': '民谣歌单'},
            {'type_id': 'pl_摇滚', 'type_name': '摇滚歌单'},
            {'type_id': 'pl_电子', 'type_name': '电子歌单'},
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
        return self.categoryContent('bang_27186466', 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
            if tid.startswith('pl_detail_'):
                pid = tid.replace('pl_detail_', '')
                return self._get_playlist_songs(pid, pg)
            elif tid.startswith('pl_'):
                keyword = tid.replace('pl_', '')
                return self._get_playlist_list(keyword, pg)
            elif tid.startswith('bang_detail_'):
                rank_id = tid.replace('bang_detail_', '')
                return self._get_bang_songs(rank_id, pg)
            elif tid.startswith('bang_'):
                bang_id = tid.replace('bang_', '')
                if bang_id.isdigit():
                    return self._get_bang_songs(bang_id, pg)
                return self._get_bang_list(tid, pg)
            else:
                return self._get_playlist_list('华语', pg)
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 0}

    def detailContent(self, ids):
        try:
            vid = ids[0].strip()
            if vid.startswith('song_'):
                return self._get_song_detail(vid.replace('song_', ''))
            elif vid.startswith('pl_detail_'):
                pid = vid.replace('pl_detail_', '')
                return self._get_playlist_detail(pid)
            elif vid.startswith('bang_detail_'):
                rank_id = vid.replace('bang_detail_', '')
                return self._get_bang_detail(rank_id)
            else:
                return self._get_playlist_detail(vid)
        except Exception as e:
            print(f"detailContent error: {e}")
            return self._get_search_songs('热门歌曲', 1)

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = raw_id
                result["header"] = self.headers
                return result

            rid = raw_id

            if '&&' in rid:
                rid = rid.split('&&')[0]

            if '$' in rid:
                parts = rid.split('$')
                for part in reversed(parts):
                    if part.startswith('http'):
                        pass
                    elif part.isalnum():
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

            if not rid:
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                return result

            audio_data = self._get_play_info(rid)
            if not audio_data or not audio_data.get('url'):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                if audio_data:
                    self._attach_lyric(result, audio_data)
                return result

            play_url = audio_data['url']
            if flag and flag in ('高清320K', '超清320K') and 'MP3_128_16_Stero' in play_url:
                play_url = play_url.replace('MP3_128_16_Stero', 'MP3_320_16_Stero')

            self._attach_lyric(result, audio_data)

            result["parse"] = 0
            result["playUrl"] = ""
            result["url"] = play_url
            result["header"] = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.migu.cn/"
            }

        except Exception as e:
            print(f"playerContent error: {e}")
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}

        return result

    def _attach_lyric(self, result, audio_data):
        try:
            lrc_text = ''
            lrc_url = audio_data.get('lrcUrl', '') or audio_data.get('lrc', '')
            if lrc_url and lrc_url.startswith('http'):
                lrc_text = self._download_lrc(lrc_url)
            elif lrc_text.startswith('http'):
                lrc_text = self._download_lrc(lrc_text)

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

            if lrc_text:
                ssa_lrc = self._create_ssa_subtitle(lrc_text)
                if ssa_lrc:
                    ssa_base64 = base64.b64encode(ssa_lrc.encode('utf-8')).decode('utf-8')
                    ssa_url = f"data:text/x-ssa;base64,{ssa_base64}"
                    result["subs"] = [{
                        "name": "5行歌词",
                        "url": ssa_url,
                        "format": "text/x-ssa",
                        "selected": True
                    }]
        except Exception as e:
            print(f"_attach_lyric error: {e}")

    def searchContent(self, key, quick, pg="1"):
        return self._get_search_songs(key, pg)

    def searchContentPage(self, key, quick, pg):
        return self._get_search_songs(key, pg)

    def fetch(self, url, headers=None, timeout=10):
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)
        return requests.get(url, headers=req_headers, timeout=timeout, verify=False)

    def _decrypt_response(self, content):
        raw = bytes(content)
        if raw[:3] == self.MAGIC:
            seed = raw[3]
            plain = bytes((byte + seed - self.MIGU_KEY[i % len(self.MIGU_KEY)]) & 0xFF
                          for i, byte in enumerate(raw[4:]))
            return plain.decode('utf-8', errors='replace')
        try:
            return raw.decode('utf-8')
        except Exception:
            return raw.decode('gbk', errors='replace')

    def _parse_json(self, res):
        text = self._decrypt_response(res.content)
        return json.loads(text)

    def _abs_img(self, url):
        if not url:
            return ''
        if url.startswith('http'):
            return url
        if url.startswith('/'):
            return 'https://d.musicapp.migu.cn' + url
        return url

    def _get_play_info(self, content_id):
        try:
            params = {
                'contentId': content_id,
                'resourceType': '2',
                'netType': '01',
                'toneFlag': 'PQ',
                'scene': '',
                'lowerQualityContentId': content_id,
            }
            r = requests.get(self.LISTEN_API, headers=self.api_headers,
                             params=params, timeout=10, verify=False)
            data = self._parse_json(r)
            if data.get('code') == '000000' and data.get('data'):
                info = data['data']
                return {
                    'url': info.get('url', ''),
                    'lrcUrl': info.get('lrcUrl', ''),
                    'name': (info.get('song') or {}).get('songName', '') if isinstance(info.get('song'), dict) else '',
                }
        except Exception as e:
            print(f"_get_play_info error: {e}")
        return {}

    def _download_lrc(self, lrc_url):
        try:
            r = requests.get(lrc_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://y.migu.cn/'
            }, timeout=8, verify=False)
            raw = r.content
            try:
                return raw.decode('utf-8')
            except Exception:
                return raw.decode('gbk', errors='replace')
        except Exception as e:
            print(f"_download_lrc error: {e}")
            return ''

    def _get_playlist_list(self, keyword, pg):
        vods = []
        try:
            params = {
                'ua': 'Android_migu',
                'version': '5.0.1',
                'text': keyword,
                'pageNo': pg,
                'pageSize': 30,
                'searchSwitch': '{"song":0,"album":0,"singer":0,"tagSong":0,"mvSong":0,"songlist":1,"bestShow":1}',
            }
            r = requests.get(self.SEARCH_API, headers=self.search_headers,
                             params=params, timeout=10, verify=False)
            data = json.loads(r.content.decode('utf-8', errors='replace'))
            result_data = data.get('songListResultData', {})
            data_list = result_data.get('result', []) or result_data.get('resultList', [])
            for it in data_list:
                pid = str(it.get('id', ''))
                name = it.get('name', '未命名歌单')
                pic = self._abs_img(it.get('musicListPicUrl', ''))
                music_num = it.get('musicNum', '')
                play_num = it.get('playNum', '')
                remarks = f"{music_num}首" if music_num else '咪咕歌单'
                if play_num:
                    remarks += f" · 播{play_num}"
                if not pid:
                    continue
                vods.append({
                    'vod_name': name,
                    'vod_id': f'pl_detail_{pid}',
                    'vod_pic': pic,
                    'vod_remarks': remarks,
                })
            if vods:
                return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}
        except Exception as e:
            print(f"_get_playlist_list error: {e}")
        return {'list': [], 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 0}

    def _get_playlist_detail(self, pid):
        play_arr = []
        pic_arr = []
        vod_name = '咪咕歌单'
        vod_pic = ''
        vod_content = ''

        try:
            total_count = 0
            seen = set()
            pg = 1
            while pg <= 10:
                params = {
                    'playlistId': pid,
                    'pageNo': pg,
                    'pageSize': 100,
                }
                r = requests.get(self.PLAYLIST_SONG_API, headers=self.headers,
                                 params=params, timeout=10, verify=False)
                d = json.loads(r.content.decode('utf-8', errors='replace'))
                if d.get('code') != '000000':
                    break
                info = d.get('data', {}) or {}
                if not vod_name or vod_name == '咪咕歌单':
                    vod_name = info.get('playListName', '') or vod_name
                if not vod_pic:
                    vod_pic = self._abs_img(info.get('image', info.get('img', '')))
                total_count = total_count or int(info.get('totalCount', 0) or 0)
                song_list = info.get('songList', []) or []
                if not song_list:
                    break
                for it in song_list:
                    cid = str(it.get('contentId', ''))
                    song = str(it.get('songName', ''))
                    artist = self._get_song_artist(it)
                    if not cid or cid in seen:
                        continue
                    seen.add(cid)
                    if not song:
                        continue
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#@]', '', display_name).strip()
                    play_arr.append(f"{display_name}${cid}")
                    pic_arr.append(self._abs_img(it.get('img1', it.get('img', ''))) or self.DEFAULT_SONG_PIC)
                pg += 1
                if total_count and len(seen) >= total_count:
                    break
                if len(song_list) < 100:
                    break
        except Exception as e:
            print(f"_get_playlist_detail error: {e}")

        if not play_arr:
            search_result = self._get_search_songs('热门歌曲', 1)
            for item in search_result.get('list', []):
                cid = item['vod_id'].replace('song_', '')
                play_arr.append(f"{item['vod_name']}${cid}")
                pic_arr.append(item.get('vod_pic', '') or self.DEFAULT_SONG_PIC)
            if vod_name == '咪咕歌单':
                vod_name = '热门歌曲'

        song_list = '#'.join(play_arr)
        pic_list = '#'.join(pic_arr)
        qualities = ['高清320K', '标准128K']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])
        vod_play_pic = '$$$'.join([pic_list for _ in qualities])

        vod = {
            'vod_id': f'pl_detail_{pid}',
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_content': vod_content or '微信公众号：源力软件汇\n来源：咪咕音乐',
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
            params = {
                'playlistId': pid,
                'pageNo': pg,
                'pageSize': 30,
            }
            r = requests.get(self.PLAYLIST_SONG_API, headers=self.headers,
                             params=params, timeout=10, verify=False)
            d = json.loads(r.content.decode('utf-8', errors='replace'))
            info = d.get('data', {}) or {}
            song_list = info.get('songList', []) or []
            for it in song_list:
                cid = str(it.get('contentId', ''))
                song = str(it.get('songName', ''))
                artist = self._get_song_artist(it)
                if cid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#@]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{cid}',
                        'vod_pic': self._abs_img(it.get('img1', it.get('img', ''))),
                        'vod_remarks': '咪咕音乐',
                    })
            total = int(info.get('totalCount', 0) or 0)
            if vods:
                return {'list': vods, 'page': pg, 'pagecount': (total + 99) // 100 + 1, 'limit': 30, 'total': total}
        except Exception as e:
            print(f"_get_playlist_songs error: {e}")

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_bang_list(self, tid, pg):
        vods = []
        try:
            bang_map = {
                'bang_27186466': ('27186466', '咪咕热歌榜'),
                'bang_27553319': ('27553319', '咪咕新歌榜'),
                'bang_27553408': ('27553408', '咪咕原创榜'),
                'bang_23189399': ('23189399', '内地榜'),
                'bang_23189800': ('23189800', '港台榜'),
            }
            bang_info = bang_map.get(tid, ('27186466', '咪咕热歌榜'))
            bang_id = bang_info[0]
            bang_name = bang_info[1]
            r = requests.get(self.RANK_API, headers=self.headers,
                             params={'rankId': bang_id}, timeout=10, verify=False)
            d = json.loads(r.content.decode('utf-8', errors='replace'))
            contents = d.get('data', {}).get('contents', []) or []
            pic = ''
            if contents:
                pic = contents[0].get('img', '')
            vods = [{
                'vod_name': bang_name,
                'vod_id': f'bang_detail_{bang_id}',
                'vod_pic': pic,
                'vod_remarks': '排行榜',
            }]
            return {'list': vods, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(vods)}
        except Exception as e:
            print(f"_get_bang_list error: {e}")

        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}

    def _get_bang_detail(self, bang_id):
        play_arr = []
        pic_arr = []
        bang_name = '咪咕排行榜'

        try:
            r = requests.get(self.RANK_API, headers=self.headers,
                             params={'rankId': bang_id}, timeout=10, verify=False)
            d = json.loads(r.content.decode('utf-8', errors='replace'))
            data = d.get('data', {}) or {}
            bang_name = data.get('title', data.get('rankName', '咪咕排行榜'))
            contents = data.get('contents', []) or []
            for it in contents:
                cid = str(it.get('resId', it.get('contentId', '')))
                song = str(it.get('txt', it.get('name', '')))
                artist = str(it.get('txt2', it.get('singer', '')))
                pic = it.get('img', '')
                if cid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#@]', '', display_name).strip()
                    play_arr.append(f"{display_name}${cid}")
                    pic_arr.append(pic or self.DEFAULT_SONG_PIC)
        except Exception as e:
            print(f"_get_bang_detail error: {e}")

        if not play_arr:
            search_result = self._get_search_songs('热门歌曲', 1)
            for item in search_result.get('list', []):
                cid = item['vod_id'].replace('song_', '')
                play_arr.append(f"{item['vod_name']}${cid}")
                pic_arr.append(item.get('vod_pic', '') or self.DEFAULT_SONG_PIC)

        song_list = '#'.join(play_arr)
        pic_list = '#'.join(pic_arr)
        qualities = ['高清320K', '标准128K']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])
        vod_play_pic = '$$$'.join([pic_list for _ in qualities])

        vod = {
            'vod_id': f'bang_detail_{bang_id}',
            'vod_name': bang_name,
            'vod_pic': pic_arr[0] if pic_arr else '',
            'vod_content': '微信公众号：源力软件汇\n来源：咪咕音乐',
            'vod_remarks': f"歌曲 : {len(play_arr)}首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
            'vod_play_pic': vod_play_pic,
            'vod_play_pic_ratio': 1.0,
        }

        return {'list': [vod]}

    def _get_bang_songs(self, bang_id, pg):
        vods = []
        try:
            r = requests.get(self.RANK_API, headers=self.headers,
                             params={'rankId': bang_id}, timeout=10, verify=False)
            d = json.loads(r.content.decode('utf-8', errors='replace'))
            contents = d.get('data', {}).get('contents', []) or []
            start = (pg - 1) * 30
            page_items = contents[start:start + 30]
            for it in page_items:
                cid = str(it.get('resId', it.get('contentId', '')))
                song = str(it.get('txt', it.get('name', '')))
                artist = str(it.get('txt2', it.get('singer', '')))
                pic = it.get('img', '')
                if cid and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#@]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{cid}',
                        'vod_pic': pic,
                        'vod_remarks': '排行榜',
                    })
            total = len(contents)
            if vods:
                pagecount = max(1, (total + 29) // 30)
                return {'list': vods, 'page': pg, 'pagecount': pagecount, 'limit': 30, 'total': total}
        except Exception as e:
            print(f"_get_bang_songs error: {e}")

        if not vods:
            search_result = self._get_search_songs('热门歌曲', pg)
            vods = search_result.get('list', [])
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_song_artist(self, it):
        singers = it.get('singers') or it.get('singerList') or []
        if isinstance(singers, list) and singers:
            names = [str(s.get('name', '')) for s in singers if isinstance(s, dict) and s.get('name')]
            if names:
                return ','.join(names)
        return str(it.get('singerName', it.get('singer', '')))

    def _get_song_detail(self, content_id):
        result = {"list": []}
        try:
            song_info = self._get_song_info(content_id)
            song_name = song_info.get('name', '')
            artist = song_info.get('artist', '')
            album = song_info.get('album', '')
            pic = song_info.get('pic', '') or self.DEFAULT_SONG_PIC
            lrc_url = song_info.get('lrcUrl', '')

            if not song_name:
                song_name = f"歌曲_{content_id}"

            song_name = re.sub(r'[$#@]', '', song_name).strip()
            artist = re.sub(r'[$#@]', '', artist).strip() if artist else ''

            play_from_arr = []
            play_url_arr = []
            play_pic_arr = []

            for q_name, _, _ in self.quality_config:
                display_name = f"{song_name} - {artist}" if artist else song_name
                play_from_arr.append(q_name)
                play_url_arr.append(f"{display_name}${content_id}")
                play_pic_arr.append(pic)

            content = f"微信公众号：源力软件汇\n歌曲：{song_name}\n歌手：{artist}\n专辑：{album}\n来源：咪咕音乐"
            if lrc_url:
                lrc_text = self._download_lrc(lrc_url)
                if lrc_text:
                    lrc_lines = lrc_text.split('\n')
                    clean_lines = []
                    for line in lrc_lines:
                        clean_line = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
                        if clean_line:
                            clean_lines.append(clean_line)
                    if clean_lines:
                        content += "\n\n--- 歌词 ---\n" + '\n'.join(clean_lines)

            vod = {
                "vod_id": f"song_{content_id}",
                "vod_name": song_name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_remarks": album or '咪咕音乐',
                "vod_actor": artist,
                "vod_play_from": '$$$'.join(play_from_arr),
                "vod_play_url": '$$$'.join(play_url_arr),
                "vod_play_pic": '$$$'.join(play_pic_arr),
                "vod_play_pic_ratio": 1.0,
            }

            result["list"] = [vod]
        except Exception as e:
            print(f"_get_song_detail error: {e}")

        if not result.get('list'):
            vod = {
                "vod_id": f"song_{content_id}",
                "vod_name": f"歌曲_{content_id}",
                "vod_pic": self.DEFAULT_SONG_PIC,
                "vod_content": '微信公众号：源力软件汇',
                "vod_remarks": '咪咕音乐',
                "vod_actor": '',
                "vod_play_from": '标准音质',
                "vod_play_url": f"歌曲_{content_id}${content_id}",
                "vod_play_pic": self.DEFAULT_SONG_PIC,
                "vod_play_pic_ratio": 1.0,
            }
            result["list"] = [vod]

        return result

    def _get_song_info(self, content_id):
        try:
            params = {
                'needSimple': '00',
                'resourceType': '2',
                'resourceId': content_id,
            }
            r = requests.get(self.RESOURCEINFO_API, headers=self.search_headers,
                             params=params, timeout=8, verify=False)
            data = json.loads(r.content.decode('utf-8', errors='replace'))
            resource = data.get('resource', []) or []
            if resource:
                it = resource[0]
                album_imgs = it.get('albumImgs') or []
                pic = ''
                if album_imgs:
                    pic = album_imgs[0].get('img', '')
                return {
                    'name': it.get('songName', ''),
                    'artist': it.get('singer', ''),
                    'album': it.get('album', ''),
                    'pic': pic,
                    'lrcUrl': it.get('lrcUrl', ''),
                    'length': it.get('length', ''),
                }
        except Exception as e:
            print(f"_get_song_info error: {e}")
        return {}

    def _get_search_songs(self, keyword, pg=1):
        try:
            pg = int(pg)
            params = {
                'ua': 'Android_migu',
                'version': '5.0.1',
                'text': keyword,
                'pageNo': pg,
                'pageSize': 30,
                'searchSwitch': '{"song":1,"album":0,"singer":0,"tagSong":0,"mvSong":0,"songlist":0,"bestShow":1}',
            }
            r = requests.get(self.SEARCH_API, headers=self.search_headers,
                             params=params, timeout=10, verify=False)
            data = json.loads(r.content.decode('utf-8', errors='replace'))
            result_data = data.get('songResultData', {})
            result_list = result_data.get('result', []) or []

            vods = []
            for it in result_list:
                content_id = it.get('contentId', '')
                song = str(it.get('name', it.get('songName', '')))
                artist = self._get_song_artist(it)
                albums = it.get('albums') or []
                album_name = ''
                if isinstance(albums, list) and albums:
                    album_name = str(albums[0].get('name', ''))
                img_items = it.get('imgItems') or []
                pic_url = ''
                if img_items:
                    pic_url = img_items[-1].get('img', '')

                if content_id and song:
                    display_name = f"{song} - {artist}" if artist else song
                    display_name = re.sub(r'[$#@]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{content_id}',
                        'vod_pic': pic_url,
                        'vod_remarks': album_name or '咪咕音乐',
                    })

            return {'list': vods, 'page': pg, 'pagecount': 999, 'limit': 30, 'total': 99999}
        except Exception as e:
            print(f"_get_search_songs error: {e}")
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