# Google Advanced Scraper

A Streamlit-based application offering three different methods to scrape Google search results:

* **CSE API** (`google_scraper_cse.py`): Uses Google Custom Search JSON API for up to 100 results.
* **Playwright** (`google_scraper_pw.py`): Browser automation with Playwright and stealth techniques.
* **Selenium** (`google_scraper_sel.py`): Browser-driven scraping with undetected-chromedriver and BeautifulSoup.

## Features

* **Advanced search parameters**: main query, all words, exact phrase, any words, exclude words, numeric range, site/domain, filetype, language, region, date restrict.
* **Export options**: Download results as CSV or Excel.
* **Streamlit UI**: Interactive interface with real‑time feedback and download buttons.
* **Caching**: Results are cached (`@st.cache_data`) to reduce repeated calls.

## Prerequisites

* **Python 3.7+**
* **Google Chrome** (required by Selenium and Playwright)
* **Node.js** (for Playwright browser binaries)

## Installation

```bash
git clone <repo-url>
cd <repo>
pip install -r requirements.txt
playwright install  # install browser dependencies for Playwright
```

## Configuration

1. Move or copy the provided `secrets.toml` into the Streamlit folder:

   ```
   mkdir -p .streamlit
   cp secrets.toml .streamlit/secrets.toml
   ```
2. Edit `.streamlit/secrets.toml` and set your API credentials:

   ```toml
   GOOGLE_API_KEY = "<YOUR_API_KEY>"
   CUSTOM_SEARCH_ENGINE_ID = "<YOUR_CSE_ID>"
   ```

## Usage

### CSE API Scraper

```bash
streamlit run google_scraper_cse.py
```

### Playwright Scraper

```bash
streamlit run google_scraper_pw.py
```

### Selenium Scraper

```bash
streamlit run google_scraper_sel.py
```

1. Open the local URL shown in your terminal.
2. Fill in the search fields or advanced options.
3. Click **ค้นหา** to fetch results.
4. Use the **Download** buttons to save CSV or Excel files.

