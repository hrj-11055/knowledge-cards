"""
batch_send_clipboard.py · 半自动剪贴板模式（跨平台 · Mac/Windows/Linux）

工作流：
1. 脚本依次把每条提示词 copy 到剪贴板
2. 你切到 ChatGPT（网页或桌面端），粘贴 + 发送
3. 等 ChatGPT 出图、保存图片
4. 回到终端，按 Enter 切换到下一条

用法：
    python3 batch_send_clipboard.py            # 跑全部
    python3 batch_send_clipboard.py 1 5        # 只跑第 1 条到第 5 条
    python3 batch_send_clipboard.py --start 10 # 从第 10 条开始
    python3 batch_send_clipboard.py --filter 记忆  # 按标题筛选
    python3 batch_send_clipboard.py --prompts-file prompts_xxx.json
"""

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def find_prompts_file() -> Path:
    for d in [Path.cwd(), Path(__file__).resolve().parent]:
        f = d / "prompts.json"
        if f.exists():
            return f
    return Path(__file__).resolve().parent / "prompts.json"


def copy_to_clipboard(text: str):
    """跨平台复制到剪贴板"""
    system = platform.system()
    if system == "Darwin":  # macOS
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(input=text.encode("utf-8"))
    elif system == "Windows":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::InputEncoding = [Text.Encoding]::UTF8; "
             "$input | Set-Clipboard"],
            input=text.encode("utf-8"),
            check=True,
        )
    else:  # Linux
        for cmd in (["xclip", "-selection", "clipboard"],
                    ["xsel", "--clipboard", "--input"]):
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(input=text.encode("utf-8"))
                return
            except FileNotFoundError:
                continue
        print("❌ 需要安装 xclip 或 xsel：sudo apt install xclip",
              file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(
        description="半自动剪贴板模式 — 逐条复制提示词到剪贴板")
    ap.add_argument("range_start", nargs="?", type=int, default=1,
                    help="起始序号（1-based）")
    ap.add_argument("range_end", nargs="?", type=int, default=None,
                    help="结束序号（含）")
    ap.add_argument("--start", type=int, help="同 range_start")
    ap.add_argument("--filter", type=str,
                    help="按章节标题/卡片标题模糊筛选")
    ap.add_argument("--prompts-file", type=Path, default=find_prompts_file(),
                    help="提示词 JSON 文件")
    args = ap.parse_args()

    prompts_file = args.prompts_file
    if not prompts_file.exists():
        print(f"❌ 找不到 {prompts_file}，请先运行 extract_prompts.py")
        sys.exit(1)

    prompts = json.loads(prompts_file.read_text(encoding="utf-8"))

    if args.filter:
        prompts = [p for p in prompts
                   if args.filter in p["chapter_title"]
                   or args.filter in p["card_title"]]
        if not prompts:
            print(f"❌ 没有匹配到 filter：{args.filter}")
            sys.exit(1)

    start = (args.start or args.range_start) - 1
    end = args.range_end if args.range_end else len(prompts)
    sub = prompts[start:end]

    paste_key = "Cmd+V" if platform.system() == "Darwin" else "Ctrl+V"

    total = len(sub)
    print(f"🚀 准备发送 {total} 条提示词  [{platform.system()}]")
    print(f"📋 流程：脚本复制到剪贴板 → 你 {paste_key} 粘贴 → Enter 发送")
    print(f"💡 出图后回来按 Enter 进入下一条；按 Ctrl+C 退出\n")
    input("准备好了？回车开始 → ")

    for idx, p in enumerate(sub, start=start + 1):
        header = (f"[{idx}/{start + len(sub)}] "
                  f"第 {p['chapter_no']:02d} 章 · "
                  f"卡片 {p['card_no']} · {p['card_title']}")
        print("\n" + "=" * 60)
        print(header)
        print("=" * 60)
        copy_to_clipboard(p["prompt"])
        print(f"✅ 已复制到剪贴板（{len(p['prompt'])} 字符）")
        print(f"👉 切到 ChatGPT，{paste_key} 粘贴，Enter 发送")
        try:
            input("    出图后按 Enter 进入下一条 → ")
        except KeyboardInterrupt:
            print(f"\n👋 已中断，下次可以用 --start {idx} 继续")
            sys.exit(0)

    print("\n🎉 全部完成！")


if __name__ == "__main__":
    main()
