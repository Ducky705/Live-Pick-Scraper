
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock main.py's environment
from src.utils import clean_text_for_ai
from src.ocr_handler import extract_text_batch

SAMPLES_DIR = Path(__file__).parent.parent / "tests" / "samples"
IMAGES = [str(p) for p in SAMPLES_DIR.glob("*.jpg")][:5] # Use 5 images

def run_simulation():
    print("🚀 Simulating Batch OCR Logic from main.py...")
    
    # create mock messages
    selected_messages = []
    for i, img in enumerate(IMAGES):
        selected_messages.append({
            "id": i,
            "text": f"Msg {i}",
            "image": img,
            "do_ocr": True
        })
        
    print(f"Created {len(selected_messages)} mock messages.")
    
    # --- COPIED LOGIC FROM MAIN.PY (simplified) ---
    all_ocr_tasks = [] 
    
    for i, msg in enumerate(selected_messages):
        msg['ocr_texts'] = []
        images_to_process = [msg['image']] if msg.get('image') else []
        if msg.get('do_ocr') and images_to_process:
            for img_path in images_to_process:
                all_ocr_tasks.append((i, img_path))

    BATCH_SIZE = 32
    if all_ocr_tasks:
        total_batches = (len(all_ocr_tasks) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for b_idx in range(total_batches):
            start = b_idx * BATCH_SIZE
            end = start + BATCH_SIZE
            batch_tasks = all_ocr_tasks[start:end]
            batch_paths = [t[1] for t in batch_tasks]
            
            print(f"Processing Batch {b_idx} with {len(batch_paths)} images...")
            results = extract_text_batch(batch_paths)
            
            for t_idx, text in enumerate(results):
                orig_idx = batch_tasks[t_idx][0]
                if text and not text.startswith("[Error"):
                    cleaned = clean_text_for_ai(text)
                    selected_messages[orig_idx]['ocr_texts'].append(cleaned)
                    print(f"Mapped result to Msg {orig_idx}: {cleaned[:30]}...")
                else:
                    print(f"Error for Msg {orig_idx}: {text}")

    print("\n✅ Simulation Complete.")

if __name__ == "__main__":
    run_simulation()
