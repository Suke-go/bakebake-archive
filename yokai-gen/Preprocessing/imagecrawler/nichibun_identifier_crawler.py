#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nichibun YoukaiGazou identifier crawler (brute force)
----------------------------------------------------
- Generates candidate identifiers like U{AAA}_nichibunken_{BBBB}_{CCCC}_{DDDD}
- Fetches the corresponding card.cgi page to confirm existence
- Writes metadata for the hits (title, author, etc.) and optionally downloads images
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

import requests
from bs4 import BeautifulSoup

from nichibun_theme_crawler import download_images as download_images_helper

CARD_URL = "https://www.nichibun.ac.jp/cgi-bin/YoukaiGazou/card.cgi"
IMAGE_BASE = "https://www.nichibun.ac.jp/YoukaiGazou/image/"

DATA_DIR = Path("data")
CONFIG_DIR = DATA_DIR / "config"
DERIVED_DIR = DATA_DIR / "derived"
OUTPUT_DIR = DATA_DIR / "outputs"

LABEL_MAP = {
    "タイトル": "title",
    "著作者": "creator",
    "主題": "subjects",
    "内容記述": "description",
    "公開者": "publisher",
    "寄与者": "contributor",
    "日付": "date",
    "資源タイプ": "resource_type",
    "フォーマット": "format",
    "資源識別子": "identifier_text",
    "情報源": "source",
    "言語": "language",
    "関係": "relation",
    "時間的・空間的範囲": "coverage",
    "権利関係": "rights",
}


@dataclass(frozen=True)
class IdentifierParts:
    aaa: int
    bbbb: int
    cccc: int
    dddd: int

    @property
    def id_str(self) -> str:
        return f"U{self.aaa:03d}_nichibunken_{self.bbbb:04d}_{self.cccc:04d}_{self.dddd:04d}"


def inclusive_range(bound: Sequence[int]) -> range:
    start, end = bound
    step = 1 if end >= start else -1
    return range(start, end + step, step)


def load_ints_from_file(path: Optional[str]) -> List[int]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"--bbbb-file does not exist: {path}")
    vals: List[int] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals.extend(int(part) for part in line.split())
    return vals


def build_bbbb_values(
    values: Optional[Sequence[int]],
    file_values: Optional[Sequence[int]],
    bounds: Optional[Sequence[int]],
) -> List[int]:
    pool: Set[int] = set()
    if values:
        pool.update(int(v) for v in values)
    if file_values:
        pool.update(int(v) for v in file_values)
    if pool:
        return sorted(pool)
    if bounds:
        rng = inclusive_range(bounds)
        return list(rng)
    raise SystemExit("Provide either --bbbb or --bbbb-range to limit search space.")


def load_skip_identifiers(paths: Sequence[str]) -> Set[str]:
    skip: Set[str] = set()
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if "identifier" not in (reader.fieldnames or []):
                    continue
                for row in reader:
                    ident = (row.get("identifier") or "").strip()
                    if ident:
                        skip.add(ident)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[warn] failed to read {path}: {exc}", file=sys.stderr)
    return skip


