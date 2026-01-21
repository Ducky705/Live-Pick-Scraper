"""
OCR + Parsing Benchmark
=======================
Multi-provider OCR benchmark that tests:
1. Each provider/model individually
2. Structured vs Raw prompts
3. End-to-end: OCR → Parser → Picks

Ground truth is established by the best available vision model.

Usage:
    python -m benchmark.ocr_benchmark --limit 20 --quick
    python -m benchmark.ocr_benchmark --limit 50
"""

import os
import sys
import json
import logging
import time
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

# Setup paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import after path setup
from src.ocr_validator import is_usable_ocr, validate_ocr_detailed
from src.ocr_cascade import (
    _run_tesseract, _call_gemini, _call_groq, _call_mistral, _call_openrouter,
    STRUCTURED_PROMPT, RAW_PROMPT, OCRResult, OCRMethod
)


@dataclass
class ProviderResult:
    """Result from a single provider test."""
    provider: str
    prompt_type: str
    text: str
    confidence: float
    time_ms: int
    picks_found: List[str]
    picks_matched: int
    picks_missed: int
    error: Optional[str] = None


@dataclass 
class ImageBenchmark:
    """Benchmark results for a single image."""
    image_path: str
    ground_truth_picks: List[str]
    provider_results: List[ProviderResult]
    best_provider: str
    best_accuracy: float


@dataclass
class BenchmarkReport:
    """Full benchmark report."""
    total_images: int
    total_time_seconds: float
    ground_truth_model: str
    provider_summary: Dict[str, Dict]
    image_results: List[ImageBenchmark]
    recommendations: List[str]


# --- GROUND TRUTH EXTRACTION ---

GT_CACHE_FILE = os.path.join(BASE_DIR, "benchmark", "ground_truth_cache.json")
_GT_CACHE = {}

def load_gt_cache():
    """Load ground truth cache from disk."""
    global _GT_CACHE
    if os.path.exists(GT_CACHE_FILE):
        try:
            with open(GT_CACHE_FILE, 'r', encoding='utf-8') as f:
                _GT_CACHE = json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load GT cache: {e}")

def save_gt_cache():
    """Save ground truth cache to disk."""
    try:
        os.makedirs(os.path.dirname(GT_CACHE_FILE), exist_ok=True)
        with open(GT_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_GT_CACHE, f, indent=2)
    except Exception as e:
        logging.warning(f"Failed to save GT cache: {e}")

def get_ground_truth_picks(image_path: str) -> Tuple[List[str], str]:
    """
    Use the most accurate available vision model to establish ground truth.
    Returns (picks_list, model_used)
    """
    # Check cache first
    filename = os.path.basename(image_path)
    if not _GT_CACHE:
        load_gt_cache()
    
    if filename in _GT_CACHE:
        logging.info(f"  [Cache] Hit for {filename}")
        return _GT_CACHE[filename]["picks"], _GT_CACHE[filename]["model"]

    prompt = """Analyze this sports betting image carefully.

List ALL betting picks shown. A pick is a specific bet like:
- Team spreads: "Lakers -5", "Chiefs +3.5"  
- Totals: "Over 220", "Under 45.5"
- Moneylines: "Lakers ML", "Chiefs ML"
- Player props: "LeBron Over 25.5 points"

Return JSON:
{
    "picks": ["pick 1 exactly as written", "pick 2", ...]
}

If NO picks are visible (only promotional content), return {"picks": []}
Be thorough - extract every pick you can see."""

    # Try providers in order of reliability/speed (Mistral > Groq > Gemini > OpenRouter)
    providers = []
    
    # Mistral (Pixtral) - Usually reliable and fast
    if os.getenv("MISTRAL_TOKEN"):
        providers.append(("mistral", _call_mistral))
        
    # Groq (Llama 4) - Fast but can be 503
    if os.getenv("GROQ_TOKEN"):
        providers.append(("groq", _call_groq))
        
    # Gemini (Flash) - High quality but heavy rate limits
    if os.getenv("GEMINI_TOKEN"):
        providers.append(("gemini", _call_gemini))
        
    # OpenRouter - Fallback
    if os.getenv("OPENROUTER_API_KEY"):
        providers.append(("openrouter", _call_openrouter))
    
    for name, func in providers:
        try:
            result = func(image_path, prompt, "structured")
            if result.text and result.confidence > 0.3:
                picks = _extract_picks_from_text(result.text)
                
                # Cache the result
                _GT_CACHE[filename] = {"picks": picks, "model": name}
                save_gt_cache()
                
                return picks, name
        except Exception as e:
            logging.warning(f"[Benchmark] Ground truth {name} failed: {e}")
            continue
    
    return [], "none"


