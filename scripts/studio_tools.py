#!/usr/bin/env python3
"""Search curated optional tools without installing software or models."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "studio-addons" / "catalog.json", ROOT / "studio-addons" / "media-tools.json"]

def main():
    p = argparse.ArgumentParser(description="Clip Factory optional media tool catalog")
    p.add_argument("query", nargs="?", default="", help="Name, purpose, category or id")
    p.add_argument("--category", help="Filter by category (image, video, audio, generation, 3d-motion)")
    p.add_argument("--json", action="store_true", help="Print matching records as JSON")
    args = p.parse_args()
    matches = []
    for source in SOURCES:
        if not source.exists():
            continue
        data = json.loads(source.read_text(encoding="utf-8"))
        for item in data.get("tools", []):
            item = {**item, "registry": source.name}
            searchable = " ".join(str(v) for v in item.values()).lower()
            if args.query.lower() not in searchable:
                continue
            if args.category and args.category.lower() not in str(item.get("category", item.get("scope", ""))).lower():
                continue
            matches.append(item)
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        for item in matches:
            print(f'{item["id"]:25} {item.get("status","unknown"):24} {item.get("source") or "source unknown"}')
            print(f'  {item.get("capability", item.get("scope", ""))}')
        print(f"{len(matches)} matching tools (registry only; not installed)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
