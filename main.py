mport os

import asyncio

from playwright.async_api import async_playwright

import urllib.request

import json

import re



WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")



TARGETS = [

    {"name": "공지사항", "url": "https://maple.land/board/notices"},

    {"name": "이벤트", "url": "https://maple.land/board/events"},

    {"name": "개발일지", "url": "https://maple.land/board/devlog"}

]



def clean_title(text):

    text = " ".join(text.split()).strip()

    text = re.sub(r'\s*N$', '', text)

    return text



def send_webhook(name, title, url):

    """라이브러리 설치 없이 기본 모듈(urllib)로 웹훅 전송"""

    if not WEBHOOK_URL: return

    msg = f"**[{name}] 새 소식**\n{title}\n{url}"

    data = json.dumps({"content": msg}).encode('utf-8')

    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={'Content-Type': 'application/json'})

    try:

        urllib.request.urlopen(req)

    except Exception as e:

        print(f"⚠️ 웹훅 전송 실패: {e}")



async def check_board(context, board_info):

    name = board_info["name"]

    list_url = board_info["url"]

    db_file = os.path.join(os.getcwd(), f"last_{name}.txt")

    

    page = await context.new_page()

    try:

        await page.goto(list_url, wait_until="networkidle", timeout=60000)

        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)

        rows = page.locator('div.min-w-0.flex-1')

        count = await rows.count()



        old_titles = []

        if os.path.exists(db_file):

            with open(db_file, "r", encoding="utf-8") as f:

                old_titles = [line.strip() for line in f if line.strip()]



        current_all_titles = []

        new_notifications = []

        

        for i in range(min(count, 5)):

            raw_title = await rows.nth(i).inner_text()

            title_text = clean_title(raw_title)

            if title_text in [name, "카테고리", "제목", ""] or len(title_text) < 2:

                continue

            

            current_all_titles.append(title_text)

            if title_text not in old_titles:

                await rows.nth(i).click()

                await page.wait_for_load_state("domcontentloaded")

                detail_url = page.url

                if old_titles:

                    new_notifications.append((title_text, detail_url))

                await page.goto(list_url, wait_until="domcontentloaded")

                await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)

                rows = page.locator('div.min-w-0.flex-1')



        for title, d_url in reversed(new_notifications):

            send_webhook(name, title, d_url)



        if current_all_titles:

            with open(db_file, "w", encoding="utf-8") as f:

                f.write("\n".join(current_all_titles))

    except Exception as e:

        print(f"❌ {name} 에러: {e}")

    finally:

        await page.close()



async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])

        context = await browser.new_context(viewport={'width': 1280, 'height': 800})

        for target in TARGETS:

            await check_board(context, target)

            await asyncio.sleep(2)

        await browser.close()



if __name__ == "__main__":

    asyncio.run(main())
