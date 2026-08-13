#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乌云影视 TVBox 爬虫
网站: https://wooyun.tv/
作者: 源力软件汇
QQ群: 1054592152
"""
import json
import re
import urllib.request
import urllib.parse
import ssl

# 禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context

# 推广信息
PROMO_INFO = """

═══════════════════════════════════════
【源力软件汇】微信公众号
QQ群: 1054592152
更多优质资源尽在源力！
═══════════════════════════════════════"""


class Spider:
    def __init__(self):
        self.siteUrl = "https://wooyun.tv"
        
    def getName(self):
        return "乌云影视"
    
    def init(self, extend=""):
        pass
    
    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url
    
    def manualVideoCheck(self):
        pass
    
    def getDependence(self):
        return []
    
    def homeContent(self, filter):
        result = {}
        classes = []
        
        # 分类
        classes.append({"type_id": "movie", "type_name": "电影"})
        classes.append({"type_id": "tv_series", "type_name": "电视剧"})
        classes.append({"type_id": "anime", "type_name": "动漫"})
        classes.append({"type_id": "variety", "type_name": "综艺"})
        
        result["class"] = classes
        
        # 筛选
        if filter:
            result["filters"] = self.getFilter()
        
        return result
    
    def getFilter(self):
        filters = {}
        
        # 电影筛选
        filters["movie"] = [
            {"key": "type", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "动作", "v": "动作"},
                {"n": "喜剧", "v": "喜剧"},
                {"n": "爱情", "v": "爱情"},
                {"n": "科幻", "v": "科幻"},
                {"n": "恐怖", "v": "恐怖"},
                {"n": "剧情", "v": "剧情"},
                {"n": "战争", "v": "战争"},
                {"n": "犯罪", "v": "犯罪"},
                {"n": "冒险", "v": "冒险"},
                {"n": "奇幻", "v": "奇幻"},
                {"n": "悬疑", "v": "悬疑"},
                {"n": "惊悚", "v": "惊悚"},
                {"n": "动画", "v": "动画"},
            ]},
            {"key": "area", "name": "地区", "value": [
                {"n": "全部", "v": ""},
                {"n": "大陆", "v": "大陆"},
                {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"},
                {"n": "美国", "v": "美国"},
                {"n": "韩国", "v": "韩国"},
                {"n": "日本", "v": "日本"},
                {"n": "泰国", "v": "泰国"},
                {"n": "印度", "v": "印度"},
                {"n": "英国", "v": "英国"},
                {"n": "法国", "v": "法国"},
                {"n": "德国", "v": "德国"},
            ]},
            {"key": "year", "name": "年份", "value": [
                {"n": "全部", "v": ""},
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
            ]},
        ]
        
        # 电视剧筛选
        filters["tv_series"] = [
            {"key": "type", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "国产剧", "v": "国产"},
                {"n": "韩剧", "v": "韩剧"},
                {"n": "日剧", "v": "日剧"},
                {"n": "美剧", "v": "美剧"},
                {"n": "泰剧", "v": "泰剧"},
                {"n": "台剧", "v": "台剧"},
                {"n": "港剧", "v": "港剧"},
                {"n": "动作", "v": "动作"},
                {"n": "爱情", "v": "爱情"},
                {"n": "古装", "v": "古装"},
                {"n": "悬疑", "v": "悬疑"},
                {"n": "犯罪", "v": "犯罪"},
                {"n": "剧情", "v": "剧情"},
                {"n": "喜剧", "v": "喜剧"},
            ]},
            {"key": "area", "name": "地区", "value": [
                {"n": "全部", "v": ""},
                {"n": "大陆", "v": "大陆"},
                {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"},
                {"n": "美国", "v": "美国"},
                {"n": "韩国", "v": "韩国"},
                {"n": "日本", "v": "日本"},
                {"n": "泰国", "v": "泰国"},
            ]},
            {"key": "year", "name": "年份", "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
                {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"},
            ]},
        ]
        
        # 动漫筛选
        filters["anime"] = [
            {"key": "type", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "国产动漫", "v": "国产"},
                {"n": "日本动漫", "v": "日本"},
                {"n": "欧美动漫", "v": "欧美"},
                {"n": "动作", "v": "动作"},
                {"n": "冒险", "v": "冒险"},
                {"n": "奇幻", "v": "奇幻"},
                {"n": "科幻", "v": "科幻"},
                {"n": "喜剧", "v": "喜剧"},
                {"n": "剧情", "v": "剧情"},
            ]},
            {"key": "area", "name": "地区", "value": [
                {"n": "全部", "v": ""},
                {"n": "大陆", "v": "大陆"},
                {"n": "日本", "v": "日本"},
                {"n": "美国", "v": "美国"},
                {"n": "韩国", "v": "韩国"},
            ]},
            {"key": "year", "name": "年份", "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
            ]},
        ]
        
        # 综艺筛选
        filters["variety"] = [
            {"key": "type", "name": "类型", "value": [
                {"n": "全部", "v": ""},
                {"n": "真人秀", "v": "真人秀"},
                {"n": "脱口秀", "v": "脱口秀"},
                {"n": "音乐", "v": "音乐"},
                {"n": "舞蹈", "v": "舞蹈"},
                {"n": "美食", "v": "美食"},
                {"n": "旅行", "v": "旅行"},
                {"n": "搞笑", "v": "搞笑"},
            ]},
            {"key": "area", "name": "地区", "value": [
                {"n": "全部", "v": ""},
                {"n": "大陆", "v": "大陆"},
                {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"},
                {"n": "韩国", "v": "韩国"},
                {"n": "日本", "v": "日本"},
                {"n": "美国", "v": "美国"},
            ]},
            {"key": "year", "name": "年份", "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
            ]},
        ]
        
        return filters
    
    def homeVideoContent(self):
        """首页推荐"""
        videos = []
        try:
            url = self.siteUrl
            html = self.fetchHtml(url)
            videos = self.parseVideoList(html)
        except:
            pass
        return {"list": videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        videos = []
        try:
            url = f"{self.siteUrl}/sec/{tid}?page={pg}"
            if extend:
                for key, value in extend.items():
                    if value:
                        url += f"&{key}={urllib.parse.quote(value)}"
            
            html = self.fetchHtml(url)
            videos = self.parseVideoList(html)
        except:
            pass
        
        return {
            "page": pg,
            "pagecount": 999,
            "limit": 90,
            "total": 99999,
            "list": videos
        }
    
    def detailContent(self, ids):
        """详情内容"""
        vid = ids[0]
        try:
            url = f"{self.siteUrl}/play/{vid}"
            html = self.fetchHtml(url)
            detail = self.parseVideoDetail(html, vid)
            return {"list": [detail]}
        except:
            return {"list": []}
    
    def searchContent(self, key, quick):
        """搜索内容"""
        videos = []
        try:
            url = f"{self.siteUrl}/search?q={urllib.parse.quote(key)}"
            html = self.fetchHtml(url)
            videos = self.parseVideoList(html)
        except:
            pass
        return {"list": videos}
    
    def playerContent(self, flag, id, vipFlags):
        """播放内容"""
        return {
            "parse": 1,
            "playUrl": "",
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
    
    def fetchHtml(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=30)
        return response.read().decode('utf-8')
    
    def parseVideoList(self, html):
        videos = []
        if not html:
            return videos
        
        # 匹配视频卡片
        pattern = r'<a[^>]*href="/play/(\d+)"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*>.*?<h[1-6][^>]*>(.*?)</h[1-6]>.*?<span[^>]*>(.*?)</span>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            vid, pic, title, status = match
            title = re.sub(r'<[^>]+>', '', title).strip()
            status = re.sub(r'<[^>]+>', '', status).strip()
            
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic if pic.startswith('http') else f"https://wooyunstatic.oss-ap-southeast-1.aliyuncs.com/static/images/poster-default.svg",
                "vod_remarks": status
            })
        
        return videos
    
    def parseVideoDetail(self, html, vid):
        detail = {
            "vod_id": vid,
            "vod_name": "",
            "vod_pic": "",
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "",
            "vod_play_url": ""
        }
        
        # 提取标题
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if title_match:
            detail["vod_name"] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        # 提取简介
        desc_match = re.search(r'简介[:：]\s*</span>\s*<p[^>]*>(.*?)</p>', html, re.DOTALL)
        if desc_match:
            desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            detail["vod_content"] = desc + PROMO_INFO
        else:
            detail["vod_content"] = PROMO_INFO
        
        # 提取播放链接
        play_matches = re.findall(r'href="/play/' + vid + r'--(\d+)"', html)
        if play_matches:
            episodes = []
            for ep in sorted(set(play_matches), key=int):
                episodes.append(f"第{ep}集${self.siteUrl}/play/{vid}--{ep}")
            detail["vod_play_from"] = "乌云影视"
            detail["vod_play_url"] = "#".join(episodes)
        else:
            detail["vod_play_from"] = "乌云影视"
            detail["vod_play_url"] = f"正片${self.siteUrl}/play/{vid}"
        
        return detail


# TVBox 入口
spider = Spider()

def getSpider():
    return spider
