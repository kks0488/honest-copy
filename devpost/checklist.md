---
doc: checklist
status: approved
---
# Build Checklist
Build mode: fast, per explicit autonomous-task instruction. Approval delegated by task; no interactive learner approval claimed.

## Slices

- [ ] **1. Paste copy and understand exact risky phrases**
  Becomes usable: Running English/Korean checker with inline highlights, explanations and initial score.
  Why now: Delivers the unique kernel first, including scaffold and tests.
  PRD ref: `prd.md > Paste and Check`, `prd.md > Phrase Review`
  Spec ref: `spec.md > Rules Engine`, `spec.md > Workspace`
  Build: Add Vite/TS scaffold, bilingual rules, DOM workspace and check results.
  Verify (mechanical): Node rule tests, typecheck/build on pilot, browser sample produces all four categories.
  Learner check: Paste a listing; compare highlighted phrases with explanations. Agent will test this under explicit no-pause override; human check remains pending.
  Commit: `Build bilingual phrase checker and review workspace`

- [ ] **2. Apply suggestions and compare the revised draft**
  Becomes usable: Individual/all template rewrites, baseline/current scores, undo and copy.
  Why now: Closes the product loop on the verified detection behavior.
  PRD ref: `prd.md > Rewrite and Compare`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Rules Engine`, `spec.md > Workspace`, `spec.md > Data Model`
  Build: Add exact replacement, recheck, fixed baseline, undo, copy and stale-state resets.
  Verify (mechanical): Rules tests for repeated spans/Unicode/overlaps and score changes; browser single/all/undo/empty/edit/copy/mobile checks on pilot.
  Learner check: Apply one and all suggestions, compare scores, undo and copy. Human feedback remains pending.
  Commit: `Add safer draft comparison undo and copy`

- [ ] **3. Optional AI wording, verification and sharing**
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
- [ ] Learning activity complete — concise evidence-based recap after build.
- [ ] Optional edit and transfer reflection addressed — no extra exercise requested; personal reflection not inferred.
- [ ] `devpost/app-map.html` generated from finished code, checked and shown.
Activity and evidence: Pending build.
Route and stops: Reference-only route planned; no live learner tour claimed.
Edit outcome: Not applicable under autonomous-task instructions.
Reflection: Not collected.
Activity mode: Evidence-based recap and offline reference map.

## Revisions
