import json
import os
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")


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

    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""

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
        "post_id": post_id,
        "name": " ".join(name_parts).strip(),
        "name_parts": name_parts,
        "bio": bio,
        "website_url": website_url,
        "cv_url": cv_url,
        "social": social,
    }


def main():
    with open(os.path.join(DATA_DIR, "candidates_page_raw.html"), encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".jet-listing-grid__item")

    candidates = []
    seen_ids = set()
    for item in items:
        data = parse_item(item)
        if data["post_id"] in seen_ids:
            continue
        seen_ids.add(data["post_id"])
        candidates.append(data)

    out_path = os.path.join(DATA_DIR, "candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    missing_bio = [c["post_id"] for c in candidates if not c["bio"]]
    missing_cv = [c["post_id"] for c in candidates if not c["cv_url"]]
    print(f"Parsed {len(candidates)} candidates -> {out_path}")
    print(f"Missing bio: {len(missing_bio)} {missing_bio}")
    print(f"Missing cv: {len(missing_cv)} {missing_cv}")


if __name__ == "__main__":
    main()
