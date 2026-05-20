import os
import asyncio
from playwright.async_api import async_playwright
import urllib.request
import json

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

def send_webhook(name, title, url):
    if not WEBHOOK_URL: return
    msg = f"**[{name}] 새 소식**\n{title}\n{url}"
    data = json.dumps({"content": msg}).encode('utf-8')
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req)
    except: pass

async def check_board(context, board_info):
    name, list_url = board_info["name"], board_info["url"]
    db_file = f"last_{name}.txt"
    
    page = await context.new_page()
    try:
        await page.goto(list_url, wait_until="networkidle")
        # 제목과 링크가 포함된 부모 태그(a 태그)를 한 번에 가져옴
        items = page.locator('a[href^="/board/"]') # 게시글 링크만 선택
        
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f]

        current_titles = []
        for i in range(min(await items.count(), 5)):
            title = (await items.nth(i).inner_text()).strip()
            link = "https://maple.land" + await items.nth(i).get_attribute("href")
            
            if not title or title in ["제목", "카테고리"]: continue
            
            current_titles.append(title)
            if title not in old_titles and old_titles:
                send_webhook(name, title, link)

        with open(db_file, "w", encoding="utf-8") as f:
            f.write("\n".join(current_titles))
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
