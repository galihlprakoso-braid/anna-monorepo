#!/usr/bin/env python3
"""
Update WhatsApp data source instruction in MongoDB.

This script updates the instruction field for WhatsApp Web data sources
to use the correct workflow that calls collect_data INSIDE each chat visit.

Usage:
    cd servers/data
    python scripts/update_whatsapp_instruction.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    # Try parent .env
    env_path = Path(__file__).parent.parent.parent / "agents" / ".env"
load_dotenv(env_path)

from data.core.database import init_db, close_db
from data.models.datasource import DataSourceDocument

# The GOOD instruction (updated, more high-level - tool descriptions handle technical details)
WHATSAPP_INSTRUCTION = """Collect the last 20 messages from each of the last 10 chats on WhatsApp Web.

Output Format (use collect_data tool):
- Format: 'WhatsApp Messages | ContactName → X messages (X/20): [Sender]: message (HH:MM) | ...'
- Identify sender: [User] for your messages (green bubbles), [ContactName] for received (white bubbles)

Example output:
'WhatsApp Messages | PAKE WA → 12 messages (12/20):
[PAKE WA]: Mau esuk ki Mas (05:47) |
[User]: Kok iso boso jowo sisan yo? (10:04) |
[PAKE WA]: Yo e (10:24)'

Workflow:
1. Load the whatsapp-web skill for site-specific guidance
2. For each chat:
   - Open the chat
   - Collect visible messages using collect_data (include count like "12/20")
   - If fewer than 20 messages, scroll up to load older ones
   - Collect newly visible messages
   - Continue until you have ~20 messages per chat
3. Move to the next chat and repeat

Remember: Call collect_data multiple times (once per chat or after each scroll). It does NOT end the task.
"""


async def update_instruction():
    """Update WhatsApp data source instructions."""
    print("Initializing MongoDB connection...")
    await init_db()

    try:
        # Find all WhatsApp data sources
        whatsapp_sources = await DataSourceDocument.find(
            {
                "$or": [
                    {"name": {"$regex": "WhatsApp", "$options": "i"}},
                    {"target_url": {"$regex": "whatsapp", "$options": "i"}}
                ]
            }
        ).to_list()

        if not whatsapp_sources:
            print("❌ No WhatsApp data sources found")
            return

        print(f"Found {len(whatsapp_sources)} WhatsApp data source(s):\n")

        for source in whatsapp_sources:
            print(f"  📋 ID: {source.id}")
            print(f"     Name: {source.name}")
            print(f"     Is template: {source.is_template}")
            current_instruction = source.instruction or ""
            print(f"     Current instruction length: {len(current_instruction)} chars")

            # Check if it has the workflow pattern
            has_good_workflow = "IMPORTANT workflow:" in current_instruction
            has_collect_first = "collect ALL VISIBLE messages FIRST" in current_instruction

            if has_good_workflow and has_collect_first:
                print(f"     ✅ Already has GOOD instruction")
            else:
                print(f"     ❌ Has BAD instruction (missing collect-first pattern)")

        print(f"\n{'='*70}")
        print("Updating all WhatsApp data sources with GOOD instruction...")

        # Update all WhatsApp data sources
        print("\nUpdating instructions...")

        count = 0
        for source in whatsapp_sources:
            source.instruction = WHATSAPP_INSTRUCTION
            await source.save()
            count += 1
            print(f"  ✓ Updated: {source.name} (ID: {source.id})")

        print(f"\n✅ Successfully updated {count} data source(s)")
        print(f"   New instruction length: {len(WHATSAPP_INSTRUCTION)} chars")

        # Verify
        print("\nVerifying updates...")
        updated_sources = await DataSourceDocument.find(
            {
                "$or": [
                    {"name": {"$regex": "WhatsApp", "$options": "i"}},
                    {"target_url": {"$regex": "whatsapp", "$options": "i"}}
                ]
            }
        ).to_list()

        for source in updated_sources:
            instruction = source.instruction or ""
            has_workflow = 'IMPORTANT workflow:' in instruction
            has_collect_first = 'collect ALL VISIBLE messages FIRST' in instruction

            print(f"  ✓ {source.name}")
            print(f"    - Has workflow: {has_workflow}")
            print(f"    - Has collect-first: {has_collect_first}")

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(update_instruction())
