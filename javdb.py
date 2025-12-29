import asyncio
from playwright.async_api import async_playwright

async def run_missav_spider():
    async with async_playwright() as p:
        # 启动浏览器 (headless=True 表示后台运行，False 会弹出窗口)
        browser = await p.chromium.launch(headless=True)
        
        # 模拟真实浏览器环境，防止被简单反爬识别
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # 1. 访问页面 (如：最新视频)
        url = "https://missav.com/new"
        print(f"正在访问: {url}")
        
        # 设置较大的超时，以防网络波动
        await page.goto(url, timeout=60000, wait_until="networkidle")

        # 2. 等待视频列表加载
        # MissAV 的视频通常包裹在具有特定 class 的 div 中
        await page.wait_for_selector('.grid')

        # 3. 提取数据
        videos = await page.query_selector_all('div.thumbnail') # 根据实际 DOM 结构微调
        
        results = []
        for video in videos:
            # 提取标题
            title_tag = await video.query_selector('a.text-nord10')
            title = await title_tag.inner_text() if title_tag else "N/A"
            
            # 提取番号 (通常在标题中或特定标签内)
            code_tag = await video.query_selector('div span.font-mono')
            code = await code_tag.inner_text() if code_tag else "N/A"

            # 提取封面图链接
            img_tag = await video.query_selector('img')
            img_url = await img_tag.get_attribute('data-src') or await img_tag.get_attribute('src')

            results.append({
                "番号": code.strip(),
                "标题": title.strip(),
                "封面": img_url
            })

        # 4. 输出结果
        for item in results:
            print(f"[{item['番号']}] {item['标题']}")
            print(f"封面地址: {item['封面']}\n" + "-"*30)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_missav_spider())
