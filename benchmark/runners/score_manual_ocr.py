
import os
import json
import jiwer
from rich.console import Console
from rich.progress import track

# Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")
REPORTS_DIR = os.path.join(BASE_DIR, "benchmark", "reports")
MANUAL_INPUT_FILE = os.path.join(REPORTS_DIR, "manual_ocr_input.json")
OUTPUT_FILE = os.path.join(REPORTS_DIR, "ocr_results_manual.json")
GOLDEN_SET_FILE = os.path.join(DATASET_DIR, "ocr_golden_set.json")

console = Console()

def normalize_output(text):
    """Normalize text for scoring (strip whitespace, remove known watermarks/artifacts)."""
    if not text:
        return ""
    
    # Remove specific watermark text found in this dataset
    text = text.replace("@cappersfree", "")
    text = text.replace("cappersfree", "") 
    
    return text.strip()

def score_manual_results():
    if not os.path.exists(MANUAL_INPUT_FILE):
        console.print(f"[red]Error: Manual input file not found: {MANUAL_INPUT_FILE}[/red]")
        console.print("Please create this file with your AI-transcribed JSON.")
        return

    # Load Golden Set
    with open(GOLDEN_SET_FILE, "r", encoding='utf-8') as f:
        golden_set = json.load(f)
    sorted_golden_keys = sorted(golden_set.keys())

    # Load Manual Results
    with open(MANUAL_INPUT_FILE, "r", encoding='utf-8') as f:
        manual_results = json.load(f)
    
    console.print(f"Loaded {len(manual_results)} manual entries.")

    results = []
    total_cer = 0
    total_wer = 0
    count = 0

    # Map manual keys to golden keys
    # Handling numeric keys "1", "2" -> "image_X.jpg"
    manual_keys = sorted(manual_results.keys())
    
    for idx, key in enumerate(manual_keys):
        # Determine mapping
        golden_key = None
        
        # If key is effectively a golden key
        if key in golden_set:
            golden_key = key
        # If key is numeric string "1", "2"
        elif key.isdigit():
            idx_int = int(key) - 1
            if 0 <= idx_int < len(sorted_golden_keys):
                golden_key = sorted_golden_keys[idx_int]
        
        if not golden_key:
            console.print(f"[yellow]Skipping unknown key: {key}[/yellow]")
            continue

        ground_truth = golden_set[golden_key]
        raw_output = manual_results[key]
        normalized_output = normalize_output(raw_output)

        # Calculate metrics
        try:
            cer = jiwer.cer(ground_truth, normalized_output)
            wer = jiwer.wer(ground_truth, normalized_output)
        except Exception as e:
            console.print(f"[red]Error calculating metrics for {golden_key}: {e}[/red]")
            cer, wer = 1.0, 1.0

        results.append({
            "image": golden_key,
            "cer": cer,
            "wer": wer,
            "output_length": len(normalized_output),
            "ground_truth_length": len(ground_truth)
        })

        total_cer += cer
        total_wer += wer
        count += 1

    if count == 0:
        console.print("[red]No valid matches found to score.[/red]")
        return

    avg_cer = total_cer / count
    avg_wer = total_wer / count

    # Save format compatible with visualize_results.py
    final_output = {
        "engine": "manual_ai",
        "metrics": {
            "avg_cer": avg_cer,
            "avg_wer": avg_wer
        },
        "details": results
    }

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_output, f, indent=2)

    console.print(f"[green]Scoring Complete![/green]")
    console.print(f"Average CER: {avg_cer:.2%}")
    console.print(f"Average WER: {avg_wer:.2%}")
    console.print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    score_manual_results()
