#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 星耀短剧 TVBox 自定义爬虫 (dj991.com)
# 标准 TVBox python 接口 (type=3)，使用标准库 urllib，兼容 TVBox 内置 Python 环境

import json
import re
import ssl
import gzip
import base64
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import quote, unquote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass

        def getName(self):
            return ""

        def homeContent(self, filter):
            return {}

        def homeVideoContent(self):
            return {}

        def categoryContent(self, tid, pg, filter, extend):
            return {}

        def detailContent(self, ids):
            return {}

        def searchContent(self, key, quick, pg="1"):
            return {}

        def playerContent(self, flag, id, vipFlags):
            return {}


SITE = "https://dj991.com"
UA = "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

# 显示名称 -> 播放类型
DISPLAY_TO_FROM = {
    "蓝光-q": "qq",
    "蓝光-y": "qiyi",
    "蓝光-k": "youku",
    "蓝光-m": "mgtv",
    "BB-APP独享线路": "bilibili",
    "极速": "jsm3u8",
    "优质": "1080zyk",
    "备用-WG": "wsym3u8",
    "备用-SN": "snm3u8",
}
# 直链 m3u8 类型（可直接播放，无需解析）
DIRECT_FROM = {"jsmile3u8", "jsm3u8", "1080zyk", "wsym3u8", "snm3u8"}

# 推广信息（影片简介处添加）
PROMO = "微信公众号：源力软件汇\nQ群：1054592152\n伴随更多优质资源尽在源力"

CTX = ssl._create_unverified_context()


