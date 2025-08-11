#!/usr/bin/env python3
import json
import argparse
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
DIGEST_DIR = os.path.join(os.path.dirname(__file__), "../digests")
os.makedirs(DIGEST_DIR, exist_ok=True)

def summarize_papers(papers):
    # TODO: 这里后续接 Qwen API
    summaries = []
    for topic, items in papers.items():
        summaries.append(f"## {topic}")
        for p in items:
            summaries.append(f"- [{p['title']}]({p['link']})\n  {p['summary'][:200]}...")
    return "\n".join(summaries)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    in_file = os.path.join(DATA_DIR, "arxiv.json")
    with open(in_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    digest_content = summarize_papers(papers)
    out_file = os.path.join(DIGEST_DIR, f"digest_{args.date}.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(digest_content)

    print(f"Digest saved to {out_file}")

if __name__ == "__main__":
    main()
