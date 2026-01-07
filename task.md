# Benchmark System Overhaul

## Goal
Replace the current ad-hoc benchmark folder with a robust, scalable system capable of testing "everything" (OCR, Parsing/Refinery) on a dataset of 50+ real Telegram images.

## Structure
- `benchmark/dataset/`: Storage for raw images and the `ground_truth.json`.
- `benchmark/tools/`: Scripts for dataset management (fetching, PDF generation).
- `benchmark/runners/`: Scripts to run specific benchmarks (OCR, Parsing).
- `benchmark/reports/`: Output directory for JSON results and HTML/Chart visualizations.

## Steps
1.  **Data Acquisition**:
    - Locate or fetch 50+ real images.
    - Create `benchmark/tools/fetch_real_data.py`.
2.  **Ground Truth Generation (Golden Set)**:
    - Create `benchmark/tools/generate_validation_pdf.py` to stitch images into a single PDF for easy AI processing.
    - Finalize the "Ultimate Prompt" for generating the ground truth JSON.
3.  **Benchmark Engine**:
    - Rewrite `benchmark_runner.py` to be modular.
    - Support:
        - **OCR**: Tesseract (Local), Vision AI (Gemma/Qwen via OpenRouter).
        - **Refinery**: LLM-based parsing of the OCR text.
4.  **Reporting**:
    - Generate comparative charts (Accuracy, F1 Score, Latency).

## Checklist
- [x] Explore existing images
- [x] Design file structure
- [x] Implement data fetching/organization
- [x] Implement PDF generator for Golden Set
- [x] Create Master Prompt (and fix formatting rules)
- [x] Implement Benchmark Runner (System & OCR)
- [x] Update README
