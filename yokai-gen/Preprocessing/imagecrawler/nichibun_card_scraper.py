#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nichibun card scraper
---------------------
Given a list of card identifiers (e.g., U426_nichibunken_0051_0032_0000),
fetch the Nichibun YoukaiGazou detail page to extract:
  - subjects (主題)
  - description (内容記述)
  - IIIF manifest / viewer links
  - Best-effort image URL

Optionally download the referenced JPEGs while throttling requests so the
remote server is not overloaded. Supports limited concurrency and caption
generation so images can be passed directly into the LoRA dataset prep pipeline.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Sequence, Set
import threading
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from nichibun_identifier_crawler import CARD_URL, IMAGE_BASE, parse_card_metadata


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Fetch subjects, descriptions, and image/IIIF links for Nichibun "
            "card identifiers."
        )
    )
    ap.add_argument(
        "--identifiers",
        nargs="*",
        default=None,
        help="Identifiers to scrape (e.g., U426_nichibunken_0051_0032_0000).",
    )
    ap.add_argument(
        "--identifiers-file",
        default=None,
        help="Plain-text file with one identifier per line.",
    )
    ap.add_argument(
        "--input-csv",
        default=None,
        help="CSV file that contains an 'identifier' column.",
    )
    ap.add_argument(
        "--out",
        default="data/nichibun_card_details.csv",
        help="Output CSV path (default: data/nichibun_card_details.csv).",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Skip identifiers that already exist in the output CSV (if present).",
    )
    ap.add_argument(
        "--download-dir",
        default=None,
        help="Directory to download JPEG images (optional).",
    )
    ap.add_argument(
        "--overwrite-images",
        action="store_true",
        help="Overwrite images if they already exist locally.",
    )
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="Delay between HTTP requests in seconds (default: 0.3).",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP request timeout in seconds (default: 15).",
    )
    ap.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (compatible; NichibunCardScraper/1.0)",
        help="Custom User-Agent header.",
    )
    ap.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Maximum concurrent requests (keep small to avoid stressing the server).",
    )
    ap.add_argument(
        "--captions-dir",
        default=None,
        help="Directory to write caption .txt files (defaults to --download-dir).",
    )
    ap.add_argument(
        "--caption-trigger",
        default="yokai style",
        help="Prefix tag inserted when auto-generating captions (for LoRA training).",
    )
    return ap.parse_args()


