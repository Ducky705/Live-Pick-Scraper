
import os
import sys
import json
import time
import logging
import difflib
from pathlib import Path
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from src.vision_one_shot import parse_image_direct

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_similarity(text1, text2):
    """Calculates similarity ratio between two strings (0.0 to 1.0)"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def json_to_text(picks):
    """Converts structured picks back to a text representation for comparison."""
    lines = []
    for p in picks:
        line = f"{p.get('pick', '')} {p.get('odds', '')} ({p.get('units', '')}u)"
        if p.get('capper_name') != "Unknown":
            line = f"{p.get('capper_name')} " + line
        lines.append(line)
    return "\n".join(lines)

def run_benchmark():
    # Load Paths
    dataset_dir = os.path.join(PROJECT_ROOT, 'benchmark', 'dataset')
    map_path = os.path.join(dataset_dir, 'image_map.json')
    golden_path = os.path.join(dataset_dir, 'ocr_golden_set.json')
    
    with open(map_path, 'r', encoding='utf-8') as f:
        image_map = json.load(f)
        
    with open(golden_path, 'r', encoding='utf-8') as f:
        golden_set = json.load(f)
        
    # Process images
    image_keys = list(image_map.keys())
    # Limit to 5 images for quick test, or full set for real bench
    # image_keys = image_keys[:5] 
    
    results = []
    total_time = 0
    total_sim = 0
    
    logging.info(f"Starting One-Shot Vision Benchmark on {len(image_keys)} images...")
    
    for key in image_keys:
        rel_path = image_map[key]
        # Fix path
        p = rel_path.replace('/', os.sep).replace('\\', os.sep)
        if not os.path.isabs(p):
            p = os.path.join(PROJECT_ROOT, p)
            
        if not os.path.exists(p):
            logging.warning(f"File not found: {p}")
            continue
            
        start_t = time.time()
        picks = parse_image_direct(p)
        end_t = time.time()
        
        duration = end_t - start_t
        total_time += duration
        
        # Convert to text for comparison
        generated_text = json_to_text(picks)
        ground_truth = golden_set.get(key, "")
        
        sim = calculate_similarity(generated_text, ground_truth)
        total_sim += sim
        
        logging.info(f"[{key}] Sim: {sim:.4f} | Time: {duration:.2f}s | Picks: {len(picks)}")
        
        results.append({
            "image": key,
            "similarity": round(sim, 4),
            "latency": round(duration, 2),
            "picks_count": len(picks)
        })
        
        # Rate limit protection for free tier
        time.sleep(2) 

    avg_sim = total_sim / len(results) if results else 0
    avg_time = total_time / len(results) if results else 0
    
    print("\n" + "="*40)
    print(f"BENCHMARK RESULTS (One-Shot Vision)")
    print("="*40)
    print(f"Total Images: {len(results)}")
    print(f"Total Time:   {total_time:.2f}s")
    print(f"Avg Time/Img: {avg_time:.2f}s")
    print(f"Avg Similarity: {avg_sim:.4f}")
    print("="*40)
    
    # Save Report
    report_path = os.path.join(PROJECT_ROOT, 'benchmark', 'reports', 'one_shot_vision_results.json')
    with open(report_path, 'w') as f:
        json.dump({
            "summary": {
                "total_images": len(results),
                "avg_time": avg_time,
                "avg_similarity": avg_sim
            },
            "details": results
        }, f, indent=2)

if __name__ == "__main__":
    run_benchmark()
