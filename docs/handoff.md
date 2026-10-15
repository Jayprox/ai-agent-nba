# Outside Agents Props App — handoff (living doc)

Last updated: 2026-10-15. The spec is docs/design.md. To start or resume the build in a fresh chat, paste KICKOFF_PROMPT.md. Update this doc after every decision or finished step.

## Status
Design phase complete on 2026-10-15 (brainstormed in the Chalk That NBA chat). Design doc, kickoff prompt and README written. Build NOT started.

## Repo
This repo (ai-agent-nba) previously held an older, unrelated NBA app (Python backend, React frontend, Azure deployment). On 2026-10-15 JD asked to reuse the repo: every previous file was moved into old/ (nothing deleted; only .git and .gitignore stay at the root) and the new app's docs were added at the root. The moves are uncommitted until JD commits them (git will show them as renames).

## Things to know about the old contents
- old/backend/.env was TRACKED IN GIT (it showed up as a deleted tracked file when moved). It may contain real keys (the old RUNBOOK lists OPENAI_API_KEY, ODDS_API_KEY, API_SPORTS_KEY). If those keys are real and the repo is or ever was public, rotate them. Do not read or copy that file.
- The old CI workflows were RETIRED on 2026-10-15 (JD's call): .github moved to old/.github, so GitHub no longer runs Backend CI, Frontend CI or the Uptime Check on main. Side effect: the 10-minute uptime ping of the live old Azure backend stopped. The Azure Static Web Apps deploy workflow only ran on branch release/prod-gold-2026-02-02, which keeps its own copy of the workflow, so the live old app is unaffected. Add a new .github/ for this app when it needs CI.
- Once the move is committed, old/backend/.env is no longer tracked (the root .gitignore ignores .env), but it remains in git history and on disk locally.

## Decisions log (all captured in docs/design.md)
NBA only, web only, one user, G/F/C positions. Markets: points, rebounds, assists, threes, PRA (PA, PR, RA, steals, blocks stay in Chalk That only). Simulations and confidence are code; AI only bounded adjustments (fixed menu with hard clamps) and explanations. Row-bootstrap Monte Carlo with minutes scaling. Confidence = probability of the picked side + tier (Lean/Solid/Strong). One shared news brief per game; the NBA official injury report is status truth, agents flag disagreements only. Chalk That owns lines (open, pick-time, close). Schedule: morning provisional run (brief + code baseline) and an official wave run 2 hours before the earliest tip (never before the report window closes + 15 minutes); no later agent runs; pick graded on pick-time line; caution note if the line moves; code-only void flag if a picked player is listed out. Roster: Haiku brief agent, G/F/C Sonnet-class analysts, independent reviewer/explainer; code prefilter. Cost target about $42/month, hard cap $60/month, spend log and guard. Grading: baseline and adjusted probability stored for every line; morning evaluations graded for calibration only; own Postgres in a separate Railway project. UI: 8 screens (Today, Game page, Picks board, Player lookup with optional "run the agents", Track record, History, Ops, Sign-in), same dark Chalk That token family with a different accent. Stack: TypeScript, Railway worker + web, Postgres, own orchestrator on the Messages API, model per agent in config; single-user sign-in. Search source tiers: official report, then aggregators (ESPN, CBS, Rotowire), then open web search for late news; every claim has a source URL. Local AI on JD's M1 Pro 16" (32 GB): brainstorm only, not v1; revisit with a replay test after week one.

## Prerequisites in Chalk That (Backlog v2 items 23 to 26; also item 8)
Edited in that repo's docs/vibe-coding-checklist.md and staged, not yet committed (JD commits from his own terminal). Game props (23), 2-hour pick-time snapshot (24), reliable injury source (25, opening-night Highlightly re-test then the NBA report), agent markets scope (26), with/without a teammate (8).

## App backlog
1. Efficiency enhancements (Batch API for the morning run, caching, tighter prefilter, fewer searches, more Haiku steps, skip low-signal games). 2. Game-level analyst for spreads and totals (after Chalk That item 23). 3. Study of when lines settle if needed. 4. Local-model replay test.

## Still open
Minimum edge, minimum sample and tier cutoffs (from shadow-mode data); starting adjustment ranges (tune in dry runs); shadow-mode length; accent color; whether Chalk That item 24 ships before opening night; the CI workflow decision above.

## Next steps
1. JD commits the repo reorganization (old/ plus the new root docs).
2. Check whether the old .env keys are real and rotate them if the repo is or was public.
3. Fresh chat with KICKOFF_PROMPT.md; Step 0 is proposing the root structure.
