import json
import sys
import re
import base64
import requests
sys.path.append('yl-main')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "全民K歌"

    def init(self, extend=""):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/'
        }
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://m.y.qq.com/'
        }
        self.quality_config = [
            ("标准128K", "128"),
            ("高清192K", "192"),
            ("超清320K", "320"),
            ("无损FLAC", "flac"),
        ]
        self.wx_gzh = "源力软件汇--源力影视"
        self.default_pic = "https://cdn-icons-png.flaticon.com/512/2111/2111270.png"
        self.classes = [
            {'type_id': 'bang_hot', 'type_name': 'QQ音乐热歌榜'},
            {'type_id': 'bang_new', 'type_name': 'QQ音乐新歌榜'},
            {'type_id': 'bang_classic', 'type_name': 'QQ音乐经典榜'},
            {'type_id': 'bang_douyin', 'type_name': '抖音热歌榜'},
            {'type_id': 'bang_billboard', 'type_name': 'Billboard榜'},
            {'type_id': 'pl_hot', 'type_name': '热门歌单'},
            {'type_id': 'pl_new', 'type_name': '新歌速递'},
            {'type_id': 'pl_classic', 'type_name': '经典老歌'},
            {'type_id': 'pl_dj', 'type_name': 'DJ舞曲'},
            {'type_id': 'pl_emo', 'type_name': '治愈音乐'},
            {'type_id': 'artist_hot', 'type_name': '热门歌手'},
            {'type_id': 'artist_cn', 'type_name': '华语歌手'},
            {'type_id': 'artist_us', 'type_name': '欧美歌手'},
            {'type_id': 'artist_jp', 'type_name': '日韩歌手'},
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
        vods = [
            {'vod_id': 'bang_detail_3', 'vod_name': 'QQ音乐热歌榜', 'vod_pic': '', 'vod_remarks': '排行榜', 'vod_tag': 'folder'},
            {'vod_id': 'bang_detail_2', 'vod_name': 'QQ音乐新歌榜', 'vod_pic': '', 'vod_remarks': '排行榜', 'vod_tag': 'folder'},
            {'vod_id': 'bang_detail_23', 'vod_name': 'QQ音乐经典榜', 'vod_pic': '', 'vod_remarks': '排行榜', 'vod_tag': 'folder'},
            {'vod_id': 'bang_detail_197', 'vod_name': '抖音热歌榜', 'vod_pic': '', 'vod_remarks': '排行榜', 'vod_tag': 'folder'},
            {'vod_id': 'bang_detail_4', 'vod_name': 'Billboard榜', 'vod_pic': '', 'vod_remarks': '排行榜', 'vod_tag': 'folder'},
            {'vod_id': 'pl_detail_1079396186', 'vod_name': '华语流行精选', 'vod_pic': '', 'vod_remarks': '歌单', 'vod_tag': 'folder'},
            {'vod_id': 'pl_detail_1079396204', 'vod_name': 'DJ舞曲精选', 'vod_pic': '', 'vod_remarks': '歌单', 'vod_tag': 'folder'},
            {'vod_id': 'pl_detail_1079396200', 'vod_name': '经典老歌精选', 'vod_pic': '', 'vod_remarks': '歌单', 'vod_tag': 'folder'},
            {'vod_id': 'artist_detail_6452', 'vod_name': '周杰伦', 'vod_pic': '', 'vod_remarks': '歌手', 'vod_tag': 'folder'},
            {'vod_id': 'artist_detail_6453', 'vod_name': '林俊杰', 'vod_pic': '', 'vod_remarks': '歌手', 'vod_tag': 'folder'},
        ]
        return {'list': vods, 'page': 1, 'pagecount': 1, 'limit': 30, 'total': len(vods)}

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
                return self._get_artist_list(tid, pg)
            elif tid.startswith('bang_detail_'):
                bid = tid.replace('bang_detail_', '')
                return self._get_bang_songs(bid, pg)
            elif tid.startswith('bang_'):
                bang_id_map = {
                    'bang_hot': '3',
                    'bang_new': '2',
                    'bang_classic': '23',
                    'bang_douyin': '197',
                    'bang_billboard': '4',
                }
                bid = bang_id_map.get(tid, '3')
                return self._get_bang_songs(bid, pg)
            else:
                return self._get_bang_songs('3', pg)
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
                parts = artist_id.split('_')
                if len(parts) > 1:
                    artist_id = parts[0]
                return self._get_artist_detail(artist_id)
            elif vid.startswith('pl_detail_'):
                pid = vid.replace('pl_detail_', '')
                parts = pid.split('_')
                if len(parts) > 1:
                    pid = parts[0]
                return self._get_playlist_detail(pid)
            elif vid.startswith('bang_detail_'):
                bang_id = vid.replace('bang_detail_', '')
                parts = bang_id.split('_')
                if len(parts) > 1:
                    bang_id = parts[0]
                return self._get_bang_detail(bang_id)
            elif vid.startswith('pl_'):
                return self._get_playlist_list(vid, 1)
            elif vid.startswith('artist_'):
                return self._get_artist_list(vid, 1)
            elif vid.startswith('bang_'):
                return self._get_bang_list(vid, 1)
            else:
                return self._get_song_detail(vid)
        except Exception as e:
            print("detailContent error:", e)
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
        try:
            raw_id = str(id)

            if raw_id.startswith("http"):
                result["url"] = raw_id
                result["header"] = self.mobile_headers
                return result

            songmid = raw_id
            song_name_hint = ''
            artist_hint = ''

            if '$' in songmid:
                parts = songmid.split('$')
                if len(parts) >= 2:
                    name_part = parts[0]
                    if ' - ' in name_part:
                        np = name_part.split(' - ', 1)
                        song_name_hint = np[0].strip()
                        artist_hint = np[1].strip()
                    else:
                        song_name_hint = name_part.strip()
                for part in reversed(parts):
                    if part.startswith('http'):
                        result["url"] = part
                        result["header"] = self.headers
                        return result
                else:
                    if len(parts) > 1:
                        songmid = parts[-1]

            if '&&' in songmid:
                parts = songmid.split('&&')
                if len(parts) >= 3:
                    song_name_hint = parts[0].strip()
                    artist_hint = parts[1].strip()
                    songmid = parts[2].strip()
                elif len(parts) == 2:
                    song_name_hint = parts[0].strip()
                    songmid = parts[1].strip()

            if songmid.startswith('song_'):
                songmid = songmid.replace('song_', '')

            if self.isVideoFormat(songmid):
                result["url"] = songmid
                result["header"] = self.headers
                return result

            if not song_name_hint:
                song_info = self._get_song_info(songmid)
                song_name_hint = song_info.get('name', '')
                artist_hint = song_info.get('artist', '')

            play_url = self._get_play_url(songmid, song_name_hint, artist_hint)

            if not play_url:
                play_url = self._get_play_url_fallback(songmid, song_name_hint, artist_hint)

            if not play_url:
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = ""
                result["header"] = {}
                return result

            result["url"] = play_url
            result["header"] = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.kuwo.cn/"
            }

            lrc = self._get_lyric(songmid, song_name_hint, artist_hint)
            if lrc:
                result["lrc"] = lrc

        except Exception as e:
            print("playerContent error:", e)
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

    def _default_songs(self):
        return [{
            'vod_id': 'song_001VfUt21Gu4yY',
            'vod_name': '晴天 - 周杰伦',
            'vod_pic': '',
            'vod_remarks': '全民K歌',
        }]

    def _get_playlist_list(self, tid, pg):
        pl_map = {
            'pl_hot': [
                ('华语流行精选', '1079396186'), ('治愈系轻音乐', '1079396187'),
                ('经典老歌回忆', '1079396188'), ('深夜情感电台', '1079396189'),
            ],
            'pl_new': [
                ('新歌速递', '1079396196'), ('华语新歌榜', '1079396197'),
                ('欧美新歌', '1079396198'), ('日韩新歌', '1079396199'),
            ],
            'pl_classic': [
                ('经典老歌精选', '1079396200'), ('80年代金曲', '1079396201'),
                ('90年代怀旧', '1079396202'), ('粤语经典', '1079396203'),
            ],
            'pl_dj': [
                ('DJ舞曲精选', '1079396204'), ('电音派对', '1079396205'),
                ('劲爆舞曲', '1079396206'), ('车载DJ', '1079396207'),
            ],
            'pl_emo': [
                ('治愈轻音乐', '1079396208'), ('放松冥想', '1079396209'),
                ('咖啡馆音乐', '1079396210'), ('睡前轻音乐', '1079396211'),
            ],
        }
        playlists = pl_map.get(tid, pl_map['pl_hot'])
        vods = []
        for name, pid in playlists:
            vods.append({
                'vod_id': 'pl_detail_' + pid,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '歌单',
                'vod_tag': 'folder'
            })
        return {'list': vods, 'page': pg, 'pagecount': 1, 'limit': 30, 'total': len(vods)}

    def _get_default_playlists(self, pg):
        default = [
            ("华语流行精选", "1079396186"), ("治愈系轻音乐", "1079396187"),
            ("经典老歌回忆", "1079396188"), ("深夜情感电台", "1079396189"),
            ("欧美经典金曲", "1079396190"), ("抖音热门神曲", "1079396191"),
            ("开车必听歌曲", "1079396192"), ("学习工作专注", "1079396193"),
            ("运动健身歌单", "1079396194"), ("日系清新音乐", "1079396195"),
        ]
        return {'list': [{
            'vod_id': 'pl_detail_' + pid,
            'vod_name': name,
            'vod_pic': '',
            'vod_remarks': '歌单',
            'vod_tag': 'folder'
        } for name, pid in default], 'page': pg, 'pagecount': 1, 'limit': 30, 'total': 10}

    def _get_playlist_detail(self, pid):
        play_arr = []
        play_pics = []
        vod_name = 'QQ音乐歌单'
        vod_pic = ''
        vod_content = ''

        pl_name_map = {
            '1079396186': '华语流行', '1079396187': '轻音乐', '1079396188': '经典老歌',
            '1079396189': '情感音乐', '1079396190': '欧美金曲', '1079396191': '抖音热歌',
            '1079396192': '开车音乐', '1079396193': '学习专注', '1079396194': '运动健身',
            '1079396195': '日系清新', '1079396196': '新歌速递', '1079396197': '华语新歌',
            '1079396198': '欧美新歌', '1079396199': '日韩新歌', '1079396200': '经典老歌',
            '1079396201': '80年代', '1079396202': '90年代怀旧', '1079396203': '粤语经典',
            '1079396204': 'DJ舞曲', '1079396205': '电音派对', '1079396206': '劲爆舞曲',
            '1079396207': '车载DJ', '1079396208': '治愈轻音乐', '1079396209': '放松冥想',
            '1079396210': '咖啡馆音乐', '1079396211': '睡前轻音乐',
        }

        search_keyword = pl_name_map.get(pid, '热门歌曲')

        try:
            api_url = f"https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg?type=1&json=1&utf8=1&onlysong=0&disstid={pid}&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&catZhida=0&tpl=yqq"
            res = self.fetch(api_url)
            d = res.json()

            cdlist = d.get('cdlist', [])
            if cdlist:
                info = cdlist[0]
                vod_name = info.get('dissname', 'QQ音乐歌单')
                vod_pic = info.get('logo', info.get('imgurl', ''))
                if vod_pic and '{size}' in vod_pic:
                    vod_pic = vod_pic.replace('{size}', '400')
                vod_content = info.get('desc', '')

                song_list = info.get('songlist', [])
                for it in song_list:
                    songmid = str(it.get('songmid', ''))
                    song_name = it.get('songname', '')
                    singer_name = ''
                    singer_list = it.get('singer', [])
                    if singer_list:
                        singer_name = singer_list[0].get('name', '')

                    if songmid and song_name:
                        display_name = song_name + " - " + singer_name if singer_name else song_name
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        song_name_clean = re.sub(r'[$#&]', '', song_name).strip()
                        singer_name_clean = re.sub(r'[$#&]', '', singer_name).strip() if singer_name else ''
                        play_arr.append(display_name + "$" + song_name_clean + "&&" + singer_name_clean + "&&" + songmid)

                        albumpic = it.get('album', {}).get('albumPic', '')
                        if albumpic and '{size}' in albumpic:
                            albumpic = albumpic.replace('{size}', '400')
                        play_pics.append(albumpic)
        except Exception as e:
            print("_get_playlist_detail error:", e)

        if len(play_arr) < 30:
            existing_songmids = set()
            for item in play_arr:
                parts = item.split('&&')
                if len(parts) >= 3:
                    existing_songmids.add(parts[-1])

            search_result = self._get_search_songs(search_keyword, 1)
            for item in search_result.get('list', []):
                songmid = item['vod_id'].replace('song_', '')
                if songmid not in existing_songmids:
                    display_name = item['vod_name']
                    artist_name = item.get('vod_actor', '')
                    song_name_clean = re.sub(r'[$#&]', '', display_name).strip()
                    artist_name_clean = re.sub(r'[$#&]', '', artist_name).strip() if artist_name else ''
                    play_arr.append(display_name + "$" + song_name_clean + "&&" + artist_name_clean + "&&" + songmid)
                    play_pics.append(item.get('vod_pic', ''))
                    if len(play_arr) >= 30:
                        break
            if not vod_name:
                vod_name = pl_name_map.get(pid, vod_name)

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
        play_pic_list = [p if p and p.startswith('http') else self.default_pic for p in play_pics]
        if play_pic_list:
            vod['vod_play_pic'] = '$$$'.join(['#'.join(play_pic_list) for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.0

        return {'list': [vod]}

    def _get_playlist_songs(self, pid, pg):
        vods = []
        pl_name_map = {
            '1079396186': '华语流行', '1079396187': '轻音乐', '1079396188': '经典老歌',
            '1079396189': '情感音乐', '1079396190': '欧美金曲', '1079396191': '抖音热歌',
            '1079396192': '开车音乐', '1079396193': '学习专注', '1079396194': '运动健身',
            '1079396195': '日系清新', '1079396196': '新歌速递', '1079396197': '华语新歌',
            '1079396198': '欧美新歌', '1079396199': '日韩新歌', '1079396200': '经典老歌',
            '1079396201': '80年代', '1079396202': '90年代怀旧', '1079396203': '粤语经典',
            '1079396204': 'DJ舞曲', '1079396205': '电音派对', '1079396206': '劲爆舞曲',
            '1079396207': '车载DJ', '1079396208': '治愈轻音乐', '1079396209': '放松冥想',
            '1079396210': '咖啡馆音乐', '1079396211': '睡前轻音乐',
        }
        search_keyword = pl_name_map.get(pid, '热门歌曲')

        try:
            api_url = f"https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg?type=1&json=1&utf8=1&onlysong=0&disstid={pid}&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&catZhida=0&tpl=yqq"
            res = self.fetch(api_url)
            d = res.json()

            cdlist = d.get('cdlist', [])
            if cdlist:
                info = cdlist[0]
                song_list = info.get('songlist', [])

                start_idx = (pg - 1) * 30
                end_idx = start_idx + 30
                paginated_songs = song_list[start_idx:end_idx]

                for it in paginated_songs:
                    songmid = str(it.get('songmid', ''))
                    song_name = it.get('songname', '')
                    singer_name = ''
                    singer_list = it.get('singer', [])
                    if singer_list:
                        singer_name = singer_list[0].get('name', '')

                    albumpic = it.get('album', {}).get('albumPic', '')
                    if albumpic and '{size}' in albumpic:
                        albumpic = albumpic.replace('{size}', '400')

                    if songmid and song_name:
                        display_name = song_name + " - " + singer_name if singer_name else song_name
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        vods.append({
                            'vod_name': display_name,
                            'vod_id': 'pl_detail_' + pid + '_' + songmid,
                            'vod_pic': albumpic,
                            'vod_remarks': singer_name or 'QQ音乐',
                            'vod_actor': singer_name,
                        })
        except Exception as e:
            print("_get_playlist_songs error:", e)

        if len(vods) < 30:
            search_result = self._get_search_songs(search_keyword, pg)
            existing_songmids = set()
            for v in vods:
                existing_songmids.add(v['vod_id'].replace('pl_detail_' + pid + '_', ''))

            for item in search_result.get('list', []):
                songmid = item.get('vod_id', '').replace('song_', '')
                if songmid not in existing_songmids:
                    item['vod_id'] = 'pl_detail_' + pid + '_' + songmid
                    vods.append(item)
                    if len(vods) >= 30:
                        break

        start_idx = (pg - 1) * 30
        end_idx = start_idx + 30
        paginated_vods = vods[start_idx:end_idx]

        return {'list': paginated_vods, 'page': pg, 'pagecount': max(1, (len(vods) + 29) // 30), 'limit': 30, 'total': max(len(vods), 999)}

    def _get_artist_list(self, tid, pg):
        vods = []
        
        category_map = {
            'artist_hot': 'all_all_all',
            'artist_cn': 'cn_all_all',
            'artist_us': 'us_all_all',
            'artist_jp': 'jp_all_all',
        }
        
        key = category_map.get(tid, 'all_all_all')
        
        try:
            pagesize = 30
            api_url = f"https://c.y.qq.com/v8/fcg-bin/v8.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&channel=singer&page=list&key={key}&pagesize={pagesize}&pagenum={pg}"
            res = self.fetch(api_url)
            data = res.json()
            
            list_data = data.get('data', {}).get('list', [])
            for item in list_data:
                singer_mid = str(item.get('Fsinger_mid', ''))
                singer_name = item.get('Fsinger_name', '')
                
                if singer_mid and singer_name:
                    vods.append({
                        'vod_id': 'artist_detail_' + singer_mid,
                        'vod_name': singer_name,
                        'vod_pic': '',
                        'vod_remarks': '歌手',
                        'vod_tag': 'folder'
                    })
        except Exception as e:
            print("_get_artist_list API error:", e)
        
        if not vods:
            artist_map = {
                'artist_hot': [
                    ('周杰伦', '6452'), ('林俊杰', '6453'), ('陈奕迅', '211'),
                    ('邓紫棋', '2706'), ('薛之谦', '5056'), ('毛不易', '12138267'),
                    ('李荣浩', '5745'), ('华晨宇', '6455'), ('张杰', '131'),
                    ('张碧晨', '5926'), ('汪苏泷', '335'), ('许嵩', '563'),
                    ('徐良', '162'), ('萧敬腾', '126'), ('杨宗纬', '429'),
                    ('张韶涵', '895'), ('田馥甄', '877'), ('蔡依林', '351'),
                    ('王心凌', '353'), ('张惠妹', '276'), ('孙燕姿', '64'),
                    ('梁静茹', '83'), ('张学友', '2'), ('王菲', '9715'),
                    ('五月天', '12'), ('Taylor Swift', '6456'), ('Ed Sheeran', '7525'),
                    ('Justin Bieber', '703'), ('Ariana Grande', '10526'),
                ],
                'artist_cn': [
                    ('周杰伦', '6452'), ('林俊杰', '6453'), ('陈奕迅', '211'),
                    ('张学友', '2'), ('王菲', '9715'), ('五月天', '12'),
                    ('邓紫棋', '2706'), ('薛之谦', '5056'), ('毛不易', '12138267'),
                    ('李荣浩', '5745'), ('华晨宇', '6455'), ('张杰', '131'),
                    ('许嵩', '563'), ('汪苏泷', '335'), ('徐良', '162'),
                    ('萧敬腾', '126'), ('杨宗纬', '429'), ('张韶涵', '895'),
                    ('田馥甄', '877'), ('蔡依林', '351'), ('王心凌', '353'),
                    ('张惠妹', '276'), ('孙燕姿', '64'), ('梁静茹', '83'),
                    ('张碧晨', '5926'), ('刘若英', '212'), ('周传雄', '44'),
                    ('任贤齐', '45'), ('李宗盛', '265'), ('周华健', '46'),
                ],
                'artist_us': [
                    ('Taylor Swift', '6456'), ('Ed Sheeran', '7525'), ('Justin Bieber', '703'),
                    ('Ariana Grande', '10526'), ('Bruno Mars', '479'), ('Lady Gaga', '1096'),
                    ('Billie Eilish', '116058'), ('The Weeknd', '459'), ('Dua Lipa', '19446'),
                    ('Post Malone', '23696'), ('Shawn Mendes', '1562'), ('Selena Gomez', '1319'),
                    ('Katy Perry', '305'), ('Rihanna', '426'), ('Beyoncé', '99'),
                    ('Adele', '104'), ('Sam Smith', '1965'), ('Coldplay', '170'),
                    ('Maroon 5', '155'), ('Imagine Dragons', '32174'), ('OneRepublic', '694'),
                    ('Shakira', '180'), ('Jennifer Lopez', '181'), ('Justin Timberlake', '256'),
                    ('Usher', '257'), ('Alicia Keys', '258'), ('Eminem', '259'),
                ],
                'artist_jp': [
                    ('米津玄師', '107145'), ('RADWIMPS', '23265'), ('YOASOBI', '106925'),
                    ('ONE OK ROCK', '2142'), ('imase', '107456'), ('宇多田光', '123'),
                    ('LiSA', '9511'), ('Aimer', '98916'), ('Official髭男dism', '85714'),
                    ('King Gnu', '104814'), ('Back Number', '22695'), ('あいみょん', '114832'),
                    ('花譜', '102617'), ('Evan Call', '115018'), ('BTS', '12095'),
                    ('BLACKPINK', '13013'), ('TWICE', '17813'), (' IU', '15893'),
                    ('EXO', '9776'), ('NCT', '27681'), ('SEVENTEEN', '21988'),
                    ('Super Junior', '9775'), ('少女时代', '9777'), ('BIGBANG', '9778'),
                    ('2NE1', '9779'), ('GOT7', '14997'), ('MAMAMOO', '21269'),
                ],
            }
            artists = artist_map.get(tid, artist_map['artist_hot'])
            for name, aid in artists:
                vods.append({
                    'vod_id': 'artist_detail_' + aid,
                    'vod_name': name,
                    'vod_pic': '',
                    'vod_remarks': '歌手',
                    'vod_tag': 'folder'
                })
        total = len(vods)
        pagecount = (total + 29) // 30 if total > 0 else 1
        return {'list': vods, 'page': pg, 'pagecount': pagecount, 'limit': 30, 'total': total}

    def _get_artist_songs_by_category(self, tid, pg):
        artist_map = {
            'artist_hot': [
                ('周杰伦', '6452'), ('林俊杰', '6453'), ('陈奕迅', '211'),
                ('邓紫棋', '2706'), ('薛之谦', '5056'), ('毛不易', '12138267'),
            ],
            'artist_cn': [
                ('周杰伦', '6452'), ('林俊杰', '6453'), ('陈奕迅', '211'),
                ('张学友', '2'), ('王菲', '9715'), ('五月天', '12'),
            ],
            'artist_us': [
                ('Taylor Swift', '6456'), ('Ed Sheeran', '7525'), ('Justin Bieber', '703'),
                ('Ariana Grande', '10526'), ('Bruno Mars', '479'), ('Lady Gaga', '1096'),
            ],
            'artist_jp': [
                ('米津玄師', '107145'), ('RADWIMPS', '23265'), ('YOASOBI', '106925'),
                ('ONE OK ROCK', '2142'), ('imase', '107456'), ('宇多田光', '123'),
            ],
        }
        search_keywords = {
            'artist_hot': '热门歌曲',
            'artist_cn': '华语歌曲',
            'artist_us': '欧美歌曲',
            'artist_jp': '日韩歌曲',
        }
        artists = artist_map.get(tid, artist_map['artist_hot'])
        vods = []
        seen_songs = set()

        for name, aid in artists:
            try:
                api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&singermid={aid}&order=listen&begin=0&num=20&songstatus=1"
                res = self.fetch(api_url)
                data = res.json()
                song_list = data.get('list', [])

                for it in song_list:
                    songmid = str(it.get('songmid', ''))
                    song_name = it.get('songname', '')
                    
                    if songmid and song_name and songmid not in seen_songs:
                        seen_songs.add(songmid)
                        singer_name = name
                        
                        albumpic = it.get('album', {}).get('albumPic', '')
                        if albumpic and '{size}' in albumpic:
                            albumpic = albumpic.replace('{size}', '400')
                        
                        display_name = song_name + " - " + singer_name if singer_name else song_name
                        display_name = re.sub(r'[$#]', '', display_name).strip()
                        
                        vods.append({
                            'vod_name': display_name,
                            'vod_id': 'artist_detail_' + aid + '_' + songmid,
                            'vod_pic': albumpic,
                            'vod_remarks': singer_name or 'QQ音乐',
                            'vod_actor': singer_name,
                        })
            except Exception as e:
                print("_get_artist_songs_by_category error:", e)

        if not vods:
            keyword = search_keywords.get(tid, '热门歌曲')
            search_result = self._get_search_songs(keyword, pg)
            vods = search_result.get('list', [])
            
            artists_dict = {name: aid for name, aid in artists}
            for item in vods:
                if 'artist_detail_' not in item['vod_id']:
                    song_name = item['vod_name']
                    matched_aid = ''
                    matched_name = item.get('vod_actor', '')
                    
                    if matched_name and matched_name in artists_dict:
                        matched_aid = artists_dict[matched_name]
                    else:
                        for name, aid in artists:
                            if name in song_name:
                                matched_name = name
                                matched_aid = aid
                                break
                    
                    if not matched_aid:
                        matched_aid = artists[0][1] if artists else '6452'
                        matched_name = artists[0][0] if artists else '歌手'
                    
                    songmid = item['vod_id'].replace('song_', '')
                    item['vod_id'] = 'artist_detail_' + matched_aid + '_' + songmid
                    item['vod_actor'] = matched_name
                    item['vod_remarks'] = matched_name

        start_idx = (pg - 1) * 30
        end_idx = start_idx + 30
        paginated_vods = vods[start_idx:end_idx]

        return {'list': paginated_vods, 'page': pg, 'pagecount': max(1, (len(vods) + 29) // 30), 'limit': 30, 'total': len(vods)}

    def _default_artists(self):
        default = [
            ("周杰伦", "6452"), ("林俊杰", "6453"), ("陈奕迅", "211"),
            ("邓紫棋", "2706"), ("薛之谦", "5056"), ("毛不易", "12138267"),
            ("李荣浩", "5745"), ("华晨宇", "6455"), ("张学友", "2"),
            ("王菲", "9715"), ("五月天", "12"), ("Taylor Swift", "6456"),
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

        artist_name_map = {
            '6452': '周杰伦', '6453': '林俊杰', '211': '陈奕迅',
            '2706': '邓紫棋', '5056': '薛之谦', '12138267': '毛不易',
            '5745': '李荣浩', '6455': '华晨宇', '2': '张学友',
            '9715': '王菲', '12': '五月天', '6456': 'Taylor Swift',
            '7525': 'Ed Sheeran', '703': 'Justin Bieber', '10526': 'Ariana Grande',
            '479': 'Bruno Mars', '1096': 'Lady Gaga', '107145': '米津玄師',
            '23265': 'RADWIMPS', '106925': 'YOASOBI', '2142': 'ONE OK ROCK',
            '107456': 'imase', '123': '宇多田光',
            '131': '张杰', '5926': '张碧晨', '335': '汪苏泷',
            '563': '许嵩', '162': '徐良', '126': '萧敬腾',
            '429': '杨宗纬', '895': '张韶涵', '877': '田馥甄',
            '351': '蔡依林', '353': '王心凌', '276': '张惠妹',
            '64': '孙燕姿', '83': '梁静茹',
            '116058': 'Billie Eilish', '459': 'The Weeknd', '19446': 'Dua Lipa',
            '23696': 'Post Malone', '1562': 'Shawn Mendes', '1319': 'Selena Gomez',
            '305': 'Katy Perry', '426': 'Rihanna', '99': 'Beyoncé',
            '104': 'Adele', '1965': 'Sam Smith', '170': 'Coldplay',
            '155': 'Maroon 5', '32174': 'Imagine Dragons', '694': 'OneRepublic',
            '9511': 'LiSA', '98916': 'Aimer', '85714': 'Official髭男dism',
            '104814': 'King Gnu', '22695': 'Back Number', '114832': 'あいみょん',
            '102617': '花譜', '115018': 'Evan Call', '12095': 'BTS',
            '13013': 'BLACKPINK', '17813': 'TWICE', '15893': ' IU',
            '9776': 'EXO', '27681': 'NCT', '21988': 'SEVENTEEN',
        }

        search_keyword = artist_name_map.get(artist_id, '')

        try:
            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&singermid={artist_id}&order=listen&begin=0&num=100&songstatus=1"
            res = self.fetch(api_url)
            data = res.json()

            singer_info = data.get('singerinfo', {})
            artist_name = singer_info.get('singer_name', '')

            if not artist_name:
                artist_name = artist_name_map.get(artist_id, '')

            song_list = data.get('list', [])
            for it in song_list:
                songmid = str(it.get('songmid', ''))
                song_name = it.get('songname', '')

                if songmid and song_name:
                    display_name = song_name + " - " + artist_name if artist_name else song_name
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    song_name_clean = re.sub(r'[$#&]', '', song_name).strip()
                    artist_name_clean = re.sub(r'[$#&]', '', artist_name).strip() if artist_name else ''
                    play_arr.append(display_name + "$" + song_name_clean + "&&" + artist_name_clean + "&&" + songmid)

                    albumpic = it.get('album', {}).get('albumPic', '')
                    if albumpic and '{size}' in albumpic:
                        albumpic = albumpic.replace('{size}', '400')
                    play_pics.append(albumpic)

            if not artist_name and song_list:
                artist_name = song_list[0].get('singer', [{}])[0].get('name', '')
            
            if not search_keyword:
                search_keyword = artist_name
        except Exception as e:
            print("_get_artist_detail API error:", e)

        if len(play_arr) < 30:
            if not artist_name:
                artist_name = artist_name_map.get(artist_id, '')
            
            search_keyword = artist_name if artist_name else search_keyword
            
            if search_keyword:
                search_result = self._get_search_songs(search_keyword, 1)
                
                existing_songmids = set()
                for item in play_arr:
                    parts = item.split('&&')
                    if len(parts) >= 3:
                        existing_songmids.add(parts[-1])

                for item in search_result.get('list', []):
                    songmid = item['vod_id'].replace('song_', '')
                    if songmid not in existing_songmids:
                        display_name = item['vod_name']
                        artist_name_item = item.get('vod_actor', '')
                        song_name_clean = re.sub(r'[$#&]', '', display_name).strip()
                        artist_name_clean = re.sub(r'[$#&]', '', artist_name_item).strip() if artist_name_item else ''
                        play_arr.append(display_name + "$" + song_name_clean + "&&" + artist_name_clean + "&&" + songmid)
                        play_pics.append(item.get('vod_pic', ''))
                        if len(play_arr) >= 30:
                            break

            if not artist_name:
                artist_name = '热门歌手'

        song_list = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list for _ in qualities])

        vod = {
            'vod_id': artist_id,
            'vod_name': artist_name or '歌手',
            'vod_pic': '',
            'vod_content': "微信公众号：" + self.wx_gzh + "\n福利多多，精彩多多\n共 " + str(len(play_arr)) + " 首歌曲",
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_actor': artist_name,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        play_pic_list = [p if p and p.startswith('http') else self.default_pic for p in play_pics]
        if play_pic_list:
            vod['vod_play_pic'] = '$$$'.join(['#'.join(play_pic_list) for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.0

        return {'list': [vod]}

    def _get_artist_songs(self, artist_id, pg):
        vods = []
        artist_name_map = {
            '6452': '周杰伦', '6453': '林俊杰', '211': '陈奕迅',
            '2706': '邓紫棋', '5056': '薛之谦', '12138267': '毛不易',
            '5745': '李荣浩', '6455': '华晨宇', '2': '张学友',
            '9715': '王菲', '12': '五月天', '6456': 'Taylor Swift',
            '7525': 'Ed Sheeran', '703': 'Justin Bieber', '10526': 'Ariana Grande',
            '479': 'Bruno Mars', '1096': 'Lady Gaga', '107145': '米津玄師',
            '23265': 'RADWIMPS', '106925': 'YOASOBI', '2142': 'ONE OK ROCK',
            '107456': 'imase', '123': '宇多田光',
            '131': '张杰', '5926': '张碧晨', '335': '汪苏泷',
            '563': '许嵩', '162': '徐良', '126': '萧敬腾',
            '429': '杨宗纬', '895': '张韶涵', '877': '田馥甄',
            '351': '蔡依林', '353': '王心凌', '276': '张惠妹',
            '64': '孙燕姿', '83': '梁静茹',
            '116058': 'Billie Eilish', '459': 'The Weeknd', '19446': 'Dua Lipa',
            '23696': 'Post Malone', '1562': 'Shawn Mendes', '1319': 'Selena Gomez',
            '305': 'Katy Perry', '426': 'Rihanna', '99': 'Beyoncé',
            '104': 'Adele', '1965': 'Sam Smith', '170': 'Coldplay',
            '155': 'Maroon 5', '32174': 'Imagine Dragons', '694': 'OneRepublic',
            '9511': 'LiSA', '98916': 'Aimer', '85714': 'Official髭男dism',
            '104814': 'King Gnu', '22695': 'Back Number', '114832': 'あいみょん',
            '102617': '花譜', '115018': 'Evan Call', '12095': 'BTS',
            '13013': 'BLACKPINK', '17813': 'TWICE', '15893': ' IU',
            '9776': 'EXO', '27681': 'NCT', '21988': 'SEVENTEEN',
        }
        search_keyword = artist_name_map.get(artist_id, '')

        try:
            begin = (pg - 1) * 30
            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&singermid={artist_id}&order=listen&begin={begin}&num=30&songstatus=1"
            res = self.fetch(api_url)
            data = res.json()

            singer_info = data.get('singerinfo', {})
            singer_name = singer_info.get('singer_name', '')
            
            if not singer_name:
                singer_name = artist_name_map.get(artist_id, '')

            song_list = data.get('list', [])
            for it in song_list:
                songmid = str(it.get('songmid', ''))
                song_name = it.get('songname', '')

                albumpic = it.get('album', {}).get('albumPic', '')
                if albumpic and '{size}' in albumpic:
                    albumpic = albumpic.replace('{size}', '400')

                if songmid and song_name:
                    display_name = song_name + " - " + singer_name if singer_name else song_name
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'artist_detail_' + artist_id + '_' + songmid,
                        'vod_pic': albumpic,
                        'vod_remarks': singer_name or 'QQ音乐',
                        'vod_actor': singer_name,
                    })
            
            if not search_keyword:
                search_keyword = singer_name
        except Exception as e:
            print("_get_artist_songs API error:", e)

        if len(vods) < 30:
            if search_keyword:
                search_result = self._get_search_songs(search_keyword, pg)
                
                existing_songmids = set()
                for v in vods:
                    existing_songmids.add(v['vod_id'].replace('artist_detail_' + artist_id + '_', ''))

                for item in search_result.get('list', []):
                    songmid = item.get('vod_id', '').replace('song_', '')
                    if songmid not in existing_songmids:
                        item['vod_id'] = 'artist_detail_' + artist_id + '_' + songmid
                        vods.append(item)
                        if len(vods) >= 30:
                            break

        start_idx = (pg - 1) * 30
        end_idx = start_idx + 30
        paginated_vods = vods[start_idx:end_idx]

        return {'list': paginated_vods, 'page': pg, 'pagecount': max(1, (len(vods) + 29) // 30), 'limit': 30, 'total': max(len(vods), 999)}

    def _get_bang_list(self, tid, pg):
        vods = []
        try:
            bang_map = {
                'bang_hot': ('3', 'QQ音乐热歌榜'),
                'bang_new': ('2', 'QQ音乐新歌榜'),
                'bang_classic': ('23', 'QQ音乐经典榜'),
                'bang_douyin': ('197', '抖音热歌榜'),
                'bang_billboard': ('4', 'Billboard榜'),
            }
            bang_info = bang_map.get(tid, ('3', 'QQ音乐热歌榜'))
            bang_id = bang_info[0]
            bang_name = bang_info[1]

            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&tpl=3&page=detail&type=top&topid={bang_id}&_=1572275641432"
            res = self.fetch(api_url)
            data = res.json()

            info = data.get('detail', {})
            pic = info.get('pic_album', info.get('pic', ''))
            if pic and '{size}' in pic:
                pic = pic.replace('{size}', '400')

            vods.append({
                'vod_name': bang_name,
                'vod_id': 'bang_detail_' + bang_id,
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
            ('3', 'QQ音乐热歌榜'),
            ('2', 'QQ音乐新歌榜'),
            ('23', 'QQ音乐经典榜'),
            ('197', '抖音热歌榜'),
            ('4', 'Billboard榜'),
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
        bang_name = 'QQ音乐排行榜'
        bang_pic = ''

        bang_name_map = {
            '2': 'QQ音乐新歌榜',
            '3': 'QQ音乐热歌榜',
            '4': 'Billboard榜',
            '23': 'QQ音乐经典榜',
            '197': '抖音热歌榜',
        }
        bang_name = bang_name_map.get(bang_id, bang_name)

        try:
            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&tpl=3&page=detail&type=top&topid={bang_id}&_=1572275641432"
            res = self.fetch(api_url)
            d = res.json()

            info = d.get('topinfo', d.get('detail', {}))
            bang_name = info.get('topTitle', info.get('name', bang_name))
            bang_pic = info.get('pic_album', info.get('pic', ''))
            if bang_pic and '{size}' in bang_pic:
                bang_pic = bang_pic.replace('{size}', '400')

            song_list = d.get('songlist', [])
            for it in song_list:
                song_data = it.get('data', it)
                songmid = str(song_data.get('songmid', ''))
                song_name = song_data.get('songname', '')
                singer_name = ''
                singer_list = song_data.get('singer', [])
                if singer_list:
                    singer_name = singer_list[0].get('name', '')

                albummid = song_data.get('albummid', '')
                albumpic = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{albummid}.jpg" if albummid else ''

                if songmid and song_name:
                    display_name = song_name + " - " + singer_name if singer_name else song_name
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    song_name_clean = re.sub(r'[$#&]', '', song_name).strip()
                    singer_name_clean = re.sub(r'[$#&]', '', singer_name).strip() if singer_name else ''
                    play_arr.append(display_name + "$" + song_name_clean + "&&" + singer_name_clean + "&&" + songmid)
                    play_pics.append(albumpic)
        except Exception as e:
            print("_get_bang_detail error:", e)

        if not play_arr:
            search_keywords = {
                '2': '新歌',
                '197': '抖音热歌',
            }
            keyword = search_keywords.get(bang_id, '热门歌曲')
            search_result = self._get_search_songs(keyword, 1)
            for item in search_result.get('list', []):
                songmid = item['vod_id'].replace('song_', '')
                display_name = item['vod_name']
                artist_name = item.get('vod_actor', '')
                song_name_clean = re.sub(r'[$#&]', '', display_name).strip()
                artist_name_clean = re.sub(r'[$#&]', '', artist_name).strip() if artist_name else ''
                play_arr.append(display_name + "$" + song_name_clean + "&&" + artist_name_clean + "&&" + songmid)
                play_pics.append(item.get('vod_pic', ''))

        song_list_str = '#'.join(play_arr)
        qualities = [q[0] + ' - ' + self.wx_gzh for q in self.quality_config]
        vod_play_from = '$$$'.join(qualities)
        vod_play_url = '$$$'.join([song_list_str for _ in qualities])

        vod = {
            'vod_id': bang_id,
            'vod_name': bang_name,
            'vod_pic': bang_pic or (play_pics[0] if play_pics else ''),
            'vod_content': '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多',
            'vod_remarks': "歌曲 : " + str(len(play_arr)) + "首",
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
        }
        play_pic_list = [p if p and p.startswith('http') else self.default_pic for p in play_pics]
        if play_pic_list:
            vod['vod_play_pic'] = '$$$'.join(['#'.join(play_pic_list) for _ in qualities])
            vod['vod_play_pic_ratio'] = 1.0

        return {'list': [vod]}

    def _get_bang_songs(self, bang_id, pg):
        vods = []
        try:
            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_toplist_cp.fcg?g_tk=5381&uin=0&format=json&inCharset=utf-8&outCharset=utf-8&notice=0&platform=h5&needNewCode=1&tpl=3&page=detail&type=top&topid={bang_id}&_=1572275641432"
            res = self.fetch(api_url)
            d = res.json()

            song_list = d.get('songlist', [])

            start_idx = (pg - 1) * 30
            end_idx = start_idx + 30
            paginated_songs = song_list[start_idx:end_idx]

            for it in paginated_songs:
                song_data = it.get('data', it)
                songmid = str(song_data.get('songmid', ''))
                song_name = song_data.get('songname', '')
                singer_name = ''
                singer_list = song_data.get('singer', [])
                if singer_list:
                    singer_name = singer_list[0].get('name', '')

                albummid = song_data.get('albummid', '')
                albumpic = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{albummid}.jpg" if albummid else ''

                if songmid and song_name:
                    display_name = song_name + " - " + singer_name if singer_name else song_name
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'bang_detail_' + bang_id + '_' + songmid,
                        'vod_pic': albumpic,
                        'vod_remarks': singer_name or 'QQ音乐',
                        'vod_actor': singer_name,
                    })
        except Exception as e:
            print("_get_bang_songs error:", e)

        if not vods:
            search_keywords = {
                '2': '新歌',
                '3': '热门歌曲',
                '4': 'Billboard',
                '23': '经典老歌',
                '197': '抖音热歌',
            }
            keyword = search_keywords.get(bang_id, '热门歌曲')
            search_result = self._get_search_songs(keyword, pg)
            vods = search_result.get('list', [])
            
            for item in vods:
                if 'bang_detail_' not in item['vod_id']:
                    item['vod_id'] = 'bang_detail_' + bang_id + '_' + item['vod_id'].replace('song_', '')
                    
        return {'list': vods, 'page': pg, 'pagecount': 99, 'limit': 30, 'total': 9999}

    def _get_song_detail(self, vid):
        result = {"list": []}
        try:
            songmid = vid.replace("song_", "")
            song_info = self._get_song_info(songmid)
            song_name = song_info.get('name', '')
            artist = song_info.get('artist', '')
            album = song_info.get('album', '')
            pic = song_info.get('pic', '')

            if not song_name:
                song_name = "歌曲_" + songmid[:8]

            song_name = re.sub(r'[$#]', '', song_name).strip()
            artist = re.sub(r'[$#]', '', artist).strip() if artist else ''

            display_name = song_name + " - " + artist if artist else song_name

            play_from_arr = []
            play_url_arr = []

            song_name_clean = re.sub(r'[$#&]', '', song_name).strip()
            artist_clean = re.sub(r'[$#&]', '', artist).strip() if artist else ''
            
            for q_name, q_type in self.quality_config:
                play_from_arr.append(q_name + ' - ' + self.wx_gzh)
                play_url_arr.append(display_name + "$" + song_name_clean + "&&" + artist_clean + "&&" + songmid)

            lrc = self._get_lyric(songmid, song_name, artist)
            content = "微信公众号：" + self.wx_gzh + "\n福利多多，精彩多多\n歌曲：" + song_name + "\n歌手：" + artist + "\n专辑：" + album + "\n来源：QQ音乐"
            if lrc:
                lrc_lines = lrc.split('\n')
                clean_lines = []
                for line in lrc_lines:
                    clean_line = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
                    if clean_line and not clean_line.startswith('['):
                        clean_lines.append(clean_line)
                if clean_lines:
                    content += "\n\n--- 歌词 ---\n" + '\n'.join(clean_lines[:30])

            song_pic = pic if pic and pic.startswith('http') else self.default_pic
            vod = {
                "vod_id": vid,
                "vod_name": song_name,
                "vod_pic": song_pic,
                "vod_content": content,
                "vod_remarks": album or 'QQ音乐',
                "vod_actor": artist,
                "vod_play_from": '$$$'.join(play_from_arr),
                "vod_play_url": '$$$'.join(play_url_arr),
            }
            vod['vod_play_pic'] = '$$$'.join([song_pic for _ in play_from_arr])
            vod['vod_play_pic_ratio'] = 1.0

            result["list"] = [vod]
        except Exception as e:
            print("_get_song_detail error:", e)

        if not result.get('list'):
            songmid = vid.replace("song_", "")
            song_name_clean = "歌曲_" + songmid[:8]
            artist_clean = ''
            vod = {
                "vod_id": vid,
                "vod_name": song_name_clean,
                "vod_pic": self.default_pic,
                "vod_content": '微信公众号：' + self.wx_gzh + '\n福利多多，精彩多多\nQQ音乐',
                "vod_remarks": 'QQ音乐',
                "vod_actor": '',
                "vod_play_from": '$$$'.join([q[0] + ' - ' + self.wx_gzh for q in self.quality_config]),
                "vod_play_url": '$$$'.join([song_name_clean + "$" + song_name_clean + "&&" + artist_clean + "&&" + songmid for _ in self.quality_config]),
            }
            result["list"] = [vod]

        return result

    def _get_song_info(self, songmid):
        info = {'name': '', 'artist': '', 'album': '', 'pic': '', 'duration': ''}

        try:
            api_url = f"https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songmid={songmid}&format=json"
            r = self.fetch(api_url, timeout=5)
            data = r.json()
            if data.get('data'):
                songs = data['data'].get('song', [])
                if songs:
                    song = songs[0]
                    info['name'] = song.get('songname', '')
                    singer_list = song.get('singer', [])
                    if singer_list:
                        info['artist'] = singer_list[0].get('name', '')
                    album_info = song.get('album', {})
                    info['album'] = album_info.get('albumname', '')
                    info['pic'] = album_info.get('albumPic', '')
                    info['duration'] = song.get('interval', '')
                    if info['pic'] and '{size}' in info['pic']:
                        info['pic'] = info['pic'].replace('{size}', '400')
                    return info
        except Exception:
            pass

        if not info.get('name'):
            try:
                import urllib.parse
                search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?new_json=1&w={urllib.parse.quote(songmid)}&format=json&p=1&n=10"
                r = self.fetch(search_url, timeout=5)
                data = r.json()
                song_list = data.get('data', {}).get('song', {}).get('list', [])
                if song_list:
                    song = song_list[0]
                    info['name'] = song.get('title', song.get('songname', ''))
                    singer_list = song.get('singer', [])
                    if singer_list:
                        info['artist'] = singer_list[0].get('name', '')
                    album_info = song.get('album', {})
                    info['album'] = album_info.get('name', album_info.get('albumname', ''))
                    albummid = album_info.get('mid', album_info.get('albummid', ''))
                    if albummid:
                        info['pic'] = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{albummid}.jpg"
                    info['duration'] = song.get('interval', '')
                    return info
            except Exception:
                pass

        return info

    def _get_play_url(self, songmid, song_name_hint='', artist_hint=''):
        methods = [
            lambda: self._get_kuwo_play_url(song_name_hint, artist_hint),
            lambda: self._get_kugou_play_url(song_name_hint, artist_hint),
            lambda: self._get_netease_play_url(song_name_hint, artist_hint),
            lambda: self._get_bilibili_play_url(song_name_hint, artist_hint),
            lambda: self._get_play_url_v3(songmid, song_name_hint, artist_hint),
            lambda: self._get_play_url_v1(songmid),
            lambda: self._get_play_url_v2(songmid),
            lambda: self._get_qqmusic_play_url(songmid),
        ]
        for i, method in enumerate(methods):
            try:
                url = method()
                if url and url.startswith('http'):
                    print(f"_get_play_url method {i} succeeded: {url[:80]}")
                    return url
            except Exception as e:
                print(f"_get_play_url method {i} failed: {e}")
                continue
        return ''

    def _get_qqmusic_play_url(self, songmid):
        try:
            api_url = f"https://v1.alapi.cn/api/qqmusic/url?songmid={songmid}"
            r = self.fetch(api_url, timeout=10)
            data = r.json()
            if data.get('code') == 200 and data.get('data'):
                url = data['data'].get('url', '')
                if url and url.startswith('http'):
                    return url
        except Exception as e:
            print("_get_qqmusic_play_url error:", e)
            pass

        try:
            api_url = f"https://api.darwinlabs.net/music/qq/search?keyword={songmid}&limit=1"
            r = self.fetch(api_url, timeout=10)
            data = r.json()
            if data.get('songs') and len(data['songs']) > 0:
                song = data['songs'][0]
                return song.get('url', '')
        except Exception as e:
            print("_get_qqmusic_play_url v2 error:", e)
            pass

        return ''

    def _get_play_url_v1(self, songmid):
        try:
            api_url = f"https://u.y.qq.com/cgi-bin/musicu.fcg?format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&data=%7B%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%221234567890%22%2C%22songmid%22%3A%5B%22{songmid}%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%220%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A0%2C%22format%22%3A%22json%22%2C%22ct%22%3A24%2C%22cv%22%3A0%7D%7D"
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            req_0 = data.get('req_0', {})
            data_info = req_0.get('data', {})
            midurlinfo = data_info.get('midurlinfo', [])
            if midurlinfo:
                purl = midurlinfo[0].get('purl', '')
                if purl:
                    sip = data_info.get('sip', [])
                    if sip:
                        return sip[0] + purl
        except Exception:
            pass
        return ''

    def _get_play_url_v2(self, songmid):
        try:
            api_url = f"https://www.y.qq.com/n/ryqq/player"
            res = self.fetch(api_url, timeout=5)
            if res and res.status_code == 200:
                import re
                match = re.search(r'"guid"\s*:\s*"([^"]+)"', res.text)
                guid = match.group(1) if match else '1234567890'
                api_url2 = f"https://u.y.qq.com/cgi-bin/musicu.fcg?format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&data=%7B%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%22{guid}%22%2C%22songmid%22%3A%5B%22{songmid}%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%220%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A0%2C%22format%22%3A%22json%22%2C%22ct%22%3A24%2C%22cv%22%3A0%7D%7D"
                r = self.fetch(api_url2, timeout=8)
                data = r.json()
                req_0 = data.get('req_0', {})
                data_info = req_0.get('data', {})
                midurlinfo = data_info.get('midurlinfo', [])
                if midurlinfo:
                    purl = midurlinfo[0].get('purl', '')
                    if purl:
                        sip = data_info.get('sip', [])
                        if sip:
                            return sip[0] + purl
        except Exception:
            pass
        return ''

    def _get_kuwo_play_url(self, song_name_hint='', artist_hint=''):
        if not song_name_hint:
            return ''
        kuwo_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.kuwo.cn/'
        }
        try:
            keyword = song_name_hint
            if artist_hint:
                keyword = artist_hint + " " + song_name_hint
            search_url = "https://search.kuwo.cn/r.s?client=kt&all=" + keyword + "&pn=0&rn=5&vipver=1&ft=music&encoding=utf8&rformat=json&mobi=1"
            r = self.fetch(search_url, headers=kuwo_headers, timeout=8)
            content = r.text
            if content.startswith('try{'):
                content = content[4:]
            if content.endswith('}catch(e){}'):
                content = content[:-11]
            if content.startswith('jsonp'):
                content = content.split('(', 1)[1].rsplit(')', 1)[0]
            data = json.loads(content)
            abslist = data.get('abslist', [])
            if abslist:
                first = abslist[0]
                rid = first.get('MUSICRID', '').replace('MUSIC_', '')
                if rid:
                    api_url = "https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid=" + str(rid) + "&bitrate=320&format=mp3"
                    r2 = self.fetch(api_url, headers=kuwo_headers, timeout=8)
                    data2 = r2.json()
                    if data2.get('code') == 200 and data2.get('data') and data2['data'].get('url'):
                        url = data2['data']['url']
                        if url.startswith('//'):
                            url = 'https:' + url
                        elif url.startswith('http://'):
                            url = url.replace('http://', 'https://', 1)
                        return url
        except Exception as e:
            print("_get_kuwo_play_url v1 error:", e)
            pass

        try:
            import urllib.parse
            api_url = f"https://api.kuwo.cn/v1/www/search/searchMusicBykeyWord?key={urllib.parse.quote(keyword)}&pn=1&rn=3"
            r = self.fetch(api_url, headers=kuwo_headers, timeout=8)
            data = r.json()
            if data.get('data') and data['data'].get('list'):
                song_list = data['data']['list']
                if song_list:
                    song = song_list[0]
                    rid = song.get('rid', '')
                    if rid:
                        api_url2 = f"https://api.kuwo.cn/v1/www/music/playUrl?mid={rid}&type=music"
                        r2 = self.fetch(api_url2, headers=kuwo_headers, timeout=8)
                        data2 = r2.json()
                        if data2.get('code') == 200 and data2.get('data') and data2['data'].get('url'):
                            return data2['data']['url']
        except Exception as e:
            print("_get_kuwo_play_url v2 error:", e)
            pass

        try:
            api_url = f"https://nmobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayer_ar_4.4.2.7_B_nuoweida_vh.apk&type=convert_url_with_sign&rid={keyword}&bitrate=320&format=mp3"
            r = self.fetch(api_url, headers=kuwo_headers, timeout=8)
            data2 = r.json()
            if data2.get('code') == 200 and data2.get('data') and data2['data'].get('url'):
                url = data2['data']['url']
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('http://'):
                    url = url.replace('http://', 'https://', 1)
                return url
        except Exception as e:
            print("_get_kuwo_play_url v3 error:", e)
            pass

        return ''

    def _get_kugou_play_url(self, song_name_hint='', artist_hint=''):
        if not song_name_hint:
            return ''
        try:
            keyword = song_name_hint
            if artist_hint:
                keyword = artist_hint + " " + song_name_hint
            import urllib.parse
            search_url = "https://wwwapi.kugou.com/search?keyword=" + urllib.parse.quote(keyword) + "&page=1&pagesize=5&userid=-1&clientver=&platform=WebFilter&tag=em&filter=2&iscorrection=1&privilege_filter=0"
            r = self.fetch(search_url, timeout=8)
            data = r.json()
            if data.get('status') == 1 and data.get('data'):
                lists = data['data'].get('lists', [])
                if lists:
                    song = lists[0]
                    hash_val = song.get('Hash', '')
                    album_id = song.get('album_id', '')
                    if hash_val:
                        api_url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={hash_val.upper()}&album_id={album_id}"
                        r2 = self.fetch(api_url, timeout=8)
                        data2 = r2.json()
                        if data2.get('status') == 1 and data2.get('data'):
                            play_data = data2['data']
                            if play_data.get('play_url'):
                                return play_data.get('play_url', '')
                            if play_data.get('play_backup_url'):
                                return play_data.get('play_backup_url', '')
        except Exception:
            pass

        try:
            api_url = "http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&keyword=" + urllib.parse.quote(keyword) + "&hash="
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

        return ''

    def _get_bilibili_play_url(self, song_name_hint='', artist_hint=''):
        if not song_name_hint:
            return ''
        try:
            keyword = song_name_hint
            if artist_hint:
                keyword = artist_hint + " " + song_name_hint
            import urllib.parse
            api_url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={urllib.parse.quote(keyword)}&search_type=music"
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            if data.get('data') and data['data'].get('result'):
                music_list = data['data']['result']
                if music_list:
                    music = music_list[0]
                    bvid = music.get('bvid', '')
                    if bvid:
                        cid_api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                        r2 = self.fetch(cid_api, timeout=8)
                        data2 = r2.json()
                        cid = data2.get('data', {}).get('cid', 1)
                        play_api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=64"
                        r3 = self.fetch(play_api, timeout=8)
                        data3 = r3.json()
                        durl = data3.get('data', {}).get('durl', [])
                        if durl:
                            return durl[0].get('url', '')
        except Exception:
            pass
        return ''

    def _get_netease_play_url(self, song_name_hint='', artist_hint=''):
        if not song_name_hint:
            return ''
        try:
            keyword = song_name_hint
            if artist_hint:
                keyword = artist_hint + " " + song_name_hint
            import urllib.parse
            api_url = f"https://music.163.com/api/search/pc?s={urllib.parse.quote(keyword)}&type=1&limit=3"
            r = self.fetch(api_url, timeout=8)
            data = r.json()
            if data.get('result') and data['result'].get('songs'):
                song = data['result']['songs'][0]
                return f"https://music.163.com/song/media/outer/url?id={song['id']}.mp3"
        except Exception:
            pass

        try:
            api_url = f"https://api.darwinlabs.net/music/netease/search?keyword={urllib.parse.quote(keyword)}&limit=3"
            r = self.fetch(api_url, timeout=10)
            data = r.json()
            if data.get('songs'):
                song = data['songs'][0]
                return f"https://music.163.com/song/media/outer/url?id={song['id']}.mp3"
        except Exception:
            pass

        try:
            api_url = f"https://api.coderschool.cn/music/search?keyword={urllib.parse.quote(keyword)}&type=netease"
            r = self.fetch(api_url, timeout=10)
            data = r.json()
            if data.get('data') and data['data'].get('list'):
                song_list = data['data']['list']
                if song_list:
                    song = song_list[0]
                    return song.get('url', '')
        except Exception:
            pass

        return ''

    def _get_play_url_v3(self, songmid, song_name_hint='', artist_hint=''):
        try:
            import urllib.parse
            if song_name_hint:
                keyword = urllib.parse.quote(song_name_hint)
                search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?new_json=1&w={keyword}&format=json&p=1&n=3"
            else:
                search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?new_json=1&w={urllib.parse.quote(songmid)}&format=json&p=1&n=3"
            res = self.fetch(search_url, timeout=5)
            data = res.json()
            song_list = data.get('data', {}).get('song', {}).get('list', [])
            if song_list:
                first_song = song_list[0]
                file_info = first_song.get('file', {})
                media_mid = file_info.get('media_mid', '')
                if media_mid:
                    return f"https://aqqmusic.tc.qq.com/amobile.music.tc.qq.com/C400{media_mid}.m4a?guid=1234567890&vkey="
        except Exception:
            pass

        try:
            api_url = f"https://v1.alapi.cn/api/qqmusic/url?songmid={songmid}"
            r = self.fetch(api_url, timeout=10)
            data = r.json()
            if data.get('code') == 200 and data.get('data'):
                url = data['data'].get('url', '')
                if url and url.startswith('http'):
                    return url
        except Exception:
            pass

        try:
            if song_name_hint:
                api_url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={urllib.parse.quote(song_name_hint)}&search_type=music"
                r = self.fetch(api_url, timeout=8)
                data = r.json()
                if data.get('data') and data['data'].get('result'):
                    music_list = data['data']['result']
                    if music_list:
                        music = music_list[0]
                        bvid = music.get('bvid', '')
                        if bvid:
                            return f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid=1&qn=64"
        except Exception:
            pass

        return ''

    def _get_play_url_fallback(self, songmid, song_name_hint='', artist_hint=''):
        methods = [
            lambda: self._get_kuwo_play_url(song_name_hint, artist_hint),
            lambda: self._get_kugou_play_url(song_name_hint, artist_hint),
            lambda: self._get_bilibili_play_url(song_name_hint, artist_hint),
            lambda: self._get_netease_play_url(song_name_hint, artist_hint),
            lambda: self._get_play_url_v3(songmid, song_name_hint, artist_hint),
        ]
        for method in methods:
            try:
                url = method()
                if url and url.startswith('http'):
                    return url
            except Exception:
                continue
        return ''

    def _get_lyric(self, songmid, song_name='', artist=''):
        lrc_text = ''

        try:
            api_url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={songmid}&format=json&nobase64=1"
            r = self.fetch(api_url, timeout=5)
            content = r.text
            if content.startswith('MusicJsonCallback('):
                content = content[19:-1]
            data = json.loads(content)
            lrc_text = data.get('lyric', '')
        except Exception:
            pass

        if not lrc_text and song_name:
            try:
                keyword = song_name
                if artist:
                    keyword = artist + " - " + song_name
                search_url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric.fcg?callback=jsonp1&pcachetime=1572275641&songname={keyword}&singer={artist}&platform=yqq"
                r = self.fetch(search_url, timeout=5)
                content = r.text
                match = re.search(r'jsonp1\((.*?)\)', content)
                if match:
                    data = json.loads(match.group(1))
                    lrc_text = data.get('lyric', '')
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
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?new_json=1&w={encoded_keyword}&format=json&p={pg}&n=30"
            res = self.fetch(search_url)
            data = res.json()

            song_list = data.get('data', {}).get('song', {}).get('list', [])

            vods = []
            for it in song_list:
                songmid = str(it.get('mid', it.get('songmid', '')))
                song_name = it.get('name', it.get('songname', ''))
                singer_name = ''
                singer_list = it.get('singer', [])
                if singer_list:
                    singer_name = singer_list[0].get('name', '')
                album_info = it.get('album', {})
                album_name = album_info.get('name', album_info.get('albumname', ''))
                album_mid = album_info.get('mid', '')

                if songmid and song_name:
                    display_name = song_name + " - " + singer_name if singer_name else song_name
                    display_name = re.sub(r'[$#]', '', display_name).strip()
                    pic = f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{album_mid}.jpg" if album_mid else ''
                    if not pic or not pic.startswith('http'):
                        pic = self.default_pic
                    
                    play_from_arr = []
                    play_url_arr = []
                    for q_name, q_type in self.quality_config:
                        play_from_arr.append(q_name + ' - ' + self.wx_gzh)
                        play_url_arr.append(display_name + "$" + songmid)
                    
                    vods.append({
                        'vod_name': display_name,
                        'vod_id': 'song_' + songmid,
                        'vod_pic': pic,
                        'vod_remarks': album_name or 'QQ音乐',
                        'vod_actor': singer_name,
                        'vod_play_from': '$$$'.join(play_from_arr),
                        'vod_play_url': '$$$'.join(play_url_arr),
                    })

            total = data.get('data', {}).get('song', {}).get('totalnum', 9999) or 9999
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