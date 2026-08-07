# -*- coding: utf-8 -*-
"""
威视TV (weishitv.xyz) TVBox 爬虫
- MacCMS (shoutu45) 模板站点
- 分类/详情/播放/搜索 全功能
- 影片简介处显示微信公众号"源力软件汇"等加密信息
- 网站地址采用多重加密(反转+base64+XOR+ROT+base64)存储，运行时解密
"""

import re
import json
import ssl
import gzip
import base64
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
        def fetch(self, url, headers=None): return ""


class Spider(BaseSpider):
    # ===== 网站地址多重加密存储 =====
    # 加密层次: 原始URL -> 反转 -> base64 -> XOR -> ROT(+7) -> base64
    _enc_url = 'GRIMTisODE4LOwciHA9rCoVWVloRRzFgQjcJZQ=='

    # ===== 微信公众号加密信息(影片简介处显示) =====
    # XOR 加密, 运行时解密: 微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力
    _w_full_data = [146, 219, 199, 151, 215, 200, 186, 242, 201, 135, 212, 246, 145, 208, 133, 18, 212, 140, 231, 128, 227, 232, 128, 212, 240, 147, 222, 213, 142, 208, 243, 125, 221, 140, 190, 71, 144, 219, 205, 66, 88, 92, 107, 66, 92, 81, 89, 84, 70, 187, 142, 132, 219, 172, 248, 131, 242, 199, 141, 205, 197, 147, 217, 251, 128, 213, 220, 183, 135, 180, 212, 140, 231, 128, 217, 206, 141, 245, 247, 145, 223, 243, 141, 235, 239]
    # 线路文本加密数据(线路处显示): 威视TV·微信公众号源力软件汇
    _w_line_data = [146, 205, 232, 155, 207, 239, 11, 33, 167, 212, 141, 223, 218, 187, 141, 145, 215, 179, 219, 129, 213, 228, 141, 230, 232, 145, 223, 243, 141, 235, 239, 183, 143, 159, 214, 141, 193, 131, 216, 244]
    _w_key = b"weishi_wechat_2026"

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 分类配置: 威视TV 导航暴露的 4 个主分类(站点API已关闭，无更多子分类)
    CATEGORIES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "剧集"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
    ]

    def init(self, extend=""):
        self.extend = extend
        self.BASE_URL = self._get_base_url()

    def getName(self):
        return "威视TV"

    # ---------- 网站地址多重解密 ----------
    def _get_base_url(self):
        try:
            k = self._w_key
            # 5. base64 解码
            rotated = base64.b64decode(self._enc_url.encode('ascii'))
            # 4. ROT 反位移 (-7)
            xored = [(c - 7) & 0xFF for c in rotated]
            # 3. XOR 解密
            b = bytes([xored[i] ^ k[i % len(k)] for i in range(len(xored))])
            s = b.decode('ascii')
            # 2. base64 解码
            s = base64.b64decode(s.encode('ascii')).decode('utf-8')
            # 1. 反转还原
            return s[::-1]
        except Exception:
            return "https://weishitv.xyz"

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
        return text if text else "威视TV"

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

    def getHtml(self, url):
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

    # ---------- 字符串截取工具(兼容TVBox cat.js环境) ----------
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
        """从分类/搜索/首页页面解析视频列表(public-list-box 结构)
        采用 public-list-exp 锚点 + 上下文窗口方式，对换行符(\n/\r\n)鲁棒"""
        videos = []
        if not html:
            return videos

        # 以 public-list-exp 锚点定位每个视频项, 取锚点前后窗口提取字段
        # 锚点: <a ... class="public-list-exp" href="/index.php/vod/detail/id/{vid}.html" title="{title}">
        pattern = re.compile(
            r'<a[^>]*class="public-list-exp"[^>]*href="/index\.php/vod/detail/id/(\d+)\.html"[^>]*title="([^"]*)"'
        )
        for m in pattern.finditer(html):
            try:
                vid = m.group(1)
                title = m.group(2).replace("在线观看", "").strip()
                if not title:
                    continue
                # 窗口: 锚点后600字符(含img data-src封面与public-list-prb备注)
                # 封面/备注均在锚点之后的同一 public-list-box 块内
                start = m.start()
                end = min(len(html), m.end() + 600)
                win = html[start:end]

                # 封面: data-src > data-original > src(排除占位gif)
                pic = ""
                pm = re.search(r'data-src="([^"]+)"', win)
                if pm:
                    pic = pm.group(1)
                if not pic:
                    pm = re.search(r'data-original="([^"]+)"', win)
                    if pm:
                        pic = pm.group(1)
                if not pic:
                    pm = re.search(r'<img[^>]*src="([^"]+)"', win)
                    if pm and 'base64' not in pm.group(1) and 'loading' not in pm.group(1):
                        pic = pm.group(1)

                # 备注: public-list-prb (集数/清晰度)
                remarks = ""
                rm = re.search(r'class="public-list-prb[^"]*"[^>]*>\s*([^<]*)</span>', win)
                if rm:
                    remarks = rm.group(1).strip()

                title = html_mod.unescape(title)
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
            except Exception:
                continue

        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

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
                url = "{0}/index.php/vod/show/id/{1}.html".format(self.BASE_URL, tid)
            else:
                url = "{0}/index.php/vod/show/id/{1}/page/{2}.html".format(self.BASE_URL, tid, page)

            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_list_html(html)
            result["list"] = videos

            # 解析总页数: <div class="rg10">1&nbsp;/&nbsp;2018页</div>
            pagecount = 1
            pm = re.search(r'/\s*&nbsp;\s*(\d+)\s*页', html)
            if not pm:
                pm = re.search(r'/\s*(\d+)\s*页', html)
            if pm:
                pagecount = int(pm.group(1))
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
            url = "{0}/index.php/vod/detail/id/{1}.html".format(self.BASE_URL, vid)
            html = self.getHtml(url)
            if not html:
                return result

            # 标题: this-desc-title 优先, 再 <title>《xxx》
            title = ""
            tm = re.search(r'<div class="this-desc-title">([^<]+)</div>', html)
            if tm:
                title = tm.group(1).strip()
            if not title:
                tm = re.search(r'<title>《([^》]+)》', html)
                if tm:
                    title = tm.group(1).strip()
            title = html_mod.unescape(title)

            # 封面: this-pic-bj 背景图
            pic = ""
            pm = re.search(r'class="this-pic-bj"[^>]*background-image:\s*url\(\'([^\']+)\'\)', html)
            if pm:
                pic = pm.group(1)
            if not pic:
                pm = re.search(r'data-original="(https?://[^"]+)"', html)
                if pm:
                    pic = pm.group(1)

            # info-parameter 区块提取年份/地区/类型/状态
            year = ""
            area = ""
            cat_name = ""
            remarks = ""
            ym = re.search(r'<em class="cor4">年份：</em>([^<]+)', html)
            if ym:
                year = ym.group(1).strip()
            am = re.search(r'<em class="cor4">地区：</em>([^<]+)', html)
            if am:
                area = am.group(1).strip()
            cm = re.search(r'<em class="cor4">类型：</em>\s*<a[^>]*>([^<]+)</a>', html)
            if cm:
                cat_name = cm.group(1).strip()
            sm = re.search(r'<em class="cor4">状态：</em>\s*<span>([^<]+)</span>', html)
            if sm:
                remarks = sm.group(1).strip()

            # 导演
            director = ""
            d_block = self._cut_str(html, '<strong class="r6">导演:</strong>', '</div>')
            if d_block:
                director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))
            if not director:
                d_block = self._cut_str(html, '<em class="cor4">导演：</em>', '</li>')
                if d_block:
                    director = ', '.join(re.findall(r'>([^<]+)</a>', d_block))

            # 主演
            actor = ""
            a_block = self._cut_str(html, '<strong class="r6">演员:</strong>', '</div>')
            if a_block:
                actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))
            if not actor:
                a_block = self._cut_str(html, '<em class="cor4">主演：</em>', '</li>')
                if a_block:
                    actor = ', '.join(re.findall(r'>([^<]+)</a>', a_block))

            # 简介: height_limit 区块优先
            content = ""
            cm = re.search(r'<div id="height_limit" class="text">(.*?)</div>', html, re.DOTALL)
            if cm:
                content = self._strip_tags(cm.group(1))
                content = content.replace("简介:", "").replace("简介：", "").strip()
            if not content:
                cm = re.search(r'<em class="cor4">简介：</em>([^<]+)', html)
                if cm:
                    content = cm.group(1).strip()
            content = html_mod.unescape(content).strip()

            # 播放列表: 解析线路名(anthology-tab) + 每线路剧集(anthology-list-box)
            # 线路名: <a class="swiper-slide line-btn">...名称<span class="badge">N</span></a>
            line_btns = re.findall(r'<a class="swiper-slide line-btn"[^>]*>(.*?)</a>', html, re.DOTALL)
            source_names = []
            for lb in line_btns:
                name = self._strip_tags(lb)
                name = html_mod.unescape(name).replace("\xa0", "").strip()
                # 去除尾部数量(如 "播放线路35")
                name = re.sub(r'\d+$', '', name).strip()
                source_names.append(name if name else "线路")

            # 每个线路剧集块: anthology-list-box
            list_boxes = re.findall(r'<div class="anthology-list-box[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
            if not list_boxes:
                list_boxes = self._cut_all(html, '<div class="anthology-list-box', '</div>\n        </div>')

            play_groups = []
            for idx, box in enumerate(list_boxes):
                src_name = source_names[idx] if idx < len(source_names) else "线路%d" % (idx + 1)
                # 提取每集: <a class="episode-btn" href="/index.php/vod/play/id/{vid}/sid/{sid}/nid/{nid}.html">第01集</a>
                eps = re.findall(r'<a[^>]*href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]+)</a>', box)
                if not eps:
                    eps = re.findall(r'<a[^>]*href="(/?vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]+)</a>', box)
                ep_list = []
                for ep_url, ep_name in eps:
                    ep_name = html_mod.unescape(ep_name).strip()
                    if not ep_name:
                        ep_name = "播放"
                    ep_list.append("{0}${1}".format(ep_name, ep_url))
                if ep_list:
                    play_groups.append((src_name, ep_list))

            # 回退: 从详情页立即播放链接构造单集
            if not play_groups:
                pm = re.search(r'href="(/index\.php/vod/play/id/{0}/sid/\d+/nid/\d+\.html)"'.format(vid), html)
                if pm:
                    play_groups.append((self._get_line_info(), ["第1集${0}".format(pm.group(1))]))

            # 构造播放串
            play_from = "$$$".join(g[0] for g in play_groups)
            play_url = "$$$".join("#".join(g[1]) for g in play_groups)

            # 加密微信信息追加到简介
            wechat_info = self._get_wechat_info()
            desc = (content + '\n\n' + wechat_info) if content else wechat_info

            # 线路名使用加密信息兜底
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
            if page <= 1:
                url = "{0}/index.php/vod/search.html?wd={1}".format(self.BASE_URL, kw)
            else:
                url = "{0}/index.php/vod/search.html?wd={1}&page={2}".format(self.BASE_URL, kw, page)

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

            # 解析搜索结果总页数
            pagecount = 1
            pm = re.search(r'/\s*&nbsp;\s*(\d+)\s*页', html)
            if not pm:
                pm = re.search(r'/\s*(\d+)\s*页', html)
            if pm:
                pagecount = int(pm.group(1))
            result["pagecount"] = str(pagecount)
            result["total"] = str(len(videos))
            return result
        except Exception:
            return result

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            # id 可能为完整路径 /index.php/vod/play/id/xxx.html 或完整URL
            if id.startswith("http"):
                play_url = id
            elif id.startswith("/"):
                play_url = self.BASE_URL + id
            else:
                play_url = self.BASE_URL + "/index.php/vod/play/id/" + id + ".html"

            html = self.getHtml(play_url)
            if not html:
                return result

            # 提取 player_aaaa JSON 的 url 字段(MacCMS 标准, encrypt=0 为明文直链)
            video_url = ""
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
            if m:
                try:
                    info = json.loads(m.group(1))
                    video_url = info.get("url", "")
                except Exception:
                    video_url = ""
            # 回退: 直接匹配 m3u8/mp4 直链
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