def load_identifiers_from_file(path: Path) -> List[str]:
    identifiers: List[str] = []
    if not path.exists():
        raise SystemExit(f"[error] identifiers file not found: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        ident = raw.strip()
        if ident:
            identifiers.append(ident)
    return identifiers


def load_identifiers_from_csv(path: Path) -> List[str]:
    if not path.exists():
        raise SystemExit(f"[error] CSV not found: {path}")
    identifiers: List[str] = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "identifier" not in reader.fieldnames:
            raise SystemExit(f"[error] CSV missing 'identifier' column: {path}")
        for row in reader:
            ident = (row.get("identifier") or "").strip()
            if ident:
                identifiers.append(ident)
    return identifiers


def gather_identifiers(args: argparse.Namespace) -> List[str]:
    pool: List[str] = []
    if args.identifiers:
        pool.extend(args.identifiers)
    if args.identifiers_file:
        pool.extend(load_identifiers_from_file(Path(args.identifiers_file)))
    if args.input_csv:
        pool.extend(load_identifiers_from_csv(Path(args.input_csv)))
    uniq = []
    seen: Set[str] = set()
    for ident in pool:
        if ident not in seen:
            seen.add(ident)
            uniq.append(ident)
    if not uniq:
        raise SystemExit(
            "Provide at least one identifier via --identifiers/--identifiers-file/--input-csv."
        )
    return uniq


def load_existing_rows(out_path: Path) -> List[Dict[str, str]]:
    if not out_path.exists():
        return []
    rows: List[Dict[str, str]] = []
    with out_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row.setdefault("image_path", row.get("image_path", ""))
            rows.append(row)
    return rows


thread_local = threading.local()


def get_thread_session(user_agent: str) -> requests.Session:
    session = getattr(thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": user_agent})
        thread_local.session = session
    return session


def extract_media_links(html: str, base_url: str) -> Dict[str, str]:
    """Locate the main JPEG, IIIF manifest, and viewer links from the card page."""
    soup = BeautifulSoup(html, "html.parser")
    media: Dict[str, str] = {}

    img_tag = soup.select_one('td img[src*="YoukaiGazou/image/"]')
    if img_tag:
        src = img_tag.get("src")
        if src:
            media["image_url_html"] = urljoin(base_url, src)

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        abs_href = urljoin(base_url, href)
        if "IIIF/manifest" in href and "manifest_url" not in media:
            media["manifest_url"] = abs_href
        if "iiif-viewer" in href and "viewer_url" not in media:
            media["viewer_url"] = abs_href

    return media


def scrape_card(
    identifier: str,
    session: requests.Session,
    timeout: float,
) -> Dict[str, str]:
    params = {"identifier": identifier}
    resp = session.get(CARD_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    html = resp.text
    final_url = resp.url

    metadata = parse_card_metadata(html)
    media_links = extract_media_links(html, final_url)

    subjects = metadata.get("subjects", "")
    description = metadata.get("description", "")

    fallback_image_url = IMAGE_BASE + f"{identifier}.jpg"
    image_url = media_links.get("image_url_html", fallback_image_url)

    manifest_url = media_links.get("manifest_url", "")
    viewer_url = media_links.get("viewer_url", "")

    row = {
        "identifier": identifier,
        "subjects": subjects,
        "description": description,
        "card_url": f"{CARD_URL}?identifier={identifier}",
        "image_url": image_url,
        "manifest_url": manifest_url,
        "viewer_url": viewer_url,
    }
    return row


def download_image(
    identifier: str,
    image_url: str,
    out_dir: Path,
    session: requests.Session,
    timeout: float,
    overwrite: bool = False,
) -> Optional[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{identifier}.jpg"
    if dest.exists() and not overwrite:
        return dest
    resp = session.get(image_url, timeout=timeout)
    resp.raise_for_status()
    if not resp.headers.get("content-type", "").startswith("image"):
        print(
            f"[warn] {identifier}: unexpected content-type {resp.headers.get('content-type')}",
            file=sys.stderr,
        )
        return None
    dest.write_bytes(resp.content)
    return dest


def write_rows(rows: Sequence[Dict[str, str]], out_path: Path) -> None:
    fieldnames = [
        "identifier",
        "subjects",
        "description",
        "card_url",
        "image_url",
        "manifest_url",
        "viewer_url",
        "image_path",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_caption_text(subjects: str, description: str, trigger: str, identifier: str) -> str:
    trigger = trigger.strip()
    parts: List[str] = []
    if trigger:
        parts.append(trigger)
    if subjects:
        parts.append(subjects)
    caption = "、".join(parts).strip("、 ")
    if description:
        caption = f"{caption}。 {description}" if caption else description
    if not caption:
        caption = identifier
    return caption


def write_caption(identifier: str, caption_dir: Path, text: str) -> Path:
    caption_dir.mkdir(parents=True, exist_ok=True)
    caption_path = caption_dir / f"{identifier}.txt"
    caption_path.write_text(text + "\n", encoding="utf-8")
    return caption_path


def process_identifier(
    identifier: str,
    args: argparse.Namespace,
    image_dir: Optional[Path],
    captions_dir: Optional[Path],
) -> Dict[str, str]:
    session = get_thread_session(args.user_agent)
    row = scrape_card(identifier, session, args.timeout)

    image_path_str = ""
    if image_dir:
        saved = download_image(
            identifier,
            row["image_url"],
            image_dir,
            session,
            args.timeout,
            overwrite=args.overwrite_images,
        )
        if saved:
            image_path_str = str(saved)

    if captions_dir:
        caption_text = build_caption_text(
            row.get("subjects", ""),
            row.get("description", ""),
            args.caption_trigger,
            identifier,
        )
        write_caption(identifier, captions_dir, caption_text)

    row["image_path"] = image_path_str
    time.sleep(args.sleep)
    return row


def main() -> None:
    args = parse_args()
    identifiers = gather_identifiers(args)

    out_path = Path(args.out)
    processed_rows: List[Dict[str, str]] = []

    if args.resume and out_path.exists():
        processed_rows = load_existing_rows(out_path)
        seen = {row["identifier"] for row in processed_rows}
    else:
        seen = set()

    image_dir = Path(args.download_dir) if args.download_dir else None
    captions_dir = Path(args.captions_dir) if args.captions_dir else image_dir

    pending = [identifier for identifier in identifiers if identifier not in seen]
    total = len(pending)

    if total == 0:
        print("[info] No new identifiers to scrape.")
        write_rows(processed_rows, out_path)
        return

    max_workers = max(1, args.max_workers)
    print(f"[info] Processing {total} identifiers with up to {max_workers} workers ...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(process_identifier, identifier, args, image_dir, captions_dir): identifier
            for identifier in pending
        }

        completed = 0
        for future in as_completed(future_map):
            identifier = future_map[future]
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001
                print(f"[error] {identifier}: {exc}", file=sys.stderr)
                continue
            processed_rows.append(row)
            seen.add(identifier)
            completed += 1
            print(f"[ok] {identifier} ({completed}/{total}) subjects='{row['subjects']}'")

    if not processed_rows:
        print("[warn] No rows scraped.")
        return
    write_rows(processed_rows, out_path)
    print(f"[ok] wrote {len(processed_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

