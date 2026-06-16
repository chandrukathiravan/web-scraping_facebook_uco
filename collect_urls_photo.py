# pyrefly: ignore [missing-import]

import posixpath    
from playwright.sync_api import sync_playwright
import pandas as pd
import json
import time
import os
from urllib.parse import (
    urlparse,
    parse_qs
)
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

# =========================================
# CURRENT DATE
# =========================================

today = datetime.today()

print(
    f"\nCURRENT DATE : {today.strftime('%d-%b-%Y')}"
)

# =========================================
# PREVIOUS MONTH DATE RANGE
# =========================================

prev_month = today - relativedelta(months=1)

START_DATE = datetime(
    prev_month.year,
    prev_month.month,
    1
)

last_day = calendar.monthrange(
    prev_month.year,
    prev_month.month
)[1]

END_DATE = datetime(
    prev_month.year,
    prev_month.month,
    last_day
)

print(
    f"START DATE   : {START_DATE.strftime('%d-%b-%Y')}"
)

print(
    f"END DATE     : {END_DATE.strftime('%d-%b-%Y')}"
)

MONTH_NAME = prev_month.strftime("%B").lower()

STOP_COLLECTION = False
# =========================================
# CONFIG
# =========================================

TARGET_URL = (
    "https://www.facebook.com/"
    "official.ucobank/photos"
)

MONTH_YEAR = prev_month.strftime("%b_%Y")

URL_FOLDER = f"URL/{MONTH_YEAR}"

os.makedirs(URL_FOLDER, exist_ok=True)

OUTPUT_EXCEL = (
    f"{URL_FOLDER}/facebook_photo_urls_{MONTH_YEAR}.xlsx"
)

OUTPUT_CSV = (
    f"{URL_FOLDER}/facebook_photo_urls_{MONTH_YEAR}.csv"
)

all_posts = []

visited_urls = set()

# =========================================
# FIX COOKIES
# =========================================

