# Knowledge Cards Skill

A reusable workflow for making educational image cards from checked content. It prepares image prompts and requires review of the resulting image before distribution.

## Install

Clone this repository and copy the skill folder into your agent's skill directory:

```bash
git clone https://github.com/hrj-11055/knowledge-cards.git
mkdir -p ~/.codex/skills
cp -R knowledge-cards/skills/knowledge-cards ~/.codex/skills/
```

For Claude Code, use `~/.claude/skills/` instead. Open a new session and ask for a study card based on your notes. You can also read `SKILL.md` directly without an agent.

## Local demo

```bash
python3 skills/knowledge-cards/scripts/extract_prompts.py examples/algebra-cards.md /tmp/knowledge-card-prompts.json
```

The command extracts one prompt as JSON. It does not call an image API or verify generated pixels. Use the example prompt in an image tool, then complete the [review checklist](skills/knowledge-cards/references/review-checklist.md). The example formula is checked by expansion and numeric substitution; no generated image is presented as approved.

## What is verified

| Stage | Status |
| --- | --- |
| Markdown to JSON prompt extraction | Locally demonstrated with the example |
| Prompt template and source ledger workflow | Documented; human applies it to each new topic |
| ChatGPT image generation | Used in the source project, but no reusable end-to-end automated run is established here |
| Desktop, browser, or paid API batch sending | Experimental ideas and prior scripts; excluded from this release |
| Automated image scoring and repair | Experimental prior code; excluded because it cannot certify factual or visual correctness |
| Published image sample | None; a prompt alone is not an approved card |

## Provenance and rights

This release adapts the owner's local knowledge-card methodology and a separate teaching note about review cards. The owner account and existing repository history identify the author as MarkHuang. The educational prompt example and text in this release were written for this package. Original textbook PDFs, subject prompt collections, generated image experiments, and private paths are excluded. Sources supplied by users remain subject to their own rights; do not put copyrighted pages or private material in a public repository without permission.

One inspected physics overview image from the source project contained formulas without sufficient conditions and ambiguous symbols, so it is not included as a passing example. Formula and diagram review is a release gate for every generated card.

## License

MIT for this repository's original code and documentation. This license does not grant rights to third-party source material supplied for future cards.
