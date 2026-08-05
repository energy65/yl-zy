# -*- coding: utf-8 -*-

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
        def fetch(self, url, headers=None): return ""


class Spider(BaseSpider):
    BASE_URL = "https://hrmmzz.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 微信公众号加密数据（影片简介处显示）
    _w_full_data = [142, 203, 199, 140, 202, 192, 186, 242, 201, 135, 212, 246, 145, 208, 133, 18, 212, 140, 251, 144, 227, 243, 157, 220, 240, 147, 222, 213, 142, 208, 243, 125, 221, 140, 190, 71, 140, 203, 205, 89, 69, 84, 107, 66, 92, 81, 89, 84, 70, 187, 142, 132, 219, 172, 228, 147, 242, 220, 144, 197, 197, 147, 217, 251, 128, 213, 220, 183, 135, 180, 212, 140, 251, 144, 217, 213, 144, 253, 247, 145, 223, 243, 141, 235, 239]
    # 线路文本加密数据（线路处显示）
    _w_line_data = [141, 207, 249, 141, 255, 250, 186, 202, 212, 138, 241, 195, 182, 232, 215, 142, 156, 210, 212, 212, 140, 237, 217, 133, 227, 224, 128, 236, 223, 135, 206, 207, 215, 186, 169, 222, 214, 218, 141, 211, 195, 135, 238, 240]
    _w_key = b"kuihua_wechat_2026"

    # 分类配置：涵盖电影/电视剧/综艺/动漫及各子类，纪录片(21)包含天文地理类视频
    CATEGORIES = [
        {"type_id": "1", "type_name": "电视剧"},
        {"type_id": "6", "type_name": "香港剧"},
        {"type_id": "7", "type_name": "台湾剧"},
        {"type_id": "8", "type_name": "欧美剧"},
        {"type_id": "9", "type_name": "韩国剧"},
        {"type_id": "10", "type_name": "日本剧"},
        {"type_id": "11", "type_name": "泰国剧"},
        {"type_id": "12", "type_name": "海外剧"},
        {"type_id": "2", "type_name": "电影"},
        {"type_id": "14", "type_name": "动作片"},
        {"type_id": "15", "type_name": "喜剧片"},
        {"type_id": "16", "type_name": "爱情片"},
        {"type_id": "17", "type_name": "科幻片"},
        {"type_id": "18", "type_name": "恐怖片"},
        {"type_id": "19", "type_name": "剧情片"},
        {"type_id": "20", "type_name": "战争片"},
        {"type_id": "21", "type_name": "纪录片"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "13", "type_name": "短剧"},
    ]

    def init(self, extend=""):
        self.extend = extend
        # 初始化 cookie 会话，用于绕过 search.php 的加载页挑战
        try:
            import http.cookiejar
            self._cj = http.cookiejar.CookieJar()
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self._cj),
                urllib.request.HTTPSHandler(self._build_ctx())
            )
            self._opener.addheaders = [
                ("User-Agent", self.UA),
                ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
                ("Accept-Language", "zh-CN,zh;q=0.9"),
                ("Accept-Encoding", "gzip"),
                ("Referer", self.BASE_URL + "/"),
                ("Connection", "keep-alive"),
                ("Upgrade-Insecure-Requests", "1"),
            ]
        except Exception:
            self._cj = None
            self._opener = None

    def getName(self):
        return "葵花影院"

    # ---------- 加密信息解密 ----------
    def _xor_decrypt(self, data):
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
        return self._xor_decrypt(self._w_full_data)

    def _get_line_info(self):
        text = self._xor_decrypt(self._w_line_data)
        return text if text else "葵花影院"

    # ---------- HTTP ----------
    @staticmethod
    def _build_ctx():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
        except Exception:
            pass
        return ctx

    def getHtml(self, url, retry=2):
        """获取页面，自动处理 gzip/编码；对 search.php 加载页挑战进行重试"""
        # 优先使用带 cookie 的 opener（应对 search.php 的 503 加载页挑战）
        if self._opener is not None:
            try:
                resp = self._opener.open(url, timeout=20)
                data = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if "gzip" in enc:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                txt = self._decode_html(data)
                # search.php 加载页挑战检测：返回 503 或包含加载中 reload 脚本
                if "location.reload()" in txt and "加载中" in txt:
                    import time
                    time.sleep(2)
                    return self.getHtml(url, retry - 1) if retry > 0 else ""
                return txt
            except urllib.error.HTTPError as e:
                # 503 加载页挑战：等待后重试
                if e.code == 503 and retry > 0:
                    import time
                    time.sleep(2)
                    try:
                        resp = self._opener.open(url, timeout=20)
                        data = resp.read()
                        enc = resp.headers.get("Content-Encoding", "")
                        if "gzip" in enc:
                            try:
                                data = gzip.decompress(data)
                            except Exception:
                                pass
                        return self._decode_html(data)
                    except Exception:
                        pass
                # 其它错误回退到普通请求
            except Exception:
                pass

        # 回退：普通请求
        try:
            ctx = self._build_ctx()
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
                if "gzip" in content_encoding:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
                return self._decode_html(data)
        except Exception:
            return ""

    @staticmethod
    def _decode_html(data):
        for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    # ---------- 字符串截取工具（兼容TVBox cat.js环境）----------
    @staticmethod
    def _cut_str(s, start, end):
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
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    # ---------- 列表项解析 ----------
    def _parse_list_html(self, html):
        """从分类/搜索/首页页面解析视频列表，使用多种选择器回退"""
        videos = []
        if not html:
            return videos

        # 主选择器：vodlist_item 结构
        # <li class="vodlist_item ..."><a class="vodlist_thumb lazyload" href="/yingyuan/{id}.html" title="..." data-original="{pic}"><span class="pic_text ...">{remarks}</span></a><div class="vodlist_titbox"><p class="vodlist_title"><a href="/yingyuan/{id}.html" title="...">{name}</a></p><p class="vodlist_sub">...</p></div></li>
        blocks = self._cut_all(html, '<li class="vodlist_item', '</li>')
        if not blocks:
            # 回退：用 vodlist_thumb 锚点切分
            blocks = re.split(r'<li class="vodlist_item', html)[1:]

        for blk in blocks:
            if 'yingyuan/' not in blk:
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
        try:
            # 提取详情链接与ID
            m = re.search(r'href="/yingyuan/(\d+)\.html"', blk)
            if not m:
                return None
            vid = m.group(1)

            # 提取标题：title 优先（去掉"在线观看"后缀）
            title = ""
            tm = re.search(r'class="vodlist_title"[^>]*>\s*<a[^>]*title="([^"]+)"', blk)
            if tm:
                title = tm.group(1)
            if not title:
                tm = re.search(r'class="vodlist_thumb[^"]*"[^>]*title="([^"]+)"', blk)
                if tm:
                    title = tm.group(1)
            if not title:
                tm = re.search(r'alt="([^"]+)"', blk)
                if tm:
                    title = tm.group(1)
            if not title:
                return None
            title = title.replace("在线观看", "").strip()

            # 提取封面：data-original > data-src > src
            pic = ""
            pm = re.search(r'data-original="([^"]+)"', blk)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-src="([^"]+)"', blk)
                if pm:
                    pic = pm.group(1)
            if not pic:
                pm = re.search(r'<img[^>]*src="([^"]+)"', blk)
                if pm and 'loading.gif' not in pm.group(1):
                    pic = pm.group(1)

            # 提取备注：pic_text（集数/清晰度）
            remarks = ""
            rm = re.search(r'class="pic_text[^"]*"[^>]*>([^<]*)</span>', blk)
            if rm:
                remarks = rm.group(1).strip()
            if not remarks:
                rm = re.search(r'class="vodlist_sub"[^>]*>([^<]*)</p>', blk)
                if rm:
                    remarks = rm.group(1).strip().replace("更新时间：", "")

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
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/")
        if not html:
            return result
        videos = self._parse_list_html(html)
        result["list"] = videos[:30]
        return result

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            if page <= 1:
                url = "{0}/kuihua/{1}.html".format(self.BASE_URL, tid)
            else:
                url = "{0}/kuihua/{1}-{2}.html".format(self.BASE_URL, tid, page)

            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_list_html(html)
            result["list"] = videos

            # 解析总页数：尾页链接 /kuihua/{tid}-{n}.html
            pagecount = 1
            pm = re.search(r'/kuihua/{0}-(\d+)\.html"[^>]*>[^<]*尾页'.format(tid), html)
            if pm:
                pagecount = int(pm.group(1))
            else:
                nums = [int(x) for x in re.findall(r'/kuihua/{0}-(\d+)\.html'.format(tid), html)]
                if nums:
                    pagecount = max(nums)
            if pagecount < 1:
                pagecount = 1

            result["pagecount"] = str(pagecount)
            result["page"] = str(page)
            result["limit"] = str(len(videos))
            result["total"] = str(pagecount * 30)
            return result
        except Exception:
            return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = ids[0] if isinstance(ids, list) and ids else ids
            url = "{0}/yingyuan/{1}.html".format(self.BASE_URL, vid)
            html = self.getHtml(url)
            if not html:
                return result

            # 标题
            title = ""
            tm = re.search(r'<h2 class="title">\s*([^<]+)</h2>', html)
            if tm:
                title = tm.group(1).strip()
            if not title:
                title = self._cut_str(html, '<h2 class="title">', '</h2>')
            title = html_mod.unescape(title.strip())

            # 封面
            pic = ""
            pm = re.search(r'class="vodlist_thumb lazyload"[^>]*data-original="([^"]+)"', html)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-original="(https?://[^"]+)"', html)
                if pm:
                    pic = pm.group(1)

            # 分类（类型）
            cat_name = ""
            cm = re.search(r'类型：</span>\s*<a href="/kuihua/\d+\.html"[^>]*>([^<]+)</a>', html)
            if cm:
                cat_name = cm.group(1).strip()

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

            # 状态
            remarks = ""
            sm = re.search(r'<span class="data_style">([^<]+)</span>', html)
            if sm:
                remarks = sm.group(1).strip()

            # 导演
            director = ""
            d_block = self._cut_str(html, '>导演：</span>', '</li>')
            if d_block:
                director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))

            # 主演
            actor = ""
            a_block = self._cut_str(html, '>主演：</span>', '</li>')
            if a_block:
                actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))

            # 简介：content_desc 内的 <p> 文本
            content = ""
            cm = re.search(r'<div class="content_desc[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
            if cm:
                ps = re.findall(r'<p>(.*?)</p>', cm.group(1), re.DOTALL)
                if ps:
                    content = self._strip_tags(ps[0])
            if not content:
                cm = re.search(r'<span class="left text_muted">简介：</span>(.*?)<a', html, re.DOTALL)
                if cm:
                    content = self._strip_tags(cm.group(1))
            content = html_mod.unescape(content).strip()

            # 播放列表：解析所有 playlist 块及对应线路名
            # 线路名：<a href="#playlistN" data-toggle="tab"><i class="iconfont">xxx</i> 名称</a>
            source_names = re.findall(r'href="#(playlist\d+)"[^>]*>\s*<i class="iconfont">[^<]*</i>\s*([^<]+)</a>', html)
            source_names = [(pid, name.strip()) for pid, name in source_names if name.strip()]

            # 每个 playlist 块：从该 div 开始到下一个 playlist div 或结束标记
            play_groups = []
            playlist_starts = list(re.finditer(r'<div id="(playlist\d+)"[^>]*class="tab-pane[^"]*"[^>]*>', html))
            for idx, m in enumerate(playlist_starts):
                pid = m.group(1)
                start = m.end()
                # 截止到下一个 playlist 或播放列表容器结束
                if idx + 1 < len(playlist_starts):
                    end = playlist_starts[idx + 1].start()
                else:
                    end_marker = html.find('<!-- 播放', start)
                    end = end_marker if end_marker != -1 else start + 60000
                blk = html[start:end]

                src_name = "线路%d" % (idx + 1)
                for sp_id, sp_name in source_names:
                    if sp_id == pid:
                        src_name = sp_name
                        break

                # 提取每集链接：<a href="/play/69-1-0.html">第01集</a>
                eps = re.findall(r'<a[^>]*href="(/play/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>', blk)
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
                    play_groups.append(("葵花影院", ["第1集${0}".format(pm.group(1))]))

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
                "vod_remarks": remarks,
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
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            kw = urllib.parse.quote(key)
            # search.php 在本地可能被 WAF 拦截(503加载页)，TVBox服务器环境通常可正常访问
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
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            # id 可能为完整路径 /play/xxx.html 或完整URL
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
        return [200, "", ""]

    def isVideoContent(self, ids):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
