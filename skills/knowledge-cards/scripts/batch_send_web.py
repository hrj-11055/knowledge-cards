"""
batch_send_web.py · 全自动网页模式（跨平台 · Playwright）

使用 Playwright 自动化浏览器：
1. 打开 ChatGPT 网页版（chatgpt.com）
2. 等待用户手动登录
3. 逐条发送提示词
4. 自动等待图片生成并下载到本地目录

安装：
    pip3 install playwright
    python3 -m playwright install chromium

用法：
    python3 batch_send_web.py                           # 跑全部
    python3 batch_send_web.py 1 5                       # 跑第 1-5 条
    python3 batch_send_web.py --start 10                # 从第 10 条续传
    python3 batch_send_web.py --filter 记忆             # 按标题筛选
    python3 batch_send_web.py --wait 120                # 每条等 120 秒
    python3 batch_send_web.py --output ./generated/心理  # 指定输出目录
    python3 batch_send_web.py --dry-run                 # 只打印不发送
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path


def find_prompts_file() -> Path:
    for d in [Path.cwd(), Path(__file__).resolve().parent]:
        f = d / "prompts.json"
        if f.exists():
            return f
    return Path(__file__).resolve().parent / "prompts.json"


def main():
    ap = argparse.ArgumentParser(
        description="全自动网页模式 — Playwright 自动化 ChatGPT 网页 + 自动下载图片")
    ap.add_argument("range_start", nargs="?", type=int, default=1)
    ap.add_argument("range_end", nargs="?", type=int, default=None)
    ap.add_argument("--start", type=int)
    ap.add_argument("--filter", type=str)
    ap.add_argument("--prompts-file", type=Path, default=find_prompts_file())
    ap.add_argument("--wait", type=int, default=120,
                    help="每条提示词后等待秒数（图片生成时间）")
    ap.add_argument("--output", type=Path,
                    default=Path.cwd() / "generated",
                    help="图片输出目录")
    ap.add_argument("--style-anchor", type=str, default=None,
                    help="风格锚定消息（首条发送前会先发这段）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 需要 Playwright：pip3 install playwright && python3 -m playwright install chromium")
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

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🌐 Playwright 网页模式 · {len(sub)} 条 · 每条等 {args.wait} 秒")
    print(f"📁 图片保存到：{output_dir.resolve()}")
    print()

    if args.dry_run:
        print("🧪 DRY RUN — 只打印不发送\n")
        for idx, p in enumerate(sub, start=start + 1):
            print(f"[{idx}] 第 {p['chapter_no']:02d} 章 · "
                  f"卡片 {p['card_no']} · {p['card_title']}")
            print(p["prompt"][:150] + "...\n")
        return

    with sync_playwright() as pw:
        # 使用持久化上下文，登录状态会保存到 user_data_dir
        user_data = Path.home() / ".cache" / "knowledge-cards-browser"
        context = pw.chromium.launch_persistent_context(
            str(user_data),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # 打开 ChatGPT
        print("🌐 正在打开 ChatGPT…")
        page.goto("https://chatgpt.com", wait_until="networkidle")
        time.sleep(2)

        # 检查是否需要登录
        print("⚠️  如果需要登录，请在浏览器中完成登录。")
        print("    登录完成后，请回到终端按 Enter 继续。\n")
        input("👉 登录完成后按 Enter → ")

        # 发送风格锚定消息
        if args.style_anchor:
            print("\n🎨 发送风格锚定消息…")
            _send_message(page, args.style_anchor)
            print("   等待确认…")
            time.sleep(10)

        # 开始逐条发送
        image_count = 0
        for idx, p in enumerate(sub, start=start + 1):
            card_label = (f"第 {p['chapter_no']:02d} 章 · "
                          f"卡片 {p['card_no']} · {p['card_title']}")
            print(f"\n{'─' * 60}")
            print(f"[{idx}/{start + len(sub)}] {card_label}")
            print("─" * 60)

            # 发送提示词
            _send_message(page, p["prompt"])
            print("📤 已发送，等待出图…")

            # 等待图片生成
            remaining = args.wait
            while remaining > 0:
                chunk = min(10, remaining)
                time.sleep(chunk)
                remaining -= chunk
                print(f"   ⏳ 还剩 {remaining} 秒…", end="\r", flush=True)
            print(" " * 40, end="\r")

            # 尝试下载图片
            downloaded = _download_latest_image(page, output_dir,
                                                p["card_no"], image_count)
            if downloaded:
                image_count += 1
                print(f"   📥 已下载：{downloaded.name}")
            else:
                print(f"   ⚠️  未检测到新图片，可能需要手动保存")
                print(f"   💡 提示：可以等更长时间（--wait 180）或手动下载")

        context.close()

    print(f"\n🎉 全部完成！共下载 {image_count} 张图片到 {output_dir}")


def _send_message(page, text: str):
    """在 ChatGPT 网页中发送一条消息"""
    # ChatGPT 的输入框选择器（可能会随版本更新变化）
    selectors = [
        '#prompt-textarea',
        'textarea[data-id="root"]',
        'textarea[placeholder]',
        'div[contenteditable="true"]',
    ]

    input_box = None
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.is_visible():
            input_box = loc
            break

    if input_box is None:
        print("   ⚠️  找不到输入框，请确保 ChatGPT 页面已加载")
        return

    input_box.click()
    time.sleep(0.3)
    input_box.fill(text)
    time.sleep(0.5)

    # 按回车发送
    input_box.press("Enter")


def _download_latest_image(page, output_dir: Path, card_no: str,
                           existing_count: int) -> Path | None:
    """尝试从 ChatGPT 页面下载最新生成的图片"""
    # 查找页面中所有图片元素
    # ChatGPT 生成的图片通常在特定容器中
    images = page.locator('img[src^="data:"], img[src*="cdn.oaistatic"], '
                          'img[src*="chatgpt"], img[src*="oai"]').all()

    if not images:
        return None

    try:
        # 获取最后一张图片的 src
        last_img = images[-1]
        src = last_img.get_attribute("src")

        if not src:
            return None

        filename = f"card_{card_no.replace('.', '_')}_{existing_count + 1:03d}.png"
        filepath = output_dir / filename

        if src.startswith("data:"):
            # base64 data URI
            import base64
            header, data = src.split(",", 1)
            img_bytes = base64.b64decode(data)
            filepath.write_bytes(img_bytes)
        else:
            # URL — 下载
            resp = page.request.get(src)
            if resp.ok:
                filepath.write_bytes(resp.body())
            else:
                return None

        return filepath

    except Exception as e:
        print(f"   (下载失败: {e})")
        return None


if __name__ == "__main__":
    main()
