# pyrefly: ignore [missing-import]

from playwright.sync_api import sync_playwright
import json
import os

# =========================================
# PROFILE FOLDER
# =========================================

PROFILE_DIR = "facebook_profile"

os.makedirs(
    PROFILE_DIR,
    exist_ok=True
)

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

        # =================================
        # FACEBOOK EXPORT FIX
        # =================================

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
# START
# =========================================

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(

        user_data_dir=PROFILE_DIR,

        headless=False,

        viewport={

            "width": 1366,

            "height": 768
        },

        user_agent=(

            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/136.0.0.0 "
            "Safari/537.36"
        ),

        locale="en-US",

        timezone_id="Asia/Kolkata",

        geolocation={

            "latitude": 22.5726,

            "longitude": 88.3639
        },

        permissions=[

            "geolocation"
        ],

        args=[

            "--disable-blink-features=AutomationControlled",

            "--start-maximized"
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

    # =====================================
    # PAGE
    # =====================================

    page = browser.new_page()

    # =====================================
    # TIMEOUTS
    # =====================================

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
        12000
    )

    print(
        f"\nCurrent URL:\n{page.url}"
    )

    print(
        f"\nTitle:\n{page.title()}"
    )

    # =====================================
    # SCREENSHOT
    # =====================================

    page.screenshot(

        path="facebook_home.png",

        full_page=True
    )

    # =====================================
    # OPEN UCO PAGE
    # =====================================

    print(
        "\nOpening UCO Page..."
    )

    page.goto(
        "https://www.facebook.com/officialUCOBank",
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(
        15000
    )

    # =====================================
    # DEBUG
    # =====================================

    print(
        f"\nFinal URL:\n{page.url}"
    )

    print(
        f"\nFinal Title:\n{page.title()}"
    )

    # =====================================
    # SAVE SCREENSHOT
    # =====================================

    page.screenshot(

        path="facebook_uco.png",

        full_page=True
    )

    print(
        "\nScreenshots saved:"
    )

    print(
        "facebook_home.png"
    )

    print(
        "facebook_uco.png"
    )

    # =====================================
    # KEEP OPEN
    # =====================================

    input(
        "\nPress ENTER to close..."
    )

    browser.close()