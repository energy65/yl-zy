# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import time
import urllib.parse
import urllib.request
import http.cookiejar

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
    BASE_URL = "https://www.bykhw.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

    # 微信公众号加密数据
    _w_data = [142, 203, 199, 140, 202, 192, 186, 242, 201, 135, 212, 246, 145, 208, 133, 18, 212, 140, 251, 144, 227, 243, 157, 220, 240, 147, 222, 213, 142, 208, 243, 125, 221, 140, 190, 71, 140, 203, 205, 89, 69, 84, 107, 66, 92, 81, 89, 84, 70, 187, 142, 132, 219, 172, 228, 147, 242, 220, 144, 197, 197, 147, 217, 251, 128, 213, 220, 183, 135, 180, 212, 140, 251, 144, 217, 213, 144, 253, 247, 145, 223, 243, 141, 235, 239]
    # 线路文本加密数据
    _w_line_data = [131, 228, 220, 128, 255, 208, 186, 202, 212, 139, 207, 231, 89, 185, 136, 160, 215, 188, 240, 145, 209, 251, 146, 219, 224]
    _w_key = b"kuihua_wechat_2026"

    # 分类配置: type_id格式为 parent-child, child=0表示大类
    CATEGORIES = [
        # 电影
        {"type_id": "1-0", "type_name": "电影"},
        {"type_id": "1-2", "type_name": "动作片"},
        {"type_id": "1-3", "type_name": "喜剧片"},
        {"type_id": "1-4", "type_name": "爱情片"},
        {"type_id": "1-5", "type_name": "科幻片"},
        {"type_id": "1-6", "type_name": "恐怖片"},
        {"type_id": "1-7", "type_name": "剧情片"},
        {"type_id": "1-8", "type_name": "战争片"},
        {"type_id": "1-10", "type_name": "悬疑片"},
        {"type_id": "1-11", "type_name": "动画片"},
        {"type_id": "1-12", "type_name": "犯罪片"},
        {"type_id": "1-13", "type_name": "奇幻片"},
        {"type_id": "1-48", "type_name": "影视解说"},
        {"type_id": "1-49", "type_name": "预告片"},
        # 电视剧
        {"type_id": "14-0", "type_name": "电视剧"},
        {"type_id": "14-15", "type_name": "国产剧"},
        {"type_id": "14-16", "type_name": "香港剧"},
        {"type_id": "14-17", "type_name": "台湾剧"},
        {"type_id": "14-18", "type_name": "欧美剧"},
        {"type_id": "14-19", "type_name": "韩国剧"},
        {"type_id": "14-20", "type_name": "日本剧"},
        {"type_id": "14-21", "type_name": "泰剧"},
        {"type_id": "14-22", "type_name": "海外剧"},
        # 综艺
        {"type_id": "23-0", "type_name": "综艺"},
        {"type_id": "23-24", "type_name": "大陆综艺"},
        {"type_id": "23-25", "type_name": "日韩综艺"},
        {"type_id": "23-26", "type_name": "港台综艺"},
        {"type_id": "23-27", "type_name": "欧美综艺"},
        # 动漫
        {"type_id": "28-0", "type_name": "动漫"},
        {"type_id": "28-29", "type_name": "国产动漫"},
        {"type_id": "28-30", "type_name": "日韩动漫"},
        {"type_id": "28-31", "type_name": "欧美动漫"},
        {"type_id": "28-32", "type_name": "港台动漫"},
        {"type_id": "28-33", "type_name": "海外动漫"},
        {"type_id": "28-35", "type_name": "有声动漫"},
        # 短剧
        {"type_id": "34-0", "type_name": "短剧"},
        {"type_id": "34-36", "type_name": "女频恋爱"},
        {"type_id": "34-37", "type_name": "反转爽剧"},
        {"type_id": "34-38", "type_name": "脑洞悬疑"},
        {"type_id": "34-39", "type_name": "年代穿越"},
        {"type_id": "34-40", "type_name": "古装仙侠"},
        {"type_id": "34-41", "type_name": "现代都市"},
        # 体育
        {"type_id": "42-0", "type_name": "体育赛事"},
        {"type_id": "42-43", "type_name": "篮球"},
        {"type_id": "42-44", "type_name": "足球"},
        {"type_id": "42-45", "type_name": "网球"},
        {"type_id": "42-46", "type_name": "斯诺克"},
        # 纪录片
        {"type_id": "9-0", "type_name": "纪录片"},
        # 演唱会
        {"type_id": "47-0", "type_name": "演唱会"},
    ]

    def init(self, extend=""):
        pass

    def getName(self):
        return "葵花影视网"

    # ========== 解密方法 ==========
    def _get_wechat_info(self):
        try:
            key = self._w_key
            data = self._w_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                data = self._w_data
                result = []
                for i in range(len(data)):
                    result.append(chr(data[i] ^ key[i % len(key)]))
                return ''.join(result)
            except Exception:
                return ''

    def _get_line_info(self):
        try:
            key = self._w_key
            data = self._w_line_data
            plain = bytearray(len(data))
            for i in range(len(data)):
                plain[i] = data[i] ^ key[i % len(key)]
            return plain.decode('utf-8')
        except Exception:
            try:
                key = self._w_key
                data = self._w_line_data
                result = []
                for i in range(len(data)):
                    result.append(chr(data[i] ^ key[i % len(key)]))
                return ''.join(result)
            except Exception:
                return '葵花影视'

    # ========== 反爬虫绕过 ==========
    def _mask32(self, x):
        return x & 0xFFFFFFFF

    def _rotate_left(self, lValue, iShiftBits):
        return self._mask32((lValue << iShiftBits) | (lValue >> (32 - iShiftBits)))

    def _add_unsigned(self, lX, lY):
        lX8 = lX & 0x80000000; lY8 = lY & 0x80000000
        lX4 = lX & 0x40000000; lY4 = lY & 0x40000000
        lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF)
        if lX4 & lY4:
            return lResult ^ 0x80000000 ^ lX8 ^ lY8
        if lX4 | lY4:
            if lResult & 0x40000000:
                return lResult ^ 0xC0000000 ^ lX8 ^ lY8
            else:
                return lResult ^ 0x40000000 ^ lX8 ^ lY8
        return lResult ^ lX8 ^ lY8

    def _md5_F(self, x, y, z): return (x & y) | ((~x) & z)
    def _md5_G(self, x, y, z): return (x & z) | (y & (~z))
    def _md5_H(self, x, y, z): return x ^ y ^ z
    def _md5_I(self, x, y, z): return y ^ (x | (~z))

    def _md5_FF(self, a, b, c, d, x, s, ac):
        a = self._add_unsigned(a, self._add_unsigned(self._add_unsigned(self._md5_F(b, c, d), x), ac))
        return self._add_unsigned(self._rotate_left(a, s), b)

    def _md5_GG(self, a, b, c, d, x, s, ac):
        a = self._add_unsigned(a, self._add_unsigned(self._add_unsigned(self._md5_G(b, c, d), x), ac))
        return self._add_unsigned(self._rotate_left(a, s), b)

    def _md5_HH(self, a, b, c, d, x, s, ac):
        a = self._add_unsigned(a, self._add_unsigned(self._add_unsigned(self._md5_H(b, c, d), x), ac))
        return self._add_unsigned(self._rotate_left(a, s), b)

    def _md5_II(self, a, b, c, d, x, s, ac):
        a = self._add_unsigned(a, self._add_unsigned(self._add_unsigned(self._md5_I(b, c, d), x), ac))
        return self._add_unsigned(self._rotate_left(a, s), b)

    _MD5_FUNCS = None

    def _get_md5_funcs(self):
        if self._MD5_FUNCS is None:
            self._MD5_FUNCS = {
                'FF': self._md5_FF, 'GG': self._md5_GG,
                'HH': self._md5_HH, 'II': self._md5_II
            }
        return self._MD5_FUNCS

    def _convert_to_word_array(self, s):
        lMessageLength = len(s)
        lNumberOfWords_temp1 = lMessageLength + 8
        lNumberOfWords_temp2 = (lNumberOfWords_temp1 - (lNumberOfWords_temp1 % 64)) // 64
        lNumberOfWords = (lNumberOfWords_temp2 + 1) * 16
        lWordArray = [0] * lNumberOfWords
        lByteCount = 0
        while lByteCount < lMessageLength:
            lWordCount = (lByteCount - (lByteCount % 4)) // 4
            lBytePosition = (lByteCount % 4) * 8
            lWordArray[lWordCount] = lWordArray[lWordCount] | (ord(s[lByteCount]) << lBytePosition)
            lByteCount += 1
        lWordCount = (lByteCount - (lByteCount % 4)) // 4
        lBytePosition = (lByteCount % 4) * 8
        lWordArray[lWordCount] = lWordArray[lWordCount] | (0x80 << lBytePosition)
        lWordArray[lNumberOfWords - 2] = lMessageLength << 3
        lWordArray[lNumberOfWords - 1] = lMessageLength >> 29
        return lWordArray

    def _word_to_hex(self, lValue):
        result = ""
        for lCount in range(4):
            lByte = (lValue >> (lCount * 8)) & 255
            temp = "0" + format(lByte, 'x')
            result += temp[-2:]
        return result

    def _parse_js_operations(self, js_text):
        """从JS源码中解析FF/GG/HH/II操作序列"""
        m = re.search(r'for\(k=0(.+?)var temp=', js_text, re.DOTALL)
        if not m:
            return None, None
        loop_body = m.group(1)
        hash_m = re.search(r'"/([0-9a-f]+)/"\+temp\+"(\d+)/"', js_text)
        if not hash_m:
            return None, None
        prefix = hash_m.group(1)
        suffix = hash_m.group(2)
        ops = []
        pattern = r'([abcd])\s*=\s*(FF|GG|HH|II)\(\s*([abcd])\s*,\s*([abcd])\s*,\s*([abcd])\s*,\s*([abcd])\s*,\s*x\[k\s*\+\s*(\d+)\]\s*,\s*S(\d+)(\d+)\s*,\s*(0x[0-9A-Fa-f]+)\s*\)'
        for m2 in re.finditer(pattern, loop_body):
            ops.append((
                m2.group(1), m2.group(2), m2.group(3), m2.group(4),
                m2.group(5), m2.group(6), int(m2.group(7)),
                int(m2.group(8) + m2.group(9)), int(m2.group(10), 16)
            ))
        return ops, (prefix, suffix)

    def _compute_hash(self, c2, ops, prefix, suffix):
        """使用解析的操作序列计算hash"""
        S = {11: 7, 12: 12, 13: 17, 14: 22, 21: 5, 22: 9, 23: 14, 24: 20,
             31: 4, 32: 11, 33: 16, 34: 23, 41: 6, 42: 10, 43: 15, 44: 21}
        x = self._convert_to_word_array(c2)
        a = 0x67452301; b = 0xEFCDAB89; c = 0x98BADCFE; d = 0x10325476
        funcs = self._get_md5_funcs()
        for k in range(0, len(x), 16):
            AA, BB, CC, DD = a, b, c, d
            for (target, func_name, p1, p2, p3, p4, x_idx, s_num, const) in ops:
                vals = {'a': a, 'b': b, 'c': c, 'd': d}
                result = funcs[func_name](vals[p1], vals[p2], vals[p3], vals[p4], x[k + x_idx], S[s_num], const)
                if target == 'a': a = result
                elif target == 'b': b = result
                elif target == 'c': c = result
                elif target == 'd': d = result
            a = self._add_unsigned(a, AA)
            b = self._add_unsigned(b, BB)
            c = self._add_unsigned(c, CC)
            d = self._add_unsigned(d, DD)
        temp = self._word_to_hex(a) + self._word_to_hex(b) + self._word_to_hex(c) + self._word_to_hex(d)
        return ("/" + prefix + "/" + temp + suffix + "/").lower()

    # ========== HTTP请求 ==========
    def _get_ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1:HIGH:!aNULL:!MD5")
        except Exception:
            pass
        return ctx

    def getHtml(self, url, bypass=True):
        """获取页面HTML，支持反爬虫绕过"""
        ctx = self._get_ctx()
        if bypass:
            # 需要cookie jar来处理反爬虫挑战
            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj),
                urllib.request.HTTPSHandler(context=ctx)
            )
            headers = {
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": self.BASE_URL + "/"
            }
        else:
            # 不使用cookie jar和opener，避免触发验证码
            opener = None
            headers = {
                "User-Agent": self.UA,
                "Accept-Encoding": "gzip",
                "Referer": self.BASE_URL + "/"
            }
        try:
            req = urllib.request.Request(url, headers=headers)
            if opener:
                r = opener.open(req, timeout=20)
            else:
                r = urllib.request.urlopen(req, timeout=20, context=ctx)
            data = r.read()
            ce = r.headers.get("Content-Encoding", "")
            if "gzip" in ce:
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            # 检查是否为反爬虫挑战页面
            if bypass and b'c2=' in data and len(data) < 1000:
                data = self._bypass_challenge(url, opener, data)
            for enc in ["gbk", "utf-8", "gb2312", "latin-1"]:
                try:
                    return data.decode(enc)
                except Exception:
                    continue
            return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _bypass_challenge(self, url, opener, body):
        """绕过反爬虫挑战"""
        try:
            body_str = body.decode('gbk', 'ignore')
            c2_m = re.search(r'c2="([^"]+)"', body_str)
            js_m = re.search(r'src="(/nnxswnn/\d+\.js[^"]*)"', body_str)
            if not c2_m or not js_m:
                return body
            c2 = c2_m.group(1)
            # 获取JS文件
            js_url = self.BASE_URL + js_m.group(1)
            req_js = urllib.request.Request(js_url, headers={
                "User-Agent": self.UA,
                "Referer": url
            })
            r_js = opener.open(req_js, timeout=20)
            js_text = r_js.read().decode('utf-8', 'ignore')
            # 解析操作并计算hash
            ops, (prefix, suffix) = self._parse_js_operations(js_text)
            if not ops:
                return body
            hash_path = self._compute_hash(c2, ops, prefix, suffix)
            validate_url = self.BASE_URL + hash_path
            # 验证
            req2 = urllib.request.Request(validate_url, headers={
                "User-Agent": self.UA,
                "Referer": url
            })
            r2 = opener.open(req2, timeout=20)
            r2.read()
            time.sleep(0.5)
            # 重新请求原页面
            req3 = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept-Encoding": "gzip, deflate",
                "Referer": self.BASE_URL + "/"
            })
            r3 = opener.open(req3, timeout=20)
            data = r3.read()
            ce = r3.headers.get("Content-Encoding", "")
            if "gzip" in ce:
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            # 如果仍然是挑战页面，再试一次
            if b'c2=' in data and len(data) < 1000:
                time.sleep(1)
                req4 = urllib.request.Request(url, headers={
                    "User-Agent": self.UA,
                    "Accept-Encoding": "gzip, deflate",
                    "Referer": self.BASE_URL + "/"
                })
                r4 = opener.open(req4, timeout=20)
                data = r4.read()
                ce = r4.headers.get("Content-Encoding", "")
                if "gzip" in ce:
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        pass
            return data
        except Exception:
            return body

    # ========== HTML解析 ==========
    def _parse_video_list(self, html):
        """从HTML中解析视频列表"""
        videos = []
        # 匹配 <dl class="B BHomeList m1"> 块
        pattern = r'<dl class="B BHomeList[^"]*">(.*?)</dl>'
        for m in re.finditer(pattern, html, re.DOTALL):
            block = m.group(1)
            try:
                # 提取链接和ID
                link_m = re.search(r'<a href="/kuihuamv/(\d+)/"', block)
                if not link_m:
                    continue
                vid = link_m.group(1)
                # 提取图片
                img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
                if not img_m:
                    img_m = re.search(r'<img[^>]+data-src="([^"]+)"', block)
                pic = img_m.group(1) if img_m else ''
                # 提取标题
                title_m = re.search(r'<img[^>]+alt="([^"]*)"', block)
                if not title_m:
                    title_m = re.search(r'<dt>\s*<a[^>]*>([^<]+)</a>', block)
                title = title_m.group(1) if title_m else ''
                # 提取分类
                cls_m = re.search(r'<span class="ysj">([^<]*)</span>', block)
                cls = cls_m.group(1) if cls_m else ''
                # 提取备注
                remark_m = re.search(r'<span class="bott">.*?<a[^>]*>([^<]*)</a>', block, re.DOTALL)
                remarks = remark_m.group(1) if remark_m else ''
                if title and vid:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remarks,
                        "vod_class": cls,
                    })
            except Exception:
                continue
        return videos

    def _add_wechat_to_desc(self, desc):
        """在简介中添加微信公众号信息"""
        wechat = self._get_wechat_info()
        if wechat:
            return (desc + '\n\n' + wechat) if desc else wechat
        return desc

    # ========== TVBox接口实现 ==========
    def homeContent(self, filter):
        return {"class": self.CATEGORIES, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL + "/")
        if not html:
            return result
        videos = self._parse_video_list(html)
        result["list"] = videos[:30]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            # 解析type_id: parent-child
            parts = str(tid).split("-")
            if len(parts) != 2:
                return result
            parent = parts[0]
            child = parts[1]
            page = int(pg) if pg and str(pg).isdigit() else 1
            url = f"{self.BASE_URL}/kuihuamb/{parent}-{child}-0-0-0-{page}.html"
            html = self.getHtml(url)
            if not html or len(html) < 1000:
                # 如果反爬虫绕过失败，尝试大类页面
                cat_url = f"{self.BASE_URL}/kuihuamc{parent}/"
                html = self.getHtml(cat_url, bypass=False)
                if not html:
                    return result
            videos = self._parse_video_list(html)
            # 如果是子分类，按分类名过滤
            if child != "0" and videos:
                cat_name = ""
                for c in self.CATEGORIES:
                    if c["type_id"] == str(tid):
                        cat_name = c["type_name"]
                        break
                if cat_name:
                    videos = [v for v in videos if cat_name in v.get("vod_class", "") or not v.get("vod_class")]
            if videos:
                result["list"] = videos
                result["total"] = str(len(videos))
                # 从页面中提取总页数
                page_m = re.search(r'/kuihuamb/\d+-\d+-0-0-0-(\d+)\.html[^"]*"[^>]*>末页', html)
                if page_m:
                    result["pagecount"] = page_m.group(1)
                else:
                    pages = re.findall(r'/kuihuamb/\d+-\d+-0-0-0-(\d+)\.html', html)
                    if pages:
                        result["pagecount"] = str(max(int(p) for p in pages))
                    else:
                        result["pagecount"] = "1" if len(videos) < 30 else str(page + 1)
            return result
        except Exception:
            return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        url = f"{self.BASE_URL}/kuihuamv/{vid}/"
        html = self.getHtml(url, bypass=False)
        if not html:
            return result
        try:
            # 标题
            title_m = re.search(r'<h1>([^<]+)</h1>', html)
            title = title_m.group(1).strip() if title_m else ''
            if not title:
                return result
            # 封面
            pic_m = re.search(r'<div class="Dimg">.*?<img src="([^"]+)"', html, re.DOTALL)
            pic = pic_m.group(1) if pic_m else ''
            # 类型
            cat_m = re.search(r'<span>类型：</span><a[^>]*>([^<]+)</a>', html)
            cat = cat_m.group(1).strip() if cat_m else ''
            # 导演
            dir_m = re.search(r'<span>导演：</span><a[^>]*>([^<]*)</a>', html)
            director = dir_m.group(1).strip() if dir_m else ''
            # 主演
            act_m = re.search(r'<span>主演：</span><a[^>]*>([^<]*)</a>', html)
            actor = act_m.group(1).strip() if act_m else ''
            # 年份
            year_m = re.search(r'<span>年份：</span>(\d+)', html)
            year = year_m.group(1) if year_m else ''
            # 地区
            area_m = re.search(r'<span>地区：</span>([^<]+)', html)
            area = area_m.group(1).strip() if area_m else ''
            # 状态
            status_m = re.search(r'<span>状态：</span>([^<]+)', html)
            remarks = status_m.group(1).strip() if status_m else ''
            # 简介
            intro_m = re.search(r'<span>剧情：</span>(.*?)</dd>', html, re.DOTALL)
            intro = intro_m.group(1).strip() if intro_m else ''
            intro = re.sub(r'<[^>]+>', '', intro).strip()
            # 添加微信公众号信息
            intro = self._add_wechat_to_desc(intro)
            # 集数列表
            episodes = []
            ep_pattern = r'<li>\s*<a href="(/kuihuamv/\d+/v\d+r\d+\.html)">([^<]+)</a>'
            for ep_m in re.finditer(ep_pattern, html):
                ep_url = ep_m.group(1)
                ep_name = ep_m.group(2).strip()
                episodes.append(f"{ep_name}${ep_url}")
            # 如果没有集数，使用详情页自身的播放链接
            if not episodes:
                og_m = re.search(r'og:video:url"\s+content="([^"]+)"', html)
                source_m = re.search(r'<source[^>]+src="([^"]+)"', html)
                play_url = og_m.group(1) if og_m else (source_m.group(1) if source_m else '')
                if play_url:
                    episodes.append(f"播放${play_url}")
            line_info = self._get_line_info()
            vod = {
                "vod_id": str(vid),
                "vod_name": title,
                "vod_pic": pic,
                "vod_actor": actor,
                "vod_director": director,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_content": intro,
                "vod_class": cat,
                "type_name": cat,
                "vod_play_from": line_info,
                "vod_play_url": '#'.join(episodes) if episodes else '',
            }
            result['list'] = [vod]
            return result
        except Exception:
            return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            kw = key.strip()
            kw_lower = kw.lower()
            page = int(pg) if pg and str(pg).isdigit() else 1
            all_videos = []
            seen_ids = set()
            # 从所有大类页面获取视频列表
            cat_urls = [
                f"{self.BASE_URL}/kuihuamc1/",
                f"{self.BASE_URL}/kuihuamc14/",
                f"{self.BASE_URL}/kuihuamc23/",
                f"{self.BASE_URL}/kuihuamc28/",
                f"{self.BASE_URL}/kuihuamc34/",
                f"{self.BASE_URL}/kuihuamc9/",
                f"{self.BASE_URL}/kuihuamc47/",
            ]
            for cat_url in cat_urls:
                html = self.getHtml(cat_url, bypass=False)
                if not html:
                    continue
                videos = self._parse_video_list(html)
                for v in videos:
                    vid = v["vod_id"]
                    if vid not in seen_ids:
                        seen_ids.add(vid)
                        all_videos.append(v)
            # 按关键词过滤
            matched = []
            for v in all_videos:
                name = v.get("vod_name", "").lower()
                cls = v.get("vod_class", "").lower()
                score = 0
                if kw_lower == name:
                    score = 100
                elif kw_lower in name:
                    score = 50
                elif kw_lower in cls:
                    score = 30
                else:
                    # 分词匹配
                    for i in range(len(kw_lower) - 1):
                        chunk = kw_lower[i:i+2]
                        if chunk in name:
                            score += 1
                if score > 0:
                    matched.append((score, v))
            # 按分数排序
            matched.sort(key=lambda x: x[0], reverse=True)
            videos = [v for (s, v) in matched]
            # 如果没有匹配，返回热门
            if not videos:
                videos = all_videos[:20]
            if videos:
                page_size = 30
                total = len(videos)
                total_pages = (total + page_size - 1) // page_size
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                result["list"] = videos[start_idx:end_idx]
                result["pagecount"] = str(total_pages)
                result["total"] = str(total)
            return result
        except Exception:
            return result

    def playerContent(self, flag, id, vipFlags):
        # 处理播放ID
        play_url = id
        if '$' in play_url:
            play_url = play_url.split('$', 1)[1]
        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
            "Accept": "*/*",
        }
        # 如果已经是直接的视频URL
        if play_url.startswith("http") and (".m3u8" in play_url or ".mp4" in play_url):
            return {
                "url": play_url,
                "parse": "0",
                "header": json.dumps(play_headers),
                "playUrl": "",
                "subtitle": ""
            }
        # 否则获取播放页面提取m3u8
        if not play_url.startswith("http"):
            play_url = self.BASE_URL + play_url
        html = self.getHtml(play_url)
        if html:
            # 优先从<source>标签提取
            source_m = re.search(r'<source[^>]+src="([^"]+)"', html)
            if source_m:
                m3u8_url = source_m.group(1)
                if m3u8_url.startswith("//"):
                    m3u8_url = "https:" + m3u8_url
                is_direct = ".m3u8" in m3u8_url or ".mp4" in m3u8_url
                return {
                    "url": m3u8_url,
                    "parse": "0" if is_direct else "1",
                    "header": json.dumps(play_headers),
                    "playUrl": "",
                    "subtitle": ""
                }
            # 从og:video:url提取
            og_m = re.search(r'og:video:url"\s+content="([^"]+)"', html)
            if og_m:
                m3u8_url = og_m.group(1)
                if m3u8_url.startswith("//"):
                    m3u8_url = "https:" + m3u8_url
                is_direct = ".m3u8" in m3u8_url or ".mp4" in m3u8_url
                return {
                    "url": m3u8_url,
                    "parse": "0" if is_direct else "1",
                    "header": json.dumps(play_headers),
                    "playUrl": "",
                    "subtitle": ""
                }
            # 从JS变量提取
            js_m = re.search(r'(https?://[^"\'<>]+\.m3u8[^"\'<>]*)', html)
            if js_m:
                m3u8_url = js_m.group(1)
                return {
                    "url": m3u8_url,
                    "parse": "0",
                    "header": json.dumps(play_headers),
                    "playUrl": "",
                    "subtitle": ""
                }
        return {
            "url": play_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": ""
        }

    def __jsEvalReturn(self):
        return {"proxy": None}
