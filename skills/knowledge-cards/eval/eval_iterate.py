"""
eval_iterate.py · 迭代协调器

读取评估结果，修复提示词，准备下一轮生成。

用法：
    python3 eval_iterate.py --subject 中考数学 --iter 1 --fix-only
    python3 eval_iterate.py --subject 中考数学 --iter 1 --fix-only --cards 3.1,3.2
    python3 eval_iterate.py --subject 中考数学 --iter 1 --full-cycle
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = EVAL_DIR / "templates" / "fix_prompt_template.md"
CONFIG_FILE = EVAL_DIR / "eval_config.json"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_template():
    return TEMPLATE_FILE.read_text(encoding="utf-8")


# ── 规则修复 ──────────────────────────────────────────────

def apply_rule_fixes(prompt: str, dimensions: dict):
    """根据评分规则自动修复提示词，返回（修复后的提示词，修复列表）"""
    fixes = []

    # 中文准确性强化
    chinese_acc = dimensions.get("chinese_text_accuracy", {})
    if isinstance(chinese_acc, dict):
        score = chinese_acc.get("score", 10)
    else:
        score = chinese_acc

    if score < 7:
        chinese_fix = "（所有字符必须与提示词原文完全一致，不得出现任何错别字、乱码、替代字符或省略）"
        if chinese_fix not in prompt:
            prompt = prompt.replace(
                "【卡片需呈现的中文文字内容",
                f"【卡片需呈现的中文文字内容{chinese_fix}",
            )
            if "【卡片需呈现的中文文字内容" not in prompt:
                # 在文字区域开头插入
                prompt = prompt.replace(
                    "【卡片",
                    f"【卡片需呈现的中文文字内容{chinese_fix}\n\n【卡片",
                    1,
                )
            fixes.append("追加中文准确性强化（文字区块标题）")

        end_fix = "\n所有中文文字必须清晰准确，与提示词原文逐字一致，不得替换、省略或乱码。"
        if "与提示词原文逐字一致" not in prompt:
            prompt += end_fix
            fixes.append("追加中文准确性强化（末尾要求）")

    # 内容缺失修复
    completeness = dimensions.get("content_completeness", {})
    if isinstance(completeness, dict):
        comp_score = completeness.get("score", 10)
    else:
        comp_score = completeness

    if comp_score < 7:
        content_fix = "\n注意：以上所有内容必须完整显示在卡片上，不得省略任何一个要点。"
        if "不得省略任何一个要点" not in prompt:
            # 找到文字内容区块末尾插入
            prompt = re.sub(
                r"(【卡片.*?内容.*?】\s*\n.*?)(\n【视觉元素】)",
                r"\1" + content_fix + r"\2",
                prompt,
                count=1,
                flags=re.DOTALL,
            )
            fixes.append("追加内容完整性要求")

    # 可读性修复（公式/下标）
    readability = dimensions.get("readability", {})
    if isinstance(readability, dict):
        read_score = readability.get("score", 10)
    else:
        read_score = readability

    if read_score < 7:
        formula_fix = "公式中的上标、下标、希腊字母（如 Δ）必须清晰可辨，字号不得小于正文的 80%。"
        if "字号不得小于正文" not in prompt:
            prompt = prompt.replace(
                "要求：",
                f"要求：{formula_fix}\n",
            )
            fixes.append("追加公式可读性要求")

    # 颜色强化
    color_acc = dimensions.get("color_accuracy", {})
    if isinstance(color_acc, dict):
        color_score = color_acc.get("score", 10)
    else:
        color_score = color_acc

    if color_score < 7:
        color_fix = "请严格使用以上 HEX 色值，不得使用近似色。"
        if "不得使用近似色" not in prompt:
            prompt = prompt.replace(
                "要求：",
                f"要求：{color_fix}\n",
            )
            fixes.append("追加颜色准确性强化")

    return prompt, fixes


def fix_with_llm(prompt: str, card_no: str, card_title: str,
                 eval_result: dict, system_prompt: str, model: str):
    """用 Claude API 修复提示词"""
    try:
        import anthropic
    except ImportError:
        return prompt, ["LLM 修复失败（缺少 anthropic 库）"]

    client = anthropic.Anthropic()

    dimensions_summary = []
    for dim, data in eval_result.get("dimensions", {}).items():
        if isinstance(data, dict) and data.get("score", 10) < 7:
            dimensions_summary.append(f"- {dim}: {data.get('score', '?')}/10 — {data.get('notes', '')}")

    errors_summary = []
    for err in eval_result.get("specific_errors", []):
        errors_summary.append(f"- [{err.get('severity', '?')}] {err.get('type', '?')}: "
                              f"期望「{err.get('expected', '?')}」实际「{err.get('actual', '?')}」")

    user_msg = f"""请修复以下知识卡片提示词。

