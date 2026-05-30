import sys
import logging
import os
sys.path.append('C:\\Users\\ashwa\\linkedin_ai_bot')
from src.gemini_service import generate_post_content
from src.image_service import fetch_unsplash_image
from src.linkedin_service import upload_image_to_linkedin, create_linkedin_post

logging.basicConfig(level=logging.INFO)

print('--- Generating Content via Elite Prompt ---')
content = generate_post_content([])

search_term = content['unsplash_search_term']
image_headline = content.get('image_headline', 'NO HEADLINE')

print('--- Fetching Unsplash Image ---')
image_path = fetch_unsplash_image(search_term, image_headline)
print('Image saved to:', image_path)

print('--- Uploading to LinkedIn ---')
caption = content['caption']
hashtags = ' '.join(['#' + tag.replace('#', '') for tag in content.get('hashtags', [])])
full_caption = f'{caption}\n\n{hashtags}'.strip()

asset_urn = upload_image_to_linkedin(image_path)
print('Asset URN:', asset_urn)

result = create_linkedin_post(full_caption, asset_urn)
print('Post Result:', result)
