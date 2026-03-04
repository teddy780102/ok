# -*- coding: utf-8 -*-
import requests
import json
import re
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 基础域名与路径后缀
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        self.base_path = "/dm194/cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': self.host,
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def homeContent(self, filter):
        # 访问首页以抓取动态分类
        res = requests.get(f"{self.host}{self.base_path}", headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        # 1. 动态抓取导航栏分类
        classes = []
        # 排除掉不需要显示的导航项
        exclude_words = ['首页', '直播', '排行榜', '我的', '登入', '注册', 'VR']
        
        # 查找所有包含 base_path 的链接
        for item in doc('nav a, .nav-item a, a[href*="/dm194/cn/"]').items():
            name = item.text().strip()
            href = item.attr('href') or ""
            
            if name and name not in exclude_words:
                # 提取相对路径作为 type_id
                # 例如从 /dm194/cn/new 中提取出 "new"
                parts = href.split(self.base_path)
                if len(parts) > 1:
                    tid = parts[1].strip('/')
                    if tid and tid not in [c['type_id'] for c in classes]:
                        classes.append({
                            "type_id": tid,
                            "type_name": name
                        })

        # 2. 如果动态抓取失败，使用常用保底分类
        if not classes:
            classes = [
                {"type_id": "new", "type_name": "最近更新"},
                {"type_id": "release", "type_name": "最新发行"},
                {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
                {"type_id": "uncensored-leak", "type_name": "无码流出"}
            ]

        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        # 拼装分类 URL
        # tid 可能是 "new" 或 "genres/uncensored"
        url = f"{self.host}{self.base_path}/{tid}?page={pg}"
        
        res = requests.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': int(pg),
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # 该站视频块通常带有 .thumbnail 类
        for item in doc('.thumbnail').items():
            # 处理懒加载图片：优先取 data-src
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'): 
                img = "https:" + img
            
            # 提取标题和详情页链接
            a_tag = item('a').last()
            title = a_tag.attr('title') or item('h2').text() or "未知影片"
            href = a_tag.attr('href') or ""
            
            # 提取 vod_id (URL 路径的最后一段)
            vod_id = href.rstrip('/').split('/')[-1] if href else ""
            
            if vod_id:
                # 提取时长或备注
                remarks = item('.duration').text() or item('.absolute.bottom-1').text()
                
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title.strip(),
                    "vod_pic": img,
                    "vod_remarks": remarks.strip() if remarks else "",
                })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        # 详情页通常直接在根域名下，例如 https://missav.ws/abc-123
        url = f"{self.host}/{mid}"
        res = requests.get(url, headers=self.headers, timeout=15)
        html_content = res.text
        doc = pq(html_content)
        
        # --- 核心：提取 M3U8 播放地址 ---
        play_url = ""
        # 尝试匹配 JavaScript 中的直接地址
        m1 = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html_content)
        # 尝试匹配 URL 编码后的地址（部分镜像站会混淆）
        m2 = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html_content)
        
        if m1:
            play_url = m1.group(1)
        elif m2:
            from urllib.parse import unquote
            play_url = unquote(m2.group(0))
        else:
            # 如果正则表达式均失效，则标记为“嗅探”，交给播放器内核处理
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip(),
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_actor": doc('a[href*="actors"]').text(),
            "vod_content": doc('.text-secondary.break-all').text().strip() or "暂无内容简介",
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放链接${play_url}"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        # 搜索路径通常为 /dm194/cn/search/关键词
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = requests.get(url, headers=self.headers, timeout=15)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        # 提取真实 URL
        actual_url = id.split('$')[-1]
        
        # 返回播放配置，必须带上 Referer 以防止 403
        return {
            "parse": 0 if "m3u8" in actual_url else 1,
            "url": actual_url,
            "header": json.dumps(self.headers)
        }
