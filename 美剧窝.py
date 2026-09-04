#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美剧屋 TVBox 接口
网站: https://www.mjwu.cc/
模式1 (TVBox type3): python 美剧窝.py ac=detail&t=1&pg=1
模式2 (HTTP服务):    python 美剧窝.py --serve [端口号]
"""

import json
import re
import sys
import time
import traceback
from urllib.request import Request, urlopen
from urllib.parse import quote

BASE_URL = "https://www.mjwu.cc"
PROMO = ("\n\n———————————————————\n"
         "微信公众号「源力软件汇」\n"
         "QQ群 1054592152\n"
         "伴随更多优质资源尽在源力")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Referer": BASE_URL + "/",
}

TYPE_MAP = {
    1: {"type_name": "美剧", "type_url": "meiju"},
    2: {"type_name": "电影", "type_url": "dianying"},
}

CLASSES = [
    {"type_id": 1, "type_name": "美剧", "type_flag": ""},
    {"type_id": 2, "type_name": "电影", "type_flag": ""},
]


def fetch(url, retries=2):
    for i in range(retries + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as resp:
                data = resp.read()
                for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
                    try:
                        return data.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="ignore")
        except Exception as e:
            if i == retries:
                print(f"[ERROR] fetch {url}: {e}", file=sys.stderr)
                return ""
            time.sleep(0.5)
    return ""


def clean(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def parse_list_page(html):
    if not html:
        return []
    videos = []
    seen = set()
    items = re.split(r'<li\s+class="hl-list-item[^"]*">', html)
    for block in items[1:]:
        m_href = re.search(r'href="/vod/(\d+)/"', block)
        if not m_href:
            continue
        vod_id = int(m_href.group(1))
        if vod_id in seen:
            continue
        seen.add(vod_id)
        m_title = re.search(
            r'title="([^"]*)"[^>]*data-original="([^"]*)"', block
        )
        if not m_title:
            continue
        name = m_title.group(1)
        pic = m_title.group(2)
        m_remark = re.search(
            r'class="hl-lc-1 remarks">([^<]*)</span>', block
        )
        remarks = m_remark.group(1).strip() if m_remark else ""
        m_score = re.search(
            r'class="hl-text-conch score">([^<]*)</span>', block
        )
        score = m_score.group(1).strip() if m_score else ""
        m_sub = re.search(
            r'class="hl-item-sub hl-text-muted hl-lc-1">(.*?)</div>',
            block, re.DOTALL
        )
        sub = clean(m_sub.group(1)) if m_sub else ""
        if not score and sub:
            ms = re.match(r"([\d.]+)\s*", sub)
            if ms:
                score = ms.group(1)
        videos.append({
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_score": score,
        })
    return videos


def parse_search_page(html):
    if not html:
        return []
    videos = []
    items = re.split(
        r'<li\s+class="hl-list-item\s+hl-col-xs-12">', html
    )
    for block in items[1:]:
        m_href = re.search(r'href="/vod/(\d+)/"', block)
        if not m_href:
            continue
        vod_id = int(m_href.group(1))
        m_title = re.search(
            r'title="([^"]*)"[^>]*data-original="([^"]*)"', block
        )
        if not m_title:
            continue
        name = m_title.group(1)
        pic = m_title.group(2)
        m_remark = re.search(
            r'class="hl-lc-1 remarks">([^<]*)</span>', block
        )
        remarks = m_remark.group(1).strip() if m_remark else ""
        m_score = re.search(
            r'class="hl-text-conch score">([^<]*)</span>', block
        )
        score = m_score.group(1).strip() if m_score else ""
        m_info = re.search(
            r'class="hl-item-sub hl-lc-1">(.*?)</p>', block, re.DOTALL
        )
        info = clean(m_info.group(1)) if m_info else ""
        type_name = ""
        vod_year = ""
        vod_area = ""
        for p in re.split(r"[\u00b7\s]+", info):
            p = p.strip()
            if not p:
                continue
            if re.match(r"\d{4}$", p):
                vod_year = p
            elif p in (
                "美国", "英国", "法国", "德国", "日本", "韩国", "中国",
                "加拿大", "澳大利亚", "西班牙", "巴西", "意大利",
                "墨西哥", "俄罗斯", "土耳其", "其它",
            ):
                vod_area = p
            elif (
                p
                and not re.match(r"^(豆瓣高分|\d+\.\d+)$", p)
                and not type_name
            ):
                type_name = p
        m_desc = re.search(
            r'class="hl-item-sub hl-text-muted hl-lc-2">(.*?)</p>',
            block, re.DOTALL
        )
        desc = clean(m_desc.group(1)) if m_desc else ""
        videos.append({
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_score": score,
            "type_name": type_name,
            "vod_year": vod_year,
            "vod_area": vod_area,
            "vod_content": desc,
        })
    return videos


def parse_total_pages(html):
    if not html:
        return 1
    text = html.replace("&nbsp;", " ")
    m = re.search(r"(\d+)\s*/\s*(\d+)\s*页", text)
    return int(m.group(2)) if m else 1


def parse_detail(html):
    if not html:
        return {}
    d = {}
    m = re.search(r'class="hl-dc-title[^"]*">([^<]+)</h2>', html)
    if m:
        d["vod_name"] = clean(m.group(1))
    m = re.search(r'class="hl-item-thumb[^"]*"[^>]*data-original="([^"]*)"', html)
    if m:
        d["vod_pic"] = m.group(1)
    for key, val in re.findall(
        r'<li[^>]*><em class="hl-text-muted">([^：]+)：</em>(.*?)</li>',
        html, re.DOTALL,
    ):
        val = clean(val)
        key = key.strip()
        if key == "片名":
            d["vod_name"] = val
        elif key == "状态":
            d["vod_remarks"] = val
        elif key == "主演":
            d["vod_actor"] = val
        elif key == "导演":
            d["vod_director"] = val
        elif key == "年份":
            d["vod_year"] = val
        elif key == "地区":
            d["vod_area"] = val
        elif key == "类型":
            d["type_name"] = val
        elif key == "语言":
            d["vod_lang"] = val
        elif key == "简介":
            d["vod_content"] = val
    m = re.search(
        r'class="hl-score-nums[^"]*">\s*<span>([^<]+)</span>', html
    )
    if m:
        d["vod_score"] = m.group(1).strip()
    sources = [
        clean(s)
        for s in re.findall(
            r'<a\s+class="hl-tabs-btn[^"]*"[^>]*alt="([^"]*)"', html
        )
        if clean(s)
    ]
    if not sources:
        sources = ["云播"]
    episodes = re.findall(
        r'<a\s+href="(/play/(\d+)-(\d+)-(\d+)/)">([^<]+)</a>', html
    )
    play_from_list = []
    play_url_list = []
    if episodes:
        groups = {}
        for ep in episodes:
            sid = int(ep[2])
            groups.setdefault(sid, []).append(ep)
        for idx, sid in enumerate(sorted(groups.keys())):
            eps = groups[sid]
            sname = sources[idx] if idx < len(sources) else f"线路{idx + 1}"
            play_from_list.append(sname)
            play_url_list.append("#".join(
                f"{clean(ep[4])}${BASE_URL}{ep[0]}" for ep in eps
            ))
    d["vod_play_from"] = "$$$".join(play_from_list)
    d["vod_play_url"] = "$$$".join(play_url_list)
    return d


def fetch_list(type_id_str, page):
    type_id = int(type_id_str) if type_id_str else 0
    type_info = TYPE_MAP.get(type_id)
    if type_id and not type_info:
        return {"code": 0, "msg": f"未知类型: {type_id}"}
    if not type_id:
        html = fetch(BASE_URL + "/")
        videos = parse_list_page(html)
        total_page = 1
        tname = "综合"
    else:
        url = f"{BASE_URL}/show/{type_info['type_url']}/"
        if page > 1:
            url += f"page/{page}/"
        html = fetch(url)
        videos = parse_list_page(html)
        total_page = parse_total_pages(html)
        tname = type_info["type_name"]
    return {
        "code": 1,
        "msg": "ok",
        "page": page,
        "pagecount": max(total_page, 1),
        "limit": 36,
        "total": total_page * 36 if total_page > 1 else len(videos),
        "list": [
            {
                "vod_id": v["vod_id"],
                "vod_name": v["vod_name"],
                "vod_pic": v["vod_pic"],
                "vod_remarks": v.get("vod_remarks", ""),
                "type_name": tname,
                **({"vod_score": v["vod_score"]} if v.get("vod_score") else {}),
            }
            for v in videos
        ],
        "class": CLASSES,
    }


def fetch_detail(vod_id):
    html = fetch(f"{BASE_URL}/vod/{vod_id}/")
    if not html:
        return {"code": 0, "msg": "无法获取详情"}
    d = parse_detail(html)
    d["vod_content"] = d.get("vod_content", "") + PROMO
    return {
        "code": 1,
        "msg": "ok",
        "list": [{
            "vod_id": int(vod_id),
            "vod_name": d.get("vod_name", ""),
            "vod_pic": d.get("vod_pic", ""),
            "vod_year": d.get("vod_year", ""),
            "vod_area": d.get("vod_area", ""),
            "vod_remarks": d.get("vod_remarks", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_actor": d.get("vod_actor", ""),
            "vod_director": d.get("vod_director", ""),
            "vod_lang": d.get("vod_lang", ""),
            "type_name": d.get("type_name", ""),
            "vod_score": d.get("vod_score", ""),
            "vod_play_from": d.get("vod_play_from", ""),
            "vod_play_url": d.get("vod_play_url", ""),
        }],
    }


def fetch_search(keyword, pg=1):
    html = fetch(f"{BASE_URL}/search/--/?wd={quote(keyword)}")
    videos = parse_search_page(html)
    return {
        "code": 1,
        "msg": "ok",
        "page": pg,
        "pagecount": 1,
        "limit": 36,
        "total": len(videos),
        "list": [
            {
                "vod_id": v["vod_id"],
                "vod_name": v["vod_name"],
                "vod_pic": v["vod_pic"],
                "vod_remarks": v.get("vod_remarks", ""),
                "type_name": v.get("type_name", ""),
                **({"vod_score": v["vod_score"]} if v.get("vod_score") else {}),
                **({"vod_year": v["vod_year"]} if v.get("vod_year") else {}),
                **({"vod_area": v["vod_area"]} if v.get("vod_area") else {}),
            }
            for v in videos
        ],
        "class": CLASSES,
    }


def fetch_home():
    result = []
    seen = set()
    for v in parse_list_page(fetch(BASE_URL + "/")):
        if v["vod_id"] not in seen:
            seen.add(v["vod_id"])
            result.append({
                "vod_id": v["vod_id"],
                "vod_name": v["vod_name"],
                "vod_pic": v["vod_pic"],
                "vod_remarks": v.get("vod_remarks", ""),
                "type_name": "美剧",
            })
    for v in parse_list_page(fetch(f"{BASE_URL}/show/meiju/")):
        if v["vod_id"] not in seen:
            seen.add(v["vod_id"])
            result.append({
                "vod_id": v["vod_id"],
                "vod_name": v["vod_name"],
                "vod_pic": v["vod_pic"],
                "vod_remarks": v.get("vod_remarks", ""),
                "type_name": "美剧",
            })
    for v in parse_list_page(fetch(f"{BASE_URL}/show/dianying/")):
        if v["vod_id"] not in seen:
            seen.add(v["vod_id"])
            result.append({
                "vod_id": v["vod_id"],
                "vod_name": v["vod_name"],
                "vod_pic": v["vod_pic"],
                "vod_remarks": v.get("vod_remarks", ""),
                "type_name": "电影",
            })
    return {"code": 1, "msg": "ok", "list": result, "class": CLASSES}


def handle_params(params_str):
    params = {}
    for pair in params_str.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            params[k] = v
    if "ac" in params:
        ac = params["ac"]
        if ac == "list":
            return {"code": 1, "msg": "ok", "class": CLASSES, "list": []}
        elif ac == "detail":
            if "ids" in params:
                return fetch_detail(params["ids"])
            return fetch_list(
                params.get("t", ""), int(params.get("pg", "1"))
            )
        return {"code": 0, "msg": f"未知ac: {ac}"}
    if "wd" in params:
        return fetch_search(params["wd"], int(params.get("pg", "1")))
    if "ids" in params:
        return fetch_detail(params["ids"])
    if "t" in params or "pg" in params:
        return fetch_list(params.get("t", ""), int(params.get("pg", "1")))
    return fetch_home()


def start_server(port):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            try:
                if "ac" in params:
                    ac = params["ac"][0]
                    if ac == "list":
                        data = {"code": 1, "msg": "ok", "class": CLASSES, "list": []}
                    elif ac == "detail":
                        if "ids" in params:
                            data = fetch_detail(params["ids"][0])
                        else:
                            data = fetch_list(
                                params.get("t", [""])[0],
                                int(params.get("pg", ["1"])[0]),
                            )
                    else:
                        data = {"code": 0, "msg": f"未知ac: {ac}"}
                elif "wd" in params:
                    data = fetch_search(
                        params["wd"][0],
                        int(params.get("pg", ["1"])[0]),
                    )
                elif "ids" in params:
                    data = fetch_detail(params["ids"][0])
                elif "t" in params or "pg" in params:
                    data = fetch_list(
                        params.get("t", [""])[0],
                        int(params.get("pg", ["1"])[0]),
                    )
                else:
                    data = fetch_home()
            except Exception:
                traceback.print_exc()
                data = {"code": 0, "msg": "服务器内部错误"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            print(f"[{self.log_date_time_string()}] {fmt % args}")

    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"美剧屋服务已启动 -> http://0.0.0.0:{port}")
    print(f"TVBox源地址: http://127.0.0.1:{port}/?ac=list")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--serve":
            p = int(sys.argv[2]) if len(sys.argv) > 2 else 9978
            start_server(p)
        else:
            params_str = " ".join(sys.argv[1:])
            for sep in ["?", "#"]:
                if sep in params_str:
                    params_str = params_str.split(sep, 1)[1]
            result = handle_params(params_str)
            print(json.dumps(result, ensure_ascii=False))
    else:
        start_server(9978)
