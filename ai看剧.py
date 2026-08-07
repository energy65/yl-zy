# -*- coding: utf-8 -*-
"""
AI看剧 - 基于琪琪影视架构的影视资源爬虫
支持TVBox协议，提供电影、电视剧、综艺、动漫等资源搜索与播放
"""

import re
import json
import ssl
import gzip
import urllib.parse
import urllib.request
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
    """AI看剧爬虫类"""
    
    # 目标网站配置
    BASE_URL = "https://www.bluedtravel.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 微信公众号加密数据（影片简介处显示）
    _w_full_data = [148, 215, 223, 141, 224, 214, 128, 230, 196, 133, 200, 200, 215, 191, 133, 20, 151, 211, 225, 140, 213, 236, 141, 222, 199, 133, 207, 233, 212, 129, 181, 20, 158, 213, 253, 24, 184, 201, 193, 82, 88, 84, 64, 106, 11, 2, 3, 3, 67, 141, 205, 221, 182, 237, 234, 133, 243, 213, 145, 251, 168, 212, 142, 174, 153, 221, 217, 129, 234, 243, 131, 217, 248, 132, 196, 226, 215, 172, 154, 208, 203, 249, 148, 227, 196]
    # 线路文本加密数据（线路处显示）
    _w_line_data = [151, 211, 225, 140, 213, 236, 128, 222, 217, 137, 211, 217, 240, 135, 215, 136, 223, 141, 206, 200, 186, 242, 201, 135, 212, 246, 145, 208, 133, 214, 136, 166, 148, 227, 234, 129, 226, 216, 129, 216, 222, 135, 197, 216]
    _w_key = b"qiqi_wechat_2026"

    # 分类配置：涵盖电影/电视剧/综艺/动漫及各子类
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "5", "type_name": "动作片"},
        {"type_id": "6", "type_name": "喜剧片"},
        {"type_id": "7", "type_name": "爱情片"},
        {"type_id": "8", "type_name": "科幻片"},
        {"type_id": "9", "type_name": "恐怖片"},
        {"type_id": "10", "type_name": "剧情片"},
        {"type_id": "11", "type_name": "战争片"},
        {"type_id": "12", "type_name": "纪录片"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "13", "type_name": "国产剧"},
        {"type_id": "14", "type_name": "香港剧"},
        {"type_id": "15", "type_name": "台湾剧"},
        {"type_id": "16", "type_name": "欧美剧"},
        {"type_id": "25", "type_name": "韩国剧"},
        {"type_id": "26", "type_name": "日本剧"},
        {"type_id": "27", "type_name": "泰国剧"},
        {"type_id": "28", "type_name": "海外剧"},
        {"type_id": "29", "type_name": "短剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "30", "type_name": "大陆综艺"},
        {"type_id": "31", "type_name": "港台综艺"},
        {"type_id": "32", "type_name": "日韩综艺"},
        {"type_id": "33", "type_name": "欧美综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "34", "type_name": "大陆动漫"},
        {"type_id": "35", "type_name": "日本动漫"},
        {"type_id": "36", "type_name": "欧美动漫"},
        {"type_id": "37", "type_name": "海外动漫"},
        {"type_id": "38", "type_name": "动画片"},
    ]

    def init(self, extend=""):
        """初始化方法"""
        pass

    def getName(self):
        """获取爬虫名称"""
        return "AI看剧"

    # ---------- 加密信息解密 ----------
    def _xor_decrypt(self, data):
        """XOR解密算法"""
        try:
            key = self._w_key
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                return ''.join(chr(data[i] ^ key[i % len(key)]) for i in range(len(data)))
            except Exception:
                return ''

    def _get_wechat_info(self):
        """获取微信公众号信息"""
        return self._xor_decrypt(self._w_full_data)

    def _get_line_info(self):
        """获取线路信息"""
        text = self._xor_decrypt(self._w_line_data)
        return text if text else "AI看剧"

    # ---------- HTTP请求 ----------
    def getHtml(self, url):
        """获取网页HTML内容"""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
            except Exception:
                pass
            
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": self.BASE_URL + "/"
            })
            
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
                content_encoding = resp.headers.get("Content-Encoding", "")
                
                # 处理gzip压缩
                if "gzip" in content_encoding:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                
                # 尝试多种编码解码
                for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
                
                return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    # ---------- 字符串截取工具 ----------
    @staticmethod
    def _cut_str(s, start, end):
        """从字符串s中截取start与end之间的内容，返回第一个匹配"""
        try:
            i = s.find(start)
            if i == -1:
                return ""
            i += len(start)
            j = s.find(end, i)
            if j == -1:
                return s[i:]
            return s[i:j]
        except Exception:
            return ""

    @staticmethod
    def _cut_all(s, start, end):
        """截取所有匹配"""
        res = []
        try:
            i = 0
            while True:
                p = s.find(start, i)
                if p == -1:
                    break
                p += len(start)
                q = s.find(end, p)
                if q == -1:
                    break
                res.append(s[p:q])
                i = q + len(end)
        except Exception:
            pass
        return res

    @staticmethod
    def _strip_tags(text):
        """去除HTML标签"""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    # ---------- 列表项解析 ----------
    def _parse_list_html(self, html):
        """从分类/搜索/首页页面解析视频列表"""
        videos = []
        if not html:
            return videos

        # 主选择器：module-item结构
        blocks = self._cut_all(html, '<div class="module-item">', '</div>\n</div>')
        if not blocks:
            # 回退：用module-item-pic锚点切分
            blocks = re.split(r'<div class="module-item(?:\s[^"]*)?">', html)

        for blk in blocks if isinstance(blocks, list) else []:
            if 'qiqiyingyuan/' not in blk:
                continue
            v = self._parse_item_block(blk)
            if v:
                videos.append(v)

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def _parse_item_block(self, blk):
        """解析单个视频项"""
        try:
            # 提取详情链接与ID
            m = re.search(r'href="(/qiqiyingyuan/(\d+)\.html)"', blk)
            if not m:
                return None
            path = m.group(1)
            vid = m.group(2)

            # 提取标题：title优先
            title = ""
            tm = re.search(r'class="module-item-title"[^>]*title="([^"]+)"', blk)
            if tm:
                title = tm.group(1)
            if not title:
                tm = re.search(r'class="module-item-pic"[^>]*title="([^"]+)"', blk)
                if tm:
                    title = tm.group(1)
            if not title:
                tm = re.search(r'alt="([^"]+)"', blk)
                if tm:
                    title = tm.group(1)
            if not title:
                return None

            # 提取封面：data-src > data-original > src
            pic = ""
            pm = re.search(r'data-src="([^"]+)"', blk)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-original="([^"]+)"', blk)
                if pm:
                    pic = pm.group(1)
            if not pic:
                pm = re.search(r'<img[^>]*src="([^"]+)"', blk)
                if pm and 'loading.gif' not in pm.group(1):
                    pic = pm.group(1)

            # 提取备注：module-item-text（日期/集数）
            remarks = ""
            rm = re.search(r'class="module-item-text">([^<]*)</div>', blk)
            if rm:
                remarks = rm.group(1).strip()

            # 解码HTML实体
            title = html_mod.unescape(title)

            return {
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
            }
        except Exception:
            return None

    # ---------- 首页 ----------
    def homeContent(self, filter):
        """获取首页分类信息"""
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        """获取首页推荐视频"""
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/")
        if not html:
            return result
        videos = self._parse_list_html(html)
        result["list"] = videos[:30]
        return result

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            if page <= 1:
                url = "{0}/qqyy/{1}.html".format(self.BASE_URL, tid)
            else:
                url = "{0}/qqyy/{1}-{2}.html".format(self.BASE_URL, tid, page)

            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_list_html(html)
            result["list"] = videos

            # 解析总页数：尾页链接 /qqyy/{tid}-{n}.html
            pagecount = 1
            pm = re.search(r'/qqyy/{0}-(\d+)\.html"[^>]*>[^<]*尾页'.format(tid), html)
            if pm:
                pagecount = int(pm.group(1))
            else:
                # 回退：所有分页链接中取最大值
                nums = [int(x) for x in re.findall(r'/qqyy/{0}-(\d+)\.html'.format(tid), html)]
                if nums:
                    pagecount = max(nums)
            if pagecount < 1:
                pagecount = 1

            result["pagecount"] = str(pagecount)
            result["page"] = str(page)
            result["limit"] = str(len(videos))
            result["total"] = str(pagecount * 36)
            return result
        except Exception:
            return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        """获取视频详情"""
        result = {"list": []}
        try:
            vid = ids[0] if isinstance(ids, list) and ids else ids
            url = "{0}/qiqiyingyuan/{1}.html".format(self.BASE_URL, vid)
            html = self.getHtml(url)
            if not html:
                return result

            # 标题
            title = self._cut_str(html, '<h1 class="page-title">', '</h1>')
            if not title:
                tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                title = tm.group(1) if tm else ""
            title = html_mod.unescape(title.strip())

            # 封面
            pic = ""
            pm = re.search(r'<img[^>]*class="lazyload"[^>]*data-src="([^"]+)"', html)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-src="(https?://[^"]+)"', html)
                if pm:
                    pic = pm.group(1)

            # 分类
            cat_name = ""
            cm = re.search(r'class="tag-link"[^>]*><div class="video-tag-icon">.*?</div>([^<]+)</a>', html, re.DOTALL)
            if cm:
                cat_name = cm.group(1).strip()
            if not cat_name:
                cm = re.search(r'href="/qqyy/\d+\.html"\s+title="([^"]+)"', html)
                if cm:
                    cat_name = cm.group(1)

            # 年份
            year = ""
            ym = re.search(r'searchtype=5&tid=\d+&year=(\d+)"', html)
            if ym:
                year = ym.group(1)

            # 地区
            area = ""
            am = re.search(r'searchtype=5&tid=\d+&area=([^"&]+)"', html)
            if am:
                area = urllib.parse.unquote(am.group(1))

            # 评分
            score = ""
            sm = re.search(r'豆瓣\s*([\d.]+)\s*分', html)
            if sm:
                score = sm.group(1)

            # 导演
            director = ""
            d_block = self._cut_str(html, '>导演：</span>', '</div>')
            if d_block:
                director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))

            # 主演
            actor = ""
            a_block = self._cut_str(html, '>主演：</span>', '</div>')
            if a_block:
                actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))

            # 简介
            content = self._cut_str(html, 'video-info-content vod_content">', '</div>')
            if content:
                content = self._strip_tags(content)
            content = html_mod.unescape(content).strip()

            # 播放列表：解析所有playlist块及对应线路名
            source_names = re.findall(r'href="#playlist\d+"[^>]*>\s*<i class="icon-play"></i>\s*([^<]+)</a>', html)
            source_names = [s.strip() for s in source_names if s.strip()]

            # 每个playlist块
            play_groups = []
            playlist_blocks = re.findall(r'<div id="(playlist\d+)"[^>]*>(.*?)</ul>\s*</div>', html, re.DOTALL)
            if not playlist_blocks:
                playlist_blocks = re.findall(r'<div id="(playlist\d+)"[^>]*class="tab-pane[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)

            for idx, (pid, pblk) in enumerate(playlist_blocks):
                src_name = source_names[idx] if idx < len(source_names) else "线路%d" % (idx + 1)
                # 提取每集链接
                eps = re.findall(r'<a[^>]*href="(/play/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>', pblk)
                if not eps:
                    eps = re.findall(r'<a[^>]*href="(/play/[^"]+)"[^>]*title="([^"]+)"', pblk)
                ep_list = []
                for ep_url, ep_name in eps:
                    ep_name = html_mod.unescape(ep_name).strip()
                    if not ep_name:
                        ep_name = "播放"
                    ep_list.append("{0}${1}".format(ep_name, ep_url))
                if ep_list:
                    play_groups.append((src_name, ep_list))

            # 若未解析到，回退：从详情页立即播放链接构造单集
            if not play_groups:
                pm = re.search(r'href="(/play/{0}-\d+-\d+\.html)"'.format(vid), html)
                if pm:
                    play_groups.append(("AI看剧", ["第1集${0}".format(pm.group(1))]))

            # 构造播放串
            play_from = "$$$".join(g[0] for g in play_groups)
            play_url = "$$$".join("#".join(g[1]) for g in play_groups)

            # 加密微信信息追加到简介
            wechat_info = self._get_wechat_info()
            desc = (content + '\n\n' + wechat_info) if content else wechat_info

            # 线路名使用加密信息
            line_info = self._get_line_info()
            if not play_from:
                play_from = line_info
                play_url = ""

            vod = {
                "vod_id": str(vid),
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": actor,
                "vod_director": director,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": ("豆瓣" + score + "分") if score else "",
                "vod_content": desc,
                "vod_class": cat_name,
                "type_name": cat_name,
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }
            result['list'] = [vod]
            return result
        except Exception:
            return result

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg="1"):
        """搜索视频"""
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            kw = urllib.parse.quote(key)
            if page <= 1:
                url = "{0}/search.php?searchword={1}&searchtype=".format(self.BASE_URL, kw)
            else:
                url = "{0}/search.php?page={1}&searchword={2}&searchtype=".format(self.BASE_URL, page, kw)

            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_list_html(html)

            # 关键词二次过滤确保结果精准匹配
            if videos and key:
                k = key.lower()
                filtered = [v for v in videos if k in v.get("vod_name", "").lower()]
                if filtered:
                    videos = filtered

            result["list"] = videos
            result["page"] = str(page)
            result["total"] = str(len(videos))
            return result
        except Exception:
            return result

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        """获取播放地址"""
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            # id可能为完整路径/play/xxx.html或完整URL
            if id.startswith("http"):
                play_url = id
            elif id.startswith("/"):
                play_url = self.BASE_URL + id
            else:
                play_url = self.BASE_URL + "/play/" + id + ".html"

            html = self.getHtml(play_url)
            if not html:
                return result

            # 提取真实视频流地址：var now="..."
            video_url = ""
            m = re.search(r'var\s+now\s*=\s*"([^"]+)"', html)
            if m:
                video_url = m.group(1)
            if not video_url:
                m = re.search(r'var\s+url\s*=\s*"([^"]+)"', html)
                if m:
                    video_url = m.group(1)
            if not video_url:
                m = re.search(r'(https?://[^\s"\']+\.m3u8)', html)
                if m:
                    video_url = m.group(1)
            if not video_url:
                m = re.search(r'(https?://[^\s"\']+\.mp4)', html)
                if m:
                    video_url = m.group(1)

            if video_url:
                result["parse"] = 0
                result["url"] = video_url
                result["header"] = json.dumps({
                    "User-Agent": self.UA,
                    "Referer": self.BASE_URL + "/"
                })
            return result
        except Exception:
            return result

    # ---------- 配置 ----------
    def localProxy(self, params):
        """本地代理"""
        return [200, "", ""]

    def isVideoContent(self, ids):
        """是否为视频内容"""
        return False

    def manualSniffer(self, ids):
        """手动嗅探"""
        return False

    def snifferContent(self, ids):
        """嗅探内容"""
        return None
