/*
title: '豆瓣发现', author: '源力'
说明：基于豆瓣 Rexxar API 的发现页爬虫，替代失效的 csp_Douban
旧 API (movie.douban.com/j/search_subjects) 已废弃返回空，改用 m.douban.com/rexxar/api/v2/
*/

const HOST = 'https://m.douban.com';
const MOBILE_UA = 'Mozilla/5.0 (Linux; Android 16; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36';
const Headers = { 'User-Agent': MOBILE_UA, 'Referer': HOST };

// 分类定义: type_id -> { name, api_type (movie/tv/book), collection (for rank lists) }
const CATEGORIES = [
    { type_name: '热门电视剧', type_id: 'tv_hot', api_type: 'tv', mode: 'recommend' },
    { type_name: '热门图书', type_id: 'book_hot', api_type: 'book', mode: 'recommend' },
    { type_name: '电影榜单', type_id: 'rank_list_movie', mode: 'collection' },
    { type_name: '电视综艺榜单', type_id: 'rank_list_tv', mode: 'collection' },
    { type_name: '图书榜单', type_id: 'rank_list_book', mode: 'collection' },
];

// 榜单集合 ID 映射
const COLLECTIONS = {
    rank_list_movie: [
        { n: '豆瓣电影Top250', v: 'movie_top250' },
        { n: '一周口碑电影榜', v: 'movie_weekly_best' },
        { n: '实时热门电影', v: 'movie_real_time_hotest' },
    ],
    rank_list_tv: [
        { n: '实时热门电视', v: 'tv_real_time_hotest' },
        { n: '华语口碑剧集榜', v: 'tv_chinese_best_weekly' },
        { n: '全球口碑剧集榜', v: 'tv_global_best_weekly' },
        { n: '国内口碑综艺榜', v: 'show_chinese_best_weekly' },
        { n: '国外口碑综艺榜', v: 'show_global_best_weekly' },
    ],
    rank_list_book: [
        { n: '豆瓣图书Top250', v: 'book_top250' },
        { n: '一周热门图书榜', v: 'book_hot' },
    ],
};

const PAGE_SIZE = 20;

async function init(cfg) {
    try {
        // 读取 ext 配置中的 filters 定义
        if (cfg && cfg.ext) {
            // ext 可以是路径字符串或对象
            if (typeof cfg.ext === 'string') {
                // 在 TVBox 中 ext 路径会自动加载为对象
            }
        }
    } catch (e) {
        console.error('初始化失败：', e.message);
    }
}

async function home(filter) {
    try {
        let classes = CATEGORIES.map(c => ({ type_id: c.type_id, type_name: c.type_name }));
        let filters = {};

        // 电视剧: 排序 + 年代 + 平台
        filters['tv_hot'] = [
            {
                key: 'sort', name: '排序', value: [
                    { n: '近期热度', v: 'U' },
                    { n: '首播时间', v: 'R' },
                    { n: '高分优先', v: 'S' },
                    { n: '综合排序', v: 'T' },
                ]
            },
            {
                key: 'year', name: '年代', value: [
                    { n: '全部', v: '' },
                    { n: '2026', v: '2026' },
                    { n: '2025', v: '2025' },
                    { n: '2024', v: '2024' },
                    { n: '2023', v: '2023' },
                    { n: '2022', v: '2022' },
                    { n: '2021', v: '2021' },
                    { n: '2020', v: '2020' },
                    { n: '2019', v: '2019' },
                    { n: '2010年代', v: '2010年代' },
                    { n: '2000年代', v: '2000年代' },
                    { n: '90年代', v: '90年代' },
                    { n: '80年代', v: '80年代' },
                    { n: '70年代', v: '70年代' },
                    { n: '60年代', v: '60年代' },
                    { n: '更早', v: '更早' },
                ]
            },
            {
                key: 'platform', name: '平台', value: [
                    { n: '全部', v: '' },
                    { n: '腾讯视频', v: '腾讯视频' },
                    { n: '爱奇艺', v: '爱奇艺' },
                    { n: '优酷', v: '优酷' },
                    { n: '湖南卫视', v: '湖南卫视' },
                    { n: 'Netflix', v: 'Netflix' },
                    { n: 'HBO', v: 'HBO' },
                    { n: 'BBC', v: 'BBC' },
                    { n: 'NHK', v: 'NHK' },
                    { n: 'CBS', v: 'CBS' },
                    { n: 'NBC', v: 'NBC' },
                    { n: 'tvN', v: 'tvN' },
                ]
            },
        ];

        // 图书: 排序 + 形式 + 体裁
        filters['book_hot'] = [
            {
                key: 'sort', name: '排序', value: [
                    { n: '近期热度', v: 'U' },
                    { n: '出版时间', v: 'R' },
                    { n: '高分优先', v: 'S' },
                    { n: '综合排序', v: 'T' },
                ]
            },
            {
                key: 'form', name: '形式', value: [
                    { n: '全部', v: '' },
                    { n: '图书', v: '图书' },
                    { n: '书单', v: '书单' },
                ]
            },
            {
                key: 'genre', name: '体裁', value: [
                    { n: '全部', v: '' },
                    { n: '小说', v: '小说' },
                    { n: '传记', v: '传记' },
                    { n: '诗歌', v: '诗歌' },
                    { n: '戏剧', v: '戏剧' },
                    { n: '随笔', v: '随笔' },
                    { n: '杂文', v: '杂文' },
                    { n: '散文', v: '散文' },
                    { n: '访谈', v: '访谈' },
                    { n: '绘本', v: '绘本' },
                    { n: '漫画', v: '漫画' },
                    { n: '童话', v: '童话' },
                    { n: '回忆录', v: '回忆录' },
                ]
            },
        ];

        // 电影榜单
        filters['rank_list_movie'] = [
            { key: '榜单', name: '榜单', value: COLLECTIONS.rank_list_movie },
        ];

        // 电视综艺榜单
        filters['rank_list_tv'] = [
            { key: '榜单', name: '榜单', value: COLLECTIONS.rank_list_tv },
        ];

        // 图书榜单
        filters['rank_list_book'] = [
            { key: '榜单', name: '榜单', value: COLLECTIONS.rank_list_book },
        ];

        return JSON.stringify({ class: classes, filters: filters });
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({ class: [], filters: {} });
    }
}

