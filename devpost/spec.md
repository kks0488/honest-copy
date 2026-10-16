---
doc: spec
status: approved
---
# Honest Copy — Technical Spec

## How This Works, In Plain Language
The page searches your draft for a small visible set of phrases. It marks the words, explains the concern and replaces only the words you choose. It checks the revised draft again so you can compare. Everything stays in this tab unless you explicitly request AI wording; that request goes through a small server handler so the secret key stays off the page.

## The Core Journey Through the System
`prd.md > The Core Journey`: textarea → analyze(text) → exact matches and weighted risk → safe DOM highlights/cards → apply exact replacement → analyze again → revised copy and before/after score → clipboard. Optional AI goes to `/api/rewrite`, returns a suggestion, then the user applies it.

## Stack
Agent selection within user's Vite + vanilla TS preference: Vite, TypeScript, browser DOM and Node built-in test runner. Shared rules and server logic are plain ESM JavaScript so tests need no transpiler. Minimal Vercel serverless handler; Vite plugin serves the same API locally. No runtime dependency or database.
Docs: https://vite.dev/guide/ (requires Node 20.19+ or 22.12+), https://www.typescriptlang.org/docs/, https://nodejs.org/api/test.html, https://vercel.com/docs/functions. Versions pinned by package-lock after install on pilot.

## Where It Runs and How Someone Tries It
Node 22.12+ recommended. `npm install && npm run dev`, open http://localhost:5173. `npm test`; `npm run build`; `npm run preview` serves the built client plus the same local API plugin. No key needed. Copy `.env.example` to `.env` for optional provider configuration; restart dev server. Vercel: `vercel --prod --yes` (explicitly authorized). Static hosting supports templates; live AI requires the server handler.
Heavy dependencies/builds/dev servers/Playwright/capture run on `pilot` in `~/workspace/hackathons/learnai`; timeout all server processes. Local work limited to edits/git/small Node tests/scans. Required public repo: https://github.com/kks0488/honest-copy. Record at 1920x1080 on pilot and pull small captures; large video in owner's requested external capture directory. Sharing URLs recorded here after verification.

## Look and Feel
Implements `prd.md > Look and Feel`: responsive 2-column paper workspace, forest green actions, system serif headline and sans body, modest rounded borders, numeric before/after score, four accessible labeled highlight types. No external fonts, imagery or logos.

## Components
### Rules Engine
`src/rules.mjs`: rule IDs, regexes, risk weights, plain explanations and deterministic bilingual templates. `analyze`, `applyFinding`, `applyAll`; stable source offsets and priority selection for overlapping matches. Score = min(100, sum matched weights), explicitly a heuristic. Implements `prd.md > Phrase Review` and `Rewrite and Compare`.
### Workspace
`src/main.ts` and `src/style.css`: render using DOM text nodes, manage input/baseline/current/history and selected suggestions. No persisted user text. Guard stale async responses by revision token. Implements `prd.md > Paste and Check`, `Rewrite and Compare`, `States and Boundaries`.
### Rewrite Service
`api/rewrite.mjs`, `server/rewrite.mjs`: GET returns configured mode without secrets. POST validates text/findingId using a current deterministic finding; rate and length limits. No key → deterministic replacement with explicit template mode. Key → native fetch OpenAI-compatible chat completion, 10-second timeout, JSON content `{replacement:string}`, no tool execution. Recheck returned suggestion, reject flagged wording or invalid/long output; fallback template with visible reason. Vite config adapts the shared handler for local dev and preview. Implements `prd.md > Optional AI Wording`.

## Data Model
Only in browser memory: `{input, baseline, current, history[], findings[], baselineScore, revision, pending}`. Finding = `{id, ruleId, start, end, phrase, category, label, explanation, replacement, weight}`. Mutation re-analyzes current text; baseline fixed until new Check. No localStorage/cookies/database. Server processes only request payload; no copy logging.

