/*
说明：可以不写ext，也可以写ext，ext支持的参数和格式参数如下
"ext": {
    "host": "xxxx", //站点网址
    "timeout": 6000,  //请求超时，单位毫秒
    "catesSet": "电视剧&电影&综艺",  //指定分类和顺序
    "tabsSet": "土星&下载线1"  //指定线路和顺序
}
微信公众号【源力软件汇】 QQ群【1054592152】更多优质资源尽在源力！
*/

const MOBILE_UA = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36';
const DefHeader = {'User-Agent': MOBILE_UA};
const PLAYLIST_EXTRA = "\n\n微信公众号：源力软件汇\nQQ群：1054592152\n更多优质资源尽在源力！";
var HOST;
var KParams = {
    headers: {'User-Agent': MOBILE_UA},
    timeout: 5000
};

async function init(cfg) {
    try {
        HOST = (cfg.ext?.host?.trim() || 'https://www.xcyycn.com').replace(/\/$/, '');
        KParams.headers['Referer'] = HOST;
        let parseTimeout = parseInt(cfg.ext?.timeout?.trim(), 10);
        if (parseTimeout > 0) {KParams.timeout = parseTimeout;}
        KParams.catesSet = cfg.ext?.catesSet?.trim() || '';
        KParams.tabsSet = cfg.ext?.tabsSet?.trim() || '';
        KParams.resHtml = await request(HOST);
    } catch (e) {
        console.error('初始化参数失败：', e.message);
    }
}

async function home(filter) {
    try {
        let resHtml = KParams.resHtml;
        if (!resHtml) {throw new Error('源码为空');}
        let navBlock = cutStr(resHtml, 'head-nav', '</ul>', '', false);
        let classes = [];
        let seen = {};
        let navRe = /<a[^>]*href="\/v\/(\d+)\.html"(?:[^>]*)>([\s\S]*?)<\/a>/g, nm;
        while ((nm = navRe.exec(navBlock))) {
            let cId = nm[1];
            if (seen[cId]) {continue;}
            seen[cId] = true;
            let cName = nm[2].replace(/<[^>]*>/g, '').replace(/&nbsp;/g, '').trim();
            if (!cName) {continue;}
            classes.push({type_name: cName, type_id: cId});
        }
        if (KParams.catesSet) {classes = ctSet(classes, KParams.catesSet);}
        return JSON.stringify({class: classes, filters: {}});
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({class: [], filters: {}});
    }
}

async function homeVod() {
    try {
        let resHtml = KParams.resHtml;
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS});
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({list: []});
    }
}

