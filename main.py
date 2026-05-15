import os
import asyncio
from playwright.async_api import async_playwright
import requests
import re

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"

TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

def clean_title(text):
    text = " ".join(text.split()).strip()
    text = re.sub(r'\s*N$', '', text)
    return text

async def check_board(context, board_info):
    name = board_info["name"]
    list_url = board_info["url"]
    db_file = os.path.join(os.getcwd(), f"last_{name}.txt")
    
    page = await context.new_page()
    try:
        print(f"🔍 {name} 탭 스캔 시작...")
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        new_notifications = []
        current_all_titles = []
        processed_count = 0

        for i in range(count):
            if processed_count >= 5:
                break
            
            raw_title = await rows.nth(i).inner_text()
            title_text = clean_title(raw_title)
            
            if title_text in [name, "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            current_all_titles.append(title_text)
            processed_count += 1

            if title_text not in old_titles:
                await rows.nth(i).click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1)
                detail_url = page.url
                
                if old_titles:
                    new_notifications.append((title_text, detail_url))
                
                print(f"    ✨ 새 소식: {title_text}")
                await page.goto(list_url, wait_until="domcontentloaded")
                rows = page.locator('div.min-w-0.flex-1')

        for title, d_url in reversed(new_notifications):
            msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
            requests.post(WEBHOOK_URL, json={"content": msg})

        if current_all_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_all_titles))
            print(f"💾 {name} 저장 완료")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