## File Structure
```
honest-copy/
  devpost/{scope,prd,spec,checklist}.md # canonical skill artifacts
  devpost/learner-profile.md          # ignored personal context
  devpost/app-map.html                # required offline code guide
  src/{main.ts,style.css,rules.mjs}    # UI + shared checks
  server/rewrite.mjs                  # provider logic
  api/rewrite.mjs                     # Vercel adapter
  tests/{rules,rewrite}.test.mjs       # built-in Node tests
  scripts/capture.mjs                 # pilot browser checks/capture
  media/                             # small real-app screenshots only
  .github/workflows/ci.yml            # tests/typecheck/build
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  package-lock.json
  .env.example
  .gitignore
  README.md
  LICENSE
```
Installed official skill-pack files remain in their original locations with upstream license retained.

## External Services and Dependencies
Official API docs verified by curl: https://docs.tokenfactory.nebius.com/quickstart. Default base `https://api.tokenfactory.nebius.com/v1/`; default model `deepseek-ai/DeepSeek-R1-0528` shown in docs. Env overrides `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. POST `chat/completions` using Bearer auth with `{model,messages:[{role,content}],temperature:0.2,max_tokens:300}`; response `{choices:[{message:{content:"{\"replacement\":\"...\"}"}}]}`. Demo fixtures follow that response schema in mocked provider tests; the actual no-key application uses real deterministic rules/templates, not a simulated live call. No paid request during development. Live costs/rate limits depend on owner's provider; not exercised without credentials. Alternative compatible endpoint can be supplied by env. Public endpoint has basic per-instance throttling; production with keys needs stronger abuse controls before broad promotion.

## Important Failure Modes
- Pattern coverage is finite → explain no-match limits and never declare copy compliant.
- Provider timeout/error/invalid response → return and label local template fallback.
- Draft changes during request → ignore stale result. Clipboard denied → select visible revised text manually.

## What Was Simplified and Why
No persistence or accounts per brief. Small bilingual pattern list instead of legal classifier. Weighted counts instead of uncalibrated compliance probability. Native fetch instead of a large SDK. Real deterministic templates let every core action work offline.

## Decisions and Open Issues
All quoted intentions originate in the brief; layout/score/limits and vanilla TS choice are delegated agent assumptions. One useful planning question: how can “safer” be tested without claiming legal safety? Answer: test exact spans, non-invented template output and fewer known pattern hits; explicitly retain coverage limits. Human learning is not inferred from this explanation. Planning is approved under autonomous task authorization, not fabricated learner sign-off.

## Sharing Results
- Live deployment: https://honest-copy.vercel.app — unauthenticated page and GET/POST API checks return HTTP 200 in actual template mode.
- Public source target: https://github.com/kks0488/honest-copy — publication verification recorded below when complete.
- Real demo: `media/demo.mp4`, 75 seconds, H.264, 1920x1080, approximately 1.1 MB. Original screen recording remains on pilot at `/tmp/learnai-capture/honest-copy-raw.webm`. Small screenshots live in `media/`.
- Agent checks: 27 Node tests; pilot TypeScript/build; English/Korean core flows, undo/copy, error states, responsive width, text injection protection, actual template API and explicitly mocked AI integration. Live provider calls remain untested without a key.
- Source planning is saved before app code in the first git commit. No learner-profile or credential files are tracked. No money spent or services signed up for.

### 6-ship outcome and owner steps
The official current ship skill requires learner-authored submission text; it does not generate a Devpost-description artifact. Its exact instruction is: “Submission copy and any optional peer feedback must be human-written, even on request.” The user's provided IDEA ANSWERS remain the source notes in scope/PRD; no invented personal reflection or submission prose was generated. Human-only reviews in the checklist remain unchecked, under the user's explicit instruction to proceed autonomously without questions. This records the deviation rather than pretending the full interactive curriculum occurred.

The public-repository, privacy, real-recording and optional-deployment mechanics of 6-ship are performed under the user's existing authorization. Remaining submission tasks: upload the MP4 publicly to YouTube or Vimeo (required by the live rules), write the short description and personal learning reflection, complete the Devpost fields/exit survey and submit personally. Devpost was not accessed for account actions or submission; no signup occurred. Core use needs no account or key. Optional live AI needs an owner's provider key; broad funded use also needs stronger abuse controls.
