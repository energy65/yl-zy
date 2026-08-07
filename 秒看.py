# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import html as html_mod
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    # Site URL is XOR-encrypted to avoid plaintext in source
    _w_url_data = [5, 29, 21, 31, 24, 91, 65, 112, 26, 12, 2, 7, 10, 21, 49, 28, 83, 81, 25]
    # WeChat info (full): 微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力
    _w_data = [136, 215, 207, 139, 212, 192, 139, 218, 219, 129, 223, 255, 132, 251, 232, 16, 214, 136, 166, 136, 227, 250, 135, 214, 206, 138, 228, 193, 131, 210, 239, 67, 155, 227, 190, 65, 213, 136, 201, 88, 81, 90, 95, 84, 87, 109, 70, 80, 81, 140, 221, 192, 182, 168, 191, 212, 173, 217, 140, 197, 245, 143, 221, 246, 183, 195, 205, 139, 221, 229, 146, 229, 162, 213, 130, 139, 136, 245, 201, 137, 209, 241, 139, 213, 236]
    # WeChat info (line): 秒看影视·微信公众号源力软件汇
    _w_line_data = [138, 206, 243, 136, 247, 234, 139, 226, 198, 141, 196, 238, 163, 195, 186, 140, 158, 214, 137, 204, 140, 228, 195, 143, 221, 249, 186, 248, 210, 133, 210, 241, 145, 213, 169, 216, 143, 153, 137, 210, 215, 137, 218, 230]
    _w_key = b"miaokan_wechat_2026"

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    CATEGORIES = [
        {"type_id": "dongzuopian", "type_name": "动作片"},
        {"type_id": "xijupian", "type_name": "喜剧片"},
        {"type_id": "aiqingpian", "type_name": "爱情片"},
        {"type_id": "kehuanpian", "type_name": "科幻片"},
        {"type_id": "kongbupian", "type_name": "恐怖片"},
        {"type_id": "juqingpian", "type_name": "剧情片"},
        {"type_id": "jilupian", "type_name": "纪录片"},
        {"type_id": "zhanzhengpian", "type_name": "战争片"},
        {"type_id": "qihuanpian", "type_name": "奇幻片"},
        {"type_id": "xuanyipian", "type_name": "悬疑片"},
        {"type_id": "guochanju", "type_name": "国产剧"},
        {"type_id": "gangtaiju", "type_name": "港台剧"},
        {"type_id": "rihanju", "type_name": "日韩剧"},
        {"type_id": "oumeiju", "type_name": "欧美剧"},
        {"type_id": "haiwaiju", "type_name": "海外剧"},
        {"type_id": "daluzongyi", "type_name": "大陆综艺"},
        {"type_id": "rihanzongyi", "type_name": "日韩综艺"},
        {"type_id": "gangtaizongyi", "type_name": "港台综艺"},
        {"type_id": "oumeizongyi", "type_name": "欧美综艺"},
        {"type_id": "haiwaizongyi", "type_name": "海外综艺"},
        {"type_id": "guochandongman", "type_name": "国产动漫"},
        {"type_id": "rihandongman", "type_name": "日韩动漫"},
        {"type_id": "gangtaidongman", "type_name": "港台动漫"},
        {"type_id": "oumeidongman", "type_name": "欧美动漫"},
        {"type_id": "haiwaidongman", "type_name": "海外动漫"},
        {"type_id": "donghuapian", "type_name": "动画片"},
        {"type_id": "duanju", "type_name": "短剧"},
        {"type_id": "nvpinlianai", "type_name": "女频恋爱"},
        {"type_id": "fanzhuanshuangju", "type_name": "反转爽剧"},
        {"type_id": "guzhuangxianxia", "type_name": "古装仙侠"},
        {"type_id": "niandaichuanyue", "type_name": "年代穿越"},
        {"type_id": "naodongxuanyi", "type_name": "脑洞悬疑"},
        {"type_id": "xiandaidushi", "type_name": "现代都市"},
        {"type_id": "yingshijieshuo", "type_name": "影视解说"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "秒看电影"

    def _xor_decrypt(self, data, key):
        try:
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                result = []
                for i in range(len(data)):
                    result.append(chr(data[i] ^ key[i % len(key)]))
                return ''.join(result)
            except Exception:
                return ''

    def _get_site_url(self):
        return self._xor_decrypt(self._w_url_data, self._w_key) or "https://miaokan.cc/"

    def _get_wechat_info(self):
        return self._xor_decrypt(self._w_data, self._w_key)

    def _get_line_info(self):
        return self._xor_decrypt(self._w_line_data, self._w_key) or "秒看影视"

    def _ssl_ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
        except Exception:
            pass
        return ctx

    def getHtml(self, url, referer=None):
        base = self._get_site_url()
        if not referer:
            referer = base
        ctx = self._ssl_ctx()
        last_err = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": self.UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Referer": referer,
                })
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    data = resp.read()
                    ce = resp.headers.get("Content-Encoding", "")
                    if "gzip" in ce:
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            pass
                    for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                        try:
                            return data.decode(enc)
                        except Exception:
                            continue
                    return data.decode("utf-8", errors="replace")
            except Exception as e:
                last_err = e
        return ""

    def getJson(self, url, referer=None):
        base = self._get_site_url()
        if not referer:
            referer = base
        ctx = self._ssl_ctx()
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": self.UA,
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Referer": referer,
                })
                with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                    data = resp.read()
                    ce = resp.headers.get("Content-Encoding", "")
                    if "gzip" in ce:
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            pass
                    return json.loads(data.decode("utf-8", errors="replace"))
            except Exception:
                continue
        return None

    def _clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r'\s+', ' ', text).strip()

    def _clean_intro(self, text):
        if not text:
            return ""
        text = re.sub(r'@[^@\s]{2,30}@', '', text)
        text = re.sub(r'&copy;[^&<]{0,30}', '', text)
        text = html_mod.unescape(text)
        text = re.sub(r'\.{2,}', '...', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _parse_vod_items(self, html):
        items = []
        seen = set()
        for m in re.finditer(
            r'<li class="col-xs-4 col-md-3 col-lg-2">(.*?)</li>',
            html, re.DOTALL
        ):
            inner = m.group(1)
            link_m = re.search(r'href="(/miaokan/(\d+)/)"', inner)
            if not link_m:
                continue
            vid = link_m.group(2)
            if vid in seen:
                continue
            seen.add(vid)

            title = ""
            title_m = re.search(r'title="([^"]*)"', inner)
            if title_m:
                title = title_m.group(1).strip()
            if not title:
                h3_m = re.search(r'<h3[^>]*>(.*?)</h3>', inner, re.DOTALL)
                if h3_m:
                    title = self._clean(re.sub(r'<[^>]*>', '', h3_m.group(1)))

            img = ""
            img_m = re.search(r'data-original="([^"]*)"', inner)
            if img_m:
                img = img_m.group(1).strip()
            if not img:
                img_m = re.search(r'src="([^"]*)"', inner)
                if img_m and 'load.gif' not in img_m.group(1):
                    img = img_m.group(1).strip()

            remarks = ""
            status_m = re.search(r'<p class="item-status text-overflow">(.*?)</p>', inner, re.DOTALL)
            if status_m:
                remarks = self._clean(re.sub(r'<[^>]*>', '', status_m.group(1)))

            if title:
                items.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": img,
                    "vod_remarks": remarks,
                })
        return items

    def _extract_pagecount(self, html):
        m = re.search(r'<span class="num">\s*\d+\s*/\s*(\d+)\s*</span>', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        m = re.search(r'/mk-kan/[^"]*--------(\d+)---/', html)
        max_pg = 1
        for mm in re.finditer(r'/mk-kan/[^"]*--------(\d+)---/', html):
            try:
                p = int(mm.group(1))
                if p > max_pg:
                    max_pg = p
            except Exception:
                pass
        return max_pg

    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        base = self._get_site_url()
        html = self.getHtml(base)
        if not html:
            return result
        videos = self._parse_vod_items(html)
        wechat_info = self._get_wechat_info()
        for v in videos[:30]:
            if wechat_info:
                v["vod_content"] = wechat_info
        result["list"] = videos[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            base = self._get_site_url()
            page = int(pg) if pg and str(pg).isdigit() else 1
            url = base + "mk-kan/" + str(tid) + "--------" + str(page) + "---/"
            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_vod_items(html)
            wechat_info = self._get_wechat_info()
            cat_name = ""
            for c in self.CATEGORIES:
                if c["type_id"] == str(tid):
                    cat_name = c["type_name"]
                    break
            for v in videos:
                if wechat_info:
                    v["vod_content"] = wechat_info
                v["vod_class"] = cat_name

            pagecount = self._extract_pagecount(html)
            if pagecount < page:
                pagecount = page
            result["list"] = videos
            result["page"] = str(page)
            result["pagecount"] = str(pagecount)
            result["total"] = str(pagecount * 36)
            result["limit"] = "36"
        except Exception:
            pass
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            base = self._get_site_url()
            vid = ids[0] if isinstance(ids, list) and ids else ids
            url = base + "miaokan/" + str(vid) + "/"
            html = self.getHtml(url)
            if not html:
                return result

            title = ""
            h3_m = re.search(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            if h3_m:
                title = self._clean(re.sub(r'<[^>]*>', '', h3_m.group(1)))
            if not title:
                h2_m = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
                if h2_m:
                    cand = self._clean(re.sub(r'<[^>]*>', '', h2_m.group(1)))
                    if cand and cand not in ("播放列表", "猜你喜欢", "用户评论") and "内容简介" not in cand and "排行榜" not in cand:
                        title = cand
            if not title:
                t_m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
                if t_m:
                    raw = t_m.group(1)
                    if "·" in raw:
                        title = raw.split("·")[0].strip()
                    elif "_" in raw:
                        title = raw.split("_")[0].strip()
                    else:
                        title = raw.split("-")[0].strip()
                    title = title.strip("《》")
            if not title:
                title = str(vid)

            pic = ""
            pic_m = re.search(r'<div class="pic">.*?data-original="([^"]*)"', html, re.DOTALL)
            if pic_m:
                pic = pic_m.group(1).strip()
            if not pic:
                pic_m = re.search(r'data-original="(https?://[^"]+(?:\.jpg|\.jpeg|\.png|\.webp|\.gif))', html)
                if pic_m:
                    pic = pic_m.group(1).strip()

            director = ""
            d_m = re.search(r'导演：(.*?)(?:</span>|<br)', html, re.DOTALL)
            if d_m:
                director = self._clean(re.sub(r'<[^>]*>', '', d_m.group(1)))

            cast = ""
            c_m = re.search(r'主演：(.*?)(?:</span>|<br)', html, re.DOTALL)
            if c_m:
                cast = self._clean(re.sub(r'<[^>]*>', '', c_m.group(1)))

            year = ""
            y_m = re.search(r'年份：<a[^>]*>(\d{4})</a>', html)
            if y_m:
                year = y_m.group(1)
            if not year:
                y_m = re.search(r'发行于(\d{4})年', html)
                if y_m:
                    year = y_m.group(1)

            area = ""
            a_m = re.search(r'地区：<a[^>]*>([^<]+)</a>', html)
            if a_m:
                area = self._clean(a_m.group(1))

            cat_name = ""
            cat_m = re.search(r'的一部(.+?)。', html)
            if cat_m:
                cat_name = self._clean(cat_m.group(1))

            intro = ""
            intro_m = re.search(r'<h2>[^<]*内容简介</h2>(.*?)</div>', html, re.DOTALL)
            if intro_m:
                intro = self._clean_intro(re.sub(r'<[^>]*>', ' ', intro_m.group(1)))
            if not intro:
                md_m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
                if md_m:
                    intro = self._clean_intro(re.sub(r'<[^>]*>', '', html_mod.unescape(md_m.group(1))))

            wechat_info = self._get_wechat_info()
            if wechat_info:
                intro = (intro + '\n\n' + wechat_info) if intro else wechat_info

            line_names = []
            for lm in re.finditer(r'<li class="swiper-slide ewave-tab[^"]*"[^>]*data-target="#ewave-playlist-(\d+)"[^>]*>(.*?)</li>', html, re.DOTALL):
                ln = self._clean(re.sub(r'<[^>]*>', '', lm.group(2)))
                line_names.append((lm.group(1), ln if ln else ("线路" + lm.group(1))))

            play_groups = []
            if line_names:
                for sid_key, ln_name in line_names:
                    eps = []
                    ul_m = re.search(
                        r'<ul[^>]*id="ewave-playlist-' + sid_key + r'"[^>]*>(.*?)</ul>',
                        html, re.DOTALL
                    )
                    if ul_m:
                        for em in re.finditer(r'href="(/mkvod/(\d+)-(\d+)-(\d+)/)"[^>]*>(.*?)</a>', ul_m.group(1), re.DOTALL):
                            ep_href = em.group(1)
                            ep_text = self._clean(re.sub(r'<[^>]*>', '', em.group(5)))
                            if not ep_text:
                                ep_text = "第" + str(em.group(4)) + "集"
                            eps.append(ep_text + "$" + ep_href)
                    if eps:
                        play_groups.append((ln_name, eps))

            if not play_groups:
                for em in re.finditer(r'href="(/mkvod/(\d+)-(\d+)-(\d+)/)"[^>]*>(.*?)</a>', html, re.DOTALL):
                    ep_href = em.group(1)
                    ep_text = self._clean(re.sub(r'<[^>]*>', '', em.group(4))) or ("第" + str(em.group(3)) + "集")
                    play_groups.append(("默认线路", [ep_text + "$" + ep_href]))

            if not play_groups:
                play_groups.append(("播放", ["播放$/mkvod/" + str(vid) + "-1-1/"]))

            line_info = self._get_line_info()
            vod_play_from = "$$$".join([g[0] for g in play_groups])
            vod_play_url = "$$$".join(["#".join(g[1]) for g in play_groups])
            if not vod_play_from:
                vod_play_from = line_info

            vod = {
                "vod_id": str(vid),
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": cast,
                "vod_director": director,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": "",
                "vod_content": intro,
                "vod_class": cat_name,
                "type_name": cat_name,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            }
            result["list"] = [vod]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            base = self._get_site_url()
            kw = urllib.parse.quote(key)
            limit = 30 if quick else 30
            url = base + "index.php/ajax/suggest?mid=1&wd=" + kw + "&limit=" + str(limit)
            obj = self.getJson(url)
            if not obj or obj.get("code") != 1:
                return result

            wechat_info = self._get_wechat_info()
            lst = obj.get("list", []) or []
            total = obj.get("total", len(lst))
            pagecount = obj.get("pagecount", 1)
            videos = []
            for it in lst:
                vid = str(it.get("id", ""))
                name = it.get("name", "")
                pic = it.get("pic", "") or ""
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                v = {
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": "",
                }
                if wechat_info:
                    v["vod_content"] = wechat_info
                videos.append(v)

            result["list"] = videos
            result["page"] = "1"
            result["pagecount"] = str(pagecount if pagecount else 1)
            result["total"] = str(total if total else len(videos))
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "url": "", "header": "", "playUrl": "", "subtitle": "", "proxy": ""}
        try:
            base = self._get_site_url()
            if not id:
                return result
            play_url = id if id.startswith("http") else (base + id.lstrip("/"))
            html = self.getHtml(play_url, referer=base)
            if not html:
                return result

            url = ""
            encrypt = 0
            pa_m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
            if not pa_m:
                pa_m = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html, re.DOTALL)
            if pa_m:
                try:
                    pa = json.loads(pa_m.group(1))
                    url = pa.get("url", "") or ""
                    encrypt = pa.get("encrypt", 0) or 0
                except Exception:
                    pass

            if not url:
                m_m = re.search(r'"url"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"', html)
                if m_m:
                    url = m_m.group(1).replace("\\/", "/")
            if not url:
                m_m = re.search(r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)', html)
                if m_m:
                    url = m_m.group(1)

            if url:
                result["url"] = url
                result["parse"] = 0
                result["header"] = json.dumps({
                    "Referer": base,
                    "Origin": base.rstrip("/"),
                    "User-Agent": self.UA,
                })
        except Exception:
            pass
        return result

    def isVip(self, url):
        return False

    def manualCall(self, code, note, url):
        return {}

    def localProxy(self, params):
        return {"url": "", "header": ""}

    def __jsEvalReturn(self):
        return {
            "site": "https://miaokan.cc/",
            "categories": self.CATEGORIES,
            "proxy": None,
        }
