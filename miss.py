# -*- coding: utf-8 -*-
import json
import re
import cloudscraper  # 必须安装这个库
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 实时检查域名是否变动
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        
        # 创建一个带有浏览器指纹的爬取器
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
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def homeContent(self, filter):
        # 强制访问一次首页，建立会话
        url = f"{self.host}{self.base_path}/new"
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=20)
            if res.status_code != 200:
                return {"class": [], "list": [], "msg": f"错误代码: {res.status_code}"}
            
            doc = pq(res.content)
            
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
        except Exception as e:
            return {"class": [], "list": [], "msg": str(e)}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}{self.base_path}/{tid}?page={pg}"
        res = self.scraper.get(url, headers=self.headers, timeout=20)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': int(pg),
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # 针对该站点的 HTML 结构精准定位
        items = doc('.thumbnail').items()
        for item in items:
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): img = "https:" + img
            
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            if not href: continue
            
            vod_id = href.rstrip('/').split('/')[-1]
            title = a_tag.attr('title') or item('h2').text() or "未知影片"
            remarks = item('.duration').text() or item('.absolute.bottom-1').text() or ""
            
            videos.append({
                "vod_id": vod_id,
                "vod_name": title.strip(),
                "vod_pic": img,
                "vod_remarks": remarks.strip(),
            })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        url = f"{self.host}/{mid}"
        res = self.scraper.get(url, headers=self.headers, timeout=20)
        html = res.text
        doc = pq(html)
        
        # 提取 m3u8
        play_url = ""
        m1 = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html)
        m2 = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html)
        
        if m1:
            play_url = m1.group(1)
        elif m2:
            from urllib.parse import unquote
            play_url = unquote(m2.group(0))
        else:
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip(),
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_actor": doc('a[href*="actors"]').text(),
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放列表${play_url}",
            "vod_content": doc('.text-secondary.break-all').text().strip()
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = self.scraper.get(url, headers=self.headers, timeout=20)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        actual_url = id.split('$')[-1]
        return {
            "parse": 0 if "m3u8" in actual_url else 1,
            "url": actual_url,
            "header": json.dumps(self.headers)
