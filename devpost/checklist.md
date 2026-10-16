---
doc: checklist
status: approved
---
# Build Checklist
Build mode: fast, per explicit autonomous-task instruction. Approval delegated by task; no interactive learner approval claimed.

## Slices

- [x] **1. Paste copy and understand exact risky phrases**
  Becomes usable: Running English/Korean checker with inline highlights, explanations and initial score.
  Why now: Delivers the unique kernel first, including scaffold and tests.
  PRD ref: `prd.md > Paste and Check`, `prd.md > Phrase Review`
  Spec ref: `spec.md > Rules Engine`, `spec.md > Workspace`
  Build: Add Vite/TS scaffold, bilingual rules, DOM workspace and check results.
  Verify (mechanical): Node rule tests, typecheck/build on pilot, browser sample produces all four categories.
  Learner check: Paste a listing; compare highlighted phrases with explanations. Agent will test this under explicit no-pause override; human check remains pending.
  Commit: `Build bilingual phrase checker and review workspace`

- [x] **2. Apply suggestions and compare the revised draft**
  Becomes usable: Individual/all template rewrites, baseline/current scores, undo and copy.
  Why now: Closes the product loop on the verified detection behavior.
  PRD ref: `prd.md > Rewrite and Compare`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Rules Engine`, `spec.md > Workspace`, `spec.md > Data Model`
  Build: Add exact replacement, recheck, fixed baseline, undo, copy and stale-state resets.
  Verify (mechanical): Rules tests for repeated spans/Unicode/overlaps and score changes; browser single/all/undo/empty/edit/copy/mobile checks on pilot.
  Learner check: Apply one and all suggestions, compare scores, undo and copy. Human feedback remains pending.
  Commit: `Add safer draft comparison undo and copy`

- [x] **3. Optional AI wording, verification and sharing**
  Becomes usable: Automatic key-based mode, honest fallbacks, documented publicly shareable application.
  Why now: AI enriches an already working rules-first loop; no key gates the demo.
  PRD ref: `prd.md > Optional AI Wording`, `prd.md > What We're Building`
  Spec ref: `spec.md > Rewrite Service`, `spec.md > Where It Runs and How Someone Tries It`
  Build: Shared server handler, mocked schema tests, CI, README/license, app map, full-flow capture, deployment and public repository.
  Verify (mechanical): Node tests, pilot typecheck/build/browser checks and capture; gitleaks working-tree and history clean before each push; unauthenticated public links.
  Learner check: Try deployed core flow and review the captured video. No owner account action beyond existing authorization; no Devpost submission.
  Commit: `Add optional AI service and verified sharing assets`

## Hands-on Checkpoints
- [ ] Early usable behavior explored by learner — not performed; autonomous agent browser check recorded separately.
- [ ] Final kick-the-tires exploration and feedback completed by learner — not performed.

## Final Review
- [ ] Final review complete — learner confirms ready to ship (not claimed).
Agent verification and publication proceed under the user's explicit no-question task override; unchecked human boxes are not implementation failures or invented approvals.

## Code Tour and App Map
- [x] Learning activity complete — evidence-based recap: exact selected-phrase requirement → applyFinding → repeated-occurrence/Unicode tests, summarized in README and app map; no human practice claimed.
- [x] Optional edit and transfer reflection addressed — not applicable under explicit autonomous task; reflection not collected.
- [x] `devpost/app-map.html` generated from finished code, checked in Chromium from a file URL with no scripts, and provided as the offline reference guide.
Activity and evidence: Reference recap links PRD Rewrite and Compare, src/rules.mjs applyFinding and tests/rules.test.mjs. Agent browser execution is recorded; personal learning is not inferred.
Route and stops: Reference-only route: src/main.ts check handler → src/rules.mjs analyze/applyFinding → src/main.ts renderHighlights/renderRevised. No live learner tour claimed.
Edit outcome: Not applicable under autonomous-task instructions.
Reflection: Not collected.
Activity mode: Evidence-based recap and offline reference map.

## Revisions

- Slice 1: nine Node tests, pilot TypeScript/production build and English/Korean Chromium checks pass. Playwright version expected a newer browser; reused the installed Chromium via explicit executable path.
- Slice 2: pilot production build and real Chromium core flow pass for both languages, including single/all rewrite, 84-to-0 comparison, undo, clipboard, blank/oversize/benign text, stale-edit reset, XSS text rendering and 390px layout.
- Rewrite API takes the checked finding ID rather than trusting a client-supplied phrase/template; draft and suggestion remain matched by server-owned rules. Raw match weights validate AI output even when displayed scores are capped at 100.
- Local API integration exposed a Vite startup failure despite a passing build: returning the middleware object from configureServer made Vite treat it as a post-hook. Changed the mount function to return nothing; startup/API/browser checks verify the repair.
- Final production URL browser suite passes; offline app map opens without scripts and its source anchors exist. Recording is 75 seconds at 1920x1080. No paid/live provider request was made.
- Public repository and MP4 return HTTP 200 without authentication; GitHub detects MIT. Vercel production page/API and the full browser suite pass. All learnai dev/recording processes on pilot are stopped. Gitleaks directory and full-history scans pass before publication.