def load_range_log(path: Path) -> Dict[str, Dict[str, int]]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_range_log(path: Path, data: Dict[str, Dict[str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_range_log(entry: Dict[str, Dict[str, int]], parts: IdentifierParts) -> None:
    key = f"{parts.bbbb:04d}"
    info = entry.setdefault(
        key,
        {"c_min": parts.cccc, "c_max": parts.cccc, "d_min": parts.dddd, "d_max": parts.dddd, "hits": 0},
    )
    info["c_min"] = min(info["c_min"], parts.cccc)
    info["c_max"] = max(info["c_max"], parts.cccc)
    info["d_min"] = min(info["d_min"], parts.dddd)
    info["d_max"] = max(info["d_max"], parts.dddd)
    info["hits"] = info.get("hits", 0) + 1


def generate_identifiers(
    aaa_values: Sequence[int],
    tasks: Sequence[Tuple[int, int, int, int, int]],
) -> Iterator[IdentifierParts]:
    for aaa in aaa_values:
        for bbbb, c_start, c_end, d_start, d_end in tasks:
            for cccc in inclusive_range((c_start, c_end)):
                for dddd in inclusive_range((d_start, d_end)):
                    yield IdentifierParts(aaa=aaa, bbbb=bbbb, cccc=cccc, dddd=dddd)


def fetch_card(identifier: str, session: requests.Session, timeout: float) -> Tuple[bool, str]:
    resp = session.get(CARD_URL, params={"identifier": identifier}, timeout=timeout)
    resp.raise_for_status()
    html = resp.text
    exists = identifier in html
    return exists, html


def parse_card_metadata(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.dataTable")
    data: Dict[str, str] = {}
    if not table:
        return data
    for tr in table.find_all("tr"):
        label_node = tr.find("th")
        value_node = tr.find("td")
        if not label_node or not value_node:
            continue
        label = label_node.get_text(strip=True)
        value = value_node.get_text(" ", strip=True)
        key = LABEL_MAP.get(label)
        if key:
            data[key] = value
    return data


def write_csv(rows: Sequence[Dict[str, str]], out_path: Path) -> None:
    if not rows:
        print("[warn] No identifiers discovered; CSV not written.")
        return
    fieldnames = [
        "identifier",
        "aaa",
        "bbbb",
        "cccc",
        "dddd",
        "title",
        "creator",
        "subjects",
        "description",
        "publisher",
        "contributor",
        "date",
        "resource_type",
        "format",
        "language",
        "source",
        "relation",
        "coverage",
        "rights",
        "card_url",
        "image_url",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ok] Wrote {len(rows)} identifiers to {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Brute-force Nichibun identifiers and fetch card metadata.")
    ap.add_argument("--aaa", nargs="+", type=int, default=[426], help="AAA collection numbers (default: 426)")
    ap.add_argument("--bbbb", nargs="*", type=int, help="Specific BBBB values to include (4-digit numbers)")
    ap.add_argument("--bbbb-file", default=None, help="Path to text file with BBBB integers (whitespace/newline separated)")
    ap.add_argument("--bbbb-range", nargs=2, type=int, metavar=("MIN", "MAX"), help="Inclusive BBBB range")
    ap.add_argument("--bbbb-priority-file", default=None, help="Text file listing BBBB values to prioritize")
    ap.add_argument("--cccc-range", nargs=2, type=int, default=[1, 40], metavar=("MIN", "MAX"), help="Inclusive CCCC range (default: 1 40)")
    ap.add_argument("--dddd-range", nargs=2, type=int, default=[0, 20], metavar=("MIN", "MAX"), help="Inclusive DDDD range (default: 0 20)")
    ap.add_argument("--ranges-json", default=None, help="JSON mapping BBBB -> {c_min,c_max,d_min,d_max}")
    ap.add_argument("--cccc-margin", type=int, default=2, help="Margin applied to JSON CCCC ranges (default: 2)")
    ap.add_argument("--dddd-margin", type=int, default=1, help="Margin applied to JSON DDDD ranges (default: 1)")
    ap.add_argument("--skip-csv", nargs="*", default=[], help="CSV file(s) with an identifier column to skip (e.g., existing datasets)")
    ap.add_argument("--out", default=str(OUTPUT_DIR / "nichibun_cards.csv"), help="Output CSV path for discovered identifiers")
    ap.add_argument("--range-log", default=str(DERIVED_DIR / "discovered_ranges.json"), help="Path to append discovered (BBBB, ranges)")
    ap.add_argument("--max-found", type=int, default=None, help="Stop after discovering this many identifiers")
    ap.add_argument("--max-candidates", type=int, default=None, help="Hard cap on total candidates processed")
    ap.add_argument("--sleep", type=float, default=0.3, help="Delay between requests (seconds)")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--user-agent", default="Mozilla/5.0 (compatible; NichibunIdentifierCrawler/1.0)", help="Custom User-Agent header")
    ap.add_argument("--download-images", default=None, help="Directory to download discovered images (optional)")
    ap.add_argument("--overwrite-images", action="store_true", help="Overwrite existing images when downloading")
    ap.add_argument("--max-miss-per-cccc", type=int, default=1, help="Max consecutive misses per (BBBB, CCCC) before skipping remaining DDDD (default: 1)")
    args = ap.parse_args()

    file_bbbb = load_ints_from_file(args.bbbb_file)
    priority_bbbb = load_ints_from_file(args.bbbb_priority_file)

    tasks: List[Tuple[int, int, int, int, int]] = []
    if args.ranges_json:
        ranges_data = json.loads(Path(args.ranges_json).read_text(encoding="utf-8"))
        available_b = sorted(int(k) for k in ranges_data.keys())
        if args.bbbb or file_bbbb:
            target_b = build_bbbb_values(args.bbbb, file_bbbb, None)
        else:
            target_b = available_b

        seen: Set[int] = set()

        def add_task(b: int) -> None:
            if b in seen:
                return
            info = ranges_data.get(str(b)) or ranges_data.get(b)
            if not info:
                return
            c_min_raw = int(info["c_min"])
            c_max_raw = int(info["c_max"])
            d_min_raw = int(info["d_min"])
            d_max_raw = int(info["d_max"])
            if c_min_raw == c_max_raw:
                c_min = c_max = c_min_raw
            else:
                c_min = max(0, c_min_raw - args.cccc_margin)
                c_max = c_max_raw + args.cccc_margin
            if d_min_raw == d_max_raw:
                d_min = d_max = d_min_raw
            else:
                d_min = max(0, d_min_raw - args.dddd_margin)
                d_max = d_max_raw + args.dddd_margin
            tasks.append((b, c_min, c_max, d_min, d_max))
            seen.add(b)

        for b in priority_bbbb:
            add_task(b)
        for b in target_b:
            add_task(b)
    else:
        bbbb_values = build_bbbb_values(args.bbbb, file_bbbb, args.bbbb_range)
        seen: Set[int] = set()

        def add_simple_task(b: int) -> None:
            if b in seen:
                return
            tasks.append((b, args.cccc_range[0], args.cccc_range[1], args.dddd_range[0], args.dddd_range[1]))
            seen.add(b)

        for b in priority_bbbb:
            add_simple_task(b)
        for b in bbbb_values:
            add_simple_task(b)

    if not tasks:
        raise SystemExit("No BBBB values specified. Provide --bbbb/--bbbb-file/--bbbb-range or --ranges-json.")

    identifier_iter = generate_identifiers(args.aaa, tasks)
    skip = load_skip_identifiers(args.skip_csv + [args.out])
    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    discovered: List[Dict[str, str]] = []
    attempts = 0
    found = 0

    last_key = None
    miss_streak = 0
    skip_cccc: Set[Tuple[int, int]] = set()

    range_log_path = Path(args.range_log)
    range_log = load_range_log(range_log_path)

    for parts in identifier_iter:
        identifier = parts.id_str
        if args.max_candidates is not None and attempts >= args.max_candidates:
            break
        attempts += 1
        key = (parts.bbbb, parts.cccc)
        if key in skip_cccc:
            continue
        if identifier in skip:
            continue
        try:
            exists, html = fetch_card(identifier, session, args.timeout)
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"[error] {identifier}: {exc}", file=sys.stderr)
            time.sleep(args.sleep)
            continue
        if key != last_key:
            miss_streak = 0
            last_key = key
        if not exists:
            miss_streak += 1
            print(f"[miss] {identifier} (miss streak: {miss_streak})")
            if miss_streak >= args.max_miss_per_cccc:
                print(f"[skip] stopping DDDD search at BBBB={parts.bbbb:04d} CCCC={parts.cccc:04d} after {miss_streak} misses")
                skip_cccc.add(key)
            time.sleep(args.sleep)
            continue
        miss_streak = 0

        meta = parse_card_metadata(html)
        row = {
            "identifier": identifier,
            "aaa": str(parts.aaa),
            "bbbb": f"{parts.bbbb:04d}",
            "cccc": f"{parts.cccc:04d}",
            "dddd": f"{parts.dddd:04d}",
            "title": meta.get("title", ""),
            "creator": meta.get("creator", ""),
            "subjects": meta.get("subjects", ""),
            "description": meta.get("description", ""),
            "publisher": meta.get("publisher", ""),
            "contributor": meta.get("contributor", ""),
            "date": meta.get("date", ""),
            "resource_type": meta.get("resource_type", ""),
            "format": meta.get("format", ""),
            "language": meta.get("language", ""),
            "source": meta.get("source", ""),
            "relation": meta.get("relation", ""),
            "coverage": meta.get("coverage", ""),
            "rights": meta.get("rights", ""),
            "card_url": f"{CARD_URL}?identifier={identifier}",
            "image_url": IMAGE_BASE + f"{identifier}.jpg",
        }
        discovered.append(row)
        skip.add(identifier)
        found += 1
        update_range_log(range_log, parts)
        print(f"[ok] {identifier} (total found: {found})")
        time.sleep(args.sleep)

        if args.max_found is not None and found >= args.max_found:
            break

    out_path = Path(args.out)
    write_csv(discovered, out_path)
    save_range_log(range_log_path, range_log)

    if args.download_images and discovered:
        from pathlib import Path as _Path

        download_images_helper(
            discovered,
            _Path(args.download_images),
            sleep=args.sleep,
            overwrite=args.overwrite_images,
        )


if __name__ == "__main__":
    main()

