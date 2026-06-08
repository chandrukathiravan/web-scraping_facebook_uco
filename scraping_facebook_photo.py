# pyrefly: ignore [missing-import]

from playwright.sync_api import sync_playwright
import pandas as pd
import json
import time
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# =========================================
# INPUT / OUTPUT
# =========================================

INPUT_EXCEL = (
    "output/facebook_photo_urls.xlsx"
)

OUTPUT_EXCEL = (
    "output/facebook_scraped_data.xlsx"
)

OUTPUT_CSV = (
    "output/facebook_scraped_data.csv"
)

os.makedirs(
    "output",
    exist_ok=True
)

# =========================================
# LOAD URLS
# =========================================

df_urls = pd.read_excel(
    INPUT_EXCEL
)

photo_urls = (
    df_urls["photo_url"]
    .dropna()
    .unique()
    .tolist()
)

print(
    f"\nTotal URLs Loaded: "
    f"{len(photo_urls)}"
)

# =========================================
# OUTPUT
# =========================================

all_data = []

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
# CLEAN COUNTS
# =========================================

def convert_count(text):

    try:

        text = (
            text.replace(",", "")
            .strip()
            .upper()
        )

        if not text:
            return ""

        if "K" in text:

            return int(
                float(
                    text.replace("K", "")
                ) * 1000
            )

        if "M" in text:

            return int(
                float(
                    text.replace("M", "")
                ) * 1000000
            )

        match = re.search(
            r"\d+",
            text
        )

        if match:

            return int(
                match.group()
            )

    except:
        pass

    return ""

# =========================================
# CLEAN HTML + EMOJI
# =========================================

def clean_html_with_emoji(html):

    try:

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # =============================
        # REPLACE IMG EMOJI
        # =============================

        imgs = soup.find_all("img")

        for img in imgs:

            alt = img.get("alt")

            if alt:

                img.replace_with(
                    alt
                )

        return soup.get_text(
            separator=" ",
            strip=True
        )

    except:

        return ""

# =========================================
# EXTRACT DATE
# =========================================

def extract_date(page):

    try:

        spans = page.locator(
            "span"
        )

        count = spans.count()

        for i in range(count):

            try:

                txt = spans.nth(
                    i
                ).inner_text().strip()

                if not txt:
                    continue

                # =========================
                # VALID DATE PATTERNS
                # =========================

                if re.search(

                    r"^\d+\s?(m|min|h|d|w)$",

                    txt,

                    re.IGNORECASE
                ):

                    return txt

                if re.search(

                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",

                    txt,

                    re.IGNORECASE
                ):

                    return txt

            except:
                pass

    except:
        pass

    return ""

# =========================================
# SAVE OUTPUT
# =========================================

