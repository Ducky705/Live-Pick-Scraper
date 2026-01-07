"""
Fixed Benchmark Runner
All pipelines use AI Parser - only OCR method differs:
- Pipeline A: Old Tesseract OCR → AI Parser
- Pipeline B: Tesseract + V3 OCR → AI Parser  
- Pipeline C: AI Vision OCR → AI Parser
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BENCHMARK_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_DIR = os.path.join(BENCHMARK_DIR, 'dataset_v2')
IMAGES_DIR = os.path.join(DATASET_DIR, 'images')
GOLDEN_SET_PATH = os.path.join(DATASET_DIR, 'golden_set.json')
METADATA_PATH = os.path.join(DATASET_DIR, 'benchmark_metadata.json')
REPORTS_DIR = os.path.join(BENCHMARK_DIR, 'reports')
CHARTS_DIR = os.path.join(BENCHMARK_DIR, 'charts')

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

def get_captions():
    """Load captions from metadata."""
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    return {d['image']: d.get('caption', '') for d in metadata.get('data', [])}

def run_ai_parser(ocr_results, captions):
    """Run AI parser on OCR text to extract picks in batches."""
    from src.prompt_builder import generate_ai_prompt
    from src.openrouter_client import openrouter_completion
    
    images = sorted(ocr_results.keys())
    all_results = {img: [] for img in images}
    
    # Process in batches of 5 images to avoid output token limits
    BATCH_SIZE = 5
    
    for i in range(0, len(images), BATCH_SIZE):
        batch_images = images[i:i+BATCH_SIZE]
        print(f"    Processing batch {i//BATCH_SIZE + 1}/{(len(images)+BATCH_SIZE-1)//BATCH_SIZE}...")
        
        # Build messages for this batch
        mock_messages = []
        id_map = {}
        
        for idx, img_file in enumerate(batch_images):
            # Unique ID structure to prevent overlap
            msg_id = 10000 + i + idx
            id_map[msg_id] = img_file
            ocr_text = ocr_results.get(img_file, '')
            caption = captions.get(img_file, '')
            
            mock_messages.append({
                "id": msg_id,
                "text": caption,
                "ocr_text": ocr_text,
                "ocr_texts": [ocr_text] if ocr_text else []
            })
        
        # Generate prompt and call AI
        master_prompt = generate_ai_prompt(mock_messages)
        
        try:
            # Use a model with larger output context if possible, or standard
            ai_response = openrouter_completion(master_prompt, model="google/gemma-3-12b-it:free")
            ai_data = json.loads(ai_response)
            picks = ai_data.get('picks', []) if isinstance(ai_data, dict) else ai_data
            
            # Map picks back to images
            for p in picks:
                pid = p.get('id')
                if pid and pid in id_map:
                    all_results[id_map[pid]].append(p)
                    
        except Exception as e:
            print(f"    ❌ Batch Error: {e}")
            # Continue to next batch
            
    return all_results

# ==================== PIPELINE A ====================
def run_pipeline_a():
    """Old Tesseract OCR → AI Parser."""
    print("\n📌 Pipeline A: Old Tesseract → AI Parser")
    
    from src.ocr_handler import extract_text_simple_tesseract
    
    captions = get_captions()
    images = sorted([f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg')])
    
    # Step 1: OCR
    print("  OCR phase...")
    ocr_results = {}
    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        ocr_results[img_file] = extract_text_simple_tesseract(img_path)
    
    # Step 2: AI Parser
    print("  AI Parser phase...")
    picks = run_ai_parser(ocr_results, captions)
    
    return picks, "Pipeline A: Tesseract → AI"

# ==================== PIPELINE B ====================
def run_pipeline_b():
    """Tesseract + V3 OCR → AI Parser."""
    print("\n📌 Pipeline B: Tesseract V3 → AI Parser")
    
    from src.ocr_handler import extract_text_v3
    
    captions = get_captions()
    images = sorted([f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg')])
    
    # Step 1: OCR
    print("  OCR phase...")
    ocr_results = {}
    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        ocr_results[img_file] = extract_text_v3(img_path)
    
    # Step 2: AI Parser
    print("  AI Parser phase...")
    picks = run_ai_parser(ocr_results, captions)
    
    return picks, "Pipeline B: Tesseract+V3 → AI"

# ==================== PIPELINE C ====================
def run_pipeline_c():
    """AI Vision OCR → AI Parser (production)."""
    print("\n📌 Pipeline C: AI Vision → AI Parser")
    
    from src.ocr_handler import extract_text_batch
    from src.utils import clean_text_for_ai
    
    captions = get_captions()
    images = sorted([f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg')])
    
    # Step 1: AI OCR
    print("  AI OCR phase...")
    ocr_results = {}
    BATCH_SIZE = 4
    
    for i in range(0, len(images), BATCH_SIZE):
        batch = images[i:i+BATCH_SIZE]
        batch_paths = [os.path.join(IMAGES_DIR, f) for f in batch]
        
        try:
            texts = extract_text_batch(batch_paths)
            for idx, img_file in enumerate(batch):
                raw_text = texts[idx]
                if not raw_text:
                    print(f"    ⚠️ Warning: Empty text for {img_file}")
                elif "[Error:" in raw_text:
                    print(f"    ❌ Error text for {img_file}: {raw_text[:100]}")
                
                ocr_results[img_file] = clean_text_for_ai(raw_text) if raw_text else ""
        except Exception as e:
            print(f"    ❌ Batch error (indices {i}-{i+BATCH_SIZE}): {e}")
            for img_file in batch:
                ocr_results[img_file] = ""
    
    # Step 2: AI Parser
    print("  AI Parser phase...")
    picks = run_ai_parser(ocr_results, captions)
    
    return picks, "Pipeline C: AI Vision → AI"

# ==================== SCORING ====================
def normalize_type(t):
    """Normalize type for comparison."""
    if not t:
        return ""
    t = t.upper().strip()
    t = t.replace(' ', '_')  # "PLAYER PROP" -> "PLAYER_PROP"
    # Map common variations
    mapping = {
        'MONEYLINE': 'MONEYLINE',
        'ML': 'MONEYLINE',
        'SPREAD': 'SPREAD',
        'TOTAL': 'TOTAL',
        'OVER': 'TOTAL',
        'UNDER': 'TOTAL',
        'PLAYER_PROP': 'PLAYER_PROP',
        'PLAYERPROP': 'PLAYER_PROP',
        'PROP': 'PLAYER_PROP',
        'PARLAY': 'PARLAY',
        'TEASER': 'TEASER',
        'GAME_PROP': 'GAME_PROP',
        'TEAM_PROP': 'TEAM_PROP',
    }
    return mapping.get(t, t)

def normalize_pick(pick_str):
    """Normalize a pick string for comparison."""
    if not pick_str:
        return ""
    s = pick_str.lower().strip()
    s = ' '.join(s.split())
    # Remove common noise
    s = s.replace('/', ' vs ').replace(' o ', ' over ').replace(' u ', ' under ')
    s = s.replace('%', '.5')  # OCR error: -10% -> -10.5
    s = s.replace('½', '.5')
    # Remove team city prefixes
    for city in ['los angeles ', 'new york ', 'new orleans ', 'kansas city ', 
                 'san francisco ', 'green bay ', 'tampa bay ', 'las vegas ',
                 'new england ', 'minnesota ', 'pittsburgh ', 'baltimore ',
                 'cleveland ', 'cincinnati ', 'houston ', 'denver ', 'chicago ',
                 'detroit ', 'washington ', 'indianapolis ', 'tennessee ',
                 'jacksonville ', 'atlanta ', 'miami ', 'buffalo ', 'philadelphia ',
                 'dallas ', 'arizona ', 'seattle ', 'memphis ', 'brooklyn ']:
        s = s.replace(city, '')
    return s

def extract_numbers(s):
    """Extract numbers from a string for comparison."""
    import re
    return set(re.findall(r'-?\d+\.?\d*', s))

def fuzzy_match(gt_pick, sys_pick, gt_type, sys_type):
    """Check if picks are a fuzzy match."""
    # Type must match (normalized)
    if normalize_type(gt_type) != normalize_type(sys_type):
        return False
    
    gt_norm = normalize_pick(gt_pick)
    sys_norm = normalize_pick(sys_pick)
    
    # Exact match after normalization
    if gt_norm == sys_norm:
        return True
    
    # Check if key numbers match (spread/total values)
    gt_nums = extract_numbers(gt_pick)
    sys_nums = extract_numbers(sys_pick)
    if gt_nums and gt_nums == sys_nums:
        # Numbers match, check if there's word overlap
        gt_words = set(gt_norm.split())
        sys_words = set(sys_norm.split())
        overlap = len(gt_words.intersection(sys_words))
        if overlap >= 1:  # At least 1 word overlap + same numbers = match
            return True
    
    return False

def calculate_score(pipeline_results, golden_set, pipeline_name, debug=False):
    """Calculate precision, recall, F1 with fuzzy matching."""
    total_gt = 0
    total_sys = 0
    correct = 0
    
    debug_info = []
    
    for img_file, gt_picks in golden_set.items():
        sys_picks = pipeline_results.get(img_file, [])
        
        matched_gt = set()
        matched_sys = set()
        
        for gi, gp in enumerate(gt_picks):
            gt_pick = gp.get('pick', '')
            gt_type = gp.get('type', '')
            
            for si, sp in enumerate(sys_picks):
                if si in matched_sys:
                    continue
                sys_pick = sp.get('p') or sp.get('pick') or ''
                sys_type = sp.get('ty') or sp.get('type') or ''
                
                if fuzzy_match(gt_pick, sys_pick, gt_type, sys_type):
                    matched_gt.add(gi)
                    matched_sys.add(si)
                    break
        
        total_gt += len(gt_picks)
        total_sys += len(sys_picks)
        correct += len(matched_gt)
        
        if debug and (len(gt_picks) > 0 or len(sys_picks) > 0):
            debug_info.append({
                "image": img_file,
                "gt_count": len(gt_picks),
                "sys_count": len(sys_picks),
                "matches": len(matched_gt)
            })
    
    precision = (correct / total_sys) if total_sys > 0 else 0
    recall = (correct / total_gt) if total_gt > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    if debug:
        print(f"\n  DEBUG - First 5 images:")
        for d in debug_info[:5]:
            print(f"    {d['image']}: GT={d['gt_count']} SYS={d['sys_count']} Match={d['matches']}")
    
    return {
        "pipeline": pipeline_name,
        "total_gt_picks": total_gt,
        "total_sys_picks": total_sys,
        "correct_matches": correct,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }


# ==================== CHARTS ====================
def generate_charts(results):
    """Generate comparison bar charts."""
    import matplotlib.pyplot as plt
    import numpy as np
    
    pipelines = [r['pipeline'].split(':')[0] for r in results]
    precision = [r['precision'] * 100 for r in results]
    recall = [r['recall'] * 100 for r in results]
    f1 = [r['f1_score'] * 100 for r in results]
    
    x = np.arange(len(pipelines))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width, precision, width, label='Precision', color='#4CAF50')
    bars2 = ax.bar(x, recall, width, label='Recall', color='#2196F3')
    bars3 = ax.bar(x + width, f1, width, label='F1 Score', color='#FF9800')
    
    ax.set_ylabel('Score (%)')
    ax.set_title('OCR Pipeline Comparison - Pick Extraction Accuracy')
    ax.set_xticks(x)
    ax.set_xticklabels(pipelines)
    ax.legend()
    ax.set_ylim(0, 100)
    
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height:.1f}%',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    chart_path = os.path.join(CHARTS_DIR, 'pipeline_comparison.png')
    plt.savefig(chart_path, dpi=150)
    plt.close()
    
    print(f"\n📊 Chart saved: {chart_path}")

# ==================== MAIN ====================
def run_benchmark(pipelines_to_run=['A', 'B', 'C']):
    print("=" * 60)
    print("🏁 BENCHMARK: OCR Pipeline Comparison")
    print("=" * 60)
    
    # Load golden set
    with open(GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        golden_set = json.load(f)
    
    total_gt_picks = sum(len(v) for v in golden_set.values())
    print(f"📋 Golden Set: {len(golden_set)} images, {total_gt_picks} picks")
    
    all_results = []
    
    if 'A' in pipelines_to_run:
        try:
            picks_a, name_a = run_pipeline_a()
            score_a = calculate_score(picks_a, golden_set, name_a, debug=True)
            all_results.append(score_a)
            print(f"  ✅ {name_a}: P={score_a['precision']:.1%} R={score_a['recall']:.1%} F1={score_a['f1_score']:.1%}")
        except Exception as e:
            print(f"  ❌ Pipeline A Error: {e}")
    
    if 'B' in pipelines_to_run:
        try:
            picks_b, name_b = run_pipeline_b()
            score_b = calculate_score(picks_b, golden_set, name_b, debug=True)
            all_results.append(score_b)
            print(f"  ✅ {name_b}: P={score_b['precision']:.1%} R={score_b['recall']:.1%} F1={score_b['f1_score']:.1%}")
        except Exception as e:
            print(f"  ❌ Pipeline B Error: {e}")
    
    if 'C' in pipelines_to_run:
        try:
            picks_c, name_c = run_pipeline_c()
            score_c = calculate_score(picks_c, golden_set, name_c, debug=True)
            all_results.append(score_c)
            print(f"  ✅ {name_c}: P={score_c['precision']:.1%} R={score_c['recall']:.1%} F1={score_c['f1_score']:.1%}")
        except Exception as e:
            print(f"  ❌ Pipeline C Error: {e}")
    
    # Save results
    report_path = os.path.join(REPORTS_DIR, 'benchmark_results.json')
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Generate charts
    if all_results:
        generate_charts(all_results)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"{'Pipeline':<30} {'Found':>8} {'Correct':>8} {'Precision':>10} {'Recall':>8} {'F1':>8}")
    print("-" * 72)
    for r in all_results:
        name = r['pipeline'].split(':')[0]
        print(f"{name:<30} {r['total_sys_picks']:>8} {r['correct_matches']:>8} {r['precision']:>9.1%} {r['recall']:>7.1%} {r['f1_score']:>7.1%}")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark()
