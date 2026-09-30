# -*- coding: utf-8 -*-

"""
星辰影院 TVBox Python Spider
网站地址: https://www.xcyycn.cc
基于 maccms 系统，标准库实现，仅使用 urllib / ssl / re / json / html，确保可在 TVBox 中运行。
支持首页分类、分类翻页、影片详情（多播放源）、搜索，并在影片简介处附加公众号信息。
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
        def searchContentPage(self, key, quick, page): return {}
        def playerContent(self, flag, id, vipFlags): return {}


class Spider(BaseSpider):
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    BASE_URL = "https://www.xcyycn.cc"

    # 推广文案
    _WX_TEXT = "微信公众号\u201c源力软件汇\u201d，QQ群1054592152，伴随更多优质资源尽在源力。"

    # ==================== 分类配置 ====================
    # 主分类与星辰影院导航一致：电影、电视剧、综艺、动漫、短剧
    # 细分类型使用 class 筛选参数，通过 /vs/ URL 实现
    CATEGORIES = [
        # 主分类
        {"type_id": "1", "type_name": "电影"},
        # 电影细分类型
        {"type_id": "10", "type_name": "动作片"},
        {"type_id": "11", "type_name": "喜剧片"},
        {"type_id": "12", "type_name": "爱情片"},
        {"type_id": "13", "type_name": "科幻片"},
        {"type_id": "14", "type_name": "恐怖片"},
        {"type_id": "15", "type_name": "剧情片"},
        {"type_id": "16", "type_name": "战争片"},
        {"type_id": "17", "type_name": "奇幻片"},
        {"type_id": "18", "type_name": "武侠片"},
        {"type_id": "19", "type_name": "悬疑片"},
        {"type_id": "20", "type_name": "惊悚片"},
        {"type_id": "21", "type_name": "犯罪片"},
        {"type_id": "22", "type_name": "历史片"},
        {"type_id": "23", "type_name": "文艺片"},
        {"type_id": "24", "type_name": "冒险片"},
        {"type_id": "25", "type_name": "动画片"},
        {"type_id": "26", "type_name": "记录片"},
        {"type_id": "27", "type_name": "传记片"},
        {"type_id": "28", "type_name": "歌舞片"},
        {"type_id": "29", "type_name": "短片"},
        {"type_id": "30", "type_name": "灾难片"},
        {"type_id": "31", "type_name": "儿童片"},
        {"type_id": "32", "type_name": "音乐片"},
        {"type_id": "33", "type_name": "西部片"},
        {"type_id": "34", "type_name": "戏曲片"},
        {"type_id": "35", "type_name": "青春片"},
        # 电视剧
        {"type_id": "2", "type_name": "电视剧"},
        # 电视剧细分类型
        {"type_id": "40", "type_name": "古装剧"},
        {"type_id": "41", "type_name": "都市剧"},
        {"type_id": "42", "type_name": "历史剧"},
        {"type_id": "43", "type_name": "谍战剧"},
        {"type_id": "44", "type_name": "家庭剧"},
        {"type_id": "45", "type_name": "年代剧"},
        {"type_id": "46", "type_name": "刑侦剧"},
        {"type_id": "47", "type_name": "军旅剧"},
        {"type_id": "48", "type_name": "青春剧"},
        {"type_id": "49", "type_name": "偶像剧"},
        {"type_id": "50", "type_name": "神话剧"},
        {"type_id": "51", "type_name": "仙侠剧"},
        {"type_id": "52", "type_name": "悬疑剧"},
        {"type_id": "53", "type_name": "喜剧"},
        {"type_id": "54", "type_name": "爱情剧"},
        {"type_id": "55", "type_name": "科幻剧"},
        {"type_id": "56", "type_name": "战争剧"},
        {"type_id": "57", "type_name": "武侠剧"},
        {"type_id": "58", "type_name": "奇幻剧"},
        {"type_id": "59", "type_name": "冒险剧"},
        {"type_id": "60", "type_name": "惊悚剧"},
        {"type_id": "61", "type_name": "犯罪剧"},
        # 其他主分类
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "5", "type_name": "短剧"},
    ]

    # 电影细分类型映射 (type_id -> (parent_type_id, class_value))
    _MOVIE_SUBCLASS_MAP = {
        "10": "动作片", "11": "喜剧片", "12": "爱情片", "13": "科幻片",
        "14": "恐怖片", "15": "剧情片", "16": "战争片", "17": "奇幻片",
        "18": "武侠片", "19": "悬疑",   "20": "惊悚",   "21": "犯罪",
        "22": "历史",   "23": "音乐",   "24": "冒险",   "25": "动画片",
        "26": "记录片", "27": "传记",   "28": "歌舞",   "29": "短片",
        "30": "灾难",   "31": "儿童",   "32": "音乐",   "33": "西部",
        "34": "戏曲",   "35": "青春",
    }

    # 电视剧细分类型映射
    _TV_SUBCLASS_MAP = {
        "40": "古装", "41": "都市", "42": "历史", "43": "谍战",
        "44": "家庭", "45": "年代", "46": "刑侦", "47": "军旅",
        "48": "青春", "49": "偶像", "50": "神话", "51": "仙侠",
        "52": "悬疑", "53": "喜剧", "54": "爱情", "55": "科幻",
        "56": "战争", "57": "武侠", "58": "奇幻", "59": "冒险",
        "60": "惊悚", "61": "犯罪",
    }

    # ==================== 筛选器 ====================
    _filters = {
        # 电影大类
        "1": {
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "动作", "v": "动作片"}, {"n": "喜剧", "v": "喜剧片"},
                    {"n": "爱情", "v": "爱情片"}, {"n": "科幻", "v": "科幻片"}, {"n": "恐怖", "v": "恐怖片"},
                    {"n": "剧情", "v": "剧情片"}, {"n": "战争", "v": "战争片"}, {"n": "奇幻", "v": "奇幻"},
                    {"n": "武侠", "v": "武侠"}, {"n": "悬疑", "v": "悬疑"}, {"n": "惊悚", "v": "惊悚"},
                    {"n": "犯罪", "v": "犯罪"}, {"n": "历史", "v": "历史"}, {"n": "冒险", "v": "冒险"},
                    {"n": "动画", "v": "动画片"}, {"n": "记录", "v": "记录片"}, {"n": "传记", "v": "传记"},
                    {"n": "歌舞", "v": "歌舞"}, {"n": "短片", "v": "短片"}, {"n": "灾难", "v": "灾难"},
                    {"n": "儿童", "v": "儿童"}, {"n": "西部", "v": "西部"}, {"n": "戏曲", "v": "戏曲"},
                    {"n": "青春", "v": "青春"}]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"}, {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"},
                    {"n": "其它", "v": "其它"}, {"n": "新加坡", "v": "新加坡"}, {"n": "澳大利亚", "v": "澳大利亚"},
                    {"n": "加拿大", "v": "加拿大"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "西班牙", "v": "西班牙"},
                    {"n": "意大利", "v": "意大利"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        },
        # 电视剧大类
        "2": {
            "class": [
                {"key": "class", "name": "类型", "value": [
                    {"n": "全部", "v": ""}, {"n": "古装", "v": "古装"}, {"n": "都市", "v": "都市"},
                    {"n": "历史", "v": "历史"}, {"n": "谍战", "v": "谍战"}, {"n": "家庭", "v": "家庭"},
                    {"n": "年代", "v": "年代"}, {"n": "刑侦", "v": "刑侦"}, {"n": "军旅", "v": "军旅"},
                    {"n": "青春", "v": "青春"}, {"n": "偶像", "v": "偶像"}, {"n": "神话", "v": "神话"},
                    {"n": "仙侠", "v": "仙侠"}, {"n": "悬疑", "v": "悬疑"}, {"n": "喜剧", "v": "喜剧"},
                    {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"}, {"n": "战争", "v": "战争"},
                    {"n": "武侠", "v": "武侠"}, {"n": "奇幻", "v": "奇幻"}, {"n": "冒险", "v": "冒险"},
                    {"n": "惊悚", "v": "惊悚"}, {"n": "犯罪", "v": "犯罪"}]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"}, {"n": "泰国", "v": "泰国"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"}, {"n": "2002", "v": "2002"}, {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        },
        # 综艺
        "3": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        },
        # 动漫
        "4": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "其它", "v": "其它"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        },
        # 短剧
        "5": {
            "class": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        },
    }

    def init(self, extend=""):
        pass

    def getName(self):
        return "星辰影院"

    def _wechat_text(self):
        return self._WX_TEXT

    # ==================== HTTP ====================
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
        text = text.replace("&#183;", "\u00b7").replace("&nbsp;", " ")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def absurl(self, u):
        if not u:
            return ""
        if u.startswith("http"):
            return u
        if u.startswith("//"):
            return "https:" + u
        return self.BASE_URL + ("" if u.startswith("/") else "/") + u

    # ==================== 列表解析 ====================
    def _parse_vitems(self, html):
        """从分类/首页页面解析视频列表"""
        items = []
        seen = set()
        # 星辰影院视频卡片: <a class="public-list-exp" href="/d-xxx.html" title="xxx">...</a>
        pat = r'<a[^>]*class="public-list-exp"[^>]*href="/d-(\d+)\.html"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(1)
            inner = m.group(2)
            if vid in seen:
                continue
            # 标题: 优先 title 属性, 其次 img alt, 再次 thumb-txt
            title = ""
            # 从 a 标签属性 title 提取
            tm = re.search(r'title="([^"]*)"', m.group(0))
            if tm:
                title = self.clean(tm.group(1))
            # 从 img alt 提取
            if not title:
                am = re.search(r'alt="([^"]*)"', inner)
                if am:
                    t = self.clean(am.group(1))
                    # 去掉 "封面图" 后缀
                    t = re.sub(r'封面图$', '', t).strip()
                    if t:
                        title = t
            if not title:
                continue
            seen.add(vid)
            # 封面图
            pic = ""
            pm = re.search(r'data-src="([^"]*)"', inner)
            if pm:
                pic = self.absurl(pm.group(1))
            if not pic:
                pm2 = re.search(r'src="([^"]*)"', inner)
                if pm2 and 'img-bj' not in pm2.group(1):
                    pic = self.absurl(pm2.group(1))
            # 备注 (正片/HD中字/更新至xx集等)
            remark = ""
            rm = re.search(r'class="public-list-prb[^"]*"[^>]*>([^<]+)<', inner)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_search_items(self, html):
        """从搜索结果页面解析视频列表"""
        items = []
        seen = set()
        # 搜索结果卡片: <a class="public-list-exp" href="/d-xxx.html">...</a>
        # 标题在同级 thumb-txt div 或 img alt 中
        pat = r'<a[^>]*class="public-list-exp"[^>]*href="/d-(\d+)\.html"[^>]*>(.*?)</a>'
        for m in re.finditer(pat, html, re.S):
            vid = m.group(1)
            inner = m.group(2)
            if vid in seen:
                continue
            # 标题: img alt 或 title 属性
            title = ""
            am = re.search(r'alt="([^"]*)"', inner)
            if am:
                t = self.clean(am.group(1))
                t = re.sub(r'封面图$', '', t).strip()
                if t:
                    title = t
            if not title:
                tm = re.search(r'title="([^"]*)"', m.group(0))
                if tm:
                    title = self.clean(tm.group(1))
            # 回退: 搜索 thumb-txt div (在外层容器中)
            if not title:
                # 搜索结果卡片后面跟着 thumb-txt
                after = html[m.end():m.end() + 2000]
                tm2 = re.search(r'class="thumb-txt[^"]*"[^>]*>([^<]+)<', after)
                if tm2:
                    title = self.clean(tm2.group(1))
            if not title:
                continue
            seen.add(vid)
            # 封面图
            pic = ""
            pm = re.search(r'data-src="([^"]*)"', inner)
            if pm:
                pic = self.absurl(pm.group(1))
            # 备注
            remark = ""
            rm = re.search(r'class="public-list-prb[^"]*"[^>]*>([^<]+)<', inner)
            if rm:
                remark = self.clean(rm.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    # ==================== 首页 ====================
    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": self._filters}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result
        videos = self._parse_vitems(html)
        result["list"] = videos
        return result

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1

        # 解析筛选参数
        cls = ""
        area = ""
        lang = ""
        year = ""
        sort = ""
        if isinstance(extend, dict):
            cls = extend.get("class", "") or ""
            area = extend.get("area", "") or ""
            lang = extend.get("lang", "") or ""
            year = extend.get("year", "") or ""
            sort = extend.get("sort", "") or ""

        tid_str = str(tid)

        # 如果是细分类型, 自动设置 class 筛选并使用父类 type_id
        if tid_str in self._MOVIE_SUBCLASS_MAP:
            cls = self._MOVIE_SUBCLASS_MAP[tid_str]
            tid_str = "1"
        elif tid_str in self._TV_SUBCLASS_MAP:
            cls = self._TV_SUBCLASS_MAP[tid_str]
            tid_str = "2"

        # 星辰影院 maccms 筛选 URL 格式 (12 段, 11 个连字符):
        # /vs/{type}-{area}-{sort}-{class}-{lang}-{letter}-{f6}-{page}-{f8}-{f9}-{f10}-{year}.html
        # 示例:
        #   全部电影第1页: /vs/1-----------.html
        #   动作片第1页:   /vs/1---动作片--------.html
        #   动作片第2页:   /vs/1---动作片-----2---.html
        #   2026年电影:    /vs/1-----------2026.html
        area_q = urllib.parse.quote(self.clean(area)) if area else ""
        sort_q = urllib.parse.quote(self.clean(sort)) if sort else ""
        cls_q = urllib.parse.quote(self.clean(cls)) if cls else ""
        lang_q = urllib.parse.quote(self.clean(lang)) if lang else ""
        year_q = self.clean(year) if year else ""
        page_q = str(page) if page > 1 else ""

        path = "/vs/%s-%s-%s-%s-%s-%s-%s-%s-%s-%s-%s-%s.html" % (
            tid_str, area_q, sort_q, cls_q, lang_q, "", "", page_q, "", "", "", year_q
        )
        url = self.BASE_URL + path
        html = self.getHtml(url, referer=self.BASE_URL + "/")
        if not html:
            return result

        videos = self._parse_vitems(html)
        if videos:
            result["list"] = videos
            pagecount = self._parse_pagecount(html)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

        videos = self._parse_vitems(html)
        if videos:
            result["list"] = videos
            pagecount = self._parse_pagecount(html)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

    def _parse_pagecount(self, html):
        """从分页HTML中解析总页数"""
        # 尾页链接格式: /vs/1--------1232---.html  (page 在第8段)
        pats = [
            r'href="/vs/[^"]*?-(\d+)---\.html"[^>]*>尾页',
            r'href="/vs/[^"]*?-(\d+)---\.html"[^>]*>尾頁',
        ]
        for pat in pats:
            m = re.search(pat, html)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    continue
        # 回退: 查找分页链接中第8段的最大数字
        # 格式: /vs/type-area-sort-class-lang-letter-f6-page-f8-f9-f10-year.html
        all_links = re.findall(r'/vs/[^"]*?\.html', html)
        max_page = 0
        for link in all_links:
            parts = link.split("-")
            if len(parts) >= 9:
                try:
                    p = int(parts[8])
                    if p > max_page:
                        max_page = p
                except Exception:
                    continue
        if max_page > 0:
            return max_page
        # 如果有"下一页"则至少2页
        if "下一页" in html or "下页" in html:
            return 2
        return 1

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        vid = str(vid).strip()
        if not vid:
            return result
        url = self.BASE_URL + "/d-%s.html" % vid
        html = self.getHtml(url)
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": vid}

        # 标题
        title = self._detail_name(html)
        vod["vod_name"] = title if title else vid

        # 封面
        pic = self._detail_pic(html)
        vod["vod_pic"] = pic

        # 元信息
        vod["vod_year"] = self._grab_label(html, "年份")
        vod["vod_area"] = self._grab_label(html, "地区")
        vod["vod_class"] = self._grab_label(html, "类型")
        vod["vod_actor"] = self._grab_label(html, "主演")
        vod["vod_director"] = self._grab_label(html, "导演")
        vod["vod_lang"] = self._grab_label(html, "语言")
        vod["vod_remarks"] = self._grab_label(html, "状态") or self._grab_label(html, "更新")

        # 简介 - 添加推广信息
        desc = self._detail_desc(html)
        wechat = self._wechat_text()
        if desc:
            vod["vod_content"] = desc + "\n\n" + wechat
        else:
            vod["vod_content"] = wechat

        # 播放源 + 选集
        from_arr, url_arr = self._detail_plays(html, vid)
        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            vod["vod_play_from"] = "星辰影院"
            vod["vod_play_url"] = "播放$%s" % (self.BASE_URL + "/p/%s-1-1.html" % vid)

        vod["type_id"] = ""
        vod["type_name"] = ""
        result["list"] = [vod]
        return result

    def _grab_label(self, html, label):
        """从详情页提取标签值"""
        # 模式1: <em>label:</em> value
        m = re.search(label + r"[:：]\s*</em>\s*(?:<a[^>]*>([^<]+)</a>|([^<]+))", html)
        if not m:
            # 模式2: label: value
            m = re.search(label + r"[:：]\s*(?:<a[^>]*>([^<]+)</a>|([^<]+))", html)
        if not m:
            return ""
        val = (m.group(1) or m.group(2) or "").strip()
        return self.clean(val)

    def _detail_name(self, html):
        """提取影片标题"""
        # 优先从 title 标签提取《》中的名称
        tm = re.search(r'<title>(.*?)</title>', html, re.S)
        if tm:
            raw = self.clean(tm.group(1))
            mm = re.search(r'《(.*?)》', raw)
            if mm:
                return mm.group(1)
            # 去掉常见后缀
            t = raw.split("_")[0].split("-")[0].strip()
            if t:
                return t
        # 回退: 从 class 含 title 的元素提取
        bm = re.search(r'class="[^"]*vod-name[^"]*"[^>]*>([^<]{2,40})<', html)
        if not bm:
            bm = re.search(r'class="[^"]*thumb-txt[^"]*"[^>]*>([^<]{2,40})<', html)
        if bm:
            return self.clean(bm.group(1))
        return ""

    def _detail_pic(self, html):
        """提取封面图"""
        # 优先从详情页主图 data-src 提取
        m = re.search(r'data-src="(https?://[^"]+)"', html)
        if m:
            return m.group(1)
        # 回退
        m2 = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
        if m2 and 'logo' not in m2.group(1) and 'img-bj' not in m2.group(1):
            return m2.group(1)
        return ""

    def _detail_desc(self, html):
        """提取影片简介"""
        # 从 简介/剧情 标签提取
        m = re.search(r'(简介|剧情)[:：]\s*</em>\s*(.*?)</div>', html, re.S)
        if m:
            txt = re.sub(r'<[^>]+>', ' ', m.group(2))
            txt = self.clean(txt)
            if txt:
                return txt
        # 回退: meta description
        md = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        if md:
            txt = self.clean(md.group(1))
            # 去掉 "xxx剧情介绍：" 前缀
            txt = re.sub(r'^[^:：]{2,10}剧情介绍[:：]\s*', '', txt)
            if txt:
                return txt
        # 回退: thumb-blurb
        tb = re.search(r'class="[^"]*thumb-blurb[^"]*"[^>]*>(.*?)</span>', html, re.S)
        if tb:
            txt = self.clean(tb.group(1))
            if txt and "暂无简介" not in txt:
                return txt
        return ""

    def _detail_plays(self, html, vid):
        """解析播放线路和选集列表"""
        # 播放源标签: <a class="swiper-slide"><i class="fa ..."></i>&nbsp;线路名<span class="badge">N</span></a>
        src_labels = []
        for m in re.finditer(r'<a[^>]*class="swiper-slide"[^>]*>(.*?)</a>', html, re.S):
            inner = m.group(1)
            # 提取文本内容 (去掉标签)
            txt = re.sub(r'<[^>]+>', '', inner).strip()
            txt = txt.replace('&nbsp;', '').strip()
            if txt:
                # 去掉末尾的数字(集数)
                txt = re.sub(r'\d+$', '', txt).strip()
                if txt:
                    src_labels.append(txt)

        # 选集列表块: <ul class="anthology-list-play ...">...</ul>
        blocks = re.findall(r'<ul class="anthology-list-play[^"]*"[^>]*>(.*?)</ul>', html, re.S)

        if not blocks:
            # 回退: 从所有 /p/ 链接提取
            all_eps = re.findall(r'href="(/p/[^"]+)"[^>]*>([^<]*)</a>', html)
            if all_eps:
                lines = []
                for ep_path, ep_name in all_eps:
                    ep_name = self.clean(ep_name) if self.clean(ep_name) else "\u7b2c%d\u96c6" % (len(lines) + 1)
                    lines.append("%s$%s" % (ep_name, self.absurl(ep_path)))
                return ["\u661f\u8fb0\u5f71\u9662"], ["#".join(lines)]
            return [], []

        groups = []
        for b in blocks:
            eps = re.findall(r'href="(/p/[^"]+)"[^>]*>([^<]*)</a>', b)
            groups.append(eps)

        # 配对线路标签与选集组
        from_arr = []
        url_arr = []
        n = max(len(src_labels), len(groups))
        for i in range(n):
            label = src_labels[i] if i < len(src_labels) else "\u7ebf\u8def%d" % (i + 1)
            eps = groups[i] if i < len(groups) else []
            if not eps:
                continue
            lines = []
            for ep_path, ep_name in eps:
                ep_name = self.clean(ep_name)
                if not ep_name:
                    ep_name = "\u7b2c%d\u96c6" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.absurl(ep_path)))
            from_arr.append(label)
            url_arr.append("#".join(lines))
        return from_arr, url_arr

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        if not key:
            return result

        if page <= 1:
            # 第一页: /s.html?wd=keyword
            url = self.BASE_URL + "/s.html?wd=" + urllib.parse.quote(key)
        else:
            # 后续页: /s{keyword}/page/{page}.html
            url = self.BASE_URL + "/s" + urllib.parse.quote(key) + "/page/%d.html" % page

        html = self.getHtml(url, referer=self.BASE_URL + "/")
        if not html:
            return result

        videos = self._parse_search_items(html)
        if videos:
            result["list"] = videos
            # 解析总页数
            pagecount = self._parse_search_pagecount(html)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

    def _parse_search_pagecount(self, html):
        """从搜索结果分页中解析总页数"""
        # 尾页链接: /s{keyword}/page/{max}.html
        m = re.search(r'href="/s[^"]*/page/(\d+)\.html"[^>]*>尾页', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        # 共N条数据,当前M/K页
        m2 = re.search(r'共\d+条数据[^,]*?(\d+)/(\d+)页', html)
        if m2:
            try:
                return int(m2.group(2))
            except Exception:
                pass
        # 如果有"下一页"则至少2页
        if "下一页" in html:
            return 2
        return 1

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_url = str(id)
        # 兼容 "名称$url" 形式
        if "$" in play_url and "http" not in play_url.split("$")[0]:
            parts = play_url.split("$")
            if len(parts) >= 2:
                play_url = parts[-1]
        play_url = self.absurl(play_url)

        # 提取 vid 用于 referer
        vid_m = re.search(r"/p/(\d+)-", play_url)
        referer = (self.BASE_URL + "/d-%s.html" % vid_m.group(1)) if vid_m else self.BASE_URL

        html = self.getHtml(play_url, referer=referer)
        play_headers = {
            "User-Agent": self.UA,
            "Referer": referer,
            "Accept": "*/*",
        }

        real = ""
        if html:
            # 方式1: maccms 标准 player_aaaa JSON
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</', html, re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                    u = data.get("url", "")
                    if u:
                        u = u.replace("\\/", "/")
                        real = u
                except Exception:
                    pass
            # 方式2: var player_data = {...}
            if not real:
                m2 = re.search(r'var\s+player_\w*\s*=\s*(\{.*?\})\s*</', html, re.S)
                if m2:
                    try:
                        data = json.loads(m2.group(1))
                        u = data.get("url", "")
                        if u:
                            u = u.replace("\\/", "/")
                            real = u
                    except Exception:
                        pass
            # 方式3: 直接搜索 m3u8 URL
            if not real:
                m3 = re.search(r'https?://[^\s"\']*?\.m3u8[^\s"\']*', html)
                if m3:
                    real = m3.group(0)
            # 方式4: 搜索 mp4 URL
            if not real:
                m4 = re.search(r'https?://[^\s"\']*?\.mp4[^\s"\']*', html)
                if m4:
                    real = m4.group(0)
            # 方式5: mac_url 变量
            if not real:
                m5 = re.search(r'(?:var\s+)?mac_url\s*=\s*["\']([^"\']+)', html)
                if m5:
                    real = m5.group(1).replace("\\/", "/")

        if real and (".m3u8" in real or ".mp4" in real):
            return {
                "url": real,
                "parse": "0",
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }

        # 无法直接解析, 交给 TVBox 嗅探
        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    def __jsEvalReturn(self):
        return {"proxy": None}

    def localProxy(self, params):
        return [200, "text/plain", ""]

    def isVideoContent(self, ids):
        return False

    def manualVideoCheck(self):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
