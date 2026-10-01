# -*- coding: utf-8 -*-
"""
悦听音乐网 - www.yueting.net
TVBox音乐接口
"""
import re
import json
import sys
import time
import requests
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.host = "https://www.yueting.net"
        self.api_host = "https://api.isoudy.com/api"
        self.name = "悦听音乐"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.yueting.net/',
        }
        self.wx_info = "微信公众号：源力软件汇"
        self._new_songs_cache = None
        self._new_songs_cache_time = 0

    def getName(self):
        return "悦听音乐"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "song", "type_name": "最新音乐"},
            {"type_id": "singer", "type_name": "歌手大全"},
            {"type_id": "hot", "type_name": "热门推荐"},
        ]
        filters = {
            "song": [{"key": "quality", "name": "音质", "value": [
                {"n": "标准128K", "v": "128kmp3"},
                {"n": "高清192K", "v": "192kmp3"},
                {"n": "超清320K", "v": "320kmp3"},
                {"n": "无损APE", "v": "2000kflac"},
            ]}],
            "singer": [{"key": "quality", "name": "音质", "value": [
                {"n": "标准128K", "v": "128kmp3"},
                {"n": "高清192K", "v": "192kmp3"},
                {"n": "超清320K", "v": "320kmp3"},
                {"n": "无损APE", "v": "2000kflac"},
            ]}],
            "hot": [{"key": "quality", "name": "音质", "value": [
                {"n": "标准128K", "v": "128kmp3"},
                {"n": "高清192K", "v": "192kmp3"},
                {"n": "超清320K", "v": "320kmp3"},
                {"n": "无损APE", "v": "2000kflac"},
            ]}],
        }
        return {'class': classes, 'filters': filters, 'list': []}

    def homeVideoContent(self):
        try:
            videos = []
            html = self._fetch_page(f"{self.host}")
            if not html:
                return {'list': []}
            items = re.findall(r'<div[^>]*class="item[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"', html, re.DOTALL)
            for img_src, href, title in items[:30]:
                if '/song/' in href:
                    m = re.search(r'/song/(\d+)\.html', href)
                    if m:
                        videos.append({
                            'vod_id': f"song_{m.group(1)}",
                            'vod_name': re.sub(r'<[^>]+>', '', title).strip(),
                            'vod_pic': '',
                            'vod_remarks': f"{self.wx_info}",
                        })
                elif '/mv/' in href:
                    m = re.search(r'/mv/(\d+)\.html', href)
                    if m:
                        pic = self._normalize_img_url(img_src)
                        videos.append({
                            'vod_id': f"mv_{m.group(1)}",
                            'vod_name': re.sub(r'<[^>]+>', '', title).strip(),
                            'vod_pic': pic,
                            'vod_remarks': f"{self.wx_info}",
                        })
            return {'list': videos}
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg else 1
            if tid == 'mv':
                return self._get_mv_list(pg)
            elif tid == 'song':
                return self._get_song_list(pg)
            elif tid == 'singer':
                return self._get_singer_list(pg)
            elif tid == 'hot':
                return self._get_hot_list(pg)
            elif tid.startswith('singer_detail_'):
                singer_id = tid.replace('singer_detail_', '')
                return self._get_singer_songs(singer_id, pg)
            elif tid.startswith('playlist_'):
                pid = tid.replace('playlist_', '')
                return self._get_playlist_songs(pid, pg)
            else:
                return self._get_song_list(pg)
        except Exception as e:
            print(f"categoryContent error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}

    def detailContent(self, ids):
        try:
            vid = ids[0].strip() if ids else ''
            if vid.startswith('song_'):
                return self._get_song_detail(vid)
            elif vid.startswith('mv_'):
                return self._get_mv_detail(vid)
            elif vid.startswith('singer_detail_'):
                singer_id = vid.replace('singer_detail_', '')
                return self._get_singer_detail(singer_id)
            else:
                return {'list': []}
        except Exception as e:
            print(f"detailContent error: {e}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            raw_id = str(id)
            if raw_id.startswith('http'):
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = raw_id
                result["header"] = self.headers
                return result

            rid = raw_id
            if '$' in rid:
                parts = rid.split('$')
                for part in reversed(parts):
                    if part.isdigit() or part.startswith('mv_') or part.startswith('song_'):
                        rid = part
                        break

            if rid.startswith('song_'):
                rid = rid.replace('song_', '')
            if rid.startswith('mv_'):
                mv_id = rid.replace('mv_', '')
                return self._get_mv_player(mv_id)

            if not rid.isdigit():
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                return result

            quality_map = {
                '标准128K': '128kmp3',
                '高清192K': '192kmp3',
                '超清320K': '320kmp3',
                '无损APE': '2000kflac',
            }

            if flag and flag in quality_map:
                play_url = self._get_song_url(rid, quality_map[flag])
            else:
                play_url = self._get_song_url(rid, '320kmp3')

            if not play_url:
                play_url = f"{self.host}/server/1/{rid}.mp3"

            lrc = self._get_lyric(rid)
            subs = []
            if lrc:
                try:
                    import base64
                    ssa_lrc = self._create_ssa_subtitle(lrc)
                    ssa_base64 = base64.b64encode(ssa_lrc.encode('utf-8')).decode('utf-8')
                    ssa_url = f"data:text/x-ssa;base64,{ssa_base64}"
                    subs = [{
                        "name": "歌词",
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
                "Referer": "https://www.yueting.net/"
            }
            if subs:
                result["subs"] = subs

        except Exception as e:
            print(f"playerContent error: {e}")
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}

        return result

    def searchContent(self, key, quick, pg="1"):
        return self._search(key, pg)

    def searchContentPage(self, key, quick, pg):
        return self._search(key, pg)

    def _fetch_page(self, url, retries=2):
        session = requests.Session()
        session.headers.update(self.headers)
        for attempt in range(retries + 1):
            try:
                resp = session.get(url, timeout=15)
                resp.encoding = 'utf-8'
                if resp.status_code == 200:
                    return resp.text
                if attempt < retries:
                    time.sleep(1)
            except Exception as e:
                if attempt < retries:
                    time.sleep(1)
                else:
                    print(f"请求失败: {url}, 错误: {e}")
        return ''

    def _normalize_img_url(self, img_url):
        if not img_url:
            return ''
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        img_url = re.sub(r'\?imageView2.*$', '', img_url)
        return img_url.strip()

    def _unescape_html(self, text):
        if not text:
            return text
        from html import unescape
        return unescape(text)

    def _get_mv_list(self, pg):
        try:
            url = f"{self.host}/mv/page/{pg}" if pg > 1 else f"{self.host}/mv"
            html = self._fetch_page(url)
            if not html:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}
            videos = []
            seen = set()
            pattern = r'<div[^>]*class="item[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>.*?<h4[^>]*class="entry-title"[^>]*><a[^>]*href="[^"]*/mv/(\d+)\.html"[^>]*>([^<]*)</a>'
            items = re.findall(pattern, html, re.DOTALL)
            for img_src, mv_id, title in items:
                if mv_id not in seen:
                    seen.add(mv_id)
                    pic = self._normalize_img_url(img_src)
                    videos.append({
                        'vod_id': f"mv_{mv_id}",
                        'vod_name': re.sub(r'&amp;', '&', title).strip(),
                        'vod_pic': pic,
                        'vod_remarks': f"{self.wx_info}",
                    })
            has_next = 'class="btn btn-small next"' in html
            pagecount = pg + 1 if has_next else pg
            return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 30, 'total': pagecount * 30}
        except Exception as e:
            print(f"_get_mv_list error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}

    def _get_song_list(self, pg):
        try:
            url = f"{self.host}/song/page/{pg}" if pg > 1 else f"{self.host}/song"
            html = self._fetch_page(url)
            if not html:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 50, 'total': 0}
            videos = []
            seen = set()
            pattern = r'<h4[^>]*class="entry-title"[^>]*><a[^>]*href="[^"]*?/song/(\d+)\.html"[^>]*title="([^"]*)"'
            items = re.findall(pattern, html)
            for rid, title in items:
                if rid not in seen:
                    seen.add(rid)
                    title_clean = re.sub(r'&amp;', '&', title).strip()
                    title_clean = re.sub(r'在线试听音乐\s*', '', title_clean)
                    videos.append({
                        'vod_id': f"song_{rid}",
                        'vod_name': title_clean,
                        'vod_pic': '',
                        'vod_remarks': f"{self.wx_info}",
                    })
            has_next = 'class="btn btn-small next"' in html
            pagecount = pg + 1 if has_next else pg
            return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 50, 'total': pagecount * 50}
        except Exception as e:
            print(f"_get_song_list error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 50, 'total': 0}

    def _get_singer_list(self, pg):
        try:
            url = f"{self.host}/singer/page/{pg}" if pg > 1 else f"{self.host}/singer"
            html = self._fetch_page(url)
            if not html:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}
            videos = []
            pattern = r'<div[^>]*class="item[^"]*"[^>]*>.*?<a[^>]*class="clip-link"[^>]*href="([^"]*)"[^>]*>.*?</a>.*?<div[^>]*class="data"[^>]*>.*?<h2[^>]*class="entry-title"[^>]*><a[^>]*>([^<]*)</a>'
            items = re.findall(pattern, html, re.DOTALL)
            for href, name in items:
                m = re.search(r'/singer/(\d+)\.html', href)
                if m:
                    sid = m.group(1)
                    videos.append({
                        'vod_id': f"singer_detail_{sid}",
                        'vod_name': name.strip(),
                        'vod_pic': '',
                        'vod_remarks': f"{self.wx_info}",
                    })
            has_next = 'class="btn btn-small next"' in html
            pagecount = pg + 1 if has_next else pg
            return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 30, 'total': pagecount * 30}
        except Exception as e:
            print(f"_get_singer_list error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}

    def _get_hot_list(self, pg):
        try:
            url = f"{self.host}/song/page/{pg}" if pg > 1 else f"{self.host}/song"
            html = self._fetch_page(url)
            if not html:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}
            videos = []
            pattern = r'<div[^>]*class="item[^"]*"[^>]*>.*?<h4[^>]*class="entry-title"[^>]*><a[^>]*href="([^"]*)"[^>]*title="([^"]*)"'
            items = re.findall(pattern, html, re.DOTALL)
            for href, title in items:
                m = re.search(r'/song/(\d+)\.html', href)
                if m:
                    rid = m.group(1)
                    title_clean = re.sub(r'<[^>]+>', '', title).strip()
                    title_clean = re.sub(r'\s+', ' ', title_clean)
                    if '播放按钮' not in title_clean:
                        videos.append({
                            'vod_id': f"song_{rid}",
                            'vod_name': title_clean,
                            'vod_pic': '',
                            'vod_remarks': f"{self.wx_info}",
                        })
            has_next = 'class="btn btn-small next"' in html
            pagecount = pg + 1 if has_next else pg
            return {'list': videos, 'page': pg, 'pagecount': pagecount, 'limit': 50, 'total': pagecount * 50}
        except Exception as e:
            print(f"_get_hot_list error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 50, 'total': 0}

    def _get_singer_songs(self, singer_id, pg):
        try:
            url = f"{self.host}/singer/{singer_id}.html"
            html = self._fetch_page(url)
            if not html:
                return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 100, 'total': 0}
            singer_name_match = re.search(r'<h2[^>]*class="entry-title"[^>]*><a[^>]*>([^<]*)</a>', html)
            singer_name = singer_name_match.group(1).strip() if singer_name_match else "歌手"
            videos = []
            seen = set()
            pattern = r'<a[^>]*href="[^"]*?/song/(\d+)\.html"[^>]*title="([^"]*)"'
            items = re.findall(pattern, html)
            for rid, title in items:
                if rid not in seen:
                    seen.add(rid)
                    title_clean = re.sub(r'&amp;', '&', title).strip()
                    title_clean = re.sub(r'在线试听音乐\s*', '', title_clean)
                    videos.append({
                        'vod_id': f"song_{rid}",
                        'vod_name': title_clean,
                        'vod_pic': '',
                        'vod_remarks': f"{self.wx_info}",
                    })
            play_arr = []
            for v in videos:
                play_arr.append(f"{v['vod_name']}${v['vod_id'].replace('song_', '')}")
            song_list = '#'.join(play_arr)
            qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
            vod_play_from = '$$$'.join(qualities)
            vod_play_url = '$$$'.join([song_list for _ in qualities])
            vod = {
                'vod_id': f"singer_detail_{singer_id}",
                'vod_name': f"{singer_name} - 全部歌曲",
                'vod_pic': '',
                'vod_content': f"{self.wx_info}",
                'vod_remarks': f"歌曲: {len(videos)}首",
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"_get_singer_songs error: {e}")
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 100, 'total': 0}

    def _get_song_detail(self, vid):
        try:
            rid = vid.replace('song_', '')
            html = self._fetch_page(f"{self.host}/song/{rid}.html")
            if not html:
                return {'list': []}
            title_match = re.search(r'<h1[^>]*class="entry-title"[^>]*>([^<]*)</h1>', html)
            title = title_match.group(1).strip() if title_match else f"歌曲{rid}"
            title = self._unescape_html(title)
            title = re.sub(r'\s+', ' ', title)
            pic = ''
            img_match = re.search(r'<div[^>]*class="entry-content"[^>]*>.*?<img[^>]*src="([^"]+)"', html, re.DOTALL)
            if img_match:
                pic = self._normalize_img_url(img_match.group(1))
            songs = self._get_new_songs_list()
            play_arr = []
            for s in songs:
                play_arr.append(f"{s['vod_name']}${s['vod_id'].replace('song_', '')}")
            if not play_arr:
                play_arr.append(f"{title}${rid}")
            song_list = '#'.join(play_arr)
            qualities = ['标准128K', '高清192K', '超清320K', '无损APE']
            vod_play_from = '$$$'.join(qualities)
            vod_play_url = '$$$'.join([song_list for _ in qualities])
            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_content': f"{self.wx_info}",
                'vod_remarks': f"选集: {len(play_arr)}首",
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"_get_song_detail error: {e}")
            return {'list': []}

    def _get_new_songs_list(self):
        try:
            now = time.time()
            if self._new_songs_cache and (now - self._new_songs_cache_time) < 3600:
                return self._new_songs_cache
            songs = []
            seen = set()
            max_pages = 10
            max_songs = 200
            for pg in range(1, max_pages + 1):
                if len(songs) >= max_songs:
                    break
                url = f"{self.host}/song/page/{pg}" if pg > 1 else f"{self.host}/song"
                html = self._fetch_page(url)
                if not html:
                    break
                pattern = r'<h4[^>]*class="entry-title"[^>]*><a[^>]*href="[^"]*?/song/(\d+)\.html"[^>]*title="([^"]*)"'
                items = re.findall(pattern, html)
                if not items:
                    break
                for sid, stitle in items:
                    if sid not in seen:
                        seen.add(sid)
                        title_clean = re.sub(r'&amp;', '&', stitle).strip()
                        title_clean = re.sub(r'在线试听音乐\s*', '', title_clean)
                        songs.append({
                            'vod_id': f"song_{sid}",
                            'vod_name': title_clean,
                            'vod_pic': '',
                            'vod_remarks': f"{self.wx_info}",
                        })
                        if len(songs) >= max_songs:
                            break
                has_next = 'class="btn btn-small next"' in html
                if not has_next:
                    break
            self._new_songs_cache = songs
            self._new_songs_cache_time = now
            return songs
        except Exception as e:
            print(f"_get_new_songs_list error: {e}")
            return []

    def _get_mv_detail(self, vid):
        try:
            mv_id = vid.replace('mv_', '')
            html = self._fetch_page(f"{self.host}/mv/{mv_id}.html")
            if not html:
                return {'list': []}
            title_match = re.search(r'<h1[^>]*class="entry-title"[^>]*>([^<]*)</h1>', html)
            title = title_match.group(1).strip() if title_match else f"MV{mv_id}"
            title = self._unescape_html(title)
            title = re.sub(r'\s+', ' ', title)
            pic = ''
            img_match = re.search(r'<div[^>]*class="entry-content"[^>]*>.*?<img[^>]*src="([^"]+)"', html, re.DOTALL)
            if img_match:
                pic = self._normalize_img_url(img_match.group(1))
            if not pic:
                thumb_match = re.search(r'<div[^>]*class="thumb"[^>]*>.*?<img[^>]*src="([^"]+)"', html, re.DOTALL)
                if thumb_match:
                    pic = self._normalize_img_url(thumb_match.group(1))
            play_from = 'MV高清'
            play_url = f"{title}$mv_{mv_id}"
            vod = {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_content': f"{self.wx_info}",
                'vod_remarks': f"{self.wx_info}",
                'vod_play_from': play_from,
                'vod_play_url': play_url,
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"_get_mv_detail error: {e}")
            return {'list': []}

    def _get_singer_detail(self, singer_id):
        return self._get_singer_songs(singer_id, 1)

    def _get_song_url(self, rid, quality="320kmp3"):
        try:
            format_map = {
                "128kmp3": "mp3",
                "192kmp3": "mp3",
                "320kmp3": "mp3",
                "2000kflac": "flac",
            }
            fmt = format_map.get(quality, "mp3")
            url = f"{self.api_host}/ajax.php"
            data = {
                "mid": str(rid),
                "token": f"corp=kuwo&source=kwplayer_ar_8.5.5.0_apk_keluze.apk&p2p=1&type=convert_url2&sig=0&format={fmt}&rid={rid}",
                "hnum": "4",
            }
            resp = requests.post(url, data=data, timeout=10, headers=self.headers)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "ok" and result.get("data"):
                    music_url = result["data"].get("url", "")
                    if music_url:
                        return music_url
            return f"{self.host}/server/1/{rid}.mp3"
        except Exception:
            return f"{self.host}/server/1/{rid}.mp3"

    def _get_mv_mid_from_page(self, html):
        patterns = [
            r'getPlayUrl\((\d+)',
            r"getPlayUrl\s*\(\s*[\"']?(\d+)",
            r"playMv\s*\(\s*[\"']?(\d+)",
            r"mv\s*\(\s*[\"']?(\d+)",
            r"playVideo\s*\(\s*[\"']?(\d+)",
            r"mid\s*[=:]\s*[\"']?(\d+)",
            r"mvId\s*[=:]\s*[\"']?(\d+)",
            r"mvid\s*[=:]\s*[\"']?(\d+)",
            r"mv_id\s*[=:]\s*[\"']?(\d+)",
            r"rid\s*[=:]\s*[\"']?(\d+)",
            r"musicId\s*[=:]\s*[\"']?(\d+)",
            r"musicRid\s*[=:]\s*[\"']?(\d+)",
            r"songId\s*[=:]\s*[\"']?(\d+)",
            r"audioId\s*[=:]\s*[\"']?(\d+)",
            r'"id"\s*:\s*["\']?(\d+)',
            r"'id'\s*:\s*[\"']?(\d+)",
            r"kuwoId\s*[=:]\s*[\"']?(\d+)",
            r"kwId\s*[=:]\s*[\"']?(\d+)",
        ]
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.DOTALL | re.I)
        all_script = '\n'.join(scripts)

        for pat in patterns:
            m = re.search(pat, all_script, re.I)
            if m:
                return m.group(1)

        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1)

        return None

    def _extract_mv_urls_from_page(self, html):
        urls = []
        seen = set()

        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.DOTALL | re.I)
        all_script = '\n'.join(scripts)

        kuwo_cdn_patterns = [
            r'["\'](https?://[^"\']*sycdn\.kuwo\.cn[^"\']*\.mp4[^"\']*)["\']',
            r'["\'](https?://[^"\']*kuwo\.cn[^"\']*\.mp4[^"\']*)["\']',
            r'["\'](/[^"\']*\.mp4[^"\']*)["\']',
        ]
        for pat in kuwo_cdn_patterns:
            matches = re.findall(pat, all_script, re.I)
            for url in matches:
                if url and url not in seen and '.mp4' in url:
                    seen.add(url)
                    full_url = url if url.startswith('http') else (
                        'https:' + url if url.startswith('//') else self.host + url
                    )
                    urls.append(("高清", full_url))
            if urls:
                break

        if not urls:
            for pat in kuwo_cdn_patterns:
                matches = re.findall(pat, html, re.I)
                for url in matches:
                    if url and url not in seen and '.mp4' in url:
                        seen.add(url)
                        full_url = url if url.startswith('http') else (
                            'https:' + url if url.startswith('//') else self.host + url
                        )
                        urls.append(("高清", full_url))
                if urls:
                    break

        if not urls:
            dplayer_match = re.search(r'quality\s*:\s*(\[.*?\])', all_script, re.DOTALL)
            if not dplayer_match:
                dplayer_match = re.search(r'quality\s*:\s*(\[.*?\])', html, re.DOTALL)
            if dplayer_match:
                quality_str = dplayer_match.group(1)
                pat1 = r"\{[^}]*name\s*:\s*['\"]([^'\"]+)['\"][^}]*url\s*:\s*['\"]([^'\"]+)['\"]"
                quality_items = re.findall(pat1, quality_str, re.DOTALL)
                if not quality_items:
                    pat2 = r"\{[^}]*url\s*:\s*['\"]([^'\"]+)['\"][^}]*name\s*:\s*['\"]([^'\"]+)['\"]"
                    quality_items = re.findall(pat2, quality_str, re.DOTALL)
                    quality_items = [(n, u) for u, n in quality_items]
                for name, url in quality_items:
                    if url not in seen:
                        seen.add(url)
                        full_url = url if url.startswith('http') else (
                            'https:' + url if url.startswith('//') else self.host + url
                        )
                        urls.append((name, full_url))

        if not urls:
            video_patterns = [
                r'<video[^>]*src=["\']([^"\']+)["\']',
                r'<source[^>]*src=["\']([^"\']+)["\']',
                r'video\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                r'url\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                r'src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
            ]
            for pat in video_patterns:
                matches = re.findall(pat, html, re.I)
                for match in matches:
                    url = match if isinstance(match, str) else match[0]
                    if url and url not in seen and re.search(r'\.(mp4|m3u8|flv)(\?|$)', url, re.I):
                        seen.add(url)
                        full_url = url if url.startswith('http') else (
                            'https:' + url if url.startswith('//') else self.host + url
                        )
                        urls.append(("高清", full_url))
                if urls:
                    break

        if not urls:
            player_patterns = [
                r'player\s*=\s*\{.*?url\s*:\s*["\']([^"\']+)["\']',
                r'aplayer\s*=\s*\{.*?url\s*:\s*["\']([^"\']+)["\']',
                r'dplayer\s*=\s*\{.*?url\s*:\s*["\']([^"\']+)["\']',
                r'music\s*=\s*\{.*?url\s*:\s*["\']([^"\']+)["\']',
                r'audio\s*:\s*["\']([^"\']+)["\']',
            ]
            for pat in player_patterns:
                m = re.search(pat, all_script, re.DOTALL | re.I)
                if not m:
                    m = re.search(pat, html, re.DOTALL | re.I)
                if m:
                    url = m.group(1)
                    if url and url not in seen:
                        seen.add(url)
                        full_url = url if url.startswith('http') else (
                            'https:' + url if url.startswith('//') else self.host + url
                        )
                        urls.append(("高清", full_url))
                        break

        return urls

    def _get_mv_video_url_kuwo(self, mid):
        try:
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; MI 9 Build/QKQ1.190825.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://m.kuwo.cn/',
            }
            web_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://www.kuwo.cn/',
            }
            api_urls = [
                f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={mid}&bitrate=1080&format=mp4",
                f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={mid}&bitrate=720&format=mp4",
                f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={mid}&bitrate=480&format=mp4",
            ]
            for api_url in api_urls:
                try:
                    resp = requests.get(api_url, headers=mobile_headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        url = None
                        if data.get('code') == 200 or data.get('data'):
                            url = data.get('data', {}).get('url', '')
                        if not url and 'url' in data:
                            url = data.get('url')
                        if url and 'mp4' in url:
                            return url
                except Exception:
                    continue

            www_api_urls = [
                f"https://www.kuwo.cn/api/v1/www/music/playUrl?mid={mid}&type=mp4&httpsStatus=1&reqId=cid",
                f"https://www.kuwo.cn/api/v1/www/music/playUrl?mid={mid}&type=convert_url3&br=1080mp4&httpsStatus=1&reqId=cid",
                f"https://www.kuwo.cn/api/v1/www/music/playUrl?mid={mid}&type=convert_url3&br=720mp4&httpsStatus=1&reqId=cid",
            ]
            for api_url in www_api_urls:
                try:
                    resp = requests.get(api_url, headers=web_headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('code') == 200 and data.get('data'):
                            url = data.get('data', {}).get('url', '')
                            if url and 'mp4' in url:
                                return url
                except Exception:
                    continue

            convert_api_urls = [
                f"http://www.kuwo.cn/url?format=mp4&rid={mid}&response=url&type=convert_url3&br=1080",
                f"https://www.kuwo.cn/url?format=mp4&rid={mid}&response=url&type=convert_url3&br=720",
            ]
            for api_url in convert_api_urls:
                try:
                    resp = requests.get(api_url, headers=web_headers, timeout=10)
                    if resp.status_code == 200:
                        text = resp.text.strip()
                        if text and text.startswith('http') and 'mp4' in text:
                            return text
                        try:
                            data = resp.json()
                            url = data.get('url') or data.get('data', {}).get('url')
                            if url and 'mp4' in url:
                                return url
                        except Exception:
                            pass
                except Exception:
                    continue

            api_urls2 = [
                "http://antiserver.kuwo.cn/anti.s",
                "https://antiserver.kuwo.cn/anti.s",
            ]
            for api_url in api_urls2:
                try:
                    resp = requests.get(
                        api_url,
                        params={
                            "type": "convert_url3",
                            "rid": mid,
                            "format": "mp4",
                            "response": "url",
                            "br": "1080",
                        },
                        headers=self.headers,
                        timeout=8
                    )
                    if resp.status_code == 200:
                        text = resp.text.strip()
                        if text and text.startswith('http') and 'mp4' in text:
                            return text
                        try:
                            result = resp.json()
                            if result.get("code") == 200 and result.get("url"):
                                return result["url"]
                        except Exception:
                            pass
                except Exception:
                    continue
            return None
        except Exception as e:
            print(f"_get_mv_video_url_kuwo error: {e}")
            return None

    def _get_mv_video_url_local(self, mid):
        try:
            url = f"{self.api_host}/ajax.php"
            formats = [
                ("mp4-1080", f"corp=kuwo&source=kwplayer_ar_8.5.5.0_apk_keluze.apk&p2p=1&type=convert_url2&sig=0&format=mp4&br=1080&rid={mid}"),
                ("mp4-720", f"corp=kuwo&source=kwplayer_ar_8.5.5.0_apk_keluze.apk&p2p=1&type=convert_url2&sig=0&format=mp4&br=720&rid={mid}"),
                ("mp4", f"corp=kuwo&source=kwplayer_ar_8.5.5.0_apk_keluze.apk&p2p=1&type=convert_url2&sig=0&format=mp4&rid={mid}"),
            ]
            for fmt_name, token in formats:
                data = {
                    "mid": str(mid),
                    "token": token,
                    "hnum": "4",
                }
                try:
                    resp = requests.post(url, data=data, timeout=10, headers=self.headers)
                    if resp.status_code == 200:
                        result = resp.json()
                        if result.get("status") == "ok" and result.get("data"):
                            video_url = result["data"].get("url", "")
                            if video_url and ('mp4' in video_url or 'm3u8' in video_url):
                                return video_url
                except Exception:
                    continue
            return None
        except Exception as e:
            print(f"_get_mv_video_url_local error: {e}")
            return None

    def _get_song_rid_from_mv_page(self, html):
        patterns = [
            r'/song/(\d+)\.html',
            r'"songId"\s*:\s*["\']?(\d+)',
            r"'songId'\s*:\s*[\"']?(\d+)",
            r'"rid"\s*:\s*["\']?(\d+)',
            r"'rid'\s*:\s*[\"']?(\d+)",
            r'"musicRid"\s*:\s*["\']?(\d+)',
            r"playMusic\s*\(\s*[\"']?(\d+)",
            r"playSong\s*\(\s*[\"']?(\d+)",
            r"audioId\s*[=:]\s*[\"']?(\d+)",
        ]
        for pat in patterns:
            matches = re.findall(pat, html, re.I)
            for match in matches:
                if match and len(match) >= 5:
                    return match
        return None

    def _get_mv_player(self, mv_id):
        result = {}
        try:
            mv_page_url = f"{self.host}/mv/{mv_id}.html"
            html = self._fetch_page(mv_page_url)
            if not html:
                result["parse"] = 1
                result["playUrl"] = mv_page_url
                result["url"] = mv_page_url
                result["header"] = self.headers
                return result

            mv_urls = self._extract_mv_urls_from_page(html)
            if mv_urls:
                video_url = mv_urls[0][1]
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = video_url
                result["header"] = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Referer": mv_page_url,
                    "Origin": "https://www.yueting.net",
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                }
                return result

            song_rid = self._get_song_rid_from_mv_page(html)
            if song_rid:
                video_url = self._get_mv_video_url_local(song_rid)
                if video_url:
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        "Referer": "https://www.kuwo.cn/",
                        "Origin": "https://www.kuwo.cn",
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                    }
                    return result

                video_url = self._get_mv_video_url_kuwo(song_rid)
                if video_url:
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = {
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 9 Build/QKQ1.190825.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
                        "Referer": "https://m.kuwo.cn/",
                        "Origin": "https://m.kuwo.cn",
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    }
                    return result

            mid = self._get_mv_mid_from_page(html)
            if mid:
                video_url = self._get_mv_video_url_local(mid)
                if video_url:
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        "Referer": "https://www.kuwo.cn/",
                        "Origin": "https://www.kuwo.cn",
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                    }
                    return result

                video_url = self._get_mv_video_url_kuwo(mid)
                if video_url:
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = {
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 9 Build/QKQ1.190825.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
                        "Referer": "https://m.kuwo.cn/",
                        "Origin": "https://m.kuwo.cn",
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    }
                    return result

            result["parse"] = 1
            result["playUrl"] = mv_page_url
            result["url"] = mv_page_url
            result["header"] = self.headers
        except Exception as e:
            print(f"_get_mv_player error: {e}")
            mv_page_url = f"{self.host}/mv/{mv_id}.html"
            result["parse"] = 1
            result["playUrl"] = mv_page_url
            result["url"] = mv_page_url
            result["header"] = self.headers
        return result

    def _get_lyric(self, rid):
        try:
            html = self._fetch_page(f"{self.host}/song/{rid}.html")
            if not html:
                return []
            pattern = r'<pre[^>]*class=["\']aplayer-lrc-content["\'][^>]*>(.*?)</pre>'
            m = re.search(pattern, html, re.DOTALL)
            if m:
                raw = m.group(1).strip()
                raw = re.sub(r'<[^>]+>', '', raw)
                from html import unescape
                raw = unescape(raw)
                lyrics = []
                for line in raw.split('\n'):
                    line = line.strip()
                    if line:
                        lyrics.append(line)
                return lyrics
            return []
        except Exception:
            return []

    def _create_ssa_subtitle(self, lyrics):
        ssa = "[Script Info]\nScriptType: v4.00+\nPlayResX: 640\nPlayResY: 360\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        time_pattern = r'\[(\d{2}):(\d{2})[\:|\.](\d{2})\](.*)'
        for line in lyrics:
            m = re.match(time_pattern, line)
            if m:
                minutes = int(m.group(1))
                seconds = int(m.group(2))
                centisec = int(m.group(3))
                text = m.group(4).strip()
                if text:
                    start_time = f"0:{minutes:02d}:{seconds:02d}.{centisec:02d}"
                    end_minutes = minutes
                    end_seconds = seconds + 5
                    if end_seconds >= 60:
                        end_minutes += 1
                        end_seconds -= 60
                    end_time = f"0:{end_minutes:02d}:{end_seconds:02d}.{centisec:02d}"
                    ssa += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
        return ssa

    def _search(self, key, pg="1"):
        try:
            pg = int(pg) if pg else 1
            videos = []
            seen = set()
            for nsid in ['4', '3']:
                url = f"{self.host}/so?q={key}&nsid={nsid}"
                html = self._fetch_page(url)
                if not html:
                    continue
                pattern = r'<div[^>]*class="item[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>.*?<a[^>]*href="[^"]*?/(song|mv)/(\d+)\.html"[^>]*title="([^"]*)"'
                items = re.findall(pattern, html, re.DOTALL)
                if items:
                    for img_src, typ, vid, title in items:
                        if vid not in seen:
                            seen.add(vid)
                            prefix = "song_" if typ == "song" else "mv_"
                            pic = self._normalize_img_url(img_src) if typ == "mv" else ''
                            videos.append({
                                'vod_id': f"{prefix}{vid}",
                                'vod_name': re.sub(r'&amp;', '&', title).strip(),
                                'vod_pic': pic,
                                'vod_remarks': f"{self.wx_info}",
                            })
                else:
                    pattern = r'<a[^>]*href="[^"]*?/(song|mv)/(\d+)\.html"[^>]*title="([^"]*)"'
                    items = re.findall(pattern, html)
                    for typ, vid, title in items:
                        if vid not in seen:
                            seen.add(vid)
                            prefix = "song_" if typ == "song" else "mv_"
                            videos.append({
                                'vod_id': f"{prefix}{vid}",
                                'vod_name': re.sub(r'&amp;', '&', title).strip(),
                                'vod_pic': '',
                                'vod_remarks': f"{self.wx_info}",
                            })
            if not videos:
                html = self._fetch_page(f"{self.host}/so?q={key}&nsid=4")
                if html:
                    pattern = r'href="[^"]*?/(song|mv)/(\d+)\.html"'
                    items = re.findall(pattern, html)
                    for typ, vid in items:
                        if vid not in seen:
                            seen.add(vid)
                            prefix = "song_" if typ == "song" else "mv_"
                            videos.append({
                                'vod_id': f"{prefix}{vid}",
                                'vod_name': f"{key} - {vid}",
                                'vod_pic': '',
                                'vod_remarks': f"{self.wx_info}",
                            })
            return {'list': videos, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(videos)}
        except Exception as e:
            print(f"_search error: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 0}
