# Benchmark System Overhaul - Implementation Plan

## Goal
Create a robust, scalable benchmark system ('The Ultimate Benchmark') to test OCR and Parsing accuracy on 50+ real Telegram images.

## Architecture
We will restructure the `benchmark/` directory to be cleaner and more modular.

### 1. File Structure
```
benchmark/
├── dataset/                  # The Golden Set
│   ├── images/               # 50+ real images (jpg/png)
│   ├── ground_truth.json     # Validated JSON data for all images
│   └── full_dataset.pdf      # PDF of all images for easy AI validation
├── tools/
│   ├── fetch_dataset.py      # Gather images from local storage/samples
│   ├── generate_pdf.py       # Create PDF for Golden Set generation
│   └── visualize_results.py  # Generate high-res charts (replacing old mermaid/html)
├── runners/
│   ├── run_ocr_test.py       # Test OCR engines (Tesseract, Vision AI)
│   └── run_system_test.py    # Test full pipeline (Refinery, Parsing)
└── reports/                  # Output directory
    ├── ocr_results.json
    ├── system_results.json
    └── comparison_chart.png
```

## Step-by-Step Plan

### Phase 1: Data Aggregation
- **Task**: Collect at least 50 images.
- **Approach**: 
    - Use existing 20 images from `tests/samples`.
    - Search for other images in `static/temp_images` or `tessdata`.
    - If <50 found, duplicate/augment existing ones or ask user for path. (For now, I'll aim to find as many unique ones as possible, or loop the 20 to get 50 data points if distinct ones aren't available).

### Phase 2: Golden Set Creation
- **Task**: Generate `dataset/full_dataset.pdf` and the Master Prompts.
- **Tools**: `benchmark/tools/generate_pdf.py`.
- **Validation**: User will feed this PDF to GPT-4o with the "Ultimate Prompt" to get `ground_truth.json`.

### Phase 3: Benchmark Runners
- **OCR Runner**:
    - Modularize `ocr_benchmark.py` into `runners/run_ocr_test.py`.
    - Support: Tesseract (Local), Qwen (Cloud), Gemma (Cloud).
    - Metrics: CER (Char Error Rate), WER (Word Error Rate), Accuracy, Latency.
- **System Runner**:
    - New script `runners/run_system_test.py`.
    - Feeds raw image to the full app pipeline (Refinery).
    - Compares final Structured JSON against Ground Truth JSON.
    - Metrics: Pick Precision, Odds Accuracy, Unit Accuracy.

### Phase 4: Reporting
- **Visualization**:
    - Use `matplotlib` to generate professional bar charts.
    - Save to `README.md` and `benchmark/reports/`.

## Verification Plan
1.  **Dataset Check**: Verify `benchmark/dataset/images` has 50+ files.
2.  **PDF Generation**: Run `python benchmark/tools/generate_pdf.py` -> Check size/pages of output PDF.
3.  **Runner Execution**:
    - Run `python benchmark/runners/run_ocr_test.py` (Draft run with small subset).
    - Run `python benchmark/runners/run_system_test.py`.
4.  **Chart Check**: Verify `benchmark/reports/comparison_chart.png` is generated.
