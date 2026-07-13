# -*- coding: utf-8 -*-
"""
汽水音乐 - https://www.qishui.com/
"""
import re
import json
import sys
import base64
import requests
import urllib.parse
from urllib.parse import quote
sys.path.append('yl-main')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "汽水音乐"

    def init(self, extend=""):
        self.host = "https://www.qishui.com"
        self.bugpk_api = "https://api.bugpk.com/api/qsmusic"
        self.vhrise_api = "https://api.vhrise.com/api/qsmusic.php"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.qishui.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.douyin_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.kuwo_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.kuwo.cn/'
        }
        self.quality_config = [
            ("标准128K", 128, "mp3"),
            ("高清192K", 192, "mp3"),
            ("超清320K", 320, "mp3"),
            ("无损APE", 2000, "ape"),
        ]
        self.classes = [
            {'type_id': 'hot', 'type_name': '热门推荐'},
            {'type_id': 'douyin_hot', 'type_name': '抖音热歌'},
            {'type_id': 'new_song', 'type_name': '新歌速递'},
            {'type_id': 'pl_kuwo', 'type_name': '酷我歌单'},
            {'type_id': 'artist_cn_man', 'type_name': '华语男歌手'},
            {'type_id': 'artist_cn_woman', 'type_name': '华语女歌手'},
            {'type_id': 'artist_kr_jp', 'type_name': '日韩歌手'},
            {'type_id': 'artist_west', 'type_name': '欧美歌手'},
        ]
        self.artist_defaults = {
            'artist_cn_man': [
                ("周杰伦", "336"), ("林俊杰", "1062"), ("陈奕迅", "47"),
                ("薛之谦", "947"), ("李荣浩", "61144"), ("毛不易", "1456705"),
                ("华晨宇", "125910"), ("张学友", "896"), ("王力宏", "1416"),
                ("许嵩", "1887"), ("汪苏泷", "5357"), ("王源", "185500"),
            ],
            'artist_cn_woman': [
                ("邓紫棋", "5371"), ("王菲", "385"), ("赵露思", "2545931"),
                ("刘雨昕", "1312347"), ("鞠婧祎", "223496"), ("周笔畅", "1115"),
                ("张靓颖", "211"), ("田馥甄", "5359"), ("梁静茹", "317"),
                ("孙燕姿", "744"), ("莫文蔚", "909"), ("蔡健雅", "522"),
            ],
            'artist_kr_jp': [
                ("BLACKPINK", "374042"), ("BTS防弹少年团", "125238"),
                ("TWICE", "263053"), ("aespa", "6117294"),
                ("IU李知恩", "9318"), ("Stray Kids", "1819232"),
                ("NewJeans", "10225347"), ("LE SSERAFIM", "9719705"),
                ("EXO", "70246"), ("BigBang", "125"),
                ("坂本龍一", "38587"), ("米津玄師", "74016"),
            ],
            'artist_west': [
                ("Taylor Swift", "4968"), ("Ed Sheeran", "30741"),
                ("Billie Eilish", "492513"), ("Adele", "1627"),
                ("The Weeknd", "22662"), ("Dua Lipa", "257953"),
                ("Post Malone", "266267"), ("Bruno Mars", "5311"),
                ("Eminem", "5258"), ("Maroon 5", "3579"),
                ("Shawn Mendes", "194215"), ("Justin Bieber", "5317"),
            ],
        }

    def isVideoFormat(self, url):
        return url.endswith(('.mp4', '.m3u8', '.flv', '.mkv'))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {}
        result['class'] = self.classes
        filters = {}
        for cls in self.classes:
            filters[cls['type_id']] = [
                {"key": "quality", "name": "音质", "value": [
                    {"n": "标准128K", "v": "标准128K"},
                    {"n": "高清192K", "v": "高清192K"},
                    {"n": "超清320K", "v": "超清320K"},
                    {"n": "无损APE", "v": "无损APE"},
                ]}
            ]
        result['filters'] = filters
        result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent('hot', 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg else 1
            if tid.startswith('artist_detail_'):
                artist_id = tid.replace('artist_detail_', '')
                return self._get_artist_songs_list(artist_id, pg)
            elif tid in self.artist_defaults:
                return self._get_artist_list(tid, pg)
            elif tid.startswith('pl_detail_'):
                playlist_id = tid.replace('pl_detail_', '')
                return self._get_playlist_songs_list(playlist_id, pg)
            elif tid == 'hot':
                return self._get_hot_songs(pg)
            elif tid == 'douyin_hot':
                return self._get_douyin_hot(pg)
            elif tid == 'new_song':
                return self._get_new_songs(pg)
            elif tid == 'pl_kuwo':
                return self._get_kuwo_playlist_list(pg)
            else:
                return self._get_hot_songs(pg)
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 30, 'total': 0}

    def detailContent(self, ids):
        try:
            vid = ids[0].strip() if isinstance(ids, list) else ids.strip()
            if vid.startswith('song_'):
                return self._get_song_detail(vid)
            elif vid.startswith('artist_detail_'):
                artist_id = vid.replace('artist_detail_', '')
                return self._get_artist_all_songs_detail(artist_id)
            elif vid.startswith('pl_detail_'):
                playlist_id = vid.replace('pl_detail_', '')
                return self._get_playlist_all_songs_detail(playlist_id)
            else:
                return self._get_song_detail(vid)
        except Exception as e:
            print(f"detailContent error: {e}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["url"] = raw_id
                result["header"] = self.headers
                return result

            if '&&' in raw_id:
                parts = raw_id.split('&&')
                raw_id = parts[0]

            if '$' in raw_id:
                dollar_parts = raw_id.split('$')
                for part in reversed(dollar_parts):
                    if part.startswith('http'):
                        result["url"] = part
                        result["header"] = self.headers
                        return result
                    elif len(part) > 5 and part.isdigit():
                        raw_id = part
                        break
                else:
                    if len(dollar_parts) > 1:
                        raw_id = dollar_parts[-1]

            if raw_id.startswith('song_'):
                raw_id = raw_id.replace('song_', '')

            if self.isVideoFormat(raw_id):
                result["url"] = raw_id
                result["header"] = self.headers
                return result

            track_id = raw_id
            share_url = f"https://www.qishui.com/?track_id={track_id}"

            song_data = self._parse_with_bugpk(share_url)

            if not song_data:
                share_url2 = f"https://music.douyin.com/qishui/share/track?track_id={track_id}"
                song_data = self._parse_share_page(share_url2)

            if not song_data:
                song_data = self._parse_with_vhrise(share_url)

            if song_data and song_data.get('url'):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = song_data['url']
                result["header"] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.douyin.com/'
                }

                lrc = song_data.get('lyrics', '')
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

            if not result.get('url'):
                kuwo_url = self._get_kuwo_play_url(track_id)
                if kuwo_url:
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = kuwo_url
                    result["header"] = self.kuwo_headers
                    lrc = self._get_kuwo_lyric(track_id)
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

        except Exception as e:
            print(f"playerContent error: {e}")

        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg) if pg else 1
            vods = self._search_douyin(key, pg)
            if not vods or not vods.get('list'):
                vods = self._search_kuwo(key, pg)
            return vods
        except Exception as e:
            print(f"searchContent error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 30, 'total': 0}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def fetch(self, url, headers=None, timeout=10):
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)
        try:
            return requests.get(url, headers=req_headers, timeout=timeout, verify=False)
        except Exception as e:
            print(f"fetch error: {e}")
            return None

    def _search_douyin(self, keyword, pg=1):
        vods = []
        try:
            offset = (pg - 1) * 15
            url = "https://www.douyin.com/aweme/v1/web/general/search/single/"
            params = {
                'search_channel': 'general',
                'enable_history': '1',
                'keyword': keyword,
                'search_source': 'tab_search',
                'query_correct_type': '1',
                'is_filter_search': '0',
                'from_group_id': '',
                'offset': str(offset),
                'count': '15',
                'need_filter_settings': '1',
                'list_type': 'multi',
                'search_id': '',
            }
            referer = f"https://www.douyin.com/search/{urllib.parse.quote(keyword)}?type=music"
            headers = self.douyin_headers.copy()
            headers['Referer'] = referer

            resp = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 15, 'total': 0}

            data = resp.json()
            data_list = data.get('data', [])

            for item in data_list:
                aweme_info = item.get('aweme_info')
                if not aweme_info:
                    continue
                music_info = aweme_info.get('music', {})
                if not music_info:
                    continue

                music_id = music_info.get('id_str', '')
                title = music_info.get('title', '')
                author = music_info.get('author', '')
                play_url_list = music_info.get('play_url', {}).get('url_list', [])
                play_url = play_url_list[0] if play_url_list else ''
                cover_list = music_info.get('cover_thumb', {}).get('url_list', [])
                cover = cover_list[0] if cover_list else ''
                duration = music_info.get('duration', 0)

                if music_id and title:
                    display_name = f"{title} - {author}" if author and author != title else title
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    remarks = f"{duration // 1000}秒" if duration else '汽水音乐'
                    play_id = f"{music_id}&&{play_url}" if play_url else music_id
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': f'song_{play_id}',
                        'vod_pic': cover,
                        'vod_remarks': remarks,
                    })
        except Exception as e:
            print(f"_search_douyin error: {e}")

        return {'list': vods, 'page': pg, 'pagecount': 999, 'limit': 15, 'total': 9999}

    def _search_kuwo(self, keyword, pg=1):
        vods = []
        try:
            search_url = f"https://search.kuwo.cn/r.s?client=kt&all={quote(keyword)}&pn={pg - 1}&rn=30&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            res = self.fetch(search_url, headers=self.kuwo_headers)
            if not res:
                return {'list': [], 'page': pg, 'pagecount': 0, 'limit': 30, 'total': 0}

            content = res.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]

            data = json.loads(content)
            abslist = data.get('abslist', [])

            for it in abslist:
                dc_target_id = it.get('DC_TARGETID')
                if dc_target_id and it.get('DC_TARGETTYPE') == 'music':
                    rid = str(dc_target_id)
                    song = str(it.get('SONGNAME', it.get('NAME', '')))
                    artist = str(it.get('ARTIST', it.get('FARTIST', '')))
                    pic_url = it.get('hts_MVPIC', '') or it.get('hts_ALBUMPIC', '')

                    if rid and song:
                        display_name = f"{song} - {artist}" if artist else song
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        vods.append({
                            'vod_name': display_name,
                            'vod_id': f'song_{rid}',
                            'vod_pic': pic_url,
                            'vod_remarks': '汽水音乐',
                        })
        except Exception as e:
            print(f"_search_kuwo error: {e}")

        return {'list': vods, 'page': pg, 'pagecount': 999, 'limit': 30, 'total': 9999}

    def _get_hot_songs(self, pg=1):
        default_songs = [
            ("稻香 - 周杰伦", "7108710628"), ("晴天 - 周杰伦", "7108710616"),
            ("七里香 - 周杰伦", "7108710624"), ("青花瓷 - 周杰伦", "7108710620"),
            ("告白气球 - 周杰伦", "7108710632"), ("起风了 - 买辣椒也用券", "7108710688"),
            ("孤勇者 - 陈奕迅", "7108710700"), ("漠河舞厅 - 柳爽", "7108710712"),
            ("错位时空 - 艾辰", "7108710720"), ("白月光与朱砂痣 - 大籽", "7108710728"),
            ("踏山河 - 是七叔呢", "7108710736"), ("半生雪 - 是七叔呢", "7108710744"),
            ("你的答案 - 阿冗", "7108710752"), ("星辰大海 - 黄霄雲", "7108710760"),
            ("大风吹 - 王赫野", "7108710768"), ("人间烟火 - 程响", "7108710776"),
            ("年少有为 - 李荣浩", "7108710784"), ("消愁 - 毛不易", "7108710792"),
            ("像我这样的人 - 毛不易", "7108710800"), ("体面 - 于文文", "7108710808"),
            ("芒种 - 音阙诗听", "7108710816"), ("下山 - 要不要买菜", "7108710824"),
            ("桥边姑娘 - 海伦", "7108710832"), ("你笑起来真好看 - 李昕融", "7108710840"),
            ("可能否 - 木小雅", "7108710848"), ("世间美好与你环环相扣 - 柏松", "7108710856"),
            ("一路生花 - 温奕心", "7108710864"), ("执子之手 - 音阙诗听", "7108710872"),
            ("下辈子不一定还能遇见你 - 海来阿木", "7108710880"), ("西楼儿女 - 岳云鹏", "7108710888"),
        ]

        start = (pg - 1) * 30
        page_songs = default_songs[start:start + 30]

        vods = []
        for name, track_id in page_songs:
            vods.append({
                'vod_name': name,
                'vod_id': f'song_{track_id}',
                'vod_pic': '',
                'vod_remarks': '汽水音乐',
            })

        if not vods:
            vods = self._search_kuwo('热门歌曲', pg).get('list', [])

        page_count = (len(default_songs) + 29) // 30
        return {'list': vods, 'page': pg, 'pagecount': max(page_count, 99), 'limit': 30, 'total': len(default_songs)}

    def _get_douyin_hot(self, pg=1):
        vods = self._search_kuwo('抖音热歌', pg)
        if not vods.get('list'):
            return self._get_hot_songs(pg)
        return vods

    def _get_new_songs(self, pg=1):
        vods = self._search_kuwo('2024新歌', pg)
        if not vods.get('list'):
            return self._get_hot_songs(pg)
        return vods

    def _get_kuwo_playlist_list(self, pg=1):
        vods = []
        try:
            api_url = f"http://wapi.kuwo.cn/api/pc/classify/playlist/getRcmPlayList?loginUid=0&loginSid=0&appUid=76039576&rn=30&order=hot&pn={pg}"
            res = self.fetch(api_url, headers=self.kuwo_headers)
            if res:
                data = res.json()
                data_list = data.get('data', {}).get('data', []) or []
                for it in data_list:
                    name = it.get('name', it.get('title', '未命名歌单'))
                    vid = str(it.get('id', it.get('pid', '')))
                    pic = it.get('img', it.get('pic', it.get('cover', '')))
                    if vid:
                        vods.append({
                            'vod_name': name,
                            'vod_id': f'pl_detail_{vid}',
                            'vod_pic': pic,
                            'vod_remarks': '歌单',
                        })
        except Exception as e:
            print(f"_get_kuwo_playlist_list error: {e}")
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_artist_list(self, cat_id, pg=1):
        artists = self.artist_defaults.get(cat_id, [])
        vods = []
        for name, artist_id in artists:
            vods.append({
                'vod_name': name,
                'vod_id': f'artist_detail_{artist_id}',
                'vod_pic': '',
                'vod_remarks': '歌手',
            })
        return {'list': vods, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(vods)}

    def _get_artist_songs_list(self, artist_id, pg=1):
        vods = []
        try:
            api_url = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={artist_id}&pn={pg}&rn=30"
            res = self.fetch(api_url, headers=self.kuwo_headers)
            if res:
                data = res.json()
                music_list = data.get('data', {}).get('list', [])
                for it in music_list:
                    rid = str(it.get('rid', it.get('id', '')))
                    song = str(it.get('name', ''))
                    artist = str(it.get('artist', it.get('singer', '')))
                    pic = it.get('albumPic', it.get('pic', ''))
                    if rid and song:
                        display_name = f"{song} - {artist}" if artist else song
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        vods.append({
                            'vod_name': display_name,
                            'vod_id': f'song_{rid}',
                            'vod_pic': pic,
                            'vod_remarks': '汽水音乐',
                        })
        except Exception as e:
            print(f"_get_artist_songs_list error: {e}")
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_artist_all_songs_detail(self, artist_id):
        all_songs = []
        artist_name = ''
        artist_pic = ''

        for cat_id, artists in self.artist_defaults.items():
            for name, aid in artists:
                if str(aid) == str(artist_id):
                    artist_name = name
                    break
            if artist_name:
                break

        try:
            for pg in range(1, 100):
                api_url = f"http://wapi.kuwo.cn/api/www/artist/artistMusic?artistid={artist_id}&pn={pg}&rn=100"
                res = self.fetch(api_url, headers=self.kuwo_headers)
                if not res:
                    break
                data = res.json()
                music_list = data.get('data', {}).get('list', [])
                total = data.get('data', {}).get('total', 0)
                if not music_list:
                    break
                for it in music_list:
                    rid = str(it.get('rid', it.get('id', '')))
                    song = str(it.get('name', ''))
                    artist = str(it.get('artist', it.get('singer', '')))
                    pic = it.get('albumPic', it.get('pic', ''))
                    if not artist_name and artist:
                        artist_name = artist
                    if not artist_pic and pic:
                        artist_pic = pic
                    if rid and song:
                        display_name = f"{song} - {artist}" if artist else song
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        all_songs.append(f"{display_name}${rid}")
                if total and len(all_songs) >= total:
                    break
                if len(all_songs) >= 2000:
                    break
        except Exception as e:
            print(f"_get_artist_all_songs_detail error: {e}")

        if not all_songs:
            search_result = self._search_kuwo(artist_name or '周杰伦', 1)
            for item in search_result.get('list', []):
                rid = item['vod_id'].replace('song_', '')
                all_songs.append(f"{item['vod_name']}${rid}")

        if not all_songs:
            return {'list': []}

        song_list = '#'.join(all_songs)
        qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        prefix = '微信公众号"源力软件汇" '
        vod = {
            'vod_id': f'artist_detail_{artist_id}',
            'vod_name': artist_name or '未知歌手',
            'vod_pic': artist_pic,
            'vod_content': f'{prefix}歌手: {artist_name}，共{len(all_songs)}首歌曲',
            'vod_remarks': f"歌曲 : {len(all_songs)}首",
            'vod_actor': artist_name,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        if artist_pic:
            vod['vod_play_pic'] = '$$$'.join([artist_pic for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.0

        return {'list': [vod]}

    def _get_playlist_songs_list(self, playlist_id, pg=1):
        vods = []
        try:
            pn = (pg - 1) * 30
            api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={playlist_id}&pn={pn}&rn=30&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
            res = self.fetch(api_url, headers=self.kuwo_headers)
            if res:
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
                            'vod_remarks': '歌单',
                        })
        except Exception as e:
            print(f"_get_playlist_songs_list error: {e}")
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_playlist_all_songs_detail(self, playlist_id):
        all_songs = []
        pl_name = ''
        pl_pic = ''

        try:
            for pg in range(0, 100):
                pn = pg * 100
                api_url = f"http://nplserver.kuwo.cn/pl.svc?op=getlistinfo&pid={playlist_id}&pn={pn}&rn=100&encode=utf8&keyset=pl2012&identity=kuwo&pcmp4=1&vipver=MUSIC_9.1.1.2_BCS2&newver=1"
                res = self.fetch(api_url, headers=self.kuwo_headers)
                if not res:
                    break
                d = res.json()
                if not pl_name:
                    pl_name = d.get('name', d.get('title', ''))
                if not pl_pic:
                    pl_pic = d.get('pic', d.get('img', ''))
                music_list = d.get('musiclist', [])
                if not music_list:
                    break
                for it in music_list:
                    rid = str(it.get('id', '')) if it.get('id') is not None else ''
                    song = str(it.get('name', it.get('SONGNAME', '')))
                    artist = str(it.get('artist', it.get('ARTIST', it.get('FARTIST', ''))))
                    if rid and song:
                        display_name = f"{song} - {artist}" if artist else song
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        all_songs.append(f"{display_name}${rid}")
                total = d.get('total', 0)
                if total and len(all_songs) >= total:
                    break
                if len(music_list) < 100:
                    break
                if len(all_songs) >= 2000:
                    break
        except Exception as e:
            print(f"_get_playlist_all_songs_detail error: {e}")

        if not all_songs:
            search_result = self._search_kuwo('热门歌曲', 1)
            for item in search_result.get('list', []):
                rid = item['vod_id'].replace('song_', '')
                all_songs.append(f"{item['vod_name']}${rid}")
            pl_name = pl_name or '热门歌单'

        if not all_songs:
            return {'list': []}

        song_list = '#'.join(all_songs)
        qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        prefix = '微信公众号"源力软件汇" '
        vod = {
            'vod_id': f'pl_detail_{playlist_id}',
            'vod_name': pl_name or '汽水歌单',
            'vod_pic': pl_pic,
            'vod_content': f'{prefix}歌单: {pl_name}，共{len(all_songs)}首歌曲',
            'vod_remarks': f"歌曲 : {len(all_songs)}首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        if pl_pic:
            vod['vod_play_pic'] = '$$$'.join([pl_pic for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.5

        return {'list': [vod]}

    def _get_song_detail(self, vid):
        result = {"list": []}
        try:
            track_id = vid.replace("song_", "")

            if '&&' in track_id:
                parts = track_id.split('&&')
                track_id = parts[0]
                direct_url = parts[1] if len(parts) > 1 else ''
            else:
                direct_url = ''

            song_name = ''
            artist = ''
            album = ''
            pic = ''
            lrc_text = ''

            if direct_url and direct_url.startswith('http'):
                kuwo_info = self._get_kuwo_song_info(track_id)
                if kuwo_info:
                    song_name = kuwo_info.get('name', '')
                    artist = kuwo_info.get('artist', '')
                    pic = kuwo_info.get('pic', '')
                if not song_name:
                    song_name = f"歌曲_{track_id}"
                    artist = '汽水音乐'
            else:
                share_url = f"https://www.qishui.com/?track_id={track_id}"
                song_data = self._parse_with_bugpk(share_url)

                if not song_data:
                    share_url2 = f"https://music.douyin.com/qishui/share/track?track_id={track_id}"
                    song_data = self._parse_share_page(share_url2)

                if not song_data:
                    song_data = self._parse_with_vhrise(share_url)

                if song_data:
                    song_name = song_data.get('title', '') or song_data.get('track_name', '')
                    artist = song_data.get('artist', '') or song_data.get('artistsname', '')
                    album = song_data.get('album', '') or song_data.get('albumname', '')
                    pic = song_data.get('cover', '') or song_data.get('cover_image', '')
                    lrc_text = song_data.get('lyrics', '')
                    direct_url = song_data.get('url', '')

                if not song_name:
                    kuwo_info = self._get_kuwo_song_info(track_id)
                    if kuwo_info:
                        song_name = kuwo_info.get('name', '')
                        artist = kuwo_info.get('artist', '')
                        pic = kuwo_info.get('pic', '')
                    if not song_name:
                        song_name = f"歌曲_{track_id}"

            song_name = re.sub(r'[$#]', '', str(song_name)).strip()
            artist = re.sub(r'[$#]', '', str(artist)).strip() if artist else ''

            play_from_arr = []
            play_url_arr = []
            play_pic_arr = []

            for q_name, bitrate, fmt in self.quality_config:
                display_name = f"{song_name} - {artist}" if artist else song_name
                play_from_arr.append(q_name)
                play_url_arr.append(f"{display_name}${track_id}")
                play_pic_arr.append(pic)

            if not play_from_arr:
                play_from_arr.append('标准128K')
                display_name = f"{song_name} - {artist}" if artist else song_name
                play_url_arr.append(f"{display_name}${track_id}")
                play_pic_arr.append(pic)

            prefix = '微信公众号"源力软件汇" '
            content = f"{prefix}歌曲：{song_name}\n歌手：{artist}\n专辑：{album}\n来源：汽水音乐"

            if lrc_text:
                clean_lrc = self._clean_lyrics_for_display(lrc_text)
                if clean_lrc:
                    content += "\n\n--- 歌词 ---\n" + clean_lrc

            vod = {
                "vod_id": vid,
                "vod_name": song_name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_remarks": album or '汽水音乐',
                "vod_actor": artist,
                "vod_play_from": '$$$'.join(play_from_arr),
                "vod_play_url": '$$$'.join(play_url_arr),
            }
            if play_pic_arr and play_pic_arr[0]:
                vod['vod_play_pic'] = '$$$'.join(play_pic_arr)
                vod['vod_play_pic_ratio'] = 1.0

            result["list"] = [vod]
        except Exception as e:
            print(f"_get_song_detail error: {e}")

        if not result.get('list'):
            track_id = vid.replace("song_", "")
            prefix = '微信公众号"源力软件汇" '
            vod = {
                "vod_id": vid,
                "vod_name": f"歌曲_{track_id}",
                "vod_pic": '',
                "vod_content": f'{prefix}汽水音乐',
                "vod_remarks": '汽水音乐',
                "vod_actor": '',
                "vod_play_from": '标准128K',
                "vod_play_url": f"歌曲_{track_id}${track_id}",
            }
            result["list"] = [vod]

        return result

    def _parse_with_bugpk(self, url):
        try:
            api_url = f"{self.bugpk_api}?url={urllib.parse.quote(url)}"
            resp = requests.get(api_url, headers=self.headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get('code') != 200:
                return None
            song_data = data.get('data', {})
            if not song_data:
                return None
            audio_url = song_data.get('url', '')
            raw_lyrics = song_data.get('lyric', '')
            lyrics = self._convert_bugpk_lyrics(raw_lyrics) if raw_lyrics else ''
            return {
                'url': audio_url,
                'lyrics': lyrics,
                'title': song_data.get('albumname', ''),
                'track_name': song_data.get('albumname', ''),
                'artist': song_data.get('artistsname', ''),
                'artistsname': song_data.get('artistsname', ''),
                'album': song_data.get('albumname', ''),
                'albumname': song_data.get('albumname', ''),
                'cover': song_data.get('artistsmedium_avatar_url', [''])[0] if song_data.get('artistsmedium_avatar_url') else '',
                'cover_image': song_data.get('artistsmedium_avatar_url', [''])[0] if song_data.get('artistsmedium_avatar_url') else '',
            }
        except Exception as e:
            print(f"_parse_with_bugpk error: {e}")
        return None

    def _parse_with_vhrise(self, url):
        try:
            api_url = f"{self.vhrise_api}?url={urllib.parse.quote(url)}"
            resp = requests.get(api_url, headers=self.headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get('code') != 200 and data.get('code') != '200':
                return None
            song_data = data.get('data', {})
            if not song_data:
                return None
            audio_url = song_data.get('url', '')
            raw_lyrics = song_data.get('lyric', '')
            lyrics = self._convert_bugpk_lyrics(raw_lyrics) if raw_lyrics else ''
            return {
                'url': audio_url,
                'lyrics': lyrics,
                'title': song_data.get('title', ''),
                'track_name': song_data.get('title', ''),
                'artist': song_data.get('author', ''),
                'artistsname': song_data.get('author', ''),
                'album': '',
                'albumname': '',
                'cover': song_data.get('cover', ''),
                'cover_image': song_data.get('cover', ''),
            }
        except Exception as e:
            print(f"_parse_with_vhrise error: {e}")
        return None

    def _parse_share_page(self, url):
        try:
            resp = requests.get(url, headers=self.douyin_headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return None
            html = resp.text
            pattern = r'_ROUTER_DATA\s*=\s*(\{[\s\S]*?\});'
            match = re.search(pattern, html)
            if not match:
                return None
            data = json.loads(match.group(1))
            track_page = data.get('loaderData', {}).get('track_page', {})
            audio_option = track_page.get('audioWithLyricsOption', {})
            audio_url = audio_option.get('url', '')
            title = track_page.get('title', '')
            cover = track_page.get('cover', '')
            lyrics_data = audio_option.get('lyrics', {}).get('sentences', [])
            lrc = self._convert_douyin_lyrics(lyrics_data) if lyrics_data else ''
            return {
                'url': audio_url,
                'lyrics': lrc,
                'title': title,
                'track_name': title,
                'artist': '',
                'artistsname': '',
                'album': '',
                'albumname': '',
                'cover': cover,
                'cover_image': cover,
            }
        except Exception as e:
            print(f"_parse_share_page error: {e}")
        return None

    def _get_kuwo_song_info(self, rid):
        try:
            api_url = f"https://kuwo.cn/openapi/v1/www/music/playInfo?mid={rid}"
            r = self.fetch(api_url, headers=self.kuwo_headers)
            if r:
                data = r.json()
                info = data.get('data', {})
                if info:
                    return {
                        'name': info.get('name', ''),
                        'artist': info.get('artist', ''),
                        'album': info.get('album', ''),
                        'pic': info.get('pic', ''),
                    }
        except Exception:
            pass
        try:
            api_url = f"https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}"
            r = self.fetch(api_url, headers=self.kuwo_headers, timeout=5)
            if r:
                data = r.json()
                if data.get('data') and data['data'].get('songinfo'):
                    info = data['data']['songinfo']
                    return {
                        'name': info.get('songName', ''),
                        'artist': info.get('artist', ''),
                        'album': info.get('album', ''),
                        'pic': info.get('pic', ''),
                    }
        except Exception:
            pass
        try:
            search_url = f"https://search.kuwo.cn/r.s?client=kt&all=MUSIC_{rid}&pn=0&rn=1&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            res = self.fetch(search_url, headers=self.kuwo_headers)
            if res:
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
                    }
        except Exception:
            pass
        return {}

    def _get_kuwo_play_url(self, rid):
        try:
            api_url = f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={rid}&br=320kmp3"
            r = self.fetch(api_url, headers=self.kuwo_headers, timeout=8)
            if r:
                data = r.json()
                if data.get('data') and data['data'].get('url'):
                    return data['data']['url']
        except Exception:
            pass
        return ''

    def _get_kuwo_lyric(self, rid):
        lrc_text = ''
        try:
            api_url = f"https://kuwo.cn/openapi/v1/www/lyric/getlyric?musicId={rid}"
            r = self.fetch(api_url, headers=self.kuwo_headers)
            if r:
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
                r = self.fetch(api_url, headers=self.kuwo_headers, timeout=5)
                if r:
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
        return lrc_text

    def _convert_bugpk_lyrics(self, bugpk_lyric):
        lines = []
        for line in bugpk_lyric.split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'\[(\d+),(\d+)\](.*)', line)
            if match:
                start_ms = int(match.group(1))
                text_part = match.group(3)
                text = re.sub(r'<\d+,\d+,\d+>', '', text_part)
                text = text.strip()
                if not text:
                    continue
                minutes = start_ms // 60000
                seconds = (start_ms % 60000) // 1000
                hundredths = (start_ms % 1000) // 10
                lines.append(f"[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{text}")
            else:
                lrc_match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)', line)
                if lrc_match:
                    text = lrc_match.group(4).strip()
                    if text:
                        lines.append(line)
        return '\n'.join(lines)

    def _convert_douyin_lyrics(self, sentences):
        lines = []
        for sentence in sentences:
            start_ms = sentence.get('startMs', 0)
            words = sentence.get('words', [])
            text = ''.join([w.get('text', '') for w in words])
            text = text.strip()
            if not text:
                continue
            minutes = start_ms // 60000
            seconds = (start_ms % 60000) // 1000
            hundredths = (start_ms % 1000) // 10
            lines.append(f"[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{text}")
        return '\n'.join(lines)

    def _clean_lyrics_for_display(self, lrc_text):
        lines = lrc_text.split('\n')
        clean_lines = []
        for line in lines:
            clean_line = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
            if clean_line and not clean_line.startswith('[') and not clean_line.startswith('<'):
                clean_lines.append(clean_line)
        return '\n'.join(clean_lines[:30])

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
                    lines.append({'start': total_seconds, 'text': text})

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
