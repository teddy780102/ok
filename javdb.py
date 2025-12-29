import asyncio
from playwright.async_api import async_playwright

async def scrape_missav():
    async with async_playwright() as p:
        # 启动浏览器，headless=False 可以让你看到操作过程
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("正在访问 MissAV...")
        try:
            # 访问首页或特定分类页
            await page.goto("https://missav.ws/dm194/cn", wait_until="domcontentloaded", timeout=60000)
            
            # 等待视频卡片元素加载
            await page.wait_for_selector(".thumbnail", timeout=10000)

            # 获取所有视频节点
            videos = await page.query_selector_all(".thumbnail")

            print(f"成功找到 {len(videos)} 个视频：\n")

            for video in videos:
                # 提取标题
                title_el = await video.query_selector("a.text-secondary")
                title = await title_el.inner_text() if title_el else "无标题"
                
                # 提取链接
                link = await title_el.get_attribute("href") if title_el else ""
                
                print(f"标题: {title.strip()}")
                print(f"链接: {link}")
                print("-" * 30)

        except Exception as e:
            print(f"发生错误: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_missav())
