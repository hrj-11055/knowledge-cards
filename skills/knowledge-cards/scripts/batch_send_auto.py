"""
batch_send_auto.py · 全自动桌面端模式（跨平台 · Mac/Windows/Linux）

macOS：使用原生 AppleScript（零依赖）
Windows/Linux：使用 pyautogui（需 pip3 install pyautogui）

工作流：
1. 你提前打开 ChatGPT（桌面端或浏览器），确认输入框聚焦
2. 启动脚本，倒计时后自动：复制 → 激活窗口 → 粘贴 → 发送 → 等待出图

用法：
    python3 batch_send_auto.py --dry-run
    python3 batch_send_auto.py 1 3 --wait 90
    python3 batch_send_auto.py --filter 记忆 --wait 60
    python3 batch_send_auto.py --prompts-file prompts_xxx.json
"""

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def find_prompts_file() -> Path:
    for d in [Path.cwd(), Path(__file__).resolve().parent]:
        f = d / "prompts.json"
        if f.exists():
            return f
    return Path(__file__).resolve().parent / "prompts.json"


# ── macOS: AppleScript（零依赖） ──────────────────────────────

def copy_to_clipboard_macos(text: str):
    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    p.communicate(input=text.encode("utf-8"))


def paste_and_send_macos(app_name="ChatGPT"):
    subprocess.run(["osascript", "-e",
                    f'tell application "{app_name}" to activate'],
                   check=False)
    time.sleep(1.0)
    script = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.5
        key code 36
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=False)


# ── Windows/Linux: pyautogui ──────────────────────────────────

def copy_to_clipboard_crossplatform(text: str):
    system = platform.system()
    if system == "Windows":
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


def paste_and_send_crossplatform():
    import pyautogui
    modifier = "command" if platform.system() == "Darwin" else "ctrl"
    pyautogui.hotkey(modifier, "v")
    time.sleep(0.5)
    pyautogui.press("enter")


# ── 统一接口 ──────────────────────────────────────────────────

SYSTEM = platform.system()


def copy_to_clipboard(text: str):
    if SYSTEM == "Darwin":
        copy_to_clipboard_macos(text)
    else:
        copy_to_clipboard_crossplatform(text)


def paste_and_send():
    if SYSTEM == "Darwin":
        paste_and_send_macos()
    else:
        paste_and_send_crossplatform()


def main():
    ap = argparse.ArgumentParser(
        description="全自动桌面端模式 — 自动粘贴发送到 ChatGPT")
    ap.add_argument("range_start", nargs="?", type=int, default=1)
    ap.add_argument("range_end", nargs="?", type=int, default=None)
    ap.add_argument("--start", type=int)
    ap.add_argument("--filter", type=str)
    ap.add_argument("--prompts-file", type=Path, default=find_prompts_file(),
                    help="提示词 JSON 文件")
    ap.add_argument("--wait", type=int, default=90,
                    help="每条提示词后等待秒数")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印不发送")
    if SYSTEM == "Darwin":
        ap.add_argument("--app", type=str, default="ChatGPT",
                        help="ChatGPT 桌面端 App 名称（macOS）")
    args = ap.parse_args()

    if SYSTEM != "Darwin":
        try:
            import pyautogui  # noqa: F401
        except ImportError:
            print("❌ Windows/Linux 需要 pyautogui：pip3 install pyautogui")
            sys.exit(1)

    if not args.prompts_file.exists():
        print(f"❌ 找不到 {args.prompts_file}，请先运行 extract_prompts.py")
        sys.exit(1)

    prompts = json.loads(args.prompts_file.read_text(encoding="utf-8"))

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

    mode = "AppleScript" if SYSTEM == "Darwin" else "pyautogui"
    print(f"🤖 全自动模式（{mode}）· {SYSTEM} · "
          f"共 {len(sub)} 条 · 每条等 {args.wait} 秒")

    if args.dry_run:
        print("🧪 DRY RUN — 不会真的发送\n")
    else:
        print("⚠️  3 秒后开始，请切到 ChatGPT 并保持输入框聚焦")
        if SYSTEM == "Darwin":
            print("    （首次运行需在「系统设置 → 辅助功能」给终端开权限）")
        print()
        for s in (3, 2, 1):
            print(f"   {s}...")
            time.sleep(1)

    for idx, p in enumerate(sub, start=start + 1):
        header = (f"[{idx}/{start + len(sub)}] "
                  f"第 {p['chapter_no']:02d} 章 · "
                  f"卡片 {p['card_no']} · {p['card_title']}")
        print("\n" + "─" * 60)
        print(header)
        print("─" * 60)

        if args.dry_run:
            print(p["prompt"][:200] + ("..." if len(p["prompt"]) > 200 else ""))
            time.sleep(0.3)
            continue

        copy_to_clipboard(p["prompt"])
        print("📋 已复制到剪贴板")

        if SYSTEM == "Darwin":
            subprocess.run(["osascript", "-e",
                            f'tell application "{args.app}" to activate'],
                           check=False)
            time.sleep(1.0)

        paste_and_send()
        print("📤 已发送，等待出图…")

        remaining = args.wait
        while remaining > 0:
            chunk = min(10, remaining)
            time.sleep(chunk)
            remaining -= chunk
            print(f"   ⏳ 还剩 {remaining} 秒…", end="\r", flush=True)
        print(" " * 30, end="\r")

    print("\n🎉 全部完成！")


if __name__ == "__main__":
    main()
