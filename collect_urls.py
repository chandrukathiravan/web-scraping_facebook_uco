# pyrefly: ignore [missing-import]

from playwright.sync_api import sync_playwright
import pandas as pd
import json
import time
import os
from datetime import datetime

# =========================================
# CONFIG
# =========================================

TARGET_URL = "https://x.com/UCOBankOfficial"

# =========================================
# DATE RANGE
# =========================================

FROM_DATE = datetime(
    2026,
    6,
    10
).date()

TO_DATE = datetime(
    2026,
    5,
    12
).date()

OUTPUT_EXCEL = "output/uco_post_urls.xlsx"

OUTPUT_CSV = "output/uco_post_urls.csv"

os.makedirs("output", exist_ok=True)

all_posts = []

visited_posts = set()

# =========================================
# LOAD COOKIES
# =========================================

def load_cookies(context):

    with open(
        "x_cookies.json",
        "r",
        encoding="utf-8"
    ) as f:

        cookies = json.load(f)

    fixed_cookies = []

    for cookie in cookies:

        same_site = cookie.get(
            "sameSite",
            "Lax"
        )

        if same_site not in [
            "Strict",
            "Lax",
            "None"
        ]:
            same_site = "Lax"

        fixed_cookie = {

            "name": cookie["name"],

            "value": cookie["value"],

            "domain": cookie["domain"],

            "path": cookie.get(
                "path",
                "/"
            ),

            "expires": cookie.get(
                "expirationDate",
                -1
            ),

            "httpOnly": cookie.get(
                "httpOnly",
                False
            ),

            "secure": cookie.get(
                "secure",
                False
            ),

            "sameSite": same_site
        }

        fixed_cookies.append(
            fixed_cookie
        )

    context.add_cookies(
        fixed_cookies
    )

# =========================================
# SAVE OUTPUT
# =========================================

def save_output():

    df = pd.DataFrame(
        all_posts
    )

    df.drop_duplicates(
        subset=["post_url"],
        inplace=True
    )

    df.to_excel(
        OUTPUT_EXCEL,
        index=False
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n===================================")
    print("DATA SAVED")
    print("===================================")

    print(
        f"\nTotal URLs: {len(df)}"
    )

    print(
        f"\nExcel: {OUTPUT_EXCEL}"
    )

    print(
        f"\nCSV: {OUTPUT_CSV}"
    )

# =========================================
# START
# =========================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        viewport={
            "width": 1400,
            "height": 1200
        }
    )

    load_cookies(context)

    page = context.new_page()

    print("\nOpening UCO profile...")

    page.goto(
        TARGET_URL,
        timeout=60000
    )

    time.sleep(10)

    scroll_count = 0

    MAX_SCROLLS = 500

    old_post_counter = 0

    # =====================================
    # MAIN LOOP
    # =====================================

    while scroll_count < MAX_SCROLLS:

        print(
            f"\nSCROLL {scroll_count + 1}"
        )

        # =================================
        # WAIT FOR POSTS
        # =================================

        page.wait_for_timeout(3000)

        posts = page.locator(
            "article[data-testid='tweet']"
        )

        count = posts.count()

        print(
            f"Visible Posts: {count}"
        )

        new_post_saved = False

        # =================================
        # LOOP POSTS
        # =================================

        for i in range(count):

            try:

                post = posts.nth(i)

                # =================================
                # FULL POST TEXT
                # =================================

                full_text = ""

                try:

                    full_text = post.inner_text()

                except:
                    pass

                # =================================
                # ONLY UCO POSTS
                # =================================

                if "@UCOBankOfficial" not in full_text:

                    continue

                # =================================
                # URL
                # =================================

                link_locator = post.locator(
                    "a[href*='/status/']"
                )

                if link_locator.count() == 0:
                    continue

                href = link_locator.first.get_attribute(
                    "href"
                )

                if not href:
                    continue

                if "/status/" not in href:
                    continue

                post_url = (
                    "https://x.com"
                    + href
                )

                # =================================
                # DUPLICATE
                # =================================

                if post_url in visited_posts:
                    continue

                # =================================
                # DATE
                # =================================

                time_locator = post.locator(
                    "time"
                )

                if time_locator.count() == 0:
                    continue

                raw_date = time_locator.get_attribute(
                    "datetime"
                )

                if not raw_date:
                    continue

                post_datetime = datetime.fromisoformat(
                    raw_date.replace(
                        "Z",
                        "+00:00"
                    )
                )

                post_date = post_datetime.date()

                print(
                    f"\nDate: {post_date}"
                )

                print(
                    f"URL: {post_url}"
                )

                # =================================
                # SAVE POSTS BETWEEN DATES
                # =================================

                if TO_DATE <= post_date <= FROM_DATE:

                    visited_posts.add(
                        post_url
                    )

                    all_posts.append({

                        "post_date": str(post_date),

                        "post_url": post_url
                    })

                    print(
                        "POST SAVED"
                    )

                    new_post_saved = True

                    old_post_counter = 0

                # =================================
                # OLDER POSTS
                # =================================

                elif post_date < TO_DATE:

                    old_post_counter += 1

                    print(
                        f"Older Posts Seen: "
                        f"{old_post_counter}"
                    )

            except Exception as e:

                print(
                    "Post Error:",
                    e
                )

        # =================================
        # STOP CONDITION
        # =================================

        if old_post_counter >= 10:

            print(
                "\nReached older timeline."
            )

            break

        # =================================
        # SLOW SCROLL
        # =================================

        page.mouse.wheel(
            0,
            3500
        )

        time.sleep(5)

        scroll_count += 1

    # =====================================
    # SAVE FINAL OUTPUT
    # =====================================

    save_output()

    browser.close()