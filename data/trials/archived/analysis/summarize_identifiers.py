#!/usr/bin/env python3
from collections import defaultdict
import csv
from pathlib import Path
import re

CSV_PATH = Path("data/nichibun_keywords.csv")


def main() -> None:
    stats = defaultdict(
        lambda: {
            "AAA": set(),
            "BBBB": set(),
            "CCCC": set(),
            "DDDD": set(),
            "AAA_min": None,
            "AAA_max": None,
            "BBBB_min": None,
            "BBBB_max": None,
            "CCCC_min": None,
            "CCCC_max": None,
            "DDDD_min": None,
            "DDDD_max": None,
        }
    )

    with CSV_PATH.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            identifier = row["identifier"]
            keyword = row["keyword"]
            m = re.match(r"U(\d+)_nichibunken_(\d{4})_(\d{4})_(\d{4})", identifier)
            if not m:
                continue
            AAA, BBBB, CCCC, DDDD = map(int, m.groups())
            bucket = stats[keyword]
            for key, value in (("AAA", AAA), ("BBBB", BBBB), ("CCCC", CCCC), ("DDDD", DDDD)):
                bucket[key].add(value)
                min_key = f"{key}_min"
                max_key = f"{key}_max"
                bucket[min_key] = value if bucket[min_key] is None else min(bucket[min_key], value)
                bucket[max_key] = value if bucket[max_key] is None else max(bucket[max_key], value)

    for kw, data in stats.items():
        print(f"{kw}:")
        for key in ("AAA", "BBBB", "CCCC", "DDDD"):
            print(
                f"  {key}: {data[f'{key}_min']}..{data[f'{key}_max']} "
                f"({len(data[key])} unique)"
            )


if __name__ == "__main__":
    main()

