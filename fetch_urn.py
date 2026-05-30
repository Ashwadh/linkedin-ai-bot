"""
fetch_urn.py — Temporary script to fetch LinkedIn Profile ID and update .env
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    print("ERROR: LINKEDIN_ACCESS_TOKEN not found in .env file.")
    exit(1)

print("Fetching your LinkedIn profile...")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202401",
}

try:
    # Try /v2/me first (classic OAuth apps)
    print("Trying /v2/me endpoint...")
    response = requests.get("https://api.linkedin.com/v2/me", headers=headers, timeout=15)

    if response.status_code == 403:
        # Fallback to /v2/userinfo (newer OpenID Connect apps)
        print("Access denied on /v2/me - trying /v2/userinfo endpoint...")
        response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        profile_id = data.get("sub")  # OpenID uses 'sub' for the unique ID
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Email: {data.get('email', 'N/A')}")
    else:
        response.raise_for_status()
        data = response.json()
        profile_id = data.get("id")

    if not profile_id:
        print("ERROR: 'id' field not found in LinkedIn response.")
        print(f"Full response: {data}")
        exit(1)

    author_urn = f"urn:li:person:{profile_id}"
    print(f"\n[OK] LinkedIn Profile ID: {profile_id}")
    print(f"[OK] Author URN: {author_urn}")

    # Update .env file — replace placeholder or append
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r") as f:
        env_content = f.read()

    if "LINKEDIN_AUTHOR_URN=" in env_content:
        # Replace the existing line (whether placeholder or real value)
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("LINKEDIN_AUTHOR_URN="):
                new_lines.append(f"LINKEDIN_AUTHOR_URN={author_urn}")
            else:
                new_lines.append(line)
        env_content = "\n".join(new_lines) + "\n"
    else:
        env_content += f"\nLINKEDIN_AUTHOR_URN={author_urn}\n"

    with open(env_path, "w") as f:
        f.write(env_content)

    print(f"\n[OK] .env file updated with LINKEDIN_AUTHOR_URN={author_urn}")

except requests.exceptions.HTTPError as e:
    print(f"\nHTTP Error {response.status_code}: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"\nRequest failed: {e}")
