---
doc: prd
status: approved
---
# Honest Copy — Product Requirements
An explainable copy check for small online sellers. Source: `scope.md > The Unique Kernel`.

## The Core Journey
1. Open a single workspace; see a short explanation and clearly labeled template/demo mode.
2. Paste up to 5,000 characters, or load a fictional English/Korean example, then select Check copy.
3. Read original copy with inline color highlights and numbered issue cards. Each card shows the matched phrase, risk type, plain explanation and proposed replacement.
4. Apply one suggestion or all template suggestions. See the revised draft, remaining issues and before/after rule-risk scores.
5. Copy the revised text, undo a change or edit and check another draft.
Source: `scope.md > The Core Loop` and `What "Working" Looks Like`.

## Screens and Layout
Agent assumption: one responsive page. Compact brand header and mode pill; editorial intro; input workspace left, score and explanations right. Revised-copy panel appears below input after a change. Stack panels on narrow screens. No new route or onboarding.

## Look and Feel
Agent assumption under delegated design judgment: warm off-white canvas, charcoal text, forest-green primary action, serif display headline with readable system sans body. Clear numbered cards. Pink medical, amber guarantee, violet superlative and blue evidence highlights; text labels also identify every category. Respect reduced motion. Native keyboard controls and visible focus.

## Features and Behavior
### Paste and Check
Labeled textarea, character count, explicit check action, English and Korean fictional samples. Check disabled for whitespace; over-limit text displays an error and cannot run. Input edits invalidate stale results and pending AI suggestions. Render all user/provider text as text, never executable HTML.
### Phrase Review
Detect deterministic patterns in both languages across the four requested categories. Highlight exact source spans, including repeated phrases, with non-overlapping matches. Each explanation states why the claim may need review without asserting illegality. No hits means “No listed patterns found,” with coverage limits.
### Rewrite and Compare
Each Apply suggestion replaces its exact matched occurrence. Apply all uses templates, shows preview and recomputes the score. Undo restores the preceding draft. Original baseline remains fixed until a new check. Score is a 0–100 weighted rule-risk indicator (lower is better), never legal safety, approval probability or factual verification. Copy reports success/failure visibly.
### Optional AI Wording
When server-side key exists, mode switches automatically. Explicit AI button sends the selected phrase and surrounding draft to the configured provider. Explain this before sending. Validate response shape and reject newly detected risky phrases; errors clearly fall back to the template. Without a key all core behavior works via templates, labeled honestly. Do not invent evidence.

## States and Boundaries
Empty: helpful start prompt. Checked: matched spans and cards. No hits: honest coverage message. Revised: before/after scores and copyable text. API pending: local suggestion still available; disable duplicate requests. API failure: visible template fallback. Changing drafts discards stale API responses. Reload clears text; no storage, analytics or database.

## Product Decisions
User choices: English UI; English/Korean copy; deterministic rules first; optional compatible LLM; tiny Vite web app; no accounts/database/payments/scraping. Agent assumptions: exact layout/palette, 5,000-character limit, weighted score and undo to make the specified loop understandable.

## What We're Building
The complete single-page journey above; tests, CI, public planning artifacts, app map, README, license, deployment and real-screen capture per the brief.

## Deferred From the POC
Jurisdiction-specific legal research and merchant evidence verification require domain review; not needed to prove wording assistance.

## Possible Later Enhancements
Seller feedback could guide additional reviewed rules and evidence fields.

## Non-Goals
No compliance certification, automatic listing submission, medical advice, invented studies, accounts or scraped listings.

## Open Questions
No product-defining blocker. Human hands-on review and learning reflection remain unperformed; agent browser checks will not be presented as human review. Planning approval follows explicit delegated task authorization.
