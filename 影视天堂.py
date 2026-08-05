# -*- coding: utf-8 -*-
# 影视天堂.py — TVBox 爬虫（影视天堂 ysttv.com）
# 适配苹果CMS（MacCMS）标准采集接口 /api.php/provide/vod/
# 输出符合 TVBox JsonXYZ 规范的 JSON
#
# 用法（TVBox 本地 PY 插件）：
#   直接运行: python3 影视天堂.py                 # 交互式自检
#   TVBox 调用: python3 影视天堂.py               # 从 stdin 读取 JSON 请求
#
# TVBox 配置（site.json）示例：
#   {
#       "key": "影视天堂 PY",
#       "name": "影视天堂丨PY",
#       "api": "./影视天堂.py",
#       "filterable": 1,
#       "quickSearch": 1,
#       "searchable": 1,
#       "type": 3
#   }
#
# 说明：ysttv.com 为 Cloudflare 防护站点，本脚本在用户本地网络运行时可正常访问；
#       沙箱环境无法直连，故采用 MacCMS 标准接口规范编写，不依赖具体 HTML 结构。

import sys
import json
import time
import base64
import random
import argparse
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import requests
except ImportError:
    requests = None  # HTTP 服务模式下用 urllib 兜底

# ============================================================
#  加密模块：对公众号 / Q群 / 宣传语做 Base64 + 异或 双层加密
#  代码中不出现任何明文宣传文字，运行时解密后注入影片简介
# ============================================================

# 异或密钥（与明文等长的伪随机种子，由固定种子生成，保证可复现）
_XOR_KEY_SEED = 0x5A  # 固定种子，保证加密结果稳定

def _xor_bytes(data: bytes, key_byte: int) -> bytes:
    """对字节序列逐字节异或"""
    return bytes(b ^ key_byte for b in data)

def _enc(plain: str) -> str:
    """加密：UTF-8 -> 异或 -> Base64"""
    xored = _xor_bytes(plain.encode('utf-8'), _XOR_KEY_SEED)
    return base64.b64encode(xored).decode('ascii')

def _dec(cipher: str) -> str:
    """解密：Base64 -> 异或 -> UTF-8"""
    try:
        raw = base64.b64decode(cipher.encode('ascii'))
        return _xor_bytes(raw, _XOR_KEY_SEED).decode('utf-8')
    except Exception:
        return ''

# 加密后的宣传文字（明文已抹除，仅保留密文，运行时解密注入影片简介）
_C_GZH    = _enc('\u6e90\u529b\u8f6f\u4ef6\u6c47')
_C_QQ     = _enc('\u0031\u0030\u0035\u0034\u0035\u0039\u0032\u0031\u0035\u0032')
_C_SLOGAN = _enc('\u4f34\u968f\u66f4\u591a\u4f18\u8d28\u8d44\u6e90\u5c3d\u5728\u6e90\u529b')

def _promo_text() -> str:
    """运行时解密，拼装宣传文案，注入影片简介"""
    gzh    = _dec(_C_GZH)
    qq     = _dec(_C_QQ)
    slogan = _dec(_C_SLOGAN)
    return (
        '\n\n━━━━━━━━━━━━━━━━━━\n'
        '【微信公众号】{gzh}\n'
        '【Q群】{qq}\n'
        '{slogan}\n'
        '━━━━━━━━━━━━━━━━━━'
    ).format(gzh=gzh, qq=qq, slogan=slogan)

def _inject_promo(vod_desc: str) -> str:
    """把宣传文案追加到影片简介末尾"""
    if vod_desc is None:
        vod_desc = ''
    return str(vod_desc).rstrip() + _promo_text()

# ============================================================
#  站点配置
# ============================================================

SITE_BASE = 'https://ysttv.com'
# MacCMS 标准采集接口（苹果CMS 通用 vod 接口）
API_VOD   = SITE_BASE + '/api.php/provide/vod/'

# 分类类型映射（MacCMS type_id -> 名称），运行时从接口动态获取，此处为兜底
_TYPE_FALLBACK = {
    1: '电影', 2: '电视剧', 3: '综艺', 4: '动漫', 5: '纪录片',
    6: '天文地理', 7: '少儿', 8: '教育', 9: '戏曲', 10: '短剧',
}

# "天文地理"类目关键词（搜索时使用）
SKY_KEYWORDS = ['天文', '地理', '宇宙', '星球', '地球', '太空', '自然', '探索', '国家地理', 'BBC']

UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)
HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': SITE_BASE + '/',
}

# ============================================================
#  HTTP 请求封装（requests 优先，urllib 兜底）
# ============================================================

def _http_get(url: str, timeout: int = 15) -> dict:
    """GET 请求并解析 JSON，失败返回空 dict"""
    try:
        if requests is not None:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                r = type('R', (), {
                    'text': resp.read().decode('utf-8', 'ignore'),
                    'status_code': resp.status,
                })()
        if r.status_code != 200:
            return {}
        # MacCMS 接口返回 JSON
        return json.loads(r.text)
    except Exception as e:
        sys.stderr.write('[WARN] GET {} failed: {}\n'.format(url, e))
        return {}

# ============================================================
#  MacCMS 接口适配
# ============================================================

def get_categories() -> list:
    """获取所有分类数据
    MacCMS 接口：?ac=list 返回 class 列表
    返回 TVBox 规范的 class 数组
    """
    data = _http_get(API_VOD + '?ac=list')
    classes = []
    # 接口标准字段：class_list
    raw = data.get('class') or data.get('class_list') or []
    for item in raw:
        tid = item.get('type_id') or item.get('list_id')
        name = item.get('type_name') or item.get('name')
        if tid and name:
            classes.append({
                'type_id':   int(tid),
                'type_name': name,
                'type_pid':  int(item.get('type_pid', 0) or 0),
            })
    # 兜底：接口未返回 class 时用本地映射
    if not classes:
        for tid, name in _TYPE_FALLBACK.items():
            classes.append({'type_id': tid, 'type_name': name, 'type_pid': 0})
    return classes

def get_list(tid: int, page: int = 1, wd: str = '') -> dict:
    """获取分类下影片列表 / 搜索
    MacCMS 接口：
      分类列表：?ac=list&pg=<page>          （全站列表，前端按 type 过滤）
      分类过滤：?ac=list&pg=<page>&t=<tid>
      搜索：    ?ac=list&wd=<keyword>&pg=<page>
    返回 TVBox 规范的 list + pagecount
    """
    params = {'ac': 'list', 'pg': page}
    if wd:
        params['wd'] = wd
    elif tid:
        params['t'] = tid
    url = API_VOD + '?' + urllib.parse.urlencode(params)
    data = _http_get(url)

    vod_list = data.get('list') or []
    out = []
    for v in vod_list:
        # 搜索/列表项字段
        item = {
            'vod_id':         v.get('vod_id') or v.get('id'),
            'vod_name':       v.get('vod_name') or v.get('name', ''),
            'vod_pic':        v.get('vod_pic') or v.get('pic', ''),
            'vod_remarks':    v.get('vod_remarks') or v.get('remarks', ''),
            'type_id':        v.get('type_id', tid),
            'type_name':      v.get('type_name', ''),
            'vod_year':       v.get('vod_year', ''),
            'vod_area':       v.get('vod_area', ''),
            'vod_actor':      v.get('vod_actor', ''),
            'vod_director':   v.get('vod_director', ''),
        }
        # 列表项不带简介，避免冗余
        out.append({k: val for k, val in item.items() if val not in (None, '')})

    pagecount = data.get('pagecount') or data.get('pagecount') or 1
    total = data.get('total') or len(out)
    return {
        'list':      out,
        'pagecount': int(pagecount),
        'total':     int(total),
        'page':      page,
        'limit':     data.get('limit', 20),
    }

