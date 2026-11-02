# -*- coding: utf-8 -*-
"""
[4K]河豚 —— TVBox type=3 Python 源（河豚APP protobuf 协议）。

协议要点（勿删）：
  · 域名从 CONFIG.host（cos txt）取 domain 字段动态下发，接口为
    http://IP:PORT（2026-11-02 实测 43.240.158.154:18004）
  · 每次请求头带 publicParams：设备指纹 JSON 经 AES-128-CBC(key=iv) 加密 hex
  · sig = RSA PKCS1v1.5(timestamp+random+vapp, 公钥)；sig2/sig3 =
    AES-256-ECB(timestamp+random, dataIv) 切 8/24
  · 业务请求体：query 串 AES-256-ECB(mSafeCode) 加密，外层 protobuf
    f1=密文前20字节 f2=其余 f4=时间戳 f5=random8；响应 data 在 f3
  · 动态公钥：POST /api/v5/find/app/zone，data.f2+f3+f4+f5 拼接为新 RSA 公钥(b64 DER)
  · 接口：GET /api/v3/drama/getCategory（分类，converUrl 内嵌筛选配置）
         POST /api/proto/v5/drama/category（分类列表，f16=总数）
         POST /api/proto/v5/drama/getDetail（详情，f29=线路列表）
         POST /api/proto/v5/drama/search（搜索）
         POST /api/proto/v5/videoUsableUrl（播放地址解析，f1=直链 f6=请求头）
         GET  /api/ex/v3/security/tag/list（首页推荐，双层 AES-256-ECB 解密）

2026-11-02 重写记录（纯标准库 + 全分类筛选 + 全量搜索 + 简介推广文案）：
  1. 纯标准库：T3 运行时不保证 requests / pycryptodome，全部改为标准库实现——
     urllib HTTP、纯 Python AES-128/256（ECB 加解密 + CBC 加密）、
     纯 Python RSA PKCS1v1.5（最小 DER 解析 + 大数 modexp），无第三方依赖
  2. 全分类：GET /api/v3/drama/getCategory 拉取全部 7 个分类
     （电影21/剧集22/动漫25/综艺26/短剧27/漫剧28/直播29，typePid 扁平），
     converUrl 内嵌服务端下发的筛选配置 JSON，逐类解析为 TVBox 标准 filters
  3. 类型细分（实测验证 vodClass 必须传服务端原始标签，带"片"字返回 0 条）：
     电影 27 类（科幻/奇幻/战争/犯罪/武侠/历史/文艺…，显示名加"片"字）、
     剧集 16 类（古装/战争/青春偶像/喜剧/家庭/历史/商战/网剧…）、
     动漫 20 类、综艺 13 类、短剧 9 类；另含地区/语言/年份/导演/排序
     （vodOrderBy 实测支持 最新/最热/好评；vodDirector 实测有效；
     vodStar/vodState/vodVersion 服务端忽略，不提供）
  4. 搜索全量化：searchContent 不再只取第 1 条（原逻辑导致大部分影片搜不到），
     返回全部结果并支持翻页
  5. 详情：简介 XOR 加密前置微信公众号“源力软件汇”文案（密钥
     hetun_wechat_2026，运行时解密，代码中不出现明文）；
     补齐 vod_class；线路预检——首集经 videoUsableUrl 解析不出 http 直链的
     线路（如部分 zijian 影片返回 zijian_HP-* token）自动剔除，保证点开可播
  6. 分类分页：category 响应 f16=总数，据此计算 pagecount（原固定 9999）
"""

import base64
import http.client
import json
import math
import random
import re
import threading
import time
import urllib.parse
import uuid

# ============ 纯标准库 AES（128/192/256，ECB 加解密 + CBC 加密） ============


def _xtime(a):
    b = a << 1
    if b & 0x100:
        b ^= 0x11B
    return b & 0xFF


