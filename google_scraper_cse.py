import datetime
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

# ======= Configuration =======
API_KEY = st.secrets["GOOGLE_API_KEY"]       # Your Google API Key
CSE_ID = st.secrets["CUSTOM_SEARCH_ENGINE_ID"]  # Your Custom Search Engine ID
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# ======= Helper Functions =======
@st.cache_data
def fetch_google_results(
    query: str,
    extra_params: Optional[Dict[str, str]] = None
) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetch all available search results via Google CSE API.
    Supports paging up to 100 results (in batches of 10).
    extra_params: map of additional CSE API parameters (exactTerms, excludeTerms, fileType, siteSearch, lr, cr, dateRestrict)
    Returns list of dicts (title, link, date_scraped) and error message if any.
    """
    if not query:
        return [], "Search query cannot be empty"
    if not API_KEY:
        return [], "Missing Google API key in Streamlit secrets"
    if not CSE_ID:
        return [], "Missing Custom Search Engine ID in Streamlit secrets"

    all_results: List[Dict] = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # loop pages of 10 results, start at 1
    for start in range(1, 101, 10):
        params = {
            "key": API_KEY,
            "cx": CSE_ID,
            "q": query,
            "start": start,
            "num": 10,
            # default geo and interface
            "gl": "th",
            "hl": "th",
        }
        if extra_params:
            params.update(extra_params)

        try:
            resp = requests.get(SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as err:
            code = resp.status_code
            if code == 403:
                return [], "API quota exceeded or invalid key"
            return [], f"HTTP error: {err}"
        except Exception as err:
            return [], f"Request error: {err}"

        items = data.get("items")
        if not items:
            # no more results
            break

        for it in items:
            all_results.append({
                "title": it.get("title", ""),
                "link": it.get("link", ""),
                "date_scraped": now,
            })

    return all_results, None


def build_query_and_params(
    query: str,
    all_words: str,
    exact_phrase: str,
    any_words: str,
    none_words: str,
    num_from: str,
    num_to: str,
    site: str,
    filetype_ext: str,
    lr: str,
    cr: str,
    date_restrict: str
) -> Tuple[str, Dict[str, str]]:
    """
    Construct the CSE API query string and extra_params mapping from advanced fields.
    """
    terms: List[str] = []
    # main words
    if all_words:
        terms += all_words.split()
    # exact phrase
    if exact_phrase:
        terms.append(f'"{exact_phrase}"')
    # any of these words
    if any_words:
        group = " OR ".join(any_words.split())
        terms.append(f'({group})')
    # exclude
    if none_words:
        terms += [f'-{w}' for w in none_words.split()]
    # numeric range
    if num_from and num_to:
        terms.append(f'{num_from}..{num_to}')
    # site
    if site:
        terms.append(f'site:{site}')

    # base query = user query or advanced terms
    q = query or " ".join(terms)
    if query and terms:
        # combine main query with advanced
        q = f"{query} " + " ".join(terms)

    extras: Dict[str, str] = {}
    if filetype_ext:
        extras["fileType"] = filetype_ext
    if lr:
        extras["lr"] = lr
    if cr:
        extras["cr"] = cr
    if date_restrict:
        extras["dateRestrict"] = date_restrict

    return q, extras


# ======= Streamlit UI =======

def main():
    st.set_page_config(page_title="Google Advanced Scraper", layout="wide")
    st.title("Google Advanced Scraper")

    # input fields
    query = st.text_input("คำค้นหาหลัก (Main Query)")
    all_words = st.text_input("ทุกคำเหล่านี้ (All words)")
    exact_phrase = st.text_input("ตรงวลีนี้ (Exact phrase)")
    any_words = st.text_input("คำใดๆ เหล่านี้ (Any of these words)")
    none_words = st.text_input("ไม่รวมคำเหล่านี้ (None of these words)")
    col1, col2 = st.columns(2)
    num_from = col1.text_input("ตัวเลขตั้งแต่ (Number from)", key="num_from")
    num_to = col2.text_input("ถึง (Number to)", key="num_to")
    site = st.text_input("ไซต์หรือโดเมน (site:)")

    filetype_options = {
        "รูปแบบใดก็ได้": "",
        "pdf": "pdf",
        "doc": "doc",
        "xls": "xls",
        "ppt": "ppt",
    }
    filetype = st.selectbox("File type", list(filetype_options.keys()))

    lang_options = {
        "ทุกภาษา": "",
        "ภาษาไทย": "lang_th",
        "อังกฤษ": "lang_en",
    }
    lr = lang_options[st.selectbox("Language restrict", list(lang_options.keys()))]

    country_options = {
        "ทุกประเทศ": "",
        "ไทย": "countryTH",
        "สหรัฐ": "countryUS",
    }
    cr = country_options[st.selectbox("Country restrict", list(country_options.keys()))]

    date_options = {
        "ทุกเวลา": "",
        "24 ชั่วโมงล่าสุด": "d1",
        "สัปดาห์ล่าสุด": "w1",
        "เดือนล่าสุด": "m1",
    }
    date_restrict = date_options[st.selectbox("Date restrict", list(date_options.keys()))]

    if st.button("ค้นหา"):
        q, extras = build_query_and_params(
            query, all_words, exact_phrase, any_words, none_words,
            num_from, num_to, site, filetype_options[filetype], lr, cr, date_restrict
        )
        with st.spinner(f"ค้นหา '{q}'..."):
            results, error = fetch_google_results(q, extras)
        if error:
            st.error(error)
            return
        if not results:
            st.info("ไม่พบผลลัพธ์")
            return

        df = pd.DataFrame(results)
        st.success(f"พบ {len(df)} ผลลัพธ์")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="results.csv", mime="text/csv")

        towrite = pd.io.common.BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="results")
        towrite.seek(0)
        st.download_button("Download Excel", data=towrite.read(), file_name="results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()