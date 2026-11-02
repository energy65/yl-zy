# -*- coding: utf-8 -*-
"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'LIBVIO',
  lang: 'hipy',
})
"""
import re
import json
import time
import hashlib
import base64
from urllib.parse import quote, urlencode
from base.spider import Spider as BaseSpider

try:
    from Crypto.Cipher import AES
    HAS_AES = True
except Exception:
    try:
        from Cryptodome.Cipher import AES
        HAS_AES = True
    except Exception:
        HAS_AES = False


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host_list = [
            "https://www.libvio.cam",
            "https://www.libvio.bid",
            "https://www.libvio.fun",
            "https://libvio.app",
        ]
        self.host = self.host_list[0]
        self.host_index = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": self.host + "/",
        }
        self.smart_salt = "RY7e48naFXPsLJC"
        self.wx_text = "微信公众号：源力软件汇"

    def getName(self):
        return 'LIBVIO'

    def homeContent(self, filter):
        classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '5', 'type_name': '综艺'},
            {'type_id': '3', 'type_name': '纪录片'},
        ]
        filters = self._get_filters()
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        html = self._fetch('/')
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        tid_str = str(tid)
        extend = extend if isinstance(extend, dict) else {}
        if filter and isinstance(filter, dict) and not extend:
            extend = filter

        class_val = extend.get('class') or extend.get('type') or ''
        area_val = extend.get('area') or ''
        lang_val = extend.get('lang') or ''
        year_val = extend.get('year') or ''
        by_val = extend.get('by') or extend.get('sort') or ''

        if class_val or area_val or lang_val or year_val or by_val:
            url = '/show/{}-{}-{}-{}-{}-{}.html'.format(
                quote(str(class_val)),
                quote(str(area_val)),
                quote(str(lang_val)),
                quote(str(year_val)),
                str(by_val),
                page
            )
        else:
            if page <= 1:
                url = '/type/{}.html'.format(tid_str)
            else:
                url = '/type/{}-{}.html'.format(tid_str, page)

        html = self._fetch(url)
        items = self._parse_video_list(html)
        pagecount = page + 1 if len(items) >= 20 else page
        return {"list": items, "page": page, "pagecount": pagecount, "limit": 24, "total": 99999}

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if ids else ''
        try:
            html = self._fetch('/detail/{}.html'.format(vid))
            if not html:
                return result

            vod_name = ''
            m_name = re.search(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', html, re.S)
            if m_name:
                vod_name = re.sub(r'<[^>]+>', '', m_name.group(1)).strip()
            if not vod_name:
                m_name = re.search(r'<title>([^<]+)</title>', html)
                if m_name:
                    vod_name = m_name.group(1).strip().split('-')[0].strip()

            vod_pic = ''
            m_pic = re.search(r'<img[^>]*class="[^"]*lazyload[^"]*"[^>]*data-original="([^"]+)"', html)
            if not m_pic:
                m_pic = re.search(r'data-original="([^"]+)"[^>]*class="[^"]*stui-vodlist__thumb', html)
            if not m_pic:
                m_pic = re.search(r'<img[^>]*data-original="([^"]+)"', html)
            if m_pic:
                vod_pic = m_pic.group(1).strip()

            vod_director = ''
            m_dir = re.search(r'导演[：:]\s*(.*?)</p>', html, re.S)
            if m_dir:
                vod_director = re.sub(r'<[^>]+>', '', m_dir.group(1)).replace(' ', '').strip()

            vod_actor = ''
            m_act = re.search(r'主演[：:]\s*(.*?)</p>', html, re.S)
            if m_act:
                vod_actor = re.sub(r'<[^>]+>', '', m_act.group(1)).strip()

            vod_year = ''
            m_year = re.findall(r'(\d{4})', html)
            for y in m_year:
                if 1900 < int(y) < 2100:
                    vod_year = y
                    break

            vod_area = ''
            m_area = re.search(r'地区[：:]\s*([^<\n]+)', html)
            if m_area:
                vod_area = m_area.group(1).strip()

            vod_type = ''
            m_type = re.search(r'类型[：:]\s*(.*?)</p>', html, re.S)
            if m_type:
                vod_type = re.sub(r'<[^>]+>', '', m_type.group(1)).strip().replace(' ', ',')

            vod_remarks = ''
            m_rem = re.search(r'<span[^>]*class="pic-text[^"]*"[^>]*>([^<]+)</span>', html)
            if m_rem:
                vod_remarks = m_rem.group(1).strip()

            vod_content = ''
            m_desc = re.search(r'class="detail-content"[^>]*>(.*?)</span>', html, re.S)
            if m_desc:
                vod_content = re.sub(r'<[^>]+>', '', m_desc.group(1)).strip()
            if not vod_content:
                m_desc = re.search(r'class="detail-sketch"[^>]*>(.*?)</span>', html, re.S)
                if m_desc:
                    vod_content = re.sub(r'<[^>]+>', '', m_desc.group(1)).strip()
            if not vod_content:
                m_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
                if m_desc:
                    vod_content = m_desc.group(1).strip()
            vod_content = self.wx_text + '\n\n' + vod_content if vod_content else self.wx_text

            play_from = []
            play_url = []

            heads = re.findall(r'<div[^>]*class="stui-vodlist__head"[^>]*>.*?<h3[^>]*>(.*?)</h3>', html, re.S)
            lists = re.findall(r'<ul[^>]*class="stui-content__playlist[^"]*"[^>]*>(.*?)</ul>', html, re.S)

            for idx, h in enumerate(heads):
                source_name = re.sub(r'<[^>]+>', '', h).strip()
                if not source_name or idx >= len(lists):
                    continue
                ul = lists[idx]
                eps = []
                for ep_href, ep_name in re.findall(r'<a[^>]*href="(/play/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>', ul, re.S):
                    name = ep_name.strip()
                    if not name:
                        continue
                    epid = '{}__{}__{}'.format(re.search(r'/play/(\d+)-(\d+)-(\d+)\.html', ep_href).group(1),
                                               re.search(r'/play/(\d+)-(\d+)-(\d+)\.html', ep_href).group(2),
                                               re.search(r'/play/(\d+)-(\d+)-(\d+)\.html', ep_href).group(3))
                    eps.append('{}${}'.format(name, epid))
                if eps:
                    play_from.append(source_name)
                    play_url.append('#'.join(eps))

            if not play_from:
                eps_all = re.findall(r'<a[^>]*href="(/play/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]+)</a>', html, re.S)
                eps = []
                for ep_href, _a, _b, _c, ep_name in eps_all:
                    eps.append('{}${}'.format(ep_name.strip(), '{}__{}__{}'.format(_a, _b, _c)))
                if eps:
                    play_from.append('默认线路')
                    play_url.append('#'.join(eps))

            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_director": vod_director,
                "vod_actor": vod_actor,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_type": vod_type,
                "vod_remarks": vod_remarks,
                "vod_content": vod_content,
                "vod_play_from": '$$$'.join(play_from),
                "vod_play_url": '$$$'.join(play_url),
            }
            result['list'].append(vod)
        except Exception as e:
            print('detailContent error: {}'.format(e))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            parts = id.split('__')
            if len(parts) != 3:
                return result
            vid, sid, nid = parts[0], parts[1], parts[2]
            play_page = '/play/{}-{}-{}.html'.format(vid, sid, nid)
            html = self._fetch(play_page)
            if not html:
                return result

            m_pa = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
            if not m_pa:
                return result
            try:
                pa = json.loads(m_pa.group(1))
            except Exception:
                return result

            purl = pa.get('url', '')
            pfrom = pa.get('from', '')
            if not purl:
                return result

            art_url = self.host + '/static/player/artplayer/?url=' + quote(purl)
            if pa.get('link_next'):
                try:
                    art_url += '&next=' + quote(self.host + pa.get('link_next'))
                except Exception:
                    pass
            art_html = self._fetch(art_url)
            if not art_html:
                result["url"] = purl
                result["parse"] = 0
                return result

            playPageUrl = self._extract_js_var(art_html, 'playPageUrl')
            secretKeySeed = self._extract_js_var(art_html, 'secretKeySeed')
            timestamp = self._extract_js_var(art_html, 'timestamp')
            videoHash = self._extract_js_var(art_html, 'videoHash')
            isSmartPlay = self._extract_js_var(art_html, 'isSmartPlay')

            if playPageUrl and secretKeySeed and timestamp and isSmartPlay and str(isSmartPlay).strip().lower() == 'true':
                t = str(int(time.time()))
                body = {
                    "vkey": playPageUrl,
                    "code": secretKeySeed,
                    "t": int(t),
                    "signature": hashlib.md5(t.encode('utf-8')).hexdigest()
                }
                api_headers = dict(self.headers)
                api_headers['Content-Type'] = 'application/json'
                api_headers['Origin'] = self.host
                api_headers['Referer'] = art_url
                try:
                    rsp = self.fetch('https://hd.ticktockwow.com/smartplay-cache/api/webvideo_ty.php', data=json.dumps(body).encode('utf-8'), headers=api_headers)
                    if rsp and rsp.text:
                        j = json.loads(rsp.text)
                        enc_url = j.get('url') or j.get('data', {}).get('url') if isinstance(j.get('data'), dict) else j.get('url')
                        if enc_url and HAS_AES:
                            dec = self._aes_decrypt_smart(enc_url, timestamp)
                            if dec and ('.m3u8' in dec or '.mp4' in dec or dec.startswith('http')):
                                result["url"] = dec
                                result["parse"] = 0
                                return result
                except Exception as e:
                    print('smartplay error', e)

            if pfrom and pfrom not in ['kuake', 'xunlei', 'quark', 'baidu', 'ucpan', 'pikpak']:
                result["header"] = json.dumps({"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"})
            result["url"] = purl
            result["parse"] = 0
            return result
        except Exception as e:
            print('playerContent error: {}'.format(e))
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = int(pg) if pg and str(pg).isdigit() else 1
        url = '/search/-------------.html?wd={}&page={}'.format(quote(key), page)
        html = self._fetch(url)
        items = self._parse_video_list(html)
        pagecount = page + 1 if len(items) >= 10 else page
        return {"list": items, "page": page, "pagecount": pagecount, "limit": 20, "total": 99999}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _extract_js_var(self, html, key):
        m = re.search(r'{}\s*=\s*([\'"])(.*?)\1'.format(re.escape(key)), html, re.S)
        if m:
            return m.group(2)
        m2 = re.search(r'{}\s*=\s*(true|false|null|\d+)'.format(re.escape(key)), html, re.S)
        if m2:
            return m2.group(1)
        return ''

    def _aes_decrypt_smart(self, enc_b64, timestamp):
        try:
            ts = str(timestamp).strip()
            h = hashlib.md5((ts + self.smart_salt).encode('utf-8')).hexdigest()
            key = bytes.fromhex(h[16:32])
            iv = bytes.fromhex(h[0:16])
            ct = base64.b64decode(enc_b64)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            pt = cipher.decrypt(ct)
            if pt and len(pt) > 0:
                pad = pt[-1]
                if pad >= 1 and pad <= 16:
                    pt = pt[:-pad]
            return pt.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print('_aes_decrypt_smart error', e)
            return ''

    def _get_filters(self):
        return {
            "1": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "剧情片", "v": "剧情片"}, {"n": "喜剧片", "v": "喜剧片"}, {"n": "动作片", "v": "动作片"},
                    {"n": "爱情片", "v": "爱情片"}, {"n": "科幻片", "v": "科幻片"}, {"n": "奇幻片", "v": "奇幻片"}, {"n": "恐怖片", "v": "恐怖片"},
                    {"n": "悬疑片", "v": "悬疑片"}, {"n": "惊悚片", "v": "惊悚片"}, {"n": "犯罪片", "v": "犯罪片"}, {"n": "战争片", "v": "战争片"},
                    {"n": "冒险片", "v": "冒险片"}, {"n": "武侠片", "v": "武侠片"}, {"n": "历史片", "v": "历史片"}, {"n": "传记片", "v": "传记片"},
                    {"n": "歌舞片", "v": "歌舞片"}, {"n": "灾难片", "v": "灾难片"}, {"n": "西部片", "v": "西部片"}, {"n": "纪录片", "v": "纪录片"}, {"n": "动画片", "v": "动画片"}
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"}, {"n": "更早", "v": "2015"}
                ]},
            ],
            "2": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "古装", "v": "古装"}, {"n": "战争", "v": "战争"}, {"n": "青春偶像", "v": "青春偶像"}, {"n": "喜剧", "v": "喜剧"},
                    {"n": "家庭", "v": "家庭"}, {"n": "犯罪", "v": "犯罪"}, {"n": "动作", "v": "动作"}, {"n": "奇幻", "v": "奇幻"}, {"n": "剧情", "v": "剧情"},
                    {"n": "历史", "v": "历史"}, {"n": "经典", "v": "经典"}, {"n": "乡村", "v": "乡村"}, {"n": "情景", "v": "情景"}, {"n": "商战", "v": "商战"},
                    {"n": "网剧", "v": "网剧"}, {"n": "其他", "v": "其他"}, {"n": "都市", "v": "都市"}, {"n": "言情", "v": "言情"}, {"n": "悬疑", "v": "悬疑"},
                    {"n": "科幻", "v": "科幻"}, {"n": "热血", "v": "热血"}, {"n": "励志", "v": "励志"}, {"n": "谍战", "v": "谍战"}, {"n": "武侠", "v": "武侠"}, {"n": "恐怖", "v": "恐怖"}
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "更早", "v": "2019"}
                ]},
            ],
            "3": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "更早", "v": "2021"}
                ]},
            ],
            "4": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "日本", "v": "日本"}, {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "更早", "v": "2021"}
                ]},
            ],
            "5": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"}, {"n": "台湾", "v": "台湾"},
                    {"n": "韩国", "v": "韩国"}, {"n": "日本", "v": "日本"}, {"n": "美国", "v": "美国"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "更早", "v": "2021"}
                ]},
            ],
        }

    def _fetch(self, url):
        try:
            if url.startswith('http'):
                headers = dict(self.headers)
                rsp = self.fetch(url, headers=headers)
                return rsp.text if rsp else ''
            for i in range(len(self.host_list)):
                idx = (self.host_index + i) % len(self.host_list)
                host = self.host_list[idx]
                try:
                    full_url = host + url
                    headers = dict(self.headers)
                    headers["Referer"] = host + "/"
                    rsp = self.fetch(full_url, headers=headers)
                    if rsp and rsp.text:
                        if idx != self.host_index:
                            self.host_index = idx
                            self.host = host
                            self.headers["Referer"] = self.host + "/"
                        return rsp.text
                except Exception:
                    continue
            return ''
        except Exception:
            return ''

    def _parse_video_list(self, html):
        videos = []
        seen = set()
        try:
            items = re.findall(
                r'<a[^>]*class="[^"]*stui-vodlist__thumb[^"]*"[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>(.*?)</a>',
                html, re.S
            )
            if not items:
                items = re.findall(
                    r'<a[^>]*href="(/detail/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>.*?data-original="([^"]+)"',
                    html, re.S
                )
                for href, vid, title, pic in items:
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    videos.append({"vod_id": vid, "vod_name": title.strip(), "vod_pic": pic.strip(), "vod_remarks": ""})
                return videos

            for href, title, pic, rest in items:
                vid = ''
                m_vid = re.search(r'/detail/(\d+)\.html', href)
                if m_vid:
                    vid = m_vid.group(1)
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                title = title.strip()
                if not title:
                    continue
                remarks = ''
                m_rem = re.search(r'class="pic-text[^"]*"[^>]*>([^<]+)</span>', rest)
                if m_rem:
                    remarks = m_rem.group(1).strip()
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic.strip() if pic else '',
                    "vod_remarks": remarks,
                })
        except Exception as e:
            print('_parse_video_list error: {}'.format(e))
        return videos
