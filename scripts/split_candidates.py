import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
REPO_ROOT = os.path.join(HERE, "..")

MAX_BYTES = 100_000
PART_FILENAME_RE = re.compile(r"^candidates(\d+)\.json$")


def _size(chunk):
    return len(json.dumps(chunk, ensure_ascii=False, indent=2).encode("utf-8"))


def chunk_candidates(candidates, max_bytes=MAX_BYTES):
    chunks = []
    current = []
    for c in candidates:
        trial = current + [c]
        if _size(trial) > max_bytes and current:
            chunks.append(current)
            current = [c]
        else:
            current = trial
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks, start=1):
        size = _size(chunk)
        if size > max_bytes:
            print(f"warning: candidates{i}.json is {size} bytes, over the "
                  f"{max_bytes}-byte cap (single candidate too large to split further)")
    return chunks


def write_parts(chunks):
    for name in os.listdir(DATA_DIR):
        if PART_FILENAME_RE.match(name):
            os.remove(os.path.join(DATA_DIR, name))

    for i, chunk in enumerate(chunks, start=1):
        path = os.path.join(DATA_DIR, f"candidates{i}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)

    return len(chunks)


def _parts_shorthand(n):
    return "candidates1.json" if n == 1 else f"candidates1-{n}.json"


def _update_agents_md(n, ranges):
    path = os.path.join(REPO_ROOT, "AGENTS.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()

    shorthand = _parts_shorthand(n)

    text, count1 = re.subn(
        r"\(`ideology\.json`, `[^`]+`\) are there too\.",
        f"(`ideology.json`, `{shorthand}`) are there too.",
        text,
    )
    text, count2 = re.subn(
        r"at stage 3b, \S+ at stage 4\.",
        f"at stage 3b, {shorthand} at stage 4.",
        text,
    )
    if count1 != 1 or count2 != 1:
        raise RuntimeError(
            f"expected 1 occurrence each of the bootstrap shorthand mentions in "
            f"AGENTS.md, found {count1} and {count2}"
        )

    names = ", ".join(f"`candidates{i}.json`" for i in range(1, n + 1))
    urls = "\n".join(
        f"- https://haggai-1000.github.io/primaries/data/candidates{i}.json "
        f"(indices {lo}-{hi})"
        for i, (lo, hi) in enumerate(ranges, start=1)
    )
    if n == 1:
        intro = f"Data: the candidate data — {names} — fetch it NOW:"
    else:
        intro = f"Data: all {n} candidate parts — {names} — fetch them NOW:"

    block_re = re.compile(
        r"Data: (?:ALL \w+ candidate parts|all \d+ candidate parts|the candidate data)"
        r".*?fetch (?:them|it) NOW:\n(?:- https://\S+(?: \(indices \d+-\d+\))?\n?)+",
        re.DOTALL,
    )
    text, count = block_re.subn(f"{intro}\n{urls}\n", text)
    if count != 1:
        raise RuntimeError(
            f"expected to replace exactly 1 Stage 4 data block in AGENTS.md, replaced {count}"
        )

    text = text.replace("all three parts", "all parts")
    if text.count("all parts") != 3:
        raise RuntimeError(
            f"expected 3 occurrences of 'all parts' in AGENTS.md after normalization, "
            f"found {text.count('all parts')}"
        )

    completeness_re = re.compile(
        r"(?<=blob pages as fallback, as in bootstrap\)\. )Completeness check:"
        r".*?(?=Match over all candidates in all parts\.)",
        re.DOTALL,
    )
    new_completeness = (
        "Completeness check: each part must parse as valid JSON and contain "
        "exactly the index range shown next to it above (its first record's "
        "`index` equals the range's start, its last record's `index` equals "
        "the range's end, with no gaps or duplicates). If any part fails "
        "this check, tell the user honestly that the candidate data could "
        "not be fully retrieved on this platform and suggest trying a "
        "different chat platform or a coding agent — never rank based on a "
        "partial candidate list. "
    )
    text, count = completeness_re.subn(new_completeness, text)
    if count != 1:
        raise RuntimeError(
            f"expected to replace exactly 1 completeness-check block in AGENTS.md, "
            f"replaced {count}"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _update_readme(n):
    path = os.path.join(REPO_ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()

    names = ", ".join(f"`data/candidates{i}.json`" for i in range(1, n + 1))
    replacement = (
        f"- {names} — candidate bios, resumes, and links, split\n"
        f"  into {n} part{'s' if n != 1 else ''} so each can be fetched whole by chat assistants"
    )

    block_re = re.compile(
        r"- `data/candidates1\.json`.*?split\n  into \S+ parts? so each can be fetched whole by chat assistants",
        re.DOTALL,
    )
    text, count = block_re.subn(replacement, text)
    if count != 1:
        raise RuntimeError(
            f"expected to replace exactly 1 candidate-parts bullet in README.md, replaced {count}"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def update_docs(n_parts, ranges):
    _update_agents_md(n_parts, ranges)
    _update_readme(n_parts)


def split_and_publish(candidates, max_bytes=MAX_BYTES):
    chunks = chunk_candidates(candidates, max_bytes)
    n = write_parts(chunks)
    ranges = [(chunk[0]["index"], chunk[-1]["index"]) for chunk in chunks]
    update_docs(n, ranges)
    return n


def main():
    candidates_path = os.path.join(DATA_DIR, "candidates.json")
    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)

    n = split_and_publish(candidates)
    print(f"Split {len(candidates)} candidates into {n} part file(s); "
          f"updated AGENTS.md and README.md")


if __name__ == "__main__":
    main()
