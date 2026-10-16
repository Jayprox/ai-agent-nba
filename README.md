# ai-agent-nba — Outside Agents Props App

A standalone web app that adds a simulated probability, a confidence tier (Lean / Solid / Strong) and written reasoning to NBA player props, using the Chalk That NBA API as its only source of stats and lines. One user (JD). A research tool, not betting advice.

Status (2026-10-15): design agreed and pushed, build not started (no code yet; the next step is proposing the root structure).

## How it works, in four lines
- Numbers are code: the simulation (row-bootstrap Monte Carlo with minutes scaling), probabilities, edge and confidence. AI only proposes bounded adjustments from a fixed menu and writes explanations; it never writes a number that is not in its input.
- Agents: a Haiku news-brief agent (web search, one brief per game), G/F/C division analysts and an independent reviewer/explainer.
- Every line is graded (baseline and adjusted probability stored), so confidence is checked against results, not trusted.
- Cost target about $42/month, hard cap $60/month, enforced in code.

## Where things are
- docs/design.md — the full design (the spec).
- docs/handoff.md — current state, decisions log, next steps. Updated after every decision.
- KICKOFF_PROMPT.md — paste into a fresh chat to start or resume the build.
- old/ — the previous contents of this repo (the earlier ai-agent-nba app: Python backend, React frontend, Azure deployment), moved here on 2026-10-15. Not part of the new app; do not reuse it unless JD says so.
- old/.github/ — the old app's CI, uptime and Azure deploy workflows, retired on 2026-10-15 by moving them out of the root (GitHub only runs workflows from the root .github/). A new .github/ can be added for this app when it needs CI.

Until the build starts, the working copies of these docs also live in the Claude project "ai-application-nba-ios" under claude/outside-agents-*.md. Once the build starts in this repo, the files here are the source of truth.

## Related
Chalk That NBA (the data source, numbers-only; publicly named Chalk That Hardwood, repo and internal names unchanged): /Users/jayprox_pro/Documents/Projects/git/ai-application-nba
