"""
config.py — Configuration & Content Strategy Module
Handles topic rotation, brand context, styles, and environment variables.
"""

import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys & Credentials ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_AUTHOR_URN = os.getenv("LINKEDIN_AUTHOR_URN")
CRON_SECRET_KEY = os.getenv("CRON_SECRET_KEY")

# --- Brand Identity ---
BRAND_CONTEXT = "Unisights"

# --- Content Strategy: Rotating Topics ---
TOPICS = [
    "Study abroad strategies and choosing the right university",
    "Acing Visa interviews (F1, Tier 4, etc.)",
    "Career growth and networking for International students",
    "Leveraging AI tools for academic and professional success",
    "Business growth and tech solutions in the education sector",
    "The financial reality of studying abroad (scholarships, budgeting)",
]

# --- Content Strategy: Rotating Visual Formats ---
STYLES = [
    "Actionable Checklist",
    "Split-screen comparison narrative (Before vs After)",
    "Infographic-style breakdown with clear bullet points",
    "Personal storytelling with a strong hook",
    "Step-by-step technical guide",
]


def get_todays_strategy():
    """
    Uses the current date in IST to deterministically pick a topic and style.
    This ensures no duplicate content on any given day and rotates through
    all combinations over time.
    """
    ist_tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist_tz)
    day_of_year = now.timetuple().tm_yday

    topic = TOPICS[day_of_year % len(TOPICS)]
    style = STYLES[day_of_year % len(STYLES)]

    return topic, style
