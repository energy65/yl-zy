# coding=utf-8
# !/usr/bin/python

"""

作者 大圣归来 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

import re
import sys
import json
from base64 import b64encode, b64decode
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
            max_retries=Retry(total=1, backoff_factor=0.1, status_forcelist=[429, 502, 503, 504]),
            pool_connections=50, pool_maxsize=100
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://music.163.com/",
        }
        self.session.headers.update(self.headers)
        self.api = "https://api.bugpk.com/api/163_music"
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._cache = {}

    def getName(self): return "网易云音乐"
    def isVideoFormat(self, url): return bool(re.search(r'\.(mp3|m4a|flac|wav|aac|ogg|m3u8|mp4|mkv)(\?|$)', url or "", re.I))
    def manualVideoCheck(self): return False
    def destroy(self):
        self.executor.shutdown(wait=False)
        self.session.close()

    def _get(self, url, timeout=5):
        """快速GET请求，带缓存"""
        if url in self._cache:
            return self._cache[url]
        try:
            r = self.session.get(url, timeout=timeout)
            data = r.json()
            if data.get("code") == 200:
                self._cache[url] = data
            return data
        except:
            return {}

    def _post(self, url, data, timeout=5):
        """POST请求"""
        try:
            r = self.session.post(url, data=data, timeout=timeout)
            return r.json()
        except:
            return {}

    def _search_songs(self, keyword, limit=30, offset=0):
        """网易云官方搜索API"""
        url = "https://music.163.com/api/search/get/web?csrf_token="
        data = {"s": keyword, "type": 1, "offset": offset, "total": "true", "limit": limit}
        result = self._post(url, data, 6)
        songs = []
        if result.get("code") == 200:
            for s in result.get("result", {}).get("songs", []):
                artists = "/".join([a.get("name", "") for a in s.get("artists", [])])
                album = s.get("album", {})
                songs.append({
                    "id": str(s.get("id", "")),
                    "name": s.get("name", ""),
                    "artists": artists,
                    "album": album.get("name", ""),
                    "picUrl": album.get("picUrl", ""),
                    "mvid": s.get("mvid", 0),
                })
        return songs

    def _playlist_detail(self, pid, limit=50):
        """网易云官方歌单详情API"""
        url = f"https://music.163.com/api/playlist/detail?id={pid}&n={limit}"
        result = self._get(url, 8)
        songs = []
        name = ""
        if result.get("code") == 200:
            r = result.get("result", {})
            name = r.get("name", "")
            for t in r.get("tracks", [])[:limit]:
                artists = "/".join([a.get("name", "") for a in t.get("artists", [])])
                songs.append({
                    "id": str(t.get("id", "")),
                    "name": t.get("name", ""),
                    "artists": artists,
                    "mvid": t.get("mvid", 0),
                })
        return name, songs

    def _toplist(self):
        """网易云官方榜单列表"""
        url = "https://music.163.com/api/toplist"
        result = self._get(url, 6)
        lists = []
        if result.get("code") == 200:
            for item in result.get("list", [])[:15]:
                lists.append({
                    "id": str(item.get("id", "")),
                    "name": item.get("name", ""),
                    "coverImgUrl": item.get("coverImgUrl", ""),
                })
        return lists

    def _song_url(self, song_id, br=320000):
        """获取播放URL - 先试官方，再试第三方API"""
        # 1. 先试官方API
        url = f"https://music.163.com/api/song/enhance/player/url?ids=[{song_id}]&br={br}"
        result = self._get(url, 6)
        if result.get("code") == 200:
            data = result.get("data", [])
            if data and isinstance(data, list):
                u = data[0].get("url", "")
                if u and u.startswith("http"):
                    return u

        # 2. 第三方API兜底
        quality_map = {128000: "standard", 320000: "exhigh", 999000: "lossless"}
        level = quality_map.get(br, "exhigh")

        api_list = [
            f"https://api.injahow.cn/meting/?type=song&server=netease&id={song_id}",
            f"https://api.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level={level}",
            f"https://meting.qjqq.cn/?server=netease&type=song&id={song_id}",
        ]

        for api_url in api_list:
            try:
                r = self.session.get(api_url, timeout=8)
                if r.status_code != 200:
                    continue
                ct = r.headers.get("Content-Type", "")
                u = ""
                if "audio" in ct or "octet-stream" in ct:
                    if r.url.startswith("http") and len(r.url) > 20:
                        u = r.url
                else:
                    try:
                        data = r.json()
                        u = data.get("data", {}).get("url", "") if isinstance(data.get("data"), dict) else ""
                        if not u:
                            u = data.get("url", "")
                        if not u and isinstance(data.get("data"), list) and data["data"]:
                            u = data["data"][0].get("url", "")
                    except Exception:
                        pass
                if isinstance(u, str) and u.startswith("http") and len(u) > 20:
                    return u
            except Exception:
                continue
        return ""

    def _get_lyric(self, song_id):
        try:
            url = f"https://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1"
            r = self.session.get(url, headers=self.headers, timeout=8)
            data = r.json()
            if data.get("code") == 200:
                lrc_obj = data.get("lrc", {})
                lyric = lrc_obj.get("lyric", "") if isinstance(lrc_obj, dict) else ""
                if lyric and len(lyric) > 10:
                    return lyric
        except Exception:
            pass
        return ""

    def homeContent(self, filter):
        classes = [
            {"type_name": n, "type_id": i} for n, i in [
                ("推荐歌单", "cate_playlist"),
                ("热门榜单", "cate_toplist"),
                ("新歌速递", "cate_new"),
                ("MV精选", "cate_mv"),
            ]
        ]
        return {"class": classes, "filters": {}, "list": []}

    def homeVideoContent(self): return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        result = {"list": [], "page": pg, "pagecount": 99, "limit": 30, "total": 99999}

        if tid == "cate_toplist":
            result["list"] = self._fast_toplist()
        elif tid == "cate_playlist":
            result["list"] = self._fast_playlists(pg)
        elif tid == "cate_artist":
            result["list"] = self._fast_artists()
        elif tid == "cate_new":
            result["list"] = self._fast_new_songs()
        elif tid == "cate_mv":
            result["list"] = self._fast_mv_list(pg)
        elif tid.startswith("artist_"):
            artist_name = tid.replace("artist_", "")
            result["list"] = self._fast_search(artist_name, pg)
        else:
            result["list"] = self._fast_playlists(pg)

        # 兜底：确保有数据
        if not result["list"]:
            result["list"] = self._default_playlists()

        return result

    def _fast_toplist(self):
        """快速获取榜单 - 网易云官方API + 兜底"""
        lists = self._toplist()
        
        res = []
        for item in lists[:12]:
            pic = ""
            if item.get("coverImgUrl"):
                pic = f"{self.getProxyUrl()}&url={quote(item['coverImgUrl'])}&type=img"
            res.append({
                "vod_id": f"playlist_{item['id']}",
                "vod_name": item["name"],
                "vod_pic": pic,
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 1.33}
            })

        if not res:
            default = [
                ("飙升榜", "19723756"), ("新歌榜", "3779629"), ("原创榜", "2884035"),
                ("热歌榜", "3778678"), ("抖音榜", "5189186980"), ("ACG榜", "3001835560"),
                ("欧美榜", "2809577409"), ("日语榜", "27135204"), ("韩语榜", "745956260"),
                ("说唱榜", "991319590"), ("电音榜", "1978921795"), ("古典榜", "71384707"),
            ]
            for name, pid in default:
                res.append({
                    "vod_id": f"playlist_{pid}",
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "",
                    "style": {"type": "rect", "ratio": 1.33}
                })
        return res

    def _fast_playlists(self, pg=1):
        """快速获取推荐歌单 - 网易云官方榜单"""
        lists = self._toplist()
        
        res = []
        for item in lists[:10]:
            pic = ""
            if item.get("coverImgUrl"):
                pic = f"{self.getProxyUrl()}&url={quote(item['coverImgUrl'])}&type=img"
            res.append({
                "vod_id": f"playlist_{item['id']}",
                "vod_name": item["name"],
                "vod_pic": pic,
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 1.33}
            })

        if not res:
            res = self._default_playlists()
        return res

    def _fast_artists(self):
        """直接返回歌手列表，不请求API"""
        default = [
            ("周杰伦", "6452"), ("林俊杰", "1119"), ("陈奕迅", "2116"),
            ("邓紫棋", "5199"), ("薛之谦", "5781"), ("毛不易", "12138267"),
            ("李荣浩", "4292"), ("华晨宇", "8736"), ("张学友", "2117"),
            ("王菲", "9643"), ("五月天", "13193"), ("Taylor Swift", "443818"),
            ("Bruno Mars", "3828"), ("Eminem", "21351"), ("BIGBANG", "11159"),
            ("BTS", "12958042"), ("EXO", "14979"), ("刘德华", "3685"),
        ]
        return [{
            "vod_id": f"artist_{name}",
            "vod_name": name,
            "vod_pic": "",
            "vod_remarks": "",
            "style": {"type": "oval", "ratio": 1}
        } for name, _ in default]

    def _fast_new_songs(self):
        """快速获取新歌"""
        data = self._get(f"{self.api}?type=search&keywords=新歌&limit=30")
        
        res = []
        if data.get("code") == 200:
            songs = data.get("data", {}).get("songs", [])
            for s in songs:
                res.append({
                    "vod_id": f"song_{s.get('id', '')}",
                    "vod_name": f"{s.get('name', '')} - {s.get('artists', '')}",
                    "vod_pic": "",
                    "vod_remarks": "新歌",
                    "style": {"type": "rect", "ratio": 1.33}
                })

        if not res:
            default = [("新歌榜", "3779629"), ("飙升榜", "19723756"), ("热歌榜", "3778678")]
            for name, pid in default:
                res.append({
                    "vod_id": f"playlist_{pid}",
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "",
                    "style": {"type": "rect", "ratio": 1.33}
                })
        return res

    def _fast_search(self, keyword, pg=1):
        """快速搜索 - 网易云官方API"""
        offset = (pg - 1) * 30
        songs = self._search_songs(keyword, 30, offset)
        
        res = []
        for s in songs:
            pic = ""
            if s.get("picUrl"):
                pic = f"{self.getProxyUrl()}&url={quote(s['picUrl'])}&type=img"
            res.append({
                "vod_id": f"song_{s['id']}",
                "vod_name": f"{s['name']} - {s['artists']}",
                "vod_pic": pic,
                "vod_remarks": s.get("album", ""),
                "style": {"type": "rect", "ratio": 1.33}
            })
        return res

    def _fast_mv_list(self, pg=1):
        """快速获取MV列表 - 通过搜索热门歌曲，筛选有MV的"""
        res = []
        try:
            offset = (pg - 1) * 30
            data = self._get(f"{self.api}?type=search&keywords=热门歌曲MV&limit=30&offset={offset}", 5)
            if data.get("code") == 200:
                songs = data.get("data", {}).get("songs", [])
                for s in songs:
                    sid = s.get("id", "")
                    name = s.get("name", "")
                    artists = s.get("artists", "")
                    pic = s.get("picUrl", "")
                    res.append({
                        "vod_id": f"mv_{sid}",
                        "vod_name": f"{name} - {artists}" if artists else name,
                        "vod_pic": f"{self.getProxyUrl()}&url={quote(pic)}&type=img" if pic else "",
                        "vod_remarks": "MV",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
        except Exception as e:
            print(f"mv list error: {e}")

        # 兜底
        if not res:
            default_mv = [
                ("周杰伦 - 晴天 MV", "186016"),
                ("周杰伦 - 稻香 MV", "5264644"),
                ("林俊杰 - 江南 MV", "108907"),
                ("陈奕迅 - 浮夸 MV", "64126"),
                ("邓紫棋 - 光年之外 MV", "4375162"),
                ("薛之谦 - 演员 MV", "33204140"),
                ("五月天 - 倔强 MV", "386538"),
                ("Taylor Swift - Love Story MV", "278116"),
            ]
            for name, sid in default_mv:
                res.append({
                    "vod_id": f"mv_{sid}",
                    "vod_name": name,
                    "vod_pic": "",
                    "vod_remarks": "MV",
                    "style": {"type": "rect", "ratio": 1.78}
                })
        return res

    def _default_playlists(self):
        """默认歌单兜底"""
        default = [
            ("华语流行精选", "5071159542"), ("治愈系轻音乐", "3136952023"),
            ("经典老歌回忆", "2829816518"), ("深夜情感电台", "2619366284"),
            ("欧美经典金曲", "2210889524"), ("抖音热门神曲", "2469682731"),
            ("开车必听歌曲", "2039265244"), ("学习工作专注", "806981868"),
            ("运动健身歌单", "991341878"), ("日系清新音乐", "2201210244"),
        ]
        return [{
            "vod_id": f"playlist_{pid}",
            "vod_name": name,
            "vod_pic": "",
            "vod_remarks": "",
            "style": {"type": "rect", "ratio": 1.33}
        } for name, pid in default]

    def detailContent(self, ids):
        """详情页 - 快速加载"""
        vid = ids[0]
        vod = {"vod_id": vid, "vod_name": "", "vod_pic": "", "vod_content": "", 
               "vod_play_from": "网易云音乐", "vod_play_url": ""}
        songs = []

        if vid.startswith("playlist_"):
            pid = vid.replace("playlist_", "")
            name, tracks = self._playlist_detail(pid, 50)
            vod["vod_name"] = name if name else "热门歌单"
            for t in tracks:
                songs.append({
                    "id": t["id"],
                    "name": t["name"],
                    "artist": t["artists"],
                    "mvid": t.get("mvid", 0),
                })

        elif vid.startswith("song_"):
            sid = vid.replace("song_", "")
            songs_data = self._search_songs(sid, 1)
            if songs_data:
                s = songs_data[0]
                songs = [{
                    "id": s["id"],
                    "name": s["name"],
                    "artist": s["artists"],
                    "mvid": s.get("mvid", 0),
                }]
                vod["vod_name"] = s["name"]

        elif vid.startswith("mv_"):
            sid = vid.replace("mv_", "")
            songs_data = self._search_songs(sid, 1)
            mv_name = "MV"
            pic = ""
            if songs_data:
                s = songs_data[0]
                mv_name = f"{s['name']} - {s['artists']} MV"
                if s.get("picUrl"):
                    pic = f"{self.getProxyUrl()}&url={quote(s['picUrl'])}&type=img"
            
            vod["vod_name"] = mv_name
            vod["vod_pic"] = pic
            vod["vod_play_from"] = "MV播放"
            vod["vod_play_url"] = f"播放$mv:{sid}"

        elif vid.startswith("artist_"):
            artist_name = vid.replace("artist_", "")
            songs = self._fast_search(artist_name, 1)[:50]
            vod["vod_name"] = artist_name
            songs = [{
                "id": s["vod_id"].replace("song_", ""),
                "name": s["vod_name"],
                "artist": artist_name,
                "mvid": 0
            } for s in songs]

        # 构建播放列表 - 4个音质线路（多线路模式）
        if songs:
            # 4个音质线路
            quality_list = [
                ("普通音质", "standard"),
                ("高清音质", "exhigh"),
                ("无损音质", "lossless"),
                ("超清音质", "hires"),
            ]
            
            play_from_list = []
            play_url_list = []
            
            for q_name, q_key in quality_list:
                play_from_list.append(q_name)
                # 该音质下的所有歌曲
                eps = []
                for s in songs:
                    sid = str(s["id"])
                    name = s["name"]
                    artist = s["artist"]
                    eps.append(f"{name} - {artist}${sid}__{q_key}")
                play_url_list.append("#".join(eps))
            
            # 用$$$分隔多线路
            vod["vod_play_from"] = "$$$".join(play_from_list)
            vod["vod_play_url"] = "$$$".join(play_url_list)

        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        """播放 - 支持音乐和MV"""
        raw_id = id.strip()
        
        is_mv = raw_id.startswith("mv:")
        if is_mv:
            raw_id = raw_id.replace("mv:", "")
        
        song_id = raw_id.split("__")[0]
        quality_key = raw_id.split("__")[1] if "__" in raw_id else ""

        quality_name_map = {
            "普通音质": "standard",
            "高清音质": "exhigh",
            "无损音质": "lossless",
            "超清音质": "hires",
        }
        quality = quality_name_map.get(flag, quality_name_map.get(quality_key, "exhigh"))

        br_map = {
            "standard": 128000,
            "exhigh": 320000,
            "lossless": 999000,
            "hires": 999000,
        }
        br = br_map.get(quality, 320000)

        play_url = ""
        lrc_text = ""
        
        if not raw_id.startswith("mv:"):
            lrc_text = self._get_lyric(song_id)
        
        if is_mv or (flag and "MV" in str(flag)):
            mv_id = 0
            play_url = ""
            
            try:
                song_url = f"https://music.163.com/api/song/detail/?id={song_id}&ids=[{song_id}]"
                song_headers = self.headers.copy()
                song_headers["Cookie"] = "appver=8.12.41"
                song_headers["Host"] = "music.163.com"
                r = self.session.get(song_url, headers=song_headers, timeout=10)
                song_data = r.json()
                songs = song_data.get("songs", [])
                if songs:
                    mv_id = songs[0].get("mvid", 0)
                
                if mv_id and mv_id != 0 and mv_id != "0":
                    mv_url = f"https://music.163.com/api/mv/detail?id={mv_id}"
                    mv_headers = self.headers.copy()
                    mv_headers["Cookie"] = "appver=8.12.41"
                    mv_headers["Host"] = "music.163.com"
                    r = self.session.get(mv_url, headers=mv_headers, timeout=10)
                    mv_data = r.json()
                    
                    if mv_data.get("code") == 200:
                        brs = mv_data.get("data", {}).get("brs", {})
                        for q in ["1080", "720", "480", "240"]:
                            if str(q) in brs:
                                play_url = brs[str(q)]
                                break
            except Exception as e:
                print(f"mv play error: {e}")
            
            if not play_url:
                play_url = self._song_url(song_id, 320000)
        else:
            play_url = self._song_url(song_id, br)
            if not play_url:
                fallback_br = [320000, 128000, 999000]
                for fb in fallback_br:
                    if fb == br:
                        continue
                    u = self._song_url(song_id, fb)
                    if u:
                        play_url = u
                        break

        result = {"parse": 0, "url": play_url, "header": self.headers}
        if lrc_text:
            result["lrc"] = lrc_text
        return result

    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        pg = int(pg or 1)
        result = {"list": self._fast_search(key, pg), "page": pg, "pagecount": 99, "limit": 30, "total": 9999}
        return result

    def localProxy(self, param):
        url = unquote(param.get("url", ""))
        if param.get("type") == "img":
            try:
                r = self.session.get(url, timeout=5)
                return [200, "image/jpeg", r.content, {}]
            except:
                return [404, "text/plain", b"Error", {}]
        return None

    def e64(self, text): return b64encode(text.encode("utf-8")).decode("utf-8")
    def d64(self, text): return b64decode(text.encode("utf-8")).decode("utf-8")
