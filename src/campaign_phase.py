"""
campaign_phase.py — 30-Day Campaign Phase Engine
Determines the active campaign phase based on a calendar month cycle.
Days 1-22: Audience Build (Marketing Focus)
Days 23-30+: Harvest (Sales Focus)
"""

import datetime
import json
import logging
import random

logger = logging.getLogger(__name__)


def get_current_campaign_phase() -> dict:
    """
    Determines the active campaign phase based on the current calendar day.
    Returns phase config with allowed types, frameworks, and CTA instructions.
    """
    current_day = datetime.datetime.now().day

    if current_day <= 22:
        phase = {
            "phase": "AUDIENCE_BUILD",
            "day_of_month": current_day,
            "allowed_types": ["Marketing"],
            "allowed_frameworks": [
                "Contrarian Myth-Buster",
                "The How-To Value Drop",
                "The Case Study / Storytelling",
                "BAB"
            ],
            "cta_instruction": (
                "The Call to Action (CTA) MUST drive algorithmic engagement "
                "(saves, shares, deep comment strings). NEVER pitch a service "
                "or ask for a direct message (DM)."
            ),
        }
    else:
        phase = {
            "phase": "HARVEST",
            "day_of_month": current_day,
            "allowed_types": ["Sales"],
            "allowed_frameworks": [
                "PAS",
                "AIDA",
                "The Enemy vs. Hero Framework"
            ],
            "cta_instruction": (
                "The CTA MUST aggressively command an inbound DM with the exact "
                "keyword 'STRATEGY'. Do not ask for comments, likes, or saves."
            ),
        }

    # Force deterministic framework selection at runtime
    phase["selected_framework"] = random.choice(phase["allowed_frameworks"])
    phase["selected_type"] = phase["allowed_types"][0]

    logger.info(
        f"Campaign Phase: {phase['phase']} | "
        f"Day: {current_day} | "
        f"Type: {phase['selected_type']} | "
        f"Framework: {phase['selected_framework']}"
    )

    return phase


def validate_campaign_compliance(content: dict) -> dict:
    """
    Post-generation validation guard. Checks the Gemini output's post_type
    and framework_used against the active phase rules.
    Logs warnings on non-compliance but does not block publishing.
    """
    phase_info = get_current_campaign_phase()

    post_type = content.get("post_type", "")
    framework_used = content.get("framework_used", "")

    if post_type and post_type not in phase_info["allowed_types"]:
        logger.warning(
            f"Compliance Warning: Generated '{post_type}' during "
            f"{phase_info['phase']} phase. Expected: {phase_info['allowed_types']}"
        )

    if framework_used and framework_used not in phase_info["allowed_frameworks"]:
        logger.warning(
            f"Compliance Warning: Framework '{framework_used}' violates "
            f"active phase rules. Expected: {phase_info['allowed_frameworks']}"
        )

    return content
