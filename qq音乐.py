# coding=utf-8
# !/usr/bin/python

"""
QQ音乐 TVBox 脚本
作者：基于公开API实现，仅供学习交流使用
"""

from base.spider import Spider
import requests
import json
import re
import sys
import base64
import time
import random
import urllib3
from urllib.parse import quote, unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')


class Spider(Spider):
    # XOR加密的微信推广信息，运行时通过_get_wechat_info解密
    _w_key = b'qqmusic_wechat_2026'
    _w_data = [
        148, 207, 195, 145, 204, 200, 134, 218, 219, 129, 223, 255, 132, 251, 232, 208,
        176, 174, 208, 203, 225, 136, 255, 232, 129, 222, 240, 147, 222, 213, 142, 208,
        243, 189, 178, 173, 221, 138, 253, 151, 246, 193, 150, 205, 249, 187, 203, 253,
        139, 220, 201, 156, 234, 182, 214, 136, 166, 148, 193, 208, 144, 239, 193, 133,
        229, 231, 128, 233, 243, 135, 249, 207, 218, 133, 146, 209, 248, 249
    ]

    def getName(self):
        return "QQ音乐"

    def init(self, extend=""):
        self.host = "https://y.qq.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/'
        }
        self.wap_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://i.y.qq.com/'
        }
        self.kw_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'Referer': 'https://m.kuwo.cn/'
        }
        self.quality_config = [
            ("普通", "M500", "mp3"),
            ("高清", "M800", "mp3"),
            ("超清", "A000", "ape"),
            ("无损", "F000", "flac"),
        ]
        self.DEFAULT_SONG_PIC = "https://y.gtimg.cn/mediastyle/mobile_v12/img/singer_300.png"
        # 榜单ID到名称的兜底映射
        self.TOP_NAME_MAP = {
            '4': '巅峰榜·新歌',
            '26': '巅峰榜·热歌',
            '62': '巅峰榜·飙升',
            '28': '巅峰榜·网络歌曲',
            '29': '巅峰榜·影视金曲',
            '30': '巅峰榜·流行指数',
            '31': '巅峰榜·听歌识曲',
            '33': '巅峰榜·K歌金曲',
        }

    def _get_wechat_info(self):
        try:
            key = self._w_key
            return bytes([b ^ key[i % len(key)] for i, b in enumerate(self._w_data)]).decode('utf-8')
        except Exception:
            return ''

    def _http(self, url, headers=None, timeout=10, **kwargs):
        h = self.headers.copy()
        if headers:
            h.update(headers)
        return requests.get(url, headers=h, timeout=timeout, verify=False, **kwargs)

    def _pic_url(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('http://'):
            url = 'https://' + url[7:]
        return url

    def _album_pic(self, albummid):
        if not albummid:
            return ''
        return 'https://y.gtimg.cn/music/photo_new/T002R300x300M000%s.jpg' % albummid

    def _singer_pic(self, singermid):
        if not singermid:
            return ''
        return 'https://y.gtimg.cn/music/photo_new/T001R300x300M000%s.jpg' % singermid

    def _clean(self, text):
        return re.sub(r'[$#]', '', str(text or '')).strip()

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|mp3|m4a|flv|flac|wav)(\?|$)', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        result = {}
        cateId = [
            {"type_name": "推荐榜单", "type_id": "toplist"},
            {"type_name": "热门歌手", "type_id": "singer_hot"},
            {"type_name": "新歌榜", "type_id": "new_songs"},
            {"type_name": "热歌榜", "type_id": "hot_songs"},
            {"type_name": "飙升榜", "type_id": "rise_songs"},
            {"type_name": "网络歌曲榜", "type_id": "net_songs"},
            {"type_name": "影视金曲榜", "type_id": "movie_songs"},
            {"type_name": "VIP金曲", "type_id": "vip_songs"},
        ]
        result['class'] = cateId
        result['list'] = []
        return result

    def homeVideoContent(self):
        return self.categoryContent("toplist", 1, False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        pg = int(pg) if pg else 1

        try:
            if tid == "toplist":
                videos = self._get_toplist()
            elif tid == "singer_hot":
                videos = self._get_hot_singers(pg)
            elif tid == "new_songs":
                videos = self._get_toplist_songs(4, pg)
            elif tid == "hot_songs":
                videos = self._get_toplist_songs(26, pg)
            elif tid == "rise_songs":
                videos = self._get_toplist_songs(62, pg)
            elif tid == "net_songs":
                videos = self._get_toplist_songs(28, pg)
            elif tid == "movie_songs":
                videos = self._get_toplist_songs(29, pg)
            elif tid == "vip_songs":
                videos = self._get_vip_songs(pg)
            elif tid.startswith("playlist_"):
                topid = tid.replace("playlist_", "")
                videos = self._get_playlist_songs(topid, pg)
            elif tid.startswith("singer_detail_"):
                singermid, singername = self._parse_singer_id(tid)
                videos = self._get_singer_songs(singermid, pg, singername)
        except Exception as e:
            print(f"categoryContent error: {e}")

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = getattr(self, '_last_pagecount', 99) or 99
        result['limit'] = 30
        result['total'] = result['pagecount'] * 30
        return result

    def _get_toplist(self):
        videos = []
        try:
            url = "https://c.y.qq.com/v8/fcg-bin/fcg_myqq_toplist.fcg?format=json&g_tk=5381&uin=0&platform=h5"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                top_list = data.get('data', {}).get('topList', [])
                for item in top_list:
                    vid = f"playlist_{item.get('id', '')}"
                    name = item.get('topTitle', '')
                    pic = self._pic_url(item.get('picUrl', ''))
                    remark = item.get('updateTips', '')
                    videos.append({
                        "vod_id": vid,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": remark,
                        "vod_tag": "folder"
                    })
        except Exception as e:
            print(f"_get_toplist error: {e}")
        return videos

    def _get_toplist_songs(self, topid, pg=1):
        videos = []
        total = 0
        try:
            url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?format=json&topid={topid}&page=detail&g_tk=5381"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                songlist = data.get('songlist', [])
                total = len(songlist)
                # 接口一次返回全部歌曲，统一按每页30条切片，避免第1页重复返回全部
                start = (pg - 1) * 30
                songlist = songlist[start:start + 30]
                for item in songlist:
                    song_data = item.get('data', item)
                    song_id = song_data.get('songid', song_data.get('id', ''))
                    song_name = self._clean(song_data.get('songname', song_data.get('name', '')))
                    singer = self._clean('/'.join([s.get('name', '') for s in song_data.get('singer', [])]))
                    name = f"{song_name} - {singer}" if singer else song_name
                    pic = self._album_pic(song_data.get('albummid', ''))
                    albumname = self._clean(song_data.get('albumname', ''))
                    videos.append({
                        "vod_id": f"song_{song_id}",
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": albumname
                    })
        except Exception as e:
            print(f"_get_toplist_songs error: {e}")
        self._last_pagecount = (total + 29) // 30 if total else 99
        return videos

    def _get_playlist_songs(self, topid, pg=1):
        return self._get_toplist_songs(topid, pg)

    def _get_hot_singers(self, pg=1):
        videos = []
        try:
            sin = (pg - 1) * 30
            data_param = json.dumps({
                "comm": {"ct": 24, "cv": 0},
                "singerList": {
                    "module": "Music.SingerListServer",
                    "method": "get_singer_list",
                    "param": {
                        "area": -100,
                        "sex": -100,
                        "genre": -100,
                        "index": -100,
                        "sin": sin,
                        "cur_page": pg
                    }
                }
            }, separators=(',', ':'))
            url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?g_tk=5381&format=json&data={quote(data_param)}"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                singer_data = data.get('singerList', {}).get('data', {})
                singer_list = singer_data.get('singerlist', singer_data.get('singerList', []))
                if isinstance(singer_list, list):
                    for item in singer_list:
                        singer_mid = item.get('singer_mid', item.get('mid', ''))
                        singer_name = item.get('singer_name', item.get('name', ''))
                        singer_pic = self._singer_pic(singer_mid)
                        if singer_mid and singer_name:
                            vid = f"singer_detail_{singer_mid}__{quote(singer_name)}"
                            videos.append({
                                "vod_id": vid,
                                "vod_name": singer_name,
                                "vod_pic": singer_pic,
                                "vod_remarks": "歌手",
                                "vod_tag": "folder"
                            })
            if not videos:
                videos = self._get_hot_singers_from_toplist()
        except Exception as e:
            print(f"_get_hot_singers error: {e}")
            videos = self._get_hot_singers_from_toplist()
        return videos

    def _get_hot_singers_from_toplist(self):
        videos = []
        try:
            toplist_ids = [26, 4, 62, 28, 29]
            seen_mid = set()
            for topid in toplist_ids:
                if len(videos) >= 50:
                    break
                url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?format=json&topid={topid}&page=detail&g_tk=5381"
                try:
                    r = self._http(url, timeout=8)
                    data = r.json()
                    if data.get('code') == 0:
                        songlist = data.get('songlist', [])
                        for item in songlist:
                            if len(videos) >= 50:
                                break
                            song_data = item.get('data', item)
                            singers = song_data.get('singer', [])
                            for s in singers:
                                s_mid = s.get('mid', '')
                                s_name = s.get('name', '')
                                if s_mid and s_name and s_mid not in seen_mid:
                                    seen_mid.add(s_mid)
                                    pic = f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{s_mid}.jpg"
                                    vid = f"singer_detail_{s_mid}__{quote(s_name)}"
                                    videos.append({
                                        "vod_id": vid,
                                        "vod_name": s_name,
                                        "vod_pic": pic,
                                        "vod_remarks": "歌手",
                                        "vod_tag": "folder"
                                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"_get_hot_singers_from_toplist error: {e}")
        return videos

    def _get_vip_songs(self, pg=1):
        videos = []
        try:
            keywords = ["VIP 热门歌曲", "付费精选", "VIP 金曲", "付费歌曲"]
            keyword = keywords[(pg - 1) % len(keywords)]
            search_url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p={pg}&n=30&w={quote(keyword)}&format=json"
            r = self._http(search_url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                song_list = data.get('data', {}).get('song', {}).get('list', [])
                for item in song_list:
                    song_id = item.get('songid', '')
                    song_name = self._clean(item.get('songname', ''))
                    singer = self._clean('/'.join([s.get('name', '') for s in item.get('singer', [])]))
                    name = f"{song_name} - {singer}" if singer else song_name
                    pic = self._album_pic(item.get('albummid', ''))
                    album_name = self._clean(item.get('albumname', ''))
                    videos.append({
                        "vod_id": f"song_{song_id}",
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": album_name
                    })
            if not videos:
                videos = self._get_toplist_songs(26, pg)
        except Exception as e:
            print(f"_get_vip_songs error: {e}")
            videos = self._get_toplist_songs(26, pg)
        return videos

    def _parse_singer_id(self, did):
        raw = did.replace("singer_detail_", "", 1)
        singermid = raw
        singername = ""
        if "__" in raw:
            parts = raw.split("__", 1)
            singermid = parts[0]
            try:
                singername = unquote(parts[1])
            except Exception:
                singername = parts[1]
        return singermid, singername

    def _get_singer_songs(self, singermid, pg=1, singername=""):
        videos = []
        try:
            begin = (pg - 1) * 30
            url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg?format=json&singermid={singermid}&order=listen&begin={begin}&num=30&g_tk=5381"
            r = self._http(url, timeout=10)
            text = r.text if r is not None else ''
            try:
                data = json.loads(text)
            except Exception:
                json_match = re.search(r'\{.*\}', text, re.S)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = {}
            song_list = []
            s_name = singername
            if data.get('code') == 0:
                song_list = data.get('data', {}).get('list', data.get('data', {}).get('songlist', []))
                if not s_name:
                    s_name = data.get('data', {}).get('singer_name', '')
            if not song_list:
                return self._get_singer_songs_by_search(singermid, pg, singername)
            # 接口已按begin/num分页，禁止再次切片（旧逻辑会导致第2页起永远为空）
            for item in song_list:
                song_data = item.get('musicData', item)
                song_id = song_data.get('songid', song_data.get('id', ''))
                song_name = self._clean(song_data.get('songname', song_data.get('name', '')))
                albumname = self._clean(song_data.get('albumname', ''))
                pic = self._album_pic(song_data.get('albummid', ''))
                name = f"{song_name} - {s_name}" if s_name else song_name
                videos.append({
                    "vod_id": f"song_{song_id}",
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": albumname
                })
        except Exception as e:
            print(f"_get_singer_songs error: {e}")
            videos = self._get_singer_songs_by_search(singermid, pg, singername)
        return videos

    def _get_singer_songs_by_search(self, singermid, pg=1, singername=""):
        videos = []
        try:
            keyword = singername if singername else singermid
            search_url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p={pg}&n=30&w={quote(keyword)}&format=json"
            r = self._http(search_url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                song_list = data.get('data', {}).get('song', {}).get('list', [])
                for item in song_list:
                    song_id = item.get('songid', '')
                    song_name = self._clean(item.get('songname', ''))
                    singer = self._clean('/'.join([s.get('name', '') for s in item.get('singer', [])]))
                    name = f"{song_name} - {singer}" if singer else song_name
                    pic = self._album_pic(item.get('albummid', ''))
                    album_name = self._clean(item.get('albumname', ''))
                    videos.append({
                        "vod_id": f"song_{song_id}",
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": album_name
                    })
        except Exception as e:
            print(f"_get_singer_songs_by_search error: {e}")
        return videos

    def detailContent(self, ids):
        did = ids[0]
        result = {"list": []}

        try:
            if did.startswith("playlist_"):
                return self._playlist_detail(did)
            elif did.startswith("singer_detail_"):
                return self._singer_detail(did)
            elif did.startswith("song_"):
                return self._song_detail(did)
        except Exception as e:
            print(f"detailContent error: {e}")

        return result

    def _quality_sources(self):
        return [q for q, _, _ in self.quality_config]

    def _build_play_entry(self, song_data):
        """把歌曲数据组装成 (播放条目, 封面, songid, songmid, 歌名, 歌手)"""
        song_id = str(song_data.get('songid', song_data.get('id', '')) or '')
        song_mid = str(song_data.get('songmid', song_data.get('mid', '')) or '')
        song_name = self._clean(song_data.get('songname', song_data.get('name', '')))
        singer = self._clean('/'.join([s.get('name', '') for s in song_data.get('singer', []) if s.get('name')]))
        albumname = self._clean(song_data.get('albumname', ''))
        pic = self._album_pic(song_data.get('albummid', ''))
        display = f"{song_name} - {singer}" if singer else song_name
        play_id = f"{song_id}|{song_mid}" if song_mid else song_id
        entry = f"{display}${play_id}"
        return entry, pic, song_id, song_mid, song_name, singer, albumname

    def _playlist_detail(self, did):
        result = {"list": []}
        topid = did.replace("playlist_", "")
        try:
            url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?format=json&topid={topid}&page=detail&g_tk=5381"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                topinfo = data.get('topinfo', {})
                list_title = (topinfo.get('ListName') or topinfo.get('listTitle')
                              or topinfo.get('topTitle') or topinfo.get('title')
                              or self.TOP_NAME_MAP.get(str(topid), 'QQ音乐榜单'))
                pic = self._pic_url(topinfo.get('pic_v12') or topinfo.get('picDetail')
                                    or topinfo.get('pic', topinfo.get('pic_mid', '')))
                desc = re.sub(r'<[^>]+>', '', topinfo.get('info', '') or '').strip()

                play_arr = []
                pic_arr = []
                for item in data.get('songlist', []):
                    entry, pic_url, _, _, _, _, _ = self._build_play_entry(item.get('data', item))
                    if entry.split('$')[0]:
                        play_arr.append(entry)
                        pic_arr.append(pic_url or self.DEFAULT_SONG_PIC)

                if play_arr:
                    sources = self._quality_sources()
                    song_list = "#".join(play_arr)
                    pic_list = "#".join(pic_arr)
                    content = self._get_wechat_info() + "\n" + (desc if desc else "QQ音乐榜单，每日更新")
                    vod = {
                        "vod_id": did,
                        "vod_name": list_title,
                        "vod_pic": pic,
                        "vod_content": content,
                        "vod_remarks": f"歌曲 : {len(play_arr)}首",
                        "vod_play_from": "$$$".join(sources),
                        "vod_play_url": "$$$".join([song_list for _ in sources]),
                        "vod_play_pic": "$$$".join([pic_list for _ in sources]),
                        "vod_play_pic_ratio": 1.0,
                    }
                    result['list'] = [vod]
        except Exception as e:
            print(f"_playlist_detail error: {e}")

        return result

    def _singer_detail(self, did):
        result = {"list": []}
        singermid, singername = self._parse_singer_id(did)
        play_arr = []
        pic_arr = []
        seen = set()
        singer_name = singername or ''
        singer_pic = self._singer_pic(singermid)

        def collect(items):
            for item in items:
                song_data = item.get('musicData', item)
                entry, pic, song_id, _, song_name, singer, _ = self._build_play_entry(song_data)
                if song_id and song_id not in seen and song_name:
                    seen.add(song_id)
                    play_arr.append(entry)
                    pic_arr.append(pic or self.DEFAULT_SONG_PIC)
                    if not singer_name and singer:
                        return singer
            return None

        try:
            # 接口每页最多返回30首，循环翻页抓取（参照kuwo歌手详情）
            # c.y.qq.com 偶发临时限流（404空body），失败页重试，不把失败当成末页
            fail_streak = 0
            for begin in range(0, 300, 30):
                url = (f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg?format=json"
                       f"&singermid={singermid}&order=listen&begin={begin}&num=30&g_tk=5381")
                page_list = None
                for attempt in range(3):
                    try:
                        r = self._http(url, timeout=10)
                        text = r.text if r is not None else ''
                        try:
                            data = json.loads(text)
                        except Exception:
                            mm = re.search(r'\{.*\}', text, re.S)
                            data = json.loads(mm.group()) if mm else {}
                        if data.get('code') == 0:
                            d = data.get('data', {})
                            if not singer_name:
                                singer_name = d.get('singer_name', '') or ''
                            page_list = d.get('list', d.get('songlist', [])) or []
                            break
                    except Exception:
                        pass
                    time.sleep(0.8 + attempt * 1.0)
                if page_list is None:
                    # 接口失败：容忍一次后继续，连续2页失败才终止
                    fail_streak += 1
                    if fail_streak >= 2:
                        break
                    continue
                fail_streak = 0
                if not page_list:
                    break  # code=0且无数据：真正末页
                before = len(play_arr)
                ns = collect(page_list)
                if ns and not singer_name:
                    singer_name = ns
                if len(play_arr) == before:
                    break
                time.sleep(0.3)

            # 翻页被限流或歌曲过少时，用soso搜索补全（soso接口较稳定）
            if len(play_arr) < 30:
                keyword = singer_name if singer_name else singermid
                for sp in (1, 2):
                    if len(play_arr) >= 120:
                        break
                    try:
                        search_url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p={sp}&n=50&w={quote(keyword)}&format=json"
                        r = self._http(search_url, timeout=10)
                        data = r.json()
                        if data.get('code') != 0:
                            continue
                        song_list = data.get('data', {}).get('song', {}).get('list', [])
                        if song_list and not singer_name:
                            singer_name = self._clean('/'.join(
                                [ss.get('name', '') for ss in song_list[0].get('singer', []) if ss.get('name')]))
                        for item in song_list:
                            ssinger = self._clean('/'.join(
                                [ss.get('name', '') for ss in item.get('singer', []) if ss.get('name')]))
                            # 只收该歌手演唱的歌，避免歌名命中关键词的无关歌曲
                            if singer_name and singer_name not in ssinger:
                                continue
                            collect([item])
                    except Exception:
                        continue

            if play_arr:
                sources = self._quality_sources()
                song_list = "#".join(play_arr)
                pic_list = "#".join(pic_arr)
                vod = {
                    "vod_id": did,
                    "vod_name": singer_name if singer_name else "歌手",
                    "vod_pic": singer_pic,
                    "vod_content": self._get_wechat_info() + "\n" + (f"歌手：{singer_name}" if singer_name else ""),
                    "vod_remarks": f"歌曲 : {len(play_arr)}首",
                    "vod_actor": singer_name,
                    "vod_play_from": "$$$".join(sources),
                    "vod_play_url": "$$$".join([song_list for _ in sources]),
                    "vod_play_pic": "$$$".join([pic_list for _ in sources]),
                    "vod_play_pic_ratio": 1.0,
                }
                result['list'] = [vod]
        except Exception as e:
            print(f"_singer_detail error: {e}")

        return result

    def _resolve_song_info(self, songid, songmid=''):
        """通过musicu详情/搜索补全歌曲信息，返回 dict(songid/songmid/name/singer/album/pic)"""
        songid = str(songid or '').strip()
        info = {'songid': songid, 'songmid': songmid or '', 'name': '', 'singer': '', 'album': '', 'pic': ''}
        if songid and str(songid).isdigit():
            try:
                data_param = json.dumps({
                    "comm": {"ct": 24, "cv": 0},
                    "songinfo": {
                        "method": "get_song_detail_yqq",
                        "param": {"song_mid": "", "song_id": int(songid)},
                        "module": "music.pf_song_detail_svr"
                    }
                }, separators=(',', ':'))
                url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?g_tk=5381&format=json&data={quote(data_param)}"
                r = self._http(url, timeout=8)
                data = r.json()
                if data.get('code') == 0:
                    ti = data.get('songinfo', {}).get('data', {}).get('track_info', {})
                    if ti:
                        info['name'] = ti.get('name', '')
                        info['songmid'] = ti.get('mid', '') or info['songmid']
                        info['singer'] = '/'.join([s.get('name', '') for s in ti.get('singer', []) if s.get('name')])
                        album = ti.get('album', {}) or {}
                        info['album'] = album.get('name', '')
                        info['pic'] = self._album_pic(album.get('mid', ''))
            except Exception:
                pass

        if (not info['songmid'] or not info['name']) and songid:
            try:
                w = quote(str(songid))
                search_url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p=1&n=1&w={w}&format=json"
                r = self._http(search_url, timeout=8)
                data = r.json()
                if data.get('code') == 0:
                    sl = data.get('data', {}).get('song', {}).get('list', [])
                    if sl:
                        item = sl[0]
                        info['name'] = info['name'] or item.get('songname', '')
                        info['songmid'] = info['songmid'] or item.get('songmid', '')
                        info['singer'] = info['singer'] or '/'.join(
                            [s.get('name', '') for s in item.get('singer', []) if s.get('name')])
                        info['album'] = info['album'] or item.get('albumname', '')
                        info['pic'] = info['pic'] or self._album_pic(item.get('albummid', ''))
            except Exception:
                pass

        info['name'] = self._clean(info['name'])
        info['singer'] = self._clean(info['singer'])
        info['album'] = self._clean(info['album'])
        return info

    def _song_detail(self, did):
        result = {"list": []}
        songid = did.replace("song_", "")
        try:
            info = self._resolve_song_info(songid)
            song_name = info['name'] or f"歌曲_{songid}"
            singer = info['singer']
            pic = info['pic'] or self.DEFAULT_SONG_PIC
            album_name = info['album']
            songmid = info['songmid']
            full_name = f"{song_name} - {singer}" if singer else song_name

            play_id = f"{songid}|{songmid}" if songmid else str(songid)
            display = f"{full_name}${play_id}"

            # 选集=该歌手的全部热门歌曲（"该歌单"），当前歌曲置顶，便于上下首切换
            play_arr = [display]
            pic_arr = [pic]
            seen = {str(songid)}
            if singer:
                try:
                    kw = quote(singer)
                    surl = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p=1&n=40&w={kw}&format=json"
                    r = self._http(surl, timeout=10)
                    sdata = r.json()
                    if sdata.get('code') == 0:
                        slist = sdata.get('data', {}).get('song', {}).get('list', [])
                        for item in slist:
                            ssinger = self._clean('/'.join(
                                [s.get('name', '') for s in item.get('singer', []) if s.get('name')]))
                            if singer not in ssinger and ssinger not in singer:
                                continue
                            entry, ep, sid, _, _, _, _ = self._build_play_entry(item)
                            if sid and str(sid) not in seen and entry.split('$')[0]:
                                seen.add(str(sid))
                                play_arr.append(entry)
                                pic_arr.append(ep or pic)
                except Exception:
                    pass

            sources = self._quality_sources()
            song_list = "#".join(play_arr)
            pic_list = "#".join(pic_arr)
            content = self._get_wechat_info() + "\n来源：QQ音乐"
            if singer:
                content += f"\n歌手：{singer}"
            if album_name:
                content += f"\n专辑：{album_name}"
            vod = {
                "vod_id": did,
                "vod_name": full_name,
                "vod_pic": pic,
                "vod_content": content,
                "vod_remarks": f"歌曲 : {len(play_arr)}首" if len(play_arr) > 1 else (album_name or 'QQ音乐'),
                "vod_actor": singer,
                "vod_play_from": "$$$".join(sources),
                "vod_play_url": "$$$".join([song_list for _ in sources]),
                "vod_play_pic": "$$$".join([pic_list for _ in sources]),
                "vod_play_pic_ratio": 1.0,
            }
            result['list'] = [vod]
        except Exception as e:
            print(f"_song_detail error: {e}")

        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
        songmid = ''
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["url"] = raw_id
                result["header"] = dict(self.headers)
                return result

            # 兼容 && 与 name$id 形式的播放ID（与kuwo一致的健壮解析）
            rid = raw_id.split("&&")[0].strip()
            if '$' in rid:
                picked = ''
                for part in reversed(rid.split('$')):
                    if '|' in part or part.isdigit():
                        picked = part
                        break
                rid = picked or rid.split('$')[-1]
            if '|' in rid:
                songid, songmid = rid.split('|', 1)
            else:
                songid, songmid = rid, ''
            songid = str(songid).strip()
            songmid = str(songmid).strip()

            info = self._resolve_song_info(songid, songmid)
            songmid = info.get('songmid') or songmid

            play_url = ""
            from_kw = False

            # 1) QQ官方vkey直链（免费歌曲，purl存在即可信，无需HEAD探测）
            if songmid:
                play_url = self._get_play_url_vkey(songmid, flag) or self._get_play_url_vkey(songmid, "")

            # 2) VIP/版权歌曲官方返回104003时，跨平台用酷我免费源兜底（参照kuwo多方法回退）
            if not play_url and info.get('name'):
                play_url = self._get_kuwo_fallback(info['name'], info.get('singer', ''), flag)
                from_kw = bool(play_url)

            if play_url:
                result["url"] = play_url
                result["header"] = dict(self.kw_headers) if from_kw else dict(self.headers)

            # 歌词与5行SSA字幕
            if songmid:
                try:
                    lrc = self._get_lyric(songmid)
                    if lrc:
                        result["lrc"] = lrc
                        ssa_lrc = self._create_ssa_subtitle(lrc)
                        if ssa_lrc:
                            ssa_base64 = base64.b64encode(ssa_lrc.encode('utf-8')).decode('utf-8')
                            result["subs"] = [{
                                "name": "5行歌词",
                                "url": f"data:text/x-ssa;base64,{ssa_base64}",
                                "format": "text/x-ssa",
                                "selected": True
                            }]
                except Exception:
                    pass

        except Exception as e:
            print(f"playerContent error: {e}")

        return result

    def _get_vkey(self, songmid, filenames):
        if not songmid or not filenames:
            return {}
        try:
            guid = str(random.randint(100000000, 999999999))
            data_param = json.dumps({
                "req_0": {
                    "module": "vkey.GetVkeyServer",
                    "method": "CgiGetVkey",
                    "param": {
                        "guid": guid,
                        "songmid": [songmid] * len(filenames),
                        "filename": filenames,
                        "songtype": [0] * len(filenames),
                        "uin": "0",
                        "loginflag": 1,
                        "platform": "20"
                    }
                }
            }, separators=(',', ':'))
            url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?g_tk=5381&format=json&data={quote(data_param)}"
            r = self._http(url, timeout=10)
            data = r.json()
            req_0 = data.get('req_0', {})
            if data.get('code') == 0 and req_0.get('code') == 0:
                d0 = req_0.get('data', {})
                midurlinfo = d0.get('midurlinfo', [])
                sip = d0.get('sip', [])
                if sip and midurlinfo:
                    base = str(sip[0]).rstrip('/')
                    res = {}
                    for it, fn in zip(midurlinfo, filenames):
                        if it and it.get('result', -1) == 0 and it.get('purl'):
                            purl = it.get('purl', '')
                            res[fn] = purl if purl.startswith('http') else f"{base}/{purl}"
                    return res
            return {}
        except Exception as e:
            print(f"_get_vkey error: {e}")
            return {}

    def _get_play_url_vkey(self, songmid, flag=""):
        if not songmid:
            return ""
        try:
            fns = {q: f"{fmt}{songmid}.{ext}" for q, fmt, ext in self.quality_config}
            mp = self._get_vkey(songmid, list(fns.values()))
            order = [q for q, _, _ in self.quality_config]
            if flag and flag in fns:
                order = [flag] + [q for q in order if q != flag]
            for q in order:
                fn = fns.get(q)
                if fn and fn in mp and mp[fn]:
                    return mp[fn]
            return ""
        except Exception as e:
            print(f"_get_play_url_vkey error: {e}")
            return ""

    def _norm_song_name(self, text):
        """歌名归一化：去空白/括号/Live等后缀词，用于跨平台匹配"""
        t = re.sub(r'（.*?）|\(.*?\)|【.*?】|\[.*?\]', '', str(text or ''))
        t = re.sub(r'[\s\-_/.,，。、！!~～]+', '', t).lower()
        return t

    def _kw_search(self, keyword):
        """酷我搜索，返回 [(rid, 歌名, 歌手)]"""
        result = []
        try:
            search_url = (f"https://search.kuwo.cn/r.s?client=kt&all={quote(keyword)}"
                          f"&pn=0&rn=10&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1")
            r = self._http(search_url, headers=self.kw_headers, timeout=8)
            content = r.text or ''
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            data = json.loads(content)
            for it in data.get('abslist', []):
                rid = it.get('DC_TARGETID')
                if rid and it.get('DC_TARGETTYPE') == 'music':
                    name = str(it.get('SONGNAME', it.get('NAME', '')))
                    artist = str(it.get('ARTIST', it.get('FARTIST', '')))
                    result.append((str(rid), name, artist))
        except Exception as e:
            print(f"_kw_search error: {e}")
        return result

    def _kw_url(self, rid, bitrate=320):
        """酷我nmobi签名转直链"""
        try:
            api_url = ("https://nmobi.kuwo.cn/mobi.s?f=web&user=0"
                       "&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign"
                       f"&rid={rid}&bitrate={bitrate}&format=mp3")
            r = self._http(api_url, headers=self.kw_headers, timeout=8)
            data = r.json()
            url = data.get('data', {}).get('url', '')
            if url and url.startswith('http'):
                return url
        except Exception:
            pass
        return ''

    def _get_kuwo_fallback(self, song_name, singer, flag=""):
        """QQ官方无版权/需VIP时，按歌名+歌手在酷我取免费直链"""
        try:
            keyword = f"{song_name} {singer.split('/')[0]}".strip() if singer else song_name
            items = self._kw_search(keyword)
            if not items:
                items = self._kw_search(song_name)

            target = self._norm_song_name(song_name)
            best = None
            best_score = -1
            for rid, name, artist in items[:10]:
                score = 0
                nname = self._norm_song_name(name)
                if nname == target:
                    score += 100
                elif target and (target in nname or nname in target):
                    score += 40
                if singer:
                    first = self._norm_song_name(singer.split('/')[0])
                    if first and first in self._norm_song_name(artist):
                        score += 30
                if score > best_score:
                    best_score = score
                    best = rid
            if not best or best_score < 40:
                return ''

            # 高音质优先、逐级降级（酷我ape部分设备不兼容，统一mp3）
            bitrates = [320, 192, 128] if flag in ('高清', '超清', '无损') else [128, 320, 192]
            for br in bitrates:
                url = self._kw_url(best, br)
                if url:
                    return url
        except Exception as e:
            print(f"_get_kuwo_fallback error: {e}")
        return ''

    def _get_lyric(self, songmid):
        if not songmid:
            return ""
        try:
            lyric = self._get_lyric_official(songmid)
            if lyric:
                return lyric
        except Exception:
            pass
        try:
            lyric = self._get_lyric_thirdparty(songmid)
            if lyric:
                return lyric
        except Exception:
            pass
        return ""

    def _get_lyric_official(self, songmid):
        if not songmid:
            return ""
        try:
            url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={songmid}&format=json&nobase64=0&g_tk=5381"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                lyric_b64 = data.get('lyric', '')
                if lyric_b64:
                    lyric = base64.b64decode(lyric_b64).decode('utf-8')
                    return lyric
            return ""
        except Exception as e:
            print(f"_get_lyric_official error: {e}")
            return ""

    def _get_lyric_thirdparty(self, songmid):
        if not songmid:
            return ""
        try:
            api_list = [
                f"https://api.injahow.cn/meting/?type=lrc&id={songmid}&server=tencent&format=json",
                f"https://meting.qjqq.cn/?server=tencent&type=lrc&id={songmid}",
            ]
            for api_url in api_list:
                try:
                    r = self._http(api_url, timeout=8)
                    if r.status_code == 200:
                        ct = r.headers.get('Content-Type', '')
                        if 'json' in ct:
                            try:
                                data = r.json()
                                lrc = data.get('lrc', {}).get('lyric', '') or data.get('lyric', '')
                                if lrc and '[ti:' not in lrc and '[00:' in lrc:
                                    return lrc
                            except Exception:
                                pass
                        else:
                            text = r.text.strip()
                            if text and '[00:' in text:
                                return text
                except Exception:
                    continue
            return ""
        except Exception as e:
            print(f"_get_lyric_thirdparty error: {e}")
            return ""

    def searchContent(self, key, quick, pg=1):
        result = {}
        videos = []
        pg = int(pg) if pg else 1

        try:
            w = quote(key)
            per_page = 20
            url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?p={pg}&n={per_page}&w={w}&format=json"
            r = self._http(url, timeout=10)
            data = r.json()
            if data.get('code') == 0:
                song_list = data.get('data', {}).get('song', {}).get('list', [])
                for item in song_list:
                    song_id = item.get('songid', '')
                    song_name = self._clean(item.get('songname', ''))
                    singer = self._clean('/'.join([s.get('name', '') for s in item.get('singer', []) if s.get('name')]))
                    name = f"{song_name} - {singer}" if singer else song_name
                    pic = self._album_pic(item.get('albummid', ''))
                    album_name = self._clean(item.get('albumname', ''))
                    videos.append({
                        "vod_id": f"song_{song_id}",
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": album_name
                    })
        except Exception as e:
            print(f"searchContent error: {e}")

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 20
        result['total'] = 999999
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

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