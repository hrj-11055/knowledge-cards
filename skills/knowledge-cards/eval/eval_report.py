"""
eval_report.py · 评估报告生成器

读取提示词评估和图片评估的 JSON 结果，生成可读的 Markdown 报告。

用法：
    python3 eval_report.py --subject 中考数学 --iter 1
    python3 eval_report.py --subject 中考数学 --iter 1 --compare 2
"""

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent


def generate_report(subject: str, iteration: int, compare_iter: int = None):
    search_dirs = [
        EVAL_DIR / ".." / "eval_data" / subject,
        Path.cwd() / "eval_data" / subject,
        EVAL_DIR / ".." / ".." / "eval_data" / subject,
    ]
    # Also check relative to the prompts file location
    for p in Path.cwd().rglob("eval_data"):
        candidate = p / subject
        if candidate.exists():
            search_dirs.insert(0, candidate)

    eval_data_dir = None
    for d in search_dirs:
        if d.exists():
            eval_data_dir = d
            break
    if not eval_data_dir.exists():
        print(f"❌ 找不到评估数据目录: eval_data/{subject}")
        sys.exit(1)

    prompt_file = eval_data_dir / f"prompt_eval_iter_{iteration:03d}.json"
    image_file = eval_data_dir / f"image_eval_iter_{iteration:03d}.json"

    prompt_eval = None
    image_eval = None

    if prompt_file.exists():
        prompt_eval = json.loads(prompt_file.read_text(encoding="utf-8"))
    if image_file.exists():
        image_eval = json.loads(image_file.read_text(encoding="utf-8"))

    if not prompt_eval and not image_eval:
        print(f"❌ 没有找到第 {iteration} 次迭代的评估数据")
        sys.exit(1)

    # 生成报告
    lines = []
    lines.append(f"# {subject} · 第 {iteration} 次迭代评估报告\n")

    # 总体成绩
    lines.append("## 总体成绩\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")

    if prompt_eval:
        s = prompt_eval["summary"]
        lines.append(f"| 提示词平均分 | {s['avg_score']}/10 |")
        lines.append(f"| 提示词通过率 | {s['pass_count']}/{s['total_cards']} "
                     f"({s['pass_count']/s['total_cards']*100:.0f}%) |")
    if image_eval:
        s = image_eval["summary"]
        lines.append(f"| 图片平均分 | {s['avg_score']}/10 |")
        lines.append(f"| 图片通过率 | {s['pass_count']}/{s['evaluated_cards']} "
                     f"({s['pass_count']/s['evaluated_cards']*100:.0f}%) |")

    # 各维度平均分
    lines.append("\n## 各维度平均分\n")
    lines.append("| 维度 | 分数 |")
    lines.append("|------|------|")

    if prompt_eval:
        for dim, avg in prompt_eval["summary"]["dimension_averages"].items():
            marker = " ★" if avg < 6 else ""
            lines.append(f"| {dim} | {avg}{marker} |")
    if image_eval:
        for dim, avg in image_eval["summary"]["dimension_averages"].items():
            marker = " ★" if avg < 6 else ""
            lines.append(f"| {dim} | {avg}{marker} |")

    lines.append("\n★ = 主要失分维度\n")

    # 卡片得分排名
    lines.append("## 卡片得分排名（从低到高）\n")

    all_cards = {}
    if prompt_eval:
        for c in prompt_eval["cards"]:
            all_cards.setdefault(c["card_no"], {})["card_title"] = c["card_title"]
            all_cards[c["card_no"]]["prompt_score"] = c["overall_score"]
            all_cards[c["card_no"]]["prompt_passed"] = c["passed"]
    if image_eval:
        for c in image_eval["cards"]:
            all_cards.setdefault(c["card_no"], {})["card_title"] = c.get("card_title", "")
            all_cards[c["card_no"]]["image_score"] = c.get("overall_score", 0)
            all_cards[c["card_no"]]["image_passed"] = c.get("passed", False)

    # 按最低分排序
    def min_score(card_data):
        scores = [card_data.get("prompt_score", 10), card_data.get("image_score", 10)]
        return min(s for s in scores if s is not None)

    sorted_cards = sorted(all_cards.items(), key=lambda x: min_score(x[1]))

    lines.append("| 排名 | 卡片 | 提示词 | 图片 | 通过？|")
    lines.append("|------|------|--------|------|-------|")

    for rank, (card_no, data) in enumerate(sorted_cards, 1):
        ps = data.get("prompt_score", "—")
        ims = data.get("image_score", "—")
        pp = data.get("prompt_passed", None)
        ip = data.get("image_passed", None)
        passed = "✓" if (pp is not False and ip is not False) else "✗"
        if isinstance(ps, float):
            ps = f"{ps:.1f}"
        if isinstance(ims, float):
            ims = f"{ims:.1f}"
        lines.append(f"| {rank} | {card_no} {data.get('card_title', '')} | "
                     f"{ps} | {ims} | {passed} |")

    # 常见问题
    if image_eval and image_eval["summary"].get("top_issues"):
        lines.append("\n## 常见失败模式\n")
        lines.append("| 失败类型 | 出现次数 |")
        lines.append("|----------|----------|")
        for issue in image_eval["summary"]["top_issues"]:
            lines.append(f"| {issue['type']} | {issue['frequency']} |")

    # 逐卡详情
    if prompt_eval:
        failed = [c for c in prompt_eval["cards"] if not c["passed"]]
        if failed:
            lines.append("\n## 未通过卡片详情\n")
            for c in failed:
                lines.append(f"### 卡片 {c['card_no']} · {c['card_title']} "
                             f"({c['overall_score']}/10)\n")
                for issue in c.get("issues", []):
                    lines.append(f"- **[{issue['severity']}]** {issue['message']}")
                for sug in c.get("suggestions", []):
                    lines.append(f"- 💡 {sug}")
                lines.append("")

    # 迭代对比
    if compare_iter:
        compare_prompt_file = eval_data_dir / f"prompt_eval_iter_{compare_iter:03d}.json"
        compare_image_file = eval_data_dir / f"image_eval_iter_{compare_iter:03d}.json"

        if compare_prompt_file.exists() or compare_image_file.exists():
            lines.append(f"\n## 与第 {compare_iter} 次迭代对比\n")
            lines.append("| 指标 | 第 {0} 次 | 第 {1} 次 | 变化 |".format(
                compare_iter, iteration))
            lines.append("|------|---------|---------|------|")

            if compare_prompt_file.exists() and prompt_eval:
                cp = json.loads(compare_prompt_file.read_text(encoding="utf-8"))
                old_avg = cp["summary"]["avg_score"]
                new_avg = prompt_eval["summary"]["avg_score"]
                delta = new_avg - old_avg
                lines.append(f"| 提示词平均分 | {old_avg} | {new_avg} | "
                             f"{'+' if delta >= 0 else ''}{delta:.1f} |")

                old_pass = cp["summary"]["pass_count"] / cp["summary"]["total_cards"]
                new_pass = prompt_eval["summary"]["pass_count"] / prompt_eval["summary"]["total_cards"]
                delta_p = new_pass - old_pass
                lines.append(f"| 通过率 | {old_pass*100:.0f}% | {new_pass*100:.0f}% | "
                             f"{'+' if delta_p >= 0 else ''}{delta_p*100:.0f}% |")

    # 写入文件
    report_dir = eval_data_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"iter_{iteration:03d}_report.md"
    report_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n📋 报告已生成：{report_file}")
    return report_file


def main():
    ap = argparse.ArgumentParser(description="生成评估报告")
    ap.add_argument("--subject", type=str, required=True, help="学科名称")
    ap.add_argument("--iter", type=int, required=True, help="迭代序号")
    ap.add_argument("--compare", type=int, default=None,
                    help="与另一次迭代对比")
    args = ap.parse_args()

    generate_report(args.subject, args.iter, args.compare)


if __name__ == "__main__":
    main()
