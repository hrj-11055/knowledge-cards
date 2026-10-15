#!/usr/bin/env python3
"""Extract fenced card prompts from the documented Markdown heading format."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CHAPTER = re.compile(r"^# 第\s*(\d+)\s*章\s*[·：:]\s*(.+?)\s*$")
CARD = re.compile(r"^## 卡片\s*([\d.]+)\s*[·：:]\s*(.+?)\s*$")


def extract(markdown: str) -> list[dict[str, str | int]]:
    rows = []
    chapter_no = None
    chapter_title = None
    card = None
    fence = False
    body = []
    for line in markdown.splitlines():
        if not fence:
            match = CHAPTER.match(line)
            if match:
                chapter_no, chapter_title = int(match.group(1)), match.group(2)
                continue
            match = CARD.match(line)
            if match:
                if chapter_no is None:
                    raise ValueError("card appears before chapter")
                card = (match.group(1), match.group(2))
                continue
            if line.startswith("```") and card:
                fence = True
                body = []
        elif line.startswith("```"):
            if not any(part.strip() for part in body):
                raise ValueError(f"empty prompt: {card[0]}")
            rows.append({"chapter_no": chapter_no, "chapter_title": chapter_title,
                         "card_no": card[0], "card_title": card[1],
                         "prompt": "\n".join(body).strip()})
            card = None
            fence = False
        else:
            body.append(line)
    if fence:
        raise ValueError("unclosed code fence")
    if not rows:
        raise ValueError("no card prompts found")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = extract(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(rows)} card prompt(s) to {args.output}")


if __name__ == "__main__":
    main()