async function homeVod() {
    try {
        let VODS = await fetchRecommend('movie', 1, 'U', []);
        return JSON.stringify({ list: VODS });
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, extend) {
    try {
        pg = parseInt(pg, 10);
        pg = pg > 0 ? pg : 1;
        let start = (pg - 1) * PAGE_SIZE;

        let cat = CATEGORIES.find(c => c.type_id === tid);
        if (!cat) {
            return JSON.stringify({ list: [], page: pg, pagecount: 0, limit: PAGE_SIZE, total: 0 });
        }

        let VODS = [];
        let pagecount = 1;

        if (cat.mode === 'recommend') {
            // 推荐类分类
            let sort = (extend && extend.sort) || 'U';
            let tags = [];

            // 年代筛选
            if (extend && extend.year) tags.push(extend.year);
            // 平台筛选 (仅电视剧)
            if (extend && extend.platform) tags.push(extend.platform);
            // 形式筛选 (仅图书)
            if (extend && extend.form) tags.push(extend.form);
            // 体裁筛选 (仅图书)
            if (extend && extend.genre) tags.push(extend.genre);

            VODS = await fetchRecommend(cat.api_type, pg, sort, tags);
            pagecount = 50;
        } else if (cat.mode === 'collection') {
            // 榜单类分类
            let collectionId = (extend && extend['榜单']) || COLLECTIONS[tid][0].v;
            VODS = await fetchCollection(collectionId, pg);
            // Top250 等有较多数据, 其他榜单通常 10 条
            pagecount = collectionId.includes('top250') || collectionId.includes('book_hot') ? 15 : 1;
        }

        return JSON.stringify({
            list: VODS,
            page: pg,
            pagecount: pagecount,
            limit: PAGE_SIZE,
            total: PAGE_SIZE * pagecount,
        });
    } catch (e) {
        console.error('分类页获取失败：', e.message);
        return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: PAGE_SIZE, total: 0 });
    }
}

// 获取推荐列表
async function fetchRecommend(apiType, page, sort, tags) {
    let VODS = [];
    try {
        let start = (page - 1) * PAGE_SIZE;
        let tagStr = tags.filter(t => t).join(',');
        let url = `${HOST}/rexxar/api/v2/${apiType}/recommend?start=${start}&count=${PAGE_SIZE}&sort=${sort}`;
        if (tagStr) url += '&tags=' + encodeURIComponent(tagStr);

        let res = await request(url, { headers: Headers, timeout: 10000 });
        let data = JSON.parse(res);
        let items = data.items || [];

        for (let item of items) {
            // 只取 subject 类型, 跳过 doulist/playlist 等推荐片单
            if (item.card && item.card !== 'subject' && item.type !== 'subject') continue;
            if (!item.id || !item.title) continue;

            let pic = item.cover_url || item.pic || '';
            if (pic && pic.startsWith('//')) pic = 'https:' + pic;

            let remark = '';
            let rating = item.rating;
            if (rating && rating.value) {
                remark = rating.value + '分';
            }
            let subtitle = item.card_subtitle || '';
            if (subtitle && !remark) {
                remark = subtitle.substring(0, 20);
            }

            VODS.push({
                vod_id: String(item.id),
                vod_name: item.title,
                vod_pic: pic,
                vod_remarks: remark,
            });
        }
    } catch (e) {
        console.error(`推荐列表获取失败(${apiType})：`, e.message);
    }
    return VODS;
}

