# Kickoff prompt — paste into a fresh chat

---

I'm JD. We're building an NBA "outside agents" props app in this repo (/Users/jayprox_pro/Documents/Projects/git/ai-agent-nba). The full design is agreed. Read these first, in this order:
1. docs/design.md (the spec)
2. docs/handoff.md (current state, decisions log, next steps)
3. In the Chalk That NBA repo (/Users/jayprox_pro/Documents/Projects/git/ai-application-nba): PLATFORM.md, docs/api.md, and Backlog v2 items 21 to 26 in docs/vibe-coding-checklist.md. Chalk That (publicly "Chalk That Hardwood", repo and internal names still NBA) is the data source and stays numbers-only.

The previous contents of this repo (an older Python/React app deployed on Azure) were moved into old/ on 2026-10-15. Do not reuse any of it unless I say so. Note: old/backend/.env was tracked in git; never read it or copy anything from it. The main branch has a ruleset requiring checks that no longer exist (see docs/handoff.md); I push as admin.

What it is, in six lines:
- A standalone web app (TypeScript, Railway worker + web service, its own Postgres) that adds a simulated probability, a confidence tier (Lean / Solid / Strong) and reasoning to NBA player props. Markets: points, rebounds, assists, threes, PRA. One user (me).
- Numbers are code. The simulation (row-bootstrap Monte Carlo with minutes scaling), probabilities, edge and confidence are code. AI only proposes bounded adjustments from a fixed menu and writes explanations. AI never writes a number that isn't in its input.
- Agents: a Haiku news-brief agent (web search, one brief per game), G/F/C division analysts and an independent reviewer/explainer (Sonnet-class). Morning run = brief + code baseline only (provisional). Official pick run per wave of games, 2 hours before the earliest tip.
- Every line is graded: store baseline AND adjusted probability for every line, grade on the pick-time line, track CLV and calibration.
- Cost target about $42/month, hard cap $60/month, enforced in code with a spend log.
- Chalk That owns lines and stats; some prerequisites (game props, 2-hour snapshot, injury source) may not exist yet. Check their status first.

How I work (please follow):
- Walk through each decision with me before building. Build one step at a time and show what each step does before moving on.
- Give terminal commands with absolute cd paths, no inline # comments, and label every step Air, Pro or Either (my MacBook Air or MacBook Pro). Put all the commands for a task in one code block (one block per machine if steps run on different Macs).
- I run builds, tests and git myself. Never enter passwords or API keys for me; I set secrets in Railway.
- Update docs/handoff.md after every decision or finished step, so a new chat can pick up where we left off.

Start with Step 0 of the build order in docs/design.md (section 15): propose the new repo structure at the root and the first step. Do not write code until we've agreed on it.

---
