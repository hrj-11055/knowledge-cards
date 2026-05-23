"""
extract_prompts.py
将知识卡片提示词集 Markdown 文件提取成结构化 JSON。

用法：
    python3 extract_prompts.py [markdown文件路径]

如果不指定文件路径，会在当前目录和脚本所在目录查找以"知识卡片提示词集"结尾的 .md 文件。

输出：
    prompts.json — 包含 章节、卡片编号、标题、提示词正文 的列表（与输入文件同目录）
"""

import json
import re
import sys
from pathlib import Path


def find_md_file() -> Path:
    """自动查找提示词集 Markdown 文件"""
    search_dirs = [Path.cwd(), Path(__file__).resolve().parent]
    for d in search_dirs:
        for f in d.glob("*知识卡片提示词集*.md"):
            return f
    return None


def extract(md_text: str):
    """
    解析逻辑：
    - 章节标题：以 '# 第 XX 章 ·' 开头
    - 卡片标题：以 '## 卡片 X.Y · ' 开头
    - 提示词正文：紧跟在卡片标题之后的 ``` 代码块
    """
    chapters = []
    lines = md_text.splitlines()

    chapter_re = re.compile(r"^# 第\s*(\d+)\s*(?:章|主题)\s*[·\·]\s*(.+)$")
    card_re = re.compile(r"^##\s*卡片\s*([\d\.]+)\s*[·\·]\s*(.+)$")

    cur_chapter = None
    prompts = []

    i = 0
    while i < len(lines):
        line = lines[i]
        m_ch = chapter_re.match(line)
        if m_ch:
            cur_chapter = {
                "number": int(m_ch.group(1)),
                "title": m_ch.group(2).strip(),
            }
            chapters.append(cur_chapter)
            i += 1
            continue

        m_card = card_re.match(line)
        if m_card and cur_chapter is not None:
            card_no = m_card.group(1).strip()
            card_title = m_card.group(2).strip()

            # 向下找第一个 ``` 代码块
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            if j >= len(lines):
                i += 1
                continue
            # 收集到下一个 ```
            k = j + 1
            buf = []
            while k < len(lines) and not lines[k].startswith("```"):
                buf.append(lines[k])
                k += 1
            prompt_body = "\n".join(buf).strip()

            prompts.append({
                "chapter_no": cur_chapter["number"],
                "chapter_title": cur_chapter["title"],
                "card_no": card_no,
                "card_title": card_title,
                "prompt": prompt_body,
            })
            i = k + 1
            continue

        i += 1

    return chapters, prompts


def main():
    # 确定输入文件
    if len(sys.argv) > 1:
        md_file = Path(sys.argv[1])
    else:
        md_file = find_md_file()

    if not md_file or not md_file.exists():
        print("❌ 找不到 Markdown 文件，请指定路径：python3 extract_prompts.py <文件.md>", file=sys.stderr)
        sys.exit(1)

    out_file = md_file.parent / "prompts.json"

    md_text = md_file.read_text(encoding="utf-8")
    chapters, prompts = extract(md_text)

    print(f"✅ 解析到 {len(chapters)} 章，{len(prompts)} 条提示词")
    for ch in chapters:
        ch_prompts = [p for p in prompts if p["chapter_no"] == ch["number"]]
        print(f"   第 {ch['number']:02d} 章 · {ch['title']:<14} · {len(ch_prompts)} 张")

    out_file.write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n📦 已写入：{out_file}")


if __name__ == "__main__":
    main()
