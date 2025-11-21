#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nichibun YoukaiGazou keyword scraper
-----------------------------------
- Fetches search results for one or more keywords using the `query` parameter.
- Reuses the BeautifulSoup-based parser from `nichibun_theme_crawler`.
- Outputs CSV rows with: keyword, identifier, title, card_url, image_url.
"""
import argparse
import csv
import time
from pathlib import Path
from typing import List, Dict

import requests

from nichibun_theme_crawler import BASE, parse_entries

SEARCH_URL = "https://www.nichibun.ac.jp/cgi-bin/YoukaiGazou/search.cgi"


def fetch_keyword(keyword: str, session: requests.Session, timeout: float = 15.0) -> List[Dict[str, str]]:
    params = {
        "query": keyword,
        "whence2": 0,
        "lang2": "ja",
    }
    resp = session.get(SEARCH_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    if resp.encoding == "ISO-8859-1":
        resp.encoding = resp.apparent_encoding or "cp932"
    html_text = resp.text
    rows = parse_entries(html_text, BASE)
    for r in rows:
        r["keyword"] = keyword
    return rows


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["keyword", "identifier", "title", "card_url", "image_url"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({fn: r.get(fn, "") for fn in fieldnames})


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Nichibun YoukaiGazou entries by keyword search (query parameter).")
    ap.add_argument("keywords", nargs="*", help="Zero or more keywords (Japanese text is OK).")
    ap.add_argument("--keyword-file", default=None, help="Optional UTF-8 text file with one keyword per line.")
    ap.add_argument("-o", "--out", default="data/nichibun_keywords.csv", help="Output CSV path")
    ap.add_argument("--sleep", type=float, default=0.3, help="Delay between keyword requests (seconds)")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--user-agent", default="Mozilla/5.0 (compatible; NichibunKeywordBot/1.0)", help="Custom User-Agent string")
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    kw_list: List[str] = list(args.keywords)
    if args.keyword_file:
        file_path = Path(args.keyword_file)
        file_kw = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        kw_list.extend(file_kw)

    if not kw_list:
        ap.error("Provide at least one keyword via arguments or --keyword-file.")

    all_rows: List[Dict[str, str]] = []
    for kw in kw_list:
        try:
            rows = fetch_keyword(kw, session=session, timeout=args.timeout)
            print(f"[ok] {kw}: fetched {len(rows)} rows")
            all_rows.extend(rows)
        except Exception as exc:
            print(f"[warn] {kw}: {exc}")
        time.sleep(args.sleep)

    if not all_rows:
        print("[warn] No rows collected.")

    out_path = Path(args.out)
    write_csv(all_rows, out_path)
    print(f"[ok] Wrote {len(all_rows)} total rows to {out_path}")


if __name__ == "__main__":
    main()

