# Mistral & Pixtral Benchmark Report

## Overview
We benchmarked Mistral AI models for two tasks:
1. **Parsing:** Extracting structured betting picks from raw text.
2. **OCR:** Extracting raw text from betting slip images (using Pixtral).

## 1. Parsing Benchmark (Text-to-JSON)
We tested models on extracting picks from pre-OCRed text.

| Model | Accuracy (F1) | Latency | Verdict |
|-------|---------------|---------|---------|
| **Mistral Large** | **100.00%** | 4.14s | **Champion.** Perfect accuracy, slightly slower. Use for complex cases. |
| **Ministral 8B** | 97.56% | **2.08s** | **Best Value.** Very fast and highly accurate. Excellent default. |
| **Mistral Small** | 95.24% | 2.82s | Good, but Ministral 8B outperforms it in speed/accuracy. |
| **Codestral** | 81.08% | 1.23s | Not recommended for this specific task. |

**Recommendation:** Add `mistral-large-latest` and `ministral-8b-latest` to the rotation.

## 2. OCR Benchmark (Image-to-Text)
We tested Pixtral models on raw images.

| Model | Similarity | Latency | Verdict |
|-------|------------|---------|---------|
| **Pixtral Large** | ~90% | 4.44s | Accurate but slow. Good fallback. |
| **Pixtral 12B** | ~78% | **1.92s** | Fast but flaky. Failed on complex/long images (Timeout). |

**Recommendation:** Do NOT replace the current primary OCR (Gemini/Tesseract) with Pixtral yet. It struggles with dense text (e.g., full betting slips). Keep `pixtral-large` only as a tertiary fallback.

## Implementation Status
- [x] **Client:** `src/mistral_client.py` implemented with retry logic.
- [x] **Pooling:** `src/provider_pool.py` created to manage concurrency between Cerebras, Groq, and Mistral.
- [x] **Config:** Models integrated into the provider pool with appropriate prioritization (Mistral Large for text, Pixtral Large for fallback vision).
