# -*- coding: utf-8 -*-
import requests
import json
import re
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 基础配置
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': self.host,
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.session = requests.Session()

    def homeContent(self, filter):
        # 1. 核心分类：根据网站当前导航结构精简
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "release", "type_name": "最新发行"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "uncensored-leak", "type_name": "无码流出"},
            {"type_id": "genres/uncensored", "type_name": "无码影片"},
            {"type_id": "genres/censored", "type_name": "有码影片"},
            {"type_id": "genres/VR", "type_name": "VR专区"},
            {"type_id": "genres/individual", "type_name": "个人单体"},
            {"type_id": "today-hot", "type_name": "今日热门"},
            {"type_id": "monthly-hot", "type_name": "本月热门"}
        ]
        
        # 首页默认加载“最近更新”的内容
        url = f"{self.host}{self.base_path}/new"
        try:
            res = self.session.get(url, headers=self.headers, timeout=15)
            doc = pq(res.content)
            vod_list = self.parse_list(doc)
        except:
            vod_list = []

        return {
            'class': classes,
            'list': vod_list,
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        # 兼容处理：tid 可能自带 genres/ 前缀
        url = f"{self.host}{self.base_path}/{tid}?page={pg}"
        
        res = self.session.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': int(pg),
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # 该站点的视频卡片选择器
        items = doc('.thumbnail').items()
        
        for item in items:
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): img = "https:" + img
            
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            if not href: continue
            
            # 提取 vod_id
            vod_id = href.rstrip('/').split('/')[-1]
            
            title = a_tag.attr('title') or item('h2').text() or "未知影片"
            remarks = item('.duration').text() or item('.absolute.