def fix_cookies(cookies):

    fixed = []

    for cookie in cookies:

        same_site = cookie.get(
            "sameSite",
            "Lax"
        )

        if same_site == "no_restriction":

            same_site = "None"

        elif same_site is None:

            same_site = "Lax"

        elif same_site not in [
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

        fixed.append(
            fixed_cookie
        )

    return fixed

# =========================================
# CLEAN FACEBOOK URL
# =========================================

def clean_facebook_url(url):

    try:

        parsed = urlparse(url)

        query = parse_qs(
            parsed.query
        )

        fbid = query.get(
            "fbid",
            [None]
        )[0]

        if not fbid:

            return None

        clean_url = (

            "https://www.facebook.com/"
            f"photo.php?fbid={fbid}"
        )

        return clean_url

    except:

        return None

# =========================================
# SAVE OUTPUT
# =========================================

def save_output():

    df = pd.DataFrame(
        all_posts
    )

    df.drop_duplicates(
        subset=["photo_url"],
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
# START PLAYWRIGHT
# =========================================

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(

        user_data_dir="facebook_profile",

        headless=False,

        viewport={

            "width": 1400,

            "height": 1000
        },

        args=[

            "--disable-blink-features=AutomationControlled"
        ]
    )

    # =====================================
    # LOAD COOKIES
    # =====================================

    print(
        "\nLoading cookies..."
    )

    with open(
        "facebook_cookies.json",
        "r",
        encoding="utf-8"
    ) as f:

        cookies = json.load(f)

    fixed_cookies = fix_cookies(
        cookies
    )

    browser.add_cookies(
        fixed_cookies
    )

    page = browser.new_page()
    temp_page = browser.new_page()

    page.set_default_navigation_timeout(
        120000
    )

    page.set_default_timeout(
        120000
    )

    # =====================================
    # OPEN FACEBOOK
    # =====================================

    print(
        "\nOpening Facebook..."
    )

    page.goto(
        "https://www.facebook.com",
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(
        10000
    )

    # =====================================
    # OPEN PHOTOS PAGE
    # =====================================

    print(
        "\nOpening Photos Page..."
    )

    page.goto(
        TARGET_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(
        15000
    )

    scroll_count = 0

    MAX_SCROLLS = 100

    duplicate_counter = 0

    # =====================================
    # MAIN LOOP
    # =====================================

    while scroll_count < MAX_SCROLLS:

        print(
            f"\nSCROLL {scroll_count + 1}"
        )

        page.wait_for_timeout(4000)

        # =================================
        # GET PHOTO LINKS
        # =================================

        photo_links = page.locator(
            "a[href*='photo.php?fbid=']"
        )

        count = photo_links.count()

        print(
            f"Photo Links Found: {count}"
        )

        new_url_found = False

        # =================================
        # LOOP LINKS
        # =================================

        for i in range(count):

            if STOP_COLLECTION:
                break

            try:

                href = photo_links.nth(
                    i
                ).get_attribute(
                    "href"
                )

                if not href:
                    continue

                # =================================
                # FULL URL
                # =================================

                if href.startswith("/"):

                    href = (
                        "https://www.facebook.com"
                        + href
                    )

                # =================================
                # CLEAN URL
                # =================================

                clean_url = clean_facebook_url(
                    href
                )

                if not clean_url:
                    continue

                # =================================
                # DUPLICATE
                # =================================

                if clean_url in visited_urls:

                    duplicate_counter += 1
                    continue

                # =================================
                # SAVE URL
                # =================================

                visited_urls.add(
                    clean_url
                )

                duplicate_counter = 0

                new_url_found = True

                print(
                    f"\nPHOTO URL:\n{clean_url}"
                )
                
                print(
                    f"\nPHOTO URL:\n{clean_url}"
                )

                # ===========================
                # TEST TIMESTAMP
                # ==========================

                try:

                    temp_page.goto(
                        clean_url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                except Exception as e:

                    print(
                        f"OPEN FAILED: {clean_url}"
                    )

                    print(e)
                    continue

                temp_page.wait_for_timeout(8000)

                html = temp_page.evaluate(
                    "() => document.documentElement.outerHTML"
                )

                import re
                from datetime import datetime

                creation_time = ""
                publish_time = ""
                post_date = ""

                m = re.search(
                    r'creation_time\\?":(\d+)',
                    html
                )

                if m:

                    creation_time = int(
                        m.group(1)
                    )

                    print(
                        "CREATION:",
                        creation_time
                    )

                m = re.search(
                    r'publish_time\\?":(\d+)',
                    html
                )

                if m:

                    publish_time = int(
                        m.group(1)
                    )

                    print(
                        "PUBLISH:",
                        publish_time
                    )

                ts = creation_time or publish_time

                if ts:

                    post_dt = datetime.fromtimestamp(ts)

                    post_date = post_dt.strftime(
                        "%d-%b-%Y"
                    )
  
                    print(
                        "POST DATE:",
                        post_date
                    )

                    post_day=post_dt.date()
 
                    if post_day > END_DATE.date():

                        print(
                            "SKIP - NEWER THAN END DATE"
                        )

                    elif START_DATE.date() <= post_day <= END_DATE.date():

                        all_posts.append({

                            "post_date": post_date,

                            "photo_url": clean_url

                        })

                        print(
                            "ADDED"
                        )

                    else:

                        print(
                            "OLDER THAN START DATE"
                        )

                        STOP_COLLECTION = True

            except Exception as e:

                print(
                    "Link Error:",
                    e
                )

                # =================================
        # DATE RANGE STOP
        # =================================

        if STOP_COLLECTION:

            print(
                "\nReached START_DATE"
            )

            print(
                "Saving data..."
            )

            save_output()

            browser.close()
            exit()

        # =================================
        # STOP CONDITION
        # =================================

        if duplicate_counter >= 40:

            print(
                "\nNo more new URLs."
            )

            break

        # =================================
        # SLOW SCROLL
        # =================================

        try:

            page.mouse.wheel(
                0,
                3000
            )

        except Exception as e:

            print(
                "SCROLL ERROR:",
                e
            )

            break
        time.sleep(5)

        scroll_count += 1

    # =====================================
    # SAVE OUTPUT
    # =====================================

    save_output()

    try:
        temp_page.close()
    except:
        pass
    browser.close()