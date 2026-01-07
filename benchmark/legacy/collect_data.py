"""
Benchmark Data Collector
Fetches 30 images + captions from a Telegram channel for benchmarking.
Selects from the MIDDLE of the day's posts (not beginning or end).
"""

import os
import sys
import json
import asyncio
import shutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.telegram_client import tg_manager

# Configuration
CHANNEL_ID = 1001900292133
TARGET_COUNT = 30  # Number of images to collect
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dataset_v2')

async def collect_benchmark_data(target_date=None):
    """
    Collects benchmark data from the specified Telegram channel.
    Gets messages from the MIDDLE of the day's posts.
    """
    print(f"📡 Connecting to Telegram...")
    
    # Connect
    connected = await tg_manager.connect_client()
    if not connected:
        print("❌ Not authorized. Please run the main app first to authenticate.")
        return
    
    print(f"✅ Connected!")
    
    # Use today's date if not specified
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Fetching messages from channel {CHANNEL_ID} for date: {target_date}")
    
    # Fetch messages
    messages = await tg_manager.fetch_messages([str(CHANNEL_ID)], target_date)
    
    print(f"📨 Found {len(messages)} messages")
    
    # Filter messages with images
    msgs_with_images = [m for m in messages if m.get('images') or m.get('image')]
    print(f"🖼️ Messages with images: {len(msgs_with_images)}")
    
    if len(msgs_with_images) < TARGET_COUNT:
        print(f"⚠️ Not enough images! Need {TARGET_COUNT}, found {len(msgs_with_images)}")
        print("Consider fetching from a different date or channel.")
        return
    
    # Select from the MIDDLE of the day's posts
    total = len(msgs_with_images)
    start_idx = (total - TARGET_COUNT) // 2
    end_idx = start_idx + TARGET_COUNT
    
    selected = msgs_with_images[start_idx:end_idx]
    print(f"📌 Selected {len(selected)} messages from index {start_idx} to {end_idx}")
    
    # Create output directory
    images_dir = os.path.join(OUTPUT_DIR, 'images')
    os.makedirs(images_dir, exist_ok=True)
    
    # Collect data
    benchmark_data = []
    
    for idx, msg in enumerate(selected):
        msg_id = msg.get('id')
        caption = msg.get('text', '')
        
        # Get image paths
        images = []
        if msg.get('images') and isinstance(msg['images'], list):
            images = msg['images']
        elif msg.get('image'):
            images = [msg['image']]
        
        # Copy first image to benchmark dataset
        if images:
            src_path = images[0]
            if src_path.startswith('/static/temp_images/'):
                # Convert web path to file path
                filename = src_path.split('/')[-1]
                src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'static', 'temp_images', filename)
            
            # New filename
            new_filename = f"benchmark_{idx+1:03d}.jpg"
            dst_path = os.path.join(images_dir, new_filename)
            
            try:
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f"  ✅ {new_filename} <- msg {msg_id}")
                else:
                    print(f"  ⚠️ Source not found: {src_path}")
                    new_filename = None
            except Exception as e:
                print(f"  ❌ Error copying: {e}")
                new_filename = None
        else:
            new_filename = None
        
        benchmark_data.append({
            "id": idx + 1,
            "original_msg_id": msg_id,
            "image": new_filename,
            "caption": caption,
            "date": target_date
        })
    
    # Save metadata
    metadata_path = os.path.join(OUTPUT_DIR, 'benchmark_metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump({
            "channel_id": CHANNEL_ID,
            "date": target_date,
            "total_messages": len(messages),
            "messages_with_images": len(msgs_with_images),
            "selected_range": f"{start_idx}-{end_idx}",
            "data": benchmark_data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Benchmark data saved to {OUTPUT_DIR}")
    print(f"   - {len([d for d in benchmark_data if d['image']])} images")
    print(f"   - Metadata: {metadata_path}")
    
    return benchmark_data

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Collect benchmark data from Telegram')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    
    asyncio.run(collect_benchmark_data(args.date))

if __name__ == "__main__":
    main()
