import time
import datetime
import io
from urllib.parse import urlencode

import streamlit as st
import pandas as pd

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

MAX_RETRIES = 3
BACKOFF_BASE = 2  # sleep = BACKOFF_BASE ** retry


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.stylesheets": 2,
        "profile.default_content_setting_values.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)
    try:
        driver.minimize_window()
    except:
        pass
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setBlockedURLs", {
        "urls": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.css", "*.woff", "*.ttf"]
    })
    return driver


def fetch_one_page_url(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "h3"))
        )
    except TimeoutException:
        return []

    html = driver.page_source
    if "detected unusual traffic" in html.lower():
        raise Exception("CAPTCHA detected or blocked by Google")

    soup = BeautifulSoup(html, "lxml")
    items = []
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for h3 in soup.find_all("h3"):
        a = h3.find_parent("a", href=True)
        if not a:
            continue
        href = a["href"]
        title = h3.get_text(strip=True)
        if href.startswith("http") and title:
            items.append({
                "title": title,
                "url": href,
                "timestamp": timestamp
            })
    return items


def scrape_google_advanced(params: dict, pause: float = 0.5):
    driver = create_driver()
    all_results = []
    page_num = 0
    base = "https://www.google.com/search"

    try:
        while True:
            p = params.copy()
            p["hl"] = "th"
            p["start"] = page_num * 10
            url = f"{base}?{urlencode(p)}"

            for retry in range(MAX_RETRIES):
                try:
                    page_results = fetch_one_page_url(driver, url)
                    break
                except (WebDriverException, Exception):
                    time.sleep(BACKOFF_BASE ** retry)
            else:
                break

            if not page_results:
                break

            all_results.extend(page_results)
            page_num += 1
            time.sleep(pause)

        return all_results
    finally:
        driver.quit()


def main():
    st.title("Google Advanced Scraper")

    # คำค้นหาหลัก
    query = st.text_input("คำค้นหาหลัก")

    # ฟิลด์ Advanced Search
    all_words    = st.text_input("ทุกคำเหล่านี้")
    exact_phrase = st.text_input("ตรงวลีนี้")
    any_words    = st.text_input("คำใดๆ เหล่านี้")
    none_words   = st.text_input("ไม่รวมคำเหล่านี้")

    # ตัวเลขตั้งแต่ ... ถึง ... ในบรรทัดเดียวกัน
    col1, col2 = st.columns(2)
    num_from = col1.text_input("ตัวเลขตั้งแต่", key="num_from")
    num_to   = col2.text_input("ถึง", key="num_to")

    site = st.text_input("ไซต์หรือโดเมน (site:)")

    # เปลี่ยนเป็น dropdown ตามรูป
    filetype_options = {
        "รูปแบบใดก็ได้":               "",
        "Adobe Acrobat PDF (.pdf)":    "pdf",
        "Adobe PostScript (.ps)":       "ps",
        "Autodesk DWF (.dwf)":         "dwf",
        "Google Earth KML (.kml)":     "kml",
        "Google Earth KMZ (.kmz)":     "kmz",
        "Microsoft Excel (.xls)":      "xls",
        "Microsoft PowerPoint (.ppt)": "ppt",
        "Microsoft Word (.doc)":       "doc",
        "Rich Text Format (.rtf)":     "rtf",
        "Shockwave Flash (.swf)":      "swf",
    }
    filetype = st.selectbox("ไฟล์นามสกุล", list(filetype_options.keys()))

    # Dropdown ภาษา
    lang_options = {
        "ทุกภาษา":    "",
        "ภาษาไทย":   "lang_th",
        "อังกฤษ":     "lang_en",
        "ญี่ปุ่น":    "lang_ja",
        "เยอรมัน":   "lang_de",
        "ฝรั่งเศส":   "lang_fr",
    }
    language = st.selectbox("ภาษา", list(lang_options.keys()))

    # Dropdown ประเทศ
    country_options = {
        "ทุกประเทศ":       "",
        "ไทย":              "countryTH",
        "สหรัฐอเมริกา":     "countryUS",
        "ญี่ปุ่น":          "countryJP",
        "เยอรมนี":         "countryDE",
        "ฝรั่งเศส":        "countryFR",
    }
    region = st.selectbox("สถานที่เผยแพร่", list(country_options.keys()))

    # Dropdown อัปเดตล่าสุด
    update_options = {
        "ทุกเวลา":             "",
        "24 ชั่วโมงที่ผ่านมา": "d",
        "สัปดาห์ที่ผ่านมา":    "w",
        "เดือนที่ผ่านมา":      "m",
        "ปีที่ผ่านมา":        "y",
    }
    last_update = st.selectbox("อัปเดตล่าสุด", list(update_options.keys()))

    if st.button("ค้นหา"):
        params = {}
        if query:
            params["q"] = query
        if all_words:
            params["as_q"] = all_words
        if exact_phrase:
            params["as_epq"] = exact_phrase
        if any_words:
            params["as_oq"] = any_words
        if none_words:
            params["as_eq"] = none_words
        if num_from:
            params["as_nlo"] = num_from
        if num_to:
            params["as_nhi"] = num_to
        if site:
            params["as_sitesearch"] = site
        if filetype_options[filetype]:
            params["as_filetype"] = filetype_options[filetype]
        if lang_options[language]:
            params["lr"] = lang_options[language]
        if country_options[region]:
            params["cr"] = country_options[region]
        if update_options[last_update]:
            params["as_qdr"] = update_options[last_update]

        with st.spinner("กำลังค้นหา..."):
            results = scrape_google_advanced(params)

        if not results:
            st.info("ไม่พบผลลัพธ์ใด ๆ")
            return

        df = pd.DataFrame(results)
        st.dataframe(df)

        # ดาวน์โหลด CSV
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ ดาวน์โหลด CSV",
            data=csv_data,
            file_name="google_results.csv",
            mime="text/csv"
        )

        # ดาวน์โหลด Excel
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="results")
        towrite.seek(0)
        st.download_button(
            label="⬇️ ดาวน์โหลด Excel",
            data=towrite,
            file_name="google_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


if __name__ == "__main__":
    main()