def _extract_picks_from_text(text: str) -> List[str]:
    """Extract picks array from OCR/API response."""
    import re
    
    if not text:
        return []
    
    # Try JSON parse first
    try:
        # Clean markdown
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        
        data = json.loads(clean)
        
        if isinstance(data, dict):
            if "picks" in data and isinstance(data["picks"], list):
                return [str(p) for p in data["picks"] if p]
            if "text" in data:
                # Parse picks from text field
                return _parse_picks_from_raw_text(data["text"])
        elif isinstance(data, list):
            return [str(p) for p in data if p]
            
    except json.JSONDecodeError:
        pass
    
    # Fallback: extract pick patterns from raw text
    return _parse_picks_from_raw_text(text)


def _parse_picks_from_raw_text(text: str) -> List[str]:
    """Extract picks from raw OCR text using patterns."""
    import re
    
    picks = []
    
    # Pattern: Team Name followed by spread/ML/total
    patterns = [
        r'([A-Z][a-zA-Z\s]+)\s+([+-]\d+\.?\d*)',  # Team +/-X.X
        r'([A-Z][a-zA-Z\s]+)\s+(ML|ml|Ml)',        # Team ML
        r'([Oo]ver|[Uu]nder)\s+(\d+\.?\d*)',       # Over/Under X
        r'([A-Z][a-zA-Z\s]+)\s+([Oo]ver|[Uu]nder)\s+(\d+\.?\d*)',  # Team Over/Under
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                pick = " ".join(str(m) for m in match if m).strip()
            else:
                pick = str(match).strip()
            if pick and len(pick) > 3:
                picks.append(pick)
    
    return list(set(picks))[:10]  # Dedupe, limit to 10


# --- PICK COMPARISON ---

def compare_picks(expected: List[str], actual: List[str]) -> Tuple[int, int, int]:
    """
    Compare expected vs actual picks using fuzzy matching.
    Returns (matched, missed, extra)
    """
    if not expected:
        return 0, 0, len(actual)
    
    matched = 0
    unmatched_expected = list(expected)
    unmatched_actual = list(actual)
    
    for exp in expected:
        best_match = None
        best_score = 0.0
        
        for act in unmatched_actual:
            score = SequenceMatcher(None, exp.lower(), act.lower()).ratio()
            if score > best_score and score > 0.5:  # 50% similarity threshold
                best_score = score
                best_match = act
        
        if best_match:
            matched += 1
            unmatched_expected.remove(exp)
            unmatched_actual.remove(best_match)
    
    missed = len(unmatched_expected)
    extra = len(unmatched_actual)
    
    return matched, missed, extra


# --- PROVIDER TESTING ---

def test_provider(
    provider_name: str,
    provider_func,
    image_path: str,
    prompt_type: str,
    ground_truth: List[str]
) -> ProviderResult:
    """Test a single provider on an image."""
    
    prompt = STRUCTURED_PROMPT if prompt_type == "structured" else RAW_PROMPT
    
    try:
        if provider_name == "tesseract":
            result = _run_tesseract(image_path)
        else:
            result = provider_func(image_path, prompt, prompt_type)
        
        # Extract picks from result
        picks = _extract_picks_from_text(result.text)
        
        # Compare to ground truth
        matched, missed, extra = compare_picks(ground_truth, picks)
        
        return ProviderResult(
            provider=provider_name,
            prompt_type=prompt_type,
            text=result.text[:500] if result.text else "",  # Truncate for storage
            confidence=result.confidence,
            time_ms=result.time_ms,
            picks_found=picks,
            picks_matched=matched,
            picks_missed=missed,
            error=result.error
        )
        
    except Exception as e:
        return ProviderResult(
            provider=provider_name,
            prompt_type=prompt_type,
            text="",
            confidence=0.0,
            time_ms=0,
            picks_found=[],
            picks_matched=0,
            picks_missed=len(ground_truth),
            error=str(e)
        )


def test_tesseract(image_path: str, ground_truth: List[str]) -> ProviderResult:
    """Test Tesseract (local, no prompt types)."""
    return test_provider("tesseract", None, image_path, "local", ground_truth)


# --- MAIN BENCHMARK ---

def run_benchmark(limit: int = 20, quick: bool = False) -> BenchmarkReport:
    """
    Run full OCR benchmark.
    
    Args:
        limit: Number of images to test
        quick: If True, only test Tesseract + 1 vision provider
    """
    start_time = time.time()
    
    # Load images from cache
    images_dir = os.path.join(BASE_DIR, "static", "temp_images")
    if not os.path.exists(images_dir):
        # Try alternate path
        images_dir = os.path.join(BASE_DIR, "temp_images")
    
    if not os.path.exists(images_dir):
        logging.error(f"Images directory not found: {images_dir}")
        return None
    
    # Get image files
    image_files = [
        os.path.join(images_dir, f) 
        for f in os.listdir(images_dir) 
        if f.endswith(('.jpg', '.jpeg', '.png'))
    ][:limit]
    
    logging.info(f"[Benchmark] Found {len(image_files)} images to benchmark")
    
    if not image_files:
        logging.error("No images found for benchmark")
        return None
    
    # Build provider list
    providers = [("tesseract", None, ["local"])]  # Tesseract is special
    
    prompt_types = ["structured", "raw"]
    
    # Always include available vision providers
    if os.getenv("GEMINI_TOKEN"):
        providers.append(("gemini", _call_gemini, prompt_types))
    if os.getenv("GROQ_TOKEN"):
        providers.append(("groq", _call_groq, prompt_types))
    if os.getenv("MISTRAL_TOKEN"):
        providers.append(("mistral", _call_mistral, prompt_types))
    
    # OpenRouter only in full mode (avoid duplicate Gemini calls)
    if os.getenv("OPENROUTER_API_KEY") and not quick:
        providers.append(("openrouter", _call_openrouter, prompt_types))
    
    logging.info(f"[Benchmark] Testing {len(providers)} providers")
    
    # Results storage
    image_results = []
    provider_stats = {}  # provider_name -> {prompt_type -> stats}
    ground_truth_model = "unknown"
    
    for i, image_path in enumerate(image_files):
        logging.info(f"[Benchmark] Image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
        
        # Get ground truth
        gt_picks, gt_model = get_ground_truth_picks(image_path)
        if i == 0:
            ground_truth_model = gt_model
        
        logging.info(f"  Ground truth ({gt_model}): {len(gt_picks)} picks")
        
        # Test each provider
        provider_results = []
        best_provider = None
        best_accuracy = 0.0
        
        for provider_name, provider_func, prompts in providers:
            for prompt_type in prompts:
                if provider_name == "tesseract":
                    result = test_tesseract(image_path, gt_picks)
                else:
                    result = test_provider(
                        provider_name, provider_func, 
                        image_path, prompt_type, gt_picks
                    )
                
                provider_results.append(result)
                
                # Track stats
                key = f"{provider_name}_{prompt_type}"
                if key not in provider_stats:
                    provider_stats[key] = {
                        "total_images": 0,
                        "total_picks_expected": 0,
                        "total_picks_matched": 0,
                        "total_picks_missed": 0,
                        "total_time_ms": 0,
                        "errors": 0,
                    }
                
                stats = provider_stats[key]
                stats["total_images"] += 1
                stats["total_picks_expected"] += len(gt_picks)
                stats["total_picks_matched"] += result.picks_matched
                stats["total_picks_missed"] += result.picks_missed
                stats["total_time_ms"] += result.time_ms
                if result.error:
                    stats["errors"] += 1
                
                # Track best
                if gt_picks:
                    accuracy = result.picks_matched / len(gt_picks)
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_provider = key
                
                logging.info(f"  {key}: {result.picks_matched}/{len(gt_picks)} picks, {result.time_ms}ms")
        
        image_results.append(ImageBenchmark(
            image_path=os.path.basename(image_path),
            ground_truth_picks=gt_picks,
            provider_results=provider_results,
            best_provider=best_provider or "none",
            best_accuracy=best_accuracy
        ))
    
    # Calculate summary stats
    provider_summary = {}
    for key, stats in provider_stats.items():
        total_expected = stats["total_picks_expected"] or 1
        provider_summary[key] = {
            "accuracy": round(stats["total_picks_matched"] / total_expected * 100, 1),
            "avg_time_ms": round(stats["total_time_ms"] / stats["total_images"]),
            "error_rate": round(stats["errors"] / stats["total_images"] * 100, 1),
            "total_matched": stats["total_picks_matched"],
            "total_missed": stats["total_picks_missed"],
        }
    
    # Generate recommendations
    recommendations = []
    
    # Find best overall
    sorted_providers = sorted(
        provider_summary.items(),
        key=lambda x: (x[1]["accuracy"], -x[1]["avg_time_ms"]),
        reverse=True
    )
    
    if sorted_providers:
        best = sorted_providers[0]
        recommendations.append(f"Best overall: {best[0]} ({best[1]['accuracy']}% accuracy, {best[1]['avg_time_ms']}ms avg)")
    
    # Find fastest with good accuracy
    fast_good = [
        (k, v) for k, v in provider_summary.items()
        if v["accuracy"] >= 70 and v["avg_time_ms"] < 2000
    ]
    if fast_good:
        fastest = min(fast_good, key=lambda x: x[1]["avg_time_ms"])
        recommendations.append(f"Fast + accurate: {fastest[0]} ({fastest[1]['accuracy']}%, {fastest[1]['avg_time_ms']}ms)")
    
    # Check Tesseract
    tess_stats = provider_summary.get("tesseract_local", {})
    if tess_stats.get("accuracy", 0) >= 60:
        recommendations.append(f"Tesseract viable for fast path: {tess_stats['accuracy']}% accuracy")
    else:
        recommendations.append(f"Tesseract needs improvement: only {tess_stats.get('accuracy', 0)}% accuracy")
    
    # Structured vs Raw
    structured_acc = [v["accuracy"] for k, v in provider_summary.items() if "structured" in k]
    raw_acc = [v["accuracy"] for k, v in provider_summary.items() if "raw" in k]
    
    if structured_acc and raw_acc:
        avg_structured = sum(structured_acc) / len(structured_acc)
        avg_raw = sum(raw_acc) / len(raw_acc)
        if avg_structured > avg_raw + 3:
            recommendations.append(f"Structured prompts better: {avg_structured:.1f}% vs {avg_raw:.1f}%")
        elif avg_raw > avg_structured + 3:
            recommendations.append(f"Raw prompts better: {avg_raw:.1f}% vs {avg_structured:.1f}%")
        else:
            recommendations.append(f"Prompt styles similar: structured={avg_structured:.1f}%, raw={avg_raw:.1f}%")
    
    elapsed = time.time() - start_time
    
    return BenchmarkReport(
        total_images=len(image_files),
        total_time_seconds=round(elapsed, 1),
        ground_truth_model=ground_truth_model,
        provider_summary=provider_summary,
        image_results=image_results,
        recommendations=recommendations
    )


def print_report(report: BenchmarkReport):
    """Print formatted benchmark report."""
    print("\n" + "=" * 70)
    print("OCR + PARSING BENCHMARK REPORT")
    print("=" * 70)
    
    print(f"\nTotal Images: {report.total_images}")
    print(f"Total Time: {report.total_time_seconds}s")
    print(f"Ground Truth Model: {report.ground_truth_model}")
    
    print("\n" + "-" * 70)
    print("PROVIDER COMPARISON")
    print("-" * 70)
    print(f"{'Provider':<30} {'Accuracy':>10} {'Avg Time':>10} {'Errors':>10}")
    print("-" * 70)
    
    sorted_providers = sorted(
        report.provider_summary.items(),
        key=lambda x: x[1]["accuracy"],
        reverse=True
    )
    
    for name, stats in sorted_providers:
        print(f"{name:<30} {stats['accuracy']:>9.1f}% {stats['avg_time_ms']:>8}ms {stats['error_rate']:>9.1f}%")
    
    print("\n" + "-" * 70)
    print("RECOMMENDATIONS")
    print("-" * 70)
    for rec in report.recommendations:
        print(f"  • {rec}")
    
    print("\n" + "=" * 70)


def save_report(report: BenchmarkReport, output_path: str):
    """Save report to JSON file."""
    # Convert to dict
    data = {
        "total_images": report.total_images,
        "total_time_seconds": report.total_time_seconds,
        "ground_truth_model": report.ground_truth_model,
        "provider_summary": report.provider_summary,
        "recommendations": report.recommendations,
        "image_results": [
            {
                "image": r.image_path,
                "ground_truth_picks": r.ground_truth_picks,
                "best_provider": r.best_provider,
                "best_accuracy": r.best_accuracy,
                "results": [asdict(pr) for pr in r.provider_results]
            }
            for r in report.image_results
        ]
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="OCR + Parsing Benchmark")
    parser.add_argument("--limit", type=int, default=20, help="Number of images to test")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer providers)")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()
    
    print(f"\n[OCR Benchmark] Starting with limit={args.limit}, quick={args.quick}\n")
    
    report = run_benchmark(limit=args.limit, quick=args.quick)
    
    if report:
        print_report(report)
        
        output_path = args.output or os.path.join(
            BASE_DIR, "benchmark", "reports", "ocr_benchmark_results.json"
        )
        save_report(report, output_path)
        
        print(f"\nFull report saved to: {output_path}")
    else:
        print("\n[ERROR] Benchmark failed - no report generated")


if __name__ == "__main__":
    main()
