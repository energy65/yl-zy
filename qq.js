var rule = {
    title: '腾云驾雾[官]',
    host: 'https://v.%71%71.com',
    // 旧 pagesheet 接口已 404,首页与分类改用新版 getPage 接口(见 _qqFetchPage)
    homeUrl: '/channel/choice',
    detailUrl: 'https://node.video.%71%71.com/x/api/float_vinfo2?cid=fyid',
    searchUrl: '/x/search/?q=**&stag=fypage',
    searchable: 2,
    filterable: 0,
    multi: 1,
    // 分类 URL 仅用于框架生成 MY_URL,实际请求由 一级 JS 函数完成(fyclass/fypage 占位保留)
    url: '/channel/fyclass?page=fypage',
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
    // 拉取一个频道页,返回 {items, ctx, hasNext}
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
                            }).join(" ")
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
    lazy: 'js:input="https://cache.json.icu/home/api?type=ys&uid=292796&key=fnoryABDEFJNPQV269&url="+input.split("?")[0];log(input);let html=JSON.parse(request(input));log(html);input=html.url||input',
    推荐: $js.toString(() => {
        let d = [];
        try {
            let r = rule._qqFetchPage(rule._qqChannelMap.choice, null);
            d = r.items.map(function (it) {
                return {
                    title: it.title,
                    img: it.img,
                    url: "https://node.video.%71%71.com/x/api/float_vinfo2?cid=" + it.cid,
                    desc: it.desc
                };
            });
        } catch (e) {
            log("QQ首页接口异常:" + e.message);
        }
        setResult(d);
    }),
    一级: $js.toString(() => {
        let d = [];
        let tid = (typeof MY_CATE == "undefined") ? "choice" : MY_CATE;
        let pg = (typeof MY_PAGE == "undefined") ? 1 : (parseInt(MY_PAGE) || 1);
        let channelId = rule._qqChannelMap[tid] || rule._qqChannelMap.choice;
        // getPage 是游标分页,page_context 按频道+页码缓存,避免每次从第1页走到目标页
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
        try {
            let last = [];
            for (let p = start; p <= pg; p++) {
                let r = rule._qqFetchPage(channelId, ctx);
                ctx = r.ctx;
                cache[p] = ctx;
                last = r.items;
            }
            d = last.map(function (it) {
                return {
                    title: it.title,
                    img: it.img,
                    url: "https://node.video.%71%71.com/x/api/float_vinfo2?cid=" + it.cid,
                    desc: it.desc
                };
            });
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