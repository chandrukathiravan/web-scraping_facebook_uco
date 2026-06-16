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
# DATE RANGE (Corrected Chronological Order)
# =========================================

FROM_DATE = datetime(2026, 5, 12).date()
TO_DATE = datetime(2026, 6, 10).date()

OUTPUT_EXCEL = "output/uco_post_urls.xlsx"
OUTPUT_CSV = "output/uco_post_urls.csv"

os.makedirs("output", exist_ok=True)

all_posts = []
visited_posts = set()

# =========================================
# LOAD COOKIES
# =========================================

def load_cookies(context):
    with open("x_cookies.json", "r", encoding="utf-8") as f:
        cookies = json.load(f)

    fixed_cookies = []
    for cookie in cookies:
        same_site = cookie.get("sameSite", "Lax")
        if same_site not in ["Strict", "Lax", "None"]:
            same_site = "Lax"

        fixed_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie.get("path", "/"),
            "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False),
            "sameSite": same_site
        }
        fixed_cookies.append(fixed_cookie)

    context.add_cookies(fixed_cookies)

# =========================================
# SAVE OUTPUT
# =========================================

def save_output():
    if not all_posts:
        print("\nNo posts gathered to save.")
        return

    df = pd.DataFrame(all_posts)
    df.drop_duplicates(subset=["post_url"], inplace=True)
    
    # Format and sort by date descending
    df["post_date"] = pd.to_datetime(df["post_date"])
    df = df.sort_values(by="post_date", ascending=False)
    
    # Convert date back to string format for cleaner excel/csv view
    df["post_date"] = df["post_date"].dt.strftime('%Y-%m-%d')

    df.to_excel(OUTPUT_EXCEL, index=False)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("\n===================================")
    print("DATA SAVED")
    print("===================================")
    print(f"Total Unique URLs: {len(df)}")
    print(f"Excel: {OUTPUT_EXCEL}")
    print(f"CSV: {OUTPUT_CSV}")

# =========================================
# START
# =========================================

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1400, "height": 1200})
    
    load_cookies(context)
    page = context.new_page()

    print("\nOpening UCO profile...")
    page.goto(TARGET_URL, timeout=60000)
    time.sleep(10)

    scroll_count = 0
    MAX_SCROLLS = 500
    stop_scraping = False
    consecutive_old_posts = 0

    # =====================================
    # MAIN LOOP
    # =====================================
    while scroll_count < MAX_SCROLLS and not stop_scraping:
        print(f"\nSCROLL {scroll_count + 1}")
        
        # Wait for posts to load
        page.wait_for_timeout(3000)
        posts = page.locator("article[data-testid='tweet']")
        count = posts.count()
        
        print(f"Visible Posts: {count}")

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
                # PINNED TWEET CHECK
                # =================================
                try:
                    is_pinned = "Pinned" in full_text or "Pinned Post" in full_text
                except:
                    is_pinned = False

                # =================================
                # URL EXTRACTION
                # =================================
                link_locator = post.locator("a[href*='/status/']")
                if link_locator.count() == 0:
                    continue

                href = link_locator.first.get_attribute("href")
                if not href or "/status/" not in href:
                    continue

                post_url = "https://x.com" + href

                # =================================
                # DUPLICATE DUPLICATION
                # =================================
                if post_url in visited_posts:
                    continue

                # =================================
                # DATE EXTRACTION
                # =================================
                time_locator = post.locator("time")
                if time_locator.count() == 0:
                    continue

                raw_date = time_locator.get_attribute("datetime")
                if not raw_date:
                    continue

                post_datetime = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                post_date = post_datetime.date()

                print(f"\nDate: {post_date}")
                print(f"URL: {post_url}")

                # =================================
                # HANDLE OLD POSTS
                # =================================
                if post_date < FROM_DATE:
                    if is_pinned:
                        print(f"Pinned tweet ignored: {post_date}")
                        continue

                    consecutive_old_posts += 1
                    print(f"Older post found ({consecutive_old_posts}/5)")

                    if consecutive_old_posts >= 5:
                        print("\n===================================")
                        print("TIMELINE BOUNDARY REACHED")
                        print(f"Stopping at date {post_date}")
                        print("===================================\n")
                        stop_scraping = True
                        break
                    continue
                else:
                    # Reset old tracker if a valid or future post is seen
                    # (helps with random out-of-order timeline items)
                    if not is_pinned:
                        consecutive_old_posts = 0

                # =================================
                # SAVE POSTS IN RANGE
                # =================================
                if FROM_DATE <= post_date <= TO_DATE:
                    if post_url not in visited_posts:
                        visited_posts.add(post_url)
                        all_posts.append({
                            "post_date": str(post_date),
                            "post_url": post_url
                        })
                        print("POST SAVED")

            except Exception as e:
                print("Post Error:", e)

        if stop_scraping:
            break

        # =================================
        # SLOW SCROLL
        # =================================
        page.mouse.wheel(0, 3500)
        time.sleep(5)
        scroll_count += 1

    # =====================================
    # SAVE FINAL OUTPUT
    # =====================================
    save_output()
    browser.close()