// 获取榜单列表
async function fetchCollection(collectionId, page) {
    let VODS = [];
    try {
        let start = (page - 1) * PAGE_SIZE;
        let url = `${HOST}/rexxar/api/v2/subject_collection/${collectionId}/items?start=${start}&count=${PAGE_SIZE}`;

        let res = await request(url, { headers: Headers, timeout: 10000 });
        let data = JSON.parse(res);
        let items = data.subject_collection_items || data.items || [];

        for (let item of items) {
            if (!item.id || !item.title) continue;

            let pic = item.cover_url || item.pic || '';
            if (pic && pic.startsWith('//')) pic = 'https:' + pic;

            let remark = '';
            if (item.rank) remark = 'No.' + item.rank;
            let rating = item.rating;
            if (rating && rating.value) {
                remark = remark ? remark + ' ' + rating.value + '分' : rating.value + '分';
            }

            VODS.push({
                vod_id: String(item.id),
                vod_name: item.title,
                vod_pic: pic,
                vod_remarks: remark,
            });
        }
    } catch (e) {
        console.error(`榜单获取失败(${collectionId})：`, e.message);
    }
    return VODS;
}

async function detail(ids) {
    try {
        let id = ids;
        if (ids && ids.indexOf('_') > -1) {
            id = ids.split('_').pop();
        }

        let url = `${HOST}/rexxar/api/v2/subject/${id}`;
        let res = await request(url, { headers: Headers, timeout: 10000 });
        let data = JSON.parse(res);

        let title = data.title || '';
        let pic = data.cover_url || data.pic || '';
        if (pic && pic.startsWith('//')) pic = 'https:' + pic;

        let director = '';
        if (data.directors && Array.isArray(data.directors)) {
            director = data.directors.map(d => d.name || d).join('/');
        }

        let actor = '';
        if (data.actors && Array.isArray(data.actors)) {
            actor = data.actors.map(a => a.name || a).join('/');
        }

        let genres = '';
        if (data.genres && Array.isArray(data.genres)) {
            genres = data.genres.join('/');
        }

        let countries = '';
        if (data.countries && Array.isArray(data.countries)) {
            countries = data.countries.join('/');
        }

        let year = data.year || '';
        let description = data.intro || data.card_subtitle || '';
        let subtitle = data.card_subtitle || '';

        let remark = '';
        let rating = data.rating;
        if (rating && rating.value) {
            remark = rating.value + '分';
        }

        // 豆瓣是发现站, 用标题作为播放搜索关键词
        // play_from 用 "搜索播放", play_url 用电影标题让 TVBox 在其他站点搜索
        let play_from = '搜索播放';
        let play_url = title + '$search://' + encodeURIComponent(title);

        let VOD = {
            vod_id: String(id),
            vod_name: title,
            vod_pic: pic,
            type_name: genres,
            vod_remarks: remark,
            vod_year: String(year),
            vod_area: countries,
            vod_director: director,
            vod_actor: actor,
            vod_content: description,
            vod_play_from: play_from,
            vod_play_url: play_url,
        };

        return JSON.stringify({ list: [VOD] });
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, ids, flags) {
    try {
        // 豆瓣是发现站, 返回搜索协议让 TVBox 在其他站点搜索
        let url = ids;
        if (url.startsWith('search://')) {
            return JSON.stringify({ jx: 0, parse: 0, url: url, header: Headers });
        }
        // 直接播放豆瓣页面 URL (webview)
        return JSON.stringify({ jx: 0, parse: 0, url: url, header: Headers });
    } catch (e) {
        console.error('播放失败：', e.message);
        return JSON.stringify({ jx: 0, parse: 0, url: '', header: {} });
    }
}

async function search(wd, quick, pg) {
    try {
        pg = parseInt(pg, 10);
        pg = pg > 0 ? pg : 1;
        let start = (pg - 1) * PAGE_SIZE;
        let url = `${HOST}/rexxar/api/v2/search?q=${encodeURIComponent(wd)}&start=${start}&count=${PAGE_SIZE}`;
        let res = await request(url, { headers: Headers, timeout: 10000 });
        let data = JSON.parse(res);
        let items = data.items || [];
        let VODS = [];

        for (let item of items) {
            let target = item.target || item;
            let title = target.title || '';
            if (!title) continue;
            let id = target.id || '';
            if (!id) continue;

            let pic = target.cover_url || target.cover || '';
            if (pic && pic.startsWith('//')) pic = 'https:' + pic;

            let remark = '';
            let rating = target.rating;
            if (rating && rating.value) {
                remark = rating.value + '分';
            }

            VODS.push({
                vod_id: String(id),
                vod_name: title,
                vod_pic: pic,
                vod_remarks: remark,
            });
        }

        let pagecount = data.total ? Math.ceil(data.total / PAGE_SIZE) : 1;
        return JSON.stringify({ list: VODS, page: pg, pagecount: pagecount, limit: PAGE_SIZE, total: data.total || VODS.length });
    } catch (e) {
        console.error('搜索失败：', e.message);
        return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: PAGE_SIZE, total: 0 });
    }
}

