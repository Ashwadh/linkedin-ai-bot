"""
intelligence_service.py — Live Intelligence Ingestion Module
Performs daily targeted web searches across rotating macroeconomic pillars
to feed real-time news context into the content generation engine.
"""

import logging
import json
from datetime import datetime

import google.generativeai as genai

from src.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# --- The 4 rotating macroeconomic pillars ---
INTELLIGENCE_PILLARS = [
    {
        "name": "Visa & Immigration Policy",
        "search_prompt": (
            "Search for the most recent and impactful visa and immigration policy changes "
            "from the last 7 days affecting international students. Focus on: "
            "US H1-B/F1 visa updates, UK Post-Study Work (PSW) rule changes, "
            "Canadian PGWP or study permit announcements, Australia skilled migration updates, "
            "France/Germany or EU Schengen/Blue Card policy shifts. "
            "Prioritize news from highly authoritative sources: Reuters, Bloomberg, "
            "PIE News, official government immigration portals, IRCC, USCIS, GOV.UK."
        ),
    },
    {
        "name": "Global Job Market Data",
        "search_prompt": (
            "Search for the most recent global job market news from the last 7 days "
            "relevant to international students and graduates. Focus on: "
            "tech hiring surges or freezes, STEM talent shortages, "
            "corporate layoffs in major hubs (Silicon Valley, London, Paris, Berlin, Melbourne), "
            "new employer sponsorship trends, AI job market disruption, "
            "salary benchmarks for international graduates. "
            "Prioritize news from: LinkedIn Economic Graph, Bloomberg, Financial Times, "
            "TechCrunch, Indeed Hiring Lab, Glassdoor."
        ),
    },
    {
        "name": "Currency & Financial Shifts",
        "search_prompt": (
            "Search for the most recent financial news from the last 7 days "
            "affecting Indian students planning to study abroad. Focus on: "
            "INR exchange rate fluctuations against USD/GBP/EUR/AUD/CAD, "
            "rising international tuition costs at major universities, "
            "changes to Indian education loan interest rates (SBI, HDFC Credila), "
            "scholarship funding changes, cost-of-living shifts in student cities. "
            "Prioritize news from: RBI, Bloomberg, Moneycontrol, Economic Times, "
            "university financial aid announcements."
        ),
    },
    {
        "name": "Geopolitical Student Sentiment",
        "search_prompt": (
            "Search for the most recent reports from the last 7 days on "
            "international student enrollment trends, housing crises in popular student destinations, "
            "university funding cuts, anti-immigration sentiment affecting students, "
            "new bilateral education agreements, student safety concerns, "
            "shifts in student destination preferences (e.g., students choosing Germany over UK). "
            "Prioritize news from: ICEF Monitor, PIE News, QS, Times Higher Education, "
            "Study International, government education department announcements."
        ),
    },
]


def _get_daily_pillar() -> dict:
    """
    Selects today's intelligence pillar based on day-of-month rotation.
    Cycles through 4 pillars: day 1 -> pillar 0, day 2 -> pillar 1, etc.
    """
    day = datetime.now().day
    pillar_index = (day - 1) % len(INTELLIGENCE_PILLARS)
    pillar = INTELLIGENCE_PILLARS[pillar_index]
    logger.info(f"Intelligence Pillar for Day {day}: {pillar['name']} (index {pillar_index})")
    return pillar


def gather_daily_intelligence() -> str:
    """
    Executes a targeted web search using Gemini + Google Search Grounding
    to retrieve the day's top news for the active macroeconomic pillar.

    Returns:
        A structured topic_context string containing the factual news update
        and instructions for how to use it in content generation.
    """
    pillar = _get_daily_pillar()

    logger.info(f"Gathering live intelligence for pillar: {pillar['name']}...")

    if not GEMINI_API_KEY:
        logger.warning("No GEMINI_API_KEY found. Returning empty intelligence context.")
        return ""

    try:
        # Initialize Gemini with Google Search Grounding for real-time data
        google_search_tool = genai.protos.Tool(
            google_search=genai.protos.Tool.GoogleSearch()
        )

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[google_search_tool],
            generation_config={
                "temperature": 0.3,  # Low temperature for factual extraction
            },
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            },
        )

        extraction_prompt = f"""
You are a research analyst for a premium study abroad consultancy.

TODAY'S INTELLIGENCE PILLAR: {pillar['name']}

SEARCH TASK:
{pillar['search_prompt']}

EXTRACTION RULES:
1. Find the TOP 1-2 most impactful, specific news updates from the last 7 days.
2. For each update, extract:
   - The core factual claim (e.g., "Canada announces 35% reduction in international student permits for 2026")
   - The source and approximate date
   - Which countries are affected
   - Why this matters for Indian students specifically
3. Do NOT include opinions, predictions, or analysis — only verified facts.
4. If no major news is found in the last 7 days, expand to the last 30 days.
5. If still nothing, provide the most relevant ongoing policy or trend.

OUTPUT FORMAT:
Return your response as a concise intelligence briefing in this exact format:

INTELLIGENCE PILLAR: {pillar['name']}
DATE: {datetime.now().strftime('%Y-%m-%d')}

UPDATE 1:
HEADLINE: [One-line factual headline]
SOURCE: [Publication name, approximate date]
COUNTRIES AFFECTED: [List]
IMPACT ON INDIAN STUDENTS: [1-2 sentences]

UPDATE 2 (if available):
HEADLINE: [One-line factual headline]
SOURCE: [Publication name, approximate date]
COUNTRIES AFFECTED: [List]
IMPACT ON INDIAN STUDENTS: [1-2 sentences]

Keep total output under 200 words. Be specific. No fluff.
"""

        response = model.generate_content(extraction_prompt)
        intelligence_text = response.text.strip()

        if not intelligence_text:
            logger.warning("Intelligence search returned empty response.")
            return ""

        logger.info(f"Intelligence gathered successfully ({len(intelligence_text)} chars)")
        logger.info(f"Intelligence preview: {intelligence_text[:200]}...")

        # Wrap with generation instructions
        topic_context = f"""
━━━━━━━━━━━━━━━━━━
LIVE INTELLIGENCE BRIEFING (USE THIS AS YOUR POST FOUNDATION)
━━━━━━━━━━━━━━━━━━

{intelligence_text}

━━━━━━━━━━━━━━━━━━
INTELLIGENCE USAGE INSTRUCTIONS
━━━━━━━━━━━━━━━━━━

You MUST use the above live news update as the foundational hook or proof point for today's post.
- If in AUDIENCE_BUILD phase: Use the news to educate the market, bust a myth, or provide a strategic workaround to the new policy/development.
- If in HARVEST phase: Use the news as the "Problem" or "Agitation" trigger to create urgency, proving that relying on outdated agency advice is now financially dangerous, and demand they DM you for a pivot strategy.

The post must reference or be directly inspired by the factual update above. Do NOT ignore this intelligence and write a generic post.
"""

        return topic_context

    except Exception as e:
        logger.error(f"Intelligence gathering failed: {e}", exc_info=True)
        logger.info("Falling back to standard generation without live intelligence.")
        return ""
