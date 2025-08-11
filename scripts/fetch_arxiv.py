# scripts/fetch_arxiv.py
import argparse, os, json
from datetime import datetime, timedelta, timezone
import requests, yaml, feedparser

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/topics.yml")
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(DATA_DIR, exist_ok=True)

ARXIV_API = "http://export.arxiv.org/api/query"

def load_profiles(want=None):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    profiles = {p["name"]: p for p in cfg.get("profiles", [])}
    if not want:
        return list(profiles.values())
    return [profiles[n] for n in want if n in profiles]

def clause(term: str) -> str:
    t = term.strip()
    return f'(ti:"{t}" OR abs:"{t}")'

def build_query(include_terms, exclude_terms):
    inc = " OR ".join([clause(t) for t in include_terms]) if include_terms else ""
    exc = " OR ".join([clause(t) for t in exclude_terms]) if exclude_terms else ""
    q = f"({inc})" if inc else ""
    if exc:
        q += f" AND NOT ({exc})"
    return q or 'all:protein'

def fetch(query, max_results=100):
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    r = requests.get(ARXIV_API, params=params, timeout=30)
    r.raise_for_status()
    return feedparser.parse(r.text).entries

def within_days(published_str, days):
    if days <= 0: return True
    try:
        dt = datetime.strptime(published_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return True
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--max", type=int, default=120)
    ap.add_argument("--profiles", nargs="*", default=None, help="可选：只抓这些 profile 名称")
    args = ap.parse_args()

    chosen = load_profiles(args.profiles)
    all_results = {}
    for p in chosen:
        q = build_query(p.get("include", []), p.get("exclude", []))
        print(f"[FETCH] {p['name']} -> {q}")
        entries = fetch(q, args.max)
        items = []
        for e in entries:
            if within_days(e.published, args.days):
                items.append({
                    "title": e.title,
                    "summary": getattr(e, "summary", "").strip(),
                    "link": e.link,
                    "published": e.published,
                    "authors": ", ".join([a.name for a in getattr(e, "authors", [])]) if hasattr(e, "authors") else "",
                    "topic": p["name"],
                })
        all_results[p["name"]] = items
        print(f"[OK] {p['name']} kept {len(items)} items within {args.days} days")

    out_file = os.path.join(DATA_DIR, "arxiv.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved -> {out_file}")

if __name__ == "__main__":
    main()
