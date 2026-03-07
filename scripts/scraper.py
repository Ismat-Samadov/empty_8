import requests
import pandas as pd
import time
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://www.million.az/_next/data/{build_id}/az{path}"
MAIN_URL = "https://www.million.az/_next/data/{build_id}/az.json"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "x-nextjs-data": "1",
    "referer": "https://www.million.az/",
    "dnt": "1",
}

OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "data.csv"


def get_build_id() -> str:
    """Extract the Next.js build ID from the main HTML page."""
    r = requests.get("https://www.million.az/az", headers={
        "user-agent": HEADERS["user-agent"],
        "accept": "text/html",
    }, timeout=30)
    r.raise_for_status()
    match = re.search(r'"buildId"\s*:\s*"([^"]+)"', r.text)
    if not match:
        raise ValueError("Could not find Next.js buildId in page HTML")
    return match.group(1)


def fetch_categories(build_id: str) -> list[dict]:
    """Fetch all service categories from the main page API."""
    url = MAIN_URL.format(build_id=build_id)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["pageProps"]["services"]


def fetch_category_merchants(build_id: str, slug: str) -> list[dict]:
    """Fetch all merchants for a given category slug."""
    url = BASE_URL.format(build_id=build_id, path=f"/services/{slug}.json")
    r = requests.get(url, params={"slug": slug}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["pageProps"].get("services", [])


def main():
    print("Fetching build ID...")
    build_id = get_build_id()
    print(f"Build ID: {build_id}")

    print("Fetching categories...")
    categories = fetch_categories(build_id)
    print(f"Found {len(categories)} categories: {[c['name'] for c in categories]}")

    all_rows = []

    for cat in categories:
        slug = cat["name"]
        display = cat.get("displayName", slug)
        print(f"  Scraping [{slug}] ({display})...", end=" ", flush=True)

        try:
            merchants = fetch_category_merchants(build_id, slug)
            print(f"{len(merchants)} merchants")

            for m in merchants:
                all_rows.append({
                    "category_slug": slug,
                    "category_name": display,
                    "merchant_id": m.get("id"),
                    "merchant_name": m.get("name"),
                    "merchant_display_name": m.get("displayName"),
                    "description": m.get("description"),
                    "hint": m.get("hint"),
                    "link": m.get("link"),
                    "icon": m.get("icon"),
                    "png_icon": m.get("pngIcon"),
                    "row_number": m.get("rowNumber"),
                    "m10": m.get("m10"),
                    "web": m.get("web"),
                    "mobile_ios": m.get("mobileIos"),
                    "mobile_android": m.get("mobileAndroid"),
                })
        except Exception as e:
            print(f"ERROR: {e}")

        time.sleep(0.3)

    if not all_rows:
        print("No data collected.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(df)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
