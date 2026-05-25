"""
eval_image.py · 知识卡片图片质量评估（Claude Vision）

用 Claude Vision API 评估生成的知识卡片图片质量（7 个维度）。

用法：
    python3 eval_image.py generated/数学/ --prompts-file prompts_数学.json
    python3 eval_image.py generated/数学/ --iter 1
    python3 eval_image.py generated/数学/ --subject 中考数学
"""

import argparse
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

EVAL_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = EVAL_DIR / "templates" / "eval_image_template.md"
CONFIG_FILE = EVAL_DIR / "eval_config.json"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_template():
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def encode_image(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def find_images(image_dir: Path, iteration: int = None) -> list[Path]:
    """查找图片文件，支持迭代命名"""
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
    images = []
    for p in patterns:
        images.extend(image_dir.glob(p))
    if iteration is not None:
        iter_tag = f"iter_{iteration:03d}"
        images = [i for i in images if iter_tag in i.name or "iter_" not in i.name]
    return sorted(images)


def evaluate_image(client, image_path: Path, prompt_text: str,
                   card_no: str, card_title: str, system_prompt: str,
                   model: str) -> dict:
    """用 Claude Vision 评估单张图片"""
    img_b64 = encode_image(image_path)

    user_message = f"""请评估这张知识卡片图片。

卡片编号：{card_no}
卡片标题：{card_title}

这是用于生成该图片的提示词：
---
{prompt_text}
---

请严格按照评分标准评估，返回 JSON。"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    }},
                    {"type": "text", "text": user_message},
                ],
            }],
        )
        text = response.content[0].text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  ⚠️  评估失败: {e}")
    return None


def main():
    ap = argparse.ArgumentParser(description="评估知识卡片图片质量")
    ap.add_argument("image_dir", type=Path, help="图片目录")
    ap.add_argument("--prompts-file", type=Path, required=True,
                    help="提示词 JSON 文件")
    ap.add_argument("--iter", type=int, default=1, help="迭代序号")
    ap.add_argument("--subject", type=str, default="", help="学科名称")
    ap.add_argument("--sample", type=int, default=None,
                    help="只评估前 N 张（调试用）")
    args = ap.parse_args()

    try:
        import anthropic
    except ImportError:
        print("❌ 需要 anthropic 库：pip install anthropic")
        sys.exit(1)

    if not args.image_dir.exists():
        print(f"❌ 找不到图片目录: {args.image_dir}")
        sys.exit(1)
    if not args.prompts_file.exists():
        print(f"❌ 找不到提示词文件: {args.prompts_file}")
        sys.exit(1)

    config = load_config()
    system_prompt = load_template()
    model = config["image_eval"]["model"]
    pass_threshold = config["scoring"]["pass_threshold"]

    client = anthropic.Anthropic()
    prompts = json.loads(args.prompts_file.read_text(encoding="utf-8"))
    prompts_map = {p["card_no"]: p for p in prompts}

    subject = args.subject or args.prompts_file.stem.replace("prompts_", "")
    images = find_images(args.image_dir, args.iter)

    if args.sample:
        images = images[:args.sample]

    if not images:
        print(f"❌ 在 {args.image_dir} 中未找到图片")
        sys.exit(1)

    output_dir = args.prompts_file.parent / "eval_data" / subject
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🖼️  评估图片 · {subject} · 第 {args.iter} 次迭代 · {len(images)} 张\n")

    cards_results = []

    for img_path in images:
        # 从文件名推断 card_no
        name = img_path.stem
        card_no_match = re.search(r"card_(\d+_\d+)", name)
        if not card_no_match:
            print(f"  ⏭️  跳过（无法解析卡片号）: {img_path.name}")
            continue

        card_no = card_no_match.group(1).replace("_", ".")
        prompt_data = prompts_map.get(card_no)

        if not prompt_data:
            print(f"  ⏭️  跳过（找不到提示词）: card {card_no}")
            continue

        print(f"  📸 [{card_no}] {prompt_data['card_title']}...", end="", flush=True)

        result = evaluate_image(
            client, img_path, prompt_data["prompt"],
            card_no, prompt_data["card_title"],
            system_prompt, model,
        )

        if result:
            overall = result.get("overall_score", 0)
            passed = result.get("passed", overall >= pass_threshold)
            result["image_path"] = str(img_path)
            result["iteration"] = args.iter
            cards_results.append(result)
            status = "✅" if passed else "❌"
            print(f" {status} {overall}/10")
        else:
            print(" ⚠️ 评估失败")

    if not cards_results:
        print("\n❌ 没有成功评估的图片")
        sys.exit(1)

    # 汇总
    passed_count = sum(1 for c in cards_results if c.get("passed", False))
    avg_score = sum(c.get("overall_score", 0) for c in cards_results) / len(cards_results)

    dim_avgs = {}
    for dim in config["image_eval"]["dimensions"]:
        scores = [c.get("dimensions", {}).get(dim, {}).get("score", 0)
                  for c in cards_results]
        if scores:
            dim_avgs[dim] = round(sum(scores) / len(scores), 1)

    top_issues = {}
    for c in cards_results:
        for err in c.get("specific_errors", []):
            t = err.get("type", "other")
            top_issues[t] = top_issues.get(t, 0) + 1

    result_data = {
        "version": "1.0",
        "subject": subject,
        "iteration": args.iter,
        "timestamp": datetime.now().isoformat(),
        "evaluator": model,
        "summary": {
            "total_cards": len(cards_results),
            "evaluated_cards": len(cards_results),
            "avg_score": round(avg_score, 1),
            "pass_count": passed_count,
            "fail_count": len(cards_results) - passed_count,
            "dimension_averages": dim_avgs,
            "top_issues": [
                {"type": t, "frequency": f}
                for t, f in sorted(top_issues.items(), key=lambda x: -x[1])
            ],
        },
        "cards": cards_results,
    }

    outfile = output_dir / f"image_eval_iter_{args.iter:03d}.json"
    outfile.write_text(json.dumps(result_data, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    print(f"\n📊 汇总：平均 {avg_score:.1f}/10 · 通过 {passed_count}/{len(cards_results)}")
    print(f"📦 已写入：{outfile}")


if __name__ == "__main__":
    main()
