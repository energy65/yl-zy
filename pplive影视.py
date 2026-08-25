# -*- coding: utf-8 -*-
# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
import requests
import base64
import time
import hashlib
from urllib import request, parse
import urllib
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class Spider(Spider):
    def getName(self):
        return "PPLive影视"

    def init(self, extend=""):
        print("============{0}============".format(extend))
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "movie",
            "电视剧": "tv",
            "动漫": "cartoon",
            "综艺": "zongyi",
            "少儿": "kid",
            "纪实": "real",
            "体育": "sports"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        if filter:
            result['filters'] = self.config['filter']
        return result

    def homeVideoContent(self):
        url = 'https://www.pptv.com/'
        HtmlTxt = self.custom_webReadFile(url, self.header)
        videos = []
        seen = set()
        pattern = r'<a[^>]*href="(https?://v\.pptv\.com/show/([^"]+)\.html)"[^>]*>(.*?)</a>'
        for m in re.finditer(pattern, HtmlTxt, re.S):
            eid = m.group(2)
            if eid in seen:
                continue
            seen.add(eid)
            inner = m.group(3)
            title = ''
            img_m = re.search(r'<img[^>]*(?:alt|title)="([^"]+)"', inner)
            if img_m:
                title = img_m.group(1).strip()
            if not title:
                title = re.sub(r'<[^>]+>', '', inner).strip()
            if not title or len(title) > 40:
                continue
            pic = re.search(r'<img[^>]*src="([^"]+)"', inner)
            pic_url = ''
            if pic:
                pic_url = pic.group(1)
                if pic_url.startswith('//'):
                    pic_url = 'https:' + pic_url
            videos.append({
                "vod_id": eid,
                "vod_name": title,
                "vod_pic": pic_url,
                "vod_remarks": ''
            })
        return {'list': videos[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        url = 'https://{0}.pptv.com/'.format(tid)
        HtmlTxt = self.custom_webReadFile(url, self.header)
        seen = set()
        pattern = r'<a[^>]*href="(https?://v\.pptv\.com/show/([^"]+)\.html)"[^>]*title="([^"]*)"'
        for m in re.finditer(pattern, HtmlTxt, re.S):
            eid = m.group(2)
            if eid in seen:
                continue
            seen.add(eid)
            title = m.group(3).strip()
            pic = re.search(r'<a[^>]*href="[^"]*' + re.escape(eid) + r'[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"', HtmlTxt[m.start():m.start() + 600], re.S)
            pic_url = ''
            if pic:
                pic_url = pic.group(1)
                if pic_url.startswith('//'):
                    pic_url = 'https:' + pic_url
            videos.append({
                "vod_id": eid,
                "vod_name": title,
                "vod_pic": pic_url,
                "vod_remarks": ''
            })
        if not videos:
            pattern2 = r'href="(https?://v\.pptv\.com/show/([^"]+)\.html)"[^>]*>'
            for m in re.finditer(pattern2, HtmlTxt, re.S):
                eid = m.group(2)
                if eid in seen:
                    continue
                seen.add(eid)
                pos = m.end()
                inner_block = HtmlTxt[pos:pos + 800]
                title = ''
                img_m = re.search(r'<img[^>]*(?:alt|title)="([^"]+)"', inner_block)
                if img_m:
                    title = img_m.group(1).strip()
                if not title:
                    img_m = re.search(r'<img[^>]*src="([^"]+)"', inner_block)
                    if img_m:
                        pic_url = img_m.group(1)
                        if pic_url.startswith('//'):
                            pic_url = 'https:' + pic_url
                    else:
                        pic_url = ''
                else:
                    pic_url = ''
                    img_m2 = re.search(r'<img[^>]*src="([^"]+)"', inner_block)
                    if img_m2:
                        pic_url = img_m2.group(1)
                        if pic_url.startswith('//'):
                            pic_url = 'https:' + pic_url
                if not title:
                    continue
                videos.append({
                    "vod_id": eid,
                    "vod_name": title,
                    "vod_pic": pic_url if pic_url else '',
                    "vod_remarks": ''
                })
        for v in videos:
            try:
                info = self._getBasicInfo(v['vod_id'])
                if info:
                    v['vod_pic'] = info.get('pic', '') or v['vod_pic']
                    v['vod_remarks'] = info.get('mark', '')
            except:
                pass
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 100
        result['limit'] = len(videos) if videos else 20
        result['total'] = 100 * result['limit']
        return result

    def detailContent(self, array):
        result = {}
        vod_id = array[0]
        html = self.custom_webReadFile('https://v.pptv.com/show/{0}.html'.format(vod_id), self.header)
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>', html, re.S)
        if not m:
            return {'list': []}
        try:
            st = json.loads(m.group(1))
        except:
            return {'list': []}
        vd = st.get('videoDetail', {})
        dc = st.get('detailContent', {})
        bi = dc.get('baseInfo', {})
        title = vd.get('title', '') or bi.get('title', '')
        pic = vd.get('sloturl', '') or bi.get('coverPic', '') or bi.get('coverTransPic', '')
        if pic and not pic.startswith('http'):
            pic = 'https:' + pic if pic.startswith('//') else pic
        description = vd.get('content', '') or bi.get('description', '') or ''
        if description:
            description += '\n\n微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力'
        else:
            description = '微信公众号"源力软件汇"，q群1054592152伴随更多优质资源尽在源力'

        actor = vd.get('actors', '') or bi.get('acts', '')
        if isinstance(actor, list):
            actor = ','.join([a.get('name', '') if isinstance(a, dict) else str(a) for a in actor])
        elif actor is None:
            actor = ''
        director = vd.get('director', '') or bi.get('directors', '')
        if isinstance(director, list):
            director = ','.join([d.get('name', '') if isinstance(d, dict) else str(d) for d in director])
        elif isinstance(director, str) and director.startswith('['):
            director = ''
        elif director is None:
            director = ''
        year = vd.get('year', '') or bi.get('year', '') or ''
        area = vd.get('area', '') or bi.get('area', '') or ''
        remark = vd.get('mark', '') or ''

        vod_play_from = ['PPLive']
        vodItems = []
        vl = vd.get('video_list', {})
        playlink2 = vl.get('playlink2', [])
        if isinstance(playlink2, dict):
            att = playlink2.get('_attributes', playlink2)
            ep_title = att.get('title', title)
            ep_id = att.get('id', '')
            if ep_id:
                vodItems.append(title + "$" + str(ep_id))
        elif isinstance(playlink2, list):
            for ep in playlink2:
                att = ep.get('_attributes', ep)
                ep_title = att.get('title', '')
                ep_id = att.get('id', '')
                if ep_id:
                    vodItems.append("第" + str(ep_title) + "集$" + str(ep_id))
        if not vodItems:
            cid = st.get('cid', '')
            if cid:
                try:
                    api_data = self._getDetailApi(str(cid))
                    if api_data:
                        v2 = api_data.get('v', {})
                        vl2 = v2.get('video_list', {})
                        pl2 = vl2.get('playlink2', [])
                        if isinstance(pl2, dict):
                            att = pl2.get('_attributes', pl2)
                            ep_title = att.get('title', title)
                            ep_id = att.get('id', '')
                            if ep_id:
                                vodItems.append(title + "$" + str(ep_id))
                        elif isinstance(pl2, list):
                            for ep in pl2:
                                att = ep.get('_attributes', ep)
                                ep_title = att.get('title', '')
                                ep_id = att.get('id', '')
                                if ep_id:
                                    vodItems.append("第" + str(ep_title) + "集$" + str(ep_id))
                except:
                    pass
        if not vodItems:
            vodItems.append(title + "$" + vod_id)
        joinStr = '#'.join(vodItems)
        vod = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": st.get('channelType', ''),
            "vod_year": str(year),
            "vod_area": str(area),
            "vod_remarks": str(remark),
            "vod_actor": str(actor),
            "vod_director": str(director),
            "vod_content": description
        }
        vod['vod_play_from'] = "$$$".join(vod_play_from)
        vod['vod_play_url'] = "$$$".join([joinStr])
        result = {'list': [vod]}
        return result

    def searchContent(self, key, quick):
        videos = []
        url = 'https://sou.pptv.com/s_video?kw={0}&context=default'.format(urllib.parse.quote(key))
        HtmlTxt = self.custom_webReadFile(url, self.header)
        pattern = r'href="(//v\.pptv\.com/show/([^"?]+)\.html)(?:\?[^"]*)?"'
        seen = set()
        for m in re.finditer(pattern, HtmlTxt, re.S):
            eid = m.group(2)
            if eid in seen:
                continue
            seen.add(eid)
            pos = m.start()
            context = HtmlTxt[max(0, pos - 300):pos + 800]
            title = ''
            img_m = re.search(r'(?:alt|title)="([^"]{2,40})"', context)
            if img_m:
                title = img_m.group(1).strip()
            if not title:
                span_m = re.search(r'class="[^"]*title[^"]*"[^>]*>([^<]+)', context)
                if span_m:
                    title = span_m.group(1).strip()
            if not title:
                title = eid
            pic = ''
            pic_m = re.search(r'<img[^>]*src="([^"]+)"', context)
            if pic_m:
                pic = pic_m.group(1)
                if pic.startswith('//'):
                    pic = 'https:' + pic
            remark = ''
            score_m = re.search(r'(\d+\.?\d*)\s*(?:分|score)', context)
            if score_m:
                remark = score_m.group(1)
            videos.append({
                "vod_id": eid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark
            })
        result = {'list': videos}
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 1
        result["playUrl"] = ''
        result["url"] = 'https://v.pptv.com/show/{0}.html'.format(id)
        result["header"] = self.header
        result["jx"] = 1
        return result

    config = {
        "player": {},
        "filter": {
            "movie": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "tv": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "cartoon": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "zongyi": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "kid": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "real": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ],
            "sports": [
                {"key": "sort", "name": "排序", "value": [{"n": "最新", "v": "new"}, {"n": "最热", "v": "hot"}]}
            ]
        }
    }
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.pptv.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    def localProxy(self, param):
        return [200, "video/MP2T", param, ""]

    # -----------------------------------------------自定义函数-----------------------------------------------

    def _getBasicInfo(self, eid):
        try:
            url = 'https://epg.api.pptv.com/detail.api?cb=cb&vid={0}&platform=web&ver=4&auth=web'.format(eid)
            r = self.custom_webReadFile(url, self.header)
            data = json.loads(r[r.index('(') + 1:r.rindex(')')])
            v = data.get('v', {})
            pic = v.get('sloturl', '') or v.get('imgurl', '')
            if pic and not pic.startswith('http'):
                pic = 'https:' + pic if pic.startswith('//') else pic
            return {
                'pic': pic,
                'mark': v.get('mark', ''),
                'year': v.get('year', ''),
                'area': v.get('area', ''),
                'title': v.get('title', '')
            }
        except:
            return None

    def _getDetailApi(self, cid):
        url = 'https://epg.api.pptv.com/detail.api?cb=cb&vid={0}&platform=web&ver=4&auth=web'.format(cid)
        r = self.custom_webReadFile(url, self.header)
        return json.loads(r[r.index('(') + 1:r.rindex(')')])

    def custom_webReadFile(self, urlStr, header=None, codeName='utf-8'):
        html = ''
        if header is None:
            header = {
                "Referer": urlStr,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36',
                "Host": self.custom_RegexGetText(Text=urlStr, RegexText=r'https*://(.*?)(/|$)', Index=1)
            }
        req = urllib.request.Request(url=urlStr, headers=header)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode(codeName, 'ignore')
        return html

    def custom_RegexGetText(self, Text, RegexText, Index):
        returnTxt = ""
        Regex = re.search(RegexText, Text, re.M | re.S)
        if Regex is None:
            returnTxt = ""
        else:
            returnTxt = Regex.group(Index)
        return returnTxt
