# Outside Agents Props App — Design Doc (v1)

Written 2026-10-15 from the brainstorm in the Chalk That NBA chat. Status: design agreed, build not started. Repo: /Users/jayprox_pro/Documents/Projects/git/ai-agent-nba (reused on 2026-10-15; the previous contents were moved into old/). Companion docs: docs/handoff.md (state and next steps) and KICKOFF_PROMPT.md (paste into a fresh chat to start the build).

## 1. Purpose and principles
A standalone web app that adds a simulated probability, a confidence tier and written reasoning to NBA player props (and later game props), using Chalk That NBA's API as the only source of stats and lines. Just one user (JD). Research tool, not betting advice, and the app says so.
Principles (non-negotiable):
1. Chalk That stays numbers-only. All predictions live in this app, never in Chalk That.
2. Numbers are code. Simulations, probabilities, edge and confidence are computed by code. AI only supplies bounded adjustments and writes explanations. AI never writes a number that is not in its input.
3. Every line is graded, so confidence can be checked against reality (calibration), not trusted.
4. Honest accuracy beats volume: "no pick" is a valid output.
5. Cost is controlled in code: target about $42/month, hard cap $60/month.

## 2. Scope
In v1: NBA only; web only; one user; markets points, rebounds, assists, threes, PRA; player props first.
Not in v1: other sports, iOS, multi-user, steals/blocks/PA/PR/RA picks (they stay in Chalk That only), game props analysis (needs Chalk That to add them first), local models, notifications.

## 3. Architecture
Two Railway services in a NEW Railway project, with its own Postgres (separate from Chalk That's):
- worker: scheduler, data loader, simulator, agent orchestrator, grader, status watcher.
- web: small server for the UI and a JSON API for the UI.
Language: TypeScript. Agent runtime: our own orchestrator on the Anthropic Messages API (same choice as ai-agents-nfl), with web search via the API's search tool. The model for every agent is set in config (provider-agnostic interface) so changing a model, or later trying a local one, is a config change.
Data flow: Chalk That API (stats, lines, results) -> data loader -> simulator (code) -> evaluations table. News brief agent (web search) -> analysts (adjustments from a menu) -> reviewer/explainer -> code applies clamped adjustments and re-simulates -> picks. Grader reads results from Chalk That after games finish.
Auth to Chalk That: its long-lived agent API key (the "agents/services" tier in PLATFORM.md). JD sets keys in Railway himself; nobody else enters secrets.

## 4. What this needs from Chalk That
Exists today (docs/api.md in the Chalk That repo): POST /query (game logs under splits, rest, venue; props hit rates at a line), GET /props (DraftKings open and close lines, graded results), GET /players/:id/props, GET /rankings/matchups (defense by position G/F/C), GET /games, team ratings and pace (est.), usage rate (est.).
Missing, added to Chalk That Backlog v2 as items 23 to 26:
- 23 Game props (spreads, totals, moneylines, team totals, quarters) from The Odds API. Needed for blowout-risk minutes and for later game-prop analysis.
- 24 Pick-time line snapshot, a third props pull 2 hours before tip in waves (games within 45 minutes pull together), served as open / pick-time / close.
- 25 Reliable injury source: Highlightly re-test on opening night (Oct 21 to 22); if still none, evaluate the NBA's official injury report (PDF, may need to run from JD's Mac) with a small test first. Chalk That's current_injury field is null until then.
- 26 Agent markets scope: the agents cover points, rebounds, assists, threes and PRA only.
- Also needed: Backlog item 8, with/without a teammate (the usage-shift adjustment depends on it).
Check before building: Chalk That API rate limits and caching behavior for agent-style bulk reads.

