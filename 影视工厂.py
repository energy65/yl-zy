# -*- coding: utf-8 -*-
"""
影视工厂 TVBox Spider
网站: https://www.piyaroad.com
站点类型: 综合影视 (电影 / 电视剧 / 综艺 / 动漫 / 短剧)
分类体系 (参照 懂片帝.py 的写法):
  - 一级分类: 站点全部片库分类 (/sgc/{slug}.html)
  - 二级筛选: 类型 / 地区 / 年份 (懂片帝式 filters 结构)
      * 类型: 站内同类片库切换 (电影片库 / 剧集片库 / 综艺片库 / 动漫片库)
      * 地区: /sgc/{slug}/area/{area}.html
      * 年份: /sgc/{slug}/year/{year}.html (支持 2010-2019 等区间)
      * 组合: /sgc/{slug}/area/{area}/year/{year}.html
  - 分页: /sgc/{slug}[/area/x][/year/y]/page/{n}.html (尾页可解析)
播放机制:
  - 详情页提取全部播放线路 (nav-tabs) 与选集 (/pgc/{vid}/{sid}/{eid}.html)
  - 播放页解析 MacCMS player_aaaa JSON, 直接取出 m3u8 直链, parse=0 直连播放
简介: 自动追加微信公众号"源力软件汇"
支持: 首页 / 一二级分类 / 搜索 / 详情 / 播放
"""

