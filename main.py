import os
import asyncio
from playwright.async_api import async_playwright
import requests
import re

# 1. 설정값 (Secrets에서 웹훅 주소를 불러옵니다)
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

def clean_title(text):
    """제목 끝의 N 표시 및 불필요한 공백 제거"""
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
        
        # 게시글 요소 대기
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        # 기존 저장된 제목 읽기
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        new_notifications = []
        current_all_titles = []
        processed_count = 0

        for i in range(count):
            if processed_count >= 5: break # 상위 5개만 확인
            
            raw_title = await rows.nth(i).inner_text()
            title_text = clean_title(raw_title)
            
            if title_text in [name, "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            current_all_titles.append(title_text)
            processed_count += 1

            # 새 글인지 확인
            if title_text not in old_titles:
                # 클릭해서 상세 URL 가져오기
                await rows.nth(i).click()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1) 
                detail_url = page.url
                
                if old_titles:
                    new_notifications.append((title_text, detail_url))
                
                print(f"    ✨ 새 소식 발견: {title_text}")
                
                # 다시 목록으로
                await page.goto(list_url, wait_until="domcontentloaded")
                rows = page.locator('div.min-w-0.flex-1')

        # 알림 전송 (주소가 정상적으로 불러와졌을 때만)
        if WEBHOOK_URL:
            for title, d_url in reversed(new_notifications):
                msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                requests.post(WEBHOOK_URL, json={"content": msg})
        else:
            print("⚠️ 경고: WEBHOOK_URL을 찾을 수 없습니다. Secrets 설정을 확인하세요.")

        # 데이터 저장
        if current_all_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_all_titles))
            print(f"💾 {name} 업데이트 완료")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    if not WEBHOOK_URL:
        print("❌ 에러: DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return

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
