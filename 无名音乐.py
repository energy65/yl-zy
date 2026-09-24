import re
import sys
import json
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
        self.host = "https://www.mvmp3.com"
        self.session = Session()
        adapter = adapters.HTTPAdapter(max_retries=Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]), pool_connections=20, pool_maxsize=50)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": "\"Android\"",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        self.session.headers.update(self.headers)

    def getName(self): return "无名音乐"
    def isVideoFormat(self, url): return bool(re.search(r'\.(m3u8|mp4|mp3|m4a|flv)(\?|$)', url or "", re.I))
    def manualVideoCheck(self): return False
    def destroy(self): self.session.close()

    # ==================== 微信信息加密 ====================
    # XOR加密，密钥: wuming_yinyue_2026
    # 解密后: 微信公众号"源力软件汇"，更多优质资源尽在源力捐赠版
    _w_key = [119, 117, 109, 105, 110, 103, 95, 121, 105, 110, 121, 117, 101, 95, 50, 48, 50, 54]  # wuming_yinyue_2026
    _w_full_data = [
        146, 203, 195, 141, 209, 198, 186, 252, 197, 138, 197, 226,
        128, 208, 133, 18, 212, 140, 231, 144, 231, 242, 134, 218,
        240, 157, 210, 216, 159, 196, 226, 125, 221, 140, 190, 208,
        236, 193, 136, 205, 244, 131, 227, 225, 129, 218, 209, 157,
        208, 219, 212, 138, 162, 211, 199, 200, 136, 245, 198, 129,
        229, 233, 140, 228, 226, 147, 232, 207, 218, 133, 146, 209,
        254, 253,
    ]

    def _get_wechat_info(self):
        if not hasattr(self, '_wechat_decrypted'):
            data = bytearray(self._w_full_data)
            key = self._w_key
            for i in range(len(data)):
                data[i] ^= key[i % len(key)]
            self._wechat_decrypted = data.decode('utf-8', errors='ignore')
        return self._wechat_decrypted

    def homeContent(self, filter):
        classes = [
            {"type_name": n, "type_id": i} for n, i in [
                ("歌手", "/singers/index/index.html"),
                ("TOP榜单", "/list/top.html"),
                ("欧美榜单", "/list/ustop.html"),
                ("内地榜单", "/list/ndtop.html"),
                ("日本歌曲", "/list/rbtop.html"),
                ("韩国歌曲", "/list/hgtop.html"),
                ("恋爱的歌", "/list/love.html"),
                ("音乐歌单", "/gdlist/index.html"),
                ("高清MV", "/mvlist/top/1.html"),
            ]
        ]
        filters = {}

        # 歌手分类过滤
        filters["/singers/index/index.html"] = [
            {"key": "area", "name": "地区", "value": [{"n": n, "v": v} for n, v in [
                ("全部", "index"), ("华语", "huayu"), ("韩国", "hanguo"),
                ("日本", "ribrn"), ("欧美", "oumei"), ("其他", "other"),
            ]]},
            {"key": "sex", "name": "性别", "value": [{"n": n, "v": v} for n, v in [
                ("全部", "index"), ("男", "male"), ("女", "girl"), ("组合", "band"),
            ]]},
        ]

        # 歌单分类过滤
        filters["/gdlist/index.html"] = [
            {"key": "cat", "name": "分类", "value": [{"n": n, "v": v} for n, v in [
                ("推荐歌单", "index"), ("热门歌单", "hot"), ("国语经典", "jyjd"),
                ("睡前推荐", "sqtj"), ("纯音精选", "cyjx"), ("运动必备", "ydbb"),
                ("网络伤感", "wlsg"), ("店铺精选", "dpjx"), ("流行专区", "lxzq"),
                ("电子专区", "dyzq"), ("摇滚专区", "ygzq"), ("Soul专区", "soul"),
                ("民谣专区", "myzq"), ("DJ歌曲", "djgq"), ("古典专区", "gdzq"),
                ("乡村专区", "xczq"), ("爵士专区", "jszq"), ("70后", "qlhou"),
                ("80后", "blhou"), ("90后", "jlhou"), ("00后", "llhou"),
            ]]},
        ]

        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self): return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        url = tid

        # 歌手分页歌曲：singer_detail#<base64(/singer/{id})>（参照kg.py artist_detail_）
        # 列表内每首歌 vod_id 均指向该歌手详情，点击进入 detailContent 取全部选集
        if tid.startswith("singer_detail#"):
            return self._singer_category(tid, pg)

        # 兼容旧版直接以歌手URL作为tid的情况
        if "/singers/" not in tid and re.search(r'/singer/\d+', tid) and "/video/" not in tid and "/album/" not in tid:
            m = re.search(r'(/singer/\d+)', tid)
            if m:
                return self._singer_category(f"singer_detail#{self.e64(m.group(1))}", pg)

        # 歌手列表：/singers/{area}/{sex}.html  + 分页 /singers/{area}/{sex}/{page}.html
        if "/singers/" in tid:
            parts = tid.split('/')
            # tid 形如 /singers/index/index.html
            area = extend.get("area", "index")
            sex = extend.get("sex", "index")
            if pg == 1:
                url = f"/singers/{area}/{sex}.html"
            else:
                url = f"/singers/{area}/{sex}/{pg}.html"

        # 歌单列表：/gdlist/{cat}.html  + 分页 /gdlist/{cat}/{page}.html
        elif "/gdlist/" in tid:
            cat = extend.get("cat", "index")
            if pg == 1:
                url = f"/gdlist/{cat}.html"
            else:
                url = f"/gdlist/{cat}/{pg}.html"

        # 榜单页 (/list/top, /list/ustop, /list/ndtop, /list/love, /list/rbtop, /list/hgtop)
        elif "/list/" in tid:
            # 提取基础路径：去掉.html后缀，如 /list/top.html -> /list/top
            base_path = tid.replace('.html', '')
            if pg == 1:
                url = tid
            else:
                url = f"{base_path}/{pg}.html"

        # MV列表：/mvlist/top/1.html  + 分页 /mvlist/top/{page}.html
        elif "/mvlist/" in tid:
            base_path = tid.rsplit('/', 1)[0]  # /mvlist/top
            url = f"{base_path}/{pg}.html"

        doc = self.getpq(url)

        # 多选择器回退
        selectors = [
            "ul.play_list li",        # 歌曲列表
            "div.play_list li",
            "ul.lkpic_list li",       # 歌单/专辑列表
            "div.lkpic_list li",
            "ul.ilingku_vlist li",    # MV列表
            "div.ilingku_vlist li",
            "ul.video_list li",       # 歌手视频列表
            "div.video_list li",
            "ul.singer_list li",      # 歌手列表
            "div.singer_list li",
            "ul li",
        ]

        items = None
        for sel in selectors:
            temp = doc(sel)
            if temp and temp.length > 0:
                # 验证至少有一个有效内容链接
                has_valid = False
                for li in temp.items():
                    all_links = li("a")
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        href = a.attr("href") or ""
                        if re.search(r'/(singer|singers|mp3|mp4|playlist|album|mv|video)/', href) and re.search(r'\.html', href):
                            if not any(x in href for x in ["/user/", "/login/", "javascript:", "void(", "/list/", "/gdlist/", "/mvlist/"]):
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
        return {"list": result, "page": pg, "pagecount": 9999, "limit": 30, "total": 999999}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        if pg == 1:
            url = f"/so/{quote(key)}.html"
        else:
            url = f"/so/{quote(key)}/{pg}.html"
        doc = self.getpq(url)
        selectors = ["ul.play_list li", "div.play_list li", "ul li"]
        items = None
        for sel in selectors:
            temp = doc(sel)
            if temp and temp.length > 0:
                items = temp
                break
        if items is None:
            items = doc("li")
        return {"list": self._parse_list(items, "search"), "page": pg}

    def detailContent(self, ids):
        vid = ids[0].strip()

        # 列表来源歌曲：选集为该歌单全部歌曲
        if vid.startswith("lsrc#"):
            return self._detail_list_sourced(vid)

        # 歌手详情：singer_detail#<base64(/singer/{id})>，返回该歌手全部歌曲作为选集
        if vid.startswith("singer_detail#"):
            try:
                base_path = self.d64(vid[len("singer_detail#"):])
            except:
                return {"list": []}
            return self._singer_detail(base_path)

        # 兼容旧版直接以歌手URL进入详情的情况
        m_singer = re.search(r'(/singer/\d+)', vid)
        if m_singer and "/video/" not in vid and "/album/" not in vid and vid.startswith(("http", "/")):
            return self._singer_detail(m_singer.group(1))

        url = self._abs(vid)
        doc = self.getpq(url)

        is_singer = "/singer/" in url and "/video/" not in url and "/album/" not in url
        is_singer_video = "/singer/video/" in url
        is_singer_album = "/singer/album/" in url
        is_playlist = "/playlist/" in url
        is_album = "/album/" in url
        is_song = "/mp3/" in url
        is_mv = "/mp4/" in url
        is_list_page = is_singer or is_singer_video or is_singer_album or is_playlist or is_album

        vod_name = self._clean(doc("h1").text() or doc(".singer_info h1").text() or doc("title").text())
        # 封面优先级
        vod_pic = self._abs(
            doc('meta[property="og:image"]').attr("content") or
            doc(".singer_info img").attr("src") or
            doc(".djpic img").attr("src") or
            doc(".play_singer img").attr("src") or
            doc(".pic img").attr("src") or
            ""
        )

        # 简介中加入微信公众号信息（已加密）
        wechat_info = self._get_wechat_info()
        vod_content = wechat_info

        vod = {
            "vod_id": url,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_play_from": "无名音乐",
            "vod_content": vod_content,
        }

        # 列表页：抓取多页剧集
        if is_list_page:
            # 歌手页面：提取歌手名，过滤掉网站末页填充的其他歌手歌曲
            singer_name = None
            if is_singer or is_singer_video:
                singer_name = self._extract_singer_name(doc)

            eps = self._get_eps(doc, singer_name)
            # 生成全部分页URL（包括分页器未显示的中间页）
            page_urls = self._get_all_page_urls(doc, url)

            # 顺序抓取（requests.Session非线程安全，并发会导致CSRF验证失败）
            for pu in page_urls:
                try:
                    eps.extend(self._get_eps(self.getpq(pu), singer_name) or [])
                except:
                    pass

            if eps:
                # 去重保持顺序
                seen = set()
                unique_eps = []
                for ep in eps:
                    if ep not in seen:
                        seen.add(ep)
                        unique_eps.append(ep)
                if is_singer:
                    source_name = "歌手歌曲"
                elif is_singer_video:
                    source_name = "歌手视频"
                elif is_singer_album:
                    source_name = "歌手专辑"
                elif is_playlist:
                    source_name = "歌单歌曲"
                elif is_album:
                    source_name = "专辑歌曲"
                else:
                    source_name = "播放列表"
                # 音质分类：标准音质$$$高清音质$$$超清音质
                qualities = [source_name, "高清音质", "超清音质"]
                song_list = "#".join(unique_eps)
                vod["vod_play_from"] = "$$$".join(qualities)
                vod["vod_play_url"] = "$$$".join([song_list for _ in qualities])
                return {"list": [vod]}

        # 单曲页：构造播放信息（多音质）
        if is_song:
            song_match = re.search(r'/mp3/([^/]+)\.html', url)
            if song_match:
                payload = self.e64(f"song@@{url}")
                ep = f"{vod_name}${payload}"
                # 音质分类：标准音质$$$高清音质$$$超清音质
                qualities = ["标准音质", "高清音质", "超清音质"]
                vod["vod_play_from"] = "$$$".join(qualities)
                vod["vod_play_url"] = "$$$".join([ep for _ in qualities])
                return {"list": [vod]}

        # MV详情页：标清/高清双线路
        elif is_mv:
            mv_match = re.search(r'/mp4/([^/]+)\.html', url)
            if mv_match:
                payload = self.e64(f"mv@@{url}")
                payload_h = self.e64(f"mv@@{url}@@1")
                vod["vod_play_from"] = "标清$$$高清"
                vod["vod_play_url"] = f"{vod_name}${payload}#{vod_name}高清${payload_h}"
                return {"list": [vod]}

        vod["vod_play_url"] = f"解析失败${self.e64('1@@@' + url)}"
        return {"list": [vod]}

    def _detail_list_sourced(self, vid):
        """列表来源歌曲详情：选集为来源歌单的全部歌曲"""
        try:
            decoded = self.d64(vid[5:])  # 去掉 "lsrc#" 前缀
            parts = decoded.split("@@", 1)
            source_tid = parts[0]
            song_url = parts[1] if len(parts) > 1 else ""
        except:
            return {"list": []}

        # 抓取来源列表页
        doc = self.getpq(source_tid)
        eps = self._get_eps(doc)

        # 生成全部分页URL并顺序抓取
        page_urls = self._get_all_page_urls(doc, self._abs(source_tid))
        for pu in page_urls:
            try:
                eps.extend(self._get_eps(self.getpq(pu)) or [])
            except:
                pass

        # 去重
        seen = set()
        unique_eps = []
        for ep in eps:
            if ep not in seen:
                seen.add(ep)
                unique_eps.append(ep)

        if not unique_eps:
            # 回退到单曲
            url = self._abs(song_url)
            song_doc = self.getpq(url)
            vod_name = self._clean(song_doc("h1").text() or song_doc("title").text())
            payload = self.e64(f"song@@{url}")
            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": self._abs(song_doc('meta[property="og:image"]').attr("content") or ""),
                "vod_content": self._get_wechat_info(),
                "vod_play_from": "标准音质",
                "vod_play_url": f"{vod_name}${payload}",
            }
            return {"list": [vod]}

        # 查找点击歌曲的名称
        song_ep_id = self.e64("song@@" + song_url)
        vod_name = "无名音乐"
        for ep in unique_eps:
            if ep.endswith("$" + song_ep_id):
                vod_name = ep.rsplit("$", 1)[0]
                break

        # 封面
        vod_pic = self._abs(
            doc('meta[property="og:image"]').attr("content") or
            doc(".pic img").attr("src") or
            ""
        )

        # 音质分类
        qualities = ["标准音质", "高清音质", "超清音质"]
        song_list = "#".join(unique_eps)
        vod_play_from = "$$$".join(qualities)
        vod_play_url = "$$$".join([song_list for _ in qualities])

        vod = {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": self._get_wechat_info(),
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url,
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = self.d64(id)
        parts = raw.split("@@")
        content_type = parts[0]
        page_url = parts[1] if len(parts) > 1 else ""
        # MV清晰度参数
        quality = parts[2] if len(parts) > 2 else "0"

        result_headers = self.headers.copy()
        result_headers["Referer"] = self.host + "/"
        result_headers["Accept"] = "*/*"
        result_headers["Accept-Language"] = "zh-CN,zh;q=0.9"

        # ==================== 单曲播放 ====================
        if content_type == "song":
            # 从详情页提取歌曲hash
            song_match = re.search(r'/mp3/([^/]+)\.html', page_url)
            if not song_match:
                return {"parse": 1, "url": page_url, "header": result_headers}
            sid = song_match.group(1)

            result = {"parse": 0, "playUrl": "", "url": "", "header": result_headers}

            # 优先：一次API调用获取 url + lrc
            play_info = self._api_play_full(sid, "dance", page_url)
            play_url = play_info.get("url", "")
            lrc = play_info.get("lrc", "")

            if not play_url or not self.isVideoFormat(play_url):
                # 回退1：调用 /plug/down.php?ac=music 获取302重定向
                redir = self._plug_redirect(f"/plug/down.php?ac=music&id={sid}", page_url)
                if redir and self.isVideoFormat(redir):
                    play_url = redir

            if not play_url or not self.isVideoFormat(play_url):
                # 回退2：TVBox解析器
                return {"parse": 1, "url": page_url, "header": result_headers}

            # 歌词转SSA字幕
            if lrc:
                lrc = self._filter_lrc_ads(lrc)
                ssa = self._create_ssa_subtitle(lrc)
                if ssa:
                    ssa_b64 = b64encode(ssa.encode("utf-8")).decode("utf-8")
                    result["subs"] = [{
                        "name": "歌词",
                        "url": f"data:text/x-ssa;base64,{ssa_b64}",
                        "format": "text/x-ssa",
                        "selected": True,
                    }]

            result["url"] = play_url
            return result

        # ==================== MV播放 ====================
        elif content_type == "mv":
            mv_match = re.search(r'/mp4/([^/]+)\.html', page_url)
            if not mv_match:
                return {"parse": 1, "url": page_url, "header": result_headers}
            vid = mv_match.group(1)

            # 优先：调用 /plug/down.php?ac=mp4&id={vid}&q={q} 获取302重定向到MP4
            for q in [quality, "0", "1", "2", "3"]:
                if not q or q == "0":
                    q = "0"
                redir = self._plug_redirect(f"/plug/down.php?ac=mp4&id={vid}&q={q}", page_url)
                if redir and self.isVideoFormat(redir):
                    result_headers["Referer"] = page_url
                    return {"parse": 0, "url": redir, "header": result_headers}

            # 回退1：调用 /plug/down.php?ac=video 获取302重定向
            for q in ["0", "1", "2", "3"]:
                redir = self._plug_redirect(f"/plug/down.php?ac=video&id={vid}&q={q}&ilingku=dx", page_url)
                if redir and self.isVideoFormat(redir):
                    result_headers["Referer"] = page_url
                    return {"parse": 0, "url": redir, "header": result_headers}

            # 回退2：通过 play.php + AES解密提取URL
            try:
                aes_url = self._get_mv_url_via_aes(vid, page_url)
                if aes_url and self.isVideoFormat(aes_url):
                    result_headers["Referer"] = page_url
                    return {"parse": 0, "url": aes_url, "header": result_headers}
            except:
                pass

            # 回退3：TVBox解析器
            return {"parse": 1, "url": page_url, "header": result_headers}

        # ==================== 通用 ====================
        return {"parse": 1, "url": page_url, "header": result_headers}

    # ==================== 列表解析 ====================
    def _parse_list(self, items, tid=""):
        res = []
        seen = set()
        for li in items.items():
            try:
                all_links = li("a")
                href = ""
                name = ""
                pic = ""

                # 找有效内容链接
                for i in range(all_links.length):
                    a = all_links.eq(i)
                    h = a.attr("href") or ""
                    if not h or h == "/" or h.startswith("#"):
                        continue
                    if any(x in h for x in ["/user/", "/login/", "javascript:", "void(", "/list/", "/gdlist/", "/mvlist/", "/singers/"]):
                        continue
                    # 内容链接：/singer/ /mp3/ /mp4/ /playlist/ /album/
                    is_content_link = bool(re.search(r'\.html', h)) and bool(re.search(r'/(singer|mp3|mp4|playlist|album|mv|video)/', h))
                    if is_content_link:
                        # 跳过 .mv 链接（这些是辅助链接）
                        if a.attr("class") == "mv":
                            continue
                        href = h
                        # 名称优先级：a.title > img.alt > a.text（a.text可能只含时长如"05:08"）
                        name = a.attr("title") or ""
                        if not name:
                            img_el = a.find("img")
                            if img_el.length > 0:
                                name = img_el.attr("alt") or ""
                        if not name:
                            t = a.text() or ""
                            # 过滤纯时长文本（如 "05:08"、"03:00"）
                            if not re.match(r'^\d{1,2}:\d{2}$', t.strip()):
                                name = t
                        break

                # 回退：找任何html链接
                if not href:
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        h = a.attr("href") or ""
                        if not h or h == "/" or h.startswith("#"):
                            continue
                        if any(x in h for x in ["/user/", "/login/", "javascript:", "void(", "/list/", "/gdlist/", "/mvlist/", "/singers/"]):
                            continue
                        if re.search(r'\.html', h) and re.search(r'/(singer|mp3|mp4|playlist|album)/', h):
                            if a.attr("class") == "mv":
                                continue
                            href = h
                            name = a.attr("title") or ""
                            if not name:
                                img_el = a.find("img")
                                if img_el.length > 0:
                                    name = img_el.attr("alt") or ""
                            if not name:
                                t = a.text() or ""
                                if not re.match(r'^\d{1,2}:\d{2}$', t.strip()):
                                    name = t
                            break

                if not href:
                    continue

                abs_href = self._abs(href)
                if abs_href in seen:
                    continue
                seen.add(abs_href)

                is_singer = "/singer/" in href and "/video/" not in href and "/album/" not in href
                is_singer_video = "/singer/video/" in href
                is_singer_album = "/singer/album/" in href
                is_playlist = "/playlist/" in href
                is_album = "/album/" in href
                is_mv = "/mp4/" in href

                # 名称优化：按优先级尝试多个选择器
                # 1. .name a.url (歌曲列表)
                # 2. .name a[title] (歌手/歌单/MV名称链接带title属性)
                # 3. .name a (通用名称链接)
                # 4. a.title[title] (其他带title的链接)
                if not name or not name.strip():
                    for sel in [".name a.url", ".name a[title]", ".name a", "a.title[title]", ".title a[title]"]:
                        try:
                            el = li(sel)
                        except Exception:
                            continue
                        if el and el.length > 0:
                            first = el.eq(0)
                            cand = first.attr("title") or first.text() or ""
                            cand = cand.strip()
                            if cand and not re.match(r'^\d{1,2}:\d{2}$', cand):
                                name = cand
                                break

                name = self._clean(name)
                # 移除搜索结果中的<font>标签高亮
                name = re.sub(r'<[^>]+>', '', name)
                # 规范化空白字符（移除换行、合并多空格）
                name = re.sub(r'\s+', ' ', name).strip()
                if not name or len(name) < 1:
                    continue
                if "$" in name:
                    name = name.replace("$", "")

                # 封面图片
                img = li("img")
                if img:
                    pic = self._abs((img.attr("data-original") or img.attr("data-src") or img.attr("src") or ""))
                    if pic and "nopic" in pic:
                        pic = ""
                    # 升级图片尺寸
                    if pic:
                        pic = (pic.replace('/120/', '/500/')
                                 .replace('f120', 'f500')
                                 .replace('f200', 'f500')
                                 .replace('f170', 'f500')
                                 .replace('120x120', '500x500')
                                 .replace('200x200', '500x500'))

                vod_tag = "folder" if any([is_singer, is_singer_video, is_singer_album, is_playlist, is_album]) else ""
                style_type = "oval" if is_singer else ("rect" if is_mv else "rect")
                style_ratio = 1 if is_singer else (1.2 if is_mv else 1.33)

                # 歌手文件夹：使用 singer_detail# 标记（参照kg.py），
                # categoryContent 返回分页歌曲，detailContent 返回该歌手全部选集
                if is_singer:
                    m = re.search(r'(/singer/\d+)', href)
                    singer_base = m.group(1) if m else href.replace(".html", "")
                    encoded_id = f"singer_detail#{self.e64(singer_base)}"
                # 非folder歌曲项：编码来源列表页URL，使detailContent能获取全部歌曲作为选集
                elif not vod_tag and tid and tid.startswith("/"):
                    encoded_id = f"lsrc#{self.e64(tid + '@@' + abs_href)}"
                else:
                    encoded_id = abs_href

                item = {
                    "vod_id": encoded_id,
                    "vod_name": name,
                    "vod_pic": f"{self.getProxyUrl()}&url={quote(pic)}&type=img" if pic else "",
                    "vod_tag": vod_tag,
                    "style": {
                        "type": style_type,
                        "ratio": style_ratio,
                    }
                }
                res.append(item)
            except Exception as e:
                continue
        return res

    def _get_eps(self, doc, singer_name=None):
        """提取歌曲列表为选集
        singer_name: 歌手名（用于歌手页面过滤掉其他歌手的填充歌曲）
        """
        eps = []
        seen = set()
        # 歌曲列表选择器
        selectors = "ul.play_list li, div.play_list li, ul.lkpic_list li, div.lkpic_list li, ul.ilingku_vlist li, div.ilingku_vlist li, ul.video_list li, div.video_list li"

        for li in doc(selectors).items():
            try:
                all_links = li("a")
                href = ""
                # 优先找 .url 链接（歌曲）或 .mv 链接（MV）
                for i in range(all_links.length):
                    a = all_links.eq(i)
                    h = a.attr("href") or ""
                    cls = a.attr("class") or ""
                    if not h or h == "/" or h.startswith("#"):
                        continue
                    # 歌曲链接：/mp3/ 或 /mp4/
                    if re.search(r'/(mp3|mp4)/[^/]+\.html', h):
                        # .mv 链接优先级低于 .url
                        if cls == "mv":
                            continue
                        href = h
                        break

                # 回退：找任何 mp3/mp4 链接
                if not href:
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        h = a.attr("href") or ""
                        if not h:
                            continue
                        if re.search(r'/(mp3|mp4)/[^/]+\.html', h):
                            cls = a.attr("class") or ""
                            if cls == "mv":
                                continue
                            href = h
                            break

                if not href:
                    continue

                full_url = self._abs(href)
                if full_url in seen:
                    continue
                seen.add(full_url)

                # 提取歌曲名
                name_el = li(".name a.url, .name a, .url, a.url")
                song_name = ""
                if name_el and name_el.length > 0:
                    song_name = name_el.eq(0).text() or name_el.eq(0).attr("title") or ""

                if not song_name:
                    # 从所有链接中找 .url 或第一个有效链接的title
                    for i in range(all_links.length):
                        a = all_links.eq(i)
                        cls = a.attr("class") or ""
                        if "url" in cls:
                            song_name = a.text() or a.attr("title") or ""
                            if song_name:
                                break

                song_name = self._clean(song_name)
                # 移除<font>标签
                song_name = re.sub(r'<[^>]+>', '', song_name)
                # 规范化空白字符
                song_name = re.sub(r'\s+', ' ', song_name).strip()
                if not song_name:
                    continue

                # 歌手页面过滤：只保留该歌手的歌曲（网站末页会填充其他歌手的歌曲）
                if singer_name and not self._is_song_by_singer(song_name, singer_name):
                    continue

                eps.append(f"{song_name}${self.e64('song@@' + full_url)}")
            except:
                continue
        return eps

    def _is_song_by_singer(self, song_name, singer_name):
        """检查歌曲是否属于该歌手
        歌曲名格式: "{artist} - {song}" 或 "{artist1}、{artist2} - {song}"（合作）
        """
        if not singer_name or not song_name:
            return True
        if " - " in song_name:
            artist_part = song_name.split(" - ", 1)[0].strip()
            # 按合作分隔符拆分，检查是否包含该歌手
            artists = re.split(r'[、/,，;；&+]+', artist_part)
            for artist in artists:
                if artist.strip() == singer_name:
                    return True
            return False
        # 无分隔符，检查歌曲名是否以歌手名开头
        return song_name.startswith(singer_name)

    def _extract_singer_name(self, doc):
        """从歌手页面提取歌手名"""
        # 优先从 .singer_info h1 提取
        h1 = doc(".singer_info h1")
        if h1.length and h1.text().strip():
            return self._clean(h1.text().strip())
        # 从第一个 h1 提取（排除"最新歌曲"等section标题）
        h1_all = doc("h1")
        for i in range(h1_all.length):
            text = h1_all.eq(i).text().strip()
            if text and text not in ("最新歌曲", "最新视频", "最新专辑"):
                return self._clean(text)
        # 从 title 提取：格式 "许嵩,许嵩资料,许嵩最新歌曲,..."
        title = doc("title").text() or ""
        if title:
            first_part = title.split(",")[0].strip()
            if first_part:
                return self._clean(first_part)
        return None

    def _get_max_page(self, doc):
        """从分页器提取最大页码（尾页链接）"""
        max_page = 1
        for a in doc(".page a, .pagelist a, .dede_pages a").items():
            h = a.attr("href") or ""
            text = (a.text() or "").strip()
            if "尾页" in text or "last" in text.lower() or "末页" in text:
                m = re.search(r'(\d+)\.html', h)
                if m:
                    max_page = max(max_page, int(m.group(1)))
            if text.isdigit():
                max_page = max(max_page, int(text))
        return max_page

    def _parse_singer_songs(self, doc, singer_name=None):
        """解析歌手页面的歌曲列表，返回 [{name, url, pic}]（页内去重）
        singer_name 存在时仅保留该歌手的歌曲（过滤网站末页填充的他人歌曲）
        """
        songs = []
        seen = set()
        for li in doc("ul.play_list li, div.play_list li").items():
            try:
                # 歌曲链接
                a = li.find(".name a.url, .name a").eq(0)
                href = ""
                if a.length:
                    href = a.attr("href") or ""
                if not href or not re.search(r'/mp3/\w+\.html', href):
                    al = li.find("a[href*='/mp3/']")
                    if not al.length:
                        continue
                    a = al.eq(0)
                    href = a.attr("href") or ""
                if not href:
                    continue
                full_url = self._abs(href)
                if full_url in seen:
                    continue

                # 歌曲名 "歌手 - 歌名"
                name = a.text() or a.attr("title") or ""
                name = re.sub(r'<[^>]+>', '', self._clean(name))
                name = re.sub(r'\s+', ' ', name).strip()
                if not name:
                    continue

                # 过滤非该歌手的填充歌曲
                if singer_name and not self._is_song_by_singer(name, singer_name):
                    continue

                seen.add(full_url)

                # 封面
                pic = ""
                img = li.find("img")
                if img.length:
                    pic = self._abs(img.attr("data-original") or img.attr("data-src") or img.attr("src") or "")
                    if pic and "nopic" in pic:
                        pic = ""
                    if pic:
                        pic = (pic.replace('/120/', '/500/')
                                  .replace('f120', 'f500').replace('f200', 'f500')
                                  .replace('120x120', '500x500').replace('200x200', '500x500'))

                songs.append({"name": name, "url": full_url, "pic": pic})
            except:
                continue
        return songs

    def _singer_category(self, marker, pg):
        """歌手分页歌曲列表（参照kg.py _get_artist_songs）
        每首歌 vod_id 均为该歌手 marker，点击进入 detailContent 获取全部选集
        """
        try:
            base_path = self.d64(marker[len("singer_detail#"):])
        except:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 30, "total": 0}

        page_url = f"{base_path}/{pg}.html"
        doc = self.getpq(page_url)
        singer_name = self._extract_singer_name(doc)
        pagecount = self._get_max_page(doc)

        vods = []
        for sg in self._parse_singer_songs(doc, singer_name):
            vods.append({
                "vod_name": sg["name"],
                "vod_id": marker,
                "vod_pic": f"{self.getProxyUrl()}&url={quote(sg['pic'])}&type=img" if sg["pic"] else "",
                "vod_remarks": "无名音乐",
            })
        return {"list": vods, "page": pg, "pagecount": pagecount, "limit": 30, "total": 9999}

    def _singer_detail(self, base_path):
        """歌手详情：抓取所有分页，返回该歌手全部歌曲作为选集（参照kg.py _get_artist_detail）"""
        first_url = f"{base_path}/1.html"
        doc = self.getpq(first_url)
        singer_name = self._extract_singer_name(doc)
        max_page = self._get_max_page(doc)

        all_songs = []
        seen = set()
        for p in range(1, max_page + 1):
            pdoc = doc if p == 1 else self.getpq(f"{base_path}/{p}.html")
            new_count = 0
            for sg in self._parse_singer_songs(pdoc, singer_name):
                if sg["url"] not in seen:
                    seen.add(sg["url"])
                    all_songs.append(sg)
                    new_count += 1
            # 末页被网站填充他人歌曲时过滤后为0，提前结束（参照kg.py new_count==0 break）
            if p > 1 and new_count == 0 and all_songs:
                break

        wechat_info = self._get_wechat_info()

        if not all_songs:
            vod = {
                "vod_id": f"singer_detail#{self.e64(base_path)}",
                "vod_name": singer_name or "歌手",
                "vod_pic": "",
                "vod_content": wechat_info,
                "vod_play_from": "无名音乐",
                "vod_play_url": f"解析失败${self.e64('1@@@' + self._abs(first_url))}",
            }
            return {"list": [vod]}

        play_arr = [f'{sg["name"]}${self.e64("song@@" + sg["url"])}' for sg in all_songs]
        pic_arr = [sg["pic"] for sg in all_songs]
        song_list = "#".join(play_arr)

        # 歌手封面
        singer_pic = self._abs(
            doc('meta[property="og:image"]').attr("content") or
            doc(".singer_info img").attr("src") or
            (pic_arr[0] if pic_arr else "")
        )

        qualities = ["歌手歌曲", "高清音质", "超清音质"]
        vod = {
            "vod_id": f"singer_detail#{self.e64(base_path)}",
            "vod_name": singer_name or "歌手",
            "vod_pic": singer_pic,
            "vod_content": wechat_info + f"\n共 {len(play_arr)} 首歌曲",
            "vod_remarks": f"歌曲 : {len(play_arr)}首",
            "vod_actor": singer_name or "",
            "vod_play_from": "$$$".join(qualities),
            "vod_play_url": "$$$".join([song_list for _ in qualities]),
            "vod_play_pic": "$$$".join(["#".join(pic_arr) for _ in qualities]),
            "vod_play_pic_ratio": 1.0,
        }
        return {"list": [vod]}

    def _get_all_page_urls(self, doc, current_url):
        """生成分页URL列表，包括分页器未显示的中间页"""
        page_urls = set()
        max_page = 1

        # 从分页链接提取最大页码
        for a in doc(".page a, .pagelist a, .dede_pages a").items():
            h = a.attr("href") or ""
            text = a.text().strip()
            if not h or "javascript" in h or h == "#":
                continue
            page_urls.add(self._abs(h))
            # 尾页/最后页包含最大页码
            if "尾页" in text or "last" in text.lower() or "末页" in text:
                m = re.search(r'(\d+)\.html', h)
                if m:
                    max_page = max(max_page, int(m.group(1)))
            # 数字页签
            if text.isdigit():
                max_page = max(max_page, int(text))

        # 如果最大页码>1，生成所有中间页URL
        if max_page > 1 and page_urls:
            sample_url = None
            for u in page_urls:
                if re.search(r'/\d+\.html', u):
                    sample_url = u
                    break
            if sample_url:
                for p in range(2, max_page + 1):
                    generated = re.sub(r'/\d+\.html$', f'/{p}.html', sample_url)
                    if generated != current_url:
                        page_urls.add(generated)

        page_urls.discard(current_url)
        return sorted(page_urls, key=lambda u: int(re.search(r'/(\d+)\.html', u).group(1))
                       if re.search(r'/(\d+)\.html', u) else 0)

    # ==================== API调用 ====================
    def _api_play_full(self, sid, ptype, referer):
        """一次API调用获取 url + pic + lrc"""
        result = {"url": "", "pic": "", "lrc": ""}
        try:
            r = self.session.post(
                f"{self.host}/style/js/play.php",
                data={"id": sid, "type": ptype},
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            )
            ct = r.headers.get("Content-Type", "")
            if "json" in ct or r.text.strip().startswith("{"):
                try:
                    j = json.loads(r.text)
                    url = j.get("url") or ""
                    if url:
                        result["url"] = url.replace(r"\/", "/")
                    result["pic"] = j.get("pic") or ""
                    result["lrc"] = j.get("lrc") or ""
                except:
                    pass
        except:
            pass
        return result

    def _format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _create_ssa_subtitle(self, lrc_text):
        """LRC转SSA字幕格式（5行歌词显示）"""
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

        events = []
        for i in range(len(lines)):
            current = lines[i]
            current_end = lines[i+1]['start'] if i+1 < len(lines) else current['start'] + 5.0

            wait2 = lines[i+2] if i+2 < len(lines) else None
            wait1 = lines[i+1] if i+1 < len(lines) else None
            played1 = lines[i-1] if i-1 >= 0 else None
            played2 = lines[i-2] if i-2 >= 0 else None

            start_str = self._format_time(current['start'])
            end_str = self._format_time(current_end)

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

    def _api_play(self, sid, ptype, referer):
        """调用 /style/js/play.php POST API 获取播放URL"""
        try:
            r = self.session.post(
                f"{self.host}/style/js/play.php",
                data={"id": sid, "type": ptype},
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            )
            ct = r.headers.get("Content-Type", "")
            if "json" in ct or r.text.strip().startswith("{"):
                try:
                    j = json.loads(r.text)
                    url = j.get("url") or ""
                    if url:
                        return url.replace(r"\/", "/")
                except:
                    pass
            return ""
        except:
            return ""

    def _fetch_lrc_via_play(self, sid, ptype, referer):
        """通过 play.php API 获取LRC歌词"""
        try:
            r = self.session.post(
                f"{self.host}/style/js/play.php",
                data={"id": sid, "type": ptype},
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            )
            if "json" in r.headers.get("Content-Type", "") or r.text.strip().startswith("{"):
                j = json.loads(r.text)
                return j.get("lrc", "") or ""
        except:
            pass
        return ""

    def _plug_redirect(self, path, referer):
        """调用 /plug/down.php 系列接口，跟随302重定向获取真实URL"""
        try:
            full_url = self._abs(path)
            r = self.session.get(
                full_url,
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "*/*",
                },
                timeout=15,
                allow_redirects=False,
            )
            loc = r.headers.get("Location", "")
            if loc:
                loc = loc.strip()
                # 过滤"清晰度没有"等错误提示
                if re.search(r'https?://', loc):
                    return loc
            return ""
        except:
            return ""

    def _get_mv_url_via_aes(self, vid, referer):
        """通过 play.php + AES解密 获取MV URL（备用方案）"""
        try:
            r = self.session.post(
                f"{self.host}/style/js/play.php",
                data={"id": vid, "type": "mp4"},
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            )
            if r.text.strip().startswith("{"):
                j = json.loads(r.text)
                enc_list = j.get("list") or ""
                if not enc_list:
                    return ""
                # AES-128-CBC解密
                try:
                    dec = self._aes_decrypt(enc_list)
                    if dec:
                        # 提取 /plug/down.php?ac=mp4&id=xxx&q=N 链接并跟随重定向
                        plug_match = re.search(r'/plug/down\.php\?ac=mp4&id=[^&\'"]+&q=\d+', dec)
                        if plug_match:
                            return self._plug_redirect("/" + plug_match.group(0), referer) or ""
                        # 或直接找视频URL
                        url_match = re.search(r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|flv)', dec, re.I)
                        if url_match:
                            return url_match.group(0)
                except:
                    pass
            return ""
        except:
            return ""

    def _aes_decrypt(self, enc_str):
        """AES-128-CBC解密 play.php 返回的 list 字段"""
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
        except ImportError:
            try:
                # cryptography库
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.primitives import padding as crypto_padding
                key = b"52c7f81cd24c9699"
                iv = b"42e07d2f7199c35d"
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
                dec = cipher.decryptor()
                ct = b64decode(enc_str.encode('utf-8'))
                pt = dec.update(ct) + dec.finalize()
                unpadder = crypto_padding.PKCS7(128).unpadder()
                pt = unpadder.update(pt) + unpadder.finalize()
                return pt.decode('utf-8', errors='ignore')
            except:
                return ""
        key = b"52c7f81cd24c9699"
        iv = b"42e07d2f7199c35d"
        try:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            ct = b64decode(enc_str.encode('utf-8'))
            pt = unpad(cipher.decrypt(ct), AES.block_size)
            return pt.decode('utf-8', errors='ignore')
        except:
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                ct = b64decode(enc_str.encode('utf-8'))
                pt = cipher.decrypt(ct)
                pad_len = pt[-1]
                if 1 <= pad_len <= 16:
                    pt = pt[:-pad_len]
                return pt.decode('utf-8', errors='ignore')
            except:
                return ""

    # ==================== LRC广告过滤 ====================
    def _filter_lrc_ads(self, lrc_text):
        """过滤LRC歌词中的广告内容"""
        if not lrc_text:
            return lrc_text
        lines = lrc_text.splitlines()
        filtered_lines = []

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
            r'.*mvmp3.*',
            r'.*提供.*',
            r'.*下载.*',
            r'.*无名.*',
        ]

        for line in lines:
            if re.match(r'\[\d{2}:\d{2}', line):
                is_ad = False
                for pattern in ad_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_ad = True
                        break
                if not is_ad:
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    # ==================== 本地代理 ====================
    def localProxy(self, param):
        url = unquote(param.get("url", ""))
        type_ = param.get("type")

        if type_ == "img":
            try:
                r = self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5)
                return [200, "image/jpeg", r.content, {}]
            except:
                return None

        elif type_ == "lrc":
            try:
                r = self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5)
                lrc_content = self._filter_lrc_ads(r.text)
                return [200, "application/octet-stream", lrc_content.encode('utf-8'), {}]
            except:
                return [404, "text/plain", "Error", {}]

        return None

    # ==================== 工具方法 ====================
    def getpq(self, url):
        import time
        abs_url = self._abs(url)

        for attempt in range(5):
            try:
                r = self.session.get(abs_url, timeout=20)
                doc = pq(r.text)

                # 检测CSRF人机验证页
                has_verify = (doc('input[name=csrf_token]').length > 0 and doc('#verifyForm').length > 0) or \
                            ('安全验证' in doc('title').text() and doc('input[type=checkbox][name=human_check]').length > 0)

                if has_verify:
                    csrf_token = doc('input[name=csrf_token]').val()
                    if not csrf_token:
                        csrf_token = doc('input[type=hidden]').val()

                    if csrf_token:
                        post_data = {
                            'csrf_token': csrf_token,
                            'human_check': 'on'
                        }
                        post_headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': abs_url,
                        'Origin': self.host,
                    }
                        self.session.post(abs_url, data=post_data, headers=post_headers, timeout=20, allow_redirects=True)
                        time.sleep(1)
                        continue
                    else:
                        time.sleep(2)
                        continue

                return doc
            except Exception as e:
                time.sleep(1)

        return pq("<html></html>")

    def _clean(self, text):
        return re.sub(
            r'(无名音乐网|无名音乐|视频下载说明|视频下载地址|www\.mvmp3\.com|MP3免费下载|LRC歌词下载|全部歌曲|\[第\d+页\]|刷新|每日推荐|最新|热门|推荐|MV|高清|无损|歌曲列表|歌曲|歌手列表|歌单歌曲列表|专辑歌曲列表)',
            '', text or "", flags=re.I
        ).strip()

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def e64(self, text): return b64encode(text.encode("utf-8")).decode("utf-8")
    def d64(self, text): return b64decode(text.encode("utf-8")).decode("utf-8")
