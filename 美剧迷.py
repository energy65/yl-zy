# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 美剧迷 (meijumi.tv)
支持: 分类栏 / 首页推荐 / 分页列表 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)
播放流程: 抓取 /player/ 页的 player_aaaa.url -> 请求聚合云播接口 php.playerla.com/cplay/ -> 提取 m3u8
"""

import re
import json
import ssl
import gzip
import time
import urllib.request
import urllib.parse

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

BASE_URL = "https://www.meijumi.tv"
CPLAY_HOST = "https://php.playerla.com"
AD_INFO = ("\n\n---\n微信公众号：源力软件汇\n"
           "QQ群：1054592152\n伴随更多优质资源尽在源力")

# (type_id, type_name, /show/ or /type/ path)
CATEGORIES = [
    {"type_id": "1", "type_name": "电视剧", "url": "/type/1/"},
    {"type_id": "2", "type_name": "电影", "url": "/type/2/"},
    {"type_id": "3", "type_name": "动漫", "url": "/type/3/"},
    {"type_id": "7", "type_name": "美剧", "url": "/show/7/"},
    {"type_id": "6", "type_name": "陆剧", "url": "/show/6/"},
    {"type_id": "9", "type_name": "日剧", "url": "/show/9/"},
    {"type_id": "8", "type_name": "韩剧", "url": "/show/8/"},
    {"type_id": "10", "type_name": "泰剧", "url": "/show/10/"},
    {"type_id": "11", "type_name": "台剧", "url": "/show/11/"},
    {"type_id": "25", "type_name": "其他剧", "url": "/show/25/"},
]


class Spider(BaseSpider):

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/126.0.0.0 Safari/537.36")

    _headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": BASE_URL + "/",
    }

    _ssl_ctx = None

    def init(self, extend=""):
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass

    def getName(self):
        return "美剧迷"

    def _get_ssl_ctx(self):
        if self._ssl_ctx is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.set_ciphers("DEFAULT@SECLEVEL=1")
            except Exception:
                pass
            Spider._ssl_ctx = ctx
        return self._ssl_ctx

    def _get(self, url, timeout=20, retries=3, headers=None):
        last_err = None
        hdrs = self._headers
        if headers:
            hdrs = dict(self._headers)
            hdrs.update(headers)
        for _ in range(retries):
            try:
                if not url.startswith("http"):
                    url = BASE_URL + "/" + url.lstrip("/")
                req = urllib.request.Request(url, headers=hdrs)
                with urllib.request.urlopen(req, timeout=timeout,
                                           context=self._get_ssl_ctx()) as resp:
                    data = resp.read()
                    enc = resp.headers.get("Content-Encoding", "")
                    if "gzip" in enc:
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            pass
                    return self._decode(data)
            except Exception as e:
                last_err = e
                time.sleep(1)
        return ""

    def _decode(self, data):
        for enc in ("utf-8", "gb18030", "gbk", "gb2312", "latin-1"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    def _clean(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        text = (text.replace("&amp;", "&").replace("&lt;", "<")
                    .replace("&gt;", ">").replace("&quot;", '"')
                    .replace("&#039;", "'").replace("&nbsp;", " "))
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0\u200e\u200f]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    # ==================== 列表解析 ====================

    def _parse_items(self, html):
        """解析形如 /detail/xxx/ 的卡片块，适用于首页/分类/搜索。"""
        items = []
        seen = set()
        if not html:
            return items

        blocks = re.split(r'<div class="col-\d+', html)
        for block in blocks:
            if 'class="pic' not in block and 'pic-itme' not in block:
                continue
            m = re.search(r'href="/detail/(\d+)/"[^>]*title="([^"]*)"', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            name = self._clean(m.group(2))

            pic = ""
            pm = re.search(r'data-original="([^"]+)"', block)
            if pm:
                cand = pm.group(1)
                if "logo" not in cand and "/statics/" not in cand:
                    pic = cand
            if not pic:
                pm2 = re.search(r'<img[^>]*src="([^"]+)"', block)
                if pm2:
                    cand = pm2.group(1)
                    if "logo" not in cand and "/statics/" not in cand:
                        pic = cand

            remark = ""
            rm = re.search(r'class="pic-text[^"]*"[^>]*>\s*(?:更新至第)?(\d+)集',
                           block)
            if rm:
                remark = "更新至第" + rm.group(1) + "集"
            else:
                rm2 = re.search(r'class="pic-text[^"]*"[^>]*>\s*([^<]{1,12})',
                                block)
                if rm2:
                    remark = self._clean(rm2.group(1))

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_page_max(self, html, id_path):
        max_pg = 1
        for m in re.finditer(re.escape(id_path) + r'page/(\d+)/', html):
            try:
                max_pg = max(max_pg, int(m.group(1)))
            except ValueError:
                pass
        return max_pg

    # ==================== 首页 ====================

    def homeContent(self, filter):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]}
                   for c in CATEGORIES]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        result = {"list": []}
        try:
            html = self._get(BASE_URL + "/")
            items = self._parse_items(html)
            for it in items:
                it["vod_content"] = AD_INFO
            result["list"] = items[:30]
        except Exception:
            pass
        return result

    # ==================== 分类 ====================

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1",
                  "limit": 24, "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except (TypeError, ValueError):
            page = 1

        cat = next((c for c in CATEGORIES if c["type_id"] == tid), None)
        if cat is None:
            return result

        id_path = cat["url"] + ("page/" if not cat["url"].endswith("/") else "page/")
        url = cat["url"]
        if page > 1:
            url = cat["url"].rstrip("/") + "/page/%d/" % page

        html = self._get(BASE_URL + url)
        if not html:
            return result

        items = self._parse_items(html)
        pc = self._parse_page_max(html, cat["url"])
        pc = max(pc, page)

        for it in items:
            it["vod_content"] = AD_INFO

        result["list"] = items
        result["page"] = str(page)
        result["pagecount"] = str(pc) if pc else "1"
        result["total"] = str(len(items))
        return result

    # ==================== 详情 ====================

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = str(ids[0]) if isinstance(ids, list) and ids else str(ids)
            vid = re.sub(r"\D", "", vid)
            if not vid:
                return result

            html = self._get("/detail/%s/" % vid)
            if not html or "详情" not in html and "<h1" not in html:
                if not html:
                    return result

            vod = {"vod_id": vid}

            nm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if nm:
                vod["vod_name"] = self._clean(nm.group(1))
            else:
                tm = re.search(r"<title>([^<]+)</title>", html)
                vod["vod_name"] = self._clean(
                    tm.group(1).split("_")[0]) if tm else vid

            pm = re.search(r'<img[^>]*data-original="([^"]+)"', html) or \
                 re.search(r'<img[^>]*src="([^"]+\.(?:jpg|jpeg|png|webp|gif))"',
                           html)
            if pm:
                vod["vod_pic"] = pm.group(1)

            # 地区 / 年份 / 类型
            area_m = re.search(r'<span class="text-body-tertiary">地区[：:]</span>\s*<a[^>]*>([^<]+)</a>', html)
            if area_m:
                vod["vod_area"] = self._clean(area_m.group(1))
            elif not area_m:
                ym = re.search(r'(\d{4})/([^/]+?)/([^<]+?)\s*<', html)
                if ym:
                    vod["vod_area"] = self._clean(ym.group(2))

            year_m = re.search(r'<span class="text-body-tertiary">年份[：:]</span>\s*<a[^>]*>(\d{4})</a>', html)
            if year_m:
                vod["vod_year"] = year_m.group(1)

            cls_m = re.search(r'<span class="text-body-tertiary">类型[：:]</span>\s*<a[^>]*>([^<]+)</a>', html)
            if cls_m:
                vod["vod_class"] = self._clean(cls_m.group(1))

            vod["vod_director"] = self._extract_info(html, "\u5bfc\u6f14")
            vod["vod_actor"] = self._extract_info(html, "\u4e3b\u6f14")

            desc = ""
            dm = re.search(
                r'<h3 class="card-title fs-5">[^<]*?\u5267\u60c5\u7b80\u4ecb</h3>'
                r'.*?<span class="text-body-tertiary"[^>]*>\s*(<p>.*?)</span>',
                html, re.S)
            if dm:
                desc = self._clean(dm.group(1))
            if not desc:
                meta = re.search(
                    r'<meta\s+name="description"\s+content="([^"]+)"', html)
                if meta:
                    desc = self._clean(meta.group(1))
            vod["vod_content"] = (desc + AD_INFO) if desc else AD_INFO

            episodes = self._parse_episodes(html, vid)

            if episodes:
                vod["vod_play_from"] = "\u805a\u5408\u4e91\u64ad"
                vod["vod_play_url"] = "#".join(episodes[:999])
            else:
                vod["vod_play_from"] = "\u805a\u5408\u4e91\u64ad"
                vod["vod_play_url"] = "\u64ad\u653e$%s/player/%s-1-1/" % (
                    BASE_URL, vid)

            result["list"] = [vod]
        except Exception:
            pass
        return result

    def _extract_info(self, html, label):
        m = re.search(
            r'<span class="text-body-tertiary">' + label + r'[：:]</span>'
            r'(.*?)</p>', html, re.S)
        if m:
            seg = m.group(1)
            names = []
            for a in re.finditer(r'<a[^>]*>([^<]+)</a>', seg):
                val = self._clean(a.group(1))
                if val:
                    names.append(val)
            if names:
                return "/".join(names)
        return ""

    def _parse_episodes(self, html, vid):
        episodes = []
        seen = set()
        order = {}
        for em in re.finditer(r'href="(/player/%s-1-(\d+)/)"' % vid, html):
            href = em.group(1)
            n = em.group(2)
            if href in seen:
                continue
            seen.add(href)
            order[href] = n
        for href in sorted(order, key=lambda h: (len(order[h]), order[h])):
            label = "\u7b2c%s\u96c6" % order[href]
            episodes.append("%s$%s%s" % (label, BASE_URL, href))
        return episodes

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1",
                  "total": "0"}
        try:
            wd = urllib.parse.quote(str(key))
            url = "%s/vodsearch/--/?wd=%s" % (BASE_URL, wd)
            html = self._get(url)
            items = self._parse_items(html)
            if not items:
                return result
            for it in items:
                it["vod_content"] = AD_INFO
            result["list"] = items
            result["pagecount"] = "1"
            result["total"] = str(len(items))
        except Exception:
            pass
        return result

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        play_page = id
        if not play_page.startswith("http"):
            play_page = BASE_URL + "/" + play_page.lstrip("/")

        try:
            html = self._get(play_page, timeout=15, retries=2)
            if not html:
                return self._fallback(play_page)
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*(?:</script>|<)',
                          html, re.S)
            if not m:
                return self._fallback(play_page)

            pd = json.loads(m.group(1))
            enc_id = pd.get("url", "")
            if not enc_id:
                return self._fallback(play_page)

            vid = pd.get("id", "")
            return self._resolve_m3u8(enc_id, vid)
        except Exception:
            pass
        return self._fallback(play_page)

    def _resolve_m3u8(self, enc_id, vid):
        cplay = "%s/cplay/?id=%s" % (
            CPLAY_HOST, urllib.parse.quote(enc_id, safe=""))
        html = self._get(cplay, timeout=20, retries=2,
                         headers={"Referer": BASE_URL + "/"})
        if html:
            urls = re.findall(r'data-url=["\']([^"\']+)["\']', html)
            if not urls:
                urls = re.findall(
                    r"['\"]url['\"]\s*:\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]",
                    html)
            if urls:
                target = urls[0].replace("\\/", "/").strip()
                if target.startswith("//"):
                    target = "https:" + target
                headers = {
                    "User-Agent": self.UA,
                    "Referer": BASE_URL + "/",
                }
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": target,
                    "header": json.dumps(headers, ensure_ascii=False),
                }
        return {"parse": 0, "playUrl": "", "url": "", "header": ""}

    def _fallback(self, play_page):
        return {"parse": 0, "playUrl": "", "url": play_page, "header": ""}


# ==================== CLI 测试 ====================

def _cli():
    import sys
    sp = Spider()
    sp.init()
    if len(sys.argv) < 2:
        print("用法: python 美剧迷.py home|list <分类id> <页>|detail <ID>|play <URL>|search <关键词>")
        return
    cmd = sys.argv[1].lower()
    if cmd == "home":
        print(json.dumps(sp.homeVideoContent(), ensure_ascii=False, indent=2))
    elif cmd == "list":
        tid = sys.argv[2] if len(sys.argv) > 2 else "7"
        pg = sys.argv[3] if len(sys.argv) > 3 else "1"
        print(json.dumps(sp.categoryContent(tid, pg, None, None),
                         ensure_ascii=False, indent=2))
    elif cmd == "detail":
        vid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(sp.detailContent([vid]), ensure_ascii=False, indent=2))
    elif cmd == "play":
        u = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(sp.playerContent("", u, []),
                         ensure_ascii=False, indent=2))
    elif cmd == "search":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        pg = sys.argv[3] if len(sys.argv) > 3 else "1"
        print(json.dumps({"list": sp.searchContent(key, 0, pg)},
                         ensure_ascii=False, indent=2))
    else:
        print("未知命令")


if __name__ == "__main__":
    _cli()
