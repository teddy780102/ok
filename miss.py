# -*- coding: utf-8 -*-
import requests
import json
import re
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 目标站
        self.host = config.get('site', 'https://missav.ws/dm223/en').rstrip('/')
        self.base_path = "/dm194/cn"
        
        # 模拟高权重浏览器 Header
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': f"{self.host}/",
            'Connection': 'keep-alive'
        }
        # 使用 Session 自动维持 Cookie
        self.session = requests.Session()

    def homeContent(self, filter):
        # 增加一次对根目录的访问，获取初始 Cookie
        try:
            self.session.get(self.host, headers=self.headers, timeout=10)
        except:
            pass
            
        url = f"{self.host}{self.base_path}/new"
        res = self.session.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        # 固定分类，确保即使动态抓取失败也有菜单
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "release", "type_name": "最新发行"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "uncensored-leak", "type_name": "无码流出"},
            {"type_id": "genres/uncensored", "type_name": "无码影片"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
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
        # MissAV 列表页关键容器：.thumbnail
        # 有时在镜像站中会变为 a.block 或其他，这里做多重兼容
        items = doc('.thumbnail, .video-item').items()
        
        for item in items:
            # 1. 封面图 (处理延迟加载)
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): img = "https:" + img
            
            # 2. 详情链接
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            if not href: continue
            
            # 3. 提取唯一标识 ID
            vod_id = href.rstrip('/').split('/')[-1]
            
            # 4. 标题与备注
            title = a_tag.attr('title') or item('h2').text() or "未知标题"
            remarks = item('.duration').text() or item('.absolute.bottom-1').text()
            
            videos.append({
                "vod_id": vod_id,
                "vod_name": title.strip(),
                "vod_pic": img,
                "vod_remarks": remarks.strip() if remarks else ""
            })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        # 详情页路径：注意有的镜像站需要加 /cn/
        url = f"{self.host}/{mid}"
        res = self.session.get(url, headers=self.headers, timeout=15)
        html = res.text
        doc = pq(html)
        
        # 匹配播放地址
        play_url = ""
        # 模式1：直接 source 定义
        m1 = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html)
        # 模式2：JSON 混淆
        m2 = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html)
        
        if m1:
            play_url = m1.group(1)
        elif m2:
            from urllib.parse import unquote
            play_url = unquote(m2.group(0))
        else:
            # 如果正则表达式抓不到，返回给壳子进行网页嗅探
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip() or "未知影片",
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放链接${play_url}",
            "vod_content": doc('.text-secondary.break-all').text().strip() or "暂无简介"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = self.session.get(url, headers=self.headers, timeout=15)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        actual_url = id.split('$')[-1]
        # 播放时也必须携带 Headers，特别是 Referer
        return {
            "parse": 0 if "m3u8" in actual_url else 1,
            "url": actual_url,
            "header": json.dumps(self.headers)
        }

