def build_narrative_context(trends, team_trends, odds, player_props):
    return {
        "player_trends": trends.get("player_trends", []),
        "team_trends": team_trends.get("team_trends", []),
        "odds": odds.get("games", []),
        "player_props": player_props or []
    }
