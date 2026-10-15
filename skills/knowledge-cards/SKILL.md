---
name: knowledge-cards
description: Turn user-uploaded electronic lesson plans, textbooks, notes, or openly reusable facts into image-ready study-card prompts, then review generated cards before release. Use for educational knowledge-card creation; do not treat image text as verified merely because a prompt was checked.
---

# Knowledge cards

Make one teachable idea per card. The human is the editor; an image model can help with illustration and layout.

## Uploaded teaching materials

Accept an electronic lesson plan or textbook as source material, including readable PDF, DOCX, Markdown, text, and page images when the current environment can extract them. First inspect the file type and whether its text can be read. For scanned pages, use available OCR or visual reading and compare uncertain passages with the page image. Preserve page or section references. If pages, formulas, tables, diagrams, or handwriting cannot be read reliably, identify those gaps and request a clearer file or page rather than inventing content. A large book may require chapter-by-chapter processing and coverage checks against its table of contents. Read [material intake](references/material-intake.md) for the intake record.

Uploaded material may be used to make a private, original summary for the user's study. Do not copy long passages or reproduce textbook figures in public cards or repositories without reuse rights. Do not upload the source file to a public repository by default.

1. Establish audience, topic, card count, format, and the source of each factual claim. Use the uploaded lesson plan or textbook when provided; otherwise prefer the user's own notes or openly licensed sources. Record source title, author or organization, URL or local reference, and the exact section/page. If a claim has no reliable source, mark it for research instead of presenting it as a fact.
2. Draft a short content ledger: card ID, one learning objective, exact text to appear, source for each fact, and any formula or diagram checks. Keep the source ledger separate from the image prompt. Ask the user only for a decision that blocks the work; otherwise proceed with a sensible format.
3. Check content before rendering. Recalculate examples and formulas independently, including assumptions and units. Check names, dates, terminology, and scope against the cited source. For diagrams, confirm arrows, labels, geometry, and quantities. Do not infer correctness from an AI evaluator score.
4. Create one self-contained prompt per card with exact title and body text, image size/aspect preference, layout, palette, and visual instructions. State which text must appear verbatim. Reduce text if it is crowded; a concise card is easier to inspect. See [prompt template](references/prompt-template.md).
5. Generate a small sample in the image tool available to the user. Save each output with its prompt and source ledger. Image-generation method, cost, and quota vary by environment; obtain authorization before paid or large batches.
6. Inspect the actual image at readable size. Compare every visible character, formula, symbol, and diagram to the ledger. Check crop, contrast, and legibility on the target display. Mark each card `approved`, `needs_fix`, or `rejected`; regenerate or correct errors and inspect again. Publish or distribute only approved cards.

For a set, keep a manifest with card ID, prompt path, image path, source, review status, reviewer, and review date. A prompt pass is not an image pass. Automation can prepare prompts and track status; it cannot replace content and visual review. Use `scripts/extract_prompts.py` only for the documented Markdown format. It performs parsing, not image generation or fact checking.

See [review checklist](references/review-checklist.md) when approving images and [example](../../examples/) for a self-authored mathematical card.
