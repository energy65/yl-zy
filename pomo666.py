"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'Pomo666',
  lang: 'hipy',
})
"""

# -*- coding: utf-8 -*-
import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://pomo.mom"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
        }

    def getName(self):
        return "Pomo666"

    def homeContent(self, filter):
        classes = [
            {"type_id": "home", "type_name": "全部电影"},
            {"type_id": "huayurm", "type_name": "华语热门"},
            {"type_id": "jiating", "type_name": "家庭影院"},
            {"type_id": "donghuadadiany", "type_name": "动画大电影"},
            {"type_id": "lengmenjiapian", "type_name": "冷门佳片"},
            {"type_id": "paihangbang", "type_name": "TOP250"},
            {"type_id": "sort/12", "type_name": "蓝光原盘"},
            {"type_id": "dianshiju", "type_name": "剧集"},
            {"type_id": "sort/10", "type_name": "待更新"},
            {"type_id": "sort/5", "type_name": "短片"},
            {"type_id": "sort/13", "type_name": "演唱会"},
            {"type_id": "doc", "type_name": "纪录片"},
        ]

        filters = {
            "home": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "huayurm": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "jiating": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "donghuadadiany": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "lengmenjiapian": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "paihangbang": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "sort/12": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "dianshiju": self._get_filter_config("剧集类型", "首播年份", "剧集地区", "语言", "最新首播"),
            "sort/10": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "sort/5": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "sort/13": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
            "doc": self._get_filter_config("影片类型", "上映年份", "上映地区", "语言", "最新上映"),
        }

        return {"class": classes, "filters": filters}

    def _get_filter_config(self, type_label, year_label, area_label, lang_label, sort_label):
        return [
            {
                "key": "type",
                "name": type_label,
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "传记", "v": "传记"},
                    {"n": "儿童", "v": "儿童"},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "剧情", "v": "剧情"},
                    {"n": "动作", "v": "动作"},
                    {"n": "动画", "v": "动画"},
                    {"n": "历史", "v": "历史"},
                    {"n": "古装", "v": "古装"},
                    {"n": "同性", "v": "同性"},
                    {"n": "喜剧", "v": "喜剧"},
                    {"n": "奇幻", "v": "奇幻"},
                    {"n": "家庭", "v": "家庭"},
                    {"n": "恐怖", "v": "恐怖"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "战争", "v": "战争"},
                    {"n": "歌舞", "v": "歌舞"},
                    {"n": "武侠", "v": "武侠"},
                    {"n": "灾难", "v": "灾难"},
                    {"n": "爱情", "v": "爱情"},
                    {"n": "犯罪", "v": "犯罪"},
                    {"n": "真人秀", "v": "真人秀"},
                    {"n": "短片", "v": "短片"},
                    {"n": "悬疑", "v": "悬疑"},
                    {"n": "情色", "v": "情色"},
                    {"n": "惊悚", "v": "惊悚"},
                    {"n": "戏曲", "v": "戏曲"},
                    {"n": "音乐", "v": "音乐"},
                    {"n": "科幻", "v": "科幻"},
                    {"n": "纪录片", "v": "纪录片"},
                    {"n": "运动", "v": "运动"},
                    {"n": "西部", "v": "西部"},
                ]
            },
            {
                "key": "year",
                "name": year_label,
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"},
                    {"n": "2008", "v": "2008"},
                    {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"},
                    {"n": "2005", "v": "2005"},
                    {"n": "2004", "v": "2004"},
                    {"n": "2003", "v": "2003"},
                    {"n": "2002", "v": "2002"},
                    {"n": "2001", "v": "2001"},
                    {"n": "2000", "v": "2000"},
                ]
            },
            {
                "key": "area",
                "name": area_label,
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "亚洲", "v": "亚洲"},
                    {"n": "海外", "v": "海外"},
                    {"n": "欧美", "v": "欧美"},
                    {"n": "美国", "v": "美国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"},
                    {"n": "西班牙", "v": "西班牙"},
                    {"n": "意大利", "v": "意大利"},
                    {"n": "俄罗斯", "v": "俄罗斯"},
                    {"n": "印度", "v": "印度"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "加拿大", "v": "加拿大"},
                    {"n": "澳大利亚", "v": "澳大利亚"},
                    {"n": "巴西", "v": "巴西"},
                    {"n": "其他", "v": "其他"},
                ]
            },
            {
                "key": "lang",
                "name": lang_label,
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "汉语普通话", "v": "汉语普通话"},
                    {"n": "国语", "v": "国语"},
                    {"n": "英语", "v": "英语"},
                    {"n": "法语", "v": "法语"},
                    {"n": "粤语", "v": "粤语"},
                    {"n": "日语", "v": "日语"},
                    {"n": "韩语", "v": "韩语"},
                    {"n": "泰语", "v": "泰语"},
                    {"n": "德语", "v": "德语"},
                    {"n": "俄语", "v": "俄语"},
                    {"n": "闽南语", "v": "闽南语"},
                    {"n": "丹麦语", "v": "丹麦语"},
                    {"n": "波兰语", "v": "波兰语"},
                    {"n": "瑞典语", "v": "瑞典语"},
                    {"n": "印地语", "v": "印地语"},
                    {"n": "挪威语", "v": "挪威语"},
                    {"n": "意大利语", "v": "意大利语"},
                    {"n": "西班牙语", "v": "西班牙语"},
                    {"n": "无对白", "v": "无对白"},
                ]
            },
            {
                "key": "sort",
                "name": sort_label,
                "value": [
                    {"n": "最新", "v": "new"},
                    {"n": "最早", "v": "old"},
                    {"n": "评分", "v": "rating"},
                ]
            }
        ]

    def homeVideoContent(self):
        try:
            html = self._fetch("/")
            items = self._parse_list(html)
            return {"list": items[:24]}
        except Exception as e:
            return {"list": []}

    def _fetch(self, url):
        try:
            if not url.startswith("http"):
                url = self.host + url
            rsp = self.fetch(url, headers=self.headers)
            return rsp.text if rsp else ""
        except Exception as e:
            print(f"fetch error: {e}")
            return ""

    def _parse_list(self, html):
        items = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            selectors = [
                "a[href*='/']",
                ".movie-item a",
                ".video-item a",
                ".item a",
                ".card a",
                "article a",
            ]
            
            found_links = []
            for selector in selectors:
                try:
                    found_links.extend(soup.select(selector))
                except:
                    pass
            
            if not found_links:
                found_links = soup.find_all("a", href=True)
            
            for a_tag in found_links:
                href = a_tag.get("href", "")
                
                m = re.search(r'pomo\.mom/(\d+)$', href) or re.search(r'^/(\d+)$', href)
                if not m:
                    continue
                    
                vid = m.group(1)
                
                img = a_tag.find("img")
                if not img:
                    continue
                    
                title = img.get("alt", "") or img.get("title", "") or a_tag.get("title", "") or ""
                pic = img.get("src", "") or img.get("data-src", "") or img.get("data-original", "") or ""
                
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                
                remarks = ""
                tag_elem = a_tag.find(class_=re.compile(r'tag|badge|rating|quality|label|mark', re.I))
                if tag_elem:
                    remarks = tag_elem.get_text(strip=True)
                
                if not remarks:
                    span_elems = a_tag.find_all(["span", "div", "p"])
                    for span_elem in span_elems:
                        text = span_elem.get_text(strip=True)
                        if text and len(text) < 30 and ("IMDB" in text or "HD" in text or "4K" in text or "Dolby" in text or "HDR" in text or "Web" in text or "WEB" in text):
                            remarks = text
                            break
                
                if not title:
                    h_elem = a_tag.find(["h3", "h4", "h5", "strong", "b"])
                    if h_elem:
                        title = h_elem.get_text(strip=True)
                
                if title and vid:
                    title = re.sub(r'\(\d{4}\)', '', title).strip()
                    items.append({
                        "vod_id": vid,
                        "vod_name": title.strip(),
                        "vod_pic": pic.strip(),
                        "vod_remarks": remarks.strip(),
                    })
            
            seen = set()
            unique_items = []
            for item in items:
                if item["vod_id"] not in seen:
                    seen.add(item["vod_id"])
                    unique_items.append(item)
            
            return unique_items
        except Exception as e:
            print(f"parse list error: {e}")
            return items

    def _get_page_count(self, html):
        try:
            soup = BeautifulSoup(html, "html.parser")
            pages = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                pm = re.search(r'page/(\d+)', href)
                if pm:
                    try:
                        pages.append(int(pm.group(1)))
                    except:
                        pass
            if pages:
                return max(pages)
            return 1
        except:
            return 1

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if pg and str(pg).isdigit() else 1
            
            type_val = extend.get("type", "") if extend else ""
            year_val = extend.get("year", "") if extend else ""
            area_val = extend.get("area", "") if extend else ""
            lang_val = extend.get("lang", "") if extend else ""
            sort_val = extend.get("sort", "new") if extend else "new"
            
            if tid == "home":
                base_url = "/"
            elif tid == "doc":
                base_url = "/"
                if not type_val:
                    type_val = "纪录片"
            else:
                base_url = f"/{tid}"
            
            params = []
            if type_val:
                params.append(f"genre={urllib.parse.quote(type_val)}")
            if year_val:
                params.append(f"year={year_val}")
            if area_val:
                params.append(f"area={urllib.parse.quote(area_val)}")
            if lang_val:
                params.append(f"lang={urllib.parse.quote(lang_val)}")
            if sort_val:
                params.append(f"order={sort_val}")
            
            query_string = "&".join(params) if params else ""
            
            if tid == "home" and not query_string:
                if pg <= 1:
                    url = "/"
                else:
                    url = f"/page/{pg}"
            elif tid == "doc":
                if pg <= 1:
                    url = "/?genre=" + urllib.parse.quote("纪录片")
                else:
                    url = f"/page/{pg}?genre=" + urllib.parse.quote("纪录片")
                if query_string:
                    url = url + "&" + query_string
            else:
                if pg <= 1:
                    url = base_url
                else:
                    url = f"{base_url}/page/{pg}"
                
                if query_string:
                    sep = "?" if "?" not in url else "&"
                    url = f"{url}{sep}{query_string}"
            
            html = self._fetch(url)
            items = self._parse_list(html)
            page_count = self._get_page_count(html)
            
            if page_count < pg and len(items) > 0:
                page_count = pg
            
            return {"page": pg, "pagecount": page_count, "limit": 24, "total": 9999, "list": items}
        except Exception as e:
            print(f"category error: {e}")
            return {"page": pg, "pagecount": 1, "limit": 24, "total": 0, "list": []}

    def detailContent(self, ids):
        try:
            if isinstance(ids, list):
                ids = ids[0]
            
            html = self._fetch(f"/{ids}")
            if not html:
                return {"list": []}
            
            soup = BeautifulSoup(html, "html.parser")
            
            title = ""
            title_el = soup.find("h2") or soup.find("h1") or soup.find("title")
            if title_el:
                title = title_el.get_text(strip=True)
                title = re.sub(r' - 4K原盘免费下载$', '', title).strip()
            
            pic = ""
            img_el = soup.find("img", class_=re.compile(r'poster|banner|cover', re.I))
            if not img_el:
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    alt = img.get("alt", "")
                    if title and alt and title[:5] in alt:
                        pic = src
                        break
                    if src and ("pomo" in src or "cdn" in src or "image" in src):
                        if not pic:
                            pic = src
            
            if pic and pic.startswith("//"):
                pic = "https:" + pic
            
            desc = ""
            desc_el = None
            for h3 in soup.find_all(["h3", "h2", "h4"]):
                if "剧情" in h3.get_text() or "简介" in h3.get_text():
                    next_elem = h3.find_next_sibling()
                    if next_elem:
                        desc_el = next_elem
                        break
            
            if desc_el:
                desc = desc_el.get_text("\n", strip=True)
            else:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        desc = text
                        break
            
            year = ""
            director = ""
            actor = ""
            area = ""
            lang = ""
            vod_type = ""
            
            year_match = re.search(r'(\d{4})', title)
            if year_match:
                year = year_match.group(1)
            
            meta_text = soup.get_text(" ", strip=True)
            
            for keyword in ["导演", "执导"]:
                pattern = rf'{keyword}[：:]\s*([^\n\r]+?)(?:\s{{2,}}|演员|主演|地区|语言|类型|年份|上映|首播|$)'
                m = re.search(pattern, meta_text)
                if m:
                    director = m.group(1).strip()
                    break
            
            for keyword in ["主演", "演员"]:
                pattern = rf'{keyword}[：:]\s*([^\n\r]+?)(?:\s{{2,}}|导演|地区|语言|类型|年份|上映|首播|$)'
                m = re.search(pattern, meta_text)
                if m:
                    actor = m.group(1).strip()
                    break
            
            m_area = re.search(r'(?:地区|产地|国家)[：:]\s*([^\n\r]+?)(?:\s{2,}|导演|演员|语言|类型|年份|$)', meta_text)
            if m_area:
                area = m_area.group(1).strip()
            
            m_lang = re.search(r'语言[：:]\s*([^\n\r]+?)(?:\s{2,}|导演|演员|地区|类型|年份|$)', meta_text)
            if m_lang:
                lang = m_lang.group(1).strip()
            
            m_type = re.search(r'类型[：:]\s*([^\n\r]+?)(?:\s{2,}|导演|演员|地区|语言|年份|$)', meta_text)
            if m_type:
                vod_type = m_type.group(1).strip()
            
            play_from_list = []
            play_url_list = []
            
            play_html = self._fetch(f"/?plugin=plyr_player&gid={ids}")
            if play_html:
                route1 = re.findall(r'route1Data\s*=\s*\[([^\]]+)\]', play_html)
                route2 = re.findall(r'route2Data\s*=\s*\[([^\]]+)\]', play_html)
                
                if route1:
                    ep_list = self._parse_route_data(route1[0])
                    if ep_list:
                        play_from_list.append("线路1")
                        play_url_list.append("#".join(ep_list))
                
                if route2:
                    ep_list = self._parse_route_data(route2[0])
                    if ep_list:
                        play_from_list.append("线路2")
                        play_url_list.append("#".join(ep_list))
            
            vod_play_from = "$$$".join(play_from_list) if play_from_list else "Pomo在线"
            vod_play_url = "$$$".join(play_url_list) if play_url_list else f"在线播放${ids}"
            
            return {"list": [{
                "vod_id": ids,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": year,
                "vod_director": director,
                "vod_actor": actor,
                "vod_area": area,
                "vod_lang": lang,
                "vod_content": desc,
                "vod_type": vod_type,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            }]}
        except Exception as e:
            print(f"detail error: {e}")
            return {"list": []}

    def _parse_route_data(self, route_str):
        ep_list = []
        try:
            items = re.findall(r'"([^"]*)"', route_str)
            for item in items:
                item = item.replace('\\/', '/')
                try:
                    item = item.encode('utf-8').decode('unicode_escape')
                except:
                    pass
                parts = item.split("$", 1)
                if len(parts) == 2:
                    ep_name = parts[0] or "播放"
                    ep_url = parts[1]
                    ep_list.append(f"{ep_name}${ep_url}")
                elif len(parts) == 1 and parts[0].startswith("http"):
                    ep_list.append(f"播放${parts[0]}")
        except Exception as e:
            print(f"parse route error: {e}")
        return ep_list

    def playerContent(self, flag, id, vipFlags):
        try:
            vid = id
            if ":" in id:
                vid = id.split(":")[0]
            
            if id.startswith("http"):
                return {"parse": 0, "url": id, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"}}
            
            play_html = self._fetch(f"/?plugin=plyr_player&gid={vid}")
            if not play_html:
                return {"parse": 0, "url": ""}
            
            route_data = None
            if flag == "线路2":
                m = re.search(r'route2Data\s*=\s*\[([^\]]+)\]', play_html)
            else:
                m = re.search(r'route1Data\s*=\s*\[([^\]]+)\]', play_html)
            
            if m:
                items = re.findall(r'"([^"]*)"', m.group(1))
                for item in items:
                    item = item.replace('\\/', '/')
                    try:
                        item = item.encode('utf-8').decode('unicode_escape')
                    except:
                        pass
                    parts = item.split("$", 1)
                    if len(parts) == 2:
                        url = parts[1]
                        if url.startswith("http"):
                            return {"parse": 0, "url": url, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"}}
                    elif len(parts) == 1 and parts[0].startswith("http"):
                        return {"parse": 0, "url": parts[0], "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"}}
            
            return {"parse": 0, "url": ""}
        except Exception as e:
            print(f"player error: {e}")
            return {"parse": 0, "url": ""}

    def searchContent(self, key, quick, pg="1"):
        try:
            wd = urllib.parse.quote(key)
            pg = int(pg) if pg and str(pg).isdigit() else 1
            
            if pg <= 1:
                url = f"/?s={wd}"
            else:
                url = f"/page/{pg}?s={wd}"
            
            html = self._fetch(url)
            items = self._parse_list(html)
            page_count = self._get_page_count(html)
            
            return {"list": items, "page": pg, "pagecount": page_count, "limit": 24, "total": 9999}
        except Exception as e:
            print(f"search error: {e}")
            return {"list": []}

    def localProxy(self, param=''):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False
