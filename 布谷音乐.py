import re
import sys
import html as html_mod
import json
from base64 import b64encode, b64decode
from urllib.parse import quote
from requests import Session, adapters
from urllib3.util.retry import Retry
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.buguyy.top"
        self.search_api = "https://www.buguyy.top/api/search"
        self.kuwo_play_api = "https://nmobi.kuwo.cn/mobi.s"
        self.kuwo_lrc_api = "https://kuwo.cn/openapi/v1/www/lyric/getlyric"
        self.session = Session()
        adapter = adapters.HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]),
            pool_connections=20, pool_maxsize=50
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "application/json, text/plain, */*",
        }
        self.session.headers.update(self.headers)
        self.kuwo_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
            "Referer": "https://www.kuwo.cn/"
        }
        self.categories = [
            ("最新歌曲", "new"),
            ("人气歌曲", "hot"),
            ("精选歌曲", "random"),
            ("热门歌手", "singer"),
            ("★合集·音乐串烧", "串烧"),
            ("★合集·音乐合集", "合集"),
            ("DJ舞曲", "DJ"),
            ("抖音热门", "抖音"),
            ("经典老歌", "经典"),
            ("情歌对唱", "情歌"),
        ]
        self._page_categories = {"new", "hot", "random"}
        self._search_categories = {"串烧", "合集", "DJ", "抖音", "经典", "情歌"}
        self._singer_list = [
            "周杰伦", "林俊杰", "邓紫棋", "陈奕迅", "薛之谦", "许嵩",
            "张杰", "刘德华", "张学友", "王菲", "周深", "五月天",
            "邓丽君", "李荣浩", "毛不易"
        ]
        self.quality_list = [
            ("超清320K", 320, "mp3"),
            ("高清192K", 192, "mp3"),
            ("标准128K", 128, "mp3"),
        ]

    def getName(self):
        return "布谷音乐"

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(mp3|m4a|flac|wav|aac|wma)(\?|$)', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.session.close()

    def homeContent(self, filter):
        classes = [{"type_name": name, "type_id": tid} for name, tid in self.categories]
        return {"class": classes, "filters": {}, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def _parse_items(self, items, category=""):
        vod_list = []
        for item in items:
            b64_id = item.get("id", "")
            title = item.get("title", "")
            singer = item.get("singer", "")
            picurl = item.get("picurl", "")
            about = item.get("about", "")
            if not b64_id or not title:
                continue
            try:
                rid = b64decode(b64_id).decode("utf-8")
            except:
                rid = b64_id
            lrc = ""
            if about:
                lrc = self._parse_lrc_from_about(about)
            name = title
            if singer:
                name = title + " - " + singer
            info = {
                "rid": rid,
                "title": title,
                "singer": singer,
                "pic": picurl,
                "lrc": lrc,
                "category": category
            }
            vod_id = "bg_" + self.e64(json.dumps(info, ensure_ascii=False))
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": picurl,
                "vod_remarks": singer
            })
            if len(vod_list) >= 50:
                break
        return vod_list

    def _parse_nuxt_page(self, path):
        try:
            if path == "new":
                url = self.host + "/"
            else:
                url = self.host + "/" + path
            r = self.session.get(url, timeout=15)
            text = r.text
            m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
            if not m:
                return []
            data_str = m.group(1).strip()
            data = json.loads(data_str)
            def resolve(index):
                if not isinstance(index, int):
                    return index
                val = data[index]
                if isinstance(val, list) and len(val) >= 2:
                    if val[0] in ('ShallowReactive', 'Ref'):
                        return resolve(val[1])
                    return [resolve(x) for x in val]
                elif isinstance(val, dict):
                    return {k: resolve(v) for k, v in val.items()}
                else:
                    return val
            root = resolve(1)
            data_obj = root.get('data', {})
            for key in data_obj:
                val = data_obj[key]
                if isinstance(val, dict) and 'data' in val:
                    return val.get('data', [])
            return []
        except Exception as e:
            print("_parse_nuxt_page error:", e)
            return []

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        try:
            if tid == "singer":
                vod_list = []
                for singer_name in self._singer_list:
                    vod_list.append({
                        "vod_id": "singer_" + singer_name,
                        "vod_name": singer_name,
                        "vod_pic": "https://img2.kuwo.cn/star/singerheads/100/100/singer_default.png",
                        "vod_remarks": "歌手"
                    })
                return {
                    "list": vod_list,
                    "page": pg,
                    "pagecount": 1,
                    "limit": 50,
                    "total": len(vod_list)
                }
            elif tid in self._page_categories:
                items = self._parse_nuxt_page(tid)
                vod_list = self._parse_items(items, tid)
            elif tid in self._search_categories:
                params = {"keyword": tid}
                r = self.session.get(self.search_api, params=params, timeout=15)
                data = r.json()
                vod_list = []
                if data.get("success") and data.get("data"):
                    vod_list = self._parse_items(data["data"], tid)
            else:
                params = {"keyword": tid}
                r = self.session.get(self.search_api, params=params, timeout=15)
                data = r.json()
                vod_list = []
                if data.get("success") and data.get("data"):
                    vod_list = self._parse_items(data["data"], tid)
            pagecount = 1
            total = len(vod_list)
            return {
                "list": vod_list,
                "page": pg,
                "pagecount": pagecount,
                "limit": 50,
                "total": total
            }
        except Exception as e:
            print("categoryContent error:", e)
            return {"list": [], "page": pg, "pagecount": 0, "limit": 50, "total": 0}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        try:
            params = {"keyword": key}
            r = self.session.get(self.search_api, params=params, timeout=15)
            data = r.json()
            vod_list = []
            if data.get("success") and data.get("data"):
                vod_list = self._parse_items(data["data"])
            return {"list": vod_list, "page": pg}
        except Exception as e:
            print("searchContent error:", e)
            return {"list": [], "page": pg}

    def _decode_vod_id(self, vod_id):
        try:
            if vod_id.startswith("bg_"):
                encoded = vod_id[3:]
                info_str = self.d64(encoded)
                info = json.loads(info_str)
                return info
        except Exception as e:
            print("_decode_vod_id error:", e)
        m = re.search(r'(\d{5,})', str(vod_id))
        if m:
            return {"rid": m.group(1), "title": "", "singer": "", "pic": "", "lrc": ""}
        return {"rid": str(vod_id), "title": "", "singer": "", "pic": "", "lrc": ""}

    def _get_songs_by_keyword(self, keyword):
        try:
            params = {"keyword": keyword}
            r = self.session.get(self.search_api, params=params, timeout=15)
            data = r.json()
            songs = []
            if data.get("success") and data.get("data"):
                for item in data["data"]:
                    b64_id = item.get("id", "")
                    title = item.get("title", "")
                    singer = item.get("singer", "")
                    picurl = item.get("picurl", "")
                    if not b64_id or not title:
                        continue
                    try:
                        rid = b64decode(b64_id).decode("utf-8")
                    except:
                        rid = b64_id
                    songs.append({
                        "rid": rid,
                        "title": title,
                        "singer": singer,
                        "pic": picurl
                    })
            return songs
        except Exception as e:
            print("_get_songs_by_keyword error:", e)
            return []
    
    def _get_songs_by_category(self, category):
        if category in self._page_categories:
            items = self._parse_nuxt_page(category)
            songs = []
            for item in items:
                b64_id = item.get("id", "")
                title = item.get("title", "")
                singer = item.get("singer", "")
                picurl = item.get("picurl", "")
                if not b64_id or not title:
                    continue
                try:
                    rid = b64decode(b64_id).decode("utf-8")
                except:
                    rid = b64_id
                songs.append({
                    "rid": rid,
                    "title": title,
                    "singer": singer,
                    "pic": picurl
                })
            return songs
        return self._get_songs_by_keyword(category)

    def detailContent(self, ids):
        vod_id = ids[0]
        try:
            if vod_id.startswith("singer_"):
                singer_name = vod_id[7:]
                songs = self._get_songs_by_keyword(singer_name)
                if not songs:
                    return {"list": []}
                
                play_arr = []
                for song in songs:
                    display_name = song["title"] + " - " + song["singer"] if song["singer"] else song["title"]
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    title_clean = re.sub(r'[$#&]', '', song["title"]).strip()
                    singer_clean = re.sub(r'[$#&]', '', song["singer"]).strip() if song["singer"] else ''
                    play_arr.append(display_name + "$" + title_clean + "&&" + singer_clean + "&&" + song["rid"])
                
                song_list_str = '#'.join(play_arr)
                qualities = [q[0] for q in self.quality_list]
                vod_play_from = '$$$'.join(qualities)
                vod_play_url = '$$$'.join([song_list_str for _ in qualities])
                
                singer_pic = songs[0].get("pic", "") if songs else ""
                if not singer_pic and songs:
                    singer_pic = self._get_cover(songs[0].get("title", ""), singer_name, songs[0].get("rid", ""))
                vod = {
                    "vod_id": vod_id,
                    "vod_name": singer_name,
                    "vod_pic": singer_pic,
                    "vod_play_from": vod_play_from,
                    "vod_play_url": vod_play_url,
                    "vod_content": "",
                    "vod_remarks": "歌曲 : " + str(len(songs)) + "首"
                }
                return {"list": [vod]}
            
            info = self._decode_vod_id(vod_id)
            rid = info.get("rid", "")
            title = info.get("title", "")
            singer = info.get("singer", "")
            pic = info.get("pic", "")
            lrc = info.get("lrc", "")
            category = info.get("category", "")
            
            if not self._is_valid_lrc(lrc):
                better_lrc = self._get_lyric(rid, title, singer)
                if better_lrc and self._is_valid_lrc(better_lrc):
                    lrc = better_lrc
            
            if not pic:
                cover = self._get_cover(title, singer, rid)
                if cover:
                    pic = cover
            
            if category:
                songs = self._get_songs_by_category(category)
            else:
                songs = self._get_songs_by_keyword(singer or title)
            
            if not songs:
                songs = [{"rid": rid, "title": title, "singer": singer, "pic": pic}]
            
            play_arr = []
            for song in songs:
                display_name = song["title"] + " - " + song["singer"] if song["singer"] else song["title"]
                display_name = re.sub(r'[$#]', '', display_name).strip()
                title_clean = re.sub(r'[$#&]', '', song["title"]).strip()
                singer_clean = re.sub(r'[$#&]', '', song["singer"]).strip() if song["singer"] else ''
                play_arr.append(display_name + "$" + title_clean + "&&" + singer_clean + "&&" + song["rid"])
            
            song_list_str = '#'.join(play_arr)
            qualities = [q[0] for q in self.quality_list]
            vod_play_from = '$$$'.join(qualities)
            vod_play_url = '$$$'.join([song_list_str for _ in qualities])
            
            full_name = title or "未知歌曲"
            if singer:
                full_name = full_name + " - " + singer
            vod = {
                "vod_id": vod_id,
                "vod_name": full_name,
                "vod_pic": pic or "",
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
                "vod_content": lrc or "",
                "vod_remarks": singer or ""
            }
            return {"list": [vod]}
        except Exception as e:
            print("detailContent error:", e)
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "url": "",
            "header": self.kuwo_headers
        }
        try:
            raw_id = str(id)
            
            if raw_id.startswith("http"):
                result["url"] = raw_id
                return result
            
            title_hint = ''
            singer_hint = ''
            rid = raw_id
            
            if '$' in raw_id:
                parts = raw_id.split('$')
                if len(parts) >= 2:
                    name_part = parts[0]
                    if ' - ' in name_part:
                        np = name_part.split(' - ', 1)
                        title_hint = np[0].strip()
                        singer_hint = np[1].strip()
                    else:
                        title_hint = name_part.strip()
                for part in reversed(parts):
                    if part.startswith('http'):
                        result["url"] = part
                        return result
                if len(parts) > 1:
                    rid = parts[-1]
            
            if '&&' in rid:
                parts = rid.split('&&')
                if len(parts) >= 3:
                    title_hint = parts[0].strip()
                    singer_hint = parts[1].strip()
                    rid = parts[2].strip()
                elif len(parts) == 2:
                    title_hint = parts[0].strip()
                    rid = parts[1].strip()
            
            m = re.search(r'(\d{5,})', rid)
            if m:
                rid = m.group(1)
            
            bitrate = 320
            format_type = "mp3"
            for qn, br, ft in self.quality_list:
                if qn == flag:
                    bitrate = br
                    format_type = ft
                    break
            
            url = self._get_play_url(rid, bitrate, format_type)
            if url:
                result["url"] = url
            
            lrc = self._get_lyric(rid, title_hint, singer_hint)
            if lrc:
                result["lrc"] = lrc
            if not result.get("pic"):
                cover = self._get_cover(title_hint, singer_hint, rid)
                if cover:
                    result["pic"] = cover
        except Exception as e:
            print("playerContent error:", e)
        return result

    def _get_play_url(self, rid, bitrate=320, format_type="mp3"):
        try:
            api_url = (self.kuwo_play_api + 
                "?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk" +
                "&type=convert_url_with_sign&rid=" + rid + 
                "&bitrate=" + str(bitrate) + "&format=" + format_type)
            r = self.session.get(api_url, headers=self.kuwo_headers, timeout=10)
            data = r.json()
            if data.get("code") == 200 and data.get("data") and data["data"].get("url"):
                url = data["data"]["url"]
                if url and url != "None":
                    url = url.replace("http://", "https://")
                    return url
        except Exception as e:
            print("_get_play_url error:", e)
        return ""

    def _get_lyric(self, rid, title="", singer=""):
        lrc = ""
        try:
            lr = self.session.get(self.kuwo_lrc_api + "?musicId=" + rid, timeout=10)
            lj = lr.json()
            if lj.get("data") and lj["data"].get("lrclist"):
                lrclist = lj["data"]["lrclist"]
                lrc_lines = []
                for item in lrclist:
                    time_val = float(item.get("time", 0))
                    line = item.get("lineLyric", "")
                    if line:
                        lrc_lines.append("[" + self._format_time(time_val) + "]" + line)
                if lrc_lines:
                    lrc = "\n".join(lrc_lines)
        except Exception as e:
            print("_get_lyric(kuwo) error:", e)
        if not self._is_valid_lrc(lrc) and title:
            bug_lrc = self._buguyy_lyric(title, singer)
            if self._is_valid_lrc(bug_lrc):
                lrc = bug_lrc
        if not self._is_valid_lrc(lrc) and title:
            fallback = self._search_lyric_fallback(title, singer)
            if fallback:
                lrc = fallback
        return lrc

    def _buguyy_lyric(self, title, singer=""):
        lrc = ""
        try:
            params = {"keyword": title}
            r = self.session.get(self.search_api, params=params, timeout=15)
            data = r.json()
            if data.get("success") and data.get("data"):
                best = ""
                best_score = -1
                for item in data["data"]:
                    t = item.get("title", "")
                    s = item.get("singer", "")
                    about = item.get("about", "")
                    if not about:
                        continue
                    cand = self._parse_lrc_from_about(about)
                    if not self._is_valid_lrc(cand):
                        continue
                    score = 0
                    if t == title:
                        score += 10
                    elif title and title in t:
                        score += 5
                    if singer and s == singer:
                        score += 10
                    elif singer and singer and singer in s:
                        score += 3
                    if score > best_score:
                        best_score = score
                        best = cand
                lrc = best
        except Exception as e:
            print("_buguyy_lyric error:", e)
        return lrc

    def _get_cover(self, title, singer="", rid=""):
        pic = ""
        try:
            params = {"keyword": title}
            r = self.session.get(self.search_api, params=params, timeout=15)
            data = r.json()
            if data.get("success") and data.get("data"):
                best = ""
                best_score = -1
                for item in data["data"]:
                    t = item.get("title", "")
                    s = item.get("singer", "")
                    pu = item.get("picurl") or ""
                    if not pu:
                        continue
                    score = 0
                    if t == title:
                        score += 10
                    elif title and title in t:
                        score += 5
                    if singer and s == singer:
                        score += 10
                    elif singer and singer in s:
                        score += 3
                    if score > best_score:
                        best_score = score
                        best = pu
                pic = best
        except Exception as e:
            print("_get_cover(buguyy) error:", e)
        if not pic and title:
            try:
                keyword = title
                if singer:
                    keyword = title + " " + singer
                search_url = "https://music.163.com/api/search/get/web"
                data = {
                    "s": keyword,
                    "type": 1,
                    "offset": 0,
                    "limit": 5,
                    "total": "true"
                }
                headers = {
                    "Referer": "https://music.163.com/",
                    "User-Agent": "Mozilla/5.0"
                }
                r = self.session.post(search_url, data=data, headers=headers, timeout=8)
                if r.status_code == 200:
                    result = r.json()
                    songs = result.get("result", {}).get("songs", [])
                    best = ""
                    best_score = -1
                    for song in songs[:5]:
                        s_name = song.get("name", "")
                        s_artists = song.get("artists", [])
                        s_artist = s_artists[0].get("name", "") if s_artists else ""
                        s_pic = song.get("album", {}).get("picUrl") or song.get("picUrl") or ""
                        score = 0
                        if title and title in s_name:
                            score += 10
                        if singer and singer in s_artist:
                            score += 10
                        if s_name == title:
                            score += 5
                        if s_artist == singer:
                            score += 5
                        if score > best_score:
                            best_score = score
                            best = s_pic
                    pic = best
            except Exception as e:
                print("_get_cover(netease) error:", e)
        return pic

    def _search_lyric_fallback(self, title, singer=""):
        try:
            keyword = title
            if singer:
                keyword = title + " " + singer
            search_url = "https://music.163.com/api/search/get/web"
            data = {
                "s": keyword,
                "type": 1,
                "offset": 0,
                "limit": 5,
                "total": "true"
            }
            headers = {
                "Referer": "https://music.163.com/",
                "User-Agent": "Mozilla/5.0"
            }
            r = self.session.post(search_url, data=data, headers=headers, timeout=8)
            if r.status_code == 200:
                result = r.json()
                songs = result.get("result", {}).get("songs", [])
                if songs and len(songs) > 0:
                    best_id = ""
                    best_score = 0
                    for song in songs[:5]:
                        s_name = song.get("name", "")
                        s_artists = song.get("artists", [])
                        s_artist = s_artists[0].get("name", "") if s_artists else ""
                        s_id = str(song.get("id", ""))
                        score = 0
                        if title and title in s_name:
                            score += 10
                        if singer and singer in s_artist:
                            score += 10
                        if s_name == title:
                            score += 5
                        if s_artist == singer:
                            score += 5
                        if score > best_score:
                            best_score = score
                            best_id = s_id
                    if best_id:
                        lrc_url = "https://music.163.com/api/song/lyric?os=pc&id=" + best_id + "&lv=-1&kv=-1&tv=-1"
                        r2 = self.session.get(lrc_url, headers=headers, timeout=8)
                        if r2.status_code == 200:
                            lrc_data = r2.json()
                            lrc = lrc_data.get("lrc", {}).get("lyric", "")
                            if lrc and self._is_valid_lrc(lrc):
                                return lrc
        except Exception as e:
            print("_search_lyric_fallback error:", e)
        return ""

    def _parse_lrc_from_about(self, about):
        try:
            if not about:
                return ""
            text = re.sub(r'<br\s*/?>', '\n', about, flags=re.I)
            text = re.sub(r'<[^>]+>', '', text)
            text = html_mod.unescape(text)
            text = text.strip('\ufeff').strip()
            lines = text.split('\n')
            result_lines = []
            has_lrc = False
            meta_re = re.compile(r'(作词|作曲|编曲|制作人|出品|发行|监制|混音|录音|和声|弦乐|钢琴|吉他|贝斯|鼓|母带|OP|SP|所属|专辑|原唱|翻唱|编写|统筹|企划|出品人|总策划|联合|特别鸣谢|voice|vocal|guitar|drum|bass|piano|strings|mix|master|produce|arrange|compose|lyric|word|music by|lyric by|arranged by)', re.I)
            for line in lines:
                line = line.strip()
                if not line:
                    if result_lines and result_lines[-1] != "":
                        result_lines.append("")
                    continue
                m = re.match(r'^\[(\d+)\.(\d+)\]', line)
                if m:
                    has_lrc = True
                    seconds = int(m.group(1)) + int(m.group(2)) / (10 ** len(m.group(2)))
                    content = line[m.end():].strip()
                    if meta_re.search(content):
                        continue
                    result_lines.append("[" + self._format_time(seconds) + "]" + content)
                elif re.match(r'^\[\d{2}:\d{2}', line):
                    has_lrc = True
                    content = re.sub(r'^\[\d{2}:\d{2}(?:[\.:]\d{1,3})?\]\s*', '', line).strip()
                    if meta_re.search(content):
                        continue
                    result_lines.append(line)
                else:
                    if meta_re.search(line):
                        continue
                    result_lines.append(line)
            result = "\n".join([l for l in result_lines if l or (result_lines and l == "")])
            result = result.strip()
            return result
        except Exception as e:
            print("_parse_lrc_from_about error:", e)
            return ""

    def _is_valid_lrc(self, lrc):
        if not lrc:
            return False
        lines = [l for l in lrc.split('\n') if l.strip()]
        if len(lines) < 2:
            return False
        time_line_count = sum(1 for l in lines if re.match(r'^\[\d{2}:\d{2}', l.strip()))
        if time_line_count >= 2:
            return True
        if len(lines) >= 5:
            return True
        return False

    def _format_time(self, seconds):
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def e64(self, text):
        return b64encode(text.encode("utf-8")).decode("utf-8")

    def d64(self, text):
        return b64decode(text.encode("utf-8")).decode("utf-8")
