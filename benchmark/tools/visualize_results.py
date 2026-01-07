"""
Generate final comparison chart including Pipeline D.
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np

BENCHMARK_DIR = "benchmark"
DATASET_DIR = os.path.join(BENCHMARK_DIR, "dataset_v2")
REPORTS_DIR = os.path.join(BENCHMARK_DIR, "reports")
CHARTS_DIR = os.path.join(BENCHMARK_DIR, "charts")

# Load results
results = []

# Load OCR Results
# Load OCR Results
ocr_results = []
for filename in os.listdir(REPORTS_DIR):
    if filename.startswith("ocr_results_") and filename.endswith(".json"):
        with open(os.path.join(REPORTS_DIR, filename), "r") as f:
            data = json.load(f)
            # Data format: [{"engine": "tesseract_v3", "metrics": {"avg_cer": X, "avg_wer": Y}}]
            # Actually, run_ocr_only.py saves a LIST of results? No, it probably saved the final metrics or list of all results?
            # Let's check run_ocr_only.py output format.
            # Assuming it saved the summary metrics for the engine.
            # If it saved the list of individual image scores, we need to aggregate.
            # Let's assume it saved the structure: [{"engine": name, "avg_cer": val, "avg_wer": val}]
            if isinstance(data, list):
                ocr_results.extend(data)
            elif isinstance(data, dict):
                ocr_results.append(data)

# Generate OCR Chart
if ocr_results:
    fig_ocr, ax_ocr = plt.subplots(figsize=(10, 6))
    
    ocr_names = [r.get('engine', 'Unknown') for r in ocr_results]
    # Handle nested metrics structure: {"engine": "...", "metrics": {"avg_cer": X, "avg_wer": Y}}
    cers = []
    wers = []
    for r in ocr_results:
        if 'metrics' in r:
            cers.append(r['metrics'].get('avg_cer', 0) * 100)
            wers.append(r['metrics'].get('avg_wer', 0) * 100)
        else:
            cers.append(r.get('avg_cer', 0) * 100)
            wers.append(r.get('avg_wer', 0) * 100)
    
    x_ocr = np.arange(len(ocr_names))
    width = 0.35
    
    bars_cer = ax_ocr.bar(x_ocr - width/2, cers, width, label='CER (Lower is Better)', color='#E91E63')
    bars_wer = ax_ocr.bar(x_ocr + width/2, wers, width, label='WER (Lower is Better)', color='#9C27B0')
    
    ax_ocr.set_ylabel('Error Rate (%)')
    ax_ocr.set_title('OCR Accuracy (CER / WER)')
    ax_ocr.set_xticks(x_ocr)
    ax_ocr.set_xticklabels(ocr_names)
    ax_ocr.legend()
    ax_ocr.set_ylim(0, max(max(cers, default=0), max(wers, default=0)) + 10)
    
    # Annotate
    for bars in [bars_cer, bars_wer]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax_ocr.annotate(f'{height:.1f}%',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, 'ocr_comparison.png'), dpi=150)
    plt.close()
    print(f"📊 Chart saved: {os.path.join(CHARTS_DIR, 'ocr_comparison.png')}")

# Load Parsing Results (F1/Precision/Recall)
parsing_results_path = os.path.join(REPORTS_DIR, "parsing_benchmark_results.json")
if os.path.exists(parsing_results_path):
    with open(parsing_results_path, "r") as f:
        parsing_data = json.load(f)
        # Convert dictionary to list format for plotting
        for model_name, metrics in parsing_data.items():
            results.append({
                "pipeline": model_name,
                "precision": metrics.get("precision", 0),
                "recall": metrics.get("recall", 0),
                "f1_score": metrics.get("f1", 0),
                "total_sys_picks": 0, # Placeholder
                "correct_matches": 0  # Placeholder
            })

# Sort by F1 Score descending
results.sort(key=lambda x: x['f1_score'], reverse=True)

# Save combined results (optional, purely for debug)
# with open(os.path.join(REPORTS_DIR, "final_results.json"), "w") as f:
#     json.dump(results, f, indent=2)

print("=== FINAL BENCHMARK RESULTS ===")
print(f"{'Pipeline':<35} {'Found':>8} {'Correct':>8} {'Precision':>10} {'Recall':>8} {'F1':>8}")
print("-" * 75)
for r in results:
    name = r['pipeline']
    print(f"{name:<35} {r['total_sys_picks']:>8} {r['correct_matches']:>8} {r['precision']:>9.1%} {r['recall']:>7.1%} {r['f1_score']:>7.1%}")
print("=" * 75)

# Generate chart - Horizontal bar chart for better readability with many models
fig, ax = plt.subplots(figsize=(12, 10))

# Clean and shorten names
pipelines = []
for r in results:
    name = r['pipeline']
    # Remove common prefixes/suffixes
    name = name.replace('google/', '').replace('meta-llama/', '').replace('mistralai/', '')
    name = name.replace('nvidia/', '').replace('nousresearch/', '').replace('tngtech/', '')
    name = name.replace('nex-agi/', '').replace('deepseek/', '').replace('openai/', '')
    name = name.replace('xiaomi/', '').replace('z-ai/', '')
    name = name.replace(':free', '')
    # Truncate long names
    if len(name) > 25: 
        name = name[:22] + '...'
    pipelines.append(name)

f1 = [r['f1_score'] * 100 for r in results]

# Horizontal bar chart (reversed so best is at top)
y = np.arange(len(pipelines))
colors = ['#4CAF50' if f >= 90 else '#2196F3' if f >= 80 else '#FF9800' if f >= 70 else '#f44336' for f in f1]

bars = ax.barh(y, f1, color=colors, edgecolor='white', height=0.7)

ax.set_xlabel('F1 Score (%)', fontsize=12)
ax.set_title('AI Parsing Model Comparison - F1 Score\n(5 image subset, 21 golden picks)', fontsize=14)
ax.set_yticks(y)
ax.set_yticklabels(pipelines, fontsize=10)
ax.set_xlim(0, 105)
ax.invert_yaxis()  # Best at top

# Add value labels at end of bars
for bar, score in zip(bars, f1):
    width = bar.get_width()
    ax.annotate(f'{score:.1f}%',
               xy=(width + 1, bar.get_y() + bar.get_height()/2),
               va='center', ha='left', fontsize=9, fontweight='bold')

# Add legend for color coding
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#4CAF50', label='Excellent (≥90%)'),
    Patch(facecolor='#2196F3', label='Good (80-89%)'),
    Patch(facecolor='#FF9800', label='Fair (70-79%)'),
    Patch(facecolor='#f44336', label='Poor (<70%)')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

plt.tight_layout()
chart_path = os.path.join(CHARTS_DIR, 'pipeline_comparison.png')
plt.savefig(chart_path, dpi=150)
plt.close()

print(f"\n📊 Chart saved: {chart_path}")
