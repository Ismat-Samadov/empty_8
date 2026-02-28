"""
FutureLearn Course Scraper — Full Scale
Phase 1 : Collect all course URLs from search listing
Phase 2 : Visit each course detail page concurrently (async) for rich data
Saves results to data/data.csv

Usage:
    python scripts/courses.py            # full run
    python scripts/courses.py --limit 20 # scrape only first 20 courses (test)
"""

import asyncio
import csv
import json
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── Config ──────────────────────────────────────────────────────────────────
SEARCH_URL   = "https://www.futurelearn.com/search?q=*&filter_type=course"
BASE_URL     = "https://www.futurelearn.com"
OUTPUT_PATH  = Path(__file__).parent.parent / "data" / "data.csv"
CONCURRENCY  = 5          # parallel detail-page scrapers
PAGE_DELAY   = 2.0        # seconds between search pages
DETAIL_DELAY = 0.5        # polite delay per detail worker

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

CSV_FIELDS = [
    "title", "url", "partner", "partner_url", "course_type", "description",
    "category", "image_url",
    "duration_weeks", "hours_per_week", "level",
    "rating", "rating_count", "enrolled_count",
    "price", "currency", "start_date",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def new_context_kwargs() -> dict:
    return dict(
        user_agent=UA,
        viewport={"width": 1280, "height": 900},
        locale="en-GB",
    )


# ── Phase 1: search listing ──────────────────────────────────────────────────

async def scrape_search(browser, limit: int = 0) -> list[dict]:
    """Return list of base course dicts from the search results listing."""
    courses: list[dict] = []
    seen: set[str] = set()

    ctx = await browser.new_context(**new_context_kwargs())
    await ctx.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    page = await ctx.new_page()

    page_num = 1
    while True:
        url = SEARCH_URL if page_num == 1 else f"{SEARCH_URL}&page={page_num}"
        print(f"  [search] page {page_num}: {url}", flush=True)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except PlaywrightTimeout:
            print(f"  [search] timeout on page {page_num}.", flush=True)
            break

        try:
            await page.wait_for_selector(".m-link-list__item", timeout=15_000)
        except PlaywrightTimeout:
            print(f"  [search] no items on page {page_num}.", flush=True)
            break

        items = await page.query_selector_all(".m-link-list__item")
        print(f"  [search] {len(items)} items", flush=True)

        if not items:
            break

        page_new = 0
        for li in items:
            try:
                course = await _parse_search_item(li)
                if not course:
                    continue
                key = course["url"] or course["title"]
                if key in seen:
                    continue
                seen.add(key)
                courses.append(course)
                page_new += 1
                if limit and len(courses) >= limit:
                    break
            except Exception as exc:
                print(f"  [search] parse error: {exc}", flush=True)

        print(f"  [search] +{page_new} new (total {len(courses)})", flush=True)

        if limit and len(courses) >= limit:
            print(f"  [search] limit {limit} reached.", flush=True)
            break

        # Stop if this page added nothing new (pagination loops same data)
        if page_new == 0:
            print("  [search] no new courses — done.", flush=True)
            break

        page_num += 1
        await asyncio.sleep(PAGE_DELAY)

    await ctx.close()
    return courses[:limit] if limit else courses


async def _parse_search_item(li) -> dict | None:
    type_el = await li.query_selector("span.u-regular, span.u-no-margin-top")
    course_type = clean(await type_el.inner_text()) if type_el else ""

    title_el = await li.query_selector("h3 a")
    if not title_el:
        return None
    title = clean(await title_el.inner_text())
    href  = (await title_el.get_attribute("href")) or ""
    url   = (BASE_URL + href) if href.startswith("/") else href

    partner_el  = await li.query_selector("a[href*='/partners/']")
    partner     = clean(await partner_el.inner_text()) if partner_el else ""
    p_href      = (await partner_el.get_attribute("href")) if partner_el else ""
    partner_url = (BASE_URL + p_href) if p_href and p_href.startswith("/") else p_href

    desc_el     = await li.query_selector("p")
    description = clean(await desc_el.inner_text()) if desc_el else ""

    return {
        "title": title, "url": url,
        "partner": partner, "partner_url": partner_url,
        "course_type": course_type, "description": description,
        # detail fields filled in phase 2
        "category": "", "image_url": "",
        "duration_weeks": "", "hours_per_week": "", "level": "",
        "rating": "", "rating_count": "", "enrolled_count": "",
        "price": "", "currency": "", "start_date": "",
    }


# ── Phase 2: detail pages ─────────────────────────────────────────────────────

async def enrich_courses(browser, courses: list[dict]) -> None:
    """Visit each course URL and fill in detail fields. Mutates courses in-place."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    total = len(courses)

    async def worker(idx: int, course: dict) -> None:
        async with semaphore:
            url = course["url"]
            if not url:
                return
            try:
                await asyncio.sleep(DETAIL_DELAY * (idx % CONCURRENCY))
                ctx  = await browser.new_context(**new_context_kwargs())
                await ctx.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                )
                page = await ctx.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    detail = await _parse_detail(page)
                    course.update(detail)
                    print(
                        f"  [{idx+1}/{total}] {course['title'][:55]:<55} "
                        f"| {course['rating'] or '?'} stars | {course['price'] or 'free'} "
                        f"| {course['duration_weeks'] or '?'}w",
                        flush=True,
                    )
                except PlaywrightTimeout:
                    print(f"  [{idx+1}/{total}] TIMEOUT: {url}", flush=True)
                finally:
                    await page.close()
                    await ctx.close()
            except Exception as exc:
                print(f"  [{idx+1}/{total}] ERROR {url}: {exc}", flush=True)

    await asyncio.gather(*[worker(i, c) for i, c in enumerate(courses)])


async def _parse_detail(page) -> dict:
    detail: dict = {}

    # ── JSON-LD (most reliable) ──────────────────────────────────────────────
    scripts = await page.query_selector_all("script[type='application/ld+json']")
    for s in scripts:
        try:
            data = json.loads(await s.inner_html())
            if data.get("@type") == "Product":
                detail["rating"]      = str(data.get("aggregateRating", {}).get("ratingValue", ""))
                detail["rating_count"]= str(data.get("aggregateRating", {}).get("reviewCount", ""))
                offer = data.get("offers", {})
                detail["price"]       = str(offer.get("price", ""))
                detail["currency"]    = offer.get("priceCurrency", "")
                detail["start_date"]  = offer.get("validFrom", "")
                detail["image_url"]   = data.get("image", "")
            elif data.get("@type") == "BreadcrumbList":
                items = data.get("itemListElement", [])
                # category = 2nd breadcrumb (index 1), skip first "Courses"
                if len(items) >= 2:
                    detail["category"] = items[1].get("item", {}).get("name", "")
        except Exception:
            pass

    # ── Key info block (duration, hours) ────────────────────────────────────
    key_info_el = await page.query_selector("[class*='keyInfo-module_wrapper']")
    if not key_info_el:
        key_info_el = await page.query_selector("[class*='keyInfo']")
    key_info_text = clean(await key_info_el.inner_text()) if key_info_el else ""

    if not key_info_text:
        # fallback: scan full page text for patterns
        key_info_text = clean(await page.inner_text("body"))[:3000]

    wk = re.search(r"(\d+)\s*weeks?", key_info_text, re.IGNORECASE)
    if wk:
        detail["duration_weeks"] = wk.group(1)

    hr = re.search(r"(\d+)\s*hours?\s*(?:per\s*week|/\s*week)", key_info_text, re.IGNORECASE)
    if hr:
        detail["hours_per_week"] = hr.group(1)

    # ── Level ────────────────────────────────────────────────────────────────
    level_el = await page.query_selector("[class*='listItemWithIcon'] [class*='text']")
    if level_el:
        level_candidates = []
        items = await page.query_selector_all("[class*='listItemWithIcon'] [class*='text-module']")
        for it in items:
            t = clean(await it.inner_text())
            if re.search(r"\b(Beginner|Intermediate|Advanced|Introductory|General)\b", t, re.IGNORECASE):
                level_candidates.append(t)
        if level_candidates:
            detail["level"] = level_candidates[0]

    # ── Enrolled count ───────────────────────────────────────────────────────
    enrol_el = await page.query_selector("[class*='enrol']")
    if enrol_el:
        enrol_text = clean(await enrol_el.inner_text())
        count_m = re.search(r"([\d,]+)", enrol_text)
        if count_m:
            detail["enrolled_count"] = count_m.group(1).replace(",", "")

    return detail


# ── CSV ───────────────────────────────────────────────────────────────────────

def save_csv(courses: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(courses)
    print(f"\nSaved {len(courses)} courses -> {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main_async(limit: int = 0) -> None:
    print("FutureLearn full-scale scraper")
    print(f"Search : {SEARCH_URL}")
    print(f"Limit  : {limit if limit else 'all'}")
    print(f"Workers: {CONCURRENCY}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        # Phase 1
        print("=== Phase 1: collecting course URLs ===")
        courses = await scrape_search(browser, limit=limit)
        print(f"\nCollected {len(courses)} courses.\n")

        if not courses:
            print("No courses found — aborting.")
            await browser.close()
            return

        # Phase 2
        print("=== Phase 2: scraping detail pages ===")
        await enrich_courses(browser, courses)

        await browser.close()

    print(f"\nTotal courses enriched: {len(courses)}")
    save_csv(courses, OUTPUT_PATH)


def main() -> None:
    limit = 0
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        limit = int(sys.argv[idx + 1])

    asyncio.run(main_async(limit=limit))


if __name__ == "__main__":
    main()
