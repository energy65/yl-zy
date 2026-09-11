var rule = {
    title: '腾云驾雾[官]',
    host: 'https://v.%71%71.com',
    homeUrl: '/channel/choice',
    detailUrl: 'https://node.video.%71%71.com/x/api/float_vinfo2?cid=fyid',
    searchUrl: 'https://pbaccess.video.%71%71.com/trpc.videosearch.smartboxServer.HttpRountRecall/Smartbox?query=**&appID=3172&appKey=lGhFIPeD3HsO9xEp&pageNum=(fypage-1)&pageSize=10',
    searchable: 2,
    multi: 1,
    filterable: 0,
    // 腾讯视频官方接口已失效,改用频道页SSR数据(仅第一页有数据),MY_PAGE>1直接返回空防止无限请求
    url: '/channel/fyclass',
    headers: {
        'User-Agent': 'PC_UA'
    },
    timeout: 5000,
    cate_exclude: '会员|游戏|全部',
    class_name: '精选&电影&电视剧&综艺&动漫&少儿&纪录片',
    class_url: 'choice&movie&tv&variety&cartoon&child&doco',
    limit: 20,
    // play_parse:true,
    // 手动调用解析请求json的url,此lazy不方便
    lazy: 'js:input="https://cache.json.icu/home/api?type=ys&uid=292796&key=fnoryABDEFJNPQV269&url="+input.split("?")[0];log(input);let html=JSON.parse(request(input));log(html);input=html.url||input',
    一级: 'js:(function(){let d=[];if(typeof MY_PAGE==="number"&&MY_PAGE>1){setResult([]);return}let html="";try{html=fetch(input,fetch_params)}catch(e){log("一级抓取失败:"+e.message)}if(!html){setResult([]);return}let arr=html.split(\'cid:"\');let seen={};for(let i=1;i<arr.length;i++){if(d.length>=60)break;let blk=arr[i];let cid=blk.split(\'"\')[0];if(!cid||cid.length<6||seen[cid])continue;seen[cid]=1;let win=blk.slice(0,2200);let mz=win.match(/mzTitle:"([^"]*)"/);let title=mz?mz[1]:"";if(!title){let mt=win.match(/title:"([^"]*)"/);title=mt&&mt[1]?mt[1]:""}if(!title)continue;let pp=win.match(/smallCoverPic:"([^"]+)"/);let pic=pp?pp[1]:"";if(!pic){let cp=win.match(/coverPic:"([^"]+)"/);pic=cp?cp[1]:""}let tl=win.match(/topicLabelTitle:"([^"]*)"/);let desc=tl?tl[1]:"";d.push({title:title,desc:desc,pic_url:pic,url:"https://node.video.qq.com/x/api/float_vinfo2?cid="+cid})}setResult(d)})()',
    推荐: 'js:(function(){let d=[];let html="";try{html=fetch(input,fetch_params)}catch(e){log("推荐抓取失败:"+e.message)}if(!html){setResult([]);return}let arr=html.split(\'cid:"\');let seen={};for(let i=1;i<arr.length;i++){if(d.length>=60)break;let blk=arr[i];let cid=blk.split(\'"\')[0];if(!cid||cid.length<6||seen[cid])continue;seen[cid]=1;let win=blk.slice(0,2200);let mz=win.match(/mzTitle:"([^"]*)"/);let title=mz?mz[1]:"";if(!title){let mt=win.match(/title:"([^"]*)"/);title=mt&&mt[1]?mt[1]:""}if(!title)continue;let pp=win.match(/smallCoverPic:"([^"]+)"/);let pic=pp?pp[1]:"";if(!pic){let cp=win.match(/coverPic:"([^"]+)"/);pic=cp?cp[1]:""}let tl=win.match(/topicLabelTitle:"([^"]*)"/);let desc=tl?tl[1]:"";d.push({title:title,desc:desc,pic_url:pic,url:"https://node.video.qq.com/x/api/float_vinfo2?cid="+cid})}setResult(d)})()',
    二级: $js.toString(() => {
        VOD = {};
        let d = [];
        let cid = "";
        try {
            let m = input.match(/cid=([^&]+)/);
            if (m) {
                cid = m[1];
            } else {
                m = input.match(/\/cover\/([^\/]+?)(?:\/|\.html|$)/);
                if (m) cid = m[1]
            }
            if (/^%/.test(cid)) cid = decodeURIComponent(cid)
        } catch (e) {
            cid = ""
        }
        if (!cid) cid = "mzc00200xscz58k";
        let fallback = "https://v.qq.com/x/cover/" + cid + ".html";
        try {
            let html = fetch(input, fetch_params);
            if (/get_playsource/.test(input)) {
                eval(html);
                let pl = QZOutputJson.PlaylistItem || {};
                let idx = pl.indexList || [];
                for (let k = 0; k < idx.length; k++) {
                    if (d.length >= 500) break;
                    let dataUrl = "https://s.video.qq.com/get_playsource?id=" + cid + "&plat=2&type=4&data_type=3&range=" + idx[k] + "&video_type=10&plname=qq&otype=json";
                    try {
                        eval(fetch(dataUrl, fetch_params));
                        let vps = (QZOutputJson.PlaylistItem && QZOutputJson.PlaylistItem.videoPlayList) || [];
                        vps.forEach(function (item, j) {
                            if (d.length >= 500) return;
                            d.push({
                                title: item.title || ("第" + (j + 1) + "集"),
                                url: item.playUrl || "",
                                pic_url: item.pic || "",
                                desc: item.episode_number || ""
                            })
                        })
                    } catch (e) {
                        log("get_playsource错误:" + e.message)
                    }
                }
            } else {
                let json = JSON.parse(html);
                let c = json.c || {};
                let join2 = typeof urljoin2 === "function" ? urljoin2 : function (a, b) {
                    return b && b.indexOf("http") === 0 ? b : a
                };
                try {
                    VOD.vod_url = input;
                    VOD.vod_name = c.title || "";
                    VOD.type_name = (json.typ || []).join(",");
                    VOD.vod_actor = (json.nam || []).join(",");
                    VOD.vod_year = c.year || "";
                    VOD.vod_content = c.description || "";
                    VOD.vod_remarks = json.rec || "";
                } catch (e) {
                    log("解析片名海报等基础信息发生错误:" + e.message)
                }
                try {
                    VOD.vod_pic = c.pic ? join2(input, c.pic) : ""
                } catch (e) {
                    log("解析海报发生错误:" + e.message)
                }
                let video_lists = c.video_ids || [];
                if (video_lists.length > 500) video_lists = video_lists.slice(0, 500);
                if (video_lists.length === 1) {
                    let vid = video_lists[0];
                    fallback = "https://v.qq.com/x/cover/" + cid + "/" + vid + ".html";
                    d.push({
                        title: "在线播放",
                        url: fallback
                    })
                } else if (video_lists.length > 1) {
                    let batches = [];
                    for (let i = 0; i < video_lists.length; i += 30) {
                        batches.push(video_lists.slice(i, i + 30))
                    }
                    let epn = 0;
                    batches.forEach(function (bt, bi) {
                        if (d.length >= 500) return;
                        let o_url = "https://union.video.qq.com/fcgi-bin/data?otype=json&tid=1804&appid=20001238&appkey=6c03bbe9658448a4&union_platform=1&idlist=" + bt.join(",");
                        try {
                            let o_html = fetch(o_url, fetch_params);
                            eval(o_html);
                            let res = QZOutputJson.results || [];
                            res.forEach(function (it1) {
                                if (d.length >= 500) return;
                                let it = it1.fields || {};
                                let url = "https://v.qq.com/x/cover/" + cid + "/" + it.vid + ".html";
                                d.push({
                                    title: it.title || ("第" + (epn + 1) + "集"),
                                    pic_url: it.pic160x90 ? it.pic160x90.replace("/160", "") : "",
                                    desc: it.video_checkup_time || "",
                                    url: url,
                                    type: it.category_map && it.category_map.length > 1 ? it.category_map[1] : ""
                                });
                                epn++
                            })
                        } catch (e) {
                            // union接口偶发失败,退化按序号生成集数,避免列表为空
                            bt.forEach(function (vid, j) {
                                if (d.length >= 500) return;
                                let url = "https://v.qq.com/x/cover/" + cid + "/" + vid + ".html";
                                d.push({
                                    title: "第" + (bi * 30 + j + 1) + "集",
                                    url: url
                                })
                            })
                        }
                    })
                } else {
                    d.push({
                        title: "在线播放",
                        url: fallback
                    })
                }
            }
        } catch (e) {
            log("二级解析异常:" + e.message);
            d.push({
                title: "在线播放",
                url: fallback
            })
        }
        let yg = [];
        let zp = [];
        d.forEach(function (it) {
            if (it.type && it.type !== "正片") {
                yg.push(it)
            } else {
                zp.push(it)
            }
        });
        VOD.vod_play_from = "qq";
        let playLines = [];
        if (zp.length > 0) {
            playLines.push(zp.map(function (it) {
                return it.title + "$" + it.url
            }).join("#"))
        }
        if (yg.length > 0) {
            playLines.push(yg.map(function (it) {
                return it.title + "$" + it.url
            }).join("#"))
        }
        if (playLines.length > 1) {
            VOD.vod_play_from = "qq$$$qq预告及花絮"
        }
        VOD.vod_play_url = playLines.join("$$$");
        if (!VOD.vod_play_url) VOD.vod_play_url = "在线播放$" + fallback
    }),
    搜索: $js.toString(() => {
        let d = [];
        try {
            let html = request(input);
            let json = JSON.parse(html);
            let list = (json.data && json.data.smartboxItemList) || [];
            let seen = {};
            list.forEach(function (it) {
                if (d.length >= 10) return;
                let doc = it.basicDoc || it || {};
                let cid = doc.id || "";
                if (!cid || seen[cid]) return;
                if (!/^[a-z0-9]{6,20}$/.test(cid)) return;
                seen[cid] = 1;
                let title = (doc.title || "").replace(/<\/?em>/g, "");
                let img = (it.videoInfo && it.videoInfo.imgUrl) || "";
                d.push({
                    title: title,
                    img: img,
                    url: "https://node.video.qq.com/x/api/float_vinfo2?cid=" + cid,
                    content: doc.docname || ""
                })
            })
        } catch (e) {
            log("搜索异常:" + e.message)
        }
        setResult(d)
    })
}