"""
linkedin_service.py — LinkedIn API Integration Service
Handles the 3-step LinkedIn media upload and posting flow.
"""

import json
import logging

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from src.config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR_URN

logger = logging.getLogger(__name__)

# LinkedIn API headers
HEADERS = {
    "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "2024-01",
}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def upload_image_to_linkedin(image_path: str) -> str:
    """
    Registers an upload with LinkedIn, uploads the image binary, and returns the asset URN.

    Step 1: Register the upload to get an upload URL and asset URN.
    Step 2: Upload the image binary data to the provided URL.

    Args:
        image_path: Local file path to the image to upload.

    Returns:
        The LinkedIn asset URN string for the uploaded image.

    Raises:
        requests.HTTPError: If any LinkedIn API call fails after retries.
    """
    # --- Step 1: Register Upload ---
    logger.info("Step 1: Registering image upload with LinkedIn...")

    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_data = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LINKEDIN_AUTHOR_URN,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }

    reg_res = requests.post(register_url, headers=HEADERS, json=register_data, timeout=30)
    reg_res.raise_for_status()
    upload_info = reg_res.json()

    upload_url = upload_info["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = upload_info["value"]["asset"]

    logger.info(f"Upload registered. Asset URN: {asset_urn}")

    # --- Step 2: Upload Image Binary ---
    logger.info("Step 2: Uploading image binary data...")

    with open(image_path, "rb") as file:
        upload_headers = {"Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"}
        upload_res = requests.put(upload_url, headers=upload_headers, data=file, timeout=60)
        upload_res.raise_for_status()

    logger.info("Image uploaded successfully to LinkedIn.")
    return asset_urn


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def create_linkedin_post(text: str, asset_urn: str) -> dict:
    """
    Creates the final UGC post combining the caption text and the uploaded image.

    Step 3: Publish the post with the attached media asset.

    Args:
        text: The full caption text (including hashtags).
        asset_urn: The LinkedIn asset URN from the upload step.

    Returns:
        The LinkedIn API response as a dict.

    Raises:
        requests.HTTPError: If the post creation fails after retries.
    """
    logger.info("Step 3: Creating final LinkedIn post...")

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    post_data = {
        "author": LINKEDIN_AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
                    }
                ],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    res = requests.post(post_url, headers=HEADERS, json=post_data, timeout=30)
    res.raise_for_status()

    post_id = res.headers.get("x-restli-id", "Unknown ID")
    logger.info(f"Post published successfully! Post ID: {post_id}")

    return res.json()
