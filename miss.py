# -*- coding: utf-8 -*-
import requests
import json
import re
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 默认使用 missav.ws，如果失效可在配置中更换为 .com 或 .ai
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        
        # 模拟高权重浏览器请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': f"{self.host}/",
            'Connection': 'keep-alive'
        }
        # 保持会话以应对 Cookie 验证
        self.session = requests.Session()

    def homeContent(self, filter):
        # 初始访问，获取基础 Cookie
        try:
            self.session.get(self.host, headers=self.headers, timeout=10)
        except:
            pass
            
        url = f"{self.host}{self.base_path}/new"
        res = self.session.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        # 适配当前站点的分类列表
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "release", "type_name": "最新发行"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "uncensored-leak", "type_name": "无码流出"},
            {"type_id": "genres/uncensored", "type_name": "无码影片"},
            {"type_id": "genres/censored", "type_name": "有码影片"},
            {"type_id": "genres/individual", "type_name": "单体作品"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        # 构造带有页码的 URL
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
        # MissAV 的视频列表容器主要为 .thumbnail
        items = doc('.thumbnail').items()
        
        for item in items:
            # 1. 提取图片（优先 data-src，处理延迟加载）
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): 
                img = "https:" + img
            
            # 2. 详情链接提取
            a_tag = item('a').last()
            href = a_tag.attr('href') or ""
            if not href: continue
            
            # 3. 提取 vod_id (URL 最后一段)
            vod_id = href.rstrip('/').split('/')[-1]
            
            # 4. 标题与时长备注
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
        # 详情页通常直接在根域名下
        url = f"{self.host}/{mid}"
        res = self.session.get(url, headers=self.headers, timeout=15)
        html = res.text
        doc = pq(html)
        
        # --- 核心：多重策略提取 m3u8 ---
        play_url = ""
        # 模式1：标准 script 赋值
        m1 = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html)
        # 模式2：URL Encode 后的地址
        m2 = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html)
        
        if m1:
            play_url = m1.group(1)
        elif m2:
            from urllib.parse import unquote
            play_url = unquote(m2.group(0))
        else:
            # 模式3：如果都找不到，则退化为嗅探模式
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip() or "未知标题",
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_actor": doc('a[href*="actors"]').text(),
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放列表${play_url}",
            "vod_content": doc('.text-secondary.break-all').text().strip() or "暂无内容简介"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        # 搜索功能适配
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = self.session.get(url, headers=self.headers, timeout=15)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        # 关键：播放请求必须带上 Referer 头
        actual_url = id.split('$')[-1]
        return {
            "parse": 0 if "m3u8" in actual_url else 1,
            "url": actual_url,
            "header": json.dumps(self.headers)
        }