async function category(tid, pg, filter, extend) {
    try {
        pg = parseInt(pg, 10), pg = pg > 0 ? pg : 1;
        let cateUrl = pg > 1 ? `${HOST}/v/${tid}-${pg}.html` : `${HOST}/v/${tid}.html`;
        let resHtml = await request(cateUrl);
        let VODS = getVodList(resHtml);
        let limit = VODS.length;
        return JSON.stringify({list: VODS, page: pg, pagecount: 1, limit: limit, total: limit});
    } catch (e) {
        console.error('类别页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

async function search(wd, quick, pg) {
    try {
        pg = parseInt(pg, 10), pg = pg > 0 ? pg : 1;
        let searchUrl = `${HOST}/s.html?wd=${encodeURIComponent(wd)}`;
        let resHtml = await request(searchUrl);
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS, page: pg, pagecount: 1, limit: VODS.length, total: VODS.length});
    } catch (e) {
        console.error('搜索页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

function getVodList(khtml) {
    try {
        if (!khtml) {throw new Error('源码为空');}
        let kvods = [], seen = {};
        const re = /public-list-exp" href="(\/[^"]+\.html)"/g;
        let m, idxs = [];
        while ((m = re.exec(khtml))) {idxs.push({href: m[1], idx: m.index});}
        for (let a of idxs) {
            if (seen[a.href]) {continue;}
            seen[a.href] = true;
            let block = khtml.slice(a.idx, a.idx + 3000);
            let kpic = cutStr(block, 'data-src="', '"', '图片');
            let kremarks = (block.match(/public-list-prb[^>]*>([^<]*)</) || [])[1] || '';
            let kname = cutStr(block, '" title="', '"', '');
            if (!kname) {
                let t = (block.match(/thumb-txt[^>]*>([^<]*)</) || [])[1] || '';
                kname = t.trim();
            }
            if (!/^http/.test(kpic)) {kpic = `${HOST}${kpic}`;}
            kvods.push({
                vod_name: kname,
                vod_pic: kpic,
                vod_remarks: kremarks.trim(),
                vod_id: `${a.href}@${kname}@${kpic}@${kremarks.trim()}`
            });
        }
        return kvods;
    } catch (e) {
        console.error(`生成视频列表失败：`, e.message);
        return [];
    }
}

async function detail(ids) {
    try {
        let [id, kname, kpic, kremarks] = ids.split('@');
        let detailUrl = !/^http/.test(id) ? `${HOST}${id}` : id;
        let resHtml = await request(detailUrl);
        if (!resHtml) {throw new Error('源码为空');}
        if (!kname || kname === '名称' || kname === 'cutFaile') {kname = cutStr(resHtml, 'slide-info-title hide">', '<', '名称');}
        if (!kpic || kpic === '图片') {kpic = cutStr(resHtml, 'detail-pic">£data-src="', '"', '图片');}
        if (!/^http/.test(kpic)) {kpic = `${HOST}${kpic}`;}
        let year = '', area = '', vod_lang = '';
        let depMatch = resHtml.match(/class="deployment[^"]*"[^>]*>(.*?)<\/a>/s);
        if (depMatch) {
            let spans = cutStr(depMatch[1], '<span', '<', '', false, 0, true).map(t => cutStr(t, '>', '<', '').trim());
            spans = spans.filter(s => s && s !== '·' && s !== '详情' && s !== '放映');
            year = /^\d{4}$/.test(spans[0] || '') ? spans[0] : '';
            area = spans[1] || '';
            vod_lang = spans[4] || '';
        }
        if (!year) {
            let yearMatch = resHtml.match(/<span>(\d{4})<\/span><span class="division">·<\/span><span>([^<]+)<\/span>/);
            if (yearMatch) {year = yearMatch[1]; if (!area) {area = yearMatch[2];}}
        }
        let director = cutStr(resHtml, '<strong class="cor6 r6">导演 :</strong>', '</div>', '', false);
        director = cutStr(director, '>', '<', '', false, 0, true).map(t => t.trim().replace(/&nbsp;/g, '')).filter(Boolean).join(',');
        let actor = cutStr(resHtml, '<strong class="cor6 r6">演员 :</strong>', '</div>', '', false);
        actor = cutStr(actor, '>', '<', '', false, 0, true).map(t => t.trim().replace(/&nbsp;/g, '')).filter(Boolean).join(',');
        let type_name = cutStr(resHtml, '<strong class="cor6 r6">类型 :</strong>', '</div>', '', false);
        type_name = cutStr(type_name, '>', '<', '', false, 0, true).map(t => t.trim().replace(/&nbsp;/g, '')).filter(Boolean).join(',');
        let content = cutStr(resHtml, 'class="check text selected cor3">', '</div>', kname);
        content = (content || kname).replace(/^\s*&nbsp;\s*/, '').trim();
        let vod_remarks = kremarks || cutStr(resHtml, 'slide-info-remarks', '<', '状态');

        let [ktabs, kurls] = [[], []];
        let lineNames = [];
        let nameRe = /class="swiper-slide">[\s\S]*?<\/i>\s*(?:&nbsp;)?([^<]+)<span/g, nm;
        while ((nm = nameRe.exec(resHtml))) {let t = nm[1].trim(); if (t) {lineNames.push(t);}}
        let epArr = cutStr(resHtml, 'class="anthology-list-play', '</ul>', '', false, 0, true);
        for (let i = 0; i < epArr.length; i++) {
            if (!epArr[i] || epArr[i] === 'cutFaile') {continue;}
            let ktab = lineNames[i] || `线路${i+1}`;
            let eps = cutStr(epArr[i], '<a', '/a>', '', false, 0, true).map(it => {
                let epn = cutStr(it, '>', '<', '集');
                let eph = cutStr(it, 'href="', '"', '');
                return `${epn}$${eph}`;
            }).filter(t => t && t.indexOf('$') > -1 && t.split('$')[1]);
            if (eps.length) {ktabs.push(ktab); kurls.push(eps.join('#'));}
        }
        if (KParams.tabsSet && ktabs.length) {
            let ktus = ktabs.map((it, idx) => { return {type_name: it, type_value: kurls[idx]} });
            ktus = ctSet(ktus, KParams.tabsSet);
            ktabs = ktus.map(it => it.type_name);
            kurls = ktus.map(it => it.type_value);
        }
        let contentFinal = content ? `${content}${PLAYLIST_EXTRA}` : `${kname}${PLAYLIST_EXTRA}`;
        let VOD = {
            vod_id: detailUrl,
            vod_name: kname,
            vod_pic: kpic,
            vod_remarks: vod_remarks,
            type_name: type_name,
            vod_year: year,
            vod_area: area,
            vod_lang: vod_lang,
            vod_director: director,
            vod_actor: actor,
            vod_content: contentFinal,
            vod_play_from: ktabs.join('$$$'),
            vod_play_url: kurls.join('$$$')
        };
        return JSON.stringify({list: [VOD]});
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({list: []});
    }
}

async function play(flag, ids, flags) {
    try {
        let kp = 0, kurl = '', kheader = DefHeader;
        let playUrl = !/^http/.test(ids) ? `${HOST}${ids}` : ids;
        let resHtml = await request(playUrl);
        kurl = extractPlayerUrl(resHtml);
        if (!/^http/.test(kurl)) {
            kurl = playUrl;
            kp = 1;
        }
        return JSON.stringify({jx: 0, parse: kp, url: kurl, header: kheader});
    } catch (e) {
        console.error('播放失败：', e.message);
        return JSON.stringify({jx: 0, parse: 0, url: '', header: {}});
    }
}

function extractPlayerUrl(resHtml) {
    try {
        if (typeof resHtml !== 'string') {return '';}
        let startIdx = resHtml.indexOf('var player_aaaa');
        let jsonStr = '';
        if (startIdx > -1) {
            let braceIdx = resHtml.indexOf('{', startIdx);
            if (braceIdx > -1) {
                let depth = 0, endIdx = -1;
                for (let p = braceIdx; p < resHtml.length; p++) {
                    let ch = resHtml[p];
                    if (ch === '{') {depth++;}
                    else if (ch === '}') {depth--; if (depth === 0) {endIdx = p; break;}}
                }
                if (endIdx > braceIdx) {jsonStr = resHtml.slice(braceIdx, endIdx + 1);}
            }
        }
        let codeObj = jsonStr ? safeParseJSON(jsonStr.replace(/\\\//g, '/').replace(/&amp;/g, '&')) : null;
        let kurl = codeObj?.url || '';
        if (typeof kurl === 'string') {kurl = kurl.replace(/\\\//g, '/').replace(/&amp;/g, '&');}
        if (!/^http/.test(kurl)) {
            let urlMatch = resHtml.match(/"(?:url|downurl|vurl)"\s*:\s*"([^"]+\.(?:m3u8|mp4)[^"]*)"/);
            if (urlMatch) {kurl = urlMatch[1].replace(/\\\//g, '/').replace(/&amp;/g, '&');}
        }
        return kurl;
    } catch (e) {
        console.error('解析播放地址失败：', e.message);
        return '';
    }
}

function ctSet(kArr, setStr) {
    try {
        if (!Array.isArray(kArr) || kArr.length === 0 || typeof setStr !== 'string' || !setStr) { throw new Error('第一参数需为非空数组，第二参数需为非空字符串'); }
        const set_arr = [...kArr];
        const arrNames = setStr.split('&');
        const filtered_arr = arrNames.map(item => set_arr.find(it => it.type_name === item)).filter(Boolean);
        return filtered_arr.length? filtered_arr : [set_arr[0]];
    } catch (e) {
        console.error('ctSet 执行异常：', e.message);
        return kArr;
    }
}

function safeParseJSON(jStr){
    try {return JSON.parse(jStr);} catch(e) {return null;}
}

function cutStr(str, prefix = '', suffix = '', defVal = '', clean = true, i = 0, all = false) {
    try {
        if (typeof str !== 'string') {throw new Error('被截取对象必须为字符串');}
        const cleanStr = cs => String(cs).replace(/<[^>]*?>/g, ' ').replace(/(&nbsp;|[\u0020\u00A0\u3000\s])+/g, ' ').trim().replace(/\s+/g, ' ');
        const esc = s => String(s).replace(/[.*+?${}()|[\]\\/^]/g, '\\$&');
        let pre = esc(prefix).replace(/£/g, '[^]*?'), end = esc(suffix);
        const regex = new RegExp(`${pre || '^'}([^]*?)${end || '$'}`, 'g');
        const matchIter = str.matchAll(regex);
        if (all) {
            let matchArr = [...matchIter];
            if (!matchArr.length) {return [defVal];}
            return matchArr.map(ela => ela[1] !== undefined ? (clean ? cleanStr(ela[1]) : ela[1]) : defVal);
        }
        const idx = parseInt(i, 10);
        if (isNaN(idx)) {throw new Error('序号必须为整数');}
        let tgResult, matchIdx = 0;
        if (idx >= 0) {
            for (let elt of matchIter) {
                if (matchIdx++ === idx) {
                    tgResult = elt[1];
                    break;
                }
            }
        } else {
            let absI = Math.abs(idx), ringBuf = new Array(absI), ringPtr = 0, ringCnt = 0;
            for (let elt of matchIter) {
                ringBuf[ringPtr] = elt[1];
                ringPtr = (ringPtr + 1) % absI;
                ringCnt = Math.min(ringCnt + 1, absI);
                matchIdx++;
            }
            tgResult = (matchIdx >= absI && ringCnt > 0) ? ringBuf[ringPtr % ringCnt] : undefined;
        }
        return tgResult !== undefined ? (clean ? (cleanStr(tgResult) || defVal) : tgResult) : defVal;
    } catch (e) {
        console.error(`字符串截取错误：`, e.message);
        return all ? ['cutErr'] : 'cutErr';
    }
}

async function request(reqUrl, options = {}) {
    try {
        if (typeof reqUrl !== 'string' || !reqUrl.trim()) { throw new Error('reqUrl需为字符串且非空'); }
        if (typeof options !== 'object' || Array.isArray(options) || options === null) { throw new Error('options类型需为非null对象'); }
        options.method = options.method?.toUpperCase() || 'GET';
        if (['GET', 'HEAD'].includes(options.method)) {
            delete options.body;
            delete options.data;
            delete options.postType;
        }
        let {headers, timeout, ...restOpts} = options;
        const optObj = {
            headers: (typeof headers === 'object' && !Array.isArray(headers) && headers) ? headers : KParams.headers,
            timeout: parseInt(timeout, 10) > 0 ? parseInt(timeout, 10) : KParams.timeout,
            ...restOpts
        };
        const res = await req(reqUrl, optObj);
        if (options.withHeaders) {
            const resHeaders = typeof res.headers === 'object' && !Array.isArray(res.headers) && res.headers ? res.headers : {};
            const resWithHeaders = { ...resHeaders, body: res?.content ?? '' };
            return JSON.stringify(resWithHeaders);
        }
        return res?.content ?? '';
    } catch (e) {
        console.error(`${reqUrl}→请求失败：`, e.message);
        return options?.withHeaders ? JSON.stringify({ body: '' }) : '';
    }
}

export function __jsEvalReturn() {
    return {
        init,
        home,
        homeVod,
        category,
        search,
        detail,
        play,
        proxy: null
    };
}