## 5. Run schedule
Per game day, in the venue time zone (ET reference):
1. Morning run, when lines open: PROVISIONAL "early look". News brief (Haiku) plus a code-only baseline simulation. No analysts, no reviewer. Evaluations are stored and graded for calibration only; never shown as picks.
2. Official pick run, in WAVES. Games tipping within 45 minutes of each other form one wave; the wave runs once at (earliest tip minus 2 hours). Never earlier than the NBA game-day injury report window closes plus 15 minutes (a noon tip runs about 10:15 am). Concurrency cap about 4, with a queue. The brief refreshes the morning one (about 2 searches), then analysts, reviewer, simulation, picks.
3. No further agent runs. No 5-minute lock re-run, no 10-minute delta run.
4. The official pick is stamped with line and price at that moment and graded on that line. The close line is recorded separately for closing line value (CLV).
5. After publication, code only: compare the pick's line with Chalk That's latest line and show a caution note when they differ. If a picked player is listed out, mark "status changed, pick void".
6. UI wording: "Picks are final about 2 hours before tip. Lines can change after."
NBA injury report rules (verified 2026-10-14 from official.nba.com and AP): day before game status due by 5 pm local; game-day resubmission 11 am to 1 pm local (8 to 10 am for tips at 5 pm or earlier); second night of a back-to-back due by 1 pm local. Inactive lists and starters appear shortly before tip (about 30 minutes believed, not verified). The official report is the status truth; agents flag disagreements, never override.

## 6. Simulation (code)
Per player and market (points, rebounds, assists, threes, PRA):
1. Inputs from Chalk That: game logs under matching splits (venue, rest, back-to-back), L5, L10, season, minutes, usage (est.), pace and ratings (est.), defense by position rank, game spread and total (for blowout-risk minutes), the line and price.
2. Minutes expectation and per-minute rate from his recent games; small-sample splits shrunk toward his season rate by sample size.
3. Context multipliers in code: opponent defense by position, pace, rest, venue.
4. Bounded AI adjustments (section 7) applied and clamped.
5. Row-bootstrap Monte Carlo, 10,000 draws: resample whole past game rows (keeps points, rebounds and assists correlated, which matters for PRA), rescale each to the projected minutes, apply multipliers.
6. Output: P(over), P(under), median, range (p10 to p90).
7. Edge = model probability for a side minus the book's no-vig implied probability for that side (convert both American prices to probabilities, then normalize so they sum to 1).
Store both the BASELINE result (no AI adjustments) and the ADJUSTED result.
Tests: validate the distributions by backtest on 23 seasons of box scores in Chalk That (do the predicted percentiles match actual outcomes?). No lines are needed for that. Edges can only be checked live because lines exist from 2026-27 only.

