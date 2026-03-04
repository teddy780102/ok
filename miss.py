# -*- coding: utf-8 -*-
import requests, json, re, time
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        self.host = config.get('site', 'https://missav.com')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host,
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

    def homeContent(self, filter):
        # 增加分类和初始列表
        res = requests.get(f"{self.host}/cn/new", headers=self.headers, timeout=10)
        doc = pq(res.content)
        
        # 动态获取分类示例
        classes = [
            {"type_id": "cn/new", "type_name": "最近更新"},
            {"type_id": "cn/release", "type_name": "新片发布"},
            {"type_id": "cn/hot", "type_name": "今日热门"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/{tid}?page={pg}"
        res = requests.get(url, headers=self.headers, timeout=10)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': pg,
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # 这里的选择器需要根据网站最新HTML结构微调
        for item in doc('.thumbnail').items():
            img = item('img').attr('data-src') or item('img').attr('src')
            title = item('.text-secondary').text() or item('a').attr('title')
            href = item('a').attr('href')
            if href:
                videos.append({
                    "vod_id": href.split('/')[-1],
                    "vod_name": title,
                    "vod_pic": img,
                    "vod_remarks": item('.absolute.bottom-1').text(),
                    "style": {"type": "rect", "ratio": 1.33}
                })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        url = f"{self.host}/{mid}"
        res = requests.get(url, headers=self.headers, timeout=10)
        doc = pq(res.content)
        
        # 核心：寻找播放地址
        # 现代网站通常将地址藏在 window.__INITIAL_STATE__ 或 eval 混淆中
        script_text = doc('script').text()
        play_url = ""
        
        # 尝试匹配 m3u8 地址
        m3u8_match = re.search(r'source\s*=\s*[\'"](https?://.*?\.m3u8.*?)[\'"]', script_text)
        if m3u8_match:
            play_url = m3u8_match.group(1)
        else:
            # 如果没找到，退而求其次使用网页嗅探
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text(),
            "vod_pic": doc('video').attr('poster'),
            "vod_type": "影片详情",
            "vod_content": doc('.text-secondary.break-all').text(),
            "vod_play_from": "MissAV",
            "vod_play_url": f"点击播放${play_url}"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/cn/search/{key}?page={pg}"
        res = requests.get(url, headers=self.headers, timeout=10)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        # 简单的播放解析返回
        return {
            "parse": 0 if "m3u8" in id else 1,
            "url": id,
            "header": self.headers
        }
