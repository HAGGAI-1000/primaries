import json
import os
import time

import requests
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
CV_DIR = os.path.join(DATA_DIR, "cvs")

HEADERS = {"User-Agent": "Mozilla/5.0"}


def download(url, dest_path):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return len(resp.content)


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def main():
    os.makedirs(CV_DIR, exist_ok=True)

    candidates_path = os.path.join(DATA_DIR, "candidates.json")
    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)

    results = {"ok": [], "no_cv": [], "download_failed": [], "extract_failed": [], "empty_text": []}

    for c in candidates:
        post_id = c["post_id"]
        cv_url = c.get("cv_url")
        if not cv_url:
            c["resume_text"] = None
            results["no_cv"].append(post_id)
            continue

        pdf_path = os.path.join(CV_DIR, f"{post_id}.pdf")
        if not os.path.exists(pdf_path):
            try:
                download(cv_url, pdf_path)
                time.sleep(0.5)
            except Exception as e:
                c["resume_text"] = None
                c["resume_error"] = f"download_failed: {e}"
                results["download_failed"].append((post_id, str(e)))
                continue

        try:
            text = extract_text(pdf_path)
        except Exception as e:
            c["resume_text"] = None
            c["resume_error"] = f"extract_failed: {e}"
            results["extract_failed"].append((post_id, str(e)))
            continue

        if not text:
            c["resume_text"] = None
            c["resume_error"] = "empty_text_probably_scanned_image"
            results["empty_text"].append(post_id)
            continue

        c["resume_text"] = text
        c.pop("resume_error", None)
        results["ok"].append(post_id)

    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    with open(os.path.join(DATA_DIR, "fetch_resumes_report.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"ok={len(results['ok'])} no_cv={len(results['no_cv'])} "
          f"download_failed={len(results['download_failed'])} "
          f"extract_failed={len(results['extract_failed'])} "
          f"empty_text={len(results['empty_text'])}")


if __name__ == "__main__":
    main()
