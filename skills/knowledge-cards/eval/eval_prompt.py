"""
eval_prompt.py · 提示词质量评估脚本

评估提示词的 8 个维度：
  - 本地计算（6 维度，零成本）：module_completeness, hex_color, text_density,
    layout_variety, self_containedness, chinese_accuracy
  - Claude API（2 维度）：visual_specificity, source_grounding

用法：
    python3 eval_prompt.py prompts.json
    python3 eval_prompt.py prompts.json --iter 1
    python3 eval_prompt.py prompts.json --local-only   # 只跑本地维度
    python3 eval_prompt.py prompts.json --subject 中考数学
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

EVAL_DIR = Path(__file__).resolve().parent
RUBRIC_FILE = EVAL_DIR / "rubrics" / "prompt_rubric.json"
CONFIG_FILE = EVAL_DIR / "eval_config.json"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_rubric():
    return json.loads(RUBRIC_FILE.read_text(encoding="utf-8"))


# ── 本地评估函数 ──────────────────────────────────────────

def eval_module_completeness(prompt: str) -> dict:
    modules = {
        "style": bool(re.search(r"(插画|手绘|极简|扁平|卡通|水墨|科技|风格)", prompt)),
        "title": bool(re.search(r"【主标题】|主标题", prompt)),
        "text": bool(re.search(r"【卡片.*文字.*内容】|卡片.*文字", prompt, re.DOTALL)),
        "visual": bool(re.search(r"【视觉元素】|视觉元素", prompt)),
        "color": bool(re.search(r"【配色】|配色", prompt)),
    }
    count = sum(modules.values())
    score = {5: 10, 4: 8, 3: 6, 2: 4}.get(count, 0)
    missing = [k for k, v in modules.items() if not v]
    notes = f"{count}/5 模块存在"
    if missing:
        notes += f"，缺失: {', '.join(missing)}"
    return {"score": score, "max": 10, "notes": notes}


def eval_hex_color(prompt: str) -> dict:
    hex_colors = re.findall(r"#[0-9A-Fa-f]{6}\b", prompt)
    named_colors = re.findall(
        r"(?:底色|主色|辅色|文字)[^#\n]*(?!#)[一-鿿]+(?:色|蓝|红|绿|橙|粉|灰|白|黑|黄|紫|棕)",
        prompt,
    )
    total = len(hex_colors) + len(named_colors)
    if total == 0:
        return {"score": 0, "max": 10, "notes": "未指定颜色"}
    ratio = len(hex_colors) / total
    if ratio >= 0.9:
        score = 10
    elif ratio >= 0.6:
        score = 7
    elif ratio >= 0.3:
        score = 4
    else:
        score = 3
    return {
        "score": score,
        "max": 10,
        "notes": f"{len(hex_colors)} 个 HEX 色值，{len(named_colors)} 个命名色",
    }


def eval_text_density(prompt: str) -> dict:
    text_match = re.search(
        r"【卡片.*?内容.*?】\s*\n(.*?)(?=【视觉元素】|【配色】|要求：)",
        prompt,
        re.DOTALL,
    )
    if not text_match:
        return {"score": 0, "max": 10, "notes": "未找到文字内容区块"}
    text = text_match.group(1).strip()
    char_count = len(re.sub(r"\s+", "", text))
    if 250 <= char_count <= 350:
        score = 10
    elif 200 <= char_count <= 400:
        score = 8
    elif 150 <= char_count <= 450:
        score = 5
    elif char_count > 0:
        score = 3
    else:
        score = 0
    return {"score": score, "max": 10, "notes": f"约 {char_count} 字"}


def eval_layout_variety(prompt: str, prev_prompt: Optional[str]) -> dict:
    layout_keywords = {
        "左文右图": r"左.*文.*右.*图|左.*文字.*右.*插画",
        "时间轴": r"时间轴|时间线|timeline",
        "网格": r"网格|田字格|九宫格|grid",
        "流程图": r"流程图|流程|箭头|flowchart",
        "环形": r"环形|辐射|层级|radial",
        "公式居中": r"公式.*居中",
        "上图下文": r"上图.*下文|上方.*插画.*下方.*文字",
    }
    detected = None
    for layout, pattern in layout_keywords.items():
        if re.search(pattern, prompt):
            detected = layout
            break

    if detected is None:
        return {"score": 0, "max": 10, "notes": "未指定版式"}

    if prev_prompt is None:
        return {"score": 10, "max": 10, "notes": f"版式: {detected}（首张卡片）"}

    prev_detected = None
    for layout, pattern in layout_keywords.items():
        if re.search(pattern, prev_prompt):
            prev_detected = layout
            break

    if prev_detected is None or detected != prev_detected:
        return {"score": 10, "max": 10, "notes": f"版式: {detected}（与上一张不同）"}
    return {"score": 4, "max": 10, "notes": f"版式: {detected}（与上一张相同）"}


def eval_self_containedness(prompt: str) -> dict:
    has_style = bool(re.search(r"(插画|手绘|极简|扁平|卡通|水墨|科技).{0,10}风", prompt))
    has_ratio = bool(re.search(r"\d+:\d+|横版|竖版", prompt))
    has_colors = bool(re.search(r"#", prompt))
    has_layout = bool(re.search(r"左文右图|时间轴|网格|流程图|环形|公式居中|上图下文", prompt))

    count = sum([has_style, has_ratio, has_colors, has_layout])
    if count >= 4:
        score = 10
    elif count >= 3:
        score = 7
    elif count >= 2:
        score = 4
    else:
        score = 0
    details = []
    if not has_style:
        details.append("缺少风格")
    if not has_ratio:
        details.append("缺少比例")
    if not has_colors:
        details.append("缺少配色")
    if not has_layout:
        details.append("缺少版式")
    notes = f"包含 {count}/4 项自包含信息"
    if details:
        notes += f"，缺失: {', '.join(details)}"
    return {"score": score, "max": 10, "notes": notes}


def eval_chinese_accuracy(prompt: str) -> dict:
    config = load_config()
    keywords = config["prompt_eval"]["chinese_accuracy_keywords"]
    matches = sum(1 for kw in keywords if kw in prompt)
    if matches >= 2:
        score = 10
    elif matches >= 1:
        score = 7
    elif "中文" in prompt:
        score = 4
    else:
        score = 0
    return {
        "score": score,
        "max": 10,
        "notes": f"匹配到 {matches} 个中文准确性关键词",
    }


# ── LLM 评估 ─────────────────────────────────────────────

def eval_with_llm(prompts_data: list[dict], iteration: int, subject: str):
    """用 Claude API 评估 visual_specificity 和 source_grounding"""
    try:
        import anthropic
    except ImportError:
        print("⚠️  需要 anthropic 库：pip install anthropic")
        return None

    client = anthropic.Anthropic()
    results = {}

    for p in prompts_data:
        card_id = p["card_no"]
        prompt_text = p["prompt"]

        eval_prompt = f"""评估以下知识卡片提示词的两个维度，返回 JSON：

