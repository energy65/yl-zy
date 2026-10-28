var rule = {
    title: '腾云驾雾[官]',
    host: 'https://v.%71%71.com',
    // 旧 pagesheet 接口已 404：精选页走 getPage，分类页(含类型细化筛选)走 getMVLPage
    homeUrl: '/channel/choice',
    detailUrl: 'https://node.video.%71%71.com/x/api/float_vinfo2?cid=fyid',
    searchUrl: '/x/search/?q=**&stag=fypage',
    searchable: 2,
    // 开启类型/排序/地区/年代等筛选
    filterable: 1,
    multi: 1,
    // 分类 URL 仅用于框架生成 MY_URL,实际请求由 一级 JS 完成(fyclass/fypage 占位保留)
    url: '/channel/fyclass?page=fypage',
    // 筛选值由框架通过 MY_FL 传入(一级 JS 读取),此处仅作占位不参与实际请求
    filter_url: 'itype={{fl.itype or -1}}&sort={{fl.sort or 75}}&iarea={{fl.iarea or -1}}&iyear={{fl.iyear or -1}}',
    headers: {
        'User-Agent': 'PC_UA'
    },
    timeout: 5000,
    cate_exclude: '会员|游戏|全部',
    class_name: '精选&电影&电视剧&综艺&动漫&少儿&纪录片',
    class_url: 'choice&movie&tv&variety&cartoon&child&doco',
    limit: 20,
    // 分类标识 -> 腾讯频道 page_id
    _qqChannelMap: {
        choice: '100101',
        movie: '100173',
        tv: '100113',
        variety: '100109',
        cartoon: '100119',
        child: '100150',
        doco: '100105'
    },

    // ========== 类型细化筛选 ==========
    // v 为纯数字(含 -1) = 腾讯官方 itype,服务端直接筛选(翻页深、结果准确)
    // v 以 g 开头(g奇幻/g武侠/g历史/g文艺/g谍战) = 腾讯无对应 itype 的类型,
    //   改用条目主类型(main_genre)客户端筛选,见 _qqCollectGenre
    filter: {
        // 电影:科幻片、奇幻片、战争片、犯罪片、武侠片、历史片、文艺片 等
        movie: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '科幻片', v: '12'},
                    {n: '奇幻片', v: 'g奇幻'},
                    {n: '战争片', v: '8'},
                    {n: '犯罪片', v: '6'},
                    {n: '武侠片', v: 'g武侠'},
                    {n: '历史片', v: 'g历史'},
                    {n: '文艺片', v: 'g文艺'},
                    {n: '剧情片', v: 'g剧情'},
                    {n: '动作片', v: '4'},
                    {n: '喜剧片', v: '3'},
                    {n: '爱情片', v: '5'},
                    {n: '悬疑片', v: '10'},
                    {n: '冒险片', v: '7'},
                    {n: '恐怖片', v: '11'},
                    {n: '动画片', v: '15'},
                    {n: '灾难片', v: '25'},
                    {n: '青春片', v: '26'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最新', v: '83'},
                    {n: '高分好评', v: '81'}
                ]
            },
            {
                key: 'iarea',
                name: '地区',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '内地', v: '100024'},
                    {n: '中国香港', v: '100025'},
                    {n: '中国台湾', v: '100026'},
                    {n: '美国', v: '100029'},
                    {n: '日本', v: '100027'},
                    {n: '韩国', v: '100028'},
                    {n: '泰国', v: '100031'},
                    {n: '印度', v: '100030'},
                    {n: '英国', v: '15'},
                    {n: '法国', v: '16'},
                    {n: '德国', v: '17'},
                    {n: '加拿大', v: '18'},
                    {n: '西班牙', v: '19'},
                    {n: '意大利', v: '20'},
                    {n: '澳大利亚', v: '21'},
                    {n: '其他', v: '100033'}
                ]
            },
            {
                key: 'iyear',
                name: '年份',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '即将上线', v: '999'},
                    {n: '2026', v: '2026'},
                    {n: '2025', v: '2025'},
                    {n: '2024', v: '2024'},
                    {n: '2023', v: '2023'},
                    {n: '2022', v: '2022'},
                    {n: '2021', v: '2021'},
                    {n: '2020', v: '2020'},
                    {n: '2019', v: '20'},
                    {n: '2018', v: '2018'},
                    {n: '2017', v: '1'},
                    {n: '2016', v: '2'},
                    {n: '2015', v: '3'},
                    {n: '2014', v: '4'},
                    {n: '2013-2011', v: '5'},
                    {n: '2010-2006', v: '6'},
                    {n: '2005-2000', v: '7'},
                    {n: '90年代', v: '8'},
                    {n: '80年代', v: '9'},
                    {n: '其他', v: '10'}
                ]
            },
            {
                key: 'ipay',
                name: '资费',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '免费', v: '1'},
                    {n: '会员', v: '8'},
                    {n: '付费', v: '4'},
                    {n: '限免', v: '3300'}
                ]
            }
        ],
        // 电视剧:古装、都市、历史、谍战、家庭剧 等
        tv: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '古装', v: '6'},
                    {n: '都市', v: '2'},
                    {n: '历史', v: 'g历史'},
                    {n: '谍战', v: 'g谍战'},
                    {n: '家庭剧', v: '12'},
                    {n: '爱情', v: '1'},
                    {n: '武侠', v: '5'},
                    {n: '奇幻', v: '4'},
                    {n: '悬疑', v: '14'},
                    {n: '刑侦', v: '18'},
                    {n: '权谋', v: '15'},
                    {n: '传奇', v: '10'},
                    {n: '民国', v: '20'},
                    {n: '军旅', v: '11'},
                    {n: '革命', v: '16'},
                    {n: '现实', v: '17'},
                    {n: '青春', v: '3'},
                    {n: '科幻', v: '7'},
                    {n: '喜剧', v: '13'},
                    {n: '竞技', v: '9'},
                    {n: '猎奇', v: '8'},
                    {n: '逆袭', v: '19'},
                    {n: 'IP改编', v: '21'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最新上架', v: '79'},
                    {n: '高分好评', v: '85'}
                ]
            },
            {
                key: 'iarea',
                name: '地区',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '内地', v: '0'},
                    {n: '中国香港', v: '14'},
                    {n: '中国台湾', v: '4'},
                    {n: '美国', v: '8'},
                    {n: '泰国', v: '9'},
                    {n: '英国', v: '1'},
                    {n: '韩国', v: '5'},
                    {n: '日本', v: '10'},
                    {n: '其他', v: '9999'}
                ]
            },
            {
                key: 'iyear',
                name: '年份',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '即将上线', v: '1'},
                    {n: '2026', v: '2026'},
                    {n: '2025', v: '2025'},
                    {n: '2024', v: '2'},
                    {n: '2023', v: '3'},
                    {n: '2022', v: '4'},
                    {n: '2021', v: '5'},
                    {n: '2020-2016', v: '6'},
                    {n: '2015-2011', v: '7'},
                    {n: '2010-2000', v: '8'},
                    {n: '更早', v: '9'}
                ]
            },
            {
                key: 'theater',
                name: '剧场',
                value: [
                    {n: '全部', v: '-1'},
                    {n: 'X剧场', v: '1'},
                    {n: '板凳单元', v: '2'},
                    {n: '萤火单元', v: '3'},
                    {n: '十分剧场', v: '4'}
                ]
            },
            {
                key: 'award',
                name: '奖项',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '白玉兰奖', v: '1'},
                    {n: '飞天奖', v: '2'},
                    {n: '金鹰奖', v: '3'}
                ]
            },
            {
                key: 'ipay',
                name: '资费',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '免费', v: '1'},
                    {n: '限免', v: '2'},
                    {n: '会员', v: '3'}
                ]
            }
        ],
        variety: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '游戏', v: '10'},
                    {n: '脱口秀', v: '2'},
                    {n: '音乐舞台', v: '11'},
                    {n: '情感', v: '12'},
                    {n: '生活', v: '22'},
                    {n: '职场', v: '20'},
                    {n: '喜剧', v: '14'},
                    {n: '美食', v: '19'},
                    {n: '潮流运动', v: '21'},
                    {n: '竞技', v: '24'},
                    {n: '影视', v: '16'},
                    {n: '电竞', v: '15'},
                    {n: '推理', v: '25'},
                    {n: '访谈', v: '3'},
                    {n: '亲子', v: '17'},
                    {n: '文化', v: '26'},
                    {n: '互动', v: '23'},
                    {n: '晚会', v: '6'},
                    {n: '资讯', v: '7'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最近更新', v: '23'},
                    {n: '高分好评', v: '85'}
                ]
            },
            {
                key: 'iarea',
                name: '地区',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '国内', v: '1'},
                    {n: '海外', v: '2'}
                ]
            },
            {
                key: 'iyear',
                name: '年份',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '2026', v: '2026'},
                    {n: '2025', v: '2025'},
                    {n: '2024', v: '2024'},
                    {n: '2023', v: '2023'},
                    {n: '2022', v: '2022'},
                    {n: '2021', v: '2021'},
                    {n: '2020', v: '50'},
                    {n: '2019', v: '7'},
                    {n: '2018', v: '1'},
                    {n: '2017', v: '2'},
                    {n: '2016', v: '3'},
                    {n: '2015', v: '4'},
                    {n: '2014', v: '5'},
                    {n: '2013', v: '6'},
                    {n: '2012', v: '2012'},
                    {n: '2011', v: '2011'},
                    {n: '2010', v: '2010'},
                    {n: '更早', v: '99'}
                ]
            }
        ],
        cartoon: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '玄幻', v: '9'},
                    {n: '科幻', v: '4'},
                    {n: '奇幻', v: '21'},
                    {n: '武侠', v: '13'},
                    {n: '仙侠', v: '23'},
                    {n: '都市', v: '24'},
                    {n: '恋爱', v: '7'},
                    {n: '搞笑', v: '1'},
                    {n: '冒险', v: '2'},
                    {n: '悬疑', v: '17'},
                    {n: '竞技', v: '20'},
                    {n: '日常', v: '15'},
                    {n: '真人', v: '18'},
                    {n: '治愈', v: '25'},
                    {n: '游戏', v: '26'},
                    {n: '异能', v: '27'},
                    {n: '历史', v: '19'},
                    {n: '古风', v: '28'},
                    {n: '智斗', v: '29'},
                    {n: '恐怖', v: '30'},
                    {n: '美食', v: '31'},
                    {n: '音乐', v: '32'},
                    {n: '其他', v: '12'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最近更新', v: '23'},
                    {n: '高分好评', v: '85'}
                ]
            },
            {
                key: 'iarea',
                name: '地区',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '内地', v: '1'},
                    {n: '日本', v: '2'},
                    {n: '欧美', v: '3'},
                    {n: '其他', v: '4'}
                ]
            },
            {
                key: 'iyear',
                name: '年份',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '2026', v: '2026'},
                    {n: '2025', v: '2025'},
                    {n: '2024', v: '2024'},
                    {n: '2023', v: '2023'},
                    {n: '2022', v: '2022'},
                    {n: '2021', v: '2021'},
                    {n: '2020', v: '50'},
                    {n: '2019', v: '11'},
                    {n: '2018', v: '2018'},
                    {n: '2017', v: '2017'},
                    {n: '2016', v: '1'},
                    {n: '2015', v: '2'},
                    {n: '2014', v: '3'},
                    {n: '2013', v: '4'},
                    {n: '2012', v: '5'},
                    {n: '2011', v: '6'},
                    {n: '00年代', v: '7'},
                    {n: '90年代', v: '8'},
                    {n: '80年代', v: '9'},
                    {n: '更早', v: '10'}
                ]
            }
        ],
        child: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '磨耳朵', v: '22'},
                    {n: '涨知识', v: '23'},
                    {n: '冒险', v: '10'},
                    {n: '儿歌', v: '1'},
                    {n: '交通工具', v: '11'},
                    {n: '益智早教', v: '2'},
                    {n: '玩具', v: '4'},
                    {n: '魔幻·科幻', v: '12'},
                    {n: '动物', v: '13'},
                    {n: '真人·特摄', v: '14'},
                    {n: '家长甄选', v: '17'},
                    {n: '动画电影', v: '20'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最新', v: '76'}
                ]
            },
            {
                key: 'iyear',
                name: '年龄',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '0-3岁', v: '1'},
                    {n: '4-6岁', v: '2'},
                    {n: '7-9岁', v: '3'},
                    {n: '10岁以上', v: '4'},
                    {n: '全年龄', v: '7'}
                ]
            }
        ],
        doco: [
            {
                key: 'itype',
                name: '类型',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '自然', v: '4'},
                    {n: '美食', v: '10'},
                    {n: '社会', v: '3'},
                    {n: '人文', v: '6'},
                    {n: '历史', v: '1'},
                    {n: '军事', v: '2'},
                    {n: '科技', v: '8'},
                    {n: '财经', v: '14'},
                    {n: '探险', v: '15'},
                    {n: '罪案', v: '7'},
                    {n: '竞技', v: '12'},
                    {n: '旅游', v: '11'}
                ]
            },
            {
                key: 'sort',
                name: '排序',
                value: [
                    {n: '最热', v: '75'},
                    {n: '最新', v: '74'},
                    {n: '高分好评', v: '85'}
                ]
            },
            {
                key: 'iyear',
                name: '年份',
                value: [
                    {n: '全部', v: '-1'},
                    {n: '2026', v: '2026'},
                    {n: '2025', v: '2025'},
                    {n: '2024', v: '1'},
                    {n: '2023', v: '2'},
                    {n: '2022', v: '3'},
                    {n: '2021', v: '4'},
                    {n: '2020', v: '5'},
                    {n: '2019-2015', v: '6'},
                    {n: '2014-2010', v: '7'},
                    {n: '2009-2005', v: '8'},
                    {n: '更早', v: '9'}
                ]
            }
        ]
    },
    // 各分类筛选默认值(供框架初始化)
    filter_def: {
        movie: {itype: '-1', sort: '75', iarea: '-1', iyear: '-1', ipay: '-1'},
        tv: {itype: '-1', sort: '75', iarea: '-1', iyear: '-1', theater: '-1', award: '-1', ipay: '-1'},
        variety: {itype: '-1', sort: '75', iarea: '-1', iyear: '-1'},
        cartoon: {itype: '-1', sort: '75', iarea: '-1', iyear: '-1'},
        child: {itype: '-1', sort: '75', iyear: '-1'},
        doco: {itype: '-1', sort: '75', iyear: '-1'}
    },
    // 腾讯无 itype 的类型 -> 条目别名规则(供客户端筛选)
    // genre: main_genre 需精确匹配的取值;tag: 角标/标题包含即命中;excl: main_genre 落入则排除
    // 例:奇幻片排除动画(动画片已有独立筛选项),避免熊出没等动画混入
    _qqGenreRule: {
        '奇幻': {genre: ['奇幻'], tag: ['奇幻'], excl: ['动画']},
        '武侠': {genre: ['武侠', '古装'], tag: ['武侠']},
        '历史': {genre: ['历史'], tag: ['历史']},
        '文艺': {genre: ['文艺', '剧情', '传记'], tag: ['文艺']},
        '剧情': {genre: ['剧情'], tag: []},
        '谍战': {genre: ['谍战'], tag: ['谍战']}
    },

    // 精选频道:拉取一个频道页(getPage 接口),返回 {items, ctx, hasNext}
    _qqFetchPage: function (channelId, pageContext) {
        let g = (Date.now().toString(16) + Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2)).slice(0, 16);
        let url = "https://pbaccess.video.%71%71.com/trpc.vector_layout.page_view.PageService/getPage?video_appid=3000010&vversion_platform=2&vdevice_guid=" + g;
        let body = {
            page_params: {
                page_type: "channel",
                page_id: String(channelId),
                scene: "channel",
                new_mark_label_enabled: "1",
                ad_exp_ids: "",
                ams_cookies: "",
                skip_privacy_types: "",
                support_click_scan: "1",
                ad_trans_data: '{"ad_request_id":"' + g + '","game_sessions":[]}'
            },
            page_bypass_params: {
                params: {
                    platform_id: "2",
                    caller_id: "3000010",
                    data_mode: "default",
                    user_mode: "default",
                    specified_strategy: "",
                    page_type: "channel",
                    page_id: String(channelId),
                    scene: "channel",
                    new_mark_label_enabled: "1"
                },
                scene: "channel",
                app_version: "",
                abtest_bypass_id: g
            },
            page_context: pageContext || null
        };
        let headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Referer": "https://v.qq.com/",
            "Origin": "https://v.qq.com"
        };
        let json = JSON.parse(post(url, {
            body: JSON.stringify(body),
            headers: headers
        }));
        let data = json.data || {};
        let items = [];
        let cards = data.CardList || [];
        for (let i = 0; i < cards.length; i++) {
            let cl = cards[i].children_list;
            if (cl && cl.list && cl.list.cards) {
                let arr = cl.list.cards;
                for (let j = 0; j < arr.length; j++) {
                    let p = arr[j].params || {};
                    if (p.cid) {
                        items.push({
                            cid: p.cid,
                            title: p.title || "",
                            img: p.image_url_vertical || p.image_url || "",
                            desc: [p.areaName, p.year, p.sub_title].filter(function (x) {
                                return !!x;
                            }).join(" "),
                            genre: "",
                            tag: ""
                        });
                    }
                }
            }
        }
        return {
            items: items,
            ctx: data.page_context || null,
            hasNext: !!data.has_next_page
        };
    },

    // 分类页:getMVLPage 接口,支持服务端筛选(filterParams),游标分页
    _qqFetchMVL: function (channelId, filterParams, pageContext) {
        let url = "https://pbaccess.video.%71%71.com/trpc.multi_vector_layout.mvl_controller.MVLPageHTTPService/getMVLPage?&vversion_platform=2";
        let pageParams = {
            page_type: "operation",
            page_id: "channel_list",
            channel_id: String(channelId)
        };
        if (filterParams) {
            pageParams.filter_params = filterParams;
        }
        let body = {
            page_params: pageParams
        };
        if (pageContext) {
            body.page_context = pageContext;
        }
        let headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Referer": "https://v.qq.com/",
            "Origin": "https://v.qq.com"
        };
        let json = JSON.parse(post(url, {
            body: JSON.stringify(body),
            headers: headers
        }));
        let data = json.data || {};
        let items = [];
        let mods = (((data.modules || {}).normal || {}).cards) || [];
        for (let i = 0; i < mods.length; i++) {
            let cl = mods[i].children_list || {};
            let arr = ((cl.poster_card || {}).cards) || [];
            for (let j = 0; j < arr.length; j++) {
                let p = arr[j].params || {};
                if (p.cid) {
                    items.push({
                        cid: p.cid,
                        title: p.title || "",
                        img: p.new_pic_vt || p.new_pic_hz || "",
                        desc: [p.main_genre, p.areaName, p.year].filter(function (x) {
                            return !!x;
                        }).join(" "),
                        genre: p.main_genre || "",
                        tag: p.third_title || ""
                    });
                }
            }
        }
        return {
            items: items,
            ctx: data.page_context || null,
            hasNext: !!data.has_next_page
        };
    },

    // 统一转成框架列表项
    _qqMap: function (items) {
        return (items || []).map(function (it) {
            return {
                title: it.title,
                img: it.img,
                url: "https://node.video.%71%71.com/x/api/float_vinfo2?cid=" + it.cid,
                desc: it.desc
            };
        });
    },

    // 客户端类型命中判断:主类型精确匹配,或角标/标题含别名(先排除明确冲突的主类型)
    _qqMatchGenre: function (it, genre) {
        let r = rule._qqGenreRule[genre] || {genre: [genre], tag: [genre], excl: []};
        let g = it.genre || "";
        let tag = it.tag || "";
        let title = it.title || "";
        if (r.excl && r.excl.indexOf(g) >= 0) {
            return false;
        }
        if (r.genre && r.genre.indexOf(g) >= 0) {
            return true;
        }
        let ts = r.tag || [];
        for (let i = 0; i < ts.length; i++) {
            let a = ts[i];
            if (a.length >= 2 && (tag.indexOf(a) >= 0 || title.indexOf(a) >= 0)) {
                return true;
            }
        }
        return false;
    },

    // 客户端类型筛选:腾讯无对应 itype 时,按条目主类型逐页扫描汇总
    // 结果缓存在 rule._qqPool,每次调用最多向上游取 budget 页(约 budget*12 条)
    _qqCollectGenre: function (channelId, genre, pg, extra) {
        rule._qqPool = rule._qqPool || {};
        let key = channelId + "#" + genre + "#" + extra;
        let pool = rule._qqPool[key];
        if (!pool || pg <= 1) {
            pool = rule._qqPool[key] = {
                items: [],
                ctx: null,
                done: false,
                scanned: 0,
                served: 0,
                seen: {}
            };
        }
        let limit = rule.limit || 20;
        let budget = 18;
        while ((pool.items.length - pool.served) < limit && !pool.done && budget > 0) {
            let r = rule._qqFetchMVL(channelId, extra, pool.ctx);
            pool.ctx = r.ctx;
            pool.scanned++;
            budget--;
            if (!r.items || r.items.length === 0) {
                pool.done = true;
                break;
            }
            for (let i = 0; i < r.items.length; i++) {
                let it = r.items[i];
                if (pool.seen[it.cid]) {
                    continue;
                }
                pool.seen[it.cid] = 1;
                if (rule._qqMatchGenre(it, genre)) {
                    pool.items.push(it);
                }
            }
            if (!r.hasNext) {
                pool.done = true;
            }
        }
        let out = pool.items.slice(pool.served, pool.served + limit);
        pool.served += out.length;
        return rule._qqMap(out);
    },

    推荐: $js.toString(() => {
        let d = [];
        try {
            let r = rule._qqFetchPage(rule._qqChannelMap.choice, null);
            d = rule._qqMap(r.items);
        } catch (e) {
            log("QQ首页接口异常:" + e.message);
        }
        setResult(d);
    }),

    一级: $js.toString(() => {
        let d = [];
        let tid = (typeof MY_CATE == "undefined" || !MY_CATE) ? "choice" : MY_CATE;
        let pg = (typeof MY_PAGE == "undefined") ? 1 : (parseInt(MY_PAGE) || 1);
        let fl = (typeof MY_FL == "undefined" || !MY_FL) ? {} : MY_FL;
        let channelId = rule._qqChannelMap[tid] || rule._qqChannelMap.choice;
        let itype = (fl.itype === undefined || fl.itype === null || fl.itype === "") ? "-1" : String(fl.itype);
        // 组装服务端筛选参数;useType=false 时不带 itype(用于客户端类型扫描)
        let srv = function (useType) {
            let a = [];
            let push = function (k, v) {
                if (v === undefined || v === null || v === "" || String(v) === "-1") {
                    return;
                }
                a.push(k + "=" + v);
            };
            if (useType && /^-?\d+$/.test(itype) && itype !== "-1") {
                a.push("itype=" + itype);
            }
            push("sort", fl.sort);
            push("iarea", fl.iarea);
            push("iyear", fl.iyear);
            push("theater", fl.theater);
            push("award", fl.award);
            push("ipay", fl.ipay);
            return a.join("&");
        };
        try {
            if (/^g/.test(itype)) {
                // 腾讯无对应 itype 的类型:客户端按主类型筛选
                d = rule._qqCollectGenre(channelId, itype.slice(1), pg, srv(false));
            } else if (tid === "choice") {
                // 精选频道无筛选,沿用 getPage 游标分页
                rule._qqCtx = rule._qqCtx || {};
                let cache = rule._qqCtx[channelId] || (rule._qqCtx[channelId] = {});
                let ctx = null;
                let start = 1;
                for (let p = pg - 1; p >= 1; p--) {
                    if (cache[p]) {
                        ctx = cache[p];
                        start = p + 1;
                        break;
                    }
                }
                let last = [];
                for (let p = start; p <= pg; p++) {
                    let r = rule._qqFetchPage(channelId, ctx);
                    ctx = r.ctx;
                    cache[p] = ctx;
                    last = r.items;
                }
                d = rule._qqMap(last);
            } else {
                let fp = srv(true);
                // 游标分页缓存,key 含筛选参数,避免切筛选后串页
                rule._qqCtx = rule._qqCtx || {};
                let key = channelId + "|" + fp;
                let cache = rule._qqCtx[key] || (rule._qqCtx[key] = {});
                let ctx = null;
                let start = 1;
                for (let p = pg - 1; p >= 1; p--) {
                    if (cache[p]) {
                        ctx = cache[p];
                        start = p + 1;
                        break;
                    }
                }
                let last = [];
                for (let p = start; p <= pg; p++) {
                    let r = rule._qqFetchMVL(channelId, fp, ctx);
                    ctx = r.ctx;
                    cache[p] = ctx;
                    last = r.items;
                }
                d = rule._qqMap(last);
            }
        } catch (e) {
            log("QQ分类接口异常:" + e.message);
        }
        setResult(d);
    }),

    二级: $js.toString(() => {
        VOD = {};
        let d = [];
        let video_list = [];
        let video_lists = [];
        let list = [];
        let QZOutputJson;
        let html = fetch(input, fetch_params);
        let sourceId = /get_playsource/.test(input) ? input.match(/id=(\d*?)&/)[1] : input.split("cid=")[1];
        let cid = sourceId;
        let detailUrl = "https://v.%71%71.com/detail/m/" + cid + ".html";
        log("详情页:" + detailUrl);
        pdfh = jsp.pdfh;
        pd = jsp.pd;
        try {
            let json = JSON.parse(html);
            VOD = {
                vod_url: input,
                vod_name: json.c.title,
                type_name: json.typ.join(","),
                vod_actor: json.nam.join(","),
                vod_year: json.c.year,
                vod_content: json.c.description,
                vod_remarks: json.rec,
                vod_pic: urljoin2(input, json.c.pic)
            }
        } catch (e) {
            log("解析片名海报等基础信息发生错误:" + e.message)
        }
        if (/get_playsource/.test(input)) {
            eval(html);
            let indexList = QZOutputJson.PlaylistItem.indexList;
            indexList.forEach(function (it) {
                let dataUrl = "https://s.video.qq.com/get_playsource?id=" + sourceId + "&plat=2&type=4&data_type=3&range=" + it + "&video_type=10&plname=qq&otype=json";
                eval(fetch(dataUrl, fetch_params));
                let vdata = QZOutputJson.PlaylistItem.videoPlayList;
                vdata.forEach(function (item) {
                    d.push({
                        title: item.title,
                        pic_url: item.pic,
                        desc: item.episode_number + "\t\t\t播放量：" + item.thirdLine,
                        url: item.playUrl
                    })
                });
                video_lists = video_lists.concat(vdata)
            })
        } else {
            let json = JSON.parse(html);
            video_lists = json.c.video_ids;
            let url = "https://v.qq.com/x/cover/" + sourceId + ".html";
            if (json.c.type === 10) {
                // 综艺栏目优先按季(range)取完整选集,接口不可用时降级到video_ids
                try {
                    let colUrl = "https://s.video.qq.com/get_playsource?id=" + json.c.column_id + "&plat=2&type=2&data_type=3&video_type=8&plname=qq&otype=json";
                    eval(fetch(colUrl, fetch_params));
                    let indexList = QZOutputJson.PlaylistItem.indexList || [];
                    indexList.forEach(function (range) {
                        let epUrl = "https://s.video.qq.com/get_playsource?id=" + json.c.column_id + "&plat=2&type=4&data_type=3&range=" + range + "&video_type=10&plname=qq&otype=json";
                        eval(fetch(epUrl, fetch_params));
                        let vdata = QZOutputJson.PlaylistItem.videoPlayList || [];
                        vdata.forEach(function (item) {
                            d.push({
                                title: item.title,
                                pic_url: item.pic,
                                desc: item.episode_number + "\t\t\t播放量：" + item.thirdLine,
                                url: item.playUrl
                            })
                        })
                    })
                } catch (eCol) {
                    log("综艺栏目选集接口异常,改用video_ids兜底:" + eCol.message);
                    d = [];
                }
            }
            if (d.length === 0 && video_lists.length === 1) {
                let vid = video_lists[0];
                url = "https://v.qq.com/x/cover/" + cid + "/" + vid + ".html";
                d.push({
                    title: "在线播放",
                    url: url
                })
            } else if (d.length === 0 && video_lists.length > 1) {
                for (let i = 0; i < video_lists.length; i += 30) {
                    video_list.push(video_lists.slice(i, i + 30))
                }
                video_list.forEach(function (it, idex) {
                    let o_url = "https://union.video.qq.com/fcgi-bin/data?otype=json&tid=1804&appid=20001238&appkey=6c03bbe9658448a4&union_platform=1&idlist=" + it.join(",");
                    let o_html = fetch(o_url, fetch_params);
                    eval(o_html);
                    QZOutputJson.results.forEach(function (it1) {
                        it1 = it1.fields;
                        let url = "https://v.qq.com/x/cover/" + cid + "/" + it1.vid + ".html";
                        d.push({
                            title: it1.title,
                            pic_url: it1.pic160x90.replace("/160", ""),
                            desc: it1.video_checkup_time,
                            url: url,
                            type: it1.category_map && it1.category_map.length > 1 ? it1.category_map[1] : ""
                        })
                    })
                })
            }
        }
        let isYg = function (it) {
            return it.type && it.type !== "正片" && it.type.indexOf("正片") === -1;
        };
        let yg = d.filter(isYg);
        let zp = d.filter(function (it) {
            return !isYg(it);
        });
        VOD.vod_play_from = yg.length < 1 ? "qq" : "qq$$$qq 预告及花絮";
        VOD.vod_play_url = yg.length < 1 ? d.map(function (it) {
            return it.title + "$" + it.url
        }).join("#") : [zp, yg].map(function (it) {
            return it.map(function (its) {
                return its.title + "$" + its.url
            }).join("#")
        }).join("$$$");
    }),

    搜索: $js.toString(() => {
        let d = [];
        let pg = (typeof MY_PAGE == "undefined") ? 1 : (parseInt(MY_PAGE) || 1);
        let cidMap = {};
        let postHeader = {
            "Content-Type": "application/json;charset=UTF-8",
            "Referer": "https://v.qq.com/",
            "Origin": "https://v.qq.com"
        };
        function cleanHtml(s) {
            return (s || "").replace(/<[^>]+>/g, "");
        }
        function addItem(cid, title, img, desc, content) {
            if (!cid || cidMap[cid]) return;
            cidMap[cid] = 1;
            d.push({
                title: title,
                img: img,
                url: "https://node.video.%71%71.com/x/api/float_vinfo2?cid=" + cid,
                desc: desc || "",
                content: content || ""
            });
        }
        // 旧 Smartbox GET 接口已失效(ret=35013),网页搜索页也已改为纯SPA,改用新版多端搜索 POST 接口
        let searchApi = "https://pbaccess.video.%71%71.com/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vversion_platform=2";
        let reqUuid = (Date.now().toString(16) + Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2)).slice(0, 16);
        let body = {
            version: "26022601",
            clientType: 1,
            filterValue: "",
            uuid: reqUuid,
            retry: 0,
            query: KEY,
            pagenum: pg - 1,
            pagesize: 30,
            queryFrom: 0,
            searchDatakey: "",
            transInfo: "",
            isneedQc: true,
            preQid: "",
            isPrefetch: false,
            adClientInfo: "",
            extraInfo: {
                isNewMarkLabel: "0",
                multi_terminal_pc: "1",
                themeType: "0",
                sugRelatedIds: "{}",
                appVersion: "",
                frontVersion: "26060108"
            },
            featureList: ["DEFAULT_FEFEATURE", "PC_SHORT_VIDEOS_WATERFALL", "PC_WANT_EPISODE_V2", "PC_WANT_EPISODE"]
        };
        function fetchCovers(kw) {
            body.query = kw;
            body.pagenum = 0;
            let json = JSON.parse(post(searchApi, {
                body: JSON.stringify(body),
                headers: postHeader
            }));
            let itemList = (json.data && json.data.normalList && json.data.normalList.itemList) || [];
            itemList.forEach(function (it) {
                if (it.doc && it.doc.dataType == 2 && it.videoInfo) {
                    let vi = it.videoInfo;
                    let desc = [vi.typeName, vi.year, cleanHtml(vi.subTitle)].filter(function (x) {
                        return !!x;
                    }).join(" ");
                    addItem(it.doc.id, cleanHtml(vi.title), vi.imgUrl, desc, cleanHtml(vi.descrip));
                }
            });
        }
        try {
            fetchCovers(KEY);
        } catch (e) {
            log("QQ多端搜索接口异常:" + e.message);
        }
        // 综艺/老剧等栏目在多端搜索中不返回,首页再用智能联想接口补充可播放的专辑/栏目
        if (pg === 1) {
            try {
                let sugApi = "https://pbaccess.video.%71%71.com/trpc.videosearch.smartboxServer.SugRecallHttp/GetSugHttp";
                let sugBody = {
                    auth_info: {
                        app_id: "3168",
                        app_key: "Ve3Z02Uwte4AH4tJ"
                    },
                    plat_version: 15,
                    version: "26022601",
                    page_num: 0,
                    page_size: 10,
                    query: KEY,
                    scene: 1
                };
                let sugJson = JSON.parse(post(sugApi, {
                    body: JSON.stringify(sugBody),
                    headers: postHeader
                }));
                let sugList = (sugJson.data && sugJson.data.result_list && sugJson.data.result_list.item_list) || [];
                let textSug = [];
                sugList.forEach(function (it) {
                    try {
                        let view = it.view || {};
                        let doc = it.doc || {};
                        let cid = "";
                        let dt = doc.data_type;
                        if (dt == 0 && /^(mzc|sdp)/.test(doc.id || "")) {
                            cid = doc.id;
                        } else if ((dt == 10 || dt == 77) && view.img_url) {
                            // 系列节点本身不可播,但海报地址里带的是可播放的代表专辑cid
                            let mm = view.img_url.match(/\/((?:mzc|sdp)[0-9a-z]{12}|[a-z][0-9a-z]{13})(?=\d{10,})/) || view.img_url.match(/\/((?:mzc|sdp)[0-9a-z]{12})/);
                            if (mm) cid = mm[1];
                        } else if (dt == 0 && !doc.id) {
                            let lines = (view.lines || []).map(function (l) {
                                return cleanHtml(l.text);
                            }).filter(function (x) {
                                return !!x;
                            });
                            if (lines[0]) textSug.push(lines[0]);
                        }
                        if (cid) {
                            let lines = (view.lines || []).map(function (l) {
                                return cleanHtml(l.text);
                            }).filter(function (x) {
                                return !!x;
                            });
                            addItem(cid, lines[0] || KEY, view.img_url, lines.slice(1).join(" "), "");
                        }
                    } catch (e2) {}
                });
                // 宽泛词多端搜索只回短视频时,用联想词再召回一次专辑
                if (d.length === 0) {
                    for (let i = 0; i < textSug.length && d.length === 0 && i < 2; i++) {
                        try {
                            fetchCovers(textSug[i]);
                        } catch (e3) {}
                    }
                }
            } catch (e) {
                log("QQ智能联想接口异常:" + e.message);
            }
        }
        setResult(d);
    })
}