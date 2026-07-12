import json
import os
import re
import time

import requests
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
CV_DIR = os.path.join(DATA_DIR, "cvs")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Some PDF generators emit Hebrew (RTL) text to pypdf in mirrored/visual
# order instead of logical reading order (either per-line, or across the
# whole extracted block). Detect this via how often common Hebrew function
# words appear and undo it; text that already reads correctly is untouched.
HEBREW_COMMON_WORDS = frozenset([
    "של", "את", "עם", "הוא", "היא", "אני", "אשר", "כי", "לא", "זה", "גם",
    "על", "אל", "כל", "יש", "היה", "אבל", "או", "כמו", "מה", "אלה", "הם",
    "הן", "בין", "אחד", "שני", "כדי", "לפני", "אחרי", "עד", "רק",
])
_HEBREW_TOKEN_RE = re.compile(r"[א-ת]+")
_LTR_RUN_RE = re.compile(r"[0-9A-Za-z.,()%/-]+")


def download(url, dest_path):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return len(resp.content)


def _hebrew_common_word_ratio(text):
    tokens = _HEBREW_TOKEN_RE.findall(text)
    if not tokens:
        return 0.0, 0
    matches = sum(1 for t in tokens if t in HEBREW_COMMON_WORDS)
    return matches / len(tokens), len(tokens)


def _fix_line_reversal(text):
    def fix_line(line):
        reversed_line = line[::-1]
        return _LTR_RUN_RE.sub(lambda m: m.group(0)[::-1], reversed_line)
    return "\n".join(fix_line(line) for line in text.split("\n"))


def _fix_whole_reversal(text):
    reversed_text = text[::-1]
    return _LTR_RUN_RE.sub(lambda m: m.group(0)[::-1], reversed_text)


def normalize_rtl_text(text):
    if not text:
        return text, False

    orig_ratio, orig_tokens = _hebrew_common_word_ratio(text)
    if orig_tokens < 15 or orig_ratio >= 0.015:
        return text, False

    best_text, best_ratio = text, orig_ratio
    for candidate in (_fix_line_reversal(text), _fix_whole_reversal(text)):
        ratio, _ = _hebrew_common_word_ratio(candidate)
        if ratio > best_ratio:
            best_text, best_ratio = candidate, ratio

    if best_ratio >= 0.03:
        return best_text, True
    return text, False


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def enrich_with_resumes(candidates):
    os.makedirs(CV_DIR, exist_ok=True)

    results = {"ok": [], "no_cv": [], "download_failed": [], "extract_failed": [],
                "empty_text": [], "rtl_fixed": []}

    for c in candidates:
        candidate_id = c["id"]
        cv_url = c.get("cv_url")
        if not cv_url:
            c["resume_text"] = None
            results["no_cv"].append(candidate_id)
            continue

        pdf_path = os.path.join(CV_DIR, f"{candidate_id}.pdf")
        if not os.path.exists(pdf_path):
            try:
                download(cv_url, pdf_path)
                time.sleep(0.5)
            except Exception as e:
                c["resume_text"] = None
                c["resume_error"] = f"download_failed: {e}"
                results["download_failed"].append((candidate_id, str(e)))
                continue

        try:
            text = extract_text(pdf_path)
        except Exception as e:
            c["resume_text"] = None
            c["resume_error"] = f"extract_failed: {e}"
            results["extract_failed"].append((candidate_id, str(e)))
            continue

        if not text:
            c["resume_text"] = None
            c["resume_error"] = "empty_text_probably_scanned_image"
            results["empty_text"].append(candidate_id)
            continue

        text, was_fixed = normalize_rtl_text(text)
        if was_fixed:
            results["rtl_fixed"].append(candidate_id)

        c["resume_text"] = text
        c.pop("resume_error", None)
        results["ok"].append(candidate_id)

    return results


def main():
    candidates_path = os.path.join(DATA_DIR, "candidates.json")
    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)

    results = enrich_with_resumes(candidates)

    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    with open(os.path.join(DATA_DIR, "fetch_resumes_report.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"ok={len(results['ok'])} no_cv={len(results['no_cv'])} "
          f"download_failed={len(results['download_failed'])} "
          f"extract_failed={len(results['extract_failed'])} "
          f"empty_text={len(results['empty_text'])} "
          f"rtl_fixed={len(results['rtl_fixed'])}")


if __name__ == "__main__":
    main()
