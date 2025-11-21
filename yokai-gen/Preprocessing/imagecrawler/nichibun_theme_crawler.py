#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nichibun YoukaiGazou "theme" crawler
------------------------------------
- Starts from https://www.nichibun.ac.jp/YoukaiGazou/
- Parses <dd><a href="../../cgi-bin/YoukaiGazou/search.cgi?query=NILL&ychar=...">鬼</a></dd> style topic links
- Visits each topic's search results, follows pagination (heuristic), and extracts:
    identifier, title (anchor text up to <br>), card_url, image_url, topic_label, topic_href
- Outputs a CSV. Optional: write URL lists and/or download images.

Usage examples:
  # Crawl ALL topics from the index page, write CSV only
  python nichibun_theme_crawler.py --out nichibun_topics.csv

  # Crawl only specific topics by label text (exact match)
  python nichibun_theme_crawler.py --topics 鬼 疫神 --out nichibun_oni_ekijin.csv

  # Crawl by ychar codes directly (URL-decoded input also OK)
  python nichibun_theme_crawler.py --ychar %E9%AC%BC %E7%96%AB%E7%A5%9E --out nichibun.csv

  # Write a flat list of image URLs (for aria2c/wget, etc.)
  python nichibun_theme_crawler.py --out nichibun.csv --write-urls urls.txt

  # (Optional) Download images (be polite and throttle with --sleep)
  python nichibun_theme_crawler.py --download-images images/ --sleep 0.5
