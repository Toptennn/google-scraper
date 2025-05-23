import sys
if sys.platform.startswith("win"):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import time
import datetime
import io
import random
from urllib.parse import urlencode

import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_sync

# --------------------------------
# CONFIGURATION
# --------------------------------
PROXIES = []  # e.g. ["http://user:pass@proxy:port"]
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
]

MAX_RETRIES = 3
BACKOFF_BASE = 2  # backoff = BACKOFF_BASE ** retry_count
DEFAULT_MAX_PAGES = 100

# --------------------------------
# BROWSER SETUP
# --------------------------------
def setup_browser(proxy=None, user_agent=None):
    playwright = sync_playwright().start()
    launch_args = {"headless": True}
    if proxy:
        launch_args["proxy"] = {"server": proxy}
    browser = playwright.chromium.launch(**launch_args)
    context = browser.new_context(
        user_agent=user_agent or random.choice(USER_AGENTS),
        locale="en-US"
    )
    stealth_sync(context)
    return playwright, browser, context

# --------------------------------
# FETCH ONE PAGE
# --------------------------------
def fetch_page_results(context, url):
    page = context.new_page()
    results = []
    # 1) Block unnecessary resources (images, stylesheets, fonts)
    def block_resource(route):
        if route.request.resource_type in ["image", "stylesheet", "font"]:
            route.abort()
        else:
            route.continue_()
    page.route("**/*", block_resource)

    try:
        # 2) Wait only for DOMContentLoaded
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        # 3) Quick check: if no <h3> present, return immediately
        h3_elements = page.query_selector_all("h3")
        if not h3_elements:
            page.close()
            return []

        html = page.content()
        # guard against CAPTCHA
        if "detected unusual traffic" in html.lower():
            page.close()
            return []

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for h3 in h3_elements:
            title = h3.text_content().strip()
            href = h3.evaluate("node => node.parentNode.href")
            if title and href and href.startswith("http"):
                results.append({"title": title, "url": href, "timestamp": ts})
    except PlaywrightTimeout:
        # timeout on navigation or checks
        pass
    finally:
        page.close()
    return results

# --------------------------------
# ADVANCED SCRAPING
# --------------------------------
@st.cache_data(ttl=3600)
def scrape_google_advanced(params: dict, pause: float = 0.5, max_pages: int = DEFAULT_MAX_PAGES):
    all_results = []
    playwright, browser, context = setup_browser(
        proxy=random.choice(PROXIES) if PROXIES else None,
        user_agent=random.choice(USER_AGENTS) if USER_AGENTS else None
    )
    try:
        base = "https://www.google.com/search"
        for page_num in range(max_pages):
            p = params.copy()
            p["hl"] = "th"
            p["start"] = page_num * 10
            url = f"{base}?{urlencode(p)}"

            page_results = []
            for retry in range(MAX_RETRIES):
                page_results = fetch_page_results(context, url)
                if page_results:
                    break
                time.sleep(BACKOFF_BASE ** retry)

            # Stop immediately if no results on this page
            if not page_results:
                break

            all_results.extend(page_results)
            time.sleep(pause)

        return pd.DataFrame(all_results)
    finally:
        context.close()
        browser.close()
        playwright.stop()

# --------------------------------
# STREAMLIT UI
# --------------------------------
def main():
    st.title("Google Advanced Scraper")

    query        = st.text_input("คำค้นหาหลัก")
    all_words    = st.text_input("ทุกคำเหล่านี้")
    exact_phrase = st.text_input("ตรงวลีนี้")
    any_words    = st.text_input("คำใดๆ เหล่านี้")
    none_words   = st.text_input("ไม่รวมคำเหล่านี้")
    col1, col2   = st.columns(2)
    num_from     = col1.text_input("ตัวเลขตั้งแต่")
    num_to       = col2.text_input("ถึง")
    site         = st.text_input("ไซต์หรือโดเมน (site:)")

    filetype_options = {
        "รูปแบบใดก็ได้": "",
        "PDF (.pdf)": "pdf",  "PS (.ps)": "ps",
        "Word (.doc)": "doc","Excel (.xls)": "xls",
    }
    filetype = st.selectbox("ไฟล์นามสกุล", list(filetype_options.keys()))

    lang_options = {"ทุกภาษา":"","ไทย":"lang_th","อังกฤษ":"lang_en"}
    language    = st.selectbox("ภาษา", list(lang_options.keys()))

    country_options = {"ทุกประเทศ":"","ไทย":"countryTH","สหรัฐฯ":"countryUS"}
    region      = st.selectbox("สถานที่เผยแพร่", list(country_options.keys()))

    update_options = {"ทุกเวลา":"","24 ชม.":"d","สัปดาห์":"w","เดือน":"m"}
    last_update = st.selectbox("อัปเดตล่าสุด", list(update_options.keys()))

    if st.button("ค้นหา"):
        params = {}
        if query:        params["q"] = query
        if all_words:    params["as_q"] = all_words
        if exact_phrase: params["as_epq"] = exact_phrase
        if any_words:    params["as_oq"] = any_words
        if none_words:   params["as_eq"] = none_words
        if num_from:     params["as_nlo"] = num_from
        if num_to:       params["as_nhi"] = num_to
        if site:         params["as_sitesearch"] = site
        if filetype_options[filetype]: params["as_filetype"] = filetype_options[filetype]
        if lang_options[language]:     params["lr"] = lang_options[language]
        if country_options[region]:    params["cr"] = country_options[region]
        if update_options[last_update]:params["as_qdr"] = update_options[last_update]

        with st.spinner("กำลังค้นหา..."):
            df = scrape_google_advanced(params)
        if df.empty:
            st.warning("ไม่พบผลลัพธ์. ลองปรับพารามิเตอร์.")
        else:
            st.dataframe(df, use_container_width=True)
            csv_data = df.to_csv(index=False).encode("utf-8")
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            buf.seek(0)
            st.download_button("⬇️ ดาวน์โหลด CSV", csv_data, "results.csv", "text/csv")
            st.download_button("⬇️ ดาวน์โหลด Excel", buf, "results.xlsx",
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
