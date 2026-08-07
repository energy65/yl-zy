# -*- coding: utf-8 -*-

"""
真狼影视 - TVBox 影视资源爬虫
网站: https://zlys9.top/
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
    """真狼影视爬虫类"""
    
    # 目标网站配置
    BASE_URL = "https://zlys9.top"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    # 微信公众号加密数据（影片简介处显示）
    _w_full_data = [148, 215, 223, 141, 224, 214, 128, 230, 196, 133, 200, 200, 215, 191, 133, 20, 151, 211, 225, 140, 213, 236, 141, 222, 199, 133, 207, 233, 212, 129, 181, 20, 158, 213, 253, 24, 184, 201, 193, 82, 88, 84, 64, 106, 11, 2, 3, 3, 67, 141, 205, 221, 182, 237, 234, 133, 243, 213, 145, 251, 168, 212, 142, 174, 153, 221, 217, 129, 234, 243, 131, 217, 248, 132, 196, 226, 215, 172, 154, 208, 203, 249, 148, 227, 196]
    # 线路文本加密数据（线路处显示）
    _w_line_data = [151, 211, 225, 140, 213, 236, 128, 222, 217, 137, 211, 217, 240, 135, 215, 136, 223, 141, 206, 200, 186, 242, 201, 135, 212, 246, 145, 208, 133, 214, 136, 166, 148, 227, 234, 129, 226, 216, 129, 216, 222, 135, 197, 216]
    _w_key = b"yuanli_wechat_2026"

    # 分类配置
    CATEGORIES = [
        {"type_id": "tv", "type_name": "电视剧"},
        {"type_id": "movie", "type_name": "电影"},
        {"type_id": "variety", "type_name": "综艺"},
        {"type_id": "anime", "type_name": "动漫"},
        {"type_id": "children", "type_name": "儿童"},
    ]

    # cat 数字 -> URL 别名映射（cat=4 同时对应 anime 和 children）
    CAT_MAP = {1: "movie", 2: "tv", 3: "variety", 4: "anime"}

    def init(self, extend=""):
        """初始化方法"""
        pass

    def getName(self):
        """获取爬虫名称"""
        return "真狼影视"

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
        return text if text else "真狼影视"

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

    # ---------- JS 反转义 & RSC 流数据解析 ----------
    @staticmethod
    def _js_unescape(s):
        """反转义 Next.js RSC 流中的 JS 字符串字面量，保留 UTF-8 字符"""
        out = []
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c == '\\' and i + 1 < n:
                nxt = s[i + 1]
                mp = {'n': '\n', 'r': '\r', 't': '\t', '"': '"', "'": "'",
                      '\\': '\\', '/': '/', 'b': '\b', 'f': '\f'}
                if nxt in mp:
                    out.append(mp[nxt]); i += 2
                elif nxt == 'u' and i + 5 < n:
                    try:
                        out.append(chr(int(s[i + 2:i + 6], 16))); i += 6
                    except Exception:
                        out.append(c); i += 1
                else:
                    out.append(c); i += 1
            else:
                out.append(c); i += 1
        return ''.join(out)

    def _parse_rsc(self, html):
        """从 HTML 中提取并拼接 Next.js RSC 流数据（self.__next_f.push 调用）"""
        if not html:
            return ""
        pushes = re.findall(r'self\.__next_f\.push\(\[\d+,"((?:[^"\\]|\\.)*)"\]\)', html, re.DOTALL)
        return "".join(self._js_unescape(p) for p in pushes)

    def _parse_rsc_videos(self, combined):
        """从 RSC 流数据中解析视频列表"""
        videos = []
        if not combined:
            return videos
        # 匹配 {"id":"...","cat":N,"title":"...","cover":"...","badge":"..."}
        for m in re.finditer(r'"id":"([^"]+)","cat":(\d+),"title":"([^"]+)","cover":"([^"]*)"', combined):
            vid, cat_num, title, cover = m.group(1), m.group(2), m.group(3), m.group(4)
            alias = self.CAT_MAP.get(int(cat_num), "movie")
            # 找 badge
            badge = ""
            bm = re.search(r'"id":"' + re.escape(vid) + r'".*?"badge":"([^"]*)"', combined)
            if bm:
                badge = bm.group(1)
            videos.append({
                "vod_id": f"{alias}/{vid}",
                "vod_name": html_mod.unescape(title),
                "vod_pic": cover,
                "vod_remarks": badge,
            })
        # 去重
        seen = set()
        unique = []
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                unique.append(v)
        return unique

    def getJson(self, url):
        """获取 JSON API 响应"""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": self.UA,
                "Accept": "application/json,text/x-component,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Referer": self.BASE_URL + "/",
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
                if "gzip" in resp.headers.get("Content-Encoding", ""):
                    data = gzip.decompress(data)
                for enc in ["utf-8", "gbk", "latin-1"]:
                    try:
                        return json.loads(data.decode(enc))
                    except Exception:
                        continue
        except Exception:
            return {}

    # ---------- 列表项解析 ----------
    def _parse_list_html(self, html):
        """从首页/分类页面解析视频列表（优先 RSC 数据，回退 HTML 解析）"""
        # 优先使用 RSC 数据（更准确，封面/标题都正确）
        combined = self._parse_rsc(html)
        if combined:
            videos = self._parse_rsc_videos(combined)
            if videos:
                return videos

        # 回退：从渲染 HTML 中解析 video-card
        videos = []
        if not html:
            return videos
        # 匹配 <a title="..." class="video-card__link" href="/detail/..."><img class="video-card__img" src="..." .../>
        for m in re.finditer(r'<a[^>]*class="[^"]*video-card__link[^"]*"[^>]*href="(/detail/(\w+)/(\w+))"[^>]*title="([^"]*)"', html):
            href, vtype, vid, title = m.group(1), m.group(2), m.group(3), m.group(4)
            # 找该 <a> 标签内的 img
            rest = html[m.end():m.end() + 500]
            pm = re.search(r'<img[^>]*src="([^"]+)"', rest)
            pic = pm.group(1) if pm else ""
            # 找 badge
            badge = ""
            bm = re.search(r'video-card__badge[^>]*>([^<]*)<', rest)
            if bm:
                badge = bm.group(1)
            if title and vid:
                videos.append({
                    "vod_id": f"{vtype}/{vid}",
                    "vod_name": html_mod.unescape(title),
                    "vod_pic": pic,
                    "vod_remarks": badge,
                })

        # 更宽松的回退
        if not videos:
            for m in re.finditer(r'<a[^>]*href="(/detail/(\w+)/(\w+))"[^>]*title="([^"]+)"', html):
                href, vtype, vid, title = m.group(1), m.group(2), m.group(3), m.group(4)
                videos.append({
                    "vod_id": f"{vtype}/{vid}",
                    "vod_name": html_mod.unescape(title),
                    "vod_pic": "",
                    "vod_remarks": "",
                })

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
            url = f"{self.BASE_URL}/category/{tid}"
            if page > 1:
                url = f"{self.BASE_URL}/category/{tid}?page={page}"

            html = self.getHtml(url)
            if not html:
                return result

            videos = self._parse_list_html(html)
            result["list"] = videos

            # 从 RSC 数据中解析分页信息
            combined = self._parse_rsc(html)
            pagecount = 1
            # 匹配 "pageCount":N 或 "totalPage":N 或 "pages":N
            pm = re.search(r'"pageCount":(\d+)', combined)
            if not pm:
                pm = re.search(r'"totalPage":(\d+)', combined)
            if not pm:
                pm = re.search(r'"pages":(\d+)', combined)
            if not pm:
                pm = re.search(r'"totalPages":(\d+)', combined)
            if pm:
                pagecount = int(pm.group(1))
            else:
                # 从分页链接推断：找最大的 page=N
                pages = re.findall(r'[?&]page=(\d+)', html)
                if pages:
                    pagecount = max(int(p) for p in pages)

            if pagecount < page:
                pagecount = page

            result["pagecount"] = str(pagecount)
            result["page"] = str(page)
            result["limit"] = str(len(videos))
            result["total"] = str(pagecount * len(videos)) if videos else "0"
            return result
        except Exception:
            return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        """获取视频详情（从 Next.js RSC 流数据中提取外链播放源）"""
        result = {"list": []}
        try:
            vid = ids[0] if isinstance(ids, list) and ids else ids
            # 注意：详情页 URL 不能加 .html 后缀，否则返回 404
            url = f"{self.BASE_URL}/detail/{vid}"
            html = self.getHtml(url)
            if not html:
                return result

            # 解析 Next.js RSC 流数据
            combined = self._parse_rsc(html)

            # 提取元信息（从 detail JSON 对象中）
            title = ""
            m = re.search(r'"title":"([^"]+)"', combined)
            if m:
                title = html_mod.unescape(m.group(1))

            pic = ""
            m = re.search(r'"cdncover":"([^"]+)"', combined)
            if m:
                pic = m.group(1)
            if not pic:
                m = re.search(r'"cover":"([^"]+)"', combined)
                if m:
                    pic = m.group(1)

            description = ""
            m = re.search(r'"description":"([^"]+)"', combined)
            if m:
                description = html_mod.unescape(m.group(1))

            director = ""
            m = re.search(r'"director":\[([^\]]*)\]', combined)
            if m:
                director = ", ".join(re.findall(r'"([^"]+)"', m.group(1)))

            actor = ""
            m = re.search(r'"actor":\[([^\]]*)\]', combined)
            if m:
                actor = ", ".join(re.findall(r'"([^"]+)"', m.group(1)))

            area = ""
            m = re.search(r'"area":\[([^\]]*)\]', combined)
            if m:
                area = ", ".join(re.findall(r'"([^"]+)"', m.group(1)))

            year = ""
            m = re.search(r'"pubdate":"([^"]+)"', combined)
            if m:
                year = m.group(1)[:4] if m.group(1) else ""

            cat_name = ""
            m = re.search(r'"moviecategory":\[([^\]]*)\]', combined)
            if m:
                cat_name = ", ".join(re.findall(r'"([^"]+)"', m.group(1)))

            remarks = ""
            m = re.search(r'"updateText":"([^"]+)"', combined)
            if m:
                remarks = html_mod.unescape(m.group(1))

            # 解析播放源（sources 数组，每个 source 含 site/name/episodes）
            # episodes 中每项有 playlink_num/url/name(可选)
            play_groups = []
            for sm in re.finditer(r'\{"site":"([^"]+)","name":"([^"]+)"[^}]*"episodes":\[([^\]]*)\]', combined):
                src_name = html_mod.unescape(sm.group(2))
                eps_str = sm.group(3)
                # 提取 playlink_num 和 url 对
                ep_pairs = re.findall(r'"playlink_num":"([^"]*)","url":"([^"]*)"', eps_str)
                # 提取 episode name（如"正片"）
                ep_names = re.findall(r'"name":"([^"]*)"', eps_str)
                ep_list = []
                for i, (num, eurl) in enumerate(ep_pairs):
                    if not eurl:
                        continue
                    ename = ep_names[i] if i < len(ep_names) else ""
                    if not ename:
                        ename = f"第{num}集" if num else "播放"
                    ep_list.append(f"{ename}${eurl}")
                if ep_list:
                    play_groups.append((src_name, ep_list))

            # 构造播放串
            play_from = "$$$".join(g[0] for g in play_groups)
            play_url = "$$$".join("#".join(g[1]) for g in play_groups)

            # 加密微信信息追加到简介
            wechat_info = self._get_wechat_info()
            desc = (description + '\n\n' + wechat_info) if description else wechat_info

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
        """搜索视频（使用 /api/search JSON API）"""
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            kw = urllib.parse.quote(key)
            url = f"{self.BASE_URL}/api/search?q={kw}"
            if page > 1:
                url = f"{url}&page={page}"

            data = self.getJson(url)
            if not data:
                return result

            items = data.get("data", {}).get("items", [])
            total = data.get("data", {}).get("total", 0)

            videos = []
            for it in items:
                vid = it.get("id", "")
                cat_num = it.get("cat", 0)
                title = it.get("title", "")
                cover = it.get("cover", "")
                badge = it.get("badge", "") or ""
                if not vid or not title:
                    continue
                alias = self.CAT_MAP.get(cat_num, "movie")
                videos.append({
                    "vod_id": f"{alias}/{vid}",
                    "vod_name": html_mod.unescape(title),
                    "vod_pic": cover,
                    "vod_remarks": badge,
                })

            # 关键词二次过滤
            if videos and key:
                k = key.lower()
                filtered = [v for v in videos if k in v.get("vod_name", "").lower()]
                if filtered:
                    videos = filtered

            result["list"] = videos
            result["page"] = str(page)
            result["total"] = str(total if total else len(videos))
            pagecount = (int(total) + 19) // 20 if total else 1
            result["pagecount"] = str(max(pagecount, page))
            return result
        except Exception:
            return result

    # ---------- 播放 ----------
    # 第三方解析接口（TVBox 会在 WebView 中打开 playUrl+url 进行嗅探）
    _PARSE_APIS = [
        "https://jx.xmflv.com/?url=",
        "https://jx.playerjy.com/?url=",
        "https://jx.parwix.com:4433/player/?v=",
    ]

    def _extract_video_url(self, html):
        """从页面 HTML 中提取视频直链（m3u8/mp4）"""
        if not html:
            return None
        m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        if m:
            return m.group(1)
        m = re.search(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
        if m:
            return m.group(1)
        return None

    def playerContent(self, flag, id, vipFlags):
        """获取播放地址（B站等提取直链，其他平台用解析接口）"""
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            play_url = id.strip() if id else ""
            if not play_url:
                return result

            if not play_url.startswith("http"):
                play_url = "https://" + play_url

            # 步骤1：尝试从页面提取直链（B站可直接提取 mp4）
            try:
                html = self.getHtml(play_url)
                if html:
                    video_url = self._extract_video_url(html)
                    if video_url:
                        result["parse"] = 0
                        result["url"] = video_url
                        result["header"] = json.dumps({
                            "User-Agent": self.UA,
                            "Referer": play_url
                        })
                        return result
            except Exception:
                pass

            # 步骤2：无法提取直链 → 用解析接口
            # playUrl 设为解析接口前缀，url 设为原始视频页 URL
            # TVBox 会在 WebView 中打开 playUrl+url，嗅探视频流
            result["parse"] = 1
            result["url"] = play_url
            result["playUrl"] = self._PARSE_APIS[0]
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


# ---------- 测试代码 ----------
if __name__ == "__main__":
    spider = Spider()
    print("=" * 60)
    print("真狼影视 - TVBox 爬虫测试")
    print("=" * 60)
    
    # 测试首页分类
    print("\n[1] 测试首页分类...")
    home = spider.homeContent({})
    print(f"分类数量: {len(home.get('class', []))}")
    for cat in home.get('class', []):
        print(f"  - {cat['type_name']} (ID: {cat['type_id']})")
    
    # 测试首页视频
    print("\n[2] 测试首页视频...")
    home_videos = spider.homeVideoContent()
    videos = home_videos.get('list', [])
    print(f"获取到 {len(videos)} 个视频")
    for v in videos[:5]:
        print(f"  - {v['vod_name']}")
    
    # 测试分类
    print("\n[3] 测试分类内容...")
    cat_result = spider.categoryContent("movie", "1", {}, {})
    print(f"分类视频数量: {len(cat_result.get('list', []))}")
    
    # 测试搜索
    print("\n[4] 测试搜索...")
    search_result = spider.searchContent("动作", False, "1")
    print(f"搜索结果数量: {len(search_result.get('list', []))}")
    
    # 测试详情
    if videos:
        print("\n[5] 测试详情...")
        vid = videos[0]['vod_id']
        detail = spider.detailContent([vid])
        if detail.get('list'):
            vod = detail['list'][0]
            print(f"标题: {vod['vod_name']}")
            print(f"简介: {vod['vod_content'][:50]}...")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
