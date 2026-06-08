# pyrefly: ignore [missing-import]

from playwright.sync_api import sync_playwright
import pandas as pd
import json
import time
import os
import re
from bs4 import BeautifulSoup

# =========================================
# INPUT / OUTPUT
# =========================================

INPUT_EXCEL = "URL/facebook_photo_urls_jan.xlsx"
OUTPUT_EXCEL = "output/facebook_scraped_data_final_jan.xlsx"
OUTPUT_CSV = "output/facebook_scraped_data_final_jan.csv"

os.makedirs("output", exist_ok=True)

# =========================================
# LOAD URLS
# =========================================

df_urls = pd.read_excel(INPUT_EXCEL)

url_date_map = {}

for _, row in df_urls.iterrows():

    photo_url = str(
        row.get("photo_url", "")
    ).strip()

    post_date = str(
        row.get("post_date", "")
    ).strip()

    if photo_url:

        url_date_map[
            photo_url
        ] = post_date

photo_urls = list(
    url_date_map.keys()
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
        same_site = cookie.get("sameSite", "Lax")
        if same_site == "no_restriction":
            same_site = "None"
        elif same_site is None:
            same_site = "Lax"
        elif same_site not in ["Strict", "Lax", "None"]:
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
        fixed.append(fixed_cookie)
    return fixed

# =========================================
# CONVERT COUNTS
# =========================================

def convert_count(text):
    try:
        text = str(text).replace(",", "").strip().upper()
        if not text:
            return ""
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        if "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        match = re.search(r"\d+", text)
        if match:
            return int(match.group())
    except:
        pass
    return ""

# =========================================
# CLEAN HTML + EMOJI
# =========================================

def clean_html_with_emoji(html):
    try:
        soup = BeautifulSoup(html, "html.parser")

        # =================================
        # REMOVE SEE MORE BUTTONS
        # =================================
        for div in soup.find_all("div", role="button"):
            txt = div.get_text(strip=True).lower()
            if "see more" in txt:
                div.decompose()

        # =================================
        # REPLACE EMOJI IMAGES
        # =================================
        imgs = soup.find_all("img")
        for img in imgs:
            alt = img.get("alt")
            if alt:
                img.replace_with(f" {alt} ")

        # =================================
        # REMOVE LINKS
        # =================================
        for a in soup.find_all("a"):
            a.replace_with(a.get_text(strip=True))

        # =================================
        # GET TEXT
        # =================================
        text = soup.get_text(separator=" ", strip=True)

        # =================================
        # CLEAN EXTRA SPACES
        # =================================
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except:
        return ""

# =========================================
# SAVE OUTPUT
# =========================================

def save_output():
    df = pd.DataFrame(all_data)
    df.to_excel(OUTPUT_EXCEL, index=False)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print("\n===================================")
    print("DATA SAVED")
    print("===================================")
    print(f"\nRows: {len(df)}")

# =========================================
# START PLAYWRIGHT
# =========================================

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="facebook_profile",
        headless=False,
        viewport={"width": 1400, "height": 1000},
        args=["--disable-blink-features=AutomationControlled"]
    )

    # =====================================
    # LOAD COOKIES
    # =====================================
    print("\nLoading cookies...")
    with open("facebook_cookies.json", "r", encoding="utf-8") as f:
        cookies = json.load(f)

    fixed_cookies = fix_cookies(cookies)
    browser.add_cookies(fixed_cookies)

    page = browser.new_page()
    page.set_default_navigation_timeout(120000)
    page.set_default_timeout(120000)

    # =====================================
    # OPEN FACEBOOK
    # =====================================
    page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=120000)
    time.sleep(10)
   
    # =====================================
    # LOOP POSTS
    # =====================================
    for idx, url in enumerate(photo_urls):
        try:
            print("\n===================================")
            print(f"POST {idx + 1}")
            print("===================================")
            print(f"\nOpening:\n{url}")

            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            time.sleep(8)
            post_date = url_date_map.get(
                url,
                ""
                )

            print(
                f"\nPOST DATE: {post_date}"
    )

            # =================================
            # EXPAND ALL SEE MORE
            # =================================
            try:
                for _ in range(10):
                    buttons = page.locator("div[role='button']")
                    btn_count = buttons.count()
                    clicked = False
                    for i in range(btn_count):
                        try:
                            txt = buttons.nth(i).inner_text().strip().lower()
                            if "see more" in txt or txt == "more":
                                buttons.nth(i).click()
                                time.sleep(1.5)
                                clicked = True
                        except:
                            pass
                    if not clicked:
                        break
            except:
                pass

            # =================================
            # POST TEXT
            # =================================
            post_text = ""
            try:
                post_container = page.locator("div.xyinxu5.xyri2b.x1g2khh7.x1c1uobl")
                print(f"\nPost Containers Found: {post_container.count()}")
                if post_container.count() > 0:
                    html = post_container.first.inner_html()
                    post_text = clean_html_with_emoji(html)
                    post_text = re.sub(r"http\S+", "", post_text)
                    post_text = re.sub(r"\s+", " ", post_text).strip()
            except Exception as e:
                print("POST TEXT ERROR:", e)

            print("\nPOST TEXT:")
            print(post_text)

            # =================================
            # LIKES COUNT
            # =================================
            likes_count = ""
            try:
                like_button = page.locator("div[data-ad-rendering-role='like_button']")
                print(f"\nLike Buttons: {like_button.count()}")
                if like_button.count() > 0:
                    parent = like_button.first.locator("xpath=ancestor::div[2]")
                    txt = parent.inner_text()
                    likes_count = convert_count(txt)
            except:
                pass

            # =================================
            # COMMENTS COUNT
            # =================================
            comments_count = ""
            try:
                comment_button = page.locator("div[data-ad-rendering-role='comment_button']")
                print(f"\nComment Buttons: {comment_button.count()}")
                if comment_button.count() > 0:
                    parent = comment_button.first.locator("xpath=ancestor::div[2]")
                    txt = parent.inner_text()
                    comments_count = convert_count(txt)
            except:
                pass

            # =================================
            # SHARES COUNT
            # =================================
            shares_count = ""
            try:
                share_button = page.locator("div[data-ad-rendering-role='share_button']")
                print(f"\nShare Buttons: {share_button.count()}")
                if share_button.count() > 0:
                    parent = share_button.first.locator("xpath=ancestor::div[2]")
                    txt = parent.inner_text()
                    shares_count = convert_count(txt)
            except:
                pass

            print(f"\nLikes: {likes_count}")
            print(f"Comments: {comments_count}")
            print(f"Shares: {shares_count}")

            # =================================
            # LOAD ALL COMMENTS
            # =================================

            print("\nLoading ALL comments...")

            previous_count = 0
            same_count = 0

            for scroll in range(100):

                try:

                    spans = page.locator("span")

                    total_spans = spans.count()

                    for i in range(total_spans):

                        try:

                            txt = spans.nth(i).inner_text().strip().lower()

                            if any(x in txt for x in [

                                "view more comments",
                                "view previous comments",
                                "view all comments",
                                "see more comments",
                                "more comments",

                                "view more replies",
                                "view previous replies",
                                "view all replies",
                                "more replies",

                                "view 1 more comment",
                                "view 2 more comments",
                                "view 3 more comments",
                                "view 4 more comments",
                                "view 5 more comments"

                            ]):

                                spans.nth(i).scroll_into_view_if_needed()

                                time.sleep(1)

                                try:
                                    spans.nth(i).click(
                                        timeout=3000
                                    )

                                    print(
                                        f"Clicked: {txt}"
                                    )

                                    time.sleep(2)

                                except:
                                    pass

                        except:
                            pass

                except:
                    pass

                page.mouse.wheel(
                    0,
                    4000
                )

                time.sleep(4)

                comments = page.locator(
                    "div[aria-label^='Comment by']"
                )

                current_count = comments.count()

                print(
                    f"Comments Loaded: {current_count}"
                )

                if current_count == previous_count:

                    same_count += 1

                else:

                    same_count = 0

                if same_count >= 10:

                    print(
                        "\nNo more comments found."
                    )

                    break

                previous_count = current_count

            # =================================
            # FINAL COMMENTS
            # =================================
            comments = page.locator("div[aria-label^='Comment by']")
            comments_found = comments.count()
            print(
                "\nFacebook says comments:",
                comments_count
            )

            print(
                "Comments scraped:",
                comments.count()
            )
            print(f"\nFinal Comments: {comments_found}")

            # =================================
            # LOOP COMMENTS
            # =================================
            for c in range(comments_found):
                try:
                    comment = comments.nth(c)
                    comment_user = ""
                    comment_text = ""
                    comment_likes = ""

                    # =============================
                    # COMMENT USER
                    # =============================
                    try:
                        user_locator = comment.locator("a[role='link'] span")
                        if user_locator.count() > 0:
                            comment_user = user_locator.first.inner_text().strip()
                    except:
                        pass

                    # =============================
                    # COMMENT SEE MORE
                    # =============================
                    try:
                        for _ in range(5):
                            see_more_btns = comment.locator("div[role='button']")
                            btn_count = see_more_btns.count()
                            expanded = False
                            for b in range(btn_count):
                                try:
                                    txt = see_more_btns.nth(b).inner_text().strip().lower()
                                    if "see more" in txt or txt == "more":
                                        see_more_btns.nth(b).click()
                                        time.sleep(1.2)
                                        expanded = True
                                except:
                                    pass
                            if not expanded:
                                break
                    except:
                        pass

                    # =============================
                    # COMMENT TEXT
                    # =============================
                    try:
                        comment_text = ""
                        full_html = comment.inner_html()
                        soup = BeautifulSoup(full_html, "html.parser")

                        for btn in soup.find_all():
                            try:
                                txt = btn.get_text(strip=True).lower()
                                if "see more" in txt or txt == "more" or txt == "reply" or txt == "like":
                                    btn.decompose()
                            except:
                                pass

                        imgs = soup.find_all("img")
                        for img in imgs:
                            alt = img.get("alt")
                            if alt:
                                img.replace_with(f" {alt} ")

                        for a in soup.find_all("a"):
                            a.unwrap()

                        collected = []
                        real_divs = soup.find_all("div", attrs={"dir": "auto"})

                        for div in real_divs:
                            try:
                                txt = div.get_text(" ", strip=True)
                                extra_emojis = []
                                imgs = div.find_all("img")
                                for img in imgs:
                                    alt = img.get("alt")
                                    if alt:
                                        extra_emojis.append(alt)
                                if extra_emojis:
                                    txt += " " + " ".join(extra_emojis)

                                txt = re.sub(r"\s+", " ", txt).strip()
                                if not txt:
                                    continue

                                bad = ["Like", "Reply", "Most relevant", "Edited", "Top fan", "See more", "See More"]
                                skip = False
                                for b in bad:
                                    if txt == b:
                                        skip = True
                                        break
                                if skip:
                                    continue
                                if txt == comment_user:
                                    continue
                                if txt in collected:
                                    continue

                                collected.append(txt)
                            except:
                                pass

                        comment_text = " ".join(collected)
                        comment_text = re.sub(r"\s+", " ", comment_text).strip()
                    except:
                        pass

                    # =============================
                    # COMMENT LIKES
                    # =============================
                    try:
                        reaction_divs = comment.locator("div[aria-label*='reaction']")
                        reaction_count = reaction_divs.count()
                        for r in range(reaction_count):
                            try:
                                aria = reaction_divs.nth(r).get_attribute("aria-label")
                                if aria:
                                    match = re.search(r"(\d+)", aria)
                                    if match:
                                        comment_likes = int(match.group(1))
                                        break
                            except:
                                pass
                    except:
                        pass

                    # =============================
                    # TOP FAN
                    # =============================
                    top_fan = "No"
                    try:
                        comment_html = comment.inner_html()
                        if "Top fan" in comment_html:
                            top_fan = "Yes"
                    except:
                        pass

                    # =============================
                    # SKIP EMPTY
                    # =============================
                    if not comment_text:
                        continue

                    print("\n-----------------------------------")
                    print(f"USER: {comment_user}")
                    print("-----------------------------------")
                    print(comment_text)

                    # =============================
                    # SAVE DATA
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
                        "top_fan": top_fan
                    })

                except Exception as e:
                    print("Comment Error:", e)

            # =================================
            # SAVE CONTINUOUSLY
            # =================================
            save_output()

        except Exception as e:
            print("POST ERROR:", e)

    # =====================================
    # FINAL SAVE
    # =====================================
    save_output()
    browser.close()