import re
import json
import time
import base64
import html as html_mod
import urllib.parse
import urllib.request
import ssl

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=""): pass
        def getName(self): return ""
        def homeContent(self, filter): return {}
        def homeVideoContent(self): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg="1"): return {}
        def searchContentPage(self, key, quick, page): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    HOST = "https://www.piyaroad.com"

    # 微信公众号推广 (添加在影片简介处)
    WX_TEXT = "更多影视资源，请关注微信公众号“源力软件汇”"

    # ==================== 一级分类 (站点全部片库) ====================
    # 每项: (type_id=站内片库 slug, type_name=中文名, 所属片库组)
    CATEGORIES = [
        # 电影片库
        ("dianying", "电影", "movie"),
        ("dongzuopian", "动作片", "movie"),
        ("xijupian", "喜剧片", "movie"),
        ("aiqingpian", "爱情片", "movie"),
        ("kehuanpian", "科幻片", "movie"),
        ("kongbupian", "恐怖片", "movie"),
        ("juqingpian", "剧情片", "movie"),
        ("zhanzhengpian", "战争片", "movie"),
        ("jilupian", "记录片", "movie"),
        ("yugaopian", "预告片", "movie"),
        ("yingshijieshuo", "影视解说", "movie"),
        # 电视剧片库
        ("guochanju", "国产剧", "tv"),
        ("gangju", "港剧", "tv"),
        ("taiju", "台剧", "tv"),
        ("hanju", "韩剧", "tv"),
        ("riju", "日剧", "tv"),
        ("oumeiju", "欧美剧", "tv"),
        ("haiwaiju", "海外剧", "tv"),
        ("duanju", "短剧", "tv"),
        # 综艺片库
        ("zongyi", "综艺", "variety"),
        ("daluzongyi", "大陆综艺", "variety"),
        ("gangtaizongyi", "港台综艺", "variety"),
        ("rihanzongyi", "日韩综艺", "variety"),
        ("oumeizongyi", "欧美综艺", "variety"),
        # 动漫片库
        ("dongman", "动漫", "anime"),
        ("rihandongman", "日韩动漫", "anime"),
        ("guochandongman", "国产动漫", "anime"),
        ("oumeidongman", "欧美动漫", "anime"),
        ("donghuapian", "动画片", "anime"),
    ]

    # 中文名 -> slug (兼容 TVBox 传入 type_name 的情况)
    NAME_TO_SLUG = {name: slug for slug, name, _ in CATEGORIES}
    # 各片库组对应的"类型"筛选 (切换到同组其它片库, 空值=当前分类)
    _TYPES = {
        "movie": [("", "全部"), ("dongzuopian", "动作片"), ("xijupian", "喜剧片"),
                  ("aiqingpian", "爱情片"), ("kehuanpian", "科幻片"), ("kongbupian", "恐怖片"),
                  ("juqingpian", "剧情片"), ("zhanzhengpian", "战争片"), ("jilupian", "记录片"),
                  ("yugaopian", "预告片"), ("yingshijieshuo", "影视解说")],
        "tv": [("", "全部"), ("guochanju", "国产剧"), ("gangju", "港剧"), ("taiju", "台剧"),
               ("hanju", "韩剧"), ("riju", "日剧"), ("oumeiju", "欧美剧"),
               ("haiwaiju", "海外剧"), ("duanju", "短剧")],
        "variety": [("", "全部"), ("daluzongyi", "大陆综艺"), ("gangtaizongyi", "港台综艺"),
                    ("rihanzongyi", "日韩综艺"), ("oumeizongyi", "欧美综艺")],
        "anime": [("", "全部"), ("rihandongman", "日韩动漫"), ("guochandongman", "国产动漫"),
                  ("oumeidongman", "欧美动漫"), ("donghuapian", "动画片")],
    }
    # 各片库组对应的"地区"筛选
    _AREAS = {
        "movie": [("", "全部"), ("大陆", "大陆"), ("香港", "香港"), ("台湾", "台湾"),
                  ("美国", "美国"), ("法国", "法国"), ("英国", "英国"), ("日本", "日本"),
                  ("韩国", "韩国"), ("德国", "德国"), ("泰国", "泰国"), ("印度", "印度"),
                  ("意大利", "意大利")],
        "tv": [("", "全部"), ("内地", "内地"), ("韩国", "韩国"), ("香港", "香港"),
               ("台湾", "台湾"), ("日本", "日本"), ("美国", "美国"), ("泰国", "泰国"),
               ("英国", "英国"), ("新加坡", "新加坡"), ("其他", "其他")],
        "variety": [("", "全部"), ("内地", "内地"), ("港台", "港台"),
                    ("日韩", "日韩"), ("欧美", "欧美")],
        "anime": [("", "全部"), ("国产", "国产"), ("日本", "日本"),
                  ("欧美", "欧美"), ("其他", "其他")],
    }

    def init(self, extend=""):
        self.host = self.HOST
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE
        # 年份筛选: 近 17 年 + 年代区间
        years = [("", "全部")]
        cur = time.localtime().tm_year
        years += [(str(y), str(y)) for y in range(cur, 2009, -1)]
        years += [("2010-2019", "10年代"), ("2000-2009", "00年代"),
                  ("1990-1999", "90年代"), ("1980-1989", "80年代")]
        self._years = years

    def getName(self):
        return "影视工厂"

    # ==================== 基础工具 ====================

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"[ \t\u3000]+", " ", text).strip()

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    def _get(self, path, referer=None):
        """HTTP GET, 返回解码后的 HTML 文本"""
        url = path if path.startswith("http") else self.host + path
        headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if referer:
            headers["Referer"] = referer
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=self._ssl_ctx) as resp:
                    data = resp.read()
                    for enc in ("utf-8", "gbk", "gb2312"):
                        try:
                            return data.decode(enc)
                        except Exception:
                            continue
                    return data.decode("utf-8", errors="replace")
            except Exception:
                if attempt == 0:
                    time.sleep(0.4)
                    continue
                return ""
        return ""

    def _play_header(self):
        return json.dumps({
            "User-Agent": self.UA,
            "Referer": self.host + "/",
        }, ensure_ascii=False)

    # ==================== 列表解析 ====================

    def _parse_cards(self, html):
        """解析列表卡片 (首页/分类页通用)
        结构: <div class="stui-vodlist__box">
                <a class="stui-vodlist__thumb..." href="/dgc/{id}.html" title="[类] 名-备注" data-original="图">
                  <span class="pic-text ...">备注</span></a>
                <div class="stui-vodlist__detail">
                  <p class="title..."><a href="/dgc/{id}.html">标题</a></p>
                  <p class="text...">演员</p></div></div>
        """
        items = []
        seen = set()
        chunks = re.split(r'<div class="stui-vodlist__box"', html)
        for block in chunks[1:]:
            m = re.search(r'href="/dgc/(\d+)\.html"', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue

            name = ""
            nm = re.search(r'<p class="title[^"]*">\s*<a[^>]*>([^<]+)</a>', block)
            if nm:
                name = self.clean(nm.group(1))
            if not name:
                tm = re.search(r'title="([^"]*)"', block)
                if tm:
                    raw = self.clean(tm.group(1))
                    name = re.sub(r'^\[[^\]]*\]\s*', '', raw)
                    name = re.sub(r'\s*-\s*[^-]+$', '', name).strip()
            if not name:
                continue
            seen.add(vid)

            pic = ""
            pm = re.search(r'data-original="([^"]*)"', block)
            if pm:
                pic = self._abs(pm.group(1))

            remark = ""
            rm = re.search(r'class="pic-text[^"]*"[^>]*>([^<]*)</span>', block)
            if rm:
                remark = self.clean(rm.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_media_cards(self, html):
        """解析搜索结果卡片 (stui-vodlist__media)"""
        items = []
        seen = set()
        region = html
        m = re.search(r'<ul class="stui-vodlist__media[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        if m:
            region = m.group(1)
        for block in re.split(r'<li', region)[1:]:
            vm = re.search(r'href="/dgc/(\d+)\.html"', block)
            if not vm:
                continue
            vid = vm.group(1)
            if vid in seen:
                continue
            name = ""
            nm = re.search(r'<h3 class="title">([^<]+)</h3>', block)
            if nm:
                name = self.clean(nm.group(1))
            if not name:
                tm = re.search(r'title="([^"]*)"', block)
                if tm:
                    raw = self.clean(tm.group(1))
                    name = re.sub(r'^\[[^\]]*\]\s*', '', raw)
                    name = re.sub(r'\s*-\s*[^-]+$', '', name).strip()
            if not name:
                continue
            seen.add(vid)

            pic = ""
            pm = re.search(r'data-original="([^"]*)"', block)
            if pm:
                pic = self._abs(pm.group(1))
            remark = ""
            rm = re.search(r'class="pic-text[^"]*"[^>]*>([^<]*)</span>', block)
            if rm:
                remark = self.clean(rm.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _pagecount(self, html, default=1):
        """解析总页数: 优先分页数字 <span class="num">1/N</span>, 其次"尾页"链接"""
        m = re.search(r'<span class="num">\d+/(\d+)</span>', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        m = re.search(r'href="([^"]+)"[^>]*>\s*尾页', html)
        if m:
            nums = re.findall(r'(\d+)', m.group(1))
            if nums:
                try:
                    return int(nums[-1])
                except Exception:
                    pass
        nums = re.findall(r'/page/(\d+)', html)
        if nums:
            try:
                return max(int(n) for n in nums)
            except Exception:
                pass
        return default

    # ==================== 首页 ====================

    def homeContent(self, filter):
        """首页: 一级分类 + 懂片帝式二级筛选 (类型/地区/年份)"""
        classes = []
        filters = {}
        for slug, name, group in self.CATEGORIES:
            classes.append({"type_id": slug, "type_name": name})
            filters[slug] = [
                {"key": "type", "name": "类型",
                 "value": [{"n": n, "v": v} for v, n in self._TYPES.get(group, [])]},
                {"key": "area", "name": "地区",
                 "value": [{"n": n, "v": v} for v, n in self._AREAS.get(group, [])]},
                {"key": "year", "name": "年份",
                 "value": [{"n": n, "v": v} for v, n in self._years]},
            ]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        """首页推荐视频"""
        html = self._get("/")
        if not html or len(html) < 1000:
            return {"list": []}
        return {"list": self._parse_cards(html)[:60]}

    # ==================== 分类(含二级筛选) ====================

    def _slug_of(self, tid):
        """tid 可能是 slug 或中文名, 统一转为站内片库 slug"""
        tid = str(tid or "").strip()
        if tid in self.NAME_TO_SLUG:
            return self.NAME_TO_SLUG[tid]
        # 兼容 so-/sgc-/tgc- 等前缀写法
        tid = re.sub(r'^(so|sgc|tgc)-', '', tid)
        return tid

    def _build_path(self, slug, extend, pg):
        """按筛选条件拼接分类页地址 (懂片帝式筛选叠加)"""
        if extend:
            t = str(extend.get("type") or "").strip()
            if t:
                slug = self._slug_of(t)
        segs = []
        if extend:
            area = str(extend.get("area") or "").strip()
            year = str(extend.get("year") or "").strip()
            if area and area != "全部":
                segs.append("area/" + urllib.parse.quote(area))
            if year and year != "全部":
                segs.append("year/" + urllib.parse.quote(year))
        path = "/sgc/" + slug
        if segs:
            path += "/" + "/".join(segs)
        if pg > 1:
            return "{0}/page/{1}.html".format(path, pg)
        return path + ".html"

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if not isinstance(extend, dict):
            extend = {}

        result = {"list": [], "page": pg, "pagecount": 1, "limit": 36, "total": 0}
        # TVBox 可能把 filter 为 True 时的 extend 合并在 filter 中
        if isinstance(filter, dict) and not extend:
            extend = filter

        slug = self._slug_of(tid)
        path = self._build_path(slug, extend, pg)
        html = self._get(path, referer=self.host + "/")
        if not html or len(html) < 1000:
            return result

        videos = self._parse_cards(html)
        result["list"] = videos
        result["pagecount"] = self._pagecount(html, default=pg)
        result["total"] = len(videos)
        return result

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        result = {"list": [], "page": pg, "pagecount": 1, "limit": 15, "total": 0}
        if not key:
            return result

        kw = urllib.parse.quote(key)
        if pg > 1:
            path = "/ss/wd/{0}/page/{1}.html".format(kw, pg)
        else:
            path = "/ss.html?wd={0}".format(kw)
        html = self._get(path, referer=self.host + "/")
        if not html or len(html) < 800:
            return result

        videos = self._parse_media_cards(html)
        if not videos:
            # 回退: 截取"相关的影片"区域后按普通卡片解析
            region = self._search_region(html)
            videos = self._parse_cards(region)
        if videos:
            result["list"] = videos
            result["pagecount"] = self._pagecount(html, default=pg)
            result["total"] = len(videos)
        return result

    def _search_region(self, html):
        """截取"相关的影片"区域, 避免误解析侧边推荐"""
        idx = html.find("相关的影片")
        if idx < 0:
            return html
        end = html.find("热播排行榜", idx)
        if end < 0:
            end = len(html)
        return html[idx:end]

    # ==================== 详情 ====================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip()
        if "/" in vid:
            vid = re.sub(r'\D', '', vid.split("/")[-1].split(".")[0]) or vid

        html = self._get("/dgc/%s.html" % vid, referer=self.host + "/")
        if not html or len(html) < 1000:
            return {"list": []}

        vod = {"vod_id": vid}

        # 标题
        name = ""
        nm = re.search(r'<h1 class="title">([^<]+)</h1>', html)
        if nm:
            name = self.clean(nm.group(1))
        if not name:
            tm = re.search(r'<title>([^<]+)</title>', html)
            if tm:
                raw = self.clean(tm.group(1))
                bm = re.search(r'《([^》]+)》', raw)
                name = bm.group(1) if bm else raw.split("-")[0].strip()
        vod["vod_name"] = name or vid

        # 封面
        pic = ""
        pm = re.search(r'class="stui-content__thumb".*?data-original="([^"]*)"', html, re.S)
        if not pm:
            pm = re.search(r'data-original="([^"]*)"', html)
        if pm:
            pic = self._abs(pm.group(1))
        vod["vod_pic"] = pic

        # 详细信息 (又名/类型/地区/语言/备注/年份/更新/导演/主演)
        info = self._parse_info(html)
        vod["vod_director"] = info.get("导演", "")
        vod["vod_actor"] = info.get("主演", "") or info.get("演员", "")
        vod["vod_year"] = info.get("年份", "")
        vod["vod_area"] = info.get("地区", "")
        vod["vod_class"] = info.get("类型", "")
        vod["vod_remarks"] = info.get("备注", "") or info.get("状态", "")

        # 简介 + 微信公众号推广
        desc = self._detail_desc(html)
        vod["vod_content"] = (desc + "\n\n" + self.WX_TEXT) if desc else self.WX_TEXT

        # 播放线路与选集
        play_from, play_url = self._parse_plays(html, vid)
        if play_from and play_url:
            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join(play_url)
        else:
            vod["vod_play_from"] = "影视工厂"
            vod["vod_play_url"] = "播放$%s/pgc/%s-1-1.html" % (self.host, vid)

        return {"list": [vod]}

    def _parse_info(self, html):
        """解析 <p class="data"> 中的键值对"""
        info = {}
        for mm in re.finditer(r'<p[^>]*class="[^"]*data[^"]*"[^>]*>(.*?)</p>', html, re.S):
            raw = mm.group(1)
            for part in re.split(r'(?=<span class="text-muted">)', raw):
                km = re.search(r'<span class="text-muted">\s*([^：<]+)：\s*</span>\s*(.*)', part, re.S)
                if not km:
                    continue
                label = self.clean(km.group(1))
                value = self.clean(km.group(2))
                value = re.sub(r'\s*\n\s*', "/", value).strip("/").strip()
                if label and value and label not in info:
                    info[label] = value
        return info

    def _detail_desc(self, html):
        """提取影片简介"""
        for pat in (r'<span class="detail-sketch">(.*?)</span>',
                    r'<span class="detail-content">(.*?)</span>'):
            m = re.search(pat, html, re.S)
            if m:
                txt = self.clean(m.group(1))
                if txt and len(txt) > 10:
                    return txt
        m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m:
            txt = self.clean(m.group(1))
            if txt and len(txt) > 10:
                return txt
        return ""

    def _parse_plays(self, html, vid):
        """解析全部播放线路 (tab) 与选集 (/pgc/{vid}/{sid}/{eid}.html)"""
        play_from = []
        play_url = []

        # 线路标签: <li><a href="#playlist1" ...>线路名</a></li>
        tabs = []
        tabm = re.search(r'<ul class="nav nav-tabs[^"]*"[^>]*>(.*?)</ul>', html, re.S)
        if tabm:
            for t in re.finditer(r'href="#playlist(\d+)"[^>]*>(.*?)</a>', tabm.group(1), re.S):
                label = self.clean(t.group(2))
                if label:
                    tabs.append((t.group(1), label))

        for sid, label in tabs:
            block = self._playlist_block(html, sid)
            eps = self._parse_episodes(block)
            if not eps:
                continue
            play_from.append(label)
            play_url.append("#".join(eps))

        # 无 tab 标签时兜底: 按 sid 分组
        if not play_from:
            groups = {}
            for href, ep_name, sid in self._all_pgc_links(html):
                groups.setdefault(sid, []).append((href, ep_name))
            for sid in sorted(groups.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                eps = []
                for href, ep_name in groups[sid]:
                    eps.append("{0}${1}".format(ep_name, self._abs(href)))
                if eps:
                    play_from.append("线路%s" % sid)
                    play_url.append("#".join(eps))

        return play_from, play_url

    def _playlist_block(self, html, sid):
        """截取 id="playlistN" 到下一个 playlist 之间的内容"""
        m = re.search(r'id="playlist%s"[^>]*>' % re.escape(sid), html)
        if not m:
            return ""
        start = m.end()
        nxt = re.search(r'id="playlist\d+"', html[start:])
        end = start + nxt.start() if nxt else len(html)
        return html[start:end]

    def _parse_episodes(self, block):
        eps = []
        for m in re.finditer(r'<a[^>]*href="(/pgc/[^"]+\.html)"[^>]*>(.*?)</a>', block, re.S):
            ep_name = self.clean(m.group(2))
            if not ep_name:
                ep_name = "第%d集" % (len(eps) + 1)
            eps.append("{0}${1}".format(ep_name, self._abs(m.group(1))))
        return eps

    def _all_pgc_links(self, html):
        out = []
        for m in re.finditer(r'href="(/pgc/(\d+)/(\d+)/(\d+)\.html)"[^>]*>(.*?)</a>', html, re.S):
            out.append((m.group(1), self.clean(m.group(5)) or "播放", m.group(3)))
        return out

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        """解析播放地址
        id 形如 "集名$https://www.piyaroad.com/pgc/{vid}/{sid}/{eid}.html"
        播放页含 MacCMS player_aaaa JSON, 直接取 m3u8 直链直连播放
        """
        raw = id or ""
        if "$" in raw:
            raw = raw.split("$")[-1]
        raw = raw.strip()
        if raw.startswith("//"):
            play_page = "https:" + raw
        elif raw.startswith("/"):
            play_page = self.host + raw
        elif raw.startswith("http"):
            play_page = raw
        else:
            play_page = self.host + "/" + raw.lstrip("/")

        html = self._get(play_page, referer=self.host + "/")
        real = ""
        if html:
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html, re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    data = {}
                real = self._decode_url(data.get("url", ""), data.get("encrypt", 0))
            if not real:
                m2 = re.search(r'(["\'])(https?:\\?/\\?/[^"\']*?\.m3u8[^"\']*)\1', html)
                if m2:
                    real = m2.group(2)
            if not real:
                m3 = re.search(r'https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4)[^\s"\'<>\\]*', html)
                if m3:
                    real = m3.group(0)

        real = (real or "").replace("\\/", "/").strip()
        if real and (".m3u8" in real or ".mp4" in real):
            return {
                "parse": "0",
                "url": real,
                "header": self._play_header(),
                "playUrl": "",
                "subtitle": "",
            }

        # 无法直接取出直链: 交给 TVBox 嗅探播放页
        return {
            "parse": "1",
            "url": play_page,
            "header": self._play_header(),
            "playUrl": "",
            "subtitle": "",
        }

    def _decode_url(self, url, encrypt):
        """处理 MacCMS player_aaaa 的 url / 加密字段"""
        url = (url or "").replace("\\/", "/").strip()
        if not url:
            return ""
        if encrypt in (1, "1"):
            for token in url.split("$$$"):
                try:
                    dec = base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "ignore")
                except Exception:
                    continue
                if ".m3u8" in dec or ".mp4" in dec:
                    return dec
        # 多段地址取第一段
        if "$$$" in url:
            url = url.split("$$$")[0]
        if "#" in url and (".m3u8" in url or ".mp4" in url):
            url = url.split("#")[0]
        return url

    # ==================== 其它 ====================

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def isVideoContent(self, ids):
        return False

    def manualVideoCheck(self):
        return False