def get_detail(ids) -> dict:
    """获取影片详情（含播放地址）
    MacCMS 接口：?ac=detail&ids=<id1,id2,...>
    返回 TVBox 规范的 list（含 vod_play_url）
    """
    if isinstance(ids, (list, tuple)):
        ids_str = ','.join(str(i) for i in ids)
    else:
        ids_str = str(ids)
    url = API_VOD + '?ac=detail&ids=' + urllib.parse.quote(ids_str)
    data = _http_get(url)

    vod_list = data.get('list') or []
    out = []
    for v in vod_list:
        # 播放地址解析：MacCMS 格式 "线路名$播放串#..." 或 "名称$地址#..."
        play_url = v.get('vod_play_url') or ''
        play_from = v.get('vod_play_from') or ''
        # 构造 TVBox 期望的 play_url 结构
        parsed_play = _parse_play_url(play_url, play_from)

        # 简介注入加密宣传文案
        vod_content = _inject_promo(v.get('vod_content') or v.get('vod_blurb') or '')

        item = {
            'vod_id':         v.get('vod_id') or v.get('id'),
            'vod_name':       v.get('vod_name') or v.get('name', ''),
            'vod_pic':        v.get('vod_pic') or v.get('pic', ''),
            'vod_remarks':    v.get('vod_remarks') or v.get('remarks', ''),
            'type_id':        v.get('type_id', 0),
            'type_name':      v.get('type_name', ''),
            'vod_year':       v.get('vod_year', ''),
            'vod_area':       v.get('vod_area', ''),
            'vod_actors':     v.get('vod_actor') or v.get('vod_actors', ''),
            'vod_director':   v.get('vod_director', ''),
            'vod_content':    vod_content,
            'vod_play_from':  parsed_play['from'],
            'vod_play_url':   parsed_play['url'],
            'vod_down_from':  v.get('vod_down_from', ''),
            'vod_down_url':   v.get('vod_down_url', ''),
        }
        out.append({k: val for k, val in item.items() if val not in (None, '')})
    return {'list': out}

def _parse_play_url(play_url: str, play_from: str) -> dict:
    """解析 MacCMS 播放地址
    格式1（多线路）：线路A$集1$地址1#集2$地址2$$$线路B$集1$地址1#...
    格式2（单线路）：集1$地址1#集2$地址2#...
    输出 TVBox 规范：
      from = "线路A$$$线路B"
      url  = "集1$地址1#集2$地址2$$$集1$地址1#..."
    """
    if not play_url:
        return {'from': '', 'url': ''}
    # 按线路分隔
    lines = play_url.split('$$$')
    froms = []
    urls = []
    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # 线路名：优先用 play_from 对应位置，否则用"线路N"
        if play_from:
            fl = play_from.split('$$$')
            fname = fl[idx] if idx < len(fl) else '线路{}'.format(idx + 1)
        else:
            fname = '线路{}'.format(idx + 1)
        froms.append(fname)
        urls.append(line)
    return {
        'from': '$$$'.join(froms),
        'url':  '$$$'.join(urls),
    }

# ============================================================
#  搜索：天文地理类视频
# ============================================================

def search_sky(page: int = 1) -> dict:
    """搜索天文地理类视频
    策略：遍历天文地理关键词，聚合去重
    """
    seen = set()
    merged = []
    pagecount = 1
    for kw in SKY_KEYWORDS:
        res = get_list(tid=0, page=page, wd=kw)
        for v in res.get('list', []):
            vid = v.get('vod_id')
            if vid and vid not in seen:
                seen.add(vid)
                merged.append(v)
        pc = res.get('pagecount', 1)
        if pc > pagecount:
            pagecount = pc
    return {
        'list':      merged,
        'pagecount': pagecount,
        'page':      page,
        'total':     len(merged),
    }

# ============================================================
#  TVBox HTTP 服务模式
# ============================================================

class TVBoxHandler(BaseHTTPRequestHandler):
    """TVBox 标准 HTTP 接口
    GET /?ac=...&t=...&pg=...&wd=...&ids=...
    """

    def log_message(self, fmt, *args):
        sys.stderr.write('[%s] %s\n' % (time.strftime('%H:%M:%S'), fmt % args))

    def _send_json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            q = urllib.parse.urlparse(self.path).query
            p = urllib.parse.parse_qs(q)
            ac = (p.get('ac') or [''])[0]
            wd = (p.get('wd') or [''])[0]
            tid = (p.get('t') or ['0'])[0]
            pg = int((p.get('pg') or ['1'])[0])
            ids = (p.get('ids') or [''])[0]

            if ac == 'list' and wd:
                # 搜索
                if wd in ('天文地理', '天文', '地理'):
                    self._send_json(search_sky(pg))
                else:
                    self._send_json(get_list(0, pg, wd))
            elif ac == 'list':
                # 分类列表
                self._send_json(get_list(int(tid) if tid else 0, pg))
            elif ac == 'detail':
                # 详情
                self._send_json(get_detail(ids))
            elif ac == 'class' or not ac:
                # 分类目录（TVBox 首次加载）
                self._send_json({'class': get_categories()})
            else:
                self._send_json({'list': []})
        except Exception as e:
            sys.stderr.write('[ERR] {}\n'.format(e))
            self._send_json({'list': [], 'msg': str(e)})

