#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize papers with Qwen and build a markdown digest.
Usage:
  python scripts/summarize_qwen.py --date 2025-08-11 --limit 20
Requires:
  - env QWEN_API_KEY  (set via GitHub Actions secret)
"""
import os, json, argparse, time, sys
from datetime import datetime
from typing import List, Dict
import requests

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/arxiv.json")
OUT_DIR   = os.path.join(os.path.dirname(__file__), "../digests")
os.makedirs(OUT_DIR, exist_ok=True)

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "").strip()
# 采用 OpenAI 兼容接口（DashScope Compatible Mode）
BASE_URL = os.getenv(
    "QWEN_COMPAT_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)
MODEL = os.getenv("QWEN_MODEL", "qwen-plus")  # 也可用 qwen2.5 等

SYS_PROMPT = (
    "你是资深科研助理。请根据给定的论文标题、作者、摘要，"
    "输出结构化要点，使用中文：\n"
    "1) 研究问题与背景（2-3行）\n"
    "2) 方法框架（条目化，术语标准化）\n"
    "3) 关键结果（尽量保留定量指标）\n"
    "4) 局限性与威胁（>=2点）\n"
    "5) 复现线索（数据/代码/超参，如无写“未给出”）\n"
    "6) 三行电梯演讲（<= 200字）\n"
    "只返回 Markdown 内容，不要额外寒暄。"
)

def call_qwen(title: str, authors: str, summary: str, link: str) -> str:
    if not QWEN_API_KEY:
        return "_（未配置 QWEN_API_KEY，跳过模型摘要）_"
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json",
    }
    user = (
        f"【题目】{title}\n"
        f"【作者】{authors}\n"
        f"【链接】{link}\n"
        f"【摘要】{summary}\n"
    )
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    for attempt in range(3):
        try:
            resp = requests.post(BASE_URL, headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                js = resp.json()
                # OpenAI 兼容格式
                content = js["choices"][0]["message"]["content"].strip()
                return content
            elif resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
            else:
                return f"_Qwen 调用失败（HTTP {resp.status_code}）：{resp.text[:200]}_"
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return "_Qwen 调用失败（多次重试仍失败）_"

def load_papers(limit: int) -> List[Dict]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for topic, lst in data.items():
        for p in lst:
            items.append({**p, "topic": topic})
    # 简单按发布时间降序（已是最新），截断
    return items[:limit]

def build_md(date_str: str, items: List[Dict]) -> str:
    lines = [f"# 📚 Daily Paper Digest — {date_str}", ""]
    # 按 topic 分组展示
    from collections import defaultdict
    groups = defaultdict(list)
    for it in items:
        groups[it.get("topic", "misc")].append(it)
    for topic in sorted(groups.keys()):
        lines.append(f"## {topic}")
        for idx, p in enumerate(groups[topic], 1):
            lines.append(f"### {idx}. {p['title']}")
            if p.get("authors"):
                lines.append(f"- Authors: {p['authors']}")
            lines.append(f"- Published: {p.get('published','')}")
            lines.append(f"- Link: {p['link']}\n")
            # 原摘要（裁剪）
            short = (p.get("summary","").strip() or "")[:600]
            if short:
                lines.append("**Abstract (truncated)**")
                lines.append(short)
                lines.append("")
            # Qwen 摘要
            lines.append("**Qwen Summary**")
            lines.append(p.get("_qwen", "_(no summary)_"))
            lines.append("\n---\n")
    return "\n".join(lines).strip() + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"))
    ap.add_argument("--limit", type=int, default=30, help="最多处理多少篇")
    args = ap.parse_args()

    papers = load_papers(args.limit)
    # 逐篇调用 Qwen
    for i, p in enumerate(papers, 1):
        print(f"[{i}/{len(papers)}] {p['title'][:60]} ...")
        p["_qwen"] = call_qwen(
            title=p["title"],
            authors=p.get("authors", ""),
            summary=p.get("summary", ""),
            link=p["link"],
        )
        # 轻微节流
        time.sleep(0.3)

    md = build_md(args.date, papers)
    out_path = os.path.join(OUT_DIR, f"digest_{args.date}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] Wrote {out_path}")

if __name__ == "__main__":
    main()