"""
import re, csv, html, time, argparse, sys, urllib.parse
from pathlib import Path
from typing import List, Dict, Tuple, Set
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup

BASE = "https://www.nichibun.ac.jp/"
INDEX_URL = "https://www.nichibun.ac.jp/YoukaiGazou/"
SEARCH_PATH = "/cgi-bin/YoukaiGazou/search.cgi"

def fetch(url: str, session=None, timeout: float = 15.0, user_agent: str = None) -> str:
    try:
        import requests
    except ImportError:
        print("requests is required. Install with: pip install requests", file=sys.stderr)
        sys.exit(1)
    s = session or requests.Session()
    if user_agent:
        s.headers.update({"User-Agent": user_agent})
    else:
        s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; NichibunCrawler/1.0)"})
    r = s.get(url, timeout=timeout)
    r.raise_for_status()
    # Handle encoding: use apparent_encoding if headers are misleading, or fallback to utf-8/cp932
    if r.encoding == 'ISO-8859-1':
        r.encoding = r.apparent_encoding
    
    return r.text

# --- Parsers ---

def parse_topics(index_html: str, base_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(index_html, "html.parser")
    topics = []
    # Structure: <div id="youkai-feature"> <dl> <dt>...</dt> <dd><a href="...">Label</a></dd> ...
    # Broadly search for 'dd > a' that links to search.cgi
    for a_tag in soup.select("dd a"):
        href = a_tag.get("href")
        if not href or "search.cgi" not in href:
            continue
        
        label = a_tag.get_text(strip=True)
        abs_href = urljoin(base_url, href)
        
        # Keep only those with ychar parameter
        parsed = urlparse(abs_href)
        qs = parse_qs(parsed.query)
        if "ychar" in qs:
            topics.append({"label": label, "href": abs_href})

    # De-duplicate by href
    seen = set()
    uniq = []
    for t in topics:
        if t["href"] in seen:
            continue
        seen.add(t["href"])
        uniq.append(t)
    return uniq


def parse_entries(html_text: str, base_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows = []
    
    # Entries are usually in tables. Link to card.cgi?identifier=...
    # We look for <a> tags linking to card.cgi
    # The structure seen: <p><a href="..."> Title<br></a></p> OR just <a>Title</a>
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "card.cgi" not in href:
            continue
        if "identifier=" not in href:
            continue
            
        # Check if this anchor wraps an image (thumbnail) or text (title)
        # We usually want the text one for the title, but the href contains the identifier.
        # The structure is often:
        # 1. Image link
        # 2. Text link (Title)
        
        # Strategy: capture identifier from href. 
        # Title might be in this tag or a sibling.
        # To avoid duplicates (img + text), we key by identifier.
        
        # Attempt to get text from this tag
        text_content = a_tag.get_text(strip=True)
        
        ident_match = re.search(r'identifier=([^&"#]+)', href)
        if not ident_match:
            continue
        ident = ident_match.group(1)
        
        # We want to associate a title with this identifier.
        # If this tag has text, use it. If it's an image, title might be empty.
        title = text_content
            
        card_url = urljoin(base_url, href.lstrip("./"))
        image_url = urljoin(base_url, f"YoukaiGazou/image/{ident}.jpg")
        
        rows.append({
            "identifier": ident,
            "title": title, # might be empty if it was the image link
            "card_url": card_url,
            "image_url": image_url
        })

    # Merge rows to get the best title for each identifier
    merged = {}
    for r in rows:
        ident = r["identifier"]
        if ident not in merged:
            merged[ident] = r
        else:
            # If current stored title is empty and this one has title, update it
            if not merged[ident]["title"] and r["title"]:
                merged[ident]["title"] = r["title"]
                
    return list(merged.values())


def find_pagination_links(html_text: str, base_url: str, ychar_value: str) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    links = []
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "search.cgi" not in href:
            continue
            
        txt = a_tag.get_text(strip=True)
        abs_href = urljoin(base_url, href)
        parsed = urlparse(abs_href)
        qs = parse_qs(parsed.query)
        
        yv = qs.get("ychar", [None])[0]
        if yv is None:
            continue

        # Check ychar match
        try:
            yv_dec = urllib.parse.unquote(yv)
            ychar_dec = urllib.parse.unquote(ychar_value)
            same_y = (yv == ychar_value) or (yv_dec == ychar_dec)
        except Exception:
            same_y = (yv == ychar_value)
            
        if not same_y:
            continue
            
        # Heuristic for "Next" / numeric pages
        if re.search(r'(次|Next|＞|>>|>|[0-9]{1,3})', txt):
            links.append(abs_href)

    # dedupe
    seen = set()
    out = []
    for u in links:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

# --- Main crawl logic ---
def crawl_topics(topics: List[Dict[str,str]], follow_pagination: bool = True, sleep: float = 0.3, user_agent: str = None, timeout: float = 15.0) -> List[Dict[str,str]]:
    try:
        import requests
    except ImportError:
        print("requests is required. Install with: pip install requests", file=sys.stderr)
        sys.exit(1)
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent or "Mozilla/5.0 (compatible; NichibunCrawler/1.0)"})
    all_rows: List[Dict[str, str]] = []
    seen_entries: Set[str] = set()
    for t in topics:
        topic_label = t["label"]
        topic_href = t["href"]
        # derive ychar for pagination matching
        ychar_value = parse_qs(urlparse(topic_href).query).get("ychar", [None])[0]
        if ychar_value is None:
            # try to keep ychar_value decoded from label as last resort
            ychar_value = urllib.parse.quote(topic_label)

        to_visit = [topic_href]
        visited: Set[str] = set()
        while to_visit:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                html_text = fetch(url, session=s, timeout=timeout, user_agent=user_agent)
            except Exception as ex:
                print(f"[warn] fetch failed: {url}   ({ex})", file=sys.stderr)
                continue

            # Extract entries
            for r in parse_entries(html_text, BASE):
                key = r["identifier"]
                if key in seen_entries:
                    continue
                seen_entries.add(key)
                r["topic_label"] = topic_label
                r["topic_href"] = topic_href
                all_rows.append(r)

            # Follow pagination
            if follow_pagination:
                for nxt in find_pagination_links(html_text, BASE, ychar_value):
                    if nxt not in visited and nxt not in to_visit:
                        to_visit.append(nxt)

            time.sleep(sleep)
    return all_rows

# --- Utilities ---
def write_csv(rows: List[Dict[str, str]], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["topic_label", "topic_href", "identifier", "title", "card_url", "image_url"])
        w.writeheader()
        for r in rows:
            w.writerow({
                "topic_label": r.get("topic_label",""),
                "topic_href": r.get("topic_href",""),
                "identifier": r["identifier"],
                "title": r.get("title",""),
                "card_url": r["card_url"],
                "image_url": r["image_url"],
            })

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

# --- CLI ---
def main():
    ap = argparse.ArgumentParser(description="Crawl Nichibun YoukaiGazou: collect entries by topic (ychar) from the index page.")
    ap.add_argument("--index-url", default=INDEX_URL, help=f"Index URL (default: {INDEX_URL})")
    ap.add_argument("--topics", nargs="*", default=None, help="Exact label texts to include (e.g., 鬼 疫神). If omitted, include all topics found.")
    ap.add_argument("--ychar", nargs="*", default=None, help="Direct ychar values to crawl (URL-encoded or decoded). Skips index parsing for these.")
    ap.add_argument("--out", default="nichibun_topics.csv", help="Output CSV path")
    ap.add_argument("--write-urls", default=None, help="Also write a newline-separated file of image URLs")
    ap.add_argument("--download-images", default=None, help="Directory to download images (optional, off by default)")
    ap.add_argument("--sleep", type=float, default=0.3, help="Delay between HTTP requests (default: 0.3s)")
    ap.add_argument("--no-pagination", action="store_true", help="Do not follow pagination links")
    ap.add_argument("--user-agent", default=None, help="Custom User-Agent header")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds (default: 15)")
    args = ap.parse_args()

    # Build topic list
    topics: List[Dict[str,str]] = []

    # 1) Topics by ychar (direct, if provided)
    if args.ychar:
        for yv in args.ychar:
            # Accept decoded unicode too; construct URL
            enc = urllib.parse.quote(urllib.parse.unquote(yv), safe="")
            href = urljoin(BASE, SEARCH_PATH) + f"?query=NILL&ychar={enc}"
            topics.append({"label": urllib.parse.unquote(enc), "href": href})

    # 2) Topics scraped from index (if no ychar or also in addition)
    if not args.ychar:
        idx_html = fetch(args.index_url, user_agent=args.user_agent, timeout=args.timeout)
        all_topics = parse_topics(idx_html, args.index_url)
        if args.topics:
            wanted = set(args.topics)
            topics.extend([t for t in all_topics if t["label"] in wanted])
        else:
            topics.extend(all_topics)

    if not topics:
        print("No topics found. Check --index-url or --topics/--ychar arguments.", file=sys.stderr)
        sys.exit(2)

    follow_pagination = not args.no_pagination
    rows = crawl_topics(
        topics,
        follow_pagination=follow_pagination,
        sleep=args.sleep,
        user_agent=args.user_agent,
        timeout=args.timeout,
    )

    # De-duplicate by identifier (keep first)
    seen = set()
    uniq = []
    for r in rows:
        if r["identifier"] in seen:
            continue
        seen.add(r["identifier"])
        uniq.append(r)

    out_csv = Path(args.out)
    write_csv(uniq, out_csv)
    print(f"[ok] Wrote {len(uniq)} rows to {out_csv}")

    if args.write_urls:
        url_path = Path(args.write_urls)
        write_urls(uniq, url_path)
        print(f"[ok] Wrote {len(uniq)} image URLs to {url_path}")

    if args.download_images:
        img_dir = Path(args.download_images)
        print(f"[info] Downloading {len(uniq)} images to {img_dir} ...")
        download_images(uniq, img_dir, sleep=args.sleep, user_agent=args.user_agent, timeout=args.timeout)
        print("[ok] Done.")

if __name__ == "__main__":
    main()
