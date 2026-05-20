import os
import asyncio
from playwright.async_api import async_playwright
import requests # urllib 대신 requests 사용 (더 간결함)

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

def send_webhook(name, title, url):
    if not WEBHOOK_URL: return
    msg = f"**[{name}] 새 소식**\n{title}\n{url}"
    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"웹훅 전송 오류: {e}")

async def check_board(context, board_info):
    name, list_url = board_info["name"], board_info["url"]
    db_file = f"last_{name}.txt"
    
    page = await context.new_page()
    try:
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        rows = page.locator('a[href^="/board/"]')
        
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f]

        current_titles = []
        count = await rows.count()
        for i in range(min(count, 5)):
            row = rows.nth(i)
            title = (await row.inner_text()).strip()
            title = " ".join(title.split())
            link = "https://maple.land" + await row.get_attribute("href")
            
            if not title or len(title) < 5: continue
            current_titles.append(title)
            
            if old_titles and title not in old_titles:
                send_webhook(name, title, link)

        with open(db_file, "w", encoding="utf-8") as f:
            f.write("\n".join(current_titles))
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # --no-sandbox: 리눅스 서버(Actions) 환경에서 필수 설정
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