1. visual_description_specificity（0-10）：
   10=具体到物体位置比例构图，7=大部分具体少量模糊，4=主要是模糊描述，0=缺失
2. source_grounding（0-10）：
   10=所有事实有来源标注，7=大部分有，4=无标注但内容合理，0=无标注无法验证

提示词：
{prompt_text}

只返回 JSON，格式：
{{"visual_description_specificity": {{"score": N, "notes": "..."}}, "source_grounding": {{"score": N, "notes": "..."}}}}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": eval_prompt}],
            )
            text = response.content[0].text
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                results[card_id] = json.loads(json_match.group())
        except Exception as e:
            print(f"  ⚠️  卡片 {card_id} LLM 评估失败: {e}")
            results[card_id] = {
                "visual_description_specificity": {"score": 5, "notes": "LLM 评估失败，给中间分"},
                "source_grounding": {"score": 5, "notes": "LLM 评估失败，给中间分"},
            }

    return results


# ── 主评估流程 ────────────────────────────────────────────

def evaluate_prompts(prompts_file: Path, iteration: int = 1,
                     subject: str = "", local_only: bool = False):
    config = load_config()
    rubric = load_rubric()

    prompts = json.loads(prompts_file.read_text(encoding="utf-8"))
    if not subject:
        subject = prompts_file.stem.replace("prompts_", "").replace("prompts", "").strip("_") or "unknown"

    output_dir = prompts_file.parent / "eval_data" / subject
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📊 评估提示词 · {subject} · 第 {iteration} 次迭代 · {len(prompts)} 张卡片\n")

    cards_results = []
    pass_threshold = config["scoring"]["pass_threshold"]

    prev_prompt_by_chapter = {}

    for p in prompts:
        card_id = p["card_no"]
        chapter = p["chapter_no"]
        prev = prev_prompt_by_chapter.get(chapter)

        dims = {
            "module_completeness": eval_module_completeness(p["prompt"]),
            "hex_color_specificity": eval_hex_color(p["prompt"]),
            "text_density": eval_text_density(p["prompt"]),
            "layout_variety": eval_layout_variety(p["prompt"], prev),
            "self_containedness": eval_self_containedness(p["prompt"]),
            "chinese_accuracy_emphasis": eval_chinese_accuracy(p["prompt"]),
        }

        # 占位 LLM 维度
        dims["visual_description_specificity"] = {"score": 7, "max": 10, "notes": "待 LLM 评估"}
        dims["source_grounding"] = {"score": 7, "max": 10, "notes": "待 LLM 评估"}

        local_scores = [d["score"] for d in dims.values()]
        local_avg = sum(local_scores) / len(local_scores)

        card_result = {
            "card_no": card_id,
            "card_title": p["card_title"],
            "chapter_no": chapter,
            "chapter_title": p["chapter_title"],
            "overall_score": round(local_avg, 1),
            "passed": local_avg >= pass_threshold,
            "dimensions": dims,
            "issues": [],
            "suggestions": [],
        }

        # 收集问题
        for dim_name, dim_data in dims.items():
            if dim_data["score"] < 5:
                card_result["issues"].append({
                    "severity": "critical",
                    "dimension": dim_name,
                    "message": f"{dim_name}: {dim_data['score']}/10 — {dim_data['notes']}",
                })

        cards_results.append(card_result)
        prev_prompt_by_chapter[chapter] = p["prompt"]

        status = "✅" if card_result["passed"] else "❌"
        print(f"  {status} [{card_id}] {p['card_title']:<20} {local_avg:.1f}/10")

    # LLM 评估
    if not local_only:
        print(f"\n🤖 运行 LLM 评估（visual_specificity, source_grounding）...")
        llm_results = eval_with_llm(prompts, iteration, subject)
        if llm_results:
            for card in cards_results:
                llm = llm_results.get(card["card_no"], {})
                for dim in ["visual_description_specificity", "source_grounding"]:
                    if dim in llm:
                        card["dimensions"][dim] = llm[dim]
                scores = [d["score"] for d in card["dimensions"].values()]
                card["overall_score"] = round(sum(scores) / len(scores), 1)
                card["passed"] = card["overall_score"] >= pass_threshold

    # 汇总
    passed_count = sum(1 for c in cards_results if c["passed"])
    avg_score = sum(c["overall_score"] for c in cards_results) / len(cards_results)

    dim_avgs = {}
    for dim in rubric["dimensions"]:
        scores = [c["dimensions"][dim]["score"] for c in cards_results]
        dim_avgs[dim] = round(sum(scores) / len(scores), 1)

    result = {
        "version": "1.0",
        "subject": subject,
        "source_file": str(prompts_file),
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_cards": len(cards_results),
            "avg_score": round(avg_score, 1),
            "pass_count": passed_count,
            "fail_count": len(cards_results) - passed_count,
            "dimension_averages": dim_avgs,
        },
        "cards": cards_results,
    }

    outfile = output_dir / f"prompt_eval_iter_{iteration:03d}.json"
    outfile.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📊 汇总：平均 {avg_score:.1f}/10 · 通过 {passed_count}/{len(cards_results)}")
    print(f"📦 已写入：{outfile}")

    return result


def main():
    ap = argparse.ArgumentParser(description="评估知识卡片提示词质量")
    ap.add_argument("prompts_file", type=Path, help="提示词 JSON 文件")
    ap.add_argument("--iter", type=int, default=1, help="迭代序号")
    ap.add_argument("--subject", type=str, default="", help="学科名称")
    ap.add_argument("--local-only", action="store_true", help="只跑本地维度（不调用 API）")
    args = ap.parse_args()

    if not args.prompts_file.exists():
        print(f"❌ 找不到 {args.prompts_file}")
        sys.exit(1)

    evaluate_prompts(args.prompts_file, args.iter, args.subject, args.local_only)


if __name__ == "__main__":
    main()
