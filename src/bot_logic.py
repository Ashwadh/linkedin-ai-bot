"""
bot_logic.py — Self-Healing Orchestrator Module
Manages post history state, coordinates Gemini content generation,
image creation, LinkedIn publishing, and history persistence.
Incorporates a Week 1 hardcoded ramp-up logic.
"""

import json
import logging
import os
from datetime import datetime

import pytz

from src.gemini_service import generate_post_content
from src.image_service import fetch_unsplash_image
from src.linkedin_service import upload_image_to_linkedin, create_linkedin_post
from src.campaign_phase import get_current_campaign_phase
from src.intelligence_service import gather_daily_intelligence
from src.week_1_content import WEEK_1_POSTS

# --- Configuration ---
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
HISTORY_FILE = os.path.join(ROOT_DIR, "post_history.json")
STATE_FILE = os.path.join(ROOT_DIR, "run_state.json")
MAX_HISTORY_ENTRIES = 15

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================
# STEP 1: STATE MANAGEMENT (MEMORY & EXECUTION)
# =============================================

from google.cloud import storage

BUCKET_NAME = "linkedin-bot-state-project-f189c2da-1cb6-4974-b21"

def _get_gcs_bucket():
    client = storage.Client()
    return client.bucket(BUCKET_NAME)

def read_state() -> dict:
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob("run_state.json")
        if blob.exists():
            return json.loads(blob.download_as_text())
    except Exception as e:
        logger.error(f"Failed to read run_state.json from GCS: {e}")
    return {"current_day": 1}

def write_state(state: dict) -> None:
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob("run_state.json")
        blob.upload_from_string(json.dumps(state, indent=2), content_type="application/json")
    except Exception as e:
        logger.error(f"Failed to write run_state.json to GCS: {e}")

def read_post_history() -> list[dict]:
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob("post_history.json")
        if blob.exists():
            data = json.loads(blob.download_as_text())
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to read post history from GCS: {e}")
    return []

def write_post_history(history: list[dict]) -> None:
    trimmed = history[-MAX_HISTORY_ENTRIES:]
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob("post_history.json")
        blob.upload_from_string(json.dumps(trimmed, indent=2), content_type="application/json")
    except Exception as e:
        logger.error(f"Failed to write post history to GCS: {e}")


def _build_history_record(content: dict) -> dict:
    """Extracts tracked fields from content output."""
    ist_tz = pytz.timezone("Asia/Kolkata")
    return {
        "topic_category": content.get("topic_category", "unknown"),
        "hook_type": content.get("hook_type", "unknown"),
        "target_country": content.get("target_country", "unknown"),
        "post_type": content.get("post_type", "unknown"),
        "framework_used": content.get("framework_used", "unknown"),
        "posted_at": datetime.now(ist_tz).isoformat(),
    }


# =============================================
# STEP 2: ORCHESTRATION PIPELINE
# =============================================

def run_daily_automation() -> dict:
    """
    Orchestrates the complete self-healing LinkedIn publishing pipeline:
    - Checks `current_day`.
    - If 1-6: Uses Hardcoded Week 1 content.
    - If 7: Skips (Rest Day).
    - If > 7: Falls back to Gemini AI generation with Search Grounding.
    """
    try:
        logger.info("=" * 60)
        logger.info("=== LINKEDIN PUBLISHING ENGINE: STARTING ===")
        logger.info("=" * 60)

        # --- Check State ---
        state = read_state()
        current_day = state.get("current_day", 1)
        logger.info(f"Execution Day: {current_day}")

        # --- Log Campaign Phase ---
        phase_info = get_current_campaign_phase()
        logger.info(
            f"Campaign Phase: {phase_info['phase']} | "
            f"Type: {phase_info['selected_type']} | "
            f"Framework: {phase_info['selected_framework']}"
        )

        content = None
        is_rest_day = False

        if current_day <= 6:
            # WEEK 1: Hardcoded Data
            logger.info("Using Week 1 hardcoded content.")
            content = WEEK_1_POSTS[current_day]
            # Ensure hashtags are empty for hardcoded to avoid errors later
            content["hashtags"] = content.get("hashtags", [])
            content["confidence_notes"] = ["Hardcoded Week 1"]

        elif current_day == 7:
            # REST DAY
            logger.info("Day 7 is a rest day. Skipping posting.")
            is_rest_day = True

        else:
            # WEEK 2+: Autonomous Gemini Engine
            logger.info("Using Autonomous Gemini AI Engine.")
            post_history = read_post_history()

            # --- Live Intelligence Ingestion ---
            logger.info("Gathering live intelligence briefing...")
            topic_context = gather_daily_intelligence()
            if topic_context:
                logger.info("Live intelligence acquired. Injecting into generation engine.")
            else:
                logger.info("No live intelligence available. Proceeding with standard generation.")

            content = generate_post_content(post_history, topic_context=topic_context)

        # Update and save the day tracker early in case of later failures
        state["current_day"] = current_day + 1
        write_state(state)

        if is_rest_day:
            return {
                "status": "success",
                "message": "Rest day. No post published.",
                "current_day": current_day
            }

        # --- Parse and Prepare Content ---
        caption = content["caption"]
        # Strip markdown formatting characters (*, **, _) that Gemini may inject
        caption = caption.replace("**", "").replace("*", "").replace("_", " ")
        hashtags_list = content.get("hashtags", [])
        hashtags = " ".join([f"#{tag.strip().replace('#', '')}" for tag in hashtags_list])
        full_caption = f"{caption}\n\n{hashtags}".strip()

        logger.info(f"Topic: {content.get('topic_category')}")
        logger.info(f"Hook: {content.get('hook_type')}")
        logger.info(f"Country: {content.get('target_country')}")

        # --- Generate Image ---
        search_term = content["unsplash_search_term"]
        image_text = content.get("image_headline", content.get("hook_type", "INSIGHT")).replace("_", " ").upper()
        target_country = content.get("target_country", "")
        image_path = fetch_unsplash_image(search_term, image_text, target_country=target_country)

        # --- Upload to LinkedIn ---
        asset_urn = upload_image_to_linkedin(image_path)
        result = create_linkedin_post(full_caption, asset_urn)

        # --- Update Post History ---
        if current_day > 7:
            # Only track autonomous posts in history for Gemini context
            post_history = read_post_history()
            record = _build_history_record(content)
            post_history.append(record)
            write_post_history(post_history)

        # --- Cleanup ---
        if os.path.exists(image_path):
            os.remove(image_path)

        logger.info("=" * 60)
        logger.info("=== PUBLISHING ENGINE: COMPLETED SUCCESSFULLY ===")
        logger.info("=" * 60)

        return {
            "status": "success",
            "message": "Post published to LinkedIn",
            "current_day": current_day,
            "topic_category": content.get("topic_category"),
            "hook_type": content.get("hook_type"),
            "target_country": content.get("target_country"),
            "post_type": content.get("post_type"),
            "framework_used": content.get("framework_used"),
            "campaign_phase": phase_info.get("phase"),
        }

    except Exception as e:
        logger.error(f"Publishing engine failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
