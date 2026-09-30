# -*- coding: utf-8 -*-
"""
影视工厂 TVBox Spider
网站: https://www.piyaroad.com/
基于 MacCMS 模板，播放地址可通过 player_aaaa JSON 直接提取 m3u8
"""

import re
import json
import time
import urllib.parse
import urllib.request
import urllib.error
import html as html_mod
import ssl

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

    HOST = "https://www.piyaroad.com"

    # 推广文案
    _WX_TEXT = "微信公众号\u201c源力软件汇\u201d"

    # ==================== 分类配置 ====================
    # 影视工厂导航: 电影大类下有8个子类型, 电视剧按地区分类
    # 用户要求细化类型(科幻/奇幻/战争/犯罪/武侠/历史/文艺/古装/都市/谍战/家庭等)
    # 对于网站已有的子类型使用 /sgc/{name}.html, 对于网站没有的子类型使用搜索接口模拟
    CATEGORIES = [
        # 电影大类
        {"type_id": "dianying", "type_name": "电影"},
        {"type_id": "sgc-dongzuopian", "type_name": "动作片"},
        {"type_id": "sgc-xijupian", "type_name": "喜剧片"},
        {"type_id": "sgc-aiqingpian", "type_name": "爱情片"},
        {"type_id": "sgc-kehuanpian", "type_name": "科幻片"},
        {"type_id": "sgc-kongbupian", "type_name": "恐怖片"},
        {"type_id": "sgc-juqingpian", "type_name": "剧情片"},
        {"type_id": "sgc-zhanzhengpian", "type_name": "战争片"},
        {"type_id": "sgc-jilupian", "type_name": "纪录片"},
        # 电影扩展类型(网站无独立分类,用搜索模拟)
        {"type_id": "so-奇幻", "type_name": "奇幻片"},
        {"type_id": "so-犯罪", "type_name": "犯罪片"},
        {"type_id": "so-武侠", "type_name": "武侠片"},
        {"type_id": "so-历史", "type_name": "历史片"},
        {"type_id": "so-文艺", "type_name": "文艺片"},
        {"type_id": "so-悬疑", "type_name": "悬疑片"},
        {"type_id": "so-惊悚", "type_name": "惊悚片"},
        {"type_id": "so-冒险", "type_name": "冒险片"},
        {"type_id": "so-动画", "type_name": "动画片"},
        {"type_id": "so-传记", "type_name": "传记片"},
        {"type_id": "so-歌舞", "type_name": "歌舞片"},
        {"type_id": "so-预告", "type_name": "预告片"},
        {"type_id": "so-影视解说", "type_name": "影视解说"},
        # 电视剧大类
        {"type_id": "tgc-guochanju", "type_name": "电视剧"},
        {"type_id": "tgc-guochanju", "type_name": "国产剧"},
        {"type_id": "tgc-gangju", "type_name": "港剧"},
        {"type_id": "tgc-taiju", "type_name": "台剧"},
        {"type_id": "tgc-hanju", "type_name": "韩剧"},
        {"type_id": "tgc-riju", "type_name": "日剧"},
        {"type_id": "tgc-oumeiju", "type_name": "美剧"},
        {"type_id": "tgc-haiwaiju", "type_name": "海外剧"},
        # 电视剧扩展类型(网站无独立分类,用搜索模拟)
        {"type_id": "so-古装", "type_name": "古装剧"},
        {"type_id": "so-都市", "type_name": "都市剧"},
        {"type_id": "so-历史", "type_name": "历史剧"},
        {"type_id": "so-谍战", "type_name": "谍战剧"},
        {"type_id": "so-家庭", "type_name": "家庭剧"},
        {"type_id": "so-年代", "type_name": "年代剧"},
        {"type_id": "so-刑侦", "type_name": "刑侦剧"},
        {"type_id": "so-军旅", "type_name": "军旅剧"},
        {"type_id": "so-青春", "type_name": "青春剧"},
        {"type_id": "so-偶像", "type_name": "偶像剧"},
        {"type_id": "so-神话", "type_name": "神话剧"},
        {"type_id": "so-仙侠", "type_name": "仙侠剧"},
        {"type_id": "so-悬疑", "type_name": "悬疑剧"},
        {"type_id": "so-喜剧", "type_name": "喜剧"},
        # 动漫
        {"type_id": "tgc-dongman", "type_name": "动漫"},
        {"type_id": "tgc-rihandongman", "type_name": "日韩动漫"},
        {"type_id": "tgc-guochandongman", "type_name": "国产动漫"},
        {"type_id": "tgc-oumeidongman", "type_name": "欧美动漫"},
        {"type_id": "tgc-donghuapian", "type_name": "动画片"},
        # 综艺
        {"type_id": "tgc-zongyi", "type_name": "综艺"},
        {"type_id": "tgc-daluzongyi", "type_name": "大陆综艺"},
        {"type_id": "tgc-gangtaizongyi", "type_name": "港台综艺"},
        {"type_id": "tgc-rihanzongyi", "type_name": "日韩综艺"},
        {"type_id": "tgc-oumeizongyi", "type_name": "欧美综艺"},
        # 短剧
        {"type_id": "tgc-duanju", "type_name": "短剧"},
    ]

    # ==================== 筛选器 ====================
    _filters = {
        "dianying": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"}, {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"}, {"n": "00年代", "v": "2000_2009"},
                    {"n": "90年代", "v": "1990_1999"}, {"n": "80年代", "v": "1980_1989"},
                    {"n": "更早", "v": "0_1979"}]},
            ],
        },
        "tgc-guochanju": {
            "class": [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""}, {"n": "大陆", "v": "中国大陆"}, {"n": "香港", "v": "中国香港"},
                    {"n": "台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "英国", "v": "英国"}, {"n": "泰国", "v": "泰国"},
                    {"n": "其他", "v": "其他"}]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"}, {"n": "00年代", "v": "2000_2009"},
                    {"n": "90年代", "v": "1990_1999"}, {"n": "80年代", "v": "1980_1989"},
                    {"n": "更早", "v": "0_1979"}]},
            ],
        },
        "tgc-dongman": {
            "class": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"}, {"n": "00年代", "v": "2000_2009"}]},
            ],
        },
        "tgc-zongyi": {
            "class": [
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "10年代", "v": "2010_2019"}, {"n": "00年代", "v": "2000_2009"}]},
            ],
        },
    }

    def init(self, extend=""):
        self.host = self.HOST
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def getName(self):
        return "影视工厂"

    def _wechat_text(self):
        return self._WX_TEXT

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _img_src(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    # ---------------- HTTP ----------------
    def _get(self, path, referer=None):
        """HTTP GET, 返回解码后的HTML文本"""
        if not path.startswith("http"):
            url = self.host + path
        else:
            url = path
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
                    time.sleep(0.5)
                    continue
                return ""
        return ""

    # ---------------- parse helpers ----------------
    def _parse_vitems(self, html):
        """从分类/首页页面解析视频列表
        影视工厂视频卡片结构:
        <div class="stui-vodlist__box">
          <a class="stui-vodlist__thumb lazyload" href="/dgc/xxx.html" title="..." data-original="cover.jpg">
            <span class="pic-text text-right">备注</span>
          </a>
          <div class="stui-vodlist__detail">
            <p class="title"><a href="/dgc/xxx.html" title="...">标题</a></p>
            <p class="text">演员</p>
          </div>
        </div>
        """
        items = []
        seen = set()
        # 匹配每个视频卡片 - 影视工厂使用 stui-vodlist__box
        pat = r'<div class="stui-vodlist__box"[^>]*>(.*?)</div>\s*</div>'
        for m in re.finditer(pat, html, re.S):
            block = m.group(1)
            # 提取vid和标题
            link_m = re.search(r'href="/dgc/(\d+)\.html"[^>]*title="([^"]*)"', block)
            if not link_m:
                link_m = re.search(r'href="/dgc/(\d+)\.html"', block)
            if not link_m:
                continue
            vid = link_m.group(1)
            if vid in seen:
                continue

            # 标题
            title = ""
            title_m = re.search(r'title="([^"]*)"', block)
            if title_m:
                raw_title = self.clean(title_m.group(1))
                title = re.sub(r'^\[[^\]]*\]\s*', '', raw_title)
                title = re.sub(r'\s*-\s*[^-]+$', '', title)
            if not title:
                p_m = re.search(r'<p class="title[^>]*>\s*<a[^>]*>([^<]*)</a>', block)
                if p_m:
                    title = self.clean(p_m.group(1))
            if not title:
                continue

            seen.add(vid)

            # 封面图
            pic = ""
            img_m = re.search(r'data-original="([^"]*)"', block)
            if img_m:
                pic = self._img_src(img_m.group(1))

            # 备注
            remark = ""
            rem_m = re.search(r'class="pic-text[^"]*"[^>]*>([^<]*)</span>', block)
            if rem_m:
                remark = self.clean(rem_m.group(1))
            if not remark:
                rem_m2 = re.search(r'class="pic-tag[^"]*"[^>]*>([^<]*)</span>', block)
                if rem_m2:
                    remark = self.clean(rem_m2.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        # 回退1: 尝试搜索结果的文本列表格式
        if not items:
            items = self._parse_search_text_items(html)
        # 回退2: 如果还没匹配到, 尝试更通用的匹配
        if not items:
            items = self._parse_vitems_fallback(html)
        return items

    def _parse_search_text_items(self, html):
        """解析搜索结果的文本列表格式
        影视工厂搜索结果使用 stui-vodlist__text 列表:
        <li><a class="text-overflow" href="/dgc/xxx.html" title="[类型] 标题-备注">
          <span class="text-muted pull-right">备注</span><em class="text-red">1 . </em>标题</a></li>
        """
        items = []
        seen = set()
        for m in re.finditer(r'<a[^>]*class="text-overflow"[^>]*href="/dgc/(\d+)\.html"[^>]*title="([^"]*)"[^>]*>(.*?)</a>', html, re.S):
            vid = m.group(1)
            if vid in seen:
                continue
            raw_title = self.clean(m.group(2))
            # 去掉 [类型] 前缀和 -备注 后缀
            title = re.sub(r'^\[[^\]]*\]\s*', '', raw_title)
            title = re.sub(r'\s*-\s*[^-]+$', '', title)
            if not title or len(title) < 2:
                # 从inner文本提取
                inner = self.clean(re.sub(r'<[^>]+>', '', m.group(3)))
                # 去掉序号前缀 "1 . "
                inner = re.sub(r'^\d+\s*\.\s*', '', inner)
                if inner and len(inner) >= 2:
                    title = inner
            if not title or len(title) < 2:
                continue
            seen.add(vid)
            # 备注: 从 title 属性末尾或 span 提取
            remark = ""
            rem_m = re.search(r'<span class="text-muted[^"]*"[^>]*>([^<]*)</span>', m.group(3))
            if rem_m:
                remark = self.clean(rem_m.group(1))
            if not remark:
                # 从 title 属性中提取末尾的备注
                rem_m2 = re.search(r'-([^-]+)$', raw_title)
                if rem_m2:
                    remark = self.clean(rem_m2.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": "",
                "vod_remarks": remark,
            })
        return items

    def _parse_search_media_items(self, html):
        """解析搜索结果的大卡片格式 (stui-vodlist__media)
        <li class="active clearfix">
          <div class="thumb">
            <a class="v-thumb stui-vodlist__thumb lazyload" href="/dgc/xxx.html" title="..." data-original="cover.jpg">
              <span class="pic-text text-right">备注</span>
            </a>
          </div>
          <div class="detail">
            <h3 class="title">标题</h3>
            ...
          </div>
        </li>
        """
        items = []
        seen = set()
        # 定位搜索结果区域: 在"相关的影片"和排行榜之间
        # 查找 stui-vodlist__media 列表
        for m in re.finditer(r'<li[^>]*class="[^"]*active[^"]*"[^>]*>(.*?)</li>', html, re.S):
            block = m.group(1)
            # 提取vid
            link_m = re.search(r'href="/dgc/(\d+)\.html"', block)
            if not link_m:
                continue
            vid = link_m.group(1)
            if vid in seen:
                continue

            # 标题: 从 h3.title 或 title 属性提取
            title = ""
            h3_m = re.search(r'<h3 class="title">([^<]*)</h3>', block)
            if h3_m:
                title = self.clean(h3_m.group(1))
            if not title:
                title_m = re.search(r'title="([^"]*)"', block)
                if title_m:
                    raw = self.clean(title_m.group(1))
                    title = re.sub(r'^\[[^\]]*\]\s*', '', raw)
                    title = re.sub(r'\s*-\s*[^-]+$', '', title)
            if not title or len(title) < 2:
                continue

            seen.add(vid)

            # 封面图
            pic = ""
            img_m = re.search(r'data-original="([^"]*)"', block)
            if img_m:
                pic = self._img_src(img_m.group(1))

            # 备注
            remark = ""
            rem_m = re.search(r'class="pic-text[^"]*"[^>]*>([^<]*)</span>', block)
            if rem_m:
                remark = self.clean(rem_m.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_vitems_fallback(self, html):
        """回退解析: 匹配所有 /dgc/xxx.html 链接"""
        items = []
        seen = set()
        for m in re.finditer(r'<a[^>]*href="/dgc/(\d+)\.html"[^>]*>(.*?)</a>', html, re.S):
            vid = m.group(1)
            if vid in seen:
                continue
            inner = m.group(2)
            title = self.clean(re.sub(r'<[^>]+>', '', inner))
            if not title:
                title_m = re.search(r'title="([^"]*)"', m.group(0))
                if title_m:
                    title = self.clean(title_m.group(1))
            if not title or len(title) < 2:
                continue
            seen.add(vid)
            # 封面: 往前找 data-original
            pre = html[max(0, m.start()-300):m.start()]
            pic = ""
            pic_m = re.search(r'data-original="([^"]*)"', pre)
            if pic_m:
                pic = self._img_src(pic_m.group(1))
            # 备注
            remark = ""
            rem_m = re.search(r'pic-text[^>]*>([^<]+)', pre)
            if rem_m:
                remark = self.clean(rem_m.group(1))
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    # ---------------- home ----------------
    def homeContent(self, filter):
        result = {"class": self.CATEGORIES, "filters": self._filters}
        return result

    def homeVideoContent(self):
        result = {"list": []}
        html = self._get("/")
        if not html or len(html) < 1000:
            return result
        videos = self._parse_vitems(html)
        result["list"] = videos
        return result

    # ---------------- category ----------------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1

        tid_str = str(tid)

        # 三种分类类型:
        # 1. sgc-xxx: 网站子类型分类 /sgc/{name}.html (分页: /sgc/{name}/page/{n}.html)
        # 2. tgc-xxx: 网站顶级分类 /tgc/{name}.html (分页: /tgc/{name}/page/{n}.html)
        # 3. so-xxx: 搜索模拟分类 (无独立分类页,用搜索接口)
        # 4. dianying: 电影大类

        if tid_str.startswith("so-"):
            keyword = tid_str[3:]  # 去掉 "so-" 前缀
            return self._search_category(keyword, pg)

        if tid_str.startswith("sgc-"):
            cat_name = tid_str[4:]
            path = "/sgc/%s.html" % cat_name
            if pg > 1:
                path = "/sgc/%s/page/%d.html" % (cat_name, pg)
        elif tid_str.startswith("tgc-"):
            cat_name = tid_str[4:]
            path = "/tgc/%s.html" % cat_name
            if pg > 1:
                path = "/tgc/%s/page/%d.html" % (cat_name, pg)
        elif tid_str == "dianying":
            path = "/tgc/dianying.html"
            if pg > 1:
                path = "/tgc/dianying/page/%d.html" % pg
        else:
            path = "/tgc/%s.html" % tid_str
            if pg > 1:
                path = "/tgc/%s/page/%d.html" % (tid_str, pg)

        html = self._get(path)
        if not html or len(html) < 1000:
            return result

        videos = self._parse_vitems(html)
        if videos:
            result["list"] = videos
            pagecount = self._parse_pagecount(html)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

    def _search_category(self, keyword, pg):
        """通过搜索接口模拟分类列表"""
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        path = "/ss.html?wd=%s" % urllib.parse.quote(keyword)
        if pg > 1:
            path = "/ss.html?wd=%s&page=%d" % (urllib.parse.quote(keyword), pg)
        html = self._get(path)
        if not html or len(html) < 1000:
            return result
        # 搜索结果在"相关的影片"区域, 截取该区域避免误解析排行榜
        search_html = self._extract_search_region(html)
        videos = self._parse_search_media_items(search_html)
        if not videos:
            videos = self._parse_search_text_items(search_html)
        if not videos:
            videos = self._parse_vitems(search_html)
        if videos:
            result["list"] = videos
            pagecount = self._parse_pagecount(html)
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
        return result

    def _extract_search_region(self, html):
        """从搜索页中提取"相关的影片"区域, 避免误解析排行榜"""
        idx = html.find("相关的影片")
        if idx < 0:
            return html
        # 找到下一个 pannel 标题 (排行榜)
        next_idx = html.find("热播排行榜", idx)
        if next_idx < 0:
            next_idx = len(html)
        return html[idx:next_idx]

    def _parse_pagecount(self, html):
        """从分页HTML中解析总页数"""
        nums = re.findall(r'/page/(\d+)\.html', html)
        if nums:
            try:
                return max(int(n) for n in nums)
            except Exception:
                pass
        return 1

    # ---------------- detail ----------------
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        html = self._get("/dgc/%s.html" % vid)
        if not html or len(html) < 1000:
            return result

        vod = {"vod_id": str(vid)}

        # 标题: 优先从 h1 提取(排除站名), 回退到 title 标签
        name = ""
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        for h in h1s:
            t = self.clean(re.sub(r'<[^>]+>', '', h))
            if t and "影视工厂" not in t and len(t) > 1:
                name = t
                break
        if not name:
            # 从 thumb 的 title 属性提取
            thumb_m = re.search(r'class="stui-vodlist__thumb[^"]*"[^>]*title="([^"]*)"', html)
            if thumb_m:
                raw = self.clean(thumb_m.group(1))
                name = re.sub(r'^\[[^\]]*\]\s*', '', raw)
                name = re.sub(r'\s*-\s*[^-]+$', '', name)
        if not name:
            # 从 <title> 标签提取
            m2 = re.search(r'<title>([^<]+)</title>', html)
            if m2:
                raw = self.clean(m2.group(1))
                # 格式: 科幻片-《流浪地球》免费观看-影视工厂
                name_m = re.search(r'《([^》]+)》', raw)
                if name_m:
                    name = name_m.group(1)
                else:
                    name = raw.split("-")[0].strip()
        vod["vod_name"] = name if name else str(vid)

        # 封面图
        pic = ""
        pic_m = re.search(r'data-original="([^"]*)"', html)
        if pic_m:
            pic = self._img_src(pic_m.group(1))
        vod["vod_pic"] = pic

        # 类型/地区/年份
        tags = re.findall(r'<a[^>]*href="/(?:tgc|sgc)/[^"]*\.html"[^>]*>([^<]*)</a>', html)
        tags = [self.clean(t) for t in tags if self.clean(t)]
        nav_filter = {"影视工厂", "韩剧大全", "日剧全集", "美剧推荐", "天天动漫", "综艺秀",
                      "上新", "影讯", "电影排行榜", "电视剧", "电影", "连续剧"}
        type_tags = [t for t in tags if t not in nav_filter]

        vod_class = ""
        vod_area = ""
        vod_year = ""
        for t in type_tags:
            if re.fullmatch(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            elif re.match(r"\d{4}", t):
                if not vod_year:
                    vod_year = t
            else:
                areas = ("中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国",
                         "英国", "法国", "德国", "印度", "泰国", "丹麦", "瑞典",
                         "巴西", "加拿大", "俄罗斯", "意大利", "比利时", "爱尔兰",
                         "西班牙", "澳大利亚", "捷克", "荷兰", "波兰", "挪威",
                         "芬兰", "冰岛", "匈牙利", "奥地利", "瑞士", "葡萄牙",
                         "希腊", "土耳其", "伊朗", "以色列", "墨西哥", "阿根廷",
                         "其他", "大陆", "香港", "台湾", "海外")
                if not vod_area and t in areas:
                    vod_area = t
                elif not vod_class:
                    vod_class = t
        vod["vod_year"] = vod_year
        vod["vod_area"] = vod_area
        vod["vod_class"] = vod_class

        # 简介添加推广信息
        desc = self._detail_desc(html)
        wechat = self._wechat_text()
        if desc:
            vod["vod_content"] = desc + "\n\n" + wechat
        else:
            vod["vod_content"] = wechat

        # 详细信息行 (导演/演员/又名/类型/地区/年份等)
        # 影视工厂的data行可能是混合格式: "类型：科幻 地区：大陆 语言：国语"
        # class可能为 "data" 或 "data hidden-xs" 等
        infos = {}
        for mm in re.finditer(r'<p[^>]*class="[^"]*data[^"]*"[^>]*>(.*?)</p>', html, re.S):
            raw = mm.group(1)
            # 去掉HTML标签但保留文本
            text = re.sub(r'<[^>]+>', ' ', raw)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            # 按"标签："分割提取键值对
            parts = re.split(r'(?=[\u4e00-\u9fa5]{2,4}[：:])', text)
            for part in parts:
                m = re.match(r'([\u4e00-\u9fa5]{2,4})[：:]\s*(.*)', part.strip())
                if m:
                    label = m.group(1).strip()
                    value = m.group(2).strip()
                    if label and value and label not in infos:
                        infos[label] = value
        vod["vod_director"] = infos.get("导演", "")
        vod["vod_actor"] = infos.get("主演", "") or infos.get("演员", "")
        if not vod["vod_area"]:
            vod["vod_area"] = infos.get("地区", "")
        if not vod["vod_year"]:
            ym = re.search(r"(\d{4})", infos.get("年份", "") or infos.get("首映", "") or infos.get("上映", ""))
            if ym:
                vod["vod_year"] = ym.group(1)
        if not vod_class:
            vod_class = infos.get("类型", "")
            vod["vod_class"] = vod_class
        remark = infos.get("备注", "") or infos.get("状态", "")
        if remark:
            vod["vod_remarks"] = remark

        # 播放列表
        from_arr, url_arr = self._detail_plays(html, vid)

        if from_arr and url_arr:
            vod["vod_play_from"] = "$$$".join(from_arr)
            vod["vod_play_url"] = "$$$".join(url_arr)
        else:
            # 回退: 从页面任意 pgc 链接构造
            fallback = re.search(r'href="(/pgc/%s-\d+-\d+\.html)"' % re.escape(str(vid)), html)
            if fallback:
                vod["vod_play_from"] = "影视工厂线路"
                vod["vod_play_url"] = "播放$%s" % (self.host + fallback.group(1))
            else:
                vod["vod_play_from"] = "影视工厂线路"
                vod["vod_play_url"] = "播放$%s/pgc/%s-1-1.html" % (self.host, vid)

        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def _detail_desc(self, html):
        """提取影片简介"""
        # 影视工厂: 简介在 <span class="detail-sketch"> 或 <span class="detail-content"> 中
        m = re.search(r'<span class="detail-sketch"[^>]*>(.*?)</span>', html, re.S)
        if m:
            txt = re.sub(r"<br\s*/?>", "\n", m.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt and len(txt) > 10:
                return txt
        m2 = re.search(r'<span class="detail-content"[^>]*>(.*?)</span>', html, re.S)
        if m2:
            txt = re.sub(r"<br\s*/?>", "\n", m2.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt:
                return txt
        # 回退: 从剧情介绍区域提取
        m3 = re.search(r'剧情介绍.*?<div[^>]*>(.*?)</div>', html, re.S)
        if m3:
            txt = re.sub(r"<br\s*/?>", "\n", m3.group(1))
            txt = re.sub(r"<[^>]+>", "", txt)
            txt = self.clean(txt)
            if txt and len(txt) > 10:
                return txt
        # 回退: 从 meta description 提取
        m4 = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if m4:
            txt = self.clean(m4.group(1))
            if txt and len(txt) > 10:
                return txt
        return ""

    def _detail_plays(self, html, vid):
        """解析播放线路和选集列表
        影视工厂结构:
        <a href="#playlist1">线路名</a>  -- 线路标签
        <ul id="playlist1">
          <li><a href="/pgc/{vid}/{sid}/{eid}.html">集名</a></li>
        </ul>
        """
        # 线路标签
        src_labels = []
        tab_m = re.findall(r'<a[^>]*href="#(playlist\d+)"[^>]*>(.*?)</a>', html, re.S)
        for tab_id, tab_name in tab_m:
            name = self.clean(re.sub(r'<[^>]+>', '', tab_name))
            if name:
                src_labels.append((tab_id, name))

        from_arr = []
        url_arr = []
        for tab_id, label in src_labels:
            # 查找对应的 playlist 块
            block_m = re.search(r'<ul[^>]*id="%s"[^>]*>(.*?)</ul>' % re.escape(tab_id), html, re.S)
            if not block_m:
                block_m = re.search(r'id="%s"[^>]*>(.*?)</div>' % re.escape(tab_id), html, re.S)
            if not block_m:
                continue
            block = block_m.group(1)
            # 提取选集链接
            eps = re.findall(r'<a[^>]*href="(/pgc/(\d+)/(\d+)/(\d+)\.html)"[^>]*>(.*?)</a>', block, re.S)
            if not eps:
                eps2 = re.findall(r'href="(/pgc/\d+/\d+/\d+\.html)"[^>]*>([^<]*)</a>', block)
                eps = [(e[0], "", "", "", e[1]) for e in eps2]
            if not eps:
                continue
            lines = []
            for ep_href, ev, es, eid, ep_inner in eps:
                ep_name = self.clean(re.sub(r'<[^>]+>', '', ep_inner))
                if not ep_name:
                    ep_name = "第%d集" % (len(lines) + 1)
                lines.append("%s$%s" % (ep_name, self.host + ep_href))
            if lines:
                from_arr.append(label)
                url_arr.append("#".join(lines))

        # 如果没有找到线路标签但有选集链接
        if not from_arr:
            all_eps = re.findall(r'<a[^>]*href="(/pgc/(\d+)/(\d+)/(\d+)\.html)"[^>]*>(.*?)</a>', html, re.S)
            if all_eps:
                # 按source分组
                groups = {}
                for ep_href, ev, es, eid, ep_inner in all_eps:
                    s = int(es)
                    if s not in groups:
                        groups[s] = []
                    ep_name = self.clean(re.sub(r'<[^>]+>', '', ep_inner))
                    if not ep_name:
                        ep_name = "第%d集" % (len(groups[s]) + 1)
                    groups[s].append("%s$%s" % (ep_name, self.host + ep_href))
                for s in sorted(groups.keys()):
                    from_arr.append("线路%d" % s)
                    url_arr.append("#".join(groups[s]))

        return from_arr, url_arr

    # ---------------- search ----------------
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, page)

    def _do_search(self, key, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if not key:
            return result
        # 影视工厂搜索: /ss.html?wd={keyword}
        path = "/ss.html?wd=%s" % urllib.parse.quote(key)
        if pg > 1:
            path = "/ss.html?wd=%s&page=%d" % (urllib.parse.quote(key), pg)
        html = self._get(path, referer=self.host + "/")
        if not html or len(html) < 1000:
            return result
        # 搜索结果在"相关的影片"区域, 截取该区域避免误解析排行榜
        search_html = self._extract_search_region(html)
        videos = self._parse_search_media_items(search_html)
        if not videos:
            videos = self._parse_search_text_items(search_html)
        if not videos:
            videos = self._parse_vitems(search_html)
        if videos:
            result["list"] = videos
            pagecount = self._parse_pagecount(html)
            result["pagecount"] = str(max(pagecount, pg + 1))
            result["total"] = str(len(videos))
        return result

    # ---------------- play ----------------
    def playerContent(self, flag, id, vipFlags):
        play_url = id
        if not play_url.startswith("http"):
            play_url = self.host + "/" + play_url.lstrip("/")
        html = self._get(play_url, referer=self.host + "/")
        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.host + "/",
            "Accept": "*/*",
        }

        real = ""
        if html:
            # 影视工厂使用 MacCMS player_aaaa JSON
            m = re.search(r'player_aaaa\s*=\s*(\{[^}]+\})', html)
            if m:
                try:
                    j = json.loads(m.group(1))
                    real = j.get("url", "")
                except Exception:
                    pass

            # 回退: 直接搜索m3u8
            if not real or (".m3u8" not in real and ".mp4" not in real):
                m2 = re.search(r'(["\'])(https?://[^"\']*?\.m3u8[^"\']*)\1', html)
                if m2:
                    real = m2.group(2)
            if not real:
                m3 = re.search(r'https?://[^\s"\']+?\.m3u8[^\s"\']*', html)
                if m3:
                    real = m3.group(0)
            if not real:
                m4 = re.search(r'https?://[^\s"\']+?\.mp4[^\s"\']*', html)
                if m4:
                    real = m4.group(0)
            if not real:
                m5 = re.search(r'"url"\s*:\s*"(https?://[^"]+)"', html)
                if m5:
                    u = m5.group(1).replace("\\/", "/")
                    if ".m3u8" in u or ".mp4" in u:
                        real = u

        if real and (".m3u8" in real or ".mp4" in real):
            real = real.replace("\\/", "/")
            return {
                "url": real,
                "parse": "0",
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": "",
            }

        # 无法直接解析,交给TVBox嗅探
        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

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
