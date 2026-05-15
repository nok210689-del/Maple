import os
import asyncio
from playwright.async_api import async_playwright
import requests
import re

# 1. 설정값 (디스코드 웹훅 주소)
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"

TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

def clean_title(text):
    """제목 끝의 N 표시 및 불필요한 공백 제거"""
    # 줄바꿈 및 연속된 공백 정리
    text = " ".join(text.split()).strip()
    # 끝에 붙은 'N' 제거 (공백 유무 상관없이 처리)
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
            
            # 제목 추출 및 전처리
            raw_title = await rows.nth(i).inner_text()
            title_text = clean_title(raw_title)
            
            # 유효하지 않은 텍스트 필터링
            if title_text in [name, "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            current_all_titles.append(title_text)
            processed_count += 1

            # 새 글인지 확인 (기존 목록에 없는 경우만)
