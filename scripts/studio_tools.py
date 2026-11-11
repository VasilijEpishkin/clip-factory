#!/usr/bin/env python3
"""Поиск инструментов Clip Factory во всех реестрах (без установки)."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "studio-addons"
SOURCES = (
    "catalog.json",
    "media-tools.json",
    "research-open-source-higgsfield-2026.json",
    "research-comfyui-extensions-2026.json",
    "research-moss-vsr-2026.json",
)


def collect(query="", category=""):
    """Вернуть записи с указанием реестра и сохранением upstream-метаданных."""
    entries = []
    for name in SOURCES:
        source = REGISTRY_DIR / name
        if not source.is_file():
            continue
        data = json.loads(source.read_text(encoding="utf-8"))
        for item in data.get("tools", []):
            entry = {**item, "registry": name}
            searchable = json.dumps(entry, ensure_ascii=False, sort_keys=True).lower()
            group = str(entry.get("category") or entry.get("scope") or "").lower()
            if query.lower() not in searchable or (category and category.lower() not in group):
                continue
            entries.append(entry)
    return entries


def main():
    p = argparse.ArgumentParser(description="Каталог программ и навыков Clip Factory")
    p.add_argument("query", nargs="?", default="", help="Название или задача, по-русски или по-английски")
    p.add_argument("--category", help="Фильтр категории из реестра")
    p.add_argument("--json", action="store_true", help="Вывести JSON для агента")
    args = p.parse_args()
    items = collect(query=args.query, category=args.category or "")
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        for item in items:
            name = item.get("name", item.get("id", "без названия"))
            status = (item.get("decision") or item.get("learning_status")
                      or item.get("verification") or item.get("status") or "кандидат")
            purpose = (item.get("purpose") or item.get("capability")
                       or item.get("output") or item.get("scope") or "Не описано")
            print(f"\n{name}  [{status}]")
            print(f"  Для чего: {purpose}")
            print(f"  Источник: {item.get('source') or 'не установлен'}")
            print(f"  Карточка: {item['registry']}")
        print(f"\nВсего: {len(items)} записей. Каталог не устанавливает программы.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