class Spider(BaseSpider):

    def getName(self):
        return "星耀短剧"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ---------------- 公共请求 ----------------
    def _get(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": SITE + "/"})
            resp = urllib.request.urlopen(req, timeout=20, context=CTX)
            data = resp.read()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return data.decode("utf-8", "ignore")
        except Exception:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": SITE + "/"})
                resp = urllib.request.urlopen(req, timeout=20)
                data = resp.read()
                if data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                return data.decode("utf-8", "ignore")
            except Exception:
                return ""

    # ---------------- 首页分类 ----------------
    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "追剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "36", "type_name": "短剧"},
            {"type_id": "6", "type_name": "动作片"},
            {"type_id": "7", "type_name": "喜剧片"},
            {"type_id": "8", "type_name": "爱情片"},
            {"type_id": "9", "type_name": "科幻片"},
            {"type_id": "10", "type_name": "恐怖片"},
            {"type_id": "13", "type_name": "大陆剧"},
            {"type_id": "14", "type_name": "港台剧"},
            {"type_id": "15", "type_name": "日韩剧"},
            {"type_id": "16", "type_name": "欧美剧"},
            {"type_id": "21", "type_name": "马泰剧"},
            {"type_id": "38", "type_name": "爽文短剧"},
            {"type_id": "39", "type_name": "都市短剧"},
            {"type_id": "40", "type_name": "穿越短剧"},
            {"type_id": "41", "type_name": "反转爽剧"},
            {"type_id": "42", "type_name": "女频恋爱"},
            {"type_id": "33", "type_name": "国漫"},
            {"type_id": "34", "type_name": "日韩动漫"},
            {"type_id": "35", "type_name": "海外动漫"},
            {"type_id": "50", "type_name": "漫剧"},
            {"type_id": "27", "type_name": "大陆综艺"},
            {"type_id": "28", "type_name": "港台综艺"},
            {"type_id": "29", "type_name": "日韩综艺"},
            {"type_id": "30", "type_name": "欧美综艺"},
            {"type_id": "31", "type_name": "海外综艺"},
        ]
        return {"class": classes, "filters": {}}

    # ---------------- 首页推荐 ----------------
    def homeVideoContent(self):
        html = self._get(SITE + "/")
        items = self._extract_items(html)
        return {"list": items, "page": 1, "pagecount": 1, "limit": 90, "total": len(items)}

    # ---------------- 分类列表 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        url = SITE + "/vodtype/%s-%s.html" % (tid, pg)
        html = self._get(url)
        items = self._extract_items(html)
        return {"list": items, "page": int(pg), "pagecount": 9999, "limit": 90, "total": 999999}

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        kw = quote(key)
        url = SITE + "/vodsearch/%s-------------.html" % kw
        html = self._get(url)
        items = self._extract_items(html)
        return {"list": items, "page": 1, "pagecount": 1, "limit": 90, "total": len(items)}

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        vid = ids[0]
        html = self._get(SITE + "/voddetail/%s.html" % vid)
        if not html:
            return {"list": []}

        # 标题
        m = re.search(r"<title>([^_<]+)", html)
        vod_name = m.group(1).strip() if m else vid

        # 封面
        pics = re.findall(r'data-original="([^"]+)"', html)
        vod_pic = pics[0] if pics else ""

        # 简介
        desc = ""
        dm = re.search(r'class="content_desc[^"]*">([\s\S]*?)</div>', html)
        if dm:
            desc = re.sub(r"<[^>]+>", "", dm.group(1)).strip()
        if not desc:
            dm = re.search(r"简介：([\s\S]*?)(?:详细|$)", html)
            if dm:
                desc = dm.group(1).strip()
        if desc:
            desc = desc + "\n\n" + PROMO
        else:
            desc = PROMO

        # 播放源（线路）
        tab_block = re.search(r'id="NumTab"[^>]*>([\s\S]*?)</div>', html)
        tabs = []
        if tab_block:
            tabs = re.findall(r'alt="([^"]+)"', tab_block.group(1))
        if not tabs:
            tabs = ["默认"]

        boxes = re.findall(
            r'class="play_list_box[^"]*"[^>]*>([\s\S]*?)(?=<div class="play_list_box|</div>\s*</div>\s*<div class="play_but|</div>\s*</div>\s*</div>)',
            html,
        )
        if len(boxes) < len(tabs):
            boxes = re.split(r'<div class="play_list_box', html)[1:]
            boxes = ['<div class="play_list_box' + b for b in boxes]

        sources = []  # list of (name, from_code, episodes_str)
        for i, name in enumerate(tabs):
            box = boxes[i] if i < len(boxes) else ""
            eps = re.findall(r'href="/vodplay/%s-(\d+)-(\d+)\.html"[^>]*>([^<]*)<' % vid, box)
            if not eps:
                eps = re.findall(r'/vodplay/%s-(\d+)-(\d+)\.html' % vid, box)
                eps = [(e[0], e[1], "") for e in eps]
            ep_list = []
            for sid, nid, epname in eps:
                epname = epname.strip() or ("第%s集" % nid)
                ep_list.append("%s$%s-%s-%s" % (epname, vid, sid, nid))
            if ep_list:
                from_code = DISPLAY_TO_FROM.get(name, "")
                sources.append((name, from_code, "#".join(ep_list)))

        # 排序：直链源优先（保证默认线路可正常播放）
        def _key(s):
            return 0 if s[1] in DIRECT_FROM else 1

        sources.sort(key=_key)

        if not sources:
            return {"list": []}

        play_from = "$$$".join(s[0] for s in sources)
        play_url = "$$$".join(s[2] for s in sources)

        vod = {
            "vod_id": vid,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": desc,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        m = re.match(r"(\d+)-(\d+)-(\d+)", id)
        if not m:
            return {"parse": 0, "playUrl": "", "url": "", "header": {}}
        vid, sid, nid = m.groups()
        url = SITE + "/vodplay/%s-%s-%s.html" % (vid, sid, nid)
        html = self._get(url)
        jm = re.search(r"player_aaaa\s*=\s*(\{[^}]*\})", html)
        real_url = ""
        from_code = ""
        if jm:
            try:
                data = json.loads(jm.group(1))
                real_url = data.get("url", "")
                from_code = data.get("from", "")
                enc = str(data.get("encrypt", "0"))
                if enc == "1":
                    real_url = unquote(real_url)
                elif enc == "2":
                    real_url = unquote(base64.b64decode(real_url).decode("utf-8", "ignore"))
            except Exception:
                pass

        header = {"User-Agent": UA, "Referer": SITE + "/"}
        if from_code in DIRECT_FROM or real_url.endswith((".m3u8", ".mp4", ".ts")):
            return {"parse": 0, "playUrl": "", "url": real_url, "header": json.dumps(header, ensure_ascii=False)}
        else:
            # 需要解析的源（爱奇艺/腾讯/优酷等），走本站解析接口
            parse_url = "https://jiexi.dj991.com/?url=" + quote(real_url, safe="")
            return {"parse": 1, "playUrl": "", "url": parse_url, "header": json.dumps(header, ensure_ascii=False)}

    # ---------------- 列表解析 ----------------
    def _extract_items(self, html):
        if not html:
            return []
        pat = r'class="(?:vodlist_thumb|balist_thumb)[^"]*" href="/voddetail/(\d+)\.html" title="([^"]*)" data-(?:original|background)="([^"]*)"'
        found = re.findall(pat, html)
        items = []
        seen = set()
        for vid, name, pic in found:
            if vid in seen:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return items
