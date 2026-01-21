
import os
import sys
import json
import logging
import argparse
import Levenshtein
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ocr_handler import extract_text_simple_tesseract, extract_text_v3, extract_text_ai, extract_text_batch

# Rename for clarity - these now use RapidOCR
extract_text_simple_rapidocr = extract_text_simple_tesseract
extract_text_rapidocr_v3 = extract_text_v3

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "ocr_golden_set.json")
RESULTS_DIR = os.path.join("benchmark", "reports")

def calculate_metrics(hypothesis, reference):
    """
    Calculate Character Error Rate (CER) and Word Error Rate (WER).
    """
    if not reference:
        return 1.0, 1.0
        
    # CER
    cer = Levenshtein.distance(hypothesis, reference) / len(reference)
    
    # WER
    hyp_words = hypothesis.split()
    ref_words = reference.split()
    if not ref_words:
        wer = 1.0
    else:
        wer = Levenshtein.distance(hyp_words, ref_words) / len(ref_words)
        
    return cer, wer

def normalize_output(text):
    """
    Remove known watermarks/noise to ensure fair comparison 
    between raw OCR and preprocessed OCR.
    """
    if not text: return ""
    # Remove the specific watermark we know exists
    text = text.replace("@cappersfree", "")
    # Remove common promotional noise if any
    text = text.replace("cappersfree", "")
    return text

def run_ocr_benchmark(engine="tesseract_v3"):
    if not os.path.exists(GOLDEN_SET_PATH):
        print(f"Error: Golden Set not found at {GOLDEN_SET_PATH}. Please generate it first.")
        return

    with open(GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    print(f"Running OCR Benchmark (Engine: {engine}) on {len(ground_truth)} images...")
    
    results = []
    total_cer = 0
    total_wer = 0
    
    # Define directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")

     # Load Image Map
    image_map_path = os.path.join(DATASET_DIR, "image_map.json")
    image_map = {}
    if os.path.exists(image_map_path):
        with open(image_map_path, "r", encoding="utf-8") as f:
            image_map = json.load(f)
    else:
        print(f"Warning: Image map not found at {image_map_path}. Assuming keys are filenames.")

    # Prepare image list if batching
    image_paths = list(ground_truth.keys())
    # Note: Image paths in JSON key might be filename only, need to resolve to full path
    # Assuming images are in benchmark/dataset/images/ or tests/samples/
    # For now, let's assume keys are absolute paths or relative to repo root
    
    # If using batch AI, processing is different
    if "batch" in engine:
         # TODO: Implement batch logic here if needed, for now loop one by one for granular metrics
         pass

    for i, (img_path, distinct_text) in enumerate(ground_truth.items()):
        # Resolve path
        if img_path in image_map:
             img_path = image_map[img_path]
        
        if not os.path.isabs(img_path):
             # Try common locations
             possible_paths = [
                 img_path,
                 os.path.join("benchmark", "dataset", "images", img_path),
             ]
             for p in possible_paths:
                 if os.path.exists(p):
                     img_path = p
                     break
        
        if not os.path.exists(img_path):
            print(f"Skipping missing image: {img_path}")
            continue

        try:
            # Run OCR (tesseract_* names kept for backward compatibility - now use RapidOCR)
            if engine == "tesseract_simple" or engine == "rapidocr_simple":
                output_text = extract_text_simple_tesseract(img_path)
            elif engine == "tesseract_v3" or engine == "rapidocr_v3":
                output_text = extract_text_v3(img_path)
            elif engine == "ai_vision":
                output_text = extract_text_ai(img_path) # Default Gemini
            elif engine == "pipeline_d":
                # For single image, call extract_text_batch with one image
                out = extract_text_batch([img_path])
                output_text = out[0]
            else:
                print(f"Unknown engine: {engine}")
                return

            # Normalize output to remove watermarks for fair scoring
            output_text = normalize_output(output_text)

            # Calculate metrics
            cer, wer = calculate_metrics(output_text, distinct_text)
            total_cer += cer
            total_wer += wer
            
            results.append({
                "image": img_path,
                "cer": cer,
                "wer": wer,
                "output_length": len(output_text),
                "ground_truth_length": len(distinct_text)
            })
            
            print(f"[{i+1}/{len(ground_truth)}] {engine} - CER: {cer:.2f}, WER: {wer:.2f}")

        except Exception as e:
            print(f"Error processing {img_path}: {e}")

    # Summary
    avg_cer = total_cer / len(results) if results else 0
    avg_wer = total_wer / len(results) if results else 0
    
    print("\n" + "="*30)
    print(f"BENCHMARK RESULTS: {engine}")
    print(f"Average CER: {avg_cer:.2%}")
    print(f"Average WER: {avg_wer:.2%}")
    print("="*30 + "\n")
    
    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_file = os.path.join(RESULTS_DIR, f"ocr_results_{engine}.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            "engine": engine,
            "metrics": {"avg_cer": avg_cer, "avg_wer": avg_wer},
            "details": results
        }, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=str, default="tesseract_v3", choices=["tesseract_simple", "tesseract_v3", "ai_vision", "pipeline_d"])
    args = parser.parse_args()
    
    run_ocr_benchmark(args.engine)
