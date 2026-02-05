# OCR Pipeline Documentation

The CapperSuite OCR Pipeline is a multi-stage system designed to extract text from betting slips with high accuracy and speed. It combines fast local OCR with powerful Vision AI fallbacks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OCR PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   ┌──────────┐    │
│  │  INPUT   │──▶│ PRE-PROC │───▶│ RAPIDOCR │───(>60% CONF)───▶│ SUCCESS  │    │
│  │  IMAGE   │    │ ESSING   │    │  (LOCAL) │                   │  RESULT  │    │
│  └──────────┘    └──────────┘    └──────────┘                   └──────────┘    │
│                                        │                                        │
│                                   (<60% CONF)                                   │
│                                        ▼                                        │
│                                  ┌──────────┐                                   │
│                                  │  VISION  │                                   │
│                                  │ CASCADE  │                                   │
│                                  └──────────┘                                   │
│                                        │                                        │
│                       ┌────────────────┴────────────────┐                       │
│                       ▼                                 ▼                       │
│                 ┌──────────┐                      ┌──────────┐                  │
│                 │ MISTRAL  │                      │ OPENRTR  │                  │
│                 │ PIXTRAL  │                      │  GEMMA   │                  │
│                 └──────────┘                      └──────────┘                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. RapidOCR Engine (`src/ocr_engine.py`)
A local, deep-learning based OCR engine (ONNX Runtime).
- **Performance**: ~1.2s per image.
- **Accuracy**: 93% on standard betting slips.
- **Usage**: Singleton instance for efficiency.

### 2. Preprocessing (`src/ocr_preprocessing.py`)
Optimizes images for RapidOCR.
- **Grayscale**: Converts RGB to grayscale.
- **Contrast Enhancement**: Uses CLAHE (Contrast Limited Adaptive Histogram Equalization) to handle dark/light backgrounds.
- **Resizing**: Upscales small text for better detection.

### 3. OCR Cascade (`src/ocr_cascade.py`)
Orchestrates the fallback logic.
1.  **Fast Path**: Runs RapidOCR. If confidence is high, returns immediately.
2.  **Vision Race**: If RapidOCR fails, triggers multiple Vision APIs in parallel.
3.  **Result Selection**: Returns the result with the highest confidence/usability.

### 4. OCR Validator (`src/ocr_validator.py`)
Heuristic-based validation of OCR output.
- Checks for betting-related keywords (odds, team names, "Over/Under").
- Filters out noise or unrelated text.

## Vision Providers

The cascade uses a "race" strategy to get the fastest valid result.

| Provider | Model | Latency | Reliability |
|----------|-------|---------|-------------|
| **Mistral** | `pixtral-large-latest` | ~16s | High (100% success) |
| **OpenRouter** | `google/gemma-3-27b-it` | ~17s | High |
| **Gemini** | `gemini-2.0-flash` | ~5s* | Medium (Rate limits) |

*Gemini is fast but often hits free-tier rate limits (HTTP 429).

## Batch Processing

The `OCRCascade.extract_batch()` method optimizes throughput:
1.  Runs RapidOCR on ALL images in parallel (local threads).
2.  Identifies images that need Vision AI fallback.
3.  Distributes fallback images across available providers (Mistral, OpenRouter, Gemini) to maximize API quotas.

## Usage

```python
from src.ocr_cascade import extract_text_cascade, extract_batch_cascade

# Single Image
text = extract_text_cascade("slip.jpg")

# Batch
texts = extract_batch_cascade(["slip1.jpg", "slip2.jpg"])
```