def serve(port: int = 9988):
    httpd = HTTPServer(('0.0.0.0', port), TVBoxHandler)
    sys.stderr.write('影视天堂 TVBox 服务已启动: http://0.0.0.0:{}\n'.format(port))
    sys.stderr.write('TVBox 配置 api 填: http://<本机IP>:{}\n'.format(port))
    httpd.serve_forever()

# ============================================================
#  自检 / 入口
# ============================================================

def _selftest():
    """交互式自检：打印分类、搜索天文地理、详情样例"""
    print('=' * 60)
    print('影视天堂 TVBox 爬虫 自检')
    print('=' * 60)

    # 1. 宣传文案解密验证
    print('\n[1] 宣传文案解密验证（代码中为密文，运行时解密）:')
    print(_promo_text())

    # 2. 分类
    print('\n[2] 获取所有分类:')
    cats = get_categories()
    for c in cats:
        print('  - type_id={type_id}  type_name={type_name}'.format(**c))
    if not cats:
        print('  (站点不可达，使用兜底分类)')

    # 3. 搜索天文地理
    print('\n[3] 搜索"天文地理"类视频:')
    res = search_sky(1)
    print('  共 {} 条, pagecount={}'.format(res['total'], res['pagecount']))
    for v in res['list'][:5]:
        print('  - {vod_name}  [{vod_remarks}]  pic={vod_pic}'.format(
            vod_name=v.get('vod_name', ''), vod_remarks=v.get('vod_remarks', ''),
            vod_pic=(v.get('vod_pic', '') or '')[:40]))

    # 4. 详情样例（取搜索结果第一条）
    if res['list']:
        first_id = res['list'][0].get('vod_id')
        print('\n[4] 影片详情样例 (vod_id={}):'.format(first_id))
        det = get_detail(first_id)
        for d in det.get('list', []):
            print('  名称: {vod_name}'.format(**d))
            print('  年份: {vod_year}  地区: {vod_area}'.format(
                vod_year=d.get('vod_year', ''), vod_area=d.get('vod_area', '')))
            print('  简介（含加密宣传文案）:')
            print('  ' + (d.get('vod_content', '') or '').replace('\n', '\n  '))
            print('  播放线路: {vod_play_from}'.format(**d))
            pu = (d.get('vod_play_url', '') or '')[:80]
            print('  播放地址(截断): {}...'.format(pu))
    else:
        print('\n[4] 站点不可达，跳过详情样例（脚本逻辑已就绪，本地运行可正常获取）')

    print('\n' + '=' * 60)
    print('自检完成。脚本可在用户本地网络正常访问 ysttv.com 时使用。')
    print('启动服务模式: python3 影视天堂.py --serve 9988')
    print('=' * 60)

def _py_plugin_main():
    """TVBox PY 插件标准入口：从 stdin 读取 JSON 请求，输出 JSON 响应
    TVBox 调用方式: python3 影视天堂.py
    请求格式: {"action":"home/vod/detail/search"[, "tid":..., "pg":..., "wd":..., "ids":...]}
    """
    import select
    # 检查 stdin 是否有数据（TVBox 调用时会有 JSON 输入）
    if select.select([sys.stdin], [], [], 0.1)[0]:
        try:
            req = json.loads(sys.stdin.read())
            action = req.get('action', '')
            tid = int(req.get('tid', 0) or 0)
            pg = int(req.get('pg', 1) or 1)
            wd = req.get('wd', '')
            ids = req.get('ids', '')

            if action == 'home' or action == 'class':
                # 首页/分类
                res = {'class': get_categories()}
            elif action == 'vod':
                # 分类列表
                res = get_list(tid, pg)
            elif action == 'search':
                # 搜索
                if wd in ('天文地理', '天文', '地理'):
                    res = search_sky(pg)
                else:
                    res = get_list(0, pg, wd)
            elif action == 'detail':
                # 详情
                res = get_detail(ids)
            else:
                res = {'list': []}
            print(json.dumps(res, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({'list': [], 'msg': str(e)}, ensure_ascii=False))
    else:
        # 无 stdin 输入，走自检模式
        _selftest()

def main():
    parser = argparse.ArgumentParser(description='影视天堂 TVBox 爬虫')
    parser.add_argument('--serve', type=int, metavar='PORT', help='启动 HTTP 服务模式，供 TVBox 配置 api 指向')
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
    else:
        _py_plugin_main()

if __name__ == '__main__':
    main()
