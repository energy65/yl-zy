import re
import sys
import html
import urllib3
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote
from pyquery import PyQuery as pq
from requests import Session, adapters
from urllib3.util.retry import Retry
sys.path.append('..')
from base.spider import Spider

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://higequ.com"
        self.session = Session()
        self.session.verify = False
        adapter = adapters.HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]),
            pool_connections=20, pool_maxsize=50
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": self.host + "/"
        }
        self.session.headers.update(self.headers)
        self.categories = [
            ("飙升榜", "/biaosheng/"),
            ("新歌榜单", "/xinge/"),
            ("热歌榜单", "/rege/"),
            ("抖音音乐榜", "/dy/"),
            ("经典怀旧榜", "/jdhj/"),
            ("影视金曲榜", "/ys/"),
            ("网红新歌榜", "/wh/"),
            ("儿歌排行榜", "/erge/"),
            ("车载排行榜", "/cz/"),
            ("DJ音乐排行榜", "/dj/"),
            ("华语榜", "/huayu/"),
            ("粤语榜", "/yueyu/"),
            ("欧美榜", "/oumei/"),
            ("韩语榜", "/hanyu/"),
            ("日语榜", "/riyu/"),
            ("流行趋势榜", "/lxqs/"),
            ("极品电音榜", "/jpdy/"),
            ("跑步健身榜", "/pbjs/"),
            ("KTV点唱榜", "/ktvdc/"),
        ]
        self.default_pic = "https://higequ.com/static/images/default_cover.png"

    def getName(self):
        return "Hi歌曲音乐网"

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

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        try:
            url = f"{self.host}{tid}?p={pg}"
            r = self.session.get(url, timeout=30)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('.result-item')
            vod_list = []
            seen = set()
            for item in items.items():
                rid = item.attr('data-rid') or ''
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                title = item.find('.result-title').text().strip()
                artist = item.find('.result-artist').text().strip()
                album = item.find('.result-album').text().strip()
                if not title:
                    continue
                name = title
                if artist:
                    name = f"{title} - {artist}"
                song_vod_id = f"/player/{rid}/@{tid}"
                vod_list.append({
                    "vod_id": song_vod_id,
                    "vod_name": name,
                    "vod_pic": self.default_pic,
                    "vod_remarks": album
                })
                if len(vod_list) >= 50:
                    break
            pagecount_el = doc('#total-pages')
            pagecount = int(pagecount_el.text().strip()) if pagecount_el and pagecount_el.text().strip().isdigit() else 10
            total = pagecount * 30
            return {
                "list": vod_list,
                "page": pg,
                "pagecount": pagecount,
                "limit": 50,
                "total": total
            }
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {"list": [], "page": pg, "pagecount": 0, "limit": 50, "total": 0}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        try:
            search_url = f"{self.host}/s/{quote(key)}/?p={pg}"
            r = self.session.get(search_url, timeout=30)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('.result-item')
            vod_list = []
            seen = set()
            for item in items.items():
                rid = item.attr('data-rid') or ''
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                title = item.find('.result-title').text().strip()
                artist = item.find('.result-artist').text().strip()
                album = item.find('.result-album').text().strip()
                if not title:
                    continue
                name = title
                if artist:
                    name = f"{title} - {artist}"
                song_vod_id = f"/player/{rid}/"
                vod_list.append({
                    "vod_id": song_vod_id,
                    "vod_name": name,
                    "vod_pic": self.default_pic,
                    "vod_remarks": album
                })
                if len(vod_list) >= 50:
                    break
            return {"list": vod_list, "page": pg}
        except Exception as e:
            print(f"searchContent error: {e}")
            return {"list": [], "page": pg}

    def detailContent(self, ids):
        vod_id = ids[0]
        rid, tid = self._parse_vod_id(vod_id)
        url = self._abs(f"/player/{rid}/")
        try:
            r = self.session.get(url, timeout=30)
            r.encoding = 'utf-8'
            html_text = r.text
            doc = pq(html_text)
            title = doc('.music-title').text().strip()
            artist = doc('.music-artist').text().strip()
            pic = doc('#album-cover').attr('src') or ''
            if not title:
                title = doc('h1').text().strip() or doc('title').text().strip()
            full_title = title
            if artist:
                full_title = f"{title} - {artist}"
            if not pic:
                pic = self.default_pic
            lrc_content = self._extract_lrc(html_text)
            song_list = self._get_playlist(tid, rid)
            play_list_hi = []
            play_list_standard = []
            play_list_normal = []
            if song_list:
                for song in song_list:
                    song_rid = song.get('rid', '')
                    song_title = song.get('title', '')
                    song_artist = song.get('artist', '')
                    song_name = song_title
                    if song_artist:
                        song_name = f"{song_title} - {song_artist}"
                    song_id = f"/player/{song_rid}/"
                    encoded_id = self.e64('0@@@@' + song_id)
                    play_list_hi.append(f"{song_name}${encoded_id}")
                    play_list_standard.append(f"{song_name}${encoded_id}")
                    play_list_normal.append(f"{song_name}${encoded_id}")
            else:
                song_id = f"/player/{rid}/"
                encoded_id = self.e64('0@@@@' + song_id)
                play_list_hi.append(f"{full_title}${encoded_id}")
                play_list_standard.append(f"{full_title}${encoded_id}")
                play_list_normal.append(f"{full_title}${encoded_id}")
            vod = {
                "vod_id": vod_id,
                "vod_name": full_title,
                "vod_pic": pic,
                "vod_play_from": "高品质$$$标准音质$$$普通音质",
                "vod_play_url": "#".join(play_list_hi) + "$$$" + "#".join(play_list_standard) + "$$$" + "#".join(play_list_normal),
                "vod_content": '微信公众号"源力软件汇"\n\n' + (lrc_content or ''),
                "vod_remarks": artist
            }
            return {"list": [vod]}
        except Exception as e:
            print(f"detailContent error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        raw = self.d64(id).split("@@@@")[-1]
        url = raw
        result = {
            "parse": 0,
            "url": url,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/"
            }
        }
        rid = None
        if url.startswith('/player/'):
            m = re.match(r'/player/(\d+)', url)
            if m:
                rid = m.group(1)
        elif '/player/' in url:
            rid = self._extract_rid_from_url(url)
        elif not self.isVideoFormat(url):
            m = re.match(r'(\d+)', url)
            if m:
                rid = m.group(1)
        if rid:
            detail_url = self._abs(f"/player/{rid}/")
            try:
                r = self.session.get(detail_url, timeout=30)
                r.encoding = 'utf-8'
                mp3_url = self._extract_mp3_url(r.text)
                if mp3_url:
                    result["url"] = mp3_url
                lrc = self._extract_lrc(r.text)
                if lrc:
                    result["lrc"] = lrc
            except Exception as e:
                print(f"playerContent fetch error: {e}")
        return result

    def _parse_vod_id(self, vod_id):
        rid = ''
        tid = ''
        if '@@' in vod_id:
            parts = vod_id.split('@@')
            rid = parts[0]
            tid = parts[1] if len(parts) > 1 else ''
        elif '@' in vod_id:
            parts = vod_id.split('@')
            rid = parts[0]
            tid = parts[1] if len(parts) > 1 else ''
        else:
            rid = vod_id
        rid_match = re.search(r'/player/(\d+)', rid)
        if rid_match:
            rid = rid_match.group(1)
        return rid, tid

    def _get_playlist(self, tid, current_rid):
        if not tid:
            return []
        try:
            url = f"{self.host}{tid}"
            r = self.session.get(url, timeout=30)
            r.encoding = 'utf-8'
            doc = pq(r.text)
            items = doc('.result-item')
            song_list = []
            seen = set()
            for item in items.items():
                rid = item.attr('data-rid') or ''
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                title = item.find('.result-title').text().strip()
                artist = item.find('.result-artist').text().strip()
                if title:
                    song_list.append({
                        'rid': rid,
                        'title': title,
                        'artist': artist
                    })
            return song_list
        except Exception as e:
            print(f"_get_playlist error: {e}")
            return []

    def _extract_mp3_url(self, html_text):
        try:
            m = re.search(r'let\s+code\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', html_text)
            if m:
                encoded = m.group(1)
                decoded = b64decode(encoded).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
            m = re.search(r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)', html_text)
            if m:
                encoded = m.group(1)
                decoded = b64decode(encoded).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
            m = re.search(r'audio-element[^>]*src=["\']([^"\']+)["\']', html_text)
            if m and m.group(1).startswith('http'):
                return m.group(1)
            m = re.search(r'<audio[^>]*src=["\']([^"\']+)["\']', html_text)
            if m and m.group(1).startswith('http'):
                return m.group(1)
            m = re.search(r'"url"\s*:\s*["\']([^"\']+\.mp3[^"\']*)["\']', html_text)
            if m and m.group(1).startswith('http'):
                return m.group(1)
            m = re.search(r'(https?://[^"\'>\s]+\.(mp3|m4a|flac|wav|aac))', html_text, re.I)
            if m:
                return m.group(1)
        except Exception as e:
            print(f"_extract_mp3_url error: {e}")
        return ''

    def _extract_lrc(self, html_text):
        try:
            doc = pq(html_text)
            lines = doc('.lyric-line')
            if lines:
                lrc_parts = []
                for line in lines.items():
                    time_str = line.attr('data-time') or '0'
                    text = line.text().strip()
                    if text:
                        try:
                            seconds = float(time_str)
                            minutes = int(seconds // 60)
                            secs = int(seconds % 60)
                            ms = int((seconds - int(seconds)) * 100)
                            lrc_time = f"[{minutes:02d}:{secs:02d}.{ms:02d}]"
                            lrc_parts.append(f"{lrc_time}{text}")
                        except:
                            lrc_parts.append(text)
                if lrc_parts:
                    return '\n'.join(lrc_parts)
            m = re.search(r'let\s+lrc\s*=\s*`([^`]+)`', html_text, re.S)
            if m:
                lrc_text = m.group(1)
                lrc_lines = re.findall(r'\[(\d+:\d+\.\d+)\](.+?)(?=\[|$)', lrc_text)
                if lrc_lines:
                    lrc_parts = []
                    for time_str, text in lrc_lines:
                        text = text.strip()
                        if text:
                            lrc_parts.append(f"[{time_str}]{text}")
                    if lrc_parts:
                        return '\n'.join(lrc_parts)
            m = re.search(r'lrc_data\s*=\s*["\']([^"\']+)["\']', html_text)
            if m:
                try:
                    decoded = b64decode(m.group(1)).decode('utf-8')
                    lrc_lines = re.findall(r'\[(\d+:\d+\.\d+)\](.+?)(?=\[|$)', decoded)
                    if lrc_lines:
                        lrc_parts = []
                        for time_str, text in lrc_lines:
                            text = text.strip()
                            if text:
                                lrc_parts.append(f"[{time_str}]{text}")
                        if lrc_parts:
                            return '\n'.join(lrc_parts)
                except:
                    pass
            return ''
        except Exception as e:
            print(f"_extract_lrc error: {e}")
            return ''

    def _extract_rid_from_url(self, url):
        m = re.search(r'/player/(\d+)', url)
        if m:
            return m.group(1)
        return None

    def _abs(self, url):
        if not url:
            return ''
        if url.startswith("http"):
            return url
        return f"{self.host}{'/' if not url.startswith('/') else ''}{url}"

    def e64(self, text):
        return b64encode(text.encode("utf-8")).decode("utf-8")

    def d64(self, text):
        return b64decode(text.encode("utf-8")).decode("utf-8")
