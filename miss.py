# -*- coding: utf-8 -*-
import json
import re
import cloudscraper  # 如果报错，请运行: pip install cloudscraper
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        # 使用 cloudscraper 替代标准 requests
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': self.host,
        }

    def homeContent(self, filter):
        url = f"{self.host}{self.base_path}/new"
        res = self.scraper.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        # 静态分类保障（防止动态抓取被拦截）
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "release", "type_name": "最新发行"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "uncensored-leak", "type_name": "无码流出"},
            {"type_id": "genres/uncensored", "type_name": "无码影片"},
            {"type_id": "genres/censored", "type_name": "有码影片"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}{self.base_path}/{tid}?page={pg}"
        res = self.scraper.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': int(pg),
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # MissAV 的视频块通常在 .thumbnail 或类似结构的 div 中
        items = doc('.thumbnail, .video-item').items()
        
        for item in items:
            # 1. 图片处理
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): img = "https:" + img
            
            # 2. 链接与 ID
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            if not href: continue
            
            # 提取 ID (兼容绝对路径和相对路径)
            vod_id = href.rstrip('/').split('/')[-1]
            
            # 3. 标题
            title = a_tag.attr('title') or item('h2').text() or item('.text-secondary').text()
            
            # 4. 备注 (时长)
            remarks = item('.duration').text() or item('.absolute.bottom-1').text()
            
            videos.append({
                "vod_id": vod_id,
                "vod_name": title.strip() if title else "未知标题",
                "vod_pic": img,
                "vod_remarks": remarks.strip() if remarks else "",
            })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        url = f"{self.host}/{mid}"
        res = self.scraper.get(url, headers=self.headers, timeout=15)
        html = res.text
        doc = pq(html)
        
        # 提取 m3u8
        play_url = ""
        m1 = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html)
        if m1:
            play_url = m1.group(1)
        else:
            # 备选提取逻辑：尝试从混淆脚本中提取
            m2 = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html)
            if m2:
                from urllib.parse import unquote
                play_url = unquote(m2.group(0))

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip(),
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放${play_url if play_url else '嗅探$' + url}",
            "vod_content": doc('.text-secondary.break-all').text().strip()
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = self.scraper.get(url, headers=self.headers, timeout=15)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        # 这里的 id 可能是 m3u8 或 嗅探$url
        url = id.split('$')[-1]
        return {
            "parse": 0 if "m3u8" in url else 1,
            "url": url,
            "header": json.dumps(self.headers)
        }
