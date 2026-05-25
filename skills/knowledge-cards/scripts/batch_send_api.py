"""
batch_send_api.py · 全自动 API 模式（跨平台 · OpenAI API）

直接调用 OpenAI Images API 生成图片，自动下载到本地。
最可靠的自动化方案，无需浏览器、无需桌面端。

安装：
    pip3 install openai

配置：
    export OPENAI_API_KEY="sk-..."

用法：
    python3 batch_send_api.py                            # 跑全部
    python3 batch_send_api.py 1 5                        # 跑第 1-5 条
    python3 batch_send_api.py --start 10                 # 从第 10 条续传
    python3 batch_send_api.py --filter 记忆              # 按标题筛选
    python3 batch_send_api.py --model gpt-image-1        # 指定模型
    python3 batch_send_api.py --size 1536x1024           # 指定尺寸
    python3 batch_send_api.py --output ./generated/心理   # 指定输出目录
    python3 batch_send_api.py --iter 2                   # 迭代序号（影响文件名）
    python3 batch_send_api.py --dry-run                  # 只打印不生成
"""

import argparse
import base64
import json
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
        description="全自动 API 模式 — 直接调用 OpenAI API 生成并下载图片")
    ap.add_argument("range_start", nargs="?", type=int, default=1)
    ap.add_argument("range_end", nargs="?", type=int, default=None)
    ap.add_argument("--start", type=int)
    ap.add_argument("--filter", type=str)
    ap.add_argument("--prompts-file", type=Path, default=find_prompts_file())
    ap.add_argument("--model", type=str, default="gpt-image-1",
                    help="图片生成模型：gpt-image-1 / dall-e-3")
    ap.add_argument("--size", type=str, default=None,
                    help="图片尺寸，如 1536x1024、1024x1792、1024x1024")
    ap.add_argument("--quality", type=str, default=None,
                    help="图片质量：standard / hd（仅 dall-e-3）")
    ap.add_argument("--output", type=Path,
                    default=Path.cwd() / "generated",
                    help="图片输出目录")
    ap.add_argument("--delay", type=int, default=5,
                    help="每条之间的间隔秒数（避免触发速率限制）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--iter", type=int, default=None,
                    help="迭代序号，影响输出文件名（如 card_3_1_iter_002.png）")
    args = ap.parse_args()

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ 需要 openai：pip3 install openai")
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

    # 确定默认尺寸
    if args.size is None:
        if args.model == "dall-e-3":
            size = "1792x1024"  # ~16:9
        else:
            size = "1536x1024"  # ~3:2 (gpt-image-1)
    else:
        size = args.size

    print(f"🔌 OpenAI API 模式 · {args.model} · {size}")
    print(f"📁 输出到：{output_dir.resolve()}")
    print(f"📋 共 {len(sub)} 条 · 间隔 {args.delay} 秒\n")

    client = OpenAI()

    success = 0
    failed = 0

    for idx, p in enumerate(sub, start=start + 1):
        card_label = (f"第 {p['chapter_no']:02d} 章 · "
                      f"卡片 {p['card_no']} · {p['card_title']}")
        print(f"[{idx}/{start + len(sub)}] {card_label}")

        if args.dry_run:
            print(f"   🧪 DRY RUN — 跳过生成\n")
            continue

        card_slug = p['card_no'].replace('.', '_')
        iter_tag = f"_iter_{args.iter:03d}" if args.iter else ""
        filename = f"card_{card_slug}{iter_tag}.png"
        filepath = output_dir / filename

        # 如果已存在则跳过
        if filepath.exists():
            print(f"   ⏩ 已存在，跳过：{filename}\n")
            success += 1
            continue

        try:
            print(f"   ⏳ 生成中…", end="", flush=True)

            kwargs = {
                "model": args.model,
                "prompt": p["prompt"],
                "n": 1,
                "size": size,
            }
            if args.quality and args.model == "dall-e-3":
                kwargs["quality"] = args.quality

            response = client.images.generate(**kwargs)

            # 下载图片
            img_data = response.data[0]

            if hasattr(img_data, "b64_json") and img_data.b64_json:
                img_bytes = base64.b64decode(img_data.b64_json)
            elif hasattr(img_data, "url") and img_data.url:
                import urllib.request
                img_bytes = urllib.request.urlopen(img_data.url).read()
            else:
                print(f" ❌ 无法获取图片数据")
                failed += 1
                continue

            filepath.write_bytes(img_bytes)
            print(f" ✅ {filename} ({len(img_bytes) // 1024}KB)")
            success += 1

        except Exception as e:
            print(f" ❌ 失败：{e}")
            failed += 1
            # 如果是速率限制，等待更长时间
            if "rate" in str(e).lower():
                print("   ⏳ 触发速率限制，等待 60 秒…")
                time.sleep(60)
            continue

        # 间隔
        if idx < start + len(sub):
            time.sleep(args.delay)

    print(f"\n🎉 完成！成功 {success} 张，失败 {failed} 张")
    print(f"📁 图片保存在：{output_dir.resolve()}")

    if failed > 0:
        print(f"💡 失败的卡片可以重新运行："
              f"python3 batch_send_api.py --start {start + 1}")


if __name__ == "__main__":
    main()
