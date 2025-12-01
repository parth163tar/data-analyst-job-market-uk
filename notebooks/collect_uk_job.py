import os
import time
import math
import requests
import pandas as pd
from urllib.parse import urlencode
from dotenv import load_dotenv

# -----------------------------
# 1. Load API credentials
# -----------------------------
load_dotenv()
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not APP_ID or not APP_KEY:
    raise ValueError("Please set ADZUNA_APP_ID and ADZUNA_APP_KEY in your .env file")

# -----------------------------
# 2. Basic settings
# -----------------------------
COUNTRY = "gb"  # UK
WHAT = "data analyst"  # search term
WHERE = "Birmingham"
RESULTS_PER_PAGE = 50      # max per Adzuna docs (often 50)
MAX_RESULTS = 2000         # how many jobs you want to fetch in total
SLEEP_BETWEEN_CALLS = 1.0  # seconds – be polite to the API

# Output file
OUTPUT_CSV = "uk_data_analyst_jobs.csv"

# -----------------------------
# 3. Helper: build request URL
# -----------------------------
BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def build_url(page: int) -> str:
    """
    Build the Adzuna API URL for the given page.
    """
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": WHAT,
        "where": WHERE,
        "content-type": "application/json"
    }
    query_string = urlencode(params)
    return BASE_URL.format(country=COUNTRY, page=page) + "?" + query_string


# -----------------------------
# 4. Fetch a single page
# -----------------------------
def fetch_page(page: int) -> list:
    """
    Fetch a single page of results from Adzuna.
    Returns a list of job dictionaries.
    """
    url = build_url(page)
    print(f"Fetching page {page}: {url}")
    resp = requests.get(url, timeout=15)

    if resp.status_code != 200:
        print(f"⚠️ Error {resp.status_code}: {resp.text}")
        return []

    data = resp.json()
    # 'results' is a list of job entries
    return data.get("results", [])


# -----------------------------
# 5. Normalise a single job record
# -----------------------------
def parse_job(job: dict) -> dict:
    """
    Extract and normalise fields from a raw Adzuna job record.
    Adjust fields as you like.
    """
    # Some fields might be missing, so use .get()
    return {
        "job_id": job.get("id"),
        "title": job.get("title"),
        "company": job.get("company", {}).get("display_name"),
        "category": job.get("category", {}).get("label"),
        "location_display": job.get("location", {}).get("display_name"),
        "city": job.get("location", {}).get("area", [None, None, None])[-1],
        "contract_type": job.get("contract_type"),
        "contract_time": job.get("contract_time"),
        "created": job.get("created"),
        "description": job.get("description"),
        "redirect_url": job.get("redirect_url"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_is_predicted": job.get("salary_is_predicted"),
    }


# -----------------------------
# 6. Main collection logic
# -----------------------------
def collect_jobs(max_results: int = MAX_RESULTS) -> pd.DataFrame:
    """
    Collect up to max_results job postings into a DataFrame.
    """
    all_jobs = []

    # Rough estimate of how many pages we need
    pages_needed = math.ceil(max_results / RESULTS_PER_PAGE)

    for page in range(1, pages_needed + 1):
        jobs = fetch_page(page)
        if not jobs:
            print("No results returned, stopping.")
            break

        for j in jobs:
            parsed = parse_job(j)
            all_jobs.append(parsed)

            if len(all_jobs) >= max_results:
                print("Reached max_results limit.")
                break

        if len(all_jobs) >= max_results:
            break

        # Be polite – small delay between requests
        time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"Collected {len(all_jobs)} job postings.")
    df = pd.DataFrame(all_jobs)

    # Drop rows without title or description (optional)
    df = df.dropna(subset=["title", "description"])

    return df


# -----------------------------
# 7. Run script
# -----------------------------
if __name__ == "__main__":
    df_jobs = collect_jobs()
    print(df_jobs.head())

    # Save to CSV
    df_jobs.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(df_jobs)} job postings to {OUTPUT_CSV}")
