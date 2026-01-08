"""
Generate final comparison chart with Swiss Design System (Premium Aesthetic).
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

# --- SWISS DESIGN SYSTEM CONFIGURATION ---
SWISS_BLACK = "#050505"
SWISS_BLUE = "#0044CC"
SWISS_GRAY = "#E5E5E5"
SWISS_LIGHT = "#F4F4F4"
SWISS_DARK_GRAY = "#555555"

# Configure Matplotlib for "Billion Dollar Company" look
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "SF Pro Display", "Helvetica Neue", "Arial", "sans-serif"],
    "font.size": 10,
    "text.color": SWISS_BLACK,
    "axes.labelcolor": SWISS_DARK_GRAY,
    "axes.labelsize": 11,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "axes.titlepad": 20,
    "xtick.color": SWISS_DARK_GRAY,
    "ytick.color": SWISS_DARK_GRAY,
    "axes.edgecolor": SWISS_GRAY, # Subtle borders
    "axes.linewidth": 1,
    "axes.grid": True,
    "grid.color": SWISS_LIGHT,
    "grid.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 300, # High res
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False, # Clean look
    "axes.spines.bottom": True,
})

BENCHMARK_DIR = "benchmark"
REPORTS_DIR = os.path.join(BENCHMARK_DIR, "reports")
CHARTS_DIR = os.path.join(BENCHMARK_DIR, "charts")

# Ensure charts dir exists
os.makedirs(CHARTS_DIR, exist_ok=True)

# --- LOAD DATA ---

results = []
ocr_results = []

# Load OCR Results
if os.path.exists(REPORTS_DIR):
    for filename in os.listdir(REPORTS_DIR):
        if filename.startswith("ocr_results_") and filename.endswith(".json"):
            try:
                with open(os.path.join(REPORTS_DIR, filename), "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        ocr_results.extend(data)
                    elif isinstance(data, dict):
                        ocr_results.append(data)
            except Exception as e:
                print(f"Skipping {filename}: {e}")

# Load Parsing Results
parsing_results_path = os.path.join(REPORTS_DIR, "parsing_benchmark_results.json")
if os.path.exists(parsing_results_path):
    with open(parsing_results_path, "r") as f:
        parsing_data = json.load(f)
        for model_name, metrics in parsing_data.items():
            results.append({
                "pipeline": model_name,
                "precision": metrics.get("precision", 0),
                "recall": metrics.get("recall", 0),
                "f1_score": metrics.get("f1", 0),
            })

# Sort by F1 Score descending
results.sort(key=lambda x: x['f1_score'], reverse=True)


# --- CHART 1: OCR ACCURACY (Clean Dual Bar) ---
if ocr_results:
    print("Generating OCR Chart...")
    fig_ocr, ax_ocr = plt.subplots(figsize=(10, 6))
    
    ocr_names = [r.get('engine', 'Unknown').replace('_', ' ').title().replace('V3', 'v3') for r in ocr_results]
    
    cers = []
    wers = []
    for r in ocr_results:
        metrics = r.get('metrics', r)
        cers.append(metrics.get('avg_cer', 0) * 100)
        wers.append(metrics.get('avg_wer', 0) * 100)
    
    x_ocr = np.arange(len(ocr_names))
    width = 0.3
    
    # Grid configuration for this specific chart
    ax_ocr.grid(axis='y', color=SWISS_LIGHT, zorder=0)
    ax_ocr.grid(axis='x', visible=False)

    # Bars - Premium Colors (Swiss Blue vs Dark Neutral)
    bars_cer = ax_ocr.bar(x_ocr - width/2, cers, width, label='CER (Char Error)', color=SWISS_BLUE, zorder=3)
    bars_wer = ax_ocr.bar(x_ocr + width/2, wers, width, label='WER (Word Error)', color=SWISS_BLACK, zorder=3)
    
    # Styling
    ax_ocr.set_ylabel('Error Rate (%)', labelpad=10)
    ax_ocr.set_title('OCR Engine Accuracy', loc='left')
    ax_ocr.set_xticks(x_ocr)
    ax_ocr.set_xticklabels(ocr_names, fontweight='medium')
    
    # Clean Legend
    ax_ocr.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, 1))
    
    # Remove all spines except bottom
    ax_ocr.spines['left'].set_visible(False)
    
    # Value Labels (Minimalist)
    def autolabel(rects, is_secondary=False):
        for rect in rects:
            height = rect.get_height()
            if height > 0:
                ax_ocr.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 5), textcoords="offset points",
                            ha='center', va='bottom', 
                            fontsize=9, 
                            fontweight='bold' if not is_secondary else 'normal',
                            color=SWISS_BLACK if not is_secondary else SWISS_DARK_GRAY)

    autolabel(bars_cer)
    autolabel(bars_wer, is_secondary=True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, 'ocr_comparison.png'), bbox_inches='tight', pad_inches=0.5)
    plt.close()
    print(f"📊 Chart saved: {os.path.join(CHARTS_DIR, 'ocr_comparison.png')}")


# --- CHART 2: AI PIPELINE COMPARISON (Premium Horizontal Bar) ---
if results:
    print("Generating Pipeline Chart...")
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Clean names
    pipelines = []
    for r in results:
        name = r['pipeline']
        name = name.replace('google/', '').replace('meta-llama/', '').replace('mistralai/', '')
        name = name.replace('nvidia/', '').replace('nousresearch/', '').replace('tngtech/', '')
        name = name.replace('nex-agi/', '').replace('deepseek/', '').replace('openai/', '')
        name = name.replace('xiaomi/', '').replace('z-ai/', '')
        name = name.replace(':free', '')
        if len(name) > 25: name = name[:22] + '...'
        pipelines.append(name.title())

    f1_scores = [r['f1_score'] * 100 for r in results]
    
    y = np.arange(len(pipelines))
    
    # Grid config
    ax.grid(axis='x', color=SWISS_LIGHT, linestyle='-', linewidth=1, zorder=0)
    ax.grid(axis='y', visible=False)

    # Dynamic "Swiss" Coloring
    # Top performers get the Brand Blue, others get shades of gray/black/mute
    colors = []
    for score in f1_scores:
        if score >= 90:
            colors.append(SWISS_BLUE) # Brand Blue for Excellence
        elif score >= 85:
            colors.append('#3366DD') # Lighter Blue
        elif score >= 70:
            colors.append('#555555') # Dark Gray (Neutral)
        else:
            colors.append('#999999') # Light Gray (Poor)

    bars = ax.barh(y, f1_scores, color=colors, height=0.65, zorder=3)
    
    # Styling
    ax.set_xlabel('F1 Score (%)', labelpad=10)
    ax.set_title('AI Model Performance Benchmark', loc='left', pad=15)
    ax.set_yticks(y)
    ax.set_yticklabels(pipelines, fontsize=11, fontweight='medium')
    ax.set_xlim(0, 105) # Give space for labels
    
    # Remove Y axis spine
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color(SWISS_GRAY)
    ax.tick_params(axis='y', length=0) # No ticks on Y axis
    
    ax.invert_yaxis()  # Best at top

    # Value Labels (Inside or Outside based on space)
    for i, (bar, score) in enumerate(zip(bars, f1_scores)):
        width = bar.get_width()
        
        # Bold score for top performers
        weight = 'bold' if score >= 90 else 'normal'
        color = SWISS_BLUE if score >= 90 else SWISS_BLACK
        
        # Label placement
        ax.text(width + 1.5, bar.get_y() + bar.get_height()/2, 
                f'{score:.1f}%', 
                va='center', ha='left', 
                fontsize=10, fontweight=weight, color=color)
        
        if i == 0:
            ax.text(width + 12, bar.get_y() + bar.get_height()/2, 
                    "TOP CHOICE", 
                    va='center', ha='left', 
                    fontsize=9, fontweight='bold', color=SWISS_BLUE)

    # Custom Legend
    legend_elements = [
        Patch(facecolor=SWISS_BLUE, label='Excellent (≥90%)'),
        Patch(facecolor='#3366DD', label='Good (≥85%)'),
        Patch(facecolor='#555555', label='Fair (<85%)'),
        Patch(facecolor='#999999', label='Poor (<70%)')
    ]
    ax.legend(handles=legend_elements, frameon=False, loc='lower right', bbox_to_anchor=(1, 0))

    plt.tight_layout()
    chart_path = os.path.join(CHARTS_DIR, 'pipeline_comparison.png')
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    
    print(f"📊 Chart saved: {chart_path}")

