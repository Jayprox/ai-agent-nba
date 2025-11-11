from datetime import datetime, timezone
from agents.player_performance_agent.fetch_player_performance import summarize_players
from agents.player_performance_agent.analyze_trends import analyze_player_trends

def get_player_insights():
    """
    Combine player performance and trend analysis into one unified dataset.
    """
    # Step 1: Generate base player performance data (mock or from API)
    player_names = ["LeBron James", "Stephen Curry", "Luka Doncic"]
    players = summarize_players(player_names)
    player_dicts = [p.model_dump() for p in players]

    # Step 2: Generate trend insights based on performance
    trend_summary = analyze_player_trends(player_dicts)

    # Step 3: Merge everything into one response
    insights = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "insights": []
    }

    # Align player performance with their trend verdict
    for perf in player_dicts:
        trend = next(
            (t for t in trend_summary["summary"] if t["player_name"] == perf["player_name"]),
            {}
        )
        insights["insights"].append({
            "player_name": perf["player_name"],
            "ppg": perf["ppg"],
            "rpg": perf["rpg"],
            "apg": perf["apg"],
            "tpm": perf["tpm"],
            "season_ppg": perf["season_ppg"],
            "season_rpg": perf["season_rpg"],
            "season_apg": perf["season_apg"],
            "trend": perf["trend"],
            "verdict": trend.get("verdict", "N/A")
        })

    return insights


if __name__ == "__main__":
    result = get_player_insights()
    from pprint import pprint
    pprint(result)
