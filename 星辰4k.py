#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星辰4K TVBox Python Spider
网站地址: https://hqvod.com/
标准库实现，仅使用 urllib / ssl / re / json / html，确保可在 TVBox 中运行。
支持首页分类、分类翻页、影片详情（多播放源）、搜索，并在影片简介处附加公众号与Q群信息。
"""

import re
import ssl
import json
import urllib.request
import urllib.parse
import html as html_mod

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
    BASE_URL = "https://hqvod.com"
    WECHAT_INFO = '微信公众号“源力软件汇”，q群1054592152伴随更多优质资源尽在源力'
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # 全部分类（站点导航暴露的主分类）
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "动漫"},
        {"type_id": "4", "type_name": "综艺"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "星辰4K"

    # ------------------------------------------------------------------ utils
    def getHtml(self, url, referer=None):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
                for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
                return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = text.replace("&#183;", "·").replace("&nbsp;", " ").replace("&#xe", "")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def absurl(self, u):
        if not u:
            return ""
        if u.startswith("http"):
            return u
        return self.BASE_URL + ("" if u.startswith("/") else "/") + u

    # ------------------------------------------------------------ list parser
    def parse_video_items(self, html):
        videos = []
        items = re.finditer(
            r'<a[^>]*class="public-list-exp"[^>]*href="(/xiangqing/(\d+)\.html)"[^>]*title="([^"]*)">(.*?)</a>',
            html, re.S)
        for m in items:
            href, vid, name, inner = m.group(1), m.group(2), m.group(3), m.group(4)
            pic_m = re.search(r'data-src="([^"]+)"', inner)
            pic = pic_m.group(1) if pic_m else ""
            if not pic:
                pic_m = re.search(r'src="([^"]+)"', inner)
                pic = pic_m.group(1) if pic_m else ""
            block = html[m.start():m.start() + 1500]
            remark_m = re.search(r'class="public-list-prb[^"]*">([^<]+)<', block)
            remark = self.clean(remark_m.group(1)) if remark_m else ""
            videos.append({
                "vod_id": vid,
                "vod_name": self.clean(name),
                "vod_pic": self.absurl(pic),
                "vod_remarks": remark,
            })
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    # --------------------------------------------------------------- home
    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result
        result["list"] = self.parse_video_items(html)[:30]
        return result

    # ----------------------------------------------------------- category
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        url = f"{self.BASE_URL}/fenlei/{tid}.html"
        if page > 1:
            url = f"{self.BASE_URL}/fenlei/{tid}-{page}.html"
        html = self.getHtml(url)
        if not html:
            return result
        videos = self.parse_video_items(html)
        pagecount = "1"
        if re.search(r'fenlei/%s-\d+\.html' % re.escape(tid), html) or "下一页" in html:
            pagecount = str(page + 1)
        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * max(len(videos), 1)) if videos else "0"
        return result

    # ------------------------------------------------------------- detail
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        vid = str(vid).replace("/xiangqing/", "").replace(".html", "").strip("/")
        if not vid:
            return result
        url = f"{self.BASE_URL}/xiangqing/{vid}.html"
        html = self.getHtml(url)
        if not html:
            return result

        vod = {"vod_id": vid}

        # 标题
        title = ""
        tm = re.search(r"<title>(.*?)</title>", html, re.S)
        if tm:
            raw = self.clean(tm.group(1))
            mm = re.search(r"《(.*?)》", raw)
            title = mm.group(1) if mm else raw.split("_")[0].split("-")[0]
        if not title:
            bm = re.search(r'class="[^"]*vod-name[^"]*"[^>]*>([^<]+)<', html)
            if not bm:
                bm = re.search(r'class="[^"]*title[^"]*"[^>]*>([^<]{2,40})<', html)
            title = self.clean(bm.group(1)) if bm else ""
        vod["vod_name"] = title

        # 封面
        pic_m = re.search(r'data-src="(https?://[^"]+)"', html)
        if not pic_m:
            pic_m = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
        vod["vod_pic"] = pic_m.group(1) if pic_m else ""

        # 元信息
        def grab(label):
            m = re.search(label + r"[:：]\s*</em>\s*(?:<a[^>]*>([^<]+)</a>|([^<]+))", html)
            if not m:
                m = re.search(label + r"[:：]\s*(?:<a[^>]*>([^<]+)</a>|([^<]+))", html)
            if not m:
                return ""
            val = (m.group(1) or m.group(2) or "").strip()
            return self.clean(val)

        vod["type_name"] = grab("类型")
        vod["vod_area"] = grab("地区")
        vod["vod_year"] = grab("年份")
        vod["vod_actor"] = grab("主演")
        vod["vod_director"] = grab("导演")
        vod["vod_lang"] = grab("语言")
        vod["vod_remarks"] = grab("状态") or grab("更新")

        # 简介
        desc_m = re.search(r"简介[:：]\s*([^<]+)", html)
        if not desc_m:
            desc_m = re.search(r"剧情[:：]\s*([^<]+)", html)
        if not desc_m:
            desc_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
        desc = self.clean(desc_m.group(1)) if desc_m else ""
        vod["vod_content"] = (self.WECHAT_INFO + "\n" + desc) if desc else self.WECHAT_INFO

        # 播放源 + 选集
        names = re.findall(
            r'class="swiper-slide"[^>]*>\s*(?:<i[^>]*></i>)?\s*([^<]+?)\s*</a>', html)
        uls = re.findall(r'<ul class="anthology-list-play[^"]*">(.*?)</ul>', html, re.S)

        from_list = []
        url_list = []
        for idx, ul in enumerate(uls):
            source = self.clean(names[idx]) if idx < len(names) else ("线路%d" % (idx + 1))
            if not source:
                source = "线路%d" % (idx + 1)
            eps = re.findall(r'href="(/bofang/[^"]+)"[^>]*>([^<]+)</a>', ul)
            if not eps:
                continue
            ep_parts = []
            for href, ep_name in eps:
                ep_parts.append("%s$%s" % (self.clean(ep_name) or ("第%d集" % (len(ep_parts) + 1)),
                                           self.absurl(href)))
            if ep_parts:
                from_list.append(source)
                url_list.append("#".join(ep_parts))

        if from_list:
            vod["vod_play_from"] = "$$$".join(from_list)
            vod["vod_play_url"] = "$$$".join(url_list)
        else:
            vod["vod_play_from"] = "云播"
            vod["vod_play_url"] = "播放$%s" % (self.BASE_URL + "/bofang/%s-1-1.html" % vid)

        result["list"] = [vod]
        return result

    # -------------------------------------------------------------- search
    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        q = urllib.parse.quote(key)
        url = f"{self.BASE_URL}/sousuo/-------------{q}.html"
        if page > 1:
            url = f"{self.BASE_URL}/sousuo/-------------{q}-{page}.html"
        html = self.getHtml(url)
        if not html:
            return result
        videos = self.parse_video_items(html)
        pagecount = "1"
        if "下一页" in html or re.search(r"sousuo/-------------[^.]+\.html", html):
            pagecount = str(page + 1)
        result["list"] = videos
        result["pagecount"] = pagecount
        result["total"] = str(int(pagecount) * max(len(videos), 1)) if videos else "0"
        return result

    # -------------------------------------------------------------- player
    def playerContent(self, flag, id, vipFlags):
        play_url = str(id)
        if play_url.startswith("$"):
            play_url = play_url[1:]
        # 兼容 "名称$url" 形式
        if "$" in play_url and "http" not in play_url.split("$")[0]:
            parts = play_url.split("$")
            if len(parts) >= 2:
                play_url = parts[-1]
        play_url = self.absurl(play_url)

        vid_m = re.search(r"/bofang/(\d+)-", play_url)
        referer = (self.BASE_URL + "/xiangqing/%s.html" % vid_m.group(1)) if vid_m else self.BASE_URL

        html = self.getHtml(play_url, referer=referer)
        if html:
            # 1) maccms 标准 player 数据
            pm = re.search(r"var\s+player_\w+\s*=\s*(\{.*?\});", html, re.S)
            if pm:
                try:
                    data = json.loads(pm.group(1))
                    u = data.get("url", "")
                    if u:
                        u = u.replace("\\/", "/")
                        return {"url": u, "parse": 0, "header": {"Referer": referer, "User-Agent": self.UA}}
                except Exception:
                    pass
            # 2) mac_url 变量
            um = re.search(r"(?:var\s+)?mac_url\s*=\s*[\"'](.*?)[\"']", html)
            if um:
                u = um.group(1).replace("\\/", "/")
                if u:
                    return {"url": u, "parse": 0, "header": {"Referer": referer, "User-Agent": self.UA}}
            # 3) 直接直链
            dm = re.search(r"https?://[^\s\"'\\]+?\.(?:m3u8|mp4|ts)", html)
            if dm:
                return {"url": dm.group(0), "parse": 0, "header": {"Referer": referer, "User-Agent": self.UA}}

        # 无法直解时交给 TVBox 内置 WebView 处理 JS 挑战
        return {"url": play_url, "parse": 1, "header": {"Referer": referer, "User-Agent": self.UA}}
