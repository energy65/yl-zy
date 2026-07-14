# coding=utf-8
# !/usr/bin/python

"""
网易云音乐 - 有MV版
作者：基于公开API实现，仅供学习交流使用
功能：歌单、歌手、搜索、播放、歌词、选集、MV、音质分类
"""

import re
import sys
import json
import base64
from urllib.parse import quote, unquote
from requests import Session, adapters
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://music.163.com"
        self.session = Session()
        adapter = adapters.HTTPAdapter(
            max_retries=Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504]),
            pool_connections=30, pool_maxsize=60
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://music.163.com/",
            "Accept": "application/json, text/plain, */*",
        }
        self.session.headers.update(self.headers)
        self.executor = ThreadPoolExecutor(max_workers=8)
        self._cache = {}
        self.wx_tag = "源力软件汇"
        self.quality_list = [
            ("标准128K", "standard", 128000),
            ("高清192K", "higher", 192000),
            ("超清320K", "exhigh", 320000),
            ("无损APE", "lossless", 999000),
        ]
        self._precache_data()

    def _precache_data(self):
        try:
            precache_urls = [
                "https://music.163.com/api/personalized/playlist?limit=30&offset=0",
                "https://music.163.com/api/toplist",
                "https://music.163.com/api/personalized/newsong",
            ]
            futures = []
            for url in precache_urls:
                future = self.executor.submit(self._get, url, timeout=10)
                futures.append(future)
            
            for i, future in enumerate(futures):
                try:
                    data = future.result()
                    if data.get("code") == 200:
                        print(f"预缓存成功: {precache_urls[i]}")
                    else:
                        print(f"预缓存失败: {precache_urls[i]}")
                except Exception as e:
                    print(f"预缓存异常: {precache_urls[i]} - {e}")
        except Exception as e:
            print("预缓存初始化失败:", e)

    def getName(self):
        return "网易云音乐"

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(mp3|m4a|flac|wav|aac|ogg|m3u8|mp4|mkv)(\?|$)', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.executor.shutdown(wait=False)
        except:
            pass
        self.session.close()

    def _get(self, url, timeout=8, use_cache=True):
        if use_cache and url in self._cache:
            return self._cache[url]
        try:
            r = self.session.get(url, timeout=timeout)
            data = r.json()
            if use_cache:
                self._cache[url] = data
            return data
        except:
            return {}

    def _post(self, url, data=None, timeout=8):
        try:
            r = self.session.post(url, data=data, timeout=timeout)
            return r.json()
        except:
            return {}

    def _get_song_pic(self, song):
        try:
            al = song.get('al', song.get('album', {}))
            if isinstance(al, dict):
                pic = al.get('picUrl', '')
                if pic:
                    return pic
            pic = song.get('picUrl', '')
            if pic:
                return pic
            return song.get('pic', '')
        except:
            return ''

    def _get_song_name(self, song):
        return song.get('name', '')

    def _get_song_artist(self, song):
        try:
            ar = song.get('ar', song.get('artists', []))
            if isinstance(ar, list):
                names = [a.get('name', '') for a in ar if isinstance(a, dict)]
                return '/'.join(names)
            return str(ar)
        except:
            return ''

    def homeContent(self, filter):
        classes = [
            {"type_name": "推荐歌单", "type_id": "cate_playlist"},
            {"type_name": "热门榜单", "type_id": "cate_toplist"},
            {"type_name": "新歌速递", "type_id": "cate_new"},
            {"type_name": "歌手列表", "type_id": "cate_artist"},
            {"type_name": "MV精选", "type_id": "cate_mv"},
        ]
        return {"class": classes, "filters": {}, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        result = {"list": [], "page": pg, "pagecount": 99, "limit": 30, "total": 99999}
        try:
            if tid == "cate_toplist":
                result["list"] = self._get_toplist()
            elif tid == "cate_playlist":
                result["list"] = self._get_playlists(pg)
            elif tid == "cate_artist":
                result["list"] = self._get_artists()
            elif tid == "cate_new":
                result["list"] = self._get_new_songs()
            elif tid == "cate_mv":
                result["list"] = self._get_mv_list(pg)
            elif tid.startswith("pl_detail_"):
                pid = tid.replace("pl_detail_", "")
                detail = self._get_playlist_detail(pid)
                result["list"] = detail["list"]
            elif tid.startswith("bang_detail_"):
                bid = tid.replace("bang_detail_", "")
                detail = self._get_bang_detail(bid)
                result["list"] = detail["list"]
            elif tid.startswith("artist_detail_"):
                aid = tid.replace("artist_detail_", "")
                detail = self._get_artist_detail(aid)
                result["list"] = detail["list"]
            elif tid == "new_songs_detail":
                detail = self._get_new_songs_detail()
                result["list"] = detail["list"]
            else:
                result["list"] = self._get_playlists(pg)
        except Exception as e:
            print("categoryContent error:", e)

        if not result["list"]:
            result["list"] = self._default_playlists()

        return result

    def _get_toplist(self):
        result = []
        try:
            data = self._get("https://music.163.com/api/toplist", timeout=8)
            if data.get("code") == 200:
                lists = data.get("list", data.get("listToplist", []))
                for item in lists[:20]:
                    rid = item.get("id", "")
                    name = item.get("name", "")
                    pic = item.get("coverImgUrl", item.get("picUrl", ""))
                    result.append({
                        "vod_id": "bang_detail_" + str(rid),
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": "官方榜单",
                        "vod_tag": "folder"
                    })
        except Exception as e:
            print("_get_toplist error:", e)

        if not result:
            default = [
                ("飙升榜", "19723756"), ("新歌榜", "3779629"), ("原创榜", "2884035"),
                ("热歌榜", "3778678"), ("抖音榜", "5189186980"), ("ACG榜", "3001835560"),
                ("欧美榜", "2809577409"), ("日语榜", "27135204"), ("韩语榜", "745956260"),
                ("说唱榜", "991319590"), ("电音榜", "1978921795"), ("古典榜", "71384707"),
            ]
            for name, pid in default:
                result.append({
                    "vod_id": "bang_detail_" + pid,
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "官方榜单",
                    "vod_tag": "folder"
                })
        return result

    def _get_playlists(self, pg=1):
        result = []
        try:
            data = self._get("https://music.163.com/api/personalized/playlist?limit=30&offset=" + str((pg - 1) * 30), timeout=8)
            if data.get("code") == 200:
                lists = data.get("result", [])
                for item in lists[:30]:
                    rid = item.get("id", "")
                    name = item.get("name", "")
                    pic = item.get("picUrl", item.get("coverImgUrl", ""))
                    play_count = item.get("playCount", 0)
                    result.append({
                        "vod_id": "pl_detail_" + str(rid),
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": str(play_count // 10000) + "万播放" if play_count > 10000 else str(play_count) + "次",
                        "vod_tag": "folder"
                    })
        except Exception as e:
            print("_get_playlists error:", e)

        if not result:
            result = self._default_playlists()
        return result

    def _get_artists(self):
        default = [
            ("周杰伦", "6452"), ("林俊杰", "1119"), ("陈奕迅", "2116"),
            ("邓紫棋", "5199"), ("薛之谦", "5781"), ("毛不易", "12138267"),
            ("李荣浩", "4292"), ("华晨宇", "8736"), ("张学友", "2117"),
            ("王菲", "9643"), ("五月天", "13193"), ("Taylor Swift", "443818"),
            ("Bruno Mars", "3828"), ("Eminem", "21351"), ("BIGBANG", "11159"),
            ("BTS", "12958042"), ("EXO", "14979"), ("刘德华", "3685"),
        ]
        result = []
        for name, aid in default:
            result.append({
                "vod_id": "artist_detail_" + str(aid),
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "热门歌手",
                "vod_tag": "folder"
            })
        return result

    def _get_new_songs(self):
        result = []
        try:
            data = self._get("https://music.163.com/api/personalized/newsong", timeout=8)
            if data.get("code") == 200:
                result_list = data.get("result", [])
                if result_list:
                    result.append({
                        "vod_id": "new_songs_detail",
                        "vod_name": "新歌速递",
                        "vod_pic": "",
                        "vod_remarks": "最新发布",
                        "vod_tag": "folder"
                    })
        except Exception as e:
            print("_get_new_songs error:", e)

        if not result:
            result.append({
                "vod_id": "new_songs_detail",
                "vod_name": "新歌速递",
                "vod_pic": "",
                "vod_remarks": "最新发布",
                "vod_tag": "folder"
            })
        return result

    def _get_mv_list(self, pg=1):
        result = []
        try:
            data = self._get("https://music.163.com/api/mv/first?limit=30&offset=" + str((pg - 1) * 30), timeout=8)
            if data.get("code") == 200:
                mvs = data.get("data", [])
                for mv in mvs[:30]:
                    mvid = mv.get("id", "")
                    name = mv.get("name", "")
                    artist = mv.get("artistName", "")
                    pic = mv.get("cover", "")
                    play_count = mv.get("playCount", 0)
                    full_name = name + (" - " + artist if artist else "")
                    result.append({
                        "vod_id": "mv_" + str(mvid),
                        "vod_name": full_name,
                        "vod_pic": pic,
                        "vod_remarks": str(play_count) + "次播放",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
        except Exception as e:
            print("_get_mv_list error:", e)

        if not result:
            default_mv = [
                ("周杰伦 - 晴天 MV", "504177"),
                ("周杰伦 - 稻香 MV", "5264644"),
                ("林俊杰 - 江南 MV", "108907"),
                ("陈奕迅 - 浮夸 MV", "64126"),
                ("邓紫棋 - 光年之外 MV", "4375162"),
                ("薛之谦 - 演员 MV", "33204140"),
                ("五月天 - 倔强 MV", "386538"),
            ]
            for name, mvid in default_mv:
                result.append({
                    "vod_id": "mv_" + str(mvid),
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "MV",
                    "style": {"type": "rect", "ratio": 1.78}
                })
        return result

    def _search_songs(self, keyword, pg=1):
        result = []
        try:
            offset = (pg - 1) * 30
            url = "https://music.163.com/api/search/get/web"
            data = {
                "s": keyword,
                "type": 1,
                "offset": offset,
                "limit": 30,
                "total": "true"
            }
            res = self._post(url, data=data, timeout=8)
            if res.get("code") == 200:
                songs = res.get("result", {}).get("songs", [])
                for s in songs[:30]:
                    sid = s.get("id", "")
                    name = s.get("name", "")
                    artist = self._get_song_artist(s)
                    pic = self._get_song_pic(s)
                    album = s.get("album", {}).get("name", "") if isinstance(s.get("album"), dict) else ""
                    full_name = name + (" - " + artist if artist else "")
                    result.append({
                        "vod_id": "song_" + str(sid),
                        "vod_name": full_name,
                        "vod_pic": pic,
                        "vod_remarks": album,
                        "style": {"type": "rect", "ratio": 1.33}
                    })
        except Exception as e:
            print("_search_songs error:", e)
        return result

    def _get_playlist_songs(self, playlist_id, pg=1):
        result = []
        try:
            data = self._get("https://music.163.com/api/playlist/detail?id=" + str(playlist_id), timeout=10)
            if data.get("code") == 200:
                tracks = data.get("result", {}).get("tracks", [])
                for s in tracks[:50]:
                    sid = s.get("id", "")
                    name = s.get("name", "")
                    artist = self._get_song_artist(s)
                    pic = self._get_song_pic(s)
                    full_name = name + (" - " + artist if artist else "")
                    result.append({
                        "vod_id": "song_" + str(sid),
                        "vod_name": full_name,
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "style": {"type": "rect", "ratio": 1.33}
                    })
        except Exception as e:
            print("_get_playlist_songs error:", e)
        return result

    def _default_playlists(self):
        default = [
            ("华语流行精选", "5071159542"), ("治愈系轻音乐", "3136952023"),
            ("经典老歌回忆", "2829816518"), ("深夜情感电台", "2619366284"),
            ("欧美经典金曲", "2210889524"), ("抖音热门神曲", "2469682731"),
            ("开车必听歌曲", "2039265244"), ("学习工作专注", "806981868"),
            ("运动健身歌单", "991341878"), ("日系清新音乐", "2201210244"),
        ]
        result = []
        for name, pid in default:
            result.append({
                "vod_id": "pl_detail_" + pid,
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "网易云歌单",
                "vod_tag": "folder"
            })
        return result

    def detailContent(self, ids):
        try:
            vid = ids[0].strip()
            if vid.startswith("song_"):
                return self._get_song_detail_vod(vid)
            elif vid.startswith("artist_detail_"):
                artist_id = vid.replace("artist_detail_", "")
                return self._get_artist_detail(artist_id)
            elif vid.startswith("pl_detail_"):
                pid = vid.replace("pl_detail_", "")
                return self._get_playlist_detail(pid)
            elif vid.startswith("bang_detail_"):
                bang_id = vid.replace("bang_detail_", "")
                return self._get_bang_detail(bang_id)
            elif vid.startswith("mv_"):
                mvid = vid.replace("mv_", "")
                return self._get_mv_detail_vod(mvid)
            elif vid == "new_songs_detail":
                return self._get_new_songs_detail()
            else:
                return self._get_song_detail_vod(vid)
        except Exception as e:
            print("detailContent error:", e)
            return {"list": []}

    def _build_play_lines(self, songs):
        play_arr = []
        play_pics = []
        for s in songs:
            sid = str(s.get("id", ""))
            name = s.get("name", "")
            artist = s.get("artist", "")
            pic = s.get("pic", "")
            if not sid or not name:
                continue
            display_name = name + " - " + artist if artist and artist != name else name
            display_name = re.sub(r'<[^>]+>', '', display_name)
            display_name = re.sub(r'[$#]', '', display_name).strip()
            play_arr.append(display_name + "$" + sid)
            play_pics.append(pic)
        return play_arr, play_pics

    def _build_vod_with_qualities(self, vod_id, vod_name, vod_pic, vod_content, vod_remarks, vod_actor, play_arr, play_pics):
        if not play_arr:
            return {
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_content": vod_content,
                "vod_remarks": vod_remarks,
                "vod_actor": vod_actor,
                "vod_play_from": "",
                "vod_play_url": "",
            }

        song_list = "#".join(play_arr)
        qualities = [q[0] + " - " + self.wx_tag for q in self.quality_list]
        vod_play_from = "$$$".join(qualities)
        vod_play_url = "$$$".join([song_list for _ in qualities])

        vod = {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": "微信公众号：" + self.wx_tag + "\n福利多多，精彩多多\n" + (vod_content or ""),
            "vod_remarks": vod_remarks or ("歌曲 : " + str(len(play_arr)) + "首"),
            "vod_actor": vod_actor,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url,
        }
        if play_pics:
            first_pic = play_pics[0] if play_pics else ""
            vod["vod_play_pic"] = "$$$".join([first_pic for _ in qualities])
            vod["vod_play_pic_ratio"] = 1.5
        return vod

    def _get_playlist_detail(self, playlist_id):
        songs = []
        vod_name = "网易云歌单"
        vod_pic = ""
        vod_content = ""

        try:
            data = self._get("https://music.163.com/api/playlist/detail?id=" + str(playlist_id), timeout=15)
            if data.get("code") == 200:
                result = data.get("result", {})
                vod_name = result.get("name", "网易云歌单")
                vod_pic = result.get("coverImgUrl", "")
                vod_content = result.get("description", "")

                tracks = result.get("tracks", [])
                track_ids = result.get("trackIds", [])
                max_songs = 200

                if tracks and len(tracks) > 0:
                    seen = set()
                    for t in tracks[:max_songs]:
                        sid = str(t.get("id", ""))
                        if sid and sid not in seen:
                            seen.add(sid)
                            name = t.get("name", "")
                            artist = self._get_song_artist(t)
                            pic = self._get_song_pic(t)
                            songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})
                elif track_ids:
                    all_ids = [str(t.get("id", "")) for t in track_ids if t.get("id")]
                    unique_ids = list(dict.fromkeys(all_ids))[:max_songs]
                    batch_size = 100
                    all_songs_data = []
                    for i in range(0, len(unique_ids), batch_size):
                        batch = unique_ids[i:i+batch_size]
                        ids_str = ",".join(batch)
                        songs_data = self._get("https://music.163.com/api/song/detail?ids=[" + ids_str + "]", timeout=10)
                        if songs_data.get("code") == 200:
                            all_songs_data.extend(songs_data.get("songs", []))
                    for s in all_songs_data:
                        sid = str(s.get("id", ""))
                        name = s.get("name", "")
                        artist = self._get_song_artist(s)
                        pic = self._get_song_pic(s)
                        if sid and name:
                            songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})

                seen = set()
                unique_songs = []
                for s in songs:
                    sid = str(s["id"])
                    if sid not in seen:
                        seen.add(sid)
                        unique_songs.append(s)
                songs = unique_songs
        except Exception as e:
            print("_get_playlist_detail error:", e)

        if not songs:
            songs = self._get_fallback_songs("热门歌曲")
            vod_name = vod_name or "网易云歌单"

        play_arr, play_pics = self._build_play_lines(songs)
        vod = self._build_vod_with_qualities(
            "pl_detail_" + str(playlist_id),
            vod_name,
            vod_pic or (play_pics[0] if play_pics else ""),
            vod_content,
            "歌曲 : " + str(len(play_arr)) + "首",
            "网易云音乐",
            play_arr,
            play_pics
        )
        return {"list": [vod]}

    def _get_artist_songs_list(self, artist_id, artist_name="", pg=1):
        result = []
        try:
            data = self._get("https://music.163.com/api/artist/top/song?id=" + str(artist_id), timeout=10)
            if data.get("code") == 200:
                songs = data.get("songs", [])
                for s in songs[:50]:
                    sid = s.get("id", "")
                    name = s.get("name", "")
                    ar = self._get_song_artist(s)
                    pic = self._get_song_pic(s)
                    full_name = name + (" - " + ar if ar else "")
                    result.append({
                        "vod_id": "song_" + str(sid),
                        "vod_name": full_name,
                        "vod_pic": pic,
                        "vod_remarks": "热门",
                        "style": {"type": "rect", "ratio": 1.33}
                    })
        except Exception as e:
            print("_get_artist_songs_list error:", e)
        if not result:
            result = self._search_songs(artist_name or "热门歌曲", pg)
        return result

    def _get_fallback_songs(self, keyword="热门歌曲"):
        songs = []
        try:
            search_result = self._search_songs(keyword, 1)
            for item in search_result:
                sid = item["vod_id"].replace("song_", "")
                name = item["vod_name"]
                pic = item.get("vod_pic", "")
                artist = ""
                if " - " in name:
                    parts = name.split(" - ", 1)
                    artist = parts[0]
                    name = parts[1]
                if sid and name:
                    songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})
        except Exception as e:
            print("_get_fallback_songs error:", e)
        return songs

    def _get_new_songs_detail(self):
        songs = []
        vod_name = "新歌速递"
        vod_pic = ""
        vod_content = ""

        try:
            data = self._get("https://music.163.com/api/personalized/newsong", timeout=15)
            if data.get("code") == 200:
                result_list = data.get("result", [])
                seen = set()
                for item in result_list:
                    song = item.get("song", item)
                    sid = str(song.get("id", ""))
                    if sid and sid not in seen:
                        seen.add(sid)
                        name = song.get("name", "")
                        artist = self._get_song_artist(song)
                        pic = self._get_song_pic(song)
                        songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})
        except Exception as e:
            print("_get_new_songs_detail error:", e)

        if not songs:
            songs = self._get_fallback_songs("新歌")

        play_arr, play_pics = self._build_play_lines(songs)
        vod = self._build_vod_with_qualities(
            "new_songs_detail",
            vod_name,
            vod_pic or (play_pics[0] if play_pics else ""),
            vod_content,
            "歌曲 : " + str(len(play_arr)) + "首",
            "网易云音乐",
            play_arr,
            play_pics
        )
        return {"list": [vod]}

    def _get_song_detail_vod(self, song_id):
        songs = []
        vod_name = "歌曲"
        vod_pic = ""
        vod_actor = ""
        lrc = ""

        try:
            sid = song_id.replace("song_", "") if song_id.startswith("song_") else song_id
            data = self._get("https://music.163.com/api/song/detail/?id=" + sid + "&ids=[" + sid + "]", timeout=8)
            if data.get("code") == 200:
                s_list = data.get("songs", [])
                if s_list:
                    s = s_list[0]
                    name = s.get("name", "")
                    artist = self._get_song_artist(s)
                    pic = self._get_song_pic(s)
                    songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})
                    vod_name = name
                    vod_pic = pic
                    vod_actor = artist
                    lrc = self._get_lyric(sid)
        except Exception as e:
            print("_get_song_detail_vod error:", e)

        if not songs:
            songs = self._get_fallback_songs(vod_name)
            if songs:
                vod_name = songs[0]["name"]
                vod_pic = songs[0].get("pic", "")
                vod_actor = songs[0].get("artist", "")

        play_arr, play_pics = self._build_play_lines(songs)
        vod = self._build_vod_with_qualities(
            "song_" + str(song_id),
            vod_name,
            vod_pic or (play_pics[0] if play_pics else ""),
            lrc,
            "单曲",
            vod_actor,
            play_arr,
            play_pics
        )
        return {"list": [vod]}

    def _get_artist_detail(self, artist_id):
        songs = []
        artist_name = ""
        artist_pic = ""
        artist_brief = ""

        try:
            artist_data = self._get("https://music.163.com/api/artist/" + str(artist_id), timeout=10)
            if artist_data.get("code") == 200:
                artist_info = artist_data.get("artist", {})
                artist_name = artist_info.get("name", "")
                artist_pic = artist_info.get("picUrl", "")
                artist_brief = artist_info.get("briefDesc", "")

            data = self._get("https://music.163.com/api/artist/top/song?id=" + str(artist_id), timeout=15)
            if data.get("code") == 200:
                song_list = data.get("songs", [])
                seen = set()
                for s in song_list[:200]:
                    sid = str(s.get("id", ""))
                    if sid and sid not in seen:
                        seen.add(sid)
                        name = s.get("name", "")
                        ar = self._get_song_artist(s)
                        pic = self._get_song_pic(s)
                        if name:
                            songs.append({"id": sid, "name": name, "artist": ar, "pic": pic})
        except Exception as e:
            print("_get_artist_detail error:", e)

        if not songs:
            songs = self._get_fallback_songs(artist_name or "热门歌曲")
            if not artist_name:
                artist_name = "热门歌手"

        play_arr, play_pics = self._build_play_lines(songs)
        vod = self._build_vod_with_qualities(
            "artist_detail_" + str(artist_id),
            artist_name or "歌手",
            artist_pic or (play_pics[0] if play_pics else ""),
            artist_brief or ("共 " + str(len(play_arr)) + " 首歌曲"),
            "歌曲 : " + str(len(play_arr)) + "首",
            artist_name,
            play_arr,
            play_pics
        )
        return {"list": [vod]}

    def _get_bang_detail(self, bang_id):
        songs = []
        vod_name = "网易云榜单"
        vod_pic = ""
        vod_content = ""

        try:
            data = self._get("https://music.163.com/api/playlist/detail?id=" + str(bang_id), timeout=15)
            if data.get("code") == 200:
                result = data.get("result", {})
                vod_name = result.get("name", "网易云榜单")
                vod_pic = result.get("coverImgUrl", "")
                vod_content = result.get("description", "")

                tracks = result.get("tracks", [])
                track_ids = result.get("trackIds", [])
                max_songs = 200

                if tracks and len(tracks) > 0:
                    seen = set()
                    for t in tracks[:max_songs]:
                        sid = str(t.get("id", ""))
                        if sid and sid not in seen:
                            seen.add(sid)
                            name = t.get("name", "")
                            artist = self._get_song_artist(t)
                            pic = self._get_song_pic(t)
                            songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})
                elif track_ids:
                    all_ids = [str(t.get("id", "")) for t in track_ids if t.get("id")]
                    unique_ids = list(dict.fromkeys(all_ids))[:max_songs]
                    batch_size = 100
                    all_songs_data = []
                    for i in range(0, len(unique_ids), batch_size):
                        batch = unique_ids[i:i+batch_size]
                        ids_str = ",".join(batch)
                        songs_data = self._get("https://music.163.com/api/song/detail?ids=[" + ids_str + "]", timeout=10)
                        if songs_data.get("code") == 200:
                            all_songs_data.extend(songs_data.get("songs", []))
                    for s in all_songs_data:
                        sid = str(s.get("id", ""))
                        name = s.get("name", "")
                        artist = self._get_song_artist(s)
                        pic = self._get_song_pic(s)
                        if sid and name:
                            songs.append({"id": sid, "name": name, "artist": artist, "pic": pic})

                seen = set()
                unique_songs = []
                for s in songs:
                    sid = str(s["id"])
                    if sid not in seen:
                        seen.add(sid)
                        unique_songs.append(s)
                songs = unique_songs
        except Exception as e:
            print("_get_bang_detail error:", e)

        if not songs:
            songs = self._get_fallback_songs("热门歌曲")
            vod_name = vod_name or "网易云榜单"

        play_arr, play_pics = self._build_play_lines(songs)
        vod = self._build_vod_with_qualities(
            "bang_detail_" + str(bang_id),
            vod_name,
            vod_pic or (play_pics[0] if play_pics else ""),
            vod_content,
            "歌曲 : " + str(len(play_arr)) + "首",
            "网易云音乐",
            play_arr,
            play_pics
        )
        return {"list": [vod]}

    def _get_mv_detail_vod(self, mvid):
        vod = {
            "vod_id": "mv_" + str(mvid),
            "vod_name": "MV",
            "vod_pic": "",
            "vod_content": "",
            "vod_actor": "",
            "vod_remarks": "MV",
            "vod_play_from": "",
            "vod_play_url": "",
        }
        try:
            data = self._get("https://music.163.com/api/mv/detail?id=" + str(mvid), timeout=8)
            if data.get("code") == 200:
                mv_data = data.get("data", {})
                vod["vod_name"] = mv_data.get("name", "MV")
                vod["vod_pic"] = mv_data.get("cover", "")
                vod["vod_content"] = "微信公众号：" + self.wx_tag + "\n福利多多，精彩多多\n" + (mv_data.get("desc", "") or "")
                vod["vod_actor"] = mv_data.get("artistName", "")
                vod["vod_remarks"] = "MV"

                brs = mv_data.get("brs", {})
                if brs:
                    eps = []
                    for br_str, url in brs.items():
                        if url:
                            label = str(br_str) + "P - " + self.wx_tag
                            eps.append(label + "$mv:" + str(mvid) + ":" + br_str)
                    if eps:
                        vod["vod_play_from"] = "MV播放 - " + self.wx_tag
                        vod["vod_play_url"] = "#".join(eps)
        except Exception as e:
            print("_get_mv_detail_vod error:", e)

        return {"list": [vod]}

    def _create_ssa_subtitle(self, lrc_text):
        lines = lrc_text.strip().split("\n")
        ssa_lines = []
        ssa_lines.append("[Script Info]")
        ssa_lines.append("Title: 5行歌词")
        ssa_lines.append("ScriptType: v4.00+")
        ssa_lines.append("WrapStyle: 2")
        ssa_lines.append("PlayResX: 1920")
        ssa_lines.append("PlayResY: 1080")
        ssa_lines.append("ScaledBorderAndShadow: yes")
        ssa_lines.append("")
        ssa_lines.append("[V4+ Styles]")
        ssa_lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
        ssa_lines.append("Style: Default,微软雅黑,60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,30,30,30,1")
        ssa_lines.append("Style: Current,微软雅黑,72,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,30,30,30,1")
        ssa_lines.append("")
        ssa_lines.append("[Events]")
        ssa_lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        import re
        lrc_pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
        parsed = []
        for line in lines:
            m = lrc_pattern.match(line.strip())
            if m:
                minutes = int(m.group(1))
                seconds = float(m.group(2))
                text = m.group(3).strip()
                total_seconds = minutes * 60 + seconds
                if text:
                    parsed.append((total_seconds, text))

        def format_time(sec):
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            cs = int((sec - int(sec)) * 100)
            return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

        window = 5
        for i, (start_time, text) in enumerate(parsed):
            end_idx = min(i + 1, len(parsed) - 1)
            end_time = parsed[end_idx][0] if end_idx > i else start_time + 5
            start_idx = max(0, i - 2)
            end_idx_window = min(len(parsed), i + 3)
            display_lines = []
            for j in range(start_idx, end_idx_window):
                if j == i:
                    display_lines.append(("{\\rCurrent}" + parsed[j][1]))
                else:
                    display_lines.append(parsed[j][1])
            display_text = "\\N".join(display_lines)
            ssa_lines.append(f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{display_text}")

        return "\n".join(ssa_lines)

    def _get_lyric(self, song_id):
        lrc = ""
        try:
            data = self._get("https://music.163.com/api/song/lyric?os=pc&id=" + str(song_id) + "&lv=-1&kv=-1&tv=-1", timeout=8)
            if data.get("code") == 200:
                lrc_obj = data.get("lrc", {})
                if lrc_obj:
                    lrc = lrc_obj.get("lyric", "")
        except Exception as e:
            print("_get_lyric error:", e)
        return lrc

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}, "lrc": ""}
        try:
            raw_id = str(id).strip()

            if raw_id.startswith("mv:"):
                parts = raw_id.replace("mv:", "").split(":")
                mvid = parts[0] if parts else ""
                br = parts[1] if len(parts) > 1 else "1080"
                mv_url = self._get_mv_url(mvid, br)
                if mv_url:
                    result["url"] = mv_url
                    result["header"] = self.headers
                return result

            song_id = raw_id.split("__")[0] if "__" in raw_id else raw_id

            quality_map = {
                "标准128K": "standard",
                "高清192K": "higher",
                "超清320K": "exhigh",
                "无损APE": "lossless",
            }

            clean_flag = flag
            if flag and " - " in flag:
                clean_flag = flag.split(" - ")[0].strip()

            quality_key = quality_map.get(clean_flag, "standard")

            play_url = self._get_play_url(song_id, quality_key)
            if play_url:
                result["url"] = play_url
                result["header"] = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://music.163.com/",
                }

            lrc = self._get_lyric(song_id)
            if lrc:
                result["lrc"] = lrc
                try:
                    ssa_lrc = self._create_ssa_subtitle(lrc)
                    import base64
                    ssa_base64 = base64.b64encode(ssa_lrc.encode("utf-8")).decode("utf-8")
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

    def _get_play_url(self, song_id, quality_key="standard"):
        play_url = ""

        try:
            quality_map = {
                "standard": 128000,
                "higher": 192000,
                "exhigh": 320000,
                "lossless": 999000,
            }
            br = quality_map.get(quality_key, 320000)

            api_list = [
                self._get_play_url_injahow,
                self._get_play_url_official,
                self._get_play_url_kuwo,
            ]

            for api_func in api_list:
                try:
                    url = api_func(song_id, br, quality_key)
                    if url and url.startswith("http"):
                        play_url = url
                        break
                except Exception as e:
                    print("play url func error:", e)
                    continue

        except Exception as e:
            print("_get_play_url error:", e)

        return play_url

    def _get_play_url_injahow(self, song_id, br, quality_key):
        try:
            url = "https://api.injahow.cn/meting/?server=netease&type=url&id=" + str(song_id)
            r = self.session.get(url, timeout=10, allow_redirects=True, stream=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if "audio" in ct or "octet" in ct:
                    return r.url
                if r.content and len(r.content) > 50000:
                    return r.url
        except Exception as e:
            print("_get_play_url_injahow error:", e)
        return ""

    def _get_play_url_official(self, song_id, br, quality_key):
        try:
            url = "https://music.163.com/api/song/enhance/player/url?ids=[" + str(song_id) + "]&br=" + str(br)
            data = self._get(url, timeout=8)
            if data.get("code") == 200:
                data_list = data.get("data", [])
                if data_list:
                    d = data_list[0]
                    u = d.get("url", "")
                    if u and u.startswith("http"):
                        return u
        except Exception as e:
            print("_get_play_url_official error:", e)
        return ""

    def _get_play_url_kuwo(self, song_id, br, quality_key):
        try:
            song_info = self._get_song_basic_info(song_id)
            if not song_info:
                return ""

            song_name = song_info.get("name", "")
            artist = song_info.get("artist", "")
            if not song_name:
                return ""

            keyword = song_name + " " + artist if artist else song_name
            search_url = "https://www.kuwo.cn/api/www/search/searchMusicBykeyWord?key=" + quote(keyword) + "&pn=1&rn=5"
            search_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.kuwo.cn/",
                "csrf": "abc123",
                "Cookie": "kw_token=abc123"
            }
            r = self.session.get(search_url, headers=search_headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == 200:
                    result_list = data.get("data", {}).get("list", [])
                    if result_list:
                        best_rid = ""
                        best_score = 0
                        for s in result_list[:5]:
                            s_name = s.get("name", "")
                            s_artist = s.get("artist", "")
                            s_rid = str(s.get("rid", ""))
                            score = 0
                            if song_name and song_name in s_name:
                                score += 10
                            if artist and artist in s_artist:
                                score += 10
                            if s_name == song_name:
                                score += 5
                            if score > best_score:
                                best_score = score
                                best_rid = s_rid

                        if best_rid:
                            bitrate = br // 1000 if br > 1000 else 320
                            if bitrate > 320:
                                bitrate = 320
                            play_api = ("https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk"
                                       "&type=convert_url_with_sign&rid=" + best_rid + "&bitrate=" + str(bitrate) + "&format=mp3")
                            kuwo_headers = {
                                "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
                                "Referer": "https://www.kuwo.cn/"
                            }
                            r2 = self.session.get(play_api, headers=kuwo_headers, timeout=8)
                            if r2.status_code == 200:
                                d2 = r2.json()
                                if d2.get("code") == 200 and d2.get("data") and d2["data"].get("url"):
                                    return d2["data"]["url"]
        except Exception as e:
            print("_get_play_url_kuwo error:", e)
        return ""

    def _get_song_basic_info(self, song_id):
        try:
            data = self._get("https://music.163.com/api/song/detail/?id=" + str(song_id) + "&ids=[" + str(song_id) + "]", timeout=8)
            if data.get("code") == 200:
                songs = data.get("songs", [])
                if songs:
                    s = songs[0]
                    return {
                        "id": s.get("id", ""),
                        "name": s.get("name", ""),
                        "artist": self._get_song_artist(s),
                        "pic": self._get_song_pic(s),
                    }
        except Exception as e:
            print("_get_song_basic_info error:", e)
        return None

    def _get_mv_url(self, mvid, br="1080"):
        try:
            data = self._get("https://music.163.com/api/mv/detail?id=" + str(mvid), timeout=8)
            if data.get("code") == 200:
                brs = data.get("data", {}).get("brs", {})
                if brs:
                    br_int = int(br) if str(br).isdigit() else 1080
                    for test_br in [br_int, 1080, 720, 480, 240]:
                        if str(test_br) in brs and brs[str(test_br)]:
                            return brs[str(test_br)]
        except Exception as e:
            print("_get_mv_url error:", e)

        return ""

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        result = {"list": self._search_songs(key, pg), "page": pg, "pagecount": 99, "limit": 30, "total": 9999}
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        url = unquote(param.get("url", ""))
        if param.get("type") == "img":
            try:
                r = self.session.get(url, timeout=5)
                return [200, "image/jpeg", r.content, {}]
            except:
                return [404, "text/plain", b"Error", {}]
        return None

    def e64(self, text):
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    def d64(self, text):
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")
