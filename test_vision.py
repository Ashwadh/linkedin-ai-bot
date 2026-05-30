import sys
import logging
import os
sys.path.append('C:\\Users\\ashwa\\linkedin_ai_bot')
from src.gemini_service import generate_post_content
from src.image_service import fetch_unsplash_image

logging.basicConfig(level=logging.INFO)

print('--- Generating Content via Elite Prompt ---')
content = generate_post_content([])
print('Content Generated:', content)

search_term = content['unsplash_search_term']
image_headline = content.get('image_headline', 'NO HEADLINE')

print('--- Fetching Unsplash Image with Vision Validation ---')
try:
    image_path = fetch_unsplash_image(search_term, image_headline)
    print('Image saved and validated at:', image_path)
except Exception as e:
    print('Failed after retries:', e)
