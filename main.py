import os
import asyncio
from playwright.async_api import async_playwright
import requests


# ============================================================
# Discord Webhook
# ============================================================

WEBHOOK_URLS = [
    os.environ.get("DISCORD_WEBHOOK"),
    os.environ.get("DISCORD_WEBHOOK2"),
]


TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"},
]


# ============================================================
# 프로젝트 루트
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# Discord Webhook 전송
# ============================================================

def send_webhook(name, title, url):

    msg = (
        f"**[{name}] 새 소식**\n"
        f"{title}\n"
        f"{url}"
    )

    for webhook_url in WEBHOOK_URLS:

        if not webhook_url:
            continue

        try:

            response = requests.post(
                webhook_url,
                json={"content": msg},
                timeout=10
            )

            if response.status_code not in (200, 204):

                print(
                    f"웹훅 전송 실패: "
                    f"{response.status_code}"
                )

        except Exception as e:

            print(
                f"웹훅 전송 오류: {e}"
            )


# ============================================================
# 게시판 확인
# ============================================================

async def check_board(context, board_info):

    name = board_info["name"]
    list_url = board_info["url"]

    db_file = os.path.join(
        BASE_DIR,
        f"last_{name}.txt"
    )

    page = await context.new_page()

    try:

        print(
            f"[{name}] 접속 중: {list_url}"
        )

        await page.goto(
            list_url,
            wait_until="networkidle",
            timeout=60000
        )

        rows = page.locator(
            "div.flex.items-center a"
        )

        count = await rows.count()

        old_titles = []

        if os.path.exists(db_file):

            with open(
                db_file,
                "r",
                encoding="utf-8"
            ) as f:

                old_titles = [
                    line.strip()
                    for line in f
                    if line.strip()
                ]

        current_titles = []

        for i in range(count):

            full_text = (
                await rows.nth(i).text_content()
            ) or ""

            title = " ".join(
                full_text.split()
            )

            if len(title) < 5:
                continue

            if any(
                k in title
                for k in [
                    "Discord",
                    "카테고리",
                    "제목"
                ]
            ):
                continue

            # N 제거
            clean_title = title

            if clean_title.startswith("N "):

                clean_title = (
                    clean_title[2:].strip()
                )

            # 신규 게시글
            if (
                old_titles
                and clean_title not in old_titles
            ):

                href = await rows.nth(i).get_attribute(
                    "href"
                )

                if href:

                    if href.startswith("http"):
                        link = href
                    else:
                        link = (
                            f"https://maple.land{href}"
                        )

                    print(
                        f"신규 게시글 발견: {title}"
                    )

                    # 웹훅 2곳 모두 전송
                    send_webhook(
                        name,
                        title,
                        link
                    )

            current_titles.append(
                clean_title
            )

        with open(
            db_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n".join(current_titles)
            )

        print(
            f"DEBUG: [{name}] 저장 완료. "
            f"{len(current_titles)}개 항목."
        )

    except Exception as e:

        print(
            f"❌ [{name}] 에러 발생: {e}"
        )

    finally:

        await page.close()


# ============================================================
# Main
# ============================================================

async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1280,
                "height": 800
            }
        )

        for target in TARGETS:

            await check_board(
                context,
                target
            )

            await asyncio.sleep(2)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