def save_output():

    df = pd.DataFrame(
        all_data
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
        f"\nRows: {len(df)}"
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

    page.set_default_navigation_timeout(
        120000
    )

    page.set_default_timeout(
        120000
    )

    # =====================================
    # OPEN FACEBOOK
    # =====================================

    page.goto(
        "https://www.facebook.com",
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(
        10000
    )

    # =====================================
    # LOOP POSTS
    # =====================================

    for idx, url in enumerate(photo_urls):

        try:

            print("\n===================================")
            print(
                f"POST {idx + 1}"
            )
            print("===================================")

            print(
                f"\nOpening:\n{url}"
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            page.wait_for_timeout(
                10000
            )

            # =================================
            # SEE MORE
            # =================================

            try:

                see_more = page.locator(
                    "span:has-text('See more')"
                )

                if see_more.count() > 0:

                    see_more.first.click()

                    page.wait_for_timeout(
                        2000
                    )

            except:
                pass

            # =================================
            # POST TEXT
            # =================================

            post_text = ""

            try:

                divs = page.locator(
                    "div[dir='auto']"
                )

                div_count = divs.count()

                longest = ""

                for d in range(div_count):

                    try:

                        html = divs.nth(
                            d
                        ).inner_html()

                        cleaned = clean_html_with_emoji(
                            html
                        )

                        if len(cleaned) > len(longest):

                            longest = cleaned

                    except:
                        pass

                post_text = longest

            except:
                pass

            print("\nPOST TEXT:")
            print(post_text)

            # =================================
            # DATE
            # =================================

            post_date = extract_date(
                page
            )

            print(
                f"\nDate: {post_date}"
            )

            # =================================
            # LIKES
            # =================================

            likes_count = ""

            try:

                like_button = page.locator(
                    "div[data-ad-rendering-role='like_button']"
                )

                if like_button.count() > 0:

                    parent = (
                        like_button.first
                        .locator(
                            "xpath=ancestor::div[2]"
                        )
                    )

                    txt = parent.inner_text()

                    likes_count = convert_count(
                        txt
                    )

            except:
                pass

            # =================================
            # COMMENTS
            # =================================

            comments_count = ""

            try:

                comment_button = page.locator(
                    "div[data-ad-rendering-role='comment_button']"
                )

                if comment_button.count() > 0:

                    parent = (
                        comment_button.first
                        .locator(
                            "xpath=ancestor::div[2]"
                        )
                    )

                    txt = parent.inner_text()

                    comments_count = convert_count(
                        txt
                    )

            except:
                pass

            # =================================
            # SHARES
            # =================================

            shares_count = ""

            try:

                share_button = page.locator(
                    "div[data-ad-rendering-role='share_button']"
                )

                if share_button.count() > 0:

                    parent = (
                        share_button.first
                        .locator(
                            "xpath=ancestor::div[2]"
                        )
                    )

                    txt = parent.inner_text()

                    shares_count = convert_count(
                        txt
                    )

            except:
                pass

            print(
                f"\nLikes: {likes_count}"
            )

            print(
                f"Comments: {comments_count}"
            )

            print(
                f"Shares: {shares_count}"
            )

            # =================================
            # LOAD COMMENTS
            # =================================

            print(
                "\nLoading comments..."
            )

            previous_count = 0

            same_count = 0

            for scroll in range(40):

                try:

                    more_comments = page.locator(
                        "span:has-text('View more comments')"
                    )

                    if more_comments.count() > 0:

                        more_comments.first.click()

                        page.wait_for_timeout(
                            3000
                        )

                except:
                    pass

                try:

                    more_replies = page.locator(
                        "span:has-text('View more replies')"
                    )

                    if more_replies.count() > 0:

                        more_replies.first.click()

                        page.wait_for_timeout(
                            3000
                        )

                except:
                    pass

                page.mouse.wheel(
                    0,
                    2000
                )

                time.sleep(3)

                comments = page.locator(
                    "div[aria-label^='Comment by']"
                )

                current_count = comments.count()

                print(
                    f"Comments Loaded: "
                    f"{current_count}"
                )

                if current_count == previous_count:

                    same_count += 1

                else:

                    same_count = 0

                if same_count >= 3:

                    print(
                        "\nNo more comments loading."
                    )

                    break

                previous_count = current_count

            # =================================
            # FINAL COMMENTS
            # =================================

            comments = page.locator(
                "div[aria-label^='Comment by']"
            )

            comments_found = comments.count()

            print(
                f"\nFinal Comments: "
                f"{comments_found}"
            )

            # =================================
            # LOOP COMMENTS
            # =================================

            for c in range(comments_found):

                try:

                    comment = comments.nth(c)

                    comment_user = ""
                    comment_text = ""
                    comment_likes = ""
                    comment_time = ""

                    # =============================
                    # USER
                    # =============================

                    try:

                        user_locator = comment.locator(
                            "a[role='link'] span"
                        )

                        if user_locator.count() > 0:

                            comment_user = (
                                user_locator.first
                                .inner_text()
                                .strip()
                            )

                    except:
                        pass

                    # =============================
                    # COMMENT TEXT + EMOJI
                    # =============================

                    try:

                        divs = comment.locator(
                            "div[dir='auto']"
                        )

                        div_count = divs.count()

                        longest = ""

                        for d in range(div_count):

                            try:

                                html = divs.nth(
                                    d
                                ).inner_html()

                                cleaned = (
                                    clean_html_with_emoji(
                                        html
                                    )
                                )

                                if len(cleaned) > len(longest):

                                    longest = cleaned

                            except:
                                pass

                        comment_text = longest

                    except:
                        pass

                    # =============================
                    # COMMENT TIME
                    # =============================

                    try:

                        spans = comment.locator(
                            "span"
                        )

                        span_count = spans.count()

                        for s in range(span_count):

                            try:

                                txt = spans.nth(
                                    s
                                ).inner_text().strip()

                                if re.search(

                                    r"^\d+\s?(m|min|h|d|w)$",

                                    txt,

                                    re.IGNORECASE
                                ):

                                    comment_time = txt
                                    break

                            except:
                                pass

                    except:
                        pass

                    # =============================
                    # COMMENT LIKES
                    # =============================

                    try:

                        react = comment.locator(
                            "div[aria-label='React']"
                        )

                        if react.count() > 0:

                            txt = react.first.inner_text()

                            comment_likes = (
                                convert_count(
                                    txt
                                )
                            )

                    except:
                        pass

                    # =============================
                    # SKIP EMPTY
                    # =============================

                    if not comment_text:
                        continue

                    print("\n-----------------------------------")
                    print(
                        f"USER: {comment_user}"
                    )
                    print("-----------------------------------")
                    print(comment_text)

                    # =============================
                    # SAVE
                    # =============================

                    all_data.append({

                        "post_date": post_date,

                        "photo_url": url,

                        "post_text": post_text,

                        "likes_count": likes_count,

                        "comments_count": comments_count,

                        "shares_count": shares_count,

                        "comment_user": comment_user,

                        "comment_text": comment_text,

                        "comment_likes": comment_likes,

                        "comment_time": comment_time,

                        "scrape_date": str(
                            datetime.now().date()
                        )
                    })

                except Exception as e:

                    print(
                        "Comment Error:",
                        e
                    )

            # =================================
            # SAVE CONTINUOUSLY
            # =================================

            save_output()

        except Exception as e:

            print(
                "POST ERROR:",
                e
            )

    # =====================================
    # FINAL SAVE
    # =====================================

    save_output()

    browser.close()