def _gf256_mul(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return result


def _build_aes_tables():
    exp = [0] * 256
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x = _gf256_mul(x, 0x03)
    sbox = [0] * 256
    inv_sbox = [0] * 256
    for i in range(256):
        inv = 0 if i == 0 else exp[(255 - log[i]) % 255]
        s = inv
        t = inv
        for _ in range(4):
            s = ((s << 1) | (s >> 7)) & 0xFF
            t ^= s
        sbox[i] = t ^ 0x63
        inv_sbox[sbox[i]] = i
    return bytes(sbox), bytes(inv_sbox)


_SBOX, _INV_SBOX = _build_aes_tables()


def _expand_key(key):
    """AES key expansion（兼容 128/192/256 位密钥）。"""
    nk = len(key) // 4
    nr = nk + 6
    words = [list(key[i * 4:(i + 1) * 4]) for i in range(nk)]
    rcon = 1
    while len(words) < 4 * (nr + 1):
        temp = list(words[-1])
        if len(words) % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= rcon
            rcon = _xtime(rcon)
        elif nk > 6 and len(words) % nk == 4:
            temp = [_SBOX[b] for b in temp]
        words.append([words[-nk][i] ^ temp[i] for i in range(4)])
    return [sum(words[i * 4:(i + 1) * 4], []) for i in range(nr + 1)], nr


def _shift_rows(state, encrypt=True):
    out = [0] * 16
    for r in range(4):
        for c in range(4):
            out[r + 4 * c] = state[r + 4 * ((c + (r if encrypt else -r)) % 4)]
    return out


def _mix_columns(state):
    out = state[:]
    for c in range(4):
        a, b, d, e = out[0 + 4 * c], out[1 + 4 * c], out[2 + 4 * c], out[3 + 4 * c]
        t = a ^ b ^ d ^ e
        out[0 + 4 * c] = a ^ t ^ _xtime(a ^ b)
        out[1 + 4 * c] = b ^ t ^ _xtime(b ^ d)
        out[2 + 4 * c] = d ^ t ^ _xtime(d ^ e)
        out[3 + 4 * c] = e ^ t ^ _xtime(e ^ a)
    return out


def _mul9(x):
    return _xtime(_xtime(_xtime(x))) ^ x


def _mul11(x):
    return _xtime(_xtime(_xtime(x))) ^ _xtime(x) ^ x


def _mul13(x):
    return _xtime(_xtime(_xtime(x))) ^ _xtime(_xtime(x)) ^ x


def _mul14(x):
    return _xtime(_xtime(_xtime(x))) ^ _xtime(_xtime(x)) ^ _xtime(x)


def _inv_mix_columns(state):
    out = state[:]
    for c in range(4):
        a, b, d, e = out[0 + 4 * c], out[1 + 4 * c], out[2 + 4 * c], out[3 + 4 * c]
        out[0 + 4 * c] = _mul14(a) ^ _mul11(b) ^ _mul13(d) ^ _mul9(e)
        out[1 + 4 * c] = _mul9(a) ^ _mul14(b) ^ _mul11(d) ^ _mul13(e)
        out[2 + 4 * c] = _mul13(a) ^ _mul9(b) ^ _mul14(d) ^ _mul11(e)
        out[3 + 4 * c] = _mul11(a) ^ _mul13(b) ^ _mul9(d) ^ _mul14(e)
    return out


def _aes_encrypt_block(block, round_keys, nr):
    state = [s ^ k for s, k in zip(block, round_keys[0])]
    for r in range(1, nr):
        state = [_SBOX[b] for b in state]
        state = _shift_rows(state, True)
        state = _mix_columns(state)
        state = [s ^ k for s, k in zip(state, round_keys[r])]
    state = [_SBOX[b] for b in state]
    state = _shift_rows(state, True)
    return bytes([s ^ k for s, k in zip(state, round_keys[nr])])


def _aes_decrypt_block(block, round_keys, nr):
    state = [s ^ k for s, k in zip(block, round_keys[nr])]
    for r in range(nr - 1, 0, -1):
        state = _shift_rows(state, False)
        state = [_INV_SBOX[b] for b in state]
        state = [s ^ k for s, k in zip(state, round_keys[r])]
        state = _inv_mix_columns(state)
    state = _shift_rows(state, False)
    state = [_INV_SBOX[b] for b in state]
    return bytes([s ^ k for s, k in zip(state, round_keys[0])])


def _pkcs7_pad(data):
    size = 16 - (len(data) % 16)
    return data + bytes([size] * size)


def _pkcs7_unpad(data):
    if not data or len(data) % 16:
        raise ValueError("bad aes data")
    size = data[-1]
    if size < 1 or size > 16 or data[-size:] != bytes([size] * size):
        raise ValueError("bad PKCS7 padding")
    return data[:-size]


def _aes_ecb_encrypt(data, key):
    round_keys, nr = _expand_key(key)
    data = _pkcs7_pad(data)
    out = bytearray()
    for i in range(0, len(data), 16):
        out += _aes_encrypt_block(data[i:i + 16], round_keys, nr)
    return bytes(out)


def _aes_ecb_decrypt(data, key):
    round_keys, nr = _expand_key(key)
    out = bytearray()
    for i in range(0, len(data), 16):
        out += _aes_decrypt_block(data[i:i + 16], round_keys, nr)
    return _pkcs7_unpad(bytes(out))


def _aes_cbc_encrypt(data, key, iv):
    round_keys, nr = _expand_key(key)
    data = _pkcs7_pad(data)
    out = bytearray()
    previous = iv
    for i in range(0, len(data), 16):
        block = bytes(b ^ p for b, p in zip(data[i:i + 16], previous))
        enc = _aes_encrypt_block(block, round_keys, nr)
        out += enc
        previous = enc
    return bytes(out)


# ============ 纯标准库 RSA PKCS1v1.5（公钥加密） ============


def _der_read(data, pos):
    """读取单个 DER TLV，返回 (tag, content, next_pos)。"""
    tag = data[pos]
    pos += 1
    length = data[pos]
    pos += 1
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(data[pos:pos + n], "big")
        pos += n
    return tag, data[pos:pos + length], pos + length


def _rsa_encrypt(text, public_key_b64):
    """RSA PKCS1v1.5 加密，公钥为 base64(SPKI DER)。"""
    der = base64.b64decode(public_key_b64)
    _, body, _ = _der_read(der, 0)                 # SEQUENCE (SPKI)
    _, _, p1 = _der_read(body, 0)                  # AlgorithmIdentifier
    _, bits, _ = _der_read(body, p1)               # BIT STRING
    payload = bits[1:] if bits and bits[0] == 0 else bits
    _, keyseq, _ = _der_read(payload, 0)           # RSAPublicKey SEQUENCE
    _, n_raw, p2 = _der_read(keyseq, 0)            # INTEGER n
    _, e_raw, _ = _der_read(keyseq, p2)            # INTEGER e
    n_raw = n_raw[1:] if n_raw[:1] == b"\x00" else n_raw
    e_raw = e_raw[1:] if e_raw[:1] == b"\x00" else e_raw
    n = int.from_bytes(n_raw, "big")
    e = int.from_bytes(e_raw, "big")
    k = (n.bit_length() + 7) // 8
    msg = str(text).encode("utf-8")
    ps_len = k - 3 - len(msg)
    if ps_len < 8:
        raise RuntimeError("RSA 明文过长")
    ps = bytes(random.randint(1, 255) for _ in range(ps_len))
    em = b"\x00\x02" + ps + b"\x00" + msg
    c = pow(int.from_bytes(em, "big"), e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode("utf-8")


# ============ protobuf 工具 ============


def _varint(value):
    value = int(value)
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _pb_int(field, value):
    return _varint(field << 3) + _varint(value)


def _pb_bytes(field, value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return _varint((field << 3) | 2) + _varint(len(value)) + value


def _read_varint(data, pos):
    value = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos
        shift += 7
    raise ValueError("bad protobuf varint")


def _pb_parse(data):
    if not isinstance(data, (bytes, bytearray)):
        return {}
    fields = {}
    pos = 0
    while pos < len(data):
        key, pos = _read_varint(data, pos)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _read_varint(data, pos)
        elif wire == 1:
            value = data[pos:pos + 8]
            pos += 8
        elif wire == 2:
            size, pos = _read_varint(data, pos)
            value = data[pos:pos + size]
            pos += size
        elif wire == 5:
            value = data[pos:pos + 4]
            pos += 4
        else:
            raise ValueError("unsupported protobuf wire type: %s" % wire)
        fields.setdefault(field, []).append(value)
    return fields


# ============ 影片简介推广文案（XOR 加密存储，运行时解密；勿在代码中出现明文） ============
# 解密结果：微信公众号“源力软件汇”，更多优质资源尽在源力捐赠版

_W_KEY = "hetun_wechat_2026"
_W_DATA = [
    24518, 20356, 20760, 20322, 21401, 8259, 28391, 21246, 36620, 20126,
    27686, 8297, 65363, 26310, 22826, 20266, 36126, 36140, 28405, 23625,
    22365, 28414, 21188, 25383, 36101, 29227,
]


def _get_wechat_info():
    try:
        return "".join(
            chr(b ^ ord(_W_KEY[i % len(_W_KEY)])) for i, b in enumerate(_W_DATA))
    except Exception:
        return ""


class Spider(object):
    CONFIG = {
        "appName": "河豚",
        "publicKey": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCr8SzZhjYy+rsya1K09t8d2K50pWFoBkgUqMpKOiW+3IEVKd4eTdvg9RSOjQ82kypL6R9BnsmrS1V8s4PVDwjQbUtYhTPPC9Hz16qY7rpD6m0d2vr09/UpWQ5uOy9PR0QTrsioveZ+DIe9jc3C+zBCu/kZSY/R8stwJoiitki3gwIDAQAB",
        "mSafeCode": "V04XQZNYRWN6T0JODZFIAG5CTZB3PT0=",
        "dataIv": "OC1A06E197EF10CF3F6058CA7A803B5E",
        "pkg": "com.djlxxl.xcydzkj",
        "host": "https://az1-1456692500.cos.ap-guangzhou.myqcloud.com/az1.txt",
        "vName": "7.0.0.2",
        "from": "蓝光4k,蓝光"
    }

    def __init__(self):
        self.cfg = dict(self.CONFIG)
        self.host = ""
        self.public_key = ""
        self.data_key = ""
        self.data_iv = ""
        self.common_key = "ed5fdsgucxumegqa"
        self.version = "7.0.0.2"
        self.dynamic_key = ""
        self.line_order, self.line_block = [], []
        self._class_cache = None          # [(type_id, type_name, filter_config dict)]
        self._class_cache_ts = 0.0
        self._conns = {}                  # (scheme, host, port) -> HTTPConnection
        self._http_lock = threading.Lock()

    def getName(self):
        return self.cfg.get("appName", "河豚")

    def init(self, extend=""):
        self.cfg = dict(self.CONFIG)
        if isinstance(extend, str) and '$' in extend:
            path, key = extend.split('$', 1)
            ext = self._load_config(path.strip(), key.strip())
            if isinstance(ext, dict):
                self.cfg.update(ext)
            elif ext:
                self.cfg['host'] = str(ext).strip()
        elif isinstance(extend, dict):
            self.cfg.update(extend)
        elif isinstance(extend, str) and extend.strip():
            try:
                if extend.startswith('{'):
                    self.cfg.update(json.loads(extend))
                else:
                    self.cfg['host'] = extend.strip()
            except Exception:
                self.cfg['host'] = extend.strip()

        self.host = str(self.cfg.get("host", "")).rstrip("/")
        self.public_key = str(self.cfg.get("publicKey", ""))
        self.data_key = str(self.cfg.get("mSafeCode", ""))
        self.data_iv = str(self.cfg.get("dataIv", ""))
        self.version = str(self.cfg.get("vName", "7.0.0.2"))
        self.dynamic_key = ""

        from_config = self.cfg.get("from", "")
        self.line_order, self.line_block = [], []
        if from_config and '@' in from_config:
            parts = from_config.split('@')
            if parts[0].strip():
                self.line_order = [k.strip() for k in re.split(r',|@@', parts[0]) if k.strip()]
            if len(parts) > 1 and parts[1].strip():
                self.line_block = [k.strip() for k in re.split(r',|@@', parts[1]) if k.strip()]
        elif from_config:
            self.line_order = [k.strip() for k in re.split(r',|@@', from_config) if k.strip()]

        if self.host and self.host.endswith(('.txt', '.json')):
            try:
                raw = self._http(self.host, None, {}, 12)
                domain = json.loads(raw.decode("utf-8", "ignore")).get("domain", "").strip().rstrip("/")
                if domain:
                    self.host = domain
            except Exception:
                pass

        if self.host:
            try:
                self._load_dynamic_key()
            except Exception:
                self.dynamic_key = ""

        self._class_cache = None
        self._class_cache_ts = 0.0

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        return bool(re.search(r"(?i)\.(?:mp4|m3u8|flv|mkv|avi|ts|mov|mpd|m4a|wmv)(?:\?.*)?$", str(url)))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, "text/plain", "", None]

    # ---- HTTP（纯标准库 http.client 持久连接，带重试） ----
    # 实测（2026-11-02）：该服务器对每次新建连接的首包响应极慢（urllib
    # 新连接 GET 超时、POST 7s+），必须复用 keep-alive 连接（复用后 0.06s）。

    def _get_conn(self, parsed):
        key = (parsed.scheme, parsed.hostname, parsed.port)
        conn = self._conns.get(key)
        if conn is None:
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=18)
            else:
                conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=18)
            self._conns[key] = conn
        return conn

    def _drop_conn(self, parsed):
        key = (parsed.scheme, parsed.hostname, parsed.port)
        conn = self._conns.pop(key, None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def _http(self, url, data, headers, timeout=18, retries=2):
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        last = None
        for _ in range(max(1, retries)):
            with self._http_lock:
                conn = self._get_conn(parsed)
                try:
                    conn.request("POST" if data is not None else "GET", path,
                                 body=data, headers=headers or {})
                    resp = conn.getresponse()
                    body = resp.read()
                    if resp.status >= 400:
                        last = RuntimeError("HTTP %s" % resp.status)
                        continue
                    return body
                except (http.client.HTTPException, OSError, TimeoutError) as error:
                    last = error
                # 连接失效（服务器空闲超时断开 / 网络抖动）：重建连接重试
                self._drop_conn(parsed)
        raise last if last else RuntimeError("request failed")

    def _load_config(self, config_path, config_key=None):
        try:
            content = self._http(config_path, None, {}, 12).decode("utf-8", "ignore")
            try:
                config = json.loads(content)
            except Exception:
                content = re.sub(r'(export\s+default\s+|module\.exports\s*=)|//.*?$|/\*.*?\*/',
                                 '', content, flags=re.MULTILINE | re.DOTALL)
                config = json.loads(re.search(r'(\{[\s\S]*\})', content).group(1))
            return config.get(config_key) if config_key else config
        except Exception:
            return None

    # ---- 协议封装（请求头 / 加密体 / 动态公钥） ----

    @staticmethod
    def _random(length):
        chars = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        return "".join(random.choice(chars) for _ in range(max(0, length - 1))) + "="

    def _device(self):
        uid = uuid.uuid4().hex.upper()
        return {
            "country": "CN", "vName": self.version, "cpuId": "MT6893Z%2FCZA", "young": 0,
            "facturer": "Xiaomi", "pkg": self.cfg.get("pkg", ""), "uuid": uid,
            "resolution": "1080x2272", "mac": "02%3A00%3A00%3A00%3A00%3A00", "abid": "397",
            "model": "M2012K11AC", "plat": "android", "udid": uid, "dpi": "440", "net": "1",
            "lang": "zh", "brand": "Xiaomi", "density": "2.75", "appName": self.cfg.get("appName", "河豚"),
            "cpu": "arm64-v8a", "chid": "10000", "carrier": "%E8%81%94%E9%80%9A",
            "_vOsCode": 30, "vOs": "11", "v": 1, "tenantId": "",
            "vApp": self.version.replace(".", ""), "device": 0, "androidID": uid.lower()[:16]
        }

    def _public_headers(self, protobuf=True):
        key = self.dynamic_key or self.public_key
        device = self._device()
        timestamp = int(time.time() * 1000)
        random_str = self._random(16)
        vapp = device.get("vApp") or "702"
        device["sig"] = _rsa_encrypt(str(timestamp) + random_str + vapp, key)
        device["random_str"] = random_str
        device["timestamp"] = timestamp
        sig23 = base64.b64encode(
            _aes_ecb_encrypt((str(timestamp) + random_str).encode("utf-8"),
                             self.data_iv.encode("utf-8"))).decode("utf-8")
        device["sig2"] = sig23[:8]
        device["sig3"] = sig23[8:]
        params = _aes_cbc_encrypt(
            json.dumps(device, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            self.common_key.encode("utf-8"), self.common_key.encode("utf-8")).hex()
        ctype = "application/x-protobuf" if protobuf else "application/json; charset=utf-8"
        accept = "application/x-protobuf" if protobuf else "application/json"
        return {
            "User-Agent": "okhttp/3.12.1", "Accept": accept, "Content-Type": ctype,
            "publicParams": json.dumps({"paramsData": params}, ensure_ascii=False, separators=(",", ":"))
        }

    def _secure_body(self, params):
        timestamp = int(time.time() * 1000)
        random8 = self._random(8)
        fake20 = self._random(20)
        query = "&".join("%s=%s" % (k, v) for k, v in params.items()
                         if v is not None and str(v) != "")
        # 与原协议一致：random8 + AES-256-ECB(query+timestamp) 的 base64 字符串，
        # 再按 20 字节切分进 protobuf f1/f2
        encrypted = random8.encode("utf-8") + base64.b64encode(_aes_ecb_encrypt(
            (query + str(timestamp)).encode("utf-8"), self.data_key.encode("utf-8")))
        return b"".join([
            _pb_bytes(1, encrypted[:20]), _pb_bytes(2, encrypted[20:]),
            _pb_bytes(3, fake20), _pb_int(4, timestamp), _pb_bytes(5, random8)
        ])

    def _post(self, path, body):
        if not self.host:
            raise RuntimeError("接口域名获取失败")
        return self._http(self.host + path, body, self._public_headers(True), 18)

    def _get_json(self, path):
        if not self.host:
            raise RuntimeError("接口域名获取失败")
        return json.loads(self._http(self.host + path, None,
                                     self._public_headers(False), 18).decode("utf-8", "ignore"))

    def _api_data(self, raw):
        values = _pb_parse(raw).get(3)
        return values[0] if values else b""

    def _load_dynamic_key(self):
        timestamp = int(time.time() * 1000)
        random_str = self._random(16)
        sign = _rsa_encrypt(str(timestamp) + random_str, self.public_key)
        body = b"".join([
            _pb_int(1, timestamp), _pb_bytes(2, sign), _pb_bytes(3, self._random(16)),
            _pb_bytes(4, random_str), _pb_bytes(5, self._random(16))
        ])
        fields = _pb_parse(self._api_data(self._post("/api/v5/find/app/zone", body)))
        self.dynamic_key = "".join(
            self._text(fields.get(n, [b""])[0]) for n in (2, 3, 4, 5))

    # ---- protobuf 解析工具 ----

    @staticmethod
    def _first(fields, number, default=b""):
        values = fields.get(number)
        return values[0] if values else default

    @staticmethod
    def _text(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", "ignore")
        return str(value or "")

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    def _parse_cover(self, raw):
        f = _pb_parse(raw)
        return {"path": self._text(self._first(f, 1)), "thumb": self._text(self._first(f, 2))}

    @staticmethod
    def _clean_pic(text):
        # 部分封面 URL 前带乱码字符（如 xhttps://...），截到 http 起
        return re.sub(r'^[^h]*', '', str(text or ""))

    def _extract_pic(self, cover_raw):
        if not cover_raw:
            return ""
        try:
            cf = _pb_parse(cover_raw)
        except Exception:
            return ""
        for num in (2, 1):                     # thumb 优先
            for v in cf.get(num, []):
                t = self._clean_pic(self._text(v))
                if t.startswith("http"):
                    return t
        for values in cf.values():             # 兜底扫全部字段
            for v in values:
                t = self._clean_pic(self._text(v))
                if t.startswith("http"):
                    return t
        return ""

    def _parse_drama(self, raw):
        f = _pb_parse(raw)
        return {
            "vod_id": str(self._first(f, 3, 0)),
            "vod_name": self._text(self._first(f, 5)),
            "vod_pic": self._extract_pic(self._first(f, 2, b"")),
            "vod_remarks": self._text(self._first(f, 13)),
            "vod_year": str(self._first(f, 14, "")),
            "vod_area": self._text(self._first(f, 1)),
        }

    def _parse_drama_page(self, raw):
        page = _pb_parse(self._api_data(raw))
        return [self._parse_drama(v) for v in page.get(1, []) if isinstance(v, bytes)]

    def _parse_video(self, raw):
        f = _pb_parse(raw)
        return {
            "title": self._text(self._first(f, 2)), "path": self._text(self._first(f, 4)),
            "source": self._text(self._first(f, 9)), "source_cn": self._text(self._first(f, 10))
        }

    # ---- 线路排序（CONFIG.from: 优先段@屏蔽段） ----

    def _is_match_line(self, line_name, keyword):
        name = line_name.strip().lower()
        key = keyword.strip()
        try:
            if key.startswith('/') and key.endswith('/'):
                return bool(re.search(key[1:-1], name, re.IGNORECASE))
        except Exception:
            pass
        return key.lower() in name

    def _sort_and_filter_lines(self, lines):
        if not lines:
            return lines
        if self.line_block:
            lines = [l for l in lines if not any(self._is_match_line(l['name'], kw) for kw in self.line_block)]
        if self.line_order:
            sorted_lines = []
            remaining = lines[:]
            for keyword in self.line_order:
                matched, unmatched = [], []
                for line in remaining:
                    (matched if self._is_match_line(line['name'], keyword) else unmatched).append(line)
                sorted_lines.extend(matched)
                remaining = unmatched
            lines = sorted_lines + remaining
        return lines

    # ---- 分类与筛选（全分类 + 服务端下发的类型细分配置） ----

    def _load_classes(self, force=False):
        """拉取全部分类及 converUrl 内嵌筛选配置，实例级缓存 10 分钟。"""
        if not force and self._class_cache and time.time() - self._class_cache_ts < 600:
            return self._class_cache
        classes = []
        try:
            obj = self._get_json("/api/v3/drama/getCategory?orderBy=type_id")
            for item in obj.get("data") or []:
                name = str(item.get("name", ""))
                tid = str(item.get("id", "")).strip()
                if not tid or name == "公告":
                    continue
                cfg = {}
                raw = item.get("converUrl") or ""
                if raw:
                    try:
                        cfg = json.loads(raw)
                        if not isinstance(cfg, dict):
                            cfg = {}
                    except Exception:
                        cfg = {}
                classes.append({"type_id": tid, "type_name": name, "config": cfg})
        except Exception:
            classes = []
        if classes:
            self._class_cache = classes
            self._class_cache_ts = time.time()
        return classes

    # 排序值实测有效（extend_sort 下发：最新/最热/好评）
    _SORT_VALUES = [("最新", "最新"), ("最热", "最热"), ("好评", "好评")]

    @staticmethod
    def _split_values(text):
        return [v.strip() for v in str(text or "").split(",") if v.strip()]

    @classmethod
    def _movie_type_label(cls, tag):
        """电影分类显示名加"片"字（喜剧→喜剧片、科幻→科幻片）；
        本身以"片"结尾或以"电影"结尾的（微电影/网络电影）保持原样。"""
        tag = str(tag).strip()
        if not tag or tag.endswith("片") or tag.endswith("电影"):
            return tag
        return tag + "片"

    def _filter_groups(self, tid):
        tid = str(tid)
        cfg = {}
        for c in (self._class_cache or []):
            if str(c["type_id"]) == tid:
                cfg = c.get("config") or {}
                break
        groups = []
        type_values = self._split_values(cfg.get("class"))
        if type_values:
            label = self._movie_type_label if tid == "21" else (lambda t: t)
            groups.append({"key": "type", "name": "类型",
                           "value": [{"n": "全部", "v": ""}]
                                    + [{"n": label(t), "v": t} for t in type_values]})
        for key, name in (("area", "地区"), ("lang", "语言"), ("year", "年份")):
            values = self._split_values(cfg.get(key))
            if values:
                groups.append({"key": key, "name": name,
                               "value": [{"n": "全部", "v": ""}]
                                        + [{"n": v, "v": v} for v in values]})
        director_values = self._split_values(cfg.get("director"))
        if director_values:
            groups.append({"key": "director", "name": "导演",
                           "value": [{"n": "全部", "v": ""}]
                                    + [{"n": d, "v": d} for d in director_values]})
        groups.append({"key": "sort", "name": "排序",
                       "value": [{"n": n, "v": v} for v, n in self._SORT_VALUES]})
        return groups

    @staticmethod
    def _parse_extend(extend):
        """兼容 dict / JSON 字符串 / URL query 三种 TVBox 传参。"""
        if isinstance(extend, dict):
            return dict(extend)
        text = str(extend or "").strip()
        if not text:
            return {}
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        out = {}
        for part in text.split("&"):
            if "=" in part:
                k, _, v = part.partition("=")
                out[k.strip()] = urllib.parse.unquote(v.strip())
        return out

    @staticmethod
    def _pick(extend, *keys, default=""):
        for key in keys:
            value = str(extend.get(key) or "").strip()
            if value:
                return value
        return default

    # ---- TVBox 标准接口 ----

    def homeContent(self, filter=False):
        classes = []
        filters = {}
        try:
            for c in self._load_classes():
                tid = c["type_id"]
                classes.append({"type_id": tid, "type_name": c["type_name"]})
                filters[tid] = self._filter_groups(tid)
        except Exception:
            pass
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        try:
            obj = self._get_json("/api/ex/v3/security/tag/list")
            data = obj.get("data", "")
            if data and isinstance(data, str):
                stripped = data.strip()
                if stripped and stripped[0] not in ('[', '{'):
                    data = _aes_ecb_decrypt(base64.b64decode(data),
                                            self.data_key.encode("utf-8"))
                    data = _aes_ecb_decrypt(base64.b64decode(data.decode("utf-8", "ignore")),
                                            self.data_iv.encode("utf-8"))
                    data = data.decode("utf-8", "ignore")
            arr = json.loads(data) if isinstance(data, str) else data
            videos = []
            for block in arr or []:
                for section in block.get("sections") or []:
                    for vod in section.get("vodList") or []:
                        pic = (vod.get("coverImage") or {}).get("path", "")
                        videos.append({"vod_id": str(vod.get("id", "")),
                                       "vod_name": vod.get("name", ""),
                                       "vod_pic": pic,
                                       "vod_remarks": vod.get("remark", "")})
            return {"list": videos}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter=True, extend=""):
        pg = max(1, self._to_int(pg, 1))
        ext = self._parse_extend(extend)
        params = {
            "pagesize": "21",
            "typeId1": str(tid),
            "page": str(pg),
            "vodOrderBy": self._pick(ext, "sort", "排序", default="最新"),
            "vodArea": self._pick(ext, "area", "地区"),
            "vodLang": self._pick(ext, "lang", "语言"),
            "vodClass": self._pick(ext, "type", "class", "类型"),
            "vodYear": self._pick(ext, "year", "年份"),
            "vodDirector": self._pick(ext, "director", "导演"),
        }
        dramas, total = [], 0
        try:
            raw = self._post("/api/proto/v5/drama/category", self._secure_body(params))
            fields = _pb_parse(self._api_data(raw))
            total = self._to_int(self._text(self._first(fields, 16, b"")), 0)
            for item in fields.get(1, []):
                if not isinstance(item, bytes):
                    continue
                df = _pb_parse(item)
                dramas.append({
                    "vod_id": str(self._first(df, 3, 0)),
                    "vod_name": self._text(self._first(df, 5)),
                    "vod_pic": self._extract_pic(self._first(df, 2, b"")),
                    "vod_remarks": self._text(self._first(df, 13)),
                })
        except Exception:
            pass
        pagecount = int(math.ceil(total / 21.0)) if total > 0 else 9999
        result = {"list": dramas, "page": pg, "pagecount": pagecount,
                  "limit": 21, "total": total if total > 0 else 9999 * 21}
        groups = self._filter_groups(tid)
        if groups:
            result["filters"] = {str(tid): groups}
        return result

    def detailContent(self, ids):
        try:
            raw = self._post("/api/proto/v5/drama/getDetail",
                             self._secure_body({"id": str(ids[0])}))
            fields = _pb_parse(self._api_data(raw))
            cover_raw = self._first(fields, 2, b"")
            cover = self._parse_cover(cover_raw) if cover_raw else {}
            sources = {}
            for item in fields.get(29, []):
                video = self._parse_video(item)
                if not video.get("path"):
                    continue
                quality = video.get("source_cn", "") or video.get("source", "") or "未知"
                source = video.get("source", "") or ""
                line_name = "%s (%s)" % (quality, source) if source and quality != source else quality
                path = video["path"]
                if self.isVideoFormat(path):
                    token = path
                else:
                    token = base64.b64encode(json.dumps(
                        {"vodPlayFrom": source, "playUrl": path},
                        ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("utf-8")
                sources.setdefault(line_name, []).append(
                    (video["title"] or "播放") + "$" + token)

            lines = [{"name": name, "urls": urls} for name, urls in sources.items()]
            # 线路预检：首集解析不出 http 直链的线路剔除（如部分 zijian 影片）
            lines = [l for l in lines if self._line_playable(l["urls"][0].split("$", 1)[-1])]
            lines = self._sort_and_filter_lines(lines)
            play_from = "$$$".join([line["name"] for line in lines])
            play_url = "$$$".join(["#".join(line["urls"]) for line in lines])

            type_name = ""
            tid = str(self._first(fields, 15, b""))
            for c in (self._class_cache or []):
                if c["type_id"] == tid:
                    type_name = c["type_name"]
                    break

            content = self._text(self._first(fields, 6)) or self._text(self._first(fields, 7))
            info = _get_wechat_info()
            if info:
                content = (info + "\n" + content) if content else info

            vod = {
                "vod_id": str(ids[0]), "vod_name": self._text(self._first(fields, 9)),
                "vod_pic": self._clean_pic(cover.get("path") or cover.get("thumb") or ""),
                "vod_actor": self._text(self._first(fields, 25)),
                "vod_director": self._text(self._first(fields, 12)),
                "vod_area": self._text(self._first(fields, 1)),
                "vod_year": str(self._first(fields, 18, "")),
                "vod_remarks": self._text(self._first(fields, 26)),
                "vod_class": [type_name] if type_name else [],
                "vod_content": content,
                "vod_play_from": play_from, "vod_play_url": play_url
            }
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    def _line_playable(self, sample_id):
        """预检线路首集：直链或 videoUsableUrl 能解析出 http 直链才保留。

        解析接口异常时保留线路（避免瞬时抖动误杀），仅当服务端明确返回
        非 http 内容（如 zijian_HP-* token）时判定该线路不可播。
        """
        if self.isVideoFormat(sample_id):
            return True
        try:
            params = json.loads(base64.b64decode(sample_id).decode("utf-8"))
        except Exception:
            return False
        try:
            raw = self._post("/api/proto/v5/videoUsableUrl", self._secure_body(params))
            url = self._text(self._first(_pb_parse(self._api_data(raw)), 1))
        except Exception:
            return True
        return url.startswith("http")

    def searchContent(self, key, quick=False, pg="1"):
        pg = max(1, self._to_int(pg, 1))
        keyword = str(key or "").strip()
        if not keyword:
            return {"list": []}
        try:
            raw = self._post("/api/proto/v5/drama/search", self._secure_body(
                {"searchKeys": keyword, "page": str(pg), "pagesize": "21"}))
            return {"list": self._parse_drama_page(raw), "page": pg}
        except Exception:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            if self.isVideoFormat(id):
                return {"parse": 0, "url": id, "header": {}}
            params = json.loads(base64.b64decode(id).decode("utf-8"))
            raw = self._post("/api/proto/v5/videoUsableUrl", self._secure_body(params))
            fields = _pb_parse(self._api_data(raw))
            headers = {}
            for entry in fields.get(6, []):
                ef = _pb_parse(entry)
                k, v = self._text(self._first(ef, 1)), self._text(self._first(ef, 2))
                if k:
                    headers[k] = v
            url = self._text(self._first(fields, 1))
            if not url.startswith("http"):
                # 部分 zijian 影片返回 zijian_HP-* token，无直链可播
                return {"parse": 1, "url": id, "header": {}}
            return {"parse": 0, "url": url, "header": headers}
        except Exception:
            return {"parse": 1, "url": id, "header": {}}


# ============ 命令行自检 ============

if __name__ == "__main__":
    import sys

    def _dump(obj):
        print(json.dumps(obj, ensure_ascii=False, indent=1))

    cmd = sys.argv[1] if len(sys.argv) > 1 else "home"
    sp = Spider()
    sp.init("")
    try:
        if cmd == "home":
            _dump(sp.homeContent(False))
        elif cmd == "homevideos":
            _dump(sp.homeVideoContent())
        elif cmd == "category":
            _dump(sp.categoryContent(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "1",
                                     True, sys.argv[4] if len(sys.argv) > 4 else ""))
        elif cmd == "search":
            _dump(sp.searchContent(sys.argv[2], False, sys.argv[3] if len(sys.argv) > 3 else "1"))
        elif cmd == "detail":
            _dump(sp.detailContent([sys.argv[2]]))
        elif cmd == "play":
            _dump(sp.playerContent("", sys.argv[2]))
        elif cmd == "wechat":
            print(_get_wechat_info())
        else:
            print("用法: python [4K]河豚.py home|homevideos|category 分类 页 筛选JSON|search 关键词 页|detail id|play id|wechat")
    except Exception as error:
        sys.stderr.write("%s: %s\n" % (type(error).__name__, error))
        sys.exit(1)
