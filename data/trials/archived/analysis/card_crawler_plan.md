## Identifier heuristics from keyword crawl

Sample size: 1,810 rows scraped via `nichibun_keyword_scraper.py` using keywords  
`[鬼, 疫神, 天狗, 河童, 幽霊, 妖怪, 狐, 龍]`.

| Keyword | AAA range | BBBB range (unique) | CCCC range (unique) | DDDD range (unique) |
|---------|-----------|---------------------|---------------------|---------------------|
| 鬼      | 426..426 (118) | 003..454 (118) | 001..116 (55) | 000..021 (22) |
| 疫神    | 426..426 (6)   | 012..290 (6)   | 001..022 (22) | 000..000 (1) |
| 天狗    | 426..426 (31)  | 051..442 (31)  | 000..069 (22) | 000..014 (14) |
| 河童    | 426..426 (26)  | 093..446 (26)  | 001..074 (18) | 000..044 (9)  |
| 幽霊    | 426..426 (43)  | 051..450 (43)  | 001..073 (26) | 000..026 (12) |
| 妖怪    | 426..426 (18)  | 003..452 (18)  | 001..041 (9)  | 000..058 (54) |
| 狐      | 426..426 (50)  | 051..452 (50)  | 001..118 (39) | 000..047 (28) |
| 龍      | 426..426 (40)  | 012..453 (40)  | 000..072 (30) | 000..009 (10) |

Notes:
- All keywords so far map to the same `AAA=426` collection (`U426`). Other AAA values likely exist but were not hit by these keywords; additional seed terms or other entry points are needed.
- `BBBB` behaves like a volume/chapter index. For 鬼 it spans 003–454 with no leading gaps once the lower bound is reached.
- `CCCC` looks like a page/section counter; typically ≤120.
- `DDDD` is the per-section image index; most observed ranges stay below 60.

## Proposed direct card crawler plan

1. **Seed acquisition**
   - Use `nichibun_keyword_scraper.py` (keyword search) and a future `--identifier-seed` option to gather a growing list of confirmed identifiers.
   - Persist seeds in `data/identifier_seeds.csv` along with the originating keyword/topic, timestamp, and HTTP status.

2. **Range inference**
   - For each `(AAA, BBBB)` pair present in the seeds, derive the observed min/max of `CCCC` and `DDDD`.
   - Implement a lightweight inference module (`identifier_ranges.py`) that can update ranges incrementally (e.g., widen when new seeds extend the min/max).

3. **Target generation**
   - For every `(AAA, BBBB)` range, generate candidate identifiers by iterating `CCCC` and `DDDD` within the inferred bounds plus a configurable safety margin (e.g., `min-2` to `max+2`).
   - Queue new combinations only if they have not been fetched before (track in SQLite or a simple CSV/Parquet log).

4. **Card fetcher**
   - Build `nichibun_card_crawler.py`:
     - Accepts a batch of candidate identifiers.
     - Fetches `card.cgi?identifier=...`, reusing the existing BeautifulSoup parser to extract metadata (title, author, subjects, description).
     - Handles HTTP 404/302 gracefully, marking those identifiers as empty so they are not retried unless ranges expand.
     - Optional image download flag using the existing `download_images` helper.

5. **Feedback loop**
   - Successful card fetches feed back into the range inference store, allowing the crawler to push boundaries automatically.
   - Periodically re-run the keyword scraper with new terms to discover fresh `(AAA, BBBB)` pairs outside the current coverage.

6. **Operational guardrails**
   - Centralize politeness controls (User-Agent, throttle, retry budget) shared between keyword and card crawlers.
   - Keep run metadata (timestamp, keyword, identifier, status) for auditability and to restart interrupted runs safely.

