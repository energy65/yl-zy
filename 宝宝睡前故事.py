# coding=utf-8
# !/usr/bin/python
from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os
sys.path.append('..')
xurl = "https://vyourtime.com"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }
headers = {
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'lang': 'zh',
    'origin': 'https://beddystories.com',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://beddystories.com/',
    'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
           }
class Spider(Spider):
    def getName(self):
        return "宝宝睡前故事"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [
    {"type_id": "fairy-tales", "type_name": "童话故事"},
    {"type_id": "fable", "type_name": "寓言故事"},
    {"type_id": "fantasy", "type_name": "奇幻冒险"},
    {"type_id": "bedtime", "type_name": "睡前短篇"},
    {"type_id": "folk", "type_name": "民间传说"},
    {"type_id": "education", "type_name": "成长教育"},
    {"type_id": "science", "type_name": "科普启蒙"}
    ],
    }
        return result
    def homeVideoContent(self):
        pass
    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        page = int(pg) if pg else 1

        json_data = {
            'page': str(page),
            'searchKey': 'type',
            'searchValue': cid,
                    }

        urlz = f'{xurl}/api/story/category'
        response = requests.post(url=urlz, headers=headers, json=json_data)
        response_data = response.json()

        for vod in response_data['data']['list']:

            id = vod['urlSlug']
            if len(id) >= 3 and id[-3:].isdigit():
                pass
            else:
                continue

            name = vod['title']

            pic = vod['coverImage']

            remark = vod.get('createTime', '暂无备注')

            video = {
                "vod_id": id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark
                    }
            videos.append(video)

        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        did = ids[0]
        result = {}
        videos = []
    
        json_data = {}

        urlz = f'{xurl}/api/story/query/{did}'
        response = requests.post(url=urlz, headers=headers, json=json_data)
        response_data = response.json()

        content =  response_data.get('data', {}).get('content', '')
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'\n\s*\n', '\n', content).strip().replace('\n', '')

        director = response_data.get('data', {}).get('title', '')

        actor = response_data.get('data', {}).get('storyTypeName', '')

        remarks = response_data.get('data', {}).get('ageRangeName', '')

        year = response_data.get('data', {}).get('createTime', '')

        area = response_data.get('data', {}).get('countryCodeName', '')

        bofang = response_data['data']['audio']

        videos.append({
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": "宝宝专线",
            "vod_play_url": bofang
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):

        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = id
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, pg):
        pass

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None











