# -*- coding: utf-8 -*-
import requests
import json
import re
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    def init(self, extend="{}"):
        config = json.loads(extend)
        # 基础域名
        self.host = config.get('site', 'https://missav.ws').rstrip('/')
        # 路径后缀
        self.base_path = "/dm194/cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': self.host,
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def homeContent(self, filter):
        # 首页展示最近更新
        res = requests.get(f"{self.host}{self.base_path}/new", headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        classes = [
            {"type_id": "new", "type_name": "最近更新"},
            {"type_id": "release", "type_name": "新片发布"},
            {"type_id": "hot", "type_name": "今日热门"},
            {"type_id": "monthly-hot", "type_name": "本月热门"}
        ]
        
        return {
            'class': classes,
            'list': self.parse_list(doc),
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        # 兼容处理：如果 tid 不包含基础路径则补全
        path = tid if tid.startswith('/') else f"{self.base_path}/{tid}"
        url = f"{self.host}{path}?page={pg}"
        
        res = requests.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        return {
            'list': self.parse_list(doc),
            'page': pg,
            'pagecount': 999,
            'limit': 12
        }

    def parse_list(self, doc):
        videos = []
        # 适配该站常用的 thumbnail 结构
        for item in doc('.thumbnail').items():
            # 1. 提取图片（优先 data-src 懒加载）
            img = item('img').attr('data-src') or item('img').attr('src') or ""
            if img.startswith('//'):
                img = "https:" + img
            
            # 2. 提取标题和链接
            a_tag = item('a').last()
            title = a_tag.attr('title') or item('h2').text() or "未知影片"
            href = a_tag.attr('href') or ""
            
            # 3. 提取唯一 ID (通常是 URL 最后一段)
            vod_id = href.rstrip('/').split('/')[-1] if href else ""
            
            if vod_id:
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title.strip(),
                    "vod_pic": img,
                    "vod_remarks": item('.absolute.bottom-1').text().strip() or item('.duration').text(),
                    "style": {"type": "rect", "ratio": 1.33}
                })
        return videos

    def detailContent(self, ids):
        mid = ids[0]
        # 详情页通常在根域名下或 base_path 下，这里尝试直接拼接
        url = f"{self.host}/{mid}"
        res = requests.get(url, headers=self.headers, timeout=15)
        doc = pq(res.content)
        
        html_text = res.text
        play_url = ""
        
        # 提取 m3u8 地址逻辑
        # 方案 A: 正则匹配 source = '...'
        m3u8_match = re.search(r"source\s*=\s*'(https?://[^']+?\.m3u8[^']*)'", html_text)
        if m3u8_match:
            play_url = m3u8_match.group(1)
        else:
            # 方案 B: 匹配 window.__INITIAL_STATE__ 中的地址（带转义）
            m3u8_match_escaped = re.search(r'https?%[A-F0-9]{2}[^"\']+\.m3u8[^"\']*', html_text)
            if m3u8_match_escaped:
                from urllib.parse import unquote
                play_url = unquote(m3u8_match_escaped.group(0))

        # 如果都没找到，则交给壳子自带的嗅探
        if not play_url:
            play_url = f"嗅探${url}"

        vod = {
            "vod_id": mid,
            "vod_name": doc('h1').text().strip(),
            "vod_pic": doc('video').attr('poster') or "",
            "vod_type": "影片详情",
            "vod_year": "",
            "vod_area": "",
            "vod_actor": doc('a[href*="actors"]').text(),
            "vod_director": "",
            "vod_content": doc('.text-secondary.break-all').text().strip(),
            "vod_play_from": "MissAV",
            "vod_play_url": f"播放${play_url}"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        # 搜索页通常在 /cn/search/ 路径下
        url = f"{self.host}{self.base_path}/search/{key}?page={pg}"
        res = requests.get(url, headers=self.headers, timeout=15)
        return {"list": self.parse_list(pq(res.content))}

    def playerContent(self, flag, id, vipFlags):
        # 如果 id 已经是 m3u8 链接，parse 设为 0（直接播放）
        # 如果是嗅探地址，则交给壳子处理
        is_m3u8 = "m3u8" in id.lower()
        return {
            "parse": 0 if is_m3u8 else 1,
            "url": id.replace("嗅探$", ""),
            "header": json.dumps(self.headers)
        }
