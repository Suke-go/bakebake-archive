#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nichibun YoukaiGazou list extractor
-----------------------------------
- Input: 1+ saved HTML files from the Nichibun "怪異・妖怪画像データベース" search results.
- Output: CSV with columns: identifier, title, card_url, image_url
- Optional: filter by keyword and (opt-in) download images.

Usage examples:
  python nichibun_scrape_titles.py "怪異・妖怪画像データベース.htm" -o nichibun_list_with_titles.csv
  python nichibun_scrape_titles.py page1.htm page2.htm --grep "麻疹|疫神"
  python nichibun_scrape_titles.py results.htm --write-urls urls.txt
  python nichibun_scrape_titles.py results.htm --download-images images/ --sleep 0.5

Notes:
- Title is captured as the text inside the <a ...> up to the first <br> tag.
- Directory listing of /YoukaiGazou/image is forbidden (403), but individual
  image URLs are constructed as https://www.nichibun.ac.jp/YoukaiGazou/image/{identifier}.jpg
"""
import re, csv, html, time, argparse, sys
from pathlib import Path
from typing import List, Dict, Iterable
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup, NavigableString, Tag

BASE = "https://www.nichibun.ac.jp/"


def smart_decode(path: Path) -> str:
    """Robustly decode an HTML file (utf-8, cp932, etc.)."""
    data = path.read_bytes()
    for enc in ("utf-8", "cp932", "shift_jis", "euc-jp"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize_spaces(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return html.unescape(text.strip())


def candidate_texts(a_tag: Tag) -> Iterable[str]:
    # direct text
    yield a_tag.get_text(" ", strip=True)

    # look ahead among siblings until <br> or block end
    for sib in a_tag.next_siblings:
        if isinstance(sib, NavigableString):
            yield str(sib)
        elif isinstance(sib, Tag):
            if sib.name and sib.name.lower() == "br":
                break
            yield sib.get_text(" ", strip=True)
        if isinstance(sib, Tag) and sib.name and sib.name.lower() == "br":
            break

    # parent text
    parent = a_tag.parent
    if isinstance(parent, Tag):
        yield parent.get_text(" ", strip=True)

    # alt text on any nested img
    img = a_tag.find("img")
    if img and img.get("alt"):
        yield img["alt"]


def extract_title(a_tag: Tag) -> str:
    for raw in candidate_texts(a_tag):
        cleaned = normalize_spaces(raw)
        if cleaned:
            return cleaned.split(" ", 1)[0] if "<br" in raw.lower() else cleaned
    return ""


def extract_entries_from_text(text: str) -> List[Dict[str, str]]:
    rows = []
    soup = BeautifulSoup(text, "html.parser")

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "card.cgi" not in href or "identifier=" not in href:
            continue

        ident = parse_qs(urlparse(href).query).get("identifier", [None])[0]
        if not ident:
            mm = re.search(r'identifier=([^&"#]+)', href)
            ident = mm.group(1) if mm else None
        if not ident:
            continue

        title = extract_title(a_tag)
        card_url = urljoin(BASE, href.lstrip("./"))
        image_url = urljoin(BASE, f"YoukaiGazou/image/{ident}.jpg")
        rows.append({"identifier": ident, "title": title, "card_url": card_url, "image_url": image_url})

    # Merge duplicates prioritizing non-empty titles
    merged: Dict[str, Dict[str, str]] = {}
    for r in rows:
        ident = r["identifier"]
        if ident not in merged or (not merged[ident]["title"] and r["title"]):
            merged[ident] = r
    return list(merged.values())

def parse_files(paths: List[Path]) -> List[Dict[str, str]]:
    all_rows: List[Dict[str, str]] = []
    for p in paths:
        txt = smart_decode(p)
        all_rows.extend(extract_entries_from_text(txt))

    # De-duplicate by identifier (keep first occurrence)
    seen = set()
    uniq = []
    for r in all_rows:
        if r["identifier"] in seen:
            continue
        seen.add(r["identifier"])
        uniq.append(r)
    return uniq

def write_csv(rows: List[Dict[str, str]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["identifier", "title", "card_url", "image_url"])
        w.writeheader()
        w.writerows(rows)

def filter_rows(rows: List[Dict[str, str]], pattern: str) -> List[Dict[str, str]]:
    rx = re.compile(pattern)
    return [r for r in rows if rx.search(r.get("title", "")) or rx.search(r.get("identifier", ""))]

def write_urls(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(r["image_url"] + "\n")

def download_images(rows: List[Dict[str, str]], outdir: Path, sleep: float = 0.3, overwrite: bool = False, timeout: float = 15.0, user_agent: str = None) -> None:
    try:
        import requests
    except ImportError:
        print("requests is required for downloading images. Install with: pip install requests", file=sys.stderr)
        sys.exit(1)

    outdir.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent or "Mozilla/5.0 (compatible; NichibunCollector/1.0)"})

    for r in rows:
        ident = r["identifier"]
        url = r["image_url"]
        dest = outdir / f"{ident}.jpg"
        if dest.exists() and not overwrite:
            continue
        try:
            resp = s.get(url, timeout=timeout)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                dest.write_bytes(resp.content)
            else:
                print(f"[warn] {ident}: HTTP {resp.status_code} (content-type={resp.headers.get('content-type')})", file=sys.stderr)
        except Exception as ex:
            print(f"[error] {ident}: {ex}", file=sys.stderr)
        time.sleep(sleep)

def main():
    ap = argparse.ArgumentParser(description="Extract (identifier, title, card_url, image_url) from Nichibun YoukaiGazou HTML.")
    ap.add_argument("html", nargs="+", help="Path(s) to saved Nichibun HTML files")
    ap.add_argument("-o", "--out-csv", default="nichibun_list_with_titles.csv", help="Output CSV path (default: %(default)s)")
    ap.add_argument("--grep", default=None, help="Regex filter applied to title or identifier (optional)")
    ap.add_argument("--write-urls", default=None, help="Optional: write a newline-separated images URL list to this path")
    ap.add_argument("--download-images", default=None, help="Optional: directory to save images (off by default)")
    ap.add_argument("--sleep", type=float, default=0.3, help="Delay between downloads in seconds (default: 0.3)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing images when downloading")
    ap.add_argument("--user-agent", default=None, help="Custom User-Agent header for downloads")
    args = ap.parse_args()

    paths = [Path(p) for p in args.html]
    rows = parse_files(paths)

    if args.grep:
        rows = filter_rows(rows, args.grep)

    out_csv = Path(args.out_csv)
    write_csv(rows, out_csv)
    print(f"[ok] Wrote {len(rows)} rows to {out_csv}")

    if args.write_urls:
        url_path = Path(args.write_urls)
        write_urls(rows, url_path)
        print(f"[ok] Wrote {len(rows)} image URLs to {url_path}")

    if args.download_images:
        img_dir = Path(args.download_images)
        print(f"[info] Downloading {len(rows)} images to {img_dir} ...")
        download_images(rows, img_dir, sleep=args.sleep, overwrite=args.overwrite, user_agent=args.user_agent)
        print(f"[ok] Done.")

if __name__ == "__main__":
    main()
