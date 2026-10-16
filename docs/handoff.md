# Outside Agents Props App — handoff (living doc)

Last updated: 2026-10-15. The spec is docs/design.md. To start or resume the build in a fresh chat, paste KICKOFF_PROMPT.md. Update this doc after every decision or finished step.

## Status
Design phase complete on 2026-10-15 (brainstormed in the Chalk That NBA chat). Design doc, kickoff prompt and README written, committed and pushed. Build NOT started: no code, no Railway project, no database, no API keys, no agents yet. Next action is Step 0 of docs/design.md section 15: propose the new root structure and the first step, then agree before any code.

## Repo
This repo (ai-agent-nba, remote github.com/Jayprox/ai-agent-nba, branch main) previously held an older, unrelated NBA app (Python backend, React frontend, Azure deployment). On 2026-10-15 JD asked to reuse the repo: every previous file was MOVED into old/ (nothing deleted; only .git and .gitignore stay at the root) and the new app's docs were added at the root. Committed and pushed by JD (main at 621fa98 plus later doc commits).

## Things to know about the old contents
- old/backend/.env was TRACKED IN GIT. It is no longer tracked (the root .gitignore ignores .env) but it remains in git history and on disk. It may contain real keys (the old RUNBOOK lists OPENAI_API_KEY, ODDS_API_KEY, API_SPORTS_KEY). If those keys are real and the repo is or ever was public, JD should rotate them. Do not read or copy that file.
- The old CI workflows were RETIRED on 2026-10-15 (JD's call): .github moved to old/.github, so GitHub no longer runs Backend CI, Frontend CI or the Uptime Check on main. Side effect: the 10-minute uptime ping of the live old Azure backend stopped. The Azure Static Web Apps deploy workflow only ran on branch release/prod-gold-2026-02-02, which keeps its own copy, so the live old app is unaffected. Add a new .github/ for this app when it needs CI.
- GitHub RULESET on main: requires pull requests and "2 of 2 required status checks" (the retired CI jobs, so a PR can never satisfy them). JD's pushes currently bypass it as admin ("Bypassed rule violations"). Before the build starts JD should remove the two required checks (GitHub, Settings, Rules), or keep bypassing, or add new CI and require its checks. Not yet decided.

## Decisions log (all captured in docs/design.md)
NBA only, web only, one user, G/F/C positions. Markets: points, rebounds, assists, threes, PRA (PA, PR, RA, steals, blocks stay in Chalk That only). Simulations and confidence are code; AI only bounded adjustments (fixed menu with hard clamps) and explanations. Row-bootstrap Monte Carlo with minutes scaling. Confidence = probability of the picked side + tier (Lean/Solid/Strong). One shared news brief per game; the NBA official injury report is status truth, agents flag disagreements only. Chalk That owns lines (open, pick-time, close). Schedule: morning provisional run (brief + code baseline) and an official wave run 2 hours before the earliest tip (never before the report window closes + 15 minutes); no later agent runs; pick graded on pick-time line; caution note if the line moves; code-only void flag if a picked player is listed out. Roster: Haiku brief agent, G/F/C Sonnet-class analysts, independent reviewer/explainer; code prefilter. Cost target about $42/month, hard cap $60/month, spend log and guard. Grading: baseline and adjusted probability stored for every line; morning evaluations graded for calibration only; own Postgres in a separate Railway project. UI: 8 screens (Today, Game page, Picks board, Player lookup with optional "run the agents", Track record, History, Ops, Sign-in), same dark Chalk That token family with a different accent. Stack: TypeScript, Railway worker + web, Postgres, own orchestrator on the Messages API, model per agent in config; single-user sign-in. Search source tiers: official report, then aggregators (ESPN, CBS, Rotowire), then open web search for late news; every claim has a source URL. Local AI on JD's M1 Pro 16" (32 GB): brainstorm only, not v1; revisit with a replay test after week one.

## Prerequisites in Chalk That (Backlog v2 items 23 to 26; also item 8)
Added to the Chalk That repo's docs/vibe-coding-checklist.md and PUSHED (2026-10-15), but NONE are built yet: game props (23), 2-hour pick-time snapshot (24), reliable injury source (25; the Oct 21 to 22 opening-night checks decide Highlightly vs the NBA official report), agent markets scope (26), with/without a teammate (8). The agents app can be designed and partly built before they exist, but it needs game props, the pick-time snapshot and an injury source to run for real. Check their status in that checklist first.
Naming: Chalk That NBA is now publicly "Chalk That Hardwood" on web and iOS (trademark reasons). The repo is still ai-application-nba and internal names still say NBA. Chalk That stays numbers-only; picks, simulations and confidence live only in this app.

## App backlog
1. Efficiency enhancements (Batch API for the morning run, caching, tighter prefilter, fewer searches, more Haiku steps, skip low-signal games). 2. Game-level analyst for spreads and totals (after Chalk That item 23). 3. Study of when lines settle if needed. 4. Local-model replay test.

## Still open
Minimum edge, minimum sample and tier cutoffs (from shadow-mode data); starting adjustment ranges (tune in dry runs); shadow-mode length; accent color; whether Chalk That item 24 ships before opening night; the main-branch ruleset; whether the old .env keys need rotating.

## Next steps
1. Fresh chat with KICKOFF_PROMPT.md; Step 0 is proposing the root structure (no code until agreed).
2. JD: decide the main-branch ruleset and check the old .env keys before building.
3. Opening night (Oct 21 to 22): injury source result feeds Chalk That item 25.
