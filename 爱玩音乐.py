import re
import sys
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote
from pyquery import PyQuery as pq
from requests import Session, adapters
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.22a5.com"
        self.session = Session()
        adapter = adapters.HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]), pool_connections=20, pool_maxsize=50)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"}
        self.session.headers.update(self.headers)
        self._verify_attempts = 0

    def getName(self): return "爱听音乐"
    def isVideoFormat(self, url): return bool(re.search(r'\.(m3u8|mp4|mp3|m4a|flv)(\?|$)', url or "", re.I))
    def manualVideoCheck(self): return False
    def destroy(self): self.session.close()

    def homeContent(self, filter):
        classes = [{"type_name": n, "type_id": i} for n, i in [("歌手","/singerlist/index/index/index/index.html"), ("TOP榜单","/list/top.html"), ("新歌榜","/list/new.html"), ("电台","/radiolist/index.html"), ("高清MV","/mvlist/index.html"), ("专辑","/albumlist/index.html"), ("歌单","/playtype/index.html")]]
        filters = {p: d for p in [c["type_id"] for c in classes if "singer" not in c["type_id"]] if (d := self._fetch_filters(p))}
        
        if "/radiolist/index.html" not in filters:
            filters["/radiolist/index.html"] = [{"key": "id", "name": "分类", "value": [{"n": n, "v": v} for n,v in zip(["最新","最热","有声小说","相声","音乐","情感","国漫","影视","脱口秀","历史","儿童","教育","八卦","推理","头条"], ["index","hot","novel","xiangyi","music","emotion","game","yingshi","talkshow","history","children","education","gossip","tuili","headline"])]}]

        filters["/singerlist/index/index/index/index.html"] = [
            {"key": "area", "name": "地区", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("华语","huayu"),("欧美","oumei"),("韩国","hanguo"),("日本","ribrn")]]},
            {"key": "sex", "name": "性别", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("男","male"),("女","girl"),("组合","band")]]},
            {"key": "genre", "name": "流派", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("流行","liuxing"),("电子","dianzi"),("摇滚","yaogun"),("嘻哈","xiha"),("R&B","rb"),("民谣","minyao"),("爵士","jueshi"),("古典","gudian")]]},
            {"key": "char", "name": "字母", "value": [{"n": n, "v": v} for n,v in [("全部","index")] + [{"n": chr(i), "v": chr(i).lower()} for i in range(65, 91)]]}
        ]
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self): return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        url = tid
        if "/singerlist/" in tid:
            p = tid.split('/')
            if len(p) >= 6:
                url = "/".join(p[:2] + [extend.get(k, p[i]) for i, k in enumerate(["area", "sex", "genre"], 2)] + [f"{extend.get('char', 'index')}.html"])
        elif "id" in extend and extend["id"] not in ["index", "top"]:
            url = tid.replace("index.html", f"{extend['id']}.html").replace("top.html", f"{extend['id']}.html")
            if url == tid: url = f"{tid.rsplit('/', 1)[0]}/{extend['id']}.html"

        if pg > 1:
            sep = "/" if any(x in url for x in ["/singerlist/", "/radiolist/", "/mvlist/", "/playtype/", "/list/"]) else "_"
            url = re.sub(r'(_\d+|/\d+)?\.html$', f'{sep}{pg}.html', url)
        
        doc = self.getpq(url)
        
        selectors = [
            ".play_list.mt li",
            ".play_list li", 
            ".singer_list li",
            ".video_list li",
            ".video_list .play li",
            "ul.play li",
            "div.list li",
            ".song_list li",
            ".music_list li",
            ".pic_list li",
            ".ali li",
            ".layui-row li",
            ".base_l li",
        ]
        
        items = None
        for sel in selectors:
            temp = doc(sel)
            if temp and temp.length > 0:
                has_valid = False
                for li in temp.items():
                    all_links = li("a")
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        href = a.attr("href") or ""
                        if re.search(r'/(m|s|p|a|v|song|singer|playlist|album|mv|video|play|mp3|radio)/', href) and re.search(r'\.(html|php)', href):
                            if not any(x in href for x in ["/user/", "/login/", "javascript:", "void(", "/list/"]):
                                has_valid = True
                                break
                    if has_valid:
                        break
                if has_valid:
                    items = temp
                    break
        
        if items is None:
            for sel in selectors:
                temp = doc(sel)
                if temp and temp.length > 0:
                    items = temp
                    break
        
        if items is None:
            items = doc("li")
        
        result = self._parse_list(items, tid)
        return {"list": result, "page": pg, "pagecount": 9999, "limit": 90, "total": 999999}

    def searchContent(self, key, quick, pg="1"):
        return {"list": self._parse_list(self.getpq(f"/so/{quote(key)}/{pg}.html")(".base_l li, .play_list li"), "search"), "page": int(pg)}

    def detailContent(self, ids):
        url = self._abs(ids[0])
        doc = self.getpq(url)
        
        is_singer = "/s/" in url or "/singer/" in url
        is_playlist = "/p/" in url or "/playlist/" in url or "/playtype/" in url
        is_album = "/a/" in url or "/album/" in url
        is_mv = "/v/" in url or "/mv/" in url or "/video/" in url or "/mp4/" in url
        is_list_page = is_singer or is_playlist or is_album
        
        vod_name = self._clean(doc("h1").text() or doc(".singer_info h1").text() or doc("title").text())
        vod_pic = self._abs(doc(".djpic img, .pic img, .djpg img, .singer_info img").attr("src"))
        
        vod = {
            "vod_id": url, 
            "vod_name": vod_name, 
            "vod_pic": vod_pic, 
            "vod_play_from": "爱听音乐", 
            "vod_content": ""
        }

        if is_list_page:
            eps = self._get_eps(doc)
            page_urls = {self._abs(a.attr("href")) for a in doc(".page a, .dede_pages a, .pagelist a").items() if a.attr("href") and "javascript" not in a.attr("href")} - {url}
            if page_urls:
                with ThreadPoolExecutor(max_workers=5) as ex:
                    for r in as_completed([ex.submit(lambda u: self._get_eps(self.getpq(u)), u) for u in sorted(page_urls, key=lambda x: int(re.search(r'[_\/](\d+)\.html', x).group(1)) if re.search(r'[_\/](\d+)\.html', x) else 0)]):
                        eps.extend(r.result() or [])
            if eps:
                if is_singer:
                    vod["vod_play_from"] = "歌手歌曲"
                elif is_playlist:
                    vod["vod_play_from"] = "歌单歌曲"
                elif is_album:
                    vod["vod_play_from"] = "专辑歌曲"
                else:
                    vod["vod_play_from"] = "播放列表"
                vod["vod_play_url"] = "#".join(eps)
                return {"list": [vod]}

        play_list = []
        if mid := re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', url):
            lrc_url = f"{self.host}/plug/down.php?ac=music&lk=lrc&id={mid.group(2)}"
            play_list = [f"播放${self.e64('0@@@@' + url + '|||' + lrc_url)}"]
        
        elif is_mv:
            vid_match = re.search(r'/(v|video|mp4|mv)/([^/]+)\.html', url)
            if vid_match:
                vid = vid_match.group(2)
                try:
                    mv_urls = self._get_mv_urls(doc, vid)
                    for qn, u in mv_urls:
                        play_list.append(f"{qn}${self.e64('0@@@@'+u+'|||'+url)}")
                except:
                    pass

        vod["vod_play_url"] = "#".join(play_list) if play_list else f"解析失败${self.e64('1@@@@'+url)}"
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = self.d64(id).split("@@@@")[-1]
        url, subt = raw.split("|||") if "|||" in raw else (raw, "")
        url = url.replace(r"\/", "/")
        
        is_mv_url = "ac=vplay" in url or (subt and any(x in subt for x in ["/v/", "/mv/", "/video/", "/mp4/"]))
        
        if ".html" in url and not self.isVideoFormat(url):
            if mid := re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', url):
                if r_url := self._api("/js/play.php", method="POST", data={"id": mid.group(2), "type": "music"}, headers={"Referer": url.replace("http://","https://"), "X-Requested-With": "XMLHttpRequest"}):
                    url = r_url if ".php" not in r_url else url
            elif vid := re.search(r'/(v|video|mp4|mv)/([^/]+)\.html', url):
                vid_id = vid.group(2)
                found = False
                for q in [1080, 720, 480, 420]:
                    if v_url := self._api("/plug/down.php", {"ac": "vplay", "id": vid_id, "q": q}):
                        url = v_url
                        found = True
                        break
                if not found:
                    try:
                        doc = self.getpq(url)
                        mv_urls = self._get_mv_urls(doc, vid_id)
                        if mv_urls:
                            for _, u in mv_urls:
                                if self.isVideoFormat(u):
                                    url = u
                                    found = True
                                    break
                    except:
                        pass
        
        if is_mv_url and not self.isVideoFormat(url):
            try:
                resolved = self._resolve_mv_url(url, subt or self.host + "/")
                if resolved and resolved != url and self.isVideoFormat(resolved):
                    url = resolved
            except:
                pass
        
        if is_mv_url and not self.isVideoFormat(url) and subt and ".html" in subt:
            try:
                doc = self.getpq(subt)
                html = doc.html() or ""
                video_patterns = [
                    r'video\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                    r'url\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                    r'src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                    r'<video[^>]*src=["\']([^"\']+)["\']',
                ]
                for pat in video_patterns:
                    matches = re.findall(pat, html, re.I)
                    for match in matches:
                        full_url = self._abs(match)
                        if full_url and self.isVideoFormat(full_url):
                            url = full_url
                            break
                    if self.isVideoFormat(url):
                        break
            except:
                pass
        
        result_headers = self.headers.copy()
        if is_mv_url:
            result_headers["Referer"] = subt if subt else (self.host + "/")
            result_headers["Accept"] = "*/*"
            result_headers["Accept-Language"] = "zh-CN,zh;q=0.9"
        else:
            if "22a5.com" in url: result_headers["Referer"] = self.host + "/"
        
        result = {"parse": 0, "url": url, "header": result_headers}
        
        if subt and not is_mv_url:
            try:
                r = self.session.get(subt, headers={"Referer": self.host + "/"}, timeout=5)
                lrc_content = r.text
                if lrc_content:
                    lrc_content = self._filter_lrc_ads(lrc_content)
                    result["lrc"] = lrc_content
            except:
                pass
            
        return result

    def _filter_lrc_ads(self, lrc_text):
        """过滤LRC歌词中的广告内容"""
        lines = lrc_text.splitlines()
        filtered_lines = []
        
        # 广告关键词模式
        ad_patterns = [
            r'欢迎来访.*',
            r'本站.*',
            r'.*广告.*',
            r'QQ群.*',
            r'.*www\..*',
            r'.*http.*',
            r'.*\.com.*',
            r'.*\.cn.*',
            r'.*\.net.*',
            r'.*音乐网.*',
            r'.*提供.*',
            r'.*下载.*',
        ]
        
        for line in lines:
            # 保留时间标签行，但过滤掉广告文本
            if re.match(r'\[\d{2}:\d{2}', line):
                # 检查是否包含广告
                is_ad = False
                for pattern in ad_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_ad = True
                        break
                
                if not is_ad:
                    filtered_lines.append(line)
            else:
                # 非时间标签行（可能是元数据），保留
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    def localProxy(self, param):
        url = unquote(param.get("url", ""))
        type_ = param.get("type")
        
        if type_ == "img":
            return [200, "image/jpeg", self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5).content, {}]
        
        elif type_ == "lrc":
            try:
                r = self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5)
                # 同时过滤代理中的广告
                lrc_content = r.text
                lrc_content = self._filter_lrc_ads(lrc_content)
                return [200, "application/octet-stream", lrc_content.encode('utf-8'), {}]
            except:
                return [404, "text/plain", "Error", {}]
                
        return None

    def _parse_list(self, items, tid=""):
        res = []
        seen = set()
        for li in items.items():
            try:
                all_links = li("a")
                href = ""
                name = ""
                pic = ""
                
                for i in range(all_links.length):
                    a = all_links.eq(i)
                    h = a.attr("href") or ""
                    if not h or h == "/" or h.startswith("#"):
                        continue
                    if any(x in h for x in ["/user/", "/login/", "javascript:", "void(", "/list/"]):
                        continue
                    
                    is_content_link = bool(re.search(r'\.(html|php)', h)) and bool(re.search(r'/(m|s|p|a|v|song|singer|playlist|album|mv|video|play|mp3|radio|special)/', h))
                    
                    if is_content_link:
                        href = h
                        name = a.attr("title") or a.text()
                        break
                
                if not href:
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        h = a.attr("href") or ""
                        if not h or h == "/" or h.startswith("#"):
                            continue
                        if any(x in h for x in ["/user/", "/login/", "javascript:", "void("]):
                            continue
                        if re.search(r'\.(html|php)', h):
                            href = h
                            name = a.attr("title") or a.text()
                            break
                
                if not href:
                    continue
                
                abs_href = self._abs(href)
                if abs_href in seen:
                    continue
                seen.add(abs_href)
                
                is_singer = "/s/" in href or "/singer/" in href
                is_playlist = "/p/" in href or "/playlist/" in href or "/playtype/" in href
                is_album = "/a/" in href or "/album/" in href
                is_mv = "/v/" in href or "/mv/" in href or "/video/" in href or "/mp4/" in href
                is_song = "/m/" in href or "/song/" in href or "/mp3/" in href or "/play/" in href
                
                name_el = li(".name, .title, .songname, .mvname, .singername")
                if name_el and name_el.text():
                    name = name_el.text()
                
                name = self._clean(name)
                if not name or len(name) < 1:
                    continue
                
                if "$" in name:
                    name = name.replace("$", "")
                
                img = li("img")
                if img:
                    pic = self._abs((img.attr("src") or img.attr("data-src") or img.attr("data-original") or img.attr("data-lazy-src") or ""))
                    if pic:
                        pic = pic.replace('f120', 'f500').replace('f200', 'f500').replace('f170', 'f500').replace('120x120', '500x500').replace('200x200', '500x500')
                
                vod_tag = "folder" if any([is_singer, is_playlist, is_album]) else ""
                
                style_type = "oval" if is_singer else "rect"
                style_ratio = 1 if is_singer else (1.2 if is_mv else 1.33)
                
                item = {
                    "vod_id": abs_href, 
                    "vod_name": name, 
                    "vod_pic": f"{self.getProxyUrl()}&url={quote(pic)}&type=img" if pic else "", 
                    "vod_tag": vod_tag,
                    "style": {
                        "type": style_type, 
                        "ratio": style_ratio
                    }
                }
                res.append(item)
            except Exception as e:
                continue
        return res

    def _get_eps(self, doc):
        eps = []
        seen = set()
        selectors = ".play_list li, .play_list.mt li, .song_list li, .music_list li, .lkmusic_list li"
        
        for li in doc(selectors).items():
            try:
                all_links = li("a")
                href = ""
                for i in range(all_links.length):
                    a = all_links.eq(i)
                    h = a.attr("href") or ""
                    if re.search(r'/(song|mp3|radio|radiolist|radioplay)/', h):
                        href = h
                        break
                
                if not href:
                    continue
                
                song_match = re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', href)
                if not song_match:
                    continue
                
                full_url = self._abs(href)
                if full_url in seen:
                    continue
                seen.add(full_url)
                
                lrc_part = ""
                mid = song_match.group(2)
                lrc_url = f"{self.host}/plug/down.php?ac=music&lk=lrc&id={mid}"
                lrc_part = f"|||{lrc_url}"
                
                name_el = li(".name")
                song_name = self._clean(name_el.text() if name_el else "" or all_links.eq(0).text() or all_links.eq(0).attr("title"))
                if not song_name:
                    continue
                
                eps.append(f"{song_name}${self.e64('0@@@@' + full_url + lrc_part)}")
            except:
                continue
        
        return eps

    def _clean(self, text): return re.sub(r'(爱玩音乐网|爱听音乐|视频下载说明|视频下载地址|www\.2t58\.com|www\.22a5\.com|MP3免费下载|LRC歌词下载|全部歌曲|\[第\d+页\]|刷新|每日推荐|最新|热门|推荐|MV|高清|无损)', '', text or "", flags=re.I).strip()

    def _get_mv_urls(self, doc, vid):
        urls = []
        html = doc.html() or ""
        
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
                full_url = self._abs(url)
                if full_url and self.isVideoFormat(full_url):
                    urls.append((name, full_url))
        
        if not urls:
            video_patterns = [
                r'video\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                r'url\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                r'src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8|flv))[^"\']*["\']',
                r'<video[^>]*src=["\']([^"\']+)["\']',
            ]
            for pat in video_patterns:
                matches = re.findall(pat, html, re.I)
                for match in matches:
                    full_url = self._abs(match)
                    if full_url and self.isVideoFormat(full_url):
                        if not any(u == full_url for _, u in urls):
                            urls.append(("高清", full_url))
                        break
                if urls:
                    break
        
        if not urls:
            qualities = [("蓝光", 1080), ("超清", 720), ("高清", 480), ("标清", 420)]
            for name, q in qualities:
                u = f"{self.host}/plug/down.php?ac=vplay&id={vid}&q={q}"
                urls.append((name, u))
        
        if not urls:
            u = f"{self.host}/js/play.php"
            urls.append(("播放", u))
        
        return urls

    def _resolve_mv_url(self, url, referer):
        try:
            headers = {
                "Referer": referer, 
                "User-Agent": self.headers["User-Agent"],
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Range": "bytes=0-",
            }
            r = self.session.get(url, headers=headers, timeout=15, stream=True, allow_redirects=True)
            content_type = r.headers.get("Content-Type", "")
            
            if "video" in content_type or "audio" in content_type or "octet-stream" in content_type:
                return r.url
            
            if "application/vnd.apple.mpegurl" in content_type or "mpegurl" in content_type:
                return r.url
            
            chunk = r.raw.read(4096)
            try:
                chunk_str = chunk.decode("utf-8", errors="ignore")
            except:
                chunk_str = ""
            
            if chunk_str.startswith("#EXTM3U"):
                return r.url
            
            url_match = re.search(r'https?://[^\s"\']+\.(mp4|m3u8|flv|mov|mkv|avi|webm)[^\s"\']*', chunk_str, re.I)
            if url_match:
                return url_match.group(0)
            
            url_match2 = re.search(r'["\']([^"\']+\.(mp4|m3u8|flv)[^"\']*)["\']', chunk_str, re.I)
            if url_match2:
                u = url_match2.group(1)
                if u.startswith("//"):
                    u = "http:" + u
                elif u.startswith("/"):
                    u = self._abs(u)
                return u
            
            return r.url
        except:
            return url

    def _fetch_filters(self, url):
        doc, filters = self.getpq(url), []
        for i, group in enumerate([doc(s) for s in [".ilingku_fl", ".class_list", ".screen_list", ".box_list", ".nav_list"] if doc(s)]):
            opts, seen = [{"n": "全部", "v": "top" if "top" in url else "index"}], set()
            for a in group("a").items():
                if (v := (a.attr("href") or "").split("?")[0].rstrip('/').split('/')[-1].replace('.html','')) and v not in seen:
                    opts.append({"n": a.text().strip(), "v": v}); seen.add(v)
            if len(opts) > 1: filters.append({"key": f"id{i}" if i else "id", "name": "分类", "value": opts})
        return filters

    def _api(self, path, params=None, method="GET", headers=None, data=None):
        try:
            h = self.headers.copy()
            if headers: h.update(headers)
            full_url = f"{self.host}{path}"
            r = (self.session.post if method == "POST" else self.session.get)(full_url, params=params, data=data, headers=h, timeout=10, allow_redirects=False)
            if loc := r.headers.get("Location"): return self._abs(loc.strip())
            ct = r.headers.get("Content-Type", "")
            if "text/html" in ct and "verifyForm" in r.text:
                if self._verify_at_url(full_url):
                    r = (self.session.post if method == "POST" else self.session.get)(full_url, params=params, data=data, headers=h, timeout=10, allow_redirects=False)
                    if loc := r.headers.get("Location"): return self._abs(loc.strip())
                    ct = r.headers.get("Content-Type", "")
            if "application/json" in ct or r.text.strip().startswith("{"):
                try:
                    import json
                    j = json.loads(r.text)
                    result_url = j.get("url", "")
                    if result_url:
                        return self._abs(result_url.replace(r"\/", "/"))
                except:
                    pass
                if r.text.strip().startswith("http"):
                    return r.text.strip()
            return ""
        except: return ""

    def getpq(self, url):
        import time
        abs_url = self._abs(url)
        
        for attempt in range(3):
            try:
                r = self.session.get(abs_url, timeout=15)
                doc = pq(r.text)
                
                has_verify = doc('input[name=csrf_token]').length > 0 and doc('#verifyForm').length > 0
                
                if has_verify and self._verify_attempts < 5:
                    if self._verify_at_url(abs_url):
                        self._verify_attempts += 1
                        continue
                    else:
                        self._verify_attempts += 1
                
                return doc
            except Exception as e:
                time.sleep(0.5)
        
        return pq("<html></html>")

    def _verify_at_url(self, url):
        try:
            r = self.session.get(url, timeout=15)
            doc = pq(r.text)
            
            csrf_token = doc('input[name=csrf_token]').val()
            if not csrf_token:
                return True
            
            post_data = {
                'csrf_token': csrf_token, 
                'human_check': 'on'
            }
            post_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': url,
            }
            
            r2 = self.session.post(
                url, 
                data=post_data, 
                headers=post_headers, 
                timeout=15, 
                allow_redirects=True
            )
            
            doc2 = pq(r2.text)
            still_has_verify = doc2('input[name=csrf_token]').length > 0 and doc2('#verifyForm').length > 0
            
            return not still_has_verify
        except:
            return False

    def _abs(self, url): return url if url.startswith("http") else (f"{self.host}{'/' if not url.startswith('/') else ''}{url}" if url else "")
    def e64(self, text): return b64encode(text.encode("utf-8")).decode("utf-8")
    def d64(self, text): return b64decode(text.encode("utf-8")).decode("utf-8")