卡片编号：{card_no}
卡片标题：{card_title}

失败的维度：
{chr(10).join(dimensions_summary) or '无'}

具体错误：
{chr(10).join(errors_summary) or '无'}

原始提示词：
---
{prompt}
---

请输出修复后的完整提示词。"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text
        code_match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
        if code_match:
            fixed_prompt = code_match.group(1).strip()
            # 提取修复说明
            fix_notes = []
            for line in text.split("\n"):
                if line.strip().startswith("- ") and "修改" in line:
                    fix_notes.append(line.strip())
            return fixed_prompt, fix_notes or ["LLM 修复（详见修复说明）"]
    except Exception as e:
        return prompt, [f"LLM 修复失败: {e}"]

    return prompt, ["LLM 修复未产生有效结果"]


def main():
    ap = argparse.ArgumentParser(description="迭代修复提示词")
    ap.add_argument("--subject", type=str, required=True, help="学科名称")
    ap.add_argument("--iter", type=int, required=True, help="当前迭代序号")
    ap.add_argument("--fix-only", action="store_true",
                    help="只修复提示词，不调用 LLM")
    ap.add_argument("--use-llm", action="store_true",
                    help="对规则修复后仍不通过的卡片调用 Claude 修复")
    ap.add_argument("--cards", type=str, default=None,
                    help="只修复指定卡片（逗号分隔，如 3.1,3.2）")
    args = ap.parse_args()

    config = load_config()
    pass_threshold = config["scoring"]["pass_threshold"]

    # 查找评估数据
    eval_data_dir = Path.cwd() / "eval_data" / args.subject
    if not eval_data_dir.exists():
        eval_data_dir = EVAL_DIR / ".." / "eval_data" / args.subject
    if not eval_data_dir.exists():
        print(f"❌ 找不到评估数据: eval_data/{args.subject}")
        sys.exit(1)

    # 读取图片评估
    image_eval_file = eval_data_dir / f"image_eval_iter_{args.iter:03d}.json"
    prompt_eval_file = eval_data_dir / f"prompt_eval_iter_{args.iter:03d}.json"

    if not image_eval_file.exists() and not prompt_eval_file.exists():
        print(f"❌ 找不到第 {args.iter} 次迭代的评估数据")
        sys.exit(1)

    # 读取原始提示词
    prompts_files = list(Path.cwd().glob("prompts*.json"))
    if not prompts_files:
        prompts_files = list(Path.cwd().glob("*prompts*.json"))
    if not prompts_files:
        print("❌ 找不到 prompts.json 文件")
        sys.exit(1)

    prompts_file = prompts_files[0]
    prompts = json.loads(prompts_file.read_text(encoding="utf-8"))
    prompts_map = {p["card_no"]: p for p in prompts}

    # 收集需要修复的卡片
    failed_cards = set()

    if image_eval_file.exists():
        image_eval = json.loads(image_eval_file.read_text(encoding="utf-8"))
        for c in image_eval["cards"]:
            if not c.get("passed", True):
                failed_cards.add(c["card_no"])

    if prompt_eval_file.exists():
        prompt_eval = json.loads(prompt_eval_file.read_text(encoding="utf-8"))
        for c in prompt_eval["cards"]:
            if not c.get("passed", True):
                failed_cards.add(c["card_no"])

    # 过滤指定卡片
    if args.cards:
        target_cards = set(args.cards.split(","))
        failed_cards = failed_cards & target_cards

    if not failed_cards:
        print("✅ 所有卡片都已通过，无需修复")
        return

    print(f"🔧 修复 {len(failed_cards)} 张不通过的卡片\n")

    # 获取评估详情
    image_eval_map = {}
    if image_eval_file.exists():
        image_eval_data = json.loads(image_eval_file.read_text(encoding="utf-8"))
        for c in image_eval_data["cards"]:
            image_eval_map[c["card_no"]] = c

    prompt_eval_map = {}
    if prompt_eval_file.exists():
        prompt_eval_data = json.loads(prompt_eval_file.read_text(encoding="utf-8"))
        for c in prompt_eval_data["cards"]:
            prompt_eval_map[c["card_no"]] = c

    # 修复
    fixed_prompts = []
    template = load_template() if not args.fix_only else ""
    model = config["image_eval"]["model"]

    for card_no in sorted(failed_cards):
        prompt_data = prompts_map.get(card_no)
        if not prompt_data:
            print(f"  ⚠️  找不到卡片 {card_no} 的提示词")
            continue

        prompt = prompt_data["prompt"]

        # 合并评估维度
        eval_dims = {}
        if card_no in image_eval_map:
            eval_dims = image_eval_map[card_no].get("dimensions", {})

        # Step 1: 规则修复
        fixed_prompt, rule_fixes = apply_rule_fixes(prompt, eval_dims)

        # Step 2: LLM 修复（如果需要）
        llm_fixes = []
        if args.use_llm and card_no in image_eval_map:
            # 检查规则修复后是否仍有可能不通过
            fixed_prompt, llm_fixes = fix_with_llm(
                fixed_prompt, card_no, prompt_data["card_title"],
                image_eval_map[card_no], template, model,
            )

        all_fixes = rule_fixes + llm_fixes

        fixed_entry = dict(prompt_data)
        fixed_entry["prompt"] = fixed_prompt
        fixed_entry["fixes"] = all_fixes
        fixed_prompts.append(fixed_entry)

        print(f"  🔧 [{card_no}] {prompt_data['card_title']}")
        for fix in all_fixes:
            print(f"     - {fix}")

    # 写入修复后的提示词
    next_iter = args.iter + 1
    outfile = Path.cwd() / f"prompts_fixed_iter_{next_iter:03d}.json"
    outfile.write_text(
        json.dumps(fixed_prompts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n📦 修复后的提示词已写入：{outfile}")
    print(f"💡 下一步：python3 batch_send_api.py --prompts-file {outfile.name} --iter {next_iter}")

    # 更新迭代追踪
    iterations_file = eval_data_dir / "iterations.json"
    if iterations_file.exists():
        iterations = json.loads(iterations_file.read_text(encoding="utf-8"))
    else:
        iterations = {
            "version": "1.0",
            "subject": args.subject,
            "created": datetime.now().isoformat(),
            "iterations": [],
            "card_history": {},
        }

    # 添加当前迭代记录
    iter_record = {
        "iteration": args.iter,
        "timestamp": datetime.now().isoformat(),
        "cards_failed": len(failed_cards),
        "cards_fixed": len(fixed_prompts),
        "fixes_applied": [card["fixes"] for card in fixed_prompts],
        "fixed_prompts_file": str(outfile),
    }

    if prompt_eval_file.exists():
        pe = json.loads(prompt_eval_file.read_text(encoding="utf-8"))
        iter_record["prompt_avg"] = pe["summary"]["avg_score"]
    if image_eval_file.exists():
        ie = json.loads(image_eval_file.read_text(encoding="utf-8"))
        iter_record["image_avg"] = ie["summary"]["avg_score"]

    iterations["iterations"].append(iter_record)
    iterations["updated"] = datetime.now().isoformat()

    iterations_file.write_text(
        json.dumps(iterations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"📊 迭代记录已更新：{iterations_file}")


if __name__ == "__main__":
    main()
