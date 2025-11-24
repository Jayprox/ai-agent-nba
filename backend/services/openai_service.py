# backend/services/openai_service.py
import os
import logging
from datetime import datetime, timezone
from openai import OpenAI, OpenAIError

# -------------------------------------------------
# 🧠 Logging setup
# -------------------------------------------------
logger = logging.getLogger("openai_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

LOG_AI_RAW = os.getenv("LOG_AI_RAW", "0") == "1"

# -------------------------------------------------
# 🧩 OpenAI client setup
# -------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY")
client = None

if api_key:
    try:
        client = OpenAI(api_key=api_key)
        logger.info("✅ OpenAI client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {e}")
else:
    logger.warning("⚠️ No OPENAI_API_KEY found — AI generation disabled")

# -------------------------------------------------
# 🧠 Generate narrative summary
# -------------------------------------------------
def generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
    """
    Generate a narrative summary for NBA data using OpenAI or a fallback template.
    """

    # 🧩 Template fallback (used for mock/testing)
    fallback_template = {
        "macro_summary": (
            "The current NBA landscape shows notable player performances "
            "and evolving team dynamics across recent games."
        ),
        "micro_summary": {"key_edges": [], "risk_score": 0.0},
        "analyst_takeaway": (
            "Monitor shifts in player efficiency and team pace for upcoming matchups."
        ),
        "confidence_summary": ["Medium"],
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": "NBA_Template_Fallback"
        },
    }

    # If AI mode is disabled or client unavailable
    if mode != "ai" or client is None:
        if LOG_AI_RAW:
            logger.info("🧩 [Fallback] Using template summary (no AI client or mode=template).")
        return fallback_template

    try:
        # -------------------------------------------------
        # 🧠 Construct AI prompt
        # -------------------------------------------------
        prompt_text = (
            "You are an expert NBA analyst. Analyze the following JSON summary "
            "data for player and team trends, then produce a 3-part narrative summary "
            "in Markdown format with sections: Macro Summary, Key Edges, and Analyst Takeaway.\n\n"
            f"Data:\n{data}"
        )

        if LOG_AI_RAW:
            logger.info(f"🧠 [AI] Prompt generated (length={len(prompt_text)} chars)")

        # -------------------------------------------------
        # 🚀 Call OpenAI API
        # -------------------------------------------------
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert NBA data analyst."},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.7,
            max_tokens=800,
        )

        ai_text = response.choices[0].message.content.strip()

        if LOG_AI_RAW:
            logger.info(f"🧠 [AI] Response received (length={len(ai_text)} chars)")

        return {
            "macro_summary": ai_text,
            "micro_summary": {"key_edges": [], "risk_score": 0.5},
            "analyst_takeaway": "Generated successfully via OpenAI.",
            "confidence_summary": ["High"],
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": "NBA_Data_Analyst-v1.0",
            },
        }

    except OpenAIError as e:
        logger.error(f"❌ OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected AI generation error: {e}")

    # -------------------------------------------------
    # 🧩 Fallback if anything fails
    # -------------------------------------------------
    fallback_template["metadata"]["model"] = "AI_Fallback_Mode"
    fallback_template["metadata"]["error"] = "AI generation failed — fallback used."
    return fallback_template


# -------------------------------------------------
# 🧪 Direct test mode (for local debug)
# -------------------------------------------------
if __name__ == "__main__":
    sample_data = {"player_trends": [], "team_trends": [], "odds": {"games": []}}
    print(generate_narrative_summary(sample_data, mode="ai"))
