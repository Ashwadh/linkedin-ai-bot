import logging
import os
import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)

# Fetch API keys from environment
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_with_retry(search_term: str, hook_text: str, filename: str, target_country: str = "") -> str:
    """
    Downloads an image from Unsplash and overlays the hook_text using Pillow.
    """
    logger.info(f"Fetching Unsplash image for term: '{search_term}'")
    
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY is missing! Using local fallback image.")
        return _use_local_fallback(hook_text, filename)

    url = "https://api.unsplash.com/photos/random"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {
        "query": search_term,
        "orientation": "squarish",
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        image_url = data["urls"]["regular"]
        
        # Download the actual image
        img_response = requests.get(image_url, stream=True, timeout=120)
        if img_response.status_code == 200:
            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
            with open(filename, "wb") as f:
                for chunk in img_response.iter_content(chunk_size=1024):
                    f.write(chunk)
            
            logger.info("Unsplash image downloaded. Validating mood with Vision AI...")
            
            if _evaluate_image_mood(filename, target_country):
                logger.info("Applying text overlay...")
                return _apply_text_overlay(filename, hook_text)
            else:
                os.remove(filename)
                raise Exception("Image rejected by Vision AI due to incorrect mood.")
        else:
            raise Exception(f"Failed to download image file. Status: {img_response.status_code}")
    else:
        logger.error(f"Unsplash API failed. Status: {response.status_code}")
        raise Exception(f"Unsplash API error: {response.status_code}")

def fetch_unsplash_image(search_term: str, hook_text: str, target_country: str = "", filename: str = "/tmp/post_image.jpg") -> str:
    """
    Robust Fallback Protocol for image fetching:
    1. Initial attempt via Unsplash API (with tenacity retries + Vision AI mood check).
    2. If all retries fail, pause 2s and retry the raw API call once more (no mood check).
    3. If that also fails, use a high-quality local fallback image.
    Never returns a solid black placeholder.
    """
    # --- Stage 0: Always attempt "study abroad" first ---
    try:
        logger.info("Stage 0: Attempting primary term 'study abroad' first...")
        return _fetch_with_retry("study abroad", hook_text, filename, target_country)
    except Exception as e:
        logger.warning(f"Stage 0 ('study abroad') failed: {e}. Falling back to topic-specific term.")

    # --- Stage 1: Standard attempt with retries + Vision AI ---
    try:
        return _fetch_with_retry(search_term, hook_text, filename, target_country)
    except Exception as e:
        logger.warning(f"Stage 1 failed after all retries ({e}). Entering Stage 2: Emergency API retry...")

    # --- Stage 2: Emergency retry with 2s pause, skip Vision AI ---
    import time
    time.sleep(2)
    try:
        logger.info(f"Stage 2: Retrying Unsplash API for term: '{search_term}' (skipping Vision AI)...")
        if UNSPLASH_ACCESS_KEY:
            url = "https://api.unsplash.com/photos/random"
            headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
            params = {"query": search_term, "orientation": "squarish"}
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                image_url = data["urls"]["regular"]
                img_response = requests.get(image_url, stream=True, timeout=120)
                if img_response.status_code == 200:
                    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
                    with open(filename, "wb") as f:
                        for chunk in img_response.iter_content(chunk_size=1024):
                            f.write(chunk)
                    logger.info("Stage 2: Unsplash image downloaded (Vision AI skipped). Applying overlay...")
                    return _apply_text_overlay(filename, hook_text)
            logger.warning(f"Stage 2: Unsplash API returned status {response.status_code}.")
        else:
            logger.warning("Stage 2: No UNSPLASH_ACCESS_KEY available.")
    except Exception as e2:
        logger.warning(f"Stage 2 also failed ({e2}). Entering Stage 3: Local fallback...")

    # --- Stage 3: Emergency local fallback (high-quality professional image) ---
    logger.info("Stage 3: Using local professional fallback image.")
    return _use_local_fallback(hook_text, filename)


def _evaluate_image_mood(image_path: str, target_country: str = "") -> bool:
    """
    Passes the downloaded image to Gemini 2.5 Flash to ensure it matches
    the required emotional mood (pressure, uncertainty, etc.).
    """
    if not GEMINI_API_KEY:
        return True

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        sample_file = genai.upload_file(path=image_path)

        prompt = (
            "You are a strict image quality gatekeeper for a premium LinkedIn study abroad consultancy brand. "
            "Analyze this image and answer YES or NO to EACH question below:\n\n"
            "RELEVANCE GATE (MOST CRITICAL):\n"
            "1. Is this image completely UNRELATED to education, careers, universities, immigration, professional work, travel, or urban environments? "
            "(Examples of UNRELATED: product photos, beauty/skincare/hair products, food/drinks, animals, fashion, home decor, selfies, entertainment, sports, nature close-ups, retail items, cosmetics, medical products) "
            "If the image shows ANY commercial product, personal care item, consumer good, or anything not connected to education/careers/immigration, answer YES.\n\n"
            "QUALITY CHECKS:\n"
            "2. Does it look touristy, cheerful, random, scenic, lifestyle-focused, or contain vacation aesthetics? "
            "3. Does it look like fantasy art, cartoon visuals, AI-generated textures, unrealistic faces, illustrations, or meme styles? "
            "4. Does the image contain chess pieces, chess boards, or board games? "
            "5. Does the image look generic or lack a strong narrative focus? "
            "6. Is the image blurry, low-resolution, poorly composed, poorly lit, or visually unappealing? "
            "7. Is the image a close-up of an object (laptop, coffee, notebook, bottle, product) rather than an environment or scene? "
            "8. Does the image show a tourist landmark like the Brooklyn Bridge, Eiffel Tower, Statue of Liberty, or Big Ben? "
            "\nIf YES to ANY of the above (especially question 1), you MUST output exactly REJECT. "
        )
        if target_country:
            prompt += (
                f"\nCOUNTRY LANDMARK VALIDATION: The target country is {target_country}. "
                "Verify that visible landmarks, flags, architecture, and cultural symbols belong to this country. "
                "If the post is about Germany, do NOT use UK landmarks, Big Ben, or the London skyline. "
                f"If the landmark does not match {target_country}, or if there is a famous landmark that isn't unquestionably associated with {target_country}, output exactly REJECT. "
            )
        prompt += (
            "\nThe image MUST be relevant to education, careers, immigration, or professional environments. "
            "It must look premium, high-resolution, and professionally composed — suitable for a top-tier LinkedIn consultancy brand. "
            "ONLY if the image passes ALL checks above AND is clearly related to education/careers/immigration/professional environments, output exactly PASS."
        )
        
        response = model.generate_content([prompt, sample_file])
        genai.delete_file(sample_file.name)

        result = response.text.strip().upper()
        if "REJECT" in result:
            logger.info("Vision AI rejected the image for being too cheerful/touristy.")
            return False

        logger.info("Vision AI approved the image mood.")
        return True
    except Exception as e:
        logger.warning(f"Vision evaluation failed (defaulting to PASS): {e}")
        return True


import textwrap

def _apply_text_overlay(image_path: str, text: str) -> str:
    """
    Applies high-contrast, stroke-bordered text to the upper-middle (30% from top) of the image.
    Optimized for LinkedIn Mobile with large 15% side margins.
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size

        draw = ImageDraw.Draw(img)

        font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Roboto-Bold.ttf")

        # Increase font size for "BIG bold typography" (approx 9% of width)
        font_size = int(width * 0.09)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logger.warning(f"Failed to load TrueType font, using default. Error: {e}")
            font = ImageFont.load_default()

        text_to_draw = text.upper().strip()

        # We want large safe margins (15% on each side -> 70% available width)
        max_text_width = int(width * 0.70)

        # Wrap text to fit max_text_width
        avg_char_width = font_size * 0.6  # typical for sans-serif caps
        chars_per_line = max(1, int(max_text_width / avg_char_width))
        wrapped_lines = textwrap.wrap(text_to_draw, width=chars_per_line)

        # Position: upper-middle (30% from top)
        current_y = height * 0.30

        stroke_width = max(3, int(font_size * 0.06))
        stroke_color = "black"
        text_color = "white"

        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]

            # Center horizontally
            x = (width - line_width) / 2

            draw.text(
                (x, current_y),
                line,
                font=font,
                fill=text_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
            # Move down for next line, add a little line spacing
            current_y += line_height * 1.2

        final_img = img.convert("RGB")
        final_img.save(image_path, quality=95)

        logger.info("Text overlay applied successfully.")
        return image_path

    except Exception as e:
        logger.error(f"Failed to apply text overlay: {e}")
        return image_path


def _use_local_fallback(text: str, filename: str) -> str:
    """
    Uses a high-quality, pre-stored professional image as the emergency fallback.
    Falls back to a dark gradient placeholder only if the local file is also missing.
    """
    fallback_path = os.path.join(os.path.dirname(__file__), "static", "fallback_professional_background.jpg")

    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    if os.path.exists(fallback_path):
        logger.info(f"Local fallback image found at: {fallback_path}")
        # Copy the fallback to the target filename and resize to 1080x1080
        try:
            img = Image.open(fallback_path).convert("RGB")
            img = img.resize((1080, 1080), Image.LANCZOS)
            img.save(filename, quality=95)
            return _apply_text_overlay(filename, text)
        except Exception as e:
            logger.error(f"Failed to process local fallback image: {e}")

    # Last resort: dark gradient (never solid black)
    logger.warning("Local fallback image not found. Generating dark gradient placeholder.")
    img = Image.new('RGB', (1080, 1080))
    draw = ImageDraw.Draw(img)
    for y in range(1080):
        shade = int(20 + (y / 1080) * 30)  # gradient from rgb(20,20,20) to rgb(50,50,50)
        draw.line([(0, y), (1080, y)], fill=(shade, shade, shade))
    img.save(filename, quality=95)
    return _apply_text_overlay(filename, text)