## 7. AI layer
Roster (per game, about 7 games a day over the season):
1. News brief agent (Haiku, web search): one shared brief per game. Per team and player: status (from the official report), news items {player, kind (injury, role, lineup, rest, trade), summary, source_url, published_at, source tier}. Every claim has a source URL. Source tiers: (1) the NBA official injury report, (2) aggregators such as ESPN, CBS Sports and Rotowire for role and minutes news, (3) open web search for late-breaking news, beat-writer articles preferred over social posts.
2. Division analysts G, F, C (Sonnet-class, three agents): read the brief plus Chalk That numbers for players in their position group and propose adjustments from the menu.
3. Reviewer and explainer (Sonnet-class, independent agent): checks adjustments against the official report, rejects any without a valid source or that double count, writes the explanation from the final numbers. It cannot add numbers.
Later: a game-level analyst for spreads and totals once Chalk That has game props.
Adjustment menu (starting ranges, to be tuned in dry runs; start conservative):
- minutes_delta: minutes added or removed (starting clamp: plus or minus 6).
- usage_multiplier: scales per-minute scoring and assist rate (starting clamp: 0.90 to 1.15).
- availability_flag: agrees or disagrees with the official report; a disagreement is only a flag for the reviewer and the UI, it does not change status.
- role_change: starter to bench or bench to starter, mapped by code to a minutes change.
Each adjustment carries: type, size, reason, source_url, fetched_at. Code rejects it if the URL is not in the brief's source list, if the size is outside the clamp, or if it duplicates another adjustment.
Explanation guard: the explanation text may only contain numbers that appear in the data given to the explainer; a check rejects the explanation otherwise (same guard as Chalk That's Ask).
Code prefilter: analysts only see players whose baseline edge is within a looser threshold than the pick threshold, or who are named in the brief (or whose teammate's status changed). A skipped player's pick, if any, comes from the code baseline alone.

## 8. Pick rule and confidence
- A pick requires: edge at or above a minimum, enough games in the sample, a stable role, and no unresolved disagreement flag. Minimum edge, minimum sample and tier cutoffs are set from data in shadow mode, not guessed. Until calibration exists, no picks are published.
- Confidence shown: the model's probability for the picked side (for example 62%), plus a tier Lean / Solid / Strong derived from probability, edge and sample quality.
- "No pick" is a valid, common output.

## 9. Grading and data model (own Postgres)
Tables (Chalk That ids referenced, stats not copied):
- runs (type morning or official, wave id, start, finish, status, totals).
- briefs (game, run, JSON, sources, model).
- spend_log (run, agent, model, input and output tokens, searches, cost).
- adjustments (run, player, type, requested and clamped size, reason, source_url, proposing agent, reviewer accepted or rejected with reason).
- evaluations: ONE ROW PER LINE PER RUN, pick or not: line, over and under prices, baseline minutes and rate, baseline probability, adjusted probability, no-vig implied probability, edge, median, p10, p90, simulation seed, data-quality flags, pick side and tier if any.
- picks: derived from evaluations; version, provisional or official, explanation, void flag and reason, published time.
- results: actual stat, over / under / push / dnp (from Chalk That), close line, CLV.
Rules: a push on a whole-number line and a DNP are no action; graded against the pick-time line; every report shows sample size.
Reports: calibration by probability bucket, Brier score, hit rate by tier, market and position, CLV, and baseline versus adjusted (do the AI adjustments improve on the code-only baseline?).

## 10. UI (web, one user; same dark Chalk That token family, different accent)
Colors: use Chalk That's tokens (paper #0B0F14, card #121820, ink #F5F7FA, muted #9AA7B4, line #2A3540, positive #34D399, caution #E8B64A, live #F2545B; see Chalk That docs/ios-kickoff.md section 5) with a different accent than Chalk That's orange #F4762B. Oswald display font and Inter or system text, tabular figures.
Screens:
1. Today: games grouped by wave with status (early look, official, tipped), pick count, time picks go final; budget meter (month spend vs $42 target and $60 cap).
2. Game page: the brief with sources; disagreements between news and the official report; every line with probability, edge, pick or no pick, tier, adjustments applied (baseline vs adjusted), explanation, line-moved caution, void flag.
3. Picks board: the day's official picks, sortable by tier, probability and market.
4. Player lookup: code-only simulation, free and instant; an optional "run the agents" button runs the roster on that player and counts against the cap.
5. Track record: calibration, Brier score, hit rate by tier/market/position, CLV, baseline vs adjusted, sample sizes everywhere.
6. History: past days with picks and results.
7. Ops: runs, spend log, cap status, failures, model per agent.
8. Sign-in: one user.
Empty states are designed (no games, preseason, no lines yet, run failed, cap reached).

## 11. Cost and budget guard
Prices (platform.claude.com, fetched 2026-10-15): Sonnet 5.5 $2 in / $10 out per million tokens; Haiku 5.5 $0.10 / $0.50 (up to 100K-token prompts); Opus 5.5 $4 / $20; Batch API 50% off; cache read 0.05x (Sonnet), 0.1x (Haiku); web search $10 per 1,000 searches plus tokens (results count as input).
Estimate (token counts are guesses, plus or minus 2x; about 7 games a day, about 210 games a month): all-Sonnet about $0.60 per game (about $128/month); Haiku brief plus Sonnet analysts/reviewer about $0.32 (about $67); plus prefilter, cached shared brief, reviewer only on picks, brief refresh only: about $0.20 (about $42/month, of which search about $15). The last is the design.
Guard: log tokens, searches and dollars for every call (spend_log). Monthly hard cap $60 and a daily pace guard derived from the remaining budget (about $2 a day on a normal slate, headroom for heavy nights). Near the cap: skip lowest-value games and fall back to code-only. After week one, replace estimates with measured numbers. Efficiency enhancements are an app backlog item.

## 12. Security and operations
- Single user: username and password, hashed, session cookie (httpOnly, secure), login rate limit. JD creates the account and sets secrets in Railway; no one else enters secrets.
- Chalk That API key and Anthropic API key live only in Railway variables.
- Idempotent runs (a retried wave must not double-write picks); every run is a row in runs with status.
- Health endpoint and a status line on Ops; failures never publish a half-finished pick.
- Time handling: store UTC, show ET and the viewer's local time.

## 13. Testing and validation
1. Unit tests: simulator on fixed seeds, no-vig conversion, clamp and duplicate rules, wave grouping, report-window rule, grader (push, DNP, void).
2. Backtest the simulator's distributions on 23 seasons of Chalk That box scores (no lines).
3. Dry run the brief agent: Haiku vs Sonnet on about 3 real games; switch back only if Haiku misses material news.
4. Shadow mode: run the full pipeline unpublished for a set number of game days (length set by JD), grade everything, and use the result to set minimum edge and tier cutoffs.
5. Replay test (after week one): feed logged analyst prompts to a local model on JD's M1 Pro 16" (32 GB) offline and compare. Brainstorm only; not a v1 requirement.

## 14. Risks
- Injury source not yet reliable (Chalk That item 25); the 2-hour run depends on it.
- Lines move after the pick; mitigated by pick-time stamping, a caution note and CLV tracking.
- Closing lines are hard to beat; the goal is honest calibration and positive CLV, not a promise of profit. The UI says so.
- Haiku quality on the brief; mitigated by the dry run and a config switch.
- Token costs may differ from estimates; mitigated by the spend guard.

## 15. Build order (one step at a time, walk through each with JD before building)
0. The repo is reused: the previous contents are in old/ (do not reuse unless JD says so). Propose the root structure for the new app, set up TypeScript and tests, and have JD create the new Railway project and Postgres and set secrets.
1. Chalk That client and data loader (read-only), schema migrations for the tables in section 9.
2. Simulator and the 23-season backtest (needs nothing new from Chalk That).
3. Grader against Chalk That results (props results exist from 2026-27).
4. News brief agent and the Haiku vs Sonnet dry run.
5. Analysts, reviewer, menu and guards; code prefilter.
6. Scheduler: morning run, waves, status watcher, concurrency queue.
7. UI screens (Today and Game page first, then Picks board, Player lookup, Track record, History, Ops, Sign-in).
8. Spend guard and Ops page.
9. Shadow mode, then set thresholds, then go live.
Steps 1 to 3 and the UI skeleton do not depend on the Chalk That prerequisites; steps 4 to 6 need items 24 and 25; game-prop analysis needs item 23.

## 16. Open items
Minimum edge, minimum sample and tier cutoffs (from shadow data); starting adjustment ranges (tune in dry runs); shadow-mode length; accent color; whether the Chalk That 2-hour snapshot (item 24) can ship before opening night or lands a few weeks in.

## Sources
- NBA official injury report page: https://official.nba.com/nba-injury-report-2025-26/
- AP via News4Jax, NBA tweaks injury reporting rules (Dec 19, 2025): https://www.news4jax.com/sports/2025/12/19/nba-tweaks-its-injury-reporting-rules-still-wants-changes-to-prop-betting/
- Claude API pricing: https://platform.claude.com/docs/en/about-claude/pricing
