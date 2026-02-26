import sys
import os
import json

# Ensure src in path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

from config import TARGET_DISCORD_CHANNEL_ID
from src.discord_client import DiscordScraper

import asyncio

async def test_discord():
    print(f'Configured Channels: {TARGET_DISCORD_CHANNEL_ID}')
    ds = DiscordScraper()

    if not TARGET_DISCORD_CHANNEL_ID:
        print('Error: no discord channel IDs configured.')
        sys.exit(1)

    discord_ids = [did.strip() for did in TARGET_DISCORD_CHANNEL_ID.split(',') if did.strip()]

    all_msgs = []
    for did in discord_ids:
        print(f'Fetching from {did}...')
        try:
            msgs = await ds.fetch_messages(did, limit=10)
            all_msgs.extend(msgs)
            print(f'Got {len(msgs)} messages')
        except Exception as e:
            print(f'Error fetching {did}: {e}')
        
    print('\nPreview of first 3 messages:')
    for m in all_msgs[:3]:
        print(f"- [{m.get('date')}] {m.get('capper_name', 'Unknown')}: {str(m.get('text', ''))[:50]}...")

if __name__ == '__main__':
    asyncio.run(test_discord())
