# -*- coding: utf-8 -*-

import re
import json
import ssl
import gzip
import time
import base64
import urllib.request
import urllib.parse
import urllib.error
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
        def isVideoContent(self, ids): return False
        def manualVideoCheck(self): return False
        def manualSniffer(self, ids): return False


class Spider(BaseSpider):
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    BASE_URL = "https://cn1.ifn.watch"

    # ==================== 推广文案 ====================
    _WX_TEXT = "\u5fae\u4fe1\u516c\u4f17\u53f7\uff1a\u6e90\u529b\u8f6f\u4ef6\u6c47\n\u66f4\u591a\u4f18\u8d28\u8d44\u6e90\u5c3d\u5728\u6e90\u529b"

    # ==================== 分类配置 ====================
    # 网站分类ID: 3=电影, 4=剧集, 5=综艺, 6=动漫, 7=纪录片, 8=短剧, 40=4K
    # subGenreId 在 mediaId 的第4段，用于客户端过滤
    # 电影 subGenreId 映射: 19=喜剧 20=爱情 21=动作 22=犯罪 23=科幻 24=奇幻 27=惊悚 28=剧情 32=悬疑 113=动画 123=恐怖 124=同性 125=网络电影
    # 电视剧 subGenreId 映射: 126=古装 128=武侠 130=家庭 131=青春 132=都市 133=喜剧 137=悬疑 138=罪案 144=科幻 146=爱情 150=动作 151=惊悚 152=剧情 153=同性 16=欧美剧 18=英剧

    CATEGORIES = [
        # ---- 电影大类 + 细分子类型 ----
        {"type_id": "3", "type_name": "\u7535\u5f71"},
        {"type_id": "3_28", "type_name": "\u5267\u60c5\u7247"},
        {"type_id": "3_19", "type_name": "\u559c\u5267\u7247"},
        {"type_id": "3_21", "type_name": "\u52a8\u4f5c\u7247"},
        {"type_id": "3_20", "type_name": "\u7231\u60c5\u7247"},
        {"type_id": "3_22", "type_name": "\u72af\u7f6a\u7247"},
        {"type_id": "3_23", "type_name": "\u79d1\u5e7b\u7247"},
        {"type_id": "3_24", "type_name": "\u5947\u5e7b\u7247"},
        {"type_id": "3_27", "type_name": "\u60ca\u609a\u7247"},
        {"type_id": "3_32", "type_name": "\u60ac\u7591\u7247"},
        {"type_id": "3_123", "type_name": "\u6050\u6016\u7247"},
        {"type_id": "3_113", "type_name": "\u52a8\u753b\u7247"},
        {"type_id": "3_125", "type_name": "\u7f51\u7edc\u7535\u5f71"},
        {"type_id": "3_124", "type_name": "\u540c\u6027\u7247"},
        # ---- 电视剧大类 + 细分子类型 ----
        {"type_id": "4", "type_name": "\u7535\u89c6\u5267"},
        {"type_id": "4_126", "type_name": "\u53e4\u88c5"},
        {"type_id": "4_132", "type_name": "\u90fd\u5e02"},
        {"type_id": "4_130", "type_name": "\u5bb6\u5ead"},
        {"type_id": "4_137", "type_name": "\u8c0d\u6218"},
        {"type_id": "4_128", "type_name": "\u6b66\u4fa0"},
        {"type_id": "4_131", "type_name": "\u9752\u6625"},
        {"type_id": "4_133", "type_name": "\u559c\u5267"},
        {"type_id": "4_138", "type_name": "\u7f6a\u6848"},
        {"type_id": "4_144", "type_name": "\u79d1\u5e7b"},
        {"type_id": "4_146", "type_name": "\u7231\u60c5"},
        {"type_id": "4_150", "type_name": "\u52a8\u4f5c"},
        {"type_id": "4_151", "type_name": "\u60ca\u609a"},
        {"type_id": "4_152", "type_name": "\u5267\u60c5"},
        {"type_id": "4_153", "type_name": "\u540c\u6027"},
        {"type_id": "4_16", "type_name": "\u6b27\u7f8e\u5267"},
        {"type_id": "4_18", "type_name": "\u82f1\u5267"},
        # ---- 其他大类 ----
        {"type_id": "5", "type_name": "\u7efc\u827a"},
        {"type_id": "6", "type_name": "\u52a8\u6f2b"},
        {"type_id": "7", "type_name": "\u7eaa\u5f55\u7247"},
        {"type_id": "8", "type_name": "\u77ed\u5267"},
        {"type_id": "40", "type_name": "4K\u4e13\u533a"},
    ]

    # ==================== 子类型映射 (type_id -> subGenreId) ====================
    # type_id 格式: categoryId_subGenreId, 如 3_23 表示电影科幻
    # 子类型的 type_id 以 3_ 或 4_ 开头且后面是纯数字
    _MOVIE_SUBGENRE_IDS = {"19", "20", "21", "22", "23", "24", "27", "28", "32", "113", "123", "124", "125"}
    _TV_SUBGENRE_IDS = {"126", "128", "130", "131", "132", "133", "137", "138", "144", "146", "150", "151", "152", "153", "16", "18"}

    # ==================== 筛选器 ====================
    _filters = {
        # 电影大类筛选器
        "3": {
            "class": [
                {"key": "type", "name": "\u7c7b\u578b", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "\u5267\u60c5\u7247", "v": "\u5267\u60c5"},
                    {"n": "\u559c\u5267\u7247", "v": "\u559c\u5267"}, {"n": "\u7231\u60c5\u7247", "v": "\u7231\u60c5"},
                    {"n": "\u52a8\u4f5c\u7247", "v": "\u52a8\u4f5c"}, {"n": "\u72af\u7f6a\u7247", "v": "\u72af\u7f6a"},
                    {"n": "\u79d1\u5e7b\u7247", "v": "\u79d1\u5e7b"}, {"n": "\u5947\u5e7b\u7247", "v": "\u5947\u5e7b"},
                    {"n": "\u5192\u9669\u7247", "v": "\u5192\u9669"}, {"n": "\u60ca\u609a\u7247", "v": "\u60ca\u609a"},
                    {"n": "\u6050\u6016\u7247", "v": "\u6050\u6016"}, {"n": "\u6218\u4e89\u7247", "v": "\u6218\u4e89"},
                    {"n": "\u60ac\u7591\u7247", "v": "\u60ac\u7591"}, {"n": "\u6b66\u4fa0\u7247", "v": "\u6b66\u4fa0"},
                    {"n": "\u5386\u53f2\u7247", "v": "\u5386\u53f2"}, {"n": "\u52a8\u753b\u7247", "v": "\u52a8\u753b"},
                    {"n": "\u540c\u6027\u7247", "v": "\u540c\u6027"}, {"n": "\u7f51\u7edc\u7535\u5f71", "v": "\u7f51\u7edc\u7535\u5f71"},
                ]},
                {"key": "area", "name": "\u5730\u533a", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "\u4e2d\u56fd\u5927\u9646", "v": "\u5927\u9646"},
                    {"n": "\u4e2d\u56fd\u9999\u6e2f", "v": "\u9999\u6e2f"}, {"n": "\u4e2d\u56fd\u53f0\u6e7e", "v": "\u53f0\u6e7e"},
                    {"n": "\u65e5\u672c", "v": "\u65e5\u672c"}, {"n": "\u97e9\u56fd", "v": "\u97e9\u56fd"},
                    {"n": "\u7f8e\u56fd", "v": "\u6b27\u7f8e"}, {"n": "\u82f1\u56fd", "v": "\u82f1\u56fd"},
                    {"n": "\u6cf0\u56fd", "v": "\u6cf0\u56fd"}, {"n": "\u5176\u5b83", "v": "\u5176\u5b83"},
                ]},
                {"key": "year", "name": "\u5e74\u4efd", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"},
                    {"n": "90\u5e74\u4ee3", "v": "90\u5e74\u4ee3"}, {"n": "80\u5e74\u4ee3", "v": "80\u5e74\u4ee3"},
                    {"n": "\u66f4\u65e9", "v": "\u66f4\u65e9"},
                ]},
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u6700\u8fd1\u66f4\u65b0", "v": "\u6700\u8fd1\u66f4\u65b0"},
                    {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"}, {"n": "\u8bc4\u5206", "v": "\u8bc4\u5206"},
                ]},
            ],
        },
        # 电视剧大类筛选器
        "4": {
            "class": [
                {"key": "type", "name": "\u7c7b\u578b", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "\u53e4\u88c5", "v": "\u53e4\u88c5"},
                    {"n": "\u90fd\u5e02", "v": "\u90fd\u5e02"}, {"n": "\u5386\u53f2", "v": "\u5386\u53f2"},
                    {"n": "\u8c0d\u6218", "v": "\u8c0d\u6218"}, {"n": "\u5bb6\u5ead", "v": "\u5bb6\u5ead"},
                    {"n": "\u6b66\u4fa0", "v": "\u6b66\u4fa0"}, {"n": "\u9752\u6625", "v": "\u9752\u6625"},
                    {"n": "\u7231\u60c5", "v": "\u7231\u60c5"}, {"n": "\u559c\u5267", "v": "\u559c\u5267"},
                    {"n": "\u60ac\u7591", "v": "\u60ac\u7591"}, {"n": "\u7f6a\u6848", "v": "\u7f6a\u6848"},
                    {"n": "\u79d1\u5e7b", "v": "\u79d1\u5e7b"}, {"n": "\u52a8\u4f5c", "v": "\u52a8\u4f5c"},
                    {"n": "\u60ca\u609a", "v": "\u60ca\u609a"}, {"n": "\u5267\u60c5", "v": "\u5267\u60c5"},
                    {"n": "\u5947\u5e7b", "v": "\u5947\u5e7b"}, {"n": "\u540c\u6027", "v": "\u540c\u6027"},
                    {"n": "\u7a7f\u8d8a", "v": "\u7a7f\u8d8a"}, {"n": "\u5bab\u5ef7", "v": "\u5bab\u5ef7"},
                    {"n": "\u5546\u6218", "v": "\u5546\u6218"}, {"n": "\u8b66\u532a", "v": "\u8b66\u532a"},
                    {"n": "\u77ed\u5267", "v": "\u77ed\u5267"},
                ]},
                {"key": "area", "name": "\u5730\u533a", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "\u4e2d\u56fd\u5927\u9646", "v": "\u5927\u9646"},
                    {"n": "\u4e2d\u56fd\u9999\u6e2f", "v": "\u9999\u6e2f"}, {"n": "\u4e2d\u56fd\u53f0\u6e7e", "v": "\u53f0\u6e7e"},
                    {"n": "\u65e5\u672c", "v": "\u65e5\u672c"}, {"n": "\u97e9\u56fd", "v": "\u97e9\u56fd"},
                    {"n": "\u7f8e\u56fd", "v": "\u6b27\u7f8e"}, {"n": "\u82f1\u56fd", "v": "\u82f1\u56fd"},
                    {"n": "\u6cf0\u56fd", "v": "\u6cf0\u56fd"}, {"n": "\u5176\u5b83", "v": "\u5176\u5b83"},
                ]},
                {"key": "year", "name": "\u5e74\u4efd", "value": [
                    {"n": "\u5168\u90e8", "v": ""}, {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"}, {"n": "2018", "v": "2018"},
                    {"n": "90\u5e74\u4ee3", "v": "90\u5e74\u4ee3"}, {"n": "80\u5e74\u4ee3", "v": "80\u5e74\u4ee3"},
                ]},
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u6700\u8fd1\u66f4\u65b0", "v": "\u6700\u8fd1\u66f4\u65b0"},
                    {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"}, {"n": "\u8bc4\u5206", "v": "\u8bc4\u5206"},
                ]},
            ],
        },
        # 综艺
        "5": {
            "class": [
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"},
                    {"n": "\u8bc4\u5206", "v": "\u8bc4\u5206"},
                ]},
            ],
        },
        # 动漫
        "6": {
            "class": [
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"},
                    {"n": "\u8bc4\u5206", "v": "\u8bc4\u5206"},
                ]},
            ],
        },
        # 纪录片
        "7": {
            "class": [
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u70b9\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"},
                ]},
            ],
        },
        # 短剧
        "8": {
            "class": [
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"},
                ]},
            ],
        },
        # 4K
        "40": {
            "class": [
                {"key": "sort", "name": "\u6392\u5e8f", "value": [
                    {"n": "\u6700\u65b0", "v": "\u6700\u65b0"}, {"n": "\u4eba\u6c14", "v": "\u4eba\u6c14"},
                    {"n": "\u8bc4\u5206", "v": "\u8bc4\u5206"},
                ]},
            ],
        },
    }
    # 给所有子类型一个空筛选器（继承父类）
    _all_subtypes = ["3_" + s for s in _MOVIE_SUBGENRE_IDS] + ["4_" + s for s in _TV_SUBGENRE_IDS]
    for _st in _all_subtypes:
        _filters[_st] = {"class": []}

    # ==================== HTTP 请求 ====================
    def init(self, extend=""):
        pass

    def getName(self):
        return "ifn\u5f71\u89c6"

    def clean(self, text):
        if not text:
            return ""
        text = html_mod.unescape(str(text))
        return re.sub(r"\s+", " ", text).strip()

    def _wechat_text(self):
        return self._WX_TEXT

    def getHtml(self, url, headers=None, timeout=20):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            default_headers = {
                "User-Agent": self.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "identity",
                "Connection": "close",
                "Referer": self.BASE_URL + "/",
            }
            if headers:
                default_headers.update(headers)
            req = urllib.request.Request(url, headers=default_headers)
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            data = resp.read()
            content_encoding = resp.headers.get("Content-Encoding", "")
            if "gzip" in content_encoding:
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            resp.close()
            for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
                try:
                    return data.decode(enc)
                except Exception:
                    continue
            return data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
                for enc in ("utf-8", "gbk", "gb2312"):
                    try:
                        return data.decode(enc)
                    except Exception:
                        continue
                return data.decode("utf-8", errors="replace")
            except Exception:
                return ""
        except Exception:
            return ""

    # ==================== Next.js 数据解析 ====================
    def _find_matching_bracket(self, s, start_idx, open_char, close_char):
        depth = 1
        in_string = False
        escape = False
        for i in range(start_idx + 1, len(s)):
            c = s[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _extract_escaped_json_value(self, html, key):
        """从 Next.js __next_f 数据中提取指定 key 对应的 JSON 值
        
        委托给 _extract_field 统一处理转义模式
        """
        return self._extract_field(html, key)

    def _extract_field(self, text, key):
        """从 Next.js RSC 转义 JSON 中提取字段值
        
        HTML 中实际格式为: key\\":\\":value\\"
        在 Python 字符串中即: key\\":\\"value\\"
        其中 \\ 是字面反斜杠, " 是字面引号
        对于数字值: key\\":value,
        """
        # 主模式: key\\":\\"
        search = key + '\\":\\"'
        idx = text.find(search)
        if idx >= 0:
            val_start = idx + len(search)
            end_idx = text.find('\\"', val_start)
            if end_idx > val_start:
                return text[val_start:end_idx]
            # 回退: 找逗号
            comma = text.find(',', val_start)
            if comma > val_start:
                return text[val_start:comma]
        
        # 备用模式: key":"
        search2 = key + '":"'
        idx2 = text.find(search2)
        if idx2 >= 0:
            val_start = idx2 + len(search2)
            end_idx = text.find('"', val_start)
            if end_idx > val_start:
                return text[val_start:end_idx]
        
        # 数字值模式: key\\":number,
        search3 = key + '\\":'
        idx3 = text.find(search3)
        if idx3 >= 0:
            val_start = idx3 + len(search3)
            # 查找数字
            end_idx = val_start
            while end_idx < len(text) and text[end_idx] in '0123456789.-':
                end_idx += 1
            if end_idx > val_start:
                return text[val_start:end_idx]
        
        return ""

    def _parse_video_list(self, html):
        """从分类/搜索/首页页面解析视频列表
        
        Next.js RSC 数据中，视频对象散布在 __next_f.push() 块中，
        格式为转义的 JSON: mediaId\\\":\\\"value\\\", title\\\":\\\"value\\\"
        直接用正则匹配每个含 mediaId 的对象片段。
        """
        videos = []
        seen = set()
        try:
            # 用正则匹配每个包含 mediaId 的对象片段
            # 匹配模式: 在 mediaId 前后提取一段文本，包含 title/score/coverImgUrl/date 等字段
            # 对象通常以 { 开始，包含 mediaId/title/score/coverImgUrl 等字段
            # 在 RSC 数据中，转义后的格式: \\"mediaId\\":\\"value\\"
            
            # 找到所有 mediaId 出现的位置
            media_id_pattern = r'mediaId\\+":\\"([^"\\]+)\\"'
            matches = list(re.finditer(media_id_pattern, html))
            
            for m in matches:
                media_id = m.group(1)
                if media_id in seen:
                    continue
                seen.add(media_id)
                
                # 从 mediaId 位置向前找对象起始 {
                # 向后提取一段文本（约500字符）来找 title/score/coverImgUrl
                start = m.start()
                # 向前找 { 
                obj_start = start
                for i in range(start, max(0, start - 300), -1):
                    if html[i] == '{':
                        obj_start = i
                        break
                # 向后提取对象内容（找下一个 mediaId 或到对象结束）
                obj_end = min(len(html), start + 600)
                # 尝试找到对象的结束 }
                depth = 0
                for i in range(obj_start, min(len(html), obj_start + 800)):
                    c = html[i]
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            obj_end = i + 1
                            break
                
                item = html[obj_start:obj_end]
                
                # 提取字段
                title = self._extract_field(item, 'title')
                score = self._extract_field(item, 'score')
                pic = self._extract_field(item, 'coverImgUrl')
                
                # 封面图URL处理
                if pic:
                    if not pic.startswith("http"):
                        pic = self.BASE_URL + pic
                
                # 备注: 尝试从 date/postTime 提取年份
                remark = ""
                date_val = self._extract_field(item, 'date')
                if date_val and len(date_val) >= 4:
                    remark = date_val[:4]
                if not remark:
                    post_val = self._extract_field(item, 'postTime')
                    if post_val and len(post_val) >= 4:
                        remark = post_val[:4]
                
                videos.append({
                    "vod_id": media_id,
                    "vod_name": self.clean(title),
                    "vod_pic": pic,
                    "vod_score": score,
                    "vod_remarks": remark,
                })
        except Exception:
            pass
        return videos

    # ==================== 首页 ====================
    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in self.CATEGORIES]
        filters = {}
        # 为每个大类提供筛选（子类型也使用大类筛选器结构）
        for c in self.CATEGORIES:
            tid = str(c["type_id"])
            if tid in self._filters:
                filters[tid] = self._filters[tid]["class"]
            elif "_" in tid and tid.split("_")[0] in self._filters:
                filters[tid] = self._filters[tid.split("_")[0]]["class"]
        result = {"class": classes, "filters": filters}
        return result

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.BASE_URL)
        if not html:
            return result
        videos = self._parse_video_list(html)
        result["list"] = videos[:30]
        return result

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1

        tid_str = str(tid)

        # 处理子类型: 3_xxx -> 电影(3), 4_xxx -> 剧集(4)
        # type_id 格式: categoryId_subGenreId, 如 3_23 表示电影科幻
        cat_id = tid_str
        sub_genre_id = ""
        is_movie_sub = False
        is_tv_sub = False
        if tid_str.startswith("3_") and tid_str[2:].isdigit():
            sub_genre_id = tid_str[2:]
            is_movie_sub = sub_genre_id in self._MOVIE_SUBGENRE_IDS
            cat_id = "3"
        elif tid_str.startswith("4_") and tid_str[2:].isdigit():
            sub_genre_id = tid_str[2:]
            is_tv_sub = sub_genre_id in self._TV_SUBGENRE_IDS
            cat_id = "4"

        # 如果是子类型，需要客户端过滤: 获取大类数据后按 mediaId 中的 subGenreId 过滤
        if is_movie_sub or is_tv_sub:
            # 子类型需要翻页获取更多数据来填充
            # 每页30条，但过滤后可能不足30条，所以多取几页
            all_videos = []
            max_fetch_pages = 5  # 每次最多获取5页来过滤
            start_page = (pg - 1) * max_fetch_pages + 1
            for p in range(start_page, start_page + max_fetch_pages):
                url = self.BASE_URL + "/category/" + cat_id + "?page=" + str(p)
                html = self.getHtml(url)
                if not html:
                    break
                page_videos = self._parse_video_list(html)
                if not page_videos:
                    break
                all_videos.extend(page_videos)

            # 按 subGenreId 过滤
            filtered = []
            for v in all_videos:
                mid = v.get("vod_id", "")
                parts = mid.split(",")
                if len(parts) >= 4 and parts[3] == sub_genre_id:
                    filtered.append(v)

            if filtered:
                result["list"] = filtered
                result["pagecount"] = "50"  # 估算
                result["total"] = "1500"
            else:
                result["pagecount"] = str(max(pg - 1, 1))
            return result

        # 非子类型: 正常获取大类
        url = self.BASE_URL + "/category/" + cat_id
        params = []
        if pg > 1:
            params.append("page=" + str(pg))
        if params:
            url += "?" + "&".join(params)

        html = self.getHtml(url)
        if not html:
            return result

        videos = self._parse_video_list(html)
        if videos:
            result["list"] = videos
            pagecount = 100 if len(videos) >= 30 else pg
            result["pagecount"] = str(pagecount)
            result["total"] = str(pagecount * 30)
        else:
            result["pagecount"] = str(max(pg - 1, 1))
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) and ids else ids
        vid = str(vid)

        # mediaId 格式: 34896_0,1,3,23 -> base64 去尾部= 作为详情页URL
        try:
            encoded = base64.b64encode(vid.encode("utf-8")).decode("utf-8").rstrip("=")
        except Exception:
            encoded = vid

        url = self.BASE_URL + "/detail/" + encoded
        html = self.getHtml(url)
        if not html or len(html) < 500:
            return result

        vod = {"vod_id": vid}

        # 标题
        title = self._extract_escaped_json_value(html, "title")
        if not title:
            # 回退: 从 <title> 标签提取
            tm = re.search(r"<title>\s*([^<]+?)(?:\s*[-|]\s*IFN.*)?\s*</title>", html, re.I)
            if tm:
                title = self.clean(tm.group(1))
        vod["vod_name"] = self.clean(title) if title else vid

        # 封面
        pic = self._extract_escaped_json_value(html, "coverImgUrl")
        if pic and not pic.startswith("http"):
            pic = self.BASE_URL + pic
        vod["vod_pic"] = pic

        # 类型
        type_name = self._extract_escaped_json_value(html, "typeName")
        content_type = self._extract_escaped_json_value(html, "contentType")
        vod["vod_class"] = content_type or type_name or ""

        # 地区
        regional = self._extract_escaped_json_value(html, "regional")
        vod["vod_area"] = regional or ""

        # 年份
        date_val = self._extract_escaped_json_value(html, "date")
        if date_val and len(date_val) >= 4:
            vod["vod_year"] = date_val[:4]
        else:
            post_val = self._extract_escaped_json_value(html, "postTime")
            if post_val and len(post_val) >= 4:
                vod["vod_year"] = post_val[:4]

        # 演员
        actor = self._extract_escaped_json_value(html, "actor")
        vod["vod_actor"] = self.clean(actor) if actor else ""

        # 导演
        director = self._extract_escaped_json_value(html, "director")
        vod["vod_director"] = self.clean(director) if director else ""

        # 语言
        lang = self._extract_escaped_json_value(html, "lang")
        vod["vod_lang"] = lang or ""

        # 评分
        score = self._extract_escaped_json_value(html, "score")
        vod["vod_score"] = score or ""

        # 更新状态
        update_status = self._extract_escaped_json_value(html, "updateStatus")
        vod["vod_remarks"] = update_status or ""

        # 简介 - 添加微信公众号推广信息
        desc = self._extract_escaped_json_value(html, "description")
        wechat = self._wechat_text()
        if desc:
            vod["vod_content"] = self.clean(desc) + "\n\n" + wechat
        else:
            # 回退: meta description
            dm = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
            if dm:
                vod["vod_content"] = self.clean(dm.group(1)) + "\n\n" + wechat
            else:
                vod["vod_content"] = wechat

        # 播放列表 - 解析 episodes
        play_lines = []
        media_id = self._extract_escaped_json_value(html, "mediaId")
        if not media_id:
            media_id = vid

        episodes = self._extract_episodes(html)
        if episodes:
            for ep_id, ep_title in episodes:
                # 播放ID格式: mediaId@epId，用于playerContent解析
                play_id = media_id + "@" + str(ep_id)
                play_lines.append("%s$%s" % (ep_title, play_id))
        else:
            # 回退: 单集
            episode_id = self._extract_escaped_json_value(html, "episodeId")
            if episode_id:
                play_id = media_id + "@" + str(episode_id)
                play_lines.append("\u64ad\u6536$" + play_id)
            else:
                play_lines.append("\u64ad\u6536$" + media_id + "@1")

        vod["vod_play_from"] = "ifn\u5f71\u89c6"
        vod["vod_play_url"] = "#".join(play_lines)

        vod["type_id"] = ""
        vod["type_name"] = ""

        result["list"] = [vod]
        return result

    def _extract_episodes(self, html):
        """从详情页解析 episodes 数组"""
        episodes = []
        try:
            # 找 episodes 数组
            idx = html.find("episodes")
            if idx < 0:
                return episodes

            # 找到数组起始 [
            bracket_idx = html.find("[", idx)
            if bracket_idx < 0:
                return episodes

            end_idx = self._find_matching_bracket(html, bracket_idx, "[", "]")
            if end_idx < 0:
                return episodes

            items_str = html[bracket_idx + 1:end_idx]

            # 解析每个 episode 对象 {\"id\":xxx,\"title\":\"xxx\"}
            pos = 0
            while pos < len(items_str):
                brace_idx = items_str.find("{", pos)
                if brace_idx == -1:
                    break
                end_brace = self._find_matching_bracket(items_str, brace_idx, "{", "}")
                if end_brace == -1:
                    break
                item = items_str[brace_idx:end_brace + 1]
                pos = end_brace + 1

                ep_id = self._extract_escaped_json_value(item, "id")
                ep_title = self._extract_escaped_json_value(item, "title")
                if ep_id:
                    if not ep_title:
                        ep_title = "\u7b2c%s\u96c6" % str(len(episodes) + 1)
                    episodes.append((ep_id, self.clean(ep_title)))
        except Exception:
            pass
        return episodes

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        return self._do_search(key, quick, pg)

    def searchContentPage(self, key, quick, page):
        return self._do_search(key, quick, str(page))

    def _do_search(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1", "total": "0"}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if not key:
            return result

        search_url = self.BASE_URL + "/search?q=" + urllib.parse.quote(key)
        if pg > 1:
            search_url += "&page=" + str(pg)

        html = self.getHtml(search_url)
        if not html:
            return result

        videos = self._parse_video_list(html)
        if videos:
            result["list"] = videos
            result["pagecount"] = str(pg + 1) if len(videos) >= 10 else str(pg)
            result["total"] = str(len(videos))
        return result

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        play_headers = {
            "User-Agent": self.UA,
            "Referer": self.BASE_URL + "/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": self.BASE_URL,
        }

        # id 格式: mediaId@epId
        media_id = ""
        ep_id = ""
        if "@" in id:
            parts = id.split("@", 1)
            media_id = parts[0]
            ep_id = parts[1] if len(parts) > 1 else ""
        else:
            media_id = id

        if not ep_id:
            ep_id = "1"

        # 构造详情页URL (含 ep 参数) 供 TVBox 嗅探
        try:
            encoded = base64.b64encode(media_id.encode("utf-8")).decode("utf-8").rstrip("=")
        except Exception:
            encoded = media_id

        detail_url = self.BASE_URL + "/detail/" + encoded
        if ep_id:
            detail_url += "?ep=" + str(ep_id)

        # 方式1: 尝试直接请求播放 token API (可能需要登录，大概率返回401)
        token_url = self.BASE_URL + "/api/play/token?mediaId=" + urllib.parse.quote(media_id) + "&episodeId=" + str(ep_id)
        try:
            token_resp = self.getHtml(token_url, {
                "Accept": "application/json",
                "Referer": detail_url,
            })
            if token_resp:
                try:
                    token_data = json.loads(token_resp)
                    if token_data.get("success") and token_data.get("token"):
                        token = token_data["token"]
                        # 构造 m3u8 URL: /api/play/{token}.m3u8?ts=true&reslo=720
                        m3u8_url = self.BASE_URL + "/api/play/" + token + ".m3u8?ts=true&reslo=720"
                        return {
                            "url": m3u8_url,
                            "parse": "0",
                            "header": json.dumps(play_headers),
                            "playUrl": "",
                            "subtitle": "",
                        }
                except Exception:
                    pass
        except Exception:
            pass

        # 方式2: 尝试 POST 获取 token
        try:
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            post_data = json.dumps({
                "mediaId": media_id,
                "episodeId": str(ep_id),
                "title": "",
            }).encode("utf-8")
            post_headers = {
                "User-Agent": self.UA,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": self.BASE_URL,
                "Referer": detail_url,
            }
            req = urllib.request.Request(
                self.BASE_URL + "/api/play/token",
                data=post_data,
                headers=post_headers,
            )
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                resp_data = resp.read().decode("utf-8", errors="replace")
                if resp_data:
                    j = json.loads(resp_data)
                    if j.get("success") and j.get("token"):
                        token = j["token"]
                        m3u8_url = self.BASE_URL + "/api/play/" + token + ".m3u8?ts=true&reslo=720"
                        return {
                            "url": m3u8_url,
                            "parse": "0",
                            "header": json.dumps(play_headers),
                            "playUrl": "",
                            "subtitle": "",
                        }
        except Exception:
            pass

        # 方式3: 直接尝试 m3u8 URL (token = mediaId, 可能对免费内容有效)
        for token_candidate in [media_id, media_id.split("_")[0] if "_" in media_id else media_id]:
            m3u8_url = self.BASE_URL + "/api/play/" + token_candidate + ".m3u8?ts=true&reslo=720"
            try:
                import ssl as _ssl2
                ctx2 = _ssl2.create_default_context()
                ctx2.check_hostname = False
                ctx2.verify_mode = _ssl2.CERT_NONE
                check_req = urllib.request.Request(m3u8_url, headers={
                    "User-Agent": self.UA,
                    "Referer": detail_url,
                    "Accept": "*/*",
                })
                with urllib.request.urlopen(check_req, timeout=10, context=ctx2) as resp2:
                    content = resp2.read(200).decode("utf-8", errors="replace")
                    if content.startswith("#EXTM3U"):
                        return {
                            "url": m3u8_url,
                            "parse": "0",
                            "header": json.dumps(play_headers),
                            "playUrl": "",
                            "subtitle": "",
                        }
            except Exception:
                pass

        # 方式4: 回退到 parse=1 嗅探 - 让 TVBox 打开详情页自动嗅探 m3u8
        play_headers["Referer"] = detail_url
        return {
            "url": detail_url,
            "parse": "1",
            "header": json.dumps(play_headers),
            "playUrl": "",
            "subtitle": "",
        }

    # ==================== 其他 ====================
    def __jsEvalReturn(self):
        return {"proxy": None}

    def isVideoContent(self, ids):
        return False

    def manualVideoCheck(self):
        return False

    def manualSniffer(self, ids):
        return False

    def snifferContent(self, ids):
        return None
