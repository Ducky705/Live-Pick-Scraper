import os
import random
import logging
from rapidfuzz import process, fuzz
from src.supabase_client import get_supabase
from src.utils import normalize_string

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def fetch_data():
    supabase = get_supabase()
    
    logger.info("Fetching capper directory...")
    res_dir = supabase.table("capper_directory").select("id, canonical_name").execute()
    cappers = {item["canonical_name"]: item["id"] for item in res_dir.data}
    
    logger.info("Fetching capper variants...")
    res_var = supabase.table("capper_variants").select("capper_id, variant_name").execute()
    variants = res_var.data
    
    logger.info("Fetching real-world test cases (Review Queue)...")
    res_queue = supabase.table("capper_review_queue").select("raw_name").limit(500).execute()
    queue_names = list(set(item["raw_name"] for item in res_queue.data if item["raw_name"]))

    logger.info("Fetching real-world test cases (Raw Picks)...")
    res_picks = supabase.table("raw_picks").select("capper_name").order("created_at", desc=True).limit(500).execute()
    pick_names = list(set(item["capper_name"] for item in res_picks.data if item["capper_name"]))
    
    return cappers, variants, queue_names + pick_names

def generate_hard_negatives(capper_names):
    """
    Generates names that look similar but are definitely NOT the same person.
    e.g. "Bob Smith" -> "Rob Smith", "Bill Smith"
    """
    negatives = []
    
    # Simple heuristic generation for now to avoid LLM overhead/cost in loop
    # We want to ensure we don't match "Don Best" with "Don Buster" casually
    
    for name in capper_names[:200]: # Sample 200
        parts = name.split()
        if len(parts) >= 2:
            # Swap first letter of first name
            last = parts[-1]
            first = parts[0]
            
            # Change first char
            new_first_char = chr(ord(first[0]) + 1) if first[0] < 'z' else 'a'
            fake_first = new_first_char + first[1:]
            
            negatives.append(f"{fake_first} {last}")
            
            # Change last name slightly
            negatives.append(f"{first} {last}son")
            
    return negatives

def evaluate_threshold(threshold, cappers, variants, negatives):
    """
    Returns (precision, recall, false_positives)
    
    Precision: TP / (TP + FP)
    Recall: TP / (TP + FN)
    """
    capper_names = list(cappers.keys())
    
    # 1. Check Recall (Can we find the canonical from the variant?)
    tp = 0
    fn = 0
    
    for v in variants:
        target_id = v["capper_id"]
        variant_name = v["variant_name"]
        
        # We need to look up which canonical name has this ID
        # Inefficient O(N) lookup here but dataset is small (~1000s)
        target_canonical = next((name for name, cid in cappers.items() if cid == target_id), None)
        
        if not target_canonical:
            continue
            
        # Run Match
        match = process.extractOne(variant_name, capper_names, scorer=fuzz.WRatio, score_cutoff=threshold)
        
        if match:
            matched_name, score, _ = match
            if cappers[matched_name] == target_id:
                tp += 1
            else:
                # We matched, but to the WRONG capper! This is a False Positive in the context of identification
                # But for pure recall of "did we find it", it's complex. 
                # Let's count it as incorrect match -> FN for the correct one
                fn += 1 
        else:
            fn += 1
            
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # 2. Check Precision (Do we match Hard Negatives?)
    # We expect these to match NOTHING or match with score < threshold
    fp_negatives = 0
    
    for neg in negatives:
        match = process.extractOne(neg, capper_names, scorer=fuzz.WRatio, score_cutoff=threshold)
        if match:
            # We matched a hard negative to a real capper! Bad!
            fp_negatives += 1
            
    # Precision in this context: 1 - (False Positive Rate on Negatives)
    # If we match ANY negative, our precision drops
    precision = 1.0 - (fp_negatives / len(negatives)) if len(negatives) > 0 else 1.0
    
    return precision, recall, fp_negatives

def main():
    print("Starting Calibration...")
    cappers, variants, real_queries = fetch_data()
    print(f"Loaded {len(cappers)} cappers, {len(variants)} variants, {len(real_queries)} real queries.")
    
    capper_names = list(cappers.keys())
    negatives = generate_hard_negatives(capper_names)
    print(f"Generated {len(negatives)} hard negatives.")
    
    print("\n--- Testing Thresholds ---")
    print(f"{'Threshold':<10} | {'Recall':<10} | {'Precision':<10} | {'FP Count':<10}")
    print("-" * 50)
    
    best_threshold = 100
    max_recall_at_perfect_precision = 0
    
    # Sweep from 100 down to 60
    for t in range(100, 59, -1):
        prec, rec, fp = evaluate_threshold(t, cappers, variants, negatives)
        print(f"{t:<10} | {rec:.4f}     | {prec:.4f}        | {fp:<10}")
        
        if fp == 0 and rec >= max_recall_at_perfect_precision:
            max_recall_at_perfect_precision = rec
            best_threshold = t
            
    print("-" * 50)
    print(f"OPTIMAL THRESHOLD (Zero FP): {best_threshold}")
    print(f"Recall at this threshold: {max_recall_at_perfect_precision:.2%}")
    
    # Verify strictness
    if best_threshold < 80:
        print("\n[WARNING] Optimal threshold is surprisingly low. Generated negatives might be too distinct.")
    elif best_threshold > 95:
         print("\n[WARNING] Optimal threshold is very high. We might miss many valid variations.")

if __name__ == "__main__":
    main()
