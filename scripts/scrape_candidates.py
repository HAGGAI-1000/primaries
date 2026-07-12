import json
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from fetch_resumes import enrich_with_resumes
from split_candidates import split_and_publish

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

PAGE_URL = "https://democrats.org.il/candidates/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
RAW_HTML_PATH = os.path.join(DATA_DIR, "candidates_page_raw.html")


def download_page(url=PAGE_URL, dest_path=RAW_HTML_PATH):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return len(resp.content)


def classify_social(href):
    host = urlparse(href).netloc.lower()
    if "facebook.com" in host:
        return "facebook"
    if "instagram.com" in host:
        return "instagram"
    if host in ("x.com", "twitter.com") or host.endswith(".x.com"):
        return "twitter"
    if "tiktok.com" in host:
        return "tiktok"
    if "linkedin.com" in host:
        return "linkedin"
    if "whatsapp.com" in host or host == "wa.me":
        return "whatsapp"
    return None


def parse_item(item):
    post_id = item.get("data-post-id")

    text_divs = item.select(".elementor-widget-text-editor")
    # Name is made of one or more short text blocks (title/first/last name);
    # the bio is the first block long enough to clearly not be a name part.
    NAME_LEN_THRESHOLD = 50
    name_parts = []
    bio = ""
    for div in text_divs:
        text = div.get_text("\n", strip=True)
        if not bio and len(text) < NAME_LEN_THRESHOLD:
            name_parts.append(text)
        elif not bio:
            bio = text
            break

    website_url = None
    website_icon = item.select_one('img[src*="website.svg"]')
    if website_icon:
        parent_a = website_icon.find_parent("a")
        if parent_a:
            website_url = parent_a.get("href")

    cv_url = None
    cv_icon = item.select_one('img[src*="CVd2.png"], img[src*="CV"]')
    if cv_icon:
        parent_a = cv_icon.find_parent("a")
        if parent_a and parent_a.get("href", "").lower().endswith(".pdf"):
            cv_url = parent_a.get("href")
    if not cv_url:
        pdf_a = item.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if pdf_a:
            cv_url = pdf_a.get("href")

    social = {}
    for a in item.select("a.elementor-social-icon"):
        href = a.get("href")
        if not href:
            continue
        kind = classify_social(href)
        if kind:
            social[kind] = href

    return {
        "id": post_id,
        "name": " ".join(name_parts).strip(),
        "bio": bio,
        "website_url": website_url,
        "cv_url": cv_url,
        "social": social,
    }


def main():
    size = download_page()
    print(f"Downloaded {PAGE_URL} -> {RAW_HTML_PATH} ({size} bytes)")

    with open(RAW_HTML_PATH, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".jet-listing-grid__item")

    candidates = []
    seen_ids = set()
    for item in items:
        data = parse_item(item)
        if data["id"] in seen_ids:
            continue
        seen_ids.add(data["id"])
        candidates.append(data)

    out_path = os.path.join(DATA_DIR, "candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    missing_bio = [c["id"] for c in candidates if not c["bio"]]
    missing_cv = [c["id"] for c in candidates if not c["cv_url"]]
    print(f"Parsed {len(candidates)} candidates -> {out_path}")
    print(f"Missing bio: {len(missing_bio)} {missing_bio}")
    print(f"Missing cv: {len(missing_cv)} {missing_cv}")

    results = enrich_with_resumes(candidates)
    print(f"Resumes: ok={len(results['ok'])} no_cv={len(results['no_cv'])} "
          f"download_failed={len(results['download_failed'])} "
          f"extract_failed={len(results['extract_failed'])} "
          f"empty_text={len(results['empty_text'])} "
          f"rtl_fixed={len(results['rtl_fixed'])}")

    for i, c in enumerate(candidates, start=1):
        c.pop("cv_url", None)
        candidates[i - 1] = {"index": i, **c}

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "fetch_resumes_report.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    n_parts = split_and_publish(candidates)
    print(f"Split into {n_parts} part file(s); updated AGENTS.md and README.md")


if __name__ == "__main__":
    main()
