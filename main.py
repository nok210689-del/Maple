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
    msg = f"**[{name}]**\n{title}\n{url}"
    data = json.dumps({"content": msg}).encode('utf-8')
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req)
    except: pass

async def check_board(context, board_info):
    name, list_url = board_info["name"], board_info["url"]
    db_file = f"last_{name}.txt"
    
    page = await context.new_page()
    try:
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        # 게시글 리스트의 <a> 태그를 찾음
        rows = page.locator('a[href^="/board/"]')
        
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f]

        current_titles = []
        # 상위 5개 항목 확인
        count = await rows.count()
        for i in range(min(count, 5)):
            row = rows.nth(i)
            # 텍스트 추출
            title = (await row.inner_text()).strip()
            # 날짜/시간 포맷 등이 섞여있을 수 있어 불필요한 줄바꿈 제거
            title = " ".join(title.split())
            
            link = "https://maple.land" + await row.get_attribute("href")
            
            # 카테고리 태그(점검, 패치노트 등)가 제목에 붙어서 나올 경우 깔끔하게 정리
            # 첫 번째 단어가 카테고리인 경우 필터링을 원하시면 여기서 조정 가능
            if not title or len(title) < 5: continue
            
            current_titles.append(title)
            
            # 파일에 없는 새로운 제목이면 웹훅 전송
            if old_titles and title not in old_titles:
                send_webhook(name, title, link)

        # 현재 리스트 저장
        with open(db_file, "w", encoding="utf-8") as f:
            f.write("\n".join(current_titles))
            
    except Exception as e:
        print(f"Error checking {name}: {e}")
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
