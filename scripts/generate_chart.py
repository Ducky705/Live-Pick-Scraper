import json
import matplotlib.pyplot as plt
import numpy as np
import os

# Define styles
plt.style.use('dark_background')
colors = ['#FF4B4B', '#4B7BFF', '#00CC96', '#FFAA00'] # Red, Blue, Green, Amber

def generate_charts():
    # Load Data
    data_path = 'benchmark_results/ocr_benchmark_results.json'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found")
        return

    with open(data_path, 'r') as f:
        raw_data = json.load(f)

    # Models to compare
    models = ['Tesseract (Legacy)', 'Qwen 2.5-VL', 'Gemma 3-12b']
    
    # Extract Accuracy Data (Hardcoded mapping based on raw_data keys)
    # Tesseract
    tess_acc = [m['accuracy'] * 100 for m in raw_data.get('tesseract', {}).get('metrics', [])]
    # Qwen
    qwen_acc = [m['accuracy'] * 100 for m in raw_data.get('qwen/qwen-2.5-vl-7b-instruct:free', {}).get('metrics', [])]
    # Gemma
    gemma_acc = [m['accuracy'] * 100 for m in raw_data.get('google/gemma-3-12b-it:free', {}).get('metrics', [])]

    # Labels for the 3 test cases
    labels = ['Standard Slip', 'Long Receipt', 'Handwritten']

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    
    rects1 = ax.bar(x - width, tess_acc, width, label='Tesseract v5 (Legacy)', color='#FF5252', alpha=0.9)
    rects2 = ax.bar(x, qwen_acc, width, label='Qwen 2.5-VL (Cloud)', color='#448AFF', alpha=0.9)
    rects3 = ax.bar(x + width, gemma_acc, width, label='Gemma 3-12b (Cloud)', color='#69F0AE', alpha=0.9)

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('Accuracy (%)', fontsize=12, color='white')
    ax.set_title('OCR Engine Accuracy Comparison (v3.0 vs Legacy)', fontsize=16, color='white', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, color='lightgray')
    ax.set_ylim(0, 105)
    ax.legend(loc='lower right', frameon=False, fontsize=10)
    
    # Grid
    ax.grid(axis='y', linestyle='--', alpha=0.2)
    
    # Remove borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#444')
    ax.spines['bottom'].set_color('#444')

    # Add value labels
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, color='white')

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    fig.tight_layout()

    # Save
    output_dir = 'static/images'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, 'benchmark_chart_v3.png')
    plt.savefig(output_path, dpi=150, facecolor='#121212', edgecolor='none')
    print(f"Chart saved to {output_path}")

if __name__ == "__main__":
    generate_charts()
