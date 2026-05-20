import os
import asyncio
from playwright.async_api import async_playwright
import requests

# 웹훅 URL 및 타겟 설정
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

# 프로젝트 루트 경로 확보 (파일이 엉뚱한 곳에 저장되는 것 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def send_webhook(name, title, url):
    if not WEBHOOK_URL: return
    msg = f"**[{name}] 새 소식**\n{title}\n{url}"
    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"웹훅 전송 오류: {e}")

async def check_board(context, board_info):
    name = board_info["name"]
    list_url = board_info["url"]
    # 파일 경로를 프로젝트 루트로 강제 고정
    db_file = os.path.join(BASE_DIR, f"last_{name}.txt")
    
    page = await context.new_page()
    try:
        print(f"[{name}] 접속 중: {list_url}")
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        
        # 게시판 링크를 정확히 탐색
        rows = page.locator('a[href*="/board/"]')
        count = await rows.count()
        print(f"DEBUG: [{name}] 게시글 수: {count}")
        
        if count == 0:
            print(f"❌ [{name}] 게시글을 찾지 못했습니다.")
            return

        # 기존 데이터 로드
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        current_titles = []
        for i in range(min(count, 10)):
            title = (await rows.nth(i).inner_text()).strip()
            title = " ".join(title.split())
            href = await rows.nth(i).get_attribute("href")
            link = f"https://maple.land{href}"
            
            # 필터링
            if len(title) < 5 or "카테고리" in title or "제목" in title:
                continue
                
            current_titles.append(title)
            
            # 신규 데이터 알림
            if old_titles and title not in old_titles:
                print(f"신규 게시글 발견: {title}")
                send_webhook(name, title, link)

        # 데이터 파일 저장 (루트 경로에 강제 저장)
        with open(db_file, "w", encoding="utf-8") as f:
            f.write("\n".join(current_titles))
        print(f"DEBUG: [{name}] 파일 저장 완료 ({db_file})")
                
    except Exception as e:
        print(f"❌ [{name}] 에러 발생: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
