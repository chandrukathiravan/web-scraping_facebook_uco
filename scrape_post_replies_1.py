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

INPUT_EXCEL = "output/uco_post_urls.xlsx"

OUTPUT_EXCEL = "output/uco_complete_data_1.xlsx"

OUTPUT_CSV = "output/uco_complete_data_1.csv"

os.makedirs("output", exist_ok=True)

all_data = []

# =========================================
# CONVERT COUNTS
# =========================================

def convert_count(value):

    if not value:
        return 0

    value = str(value).replace(",", "").strip()

    try:

        if "K" in value:

            return int(
                float(
                    value.replace("K", "")
                ) * 1000
            )

        elif "M" in value:

            return int(
                float(
                    value.replace("M", "")
                ) * 1000000
            )

        else:

            return int(value)

    except:

        return 0

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
# READ URL FILE
# =========================================

df_urls = pd.read_excel(
    INPUT_EXCEL
)

post_urls = df_urls[
    "post_url"
].drop_duplicates().tolist()

print(
    f"\nTotal URLs Loaded: {len(post_urls)}"
)

# =========================================
# START PLAYWRIGHT
# =========================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context()

    load_cookies(context)

    page = context.new_page()

    # =====================================
    # LOOP URLS
    # =====================================

    for idx, post_url in enumerate(post_urls):

        try:

            print("\n===================================")
            print(
                f"POST {idx + 1}"
            )
            print("===================================")

            print(
                f"\nOpening:\n{post_url}"
            )

            page.goto(
                post_url,
                timeout=60000
            )

            time.sleep(6)

            # =================================
            # MAIN POST
            # =================================

            post_text = ""

            try:

                main_post = page.locator(
                    "article[data-testid='tweet']"
                ).first

                post_text = main_post.locator(
                    "[data-testid='tweetText']"
                ).inner_text()

            except:
                pass

            # =================================
            # POST DATE
            # =================================

            post_date = ""

            try:

                raw_date = page.locator(
                    "time"
                ).first.get_attribute(
                    "datetime"
                )

                post_date = datetime.fromisoformat(
                    raw_date.replace(
                        "Z",
                        "+00:00"
                    )
                ).date()

            except:
                pass

            # =================================
            # LIKES
            # =================================

            likes = ""

            try:

                likes = page.locator(
                    "[data-testid='like']"
                ).first.inner_text()

            except:
                pass

            # =================================
            # RETWEETS
            # =================================

            retweets = ""

            try:

                retweets = page.locator(
                    "[data-testid='retweet']"
                ).first.inner_text()

            except:
                pass

            # =================================
            # REPLIES COUNT
            # =================================

            replies = ""

            try:

                replies = page.locator(
                    "[data-testid='reply']"
                ).first.inner_text()

            except:
                pass

            # =================================
            # VIEWS
            # =================================

            views = ""

            try:

                analytics = page.locator(
                    "a[href*='analytics']"
                ).inner_text()

                views = analytics.split()[0]

            except:
                pass

            print("\nPOST DETAILS")
            print(post_text)

            print(f"\nLikes: {likes}")
            print(f"Replies: {replies}")
            print(f"Retweets: {retweets}")
            print(f"Views: {views}")

            # =================================
            # SAVE POST
            # =================================

            all_data.append({

                "type": "POST",

                "post_date": str(post_date),

                "post_url": post_url,

                "post_text": post_text,

                "likes": likes,

                "likes_num": convert_count(
                    likes
                ),

                "retweets": retweets,

                "retweets_num": convert_count(
                    retweets
                ),

                "replies": replies,

                "replies_num": convert_count(
                    replies
                ),

                "views": views,

                "views_num": convert_count(
                    views
                ),

                "reply_user": "",

                "reply_text": "",

                "reply_likes": ""
            })

            # =================================
            # LOAD REPLIES SLOWLY
            # =================================

            print(
                "\nLoading replies slowly..."
            )

            MAX_REPLY_SCROLLS = 40

            for scroll_num in range(MAX_REPLY_SCROLLS):

                page.mouse.wheel(
                    0,
                    1000
                )

                time.sleep(3)

                discover_locator = page.locator(
                    "span:has-text('Discover more')"
                )

                if discover_locator.count() > 0:

                    print(
                        "\nDiscover More detected."
                    )

                    break

            # =================================
            # GET DISCOVER MORE Y POSITION
            # =================================

            discover_y = None

            try:

                discover_locator = page.locator(
                    "span:has-text('Discover more')"
                ).first

                if discover_locator.count() > 0:

                    box = discover_locator.bounding_box()

                    if box:

                        discover_y = box["y"]

                        print(
                            f"\nDiscover More Y Position: "
                            f"{discover_y}"
                        )

            except:
                pass

            # =================================
            # RELOAD REPLIES
            # =================================

            reply_articles = page.locator(
                "article[data-testid='tweet']"
            )

            reply_count = reply_articles.count()

            print(
                f"\nReply Articles Found: "
                f"{reply_count}"
            )

            seen_reply_texts = set()

            # =================================
            # SCRAPE REPLIES
            # =================================

            for j in range(1, reply_count):

                try:

                    reply = reply_articles.nth(j)

                    # =================================
                    # SKIP BELOW DISCOVER MORE
                    # =================================

                    if discover_y is not None:

                        try:

                            reply_box = reply.bounding_box()

                            if reply_box:

                                reply_y = reply_box["y"]

                                if reply_y > discover_y:

                                    print(
                                        "Skipped Below Discover More"
                                    )

                                    continue

                        except:
                            pass

                    # =================================
                    # FULL BLOCK
                    # =================================

                    try:

                        full_reply_block = (
                            reply.inner_text()
                        )

                    except:

                        continue

                    # =================================
                    # REMOVE JUNK
                    # =================================

                    banned_words = [

                        "Discover more",

                        "Who to follow",

                        "You might like",

                        "Promoted",

                        "Relevant people",

                        "Trending",

                        "Sourced from across X",

                        "Follow",

                        "Subscribe"
                    ]

                    skip = False

                    for word in banned_words:

                        if word.lower() in full_reply_block.lower():

                            skip = True
                            break

                    if skip:
                        continue

                    # =================================
                    # MUST HAVE REPLY BUTTON
                    # =================================

                    reply_btn = reply.locator(
                        "[data-testid='reply']"
                    )

                    if reply_btn.count() == 0:
                        continue

                    # =================================
                    # MUST HAVE REAL TWEET TEXT
                    # =================================

                    tweet_locator = reply.locator(
                        "[data-testid='tweetText']"
                    )

                    if tweet_locator.count() == 0:
                        continue

                    # =================================
                    # COMPLETE REPLY TEXT
                    # =================================

                    reply_text_parts = []

                    block_count = tweet_locator.count()

                    for b in range(block_count):

                        try:

                            txt = tweet_locator.nth(
                                b
                            ).inner_text().strip()

                            if txt:

                                reply_text_parts.append(
                                    txt
                                )

                        except:
                            pass

                    reply_text = "\n".join(
                        reply_text_parts
                    ).strip()

                    if not reply_text:
                        continue

                    if len(reply_text) < 3:
                        continue

                    # =================================
                    # DUPLICATES
                    # =================================

                    if reply_text in seen_reply_texts:
                        continue

                    seen_reply_texts.add(
                        reply_text
                    )

                    # =================================
                    # USER
                    # =================================

                    reply_user = ""

                    try:

                        user_spans = reply.locator(
                            "div[data-testid='User-Name'] span"
                        )

                        user_count = user_spans.count()

                        for u in range(user_count):

                            txt = user_spans.nth(
                                u
                            ).inner_text().strip()

                            if txt:

                                reply_user = txt
                                break

                    except:
                        pass

                    if not reply_user:
                        continue

                    # =================================
                    # SKIP MAIN ACCOUNT
                    # =================================

                    if "@UCOBankOfficial" in reply_user:
                        continue

                    # =================================
                    # REPLY LIKES
                    # =================================

                    reply_likes = ""

                    try:

                        reply_likes = reply.locator(
                            "[data-testid='like']"
                        ).inner_text()

                    except:
                        pass

                    print("\n-----------------------------------")
                    print(f"USER: {reply_user}")
                    print("-----------------------------------")

                    print(reply_text)

                    # =================================
                    # SAVE REPLY
                    # =================================

                    all_data.append({

                        "type": "REPLY",

                        "post_date": str(post_date),

                        "post_url": post_url,

                        "post_text": post_text,

                        "likes": likes,

                        "likes_num": convert_count(
                            likes
                        ),

                        "retweets": retweets,

                        "retweets_num": convert_count(
                            retweets
                        ),

                        "replies": replies,

                        "replies_num": convert_count(
                            replies
                        ),

                        "views": views,

                        "views_num": convert_count(
                            views
                        ),

                        "reply_user": reply_user,

                        "reply_text": reply_text,

                        "reply_likes": reply_likes
                    })

                except Exception as e:

                    print(
                        "Reply Error:",
                        e
                    )

        except Exception as e:

            print(
                "Post Error:",
                e
            )

    # =====================================
    # SAVE OUTPUT
    # =====================================

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
    print("SCRAPING COMPLETED")
    print("===================================")

    print(
        f"\nTotal Records: {len(df)}"
    )

    print(
        f"\nExcel: {OUTPUT_EXCEL}"
    )

    print(
        f"CSV: {OUTPUT_CSV}"
    )

    browser.close()