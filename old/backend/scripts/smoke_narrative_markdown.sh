#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"

echo "== Default (env) =="
curl -s "${BASE}/nba/narrative/markdown?mode=ai" \
  | jq '.ok, .raw.meta.trends_override, .raw.meta.trends_enabled_in_narrative, (.raw.player_trends|length), (.raw.team_trends|length)'

echo "== Force OFF =="
curl -s "${BASE}/nba/narrative/markdown?mode=ai&trends=0" \
  | jq '.ok, .raw.meta.trends_override, .raw.meta.trends_enabled_in_narrative, (.raw.player_trends|length), (.raw.team_trends|length), .raw.meta.soft_errors.trends'

echo "== Force ON =="
curl -s "${BASE}/nba/narrative/markdown?mode=ai&trends=1" \
  | jq '.ok, .raw.meta.trends_override, .raw.meta.trends_enabled_in_narrative, (.raw.player_trends|length), (.raw.team_trends|length)'
