#!/usr/bin/env python3
"""
Update WhatsApp data source instruction in MongoDB.

This script updates the instruction field for the WhatsApp Web data source
to use the correct workflow that calls collect_data INSIDE each chat visit.

Usage:
    python scripts/update_whatsapp_instruction.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    print("Error: motor package not found. Install it with: uv add motor")
    import sys
    sys.exit(1)

# The GOOD instruction from seed_templates_mongo.py
WHATSAPP_INSTRUCTION = """Collect the last 20 messages from each of the last 10 chats on WhatsApp Web.

Output Format:
- Title: 'WhatsApp Messages'
- For each message, identify sender:
  * [User]: Messages sent by the logged-in user (green bubbles on right)
  * [ContactName]: Messages from the contact/group member (white bubbles on left)
- Format: 'WhatsApp Messages | ContactName → [Sender]: message (HH:MM)'
- Include message count: (X/20 collected)

Example:
'WhatsApp Messages | PAKE WA → 12 messages (12/20):
[PAKE WA]: Mau esuk ki Mas (05:47) |
[User]: Kok iso boso jowo sisan yo? (10:04) |
[PAKE WA]: Yo e (10:24)'

IMPORTANT workflow:
(1) When you open a chat, collect ALL VISIBLE messages FIRST with collect_data (include count),
(2) Count messages. If < 20, scroll up to load older messages,
(3) After scrolling, take screenshot to see new messages,
(4) Collect newly visible messages with collect_data (include updated count),
(5) Repeat until ~20 messages total for this chat,
(6) Move to next chat and repeat.
The collect_data tool does NOT end the task - call it many times.
"""


async def update_whatsapp_instruction():
    """Update the WhatsApp data source instruction in MongoDB."""

    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("Error: MONGODB_URI not found in environment")
        return

    print(f"Connecting to MongoDB...")

    # Connect to MongoDB with SSL parameters
    client = AsyncIOMotorClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True  # For development/testing
    )

    # Extract database name from URI or use default
    # MongoDB URI format: mongodb+srv://user:pass@host/database?options
    db_name = "anna"  # Default database name
    if "/" in mongodb_uri and "?" in mongodb_uri:
        # Extract from URI
        parts = mongodb_uri.split("/")
        if len(parts) > 3:
            db_part = parts[3].split("?")[0]
            if db_part:
                db_name = db_part

    print(f"Using database: {db_name}")
    db = client[db_name]

    try:
        # Find WhatsApp data sources (both template and user-created)
        collection = db["data_sources"]

        # Find all WhatsApp-related data sources
        whatsapp_sources = await collection.find({
            "$or": [
                {"name": {"$regex": "WhatsApp", "$options": "i"}},
                {"target_url": {"$regex": "whatsapp", "$options": "i"}}
            ]
        }).to_list(length=None)

        if not whatsapp_sources:
            print("No WhatsApp data sources found in database")
            return

        print(f"Found {len(whatsapp_sources)} WhatsApp data source(s):")
        for source in whatsapp_sources:
            print(f"  - ID: {source['_id']}")
            print(f"    Name: {source.get('name')}")
            print(f"    Is template: {source.get('is_template', False)}")
            print(f"    Current instruction length: {len(source.get('instruction', ''))} chars")

        # Update all WhatsApp data sources
        print(f"\nUpdating instruction for all WhatsApp data sources...")

        result = await collection.update_many(
            {
                "$or": [
                    {"name": {"$regex": "WhatsApp", "$options": "i"}},
                    {"target_url": {"$regex": "whatsapp", "$options": "i"}}
                ]
            },
            {
                "$set": {
                    "instruction": WHATSAPP_INSTRUCTION
                }
            }
        )

        print(f"✓ Updated {result.modified_count} data source(s)")
        print(f"  New instruction length: {len(WHATSAPP_INSTRUCTION)} chars")

        # Verify update
        print("\nVerifying update...")
        updated_sources = await collection.find({
            "$or": [
                {"name": {"$regex": "WhatsApp", "$options": "i"}},
                {"target_url": {"$regex": "whatsapp", "$options": "i"}}
            ]
        }).to_list(length=None)

        for source in updated_sources:
            instruction = source.get('instruction', '')
            has_workflow = 'IMPORTANT workflow:' in instruction
            has_collect_first = 'collect ALL VISIBLE messages FIRST' in instruction

            print(f"\n  ID: {source['_id']}")
            print(f"  Name: {source.get('name')}")
            print(f"  ✓ Has workflow section: {has_workflow}")
            print(f"  ✓ Has collect-first pattern: {has_collect_first}")

        print("\n✅ Update complete!")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(update_whatsapp_instruction())
