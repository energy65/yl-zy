# -*- coding: utf-8 -*-
"""
TVBox Python 爬虫 - 美剧天堂 (meijutt.cc)
支持: 分类栏 / 首页推荐 / 分页列表 / 详情(含简介) / 选集 / 搜索 / 直接播放(m3u8)
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

BASE_URL = "https://www.meijutt.cc"
AD_INFO = "\n\n---\n微信公众号：源力软件汇\nQQ群：1054592152\n伴随更多优质资源尽在源力"

CATEGORIES = [
    {"type_id": "mhkh", "type_name": "魔幻科幻", "url": "/mjtt/1.html"},
    {"type_id": "lyjt", "type_name": "灵异惊悚", "url": "/mjtt/2.html"},
    {"type_id": "dsqg", "type_name": "都市情感", "url": "/mjtt/3.html"},
    {"type_id": "fzls", "type_name": "犯罪历史", "url": "/mjtt/4.html"},
    {"type_id": "xuzy", "type_name": "选秀综艺", "url": "/mjtt/5.html"},
    {"type_id": "dmtk", "type_name": "动漫卡通", "url": "/mjtt/6.html"},
    {"type_id": "zjgx", "type_name": "最近更新", "url": "/new100.html"},
    {"type_id": "2026xj", "type_name": "2026新剧", "url": "/topiclist/1.html"},
    {"type_id": "phb", "type_name": "排行榜", "url": "/alltop_hit.html"},
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
        return "美剧天堂"

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

    def _get(self, url, timeout=20, retries=3):
        last_err = None
        for _ in range(retries):
            try:
                if not url.startswith("http"):
                    url = BASE_URL + "/" + url.lstrip("/")
                req = urllib.request.Request(url, headers=self._headers)
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

    def _post(self, url, body, timeout=20):
        try:
            if not url.startswith("http"):
                url = BASE_URL + "/" + url.lstrip("/")
            data = urllib.parse.urlencode(body).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=self._headers)
            with urllib.request.urlopen(req, timeout=timeout,
                                       context=self._get_ssl_ctx()) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if "gzip" in enc:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return self._decode(raw)
        except Exception:
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
        return re.sub(r"\s+", " ", text).strip()

    # ==================== 列表解析 ====================

    def _parse_home_items(self, html):
        items = []
        seen = set()
        if not html:
            return items

        for m in re.finditer(
                r'<a[^>]*href="(/meijutt/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>',
                html):
            href, vid, title = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            name = self._clean(title)
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "",
            })

        for m in re.finditer(
                r'<a[^>]*href="(/meijutt/(\d+)\.html)"[^>]*>\s*'
                r'<img[^>]*(?:data-original|src)="([^"]+)"[^>]*>',
                html):
            vid = m.group(2)
            pic = m.group(3)
            for it in items:
                if it["vod_id"] == vid and not it["vod_pic"]:
                    it["vod_pic"] = pic
                    break

        for m in re.finditer(
                r'<a[^>]*href="(/meijutt/(\d+)\.html)"[^>]*>.*?</a>'
                r'.*?(?:至第(\d+)集|本季终|全剧完结|第(\d+)集)',
                html, re.S):
            vid = m.group(2)
            ep = m.group(3) or m.group(4)
            remark = ""
            if m.group(3):
                remark = "更新至第" + m.group(3) + "集"
            elif "全剧完结" in m.group(0):
                remark = "全剧完结"
            elif "本季终" in m.group(0):
                remark = "本季终"
            for it in items:
                if it["vod_id"] == vid and not it["vod_remarks"]:
                    it["vod_remarks"] = remark
                    break

        return items

    def _parse_category_items(self, html):
        items = []
        seen = set()
        if not html:
            return items

        for m in re.finditer(
                r'<div[^>]*class="cn_box_box3"[^>]*>.*?</div>\s*'
                r'<ul[^>]*class="list_20"[^>]*>(.*?)</ul>',
                html, re.S):
            block = m.group(0)
            hm = re.search(r'href="(/meijutt/(\d+)\.html)"', block)
            if not hm:
                continue
            vid = hm.group(2)
            if vid in seen:
                continue
            seen.add(vid)

            nm = re.search(r'title="([^"]*)"[^>]*>[^<]*</a>', block)
            name = self._clean(nm.group(1)) if nm else ""

            pic = ""
            pm = re.search(r'data-original="([^"]+)"', block)
            if pm:
                pic = pm.group(1)

            remark = ""
            rm = re.search(r'(?:至第(\d+)集|本季终|全剧完结)', block)
            if rm:
                if rm.group(1):
                    remark = "更新至第" + rm.group(1) + "集"
                else:
                    remark = rm.group(0)

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    def _parse_page_count(self, html):
        max_pg = 1
        for m in re.finditer(r'/mjtt/\d+-(\d+)\.html', html):
            try:
                max_pg = max(max_pg, int(m.group(1)))
            except ValueError:
                pass
        for m in re.finditer(r'page=(\d+)', html):
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
            items = self._parse_home_items(html)
            for it in items:
                it["vod_content"] = AD_INFO
            result["list"] = items[:30]
        except Exception:
            pass
        return result

    # ==================== 分类 ====================

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": str(pg), "pagecount": "1",
                  "limit": 20, "total": "0"}
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except (TypeError, ValueError):
            page = 1

        cat = next((c for c in CATEGORIES if c["type_id"] == tid), None)
        if cat is None:
            return result

        url = cat["url"]
        if page > 1 and "/mjtt/" in url:
            base = url.replace(".html", "")
            url = base + "-%d.html" % page
        elif page > 1:
            sep = "&" if "?" in url else "?"
            url = url + sep + "page=%d" % page

        html = self._get(url)
        if not html:
            return result

        items = self._parse_category_items(html)
        if not items:
            items = self._parse_home_items(html)

        pc = self._parse_page_count(html)
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

            html = self._get("/meijutt/%s.html" % vid)
            if not html:
                return result

            vod = {"vod_id": vid}

            nm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if nm:
                vod["vod_name"] = self._clean(nm.group(1)).strip("(年)")
            else:
                tm = re.search(r"<title>([^<]+)</title>", html)
                vod["vod_name"] = self._clean(
                    tm.group(1).split("在线")[0]) if tm else vid

            pm = re.search(
                r'data-src="([^"]+\.(?:jpg|jpeg|png|webp|gif))"', html)
            if pm:
                vod["vod_pic"] = pm.group(1)

            vod["vod_director"] = self._extract_info(html, "导演")
            vod["vod_actor"] = self._extract_info(html, "主演")

            area_m = re.search(
                r'<label><em>地区[：:]</em>([^<]+)</label>', html)
            if area_m:
                vod["vod_area"] = self._clean(area_m.group(1))

            year_m = re.search(r'<em>首播日期[：:]</em>(\d{4})', html)
            if year_m:
                vod["vod_year"] = year_m.group(1)

            cls_m = re.search(
                r'<li><em>类型[：:]</em>\s*([^<]+)</li>', html)
            if cls_m:
                vod["vod_class"] = self._clean(cls_m.group(1))

            desc = ""
            dm = re.search(r'剧情介绍[：:]?\s*</em>\s*(.*?)</div>',
                           html, re.S)
            if dm:
                desc = self._clean(dm.group(1))
            if not desc:
                meta = re.search(
                    r'<meta\s+name="description"\s+content="([^"]+)"', html)
                if meta:
                    desc = self._clean(meta.group(1))
            vod["vod_content"] = (desc + AD_INFO) if desc else AD_INFO

            episodes = self._parse_episodes(html)

            if episodes:
                vod["vod_play_from"] = "美剧天堂"
                vod["vod_play_url"] = "#".join(episodes[:999])
            else:
                vod["vod_play_from"] = "美剧天堂"
                vod["vod_play_url"] = "播放$%s/meijuplay/%s-0-0.html" % (
                    BASE_URL, vid)

            result["list"] = [vod]
        except Exception:
            pass
        return result

    def _extract_info(self, html, label):
        m = re.search(
            label + r'[：:]\s*<span\s*class="hide-text"[^>]*>([^<]+)</span>',
            html, re.S)
        if m:
            return self._clean(m.group(1))
        m = re.search(
            label + r'[：:]\s*<span[^>]*>([^<]+)</span>', html, re.S)
        if m:
            val = self._clean(m.group(1))
            if val and len(val) < 200 and "function" not in val:
                return val
        m = re.search(label + r'[：:]\s*(.*?)</li>', html, re.S)
        if m:
            raw = re.sub(r'<[^>]+>', '', m.group(1))
            val = self._clean(raw.split("/")[0].split("<")[0])
            if val and "function" not in val and len(val) < 200:
                return val
        return ""

    def _parse_episodes(self, html):
        episodes = []
        seen = set()

        source_names = {
            "playIco_wjm3u8": "无尽视频",
            "playIco_zuidam3u8": "最大视频",
            "playIco_snm3u8": "索尼视频",
        }

        source_blocks = re.findall(
            r'class="playIco_(\w+)"[^>]*>.*?<em>\[(\d+)\]</em>',
            html, re.S)

        for idx, (src_key, src_label) in enumerate(source_names.items()):
            pattern = (
                r'<ul[^>]*class="mn_list_li_movie"[^>]*id="vlink_%d"'
                r'(.*?)</ul>' % (idx + 1))
            um = re.search(pattern, html, re.S)
            if not um:
                continue

            for em in re.finditer(
                    r'<a[^>]*href="(/meijuplay/(\d+)-(\d+)-(\d+)\.html)"'
                    r'[^>]*>([^<]+)</a>', um.group(1)):
                href = em.group(1)
                ep_label = self._clean(em.group(5))
                key = "%s_%s" % (src_label, href)
                if key in seen:
                    continue
                seen.add(key)
                episodes.append(
                    "%s%s$%s" % (src_label, ep_label, BASE_URL + href))

        if not episodes:
            for em in re.finditer(
                    r'href="(/meijuplay/(\d+)-(\d+)-(\d+)\.html)"'
                    r'[^>]*>([^<]+)</a>', html):
                href = em.group(1)
                ep_label = self._clean(em.group(5))
                key = href
                if key in seen:
                    continue
                seen.add(key)
                episodes.append("%s$%s" % (ep_label, BASE_URL + href))

        return episodes

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": str(pg), "pagecount": "1",
                  "total": "0"}
        try:
            html = self._post(
                "/search.php",
                {"searchword": str(key)})

            if html and "安全验证" not in html and "验证码" not in html:
                items = self._parse_search_results(html)
                if items:
                    for it in items:
                        it["vod_content"] = AD_INFO
                    result["list"] = items
                    result["pagecount"] = "1"
                    result["total"] = str(len(items))
                    return result

            items = self._search_fallback(key)
            for it in items:
                it["vod_content"] = AD_INFO
            result["list"] = items
            result["pagecount"] = "1"
            result["total"] = str(len(items))
        except Exception:
            pass
        return result

    def _parse_search_results(self, html):
        items = []
        seen = set()
        if not html or "安全验证" in html:
            return items

        for m in re.finditer(
                r'<a[^>]*href="(/meijutt/(\d+)\.html)"[^>]*>'
                r'\s*<img[^>]*(?:data-original|src)="([^"]+)"[^>]*>'
                r'.*?</a>\s*'
                r'<p[^>]*class="move_title_p1"[^>]*>\s*'
                r'<a[^>]*>([^<]+)</a>',
                html, re.S):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": self._clean(m.group(4)),
                "vod_pic": m.group(3),
                "vod_remarks": "",
            })

        if not items:
            for m in re.finditer(
                    r'<a[^>]*href="(/meijutt/(\d+)\.html)"[^>]*'
                    r'title="([^"]*)"[^>]*>',
                    html):
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": self._clean(m.group(3)),
                    "vod_pic": "",
                    "vod_remarks": "",
                })
        return items

    def _search_fallback(self, key):
        key = str(key).strip().lower()
        if not key:
            return []
        results = []
        seen = set()
        search_cats = ["mhkh", "lyjt", "dsqg", "fzls", "xuzy", "dmtk"]
        for cat_id in search_cats:
            for pg in range(1, 6):
                try:
                    data = self.categoryContent(cat_id, str(pg), None, None)
                    for item in data.get("list", []):
                        vid = item.get("vod_id", "")
                        nm = item.get("vod_name", "").lower()
                        if (key in nm or nm in key) and vid not in seen:
                            seen.add(vid)
                            results.append(item)
                    if len(results) >= 30:
                        break
                except Exception:
                    continue
            if len(results) >= 30:
                break
        return results

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = id
            if not play_url.startswith("http"):
                play_url = BASE_URL + "/" + play_url.lstrip("/")

            html = self._get(play_url, timeout=15, retries=2)
            if html:
                m3u8 = ""
                pm = re.search(
                    r'var\s+now\s*=\s*unescape\s*\(\s*"([^"]+)"', html)
                if pm:
                    m3u8 = urllib.parse.unquote(pm.group(1))

                if not m3u8:
                    pm = re.search(
                        r'var\s+now\s*=\s*unescape\s*\(\s*\'([^\']+)', html)
                    if pm:
                        m3u8 = urllib.parse.unquote(pm.group(1))

                if not m3u8:
                    pm = re.search(
                        r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
                    if pm:
                        m3u8 = pm.group(0)

                if m3u8:
                    if m3u8.startswith("//"):
                        m3u8 = "https:" + m3u8
                    m3u8 = m3u8.replace("\\/", "/")
                    headers = {
                        "User-Agent": self.UA,
                        "Referer": BASE_URL + "/",
                    }
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": m3u8,
                        "header": json.dumps(headers, ensure_ascii=False),
                    }
        except Exception:
            pass

        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": "",
        }


# ==================== CLI 测试 ====================

def _cli():
    import sys
    sp = Spider()
    sp.init()
    if len(sys.argv) < 2:
        print("用法: python 美剧天堂.py home|list <分类id> <页>|detail <ID>|play <URL>|search <关键词>")
        return
    cmd = sys.argv[1].lower()
    if cmd == "home":
        print(json.dumps(sp.homeVideoContent(), ensure_ascii=False, indent=2))
    elif cmd == "list":
        tid = sys.argv[2] if len(sys.argv) > 2 else "mhkh"
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
