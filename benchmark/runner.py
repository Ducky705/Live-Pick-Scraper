# benchmark/runner.py
"""
Core Benchmark Runner - Executes tests across all models.
Focuses on ACCURACY while tracking time as secondary metric.
"""

import os
import sys
import json
import time
import base64
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from benchmark.config import (
    MODELS_TO_TEST, 
    DEFAULT_RUNS, 
    REQUEST_TIMEOUT, 
    RATE_LIMIT_DELAY,
    is_vision_model
)
from benchmark.metrics import (
    CaseResult, 
    ModelResult, 
    match_picks_for_case, 
    parse_ai_response,
    calculate_composite_score
)
from src.prompt_builder import generate_ai_prompt
from src.ocr_handler import extract_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Runs benchmarks across multiple models and test cases."""
    
    def __init__(self, models: List[str] = None, runs: int = DEFAULT_RUNS, output_dir: str = "benchmark_results"):
        self.models = models or MODELS_TO_TEST
        self.runs = runs
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        self.base_dir = Path(__file__).parent.parent
        self.test_cases = self._load_test_cases()
        self.results: Dict[str, ModelResult] = {}
        
        # Progress tracking
        self.total_calls = len(self.models) * len(self.test_cases) * self.runs
        self.completed_calls = 0
        self.start_time = None
        
    def _load_test_cases(self) -> List[Dict]:
        """Load test cases from manifest.json."""
        manifest_path = self.base_dir / "tests" / "manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_ocr_text(self, image_path: str) -> str:
        """Extract OCR text from image."""
        full_path = self.base_dir / image_path
        if not full_path.exists():
            return f"[Image not found: {image_path}]"
        
        try:
            return extract_text(str(full_path))
        except Exception as e:
            return f"[OCR Error: {e}]"
    
    def _get_image_base64(self, image_path: str) -> Optional[str]:
        """Get base64 encoded image for vision models."""
        full_path = self.base_dir / image_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None
    
    def _build_prompt_for_case(self, test_case: Dict, for_vision: bool = False) -> str:
        """Build the prompt for a test case."""
        image_path = test_case.get("image_file", "")
        input_text = test_case.get("input_text", "")
        
        # Get OCR text from image
        ocr_text = self._get_ocr_text(image_path) if image_path else ""
        
        # Build message in the format expected by prompt_builder
        message = {
            "id": test_case.get("id", "unknown"),
            "text": input_text,
            "ocr_texts": [ocr_text] if ocr_text else [],
            "channel_name": "BenchmarkTest"
        }
        
        return generate_ai_prompt([message])
    
    def _call_api(self, model: str, prompt: str, image_b64: Optional[str] = None) -> tuple[str, float, Optional[str]]:
        """
        Call OpenRouter API and return (response, time_ms, error).
        Falls back to non-JSON mode if model doesn't support it.
        
        Returns:
            tuple: (response_content, response_time_ms, error_message)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-scraper.local",
            "X-Title": "CapperSuite-Benchmark"
        }
        
        # Build messages based on model type
        if image_b64 and is_vision_model(model):
            # Vision model with image
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }]
        else:
            # Text-only model
            messages = [{"role": "user", "content": prompt}]
        
        total_elapsed = 0
        # Try with JSON mode first, fallback without if 400 error
        for use_json_mode in [True, False]:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
            }
            if use_json_mode:
                payload["response_format"] = {"type": "json_object"}
            
            start = time.perf_counter()
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT
                )
                elapsed_ms = (time.perf_counter() - start) * 1000
                total_elapsed += elapsed_ms
                
                # If 400 error and we used JSON mode, retry without it
                if response.status_code == 400 and use_json_mode:
                    logger.debug(f"[{model}] JSON mode not supported, retrying without...")
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    # Clean markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        parts = content.split("```")
                        if len(parts) >= 2:
                            content = parts[1].strip()
                            if content.lower().startswith('json'):
                                content = content[4:].strip()
                    return content.strip(), total_elapsed, None
                else:
                    return "", total_elapsed, "No choices in response"
                    
            except requests.exceptions.Timeout:
                elapsed_ms = (time.perf_counter() - start) * 1000
                return "", elapsed_ms, f"Timeout after {REQUEST_TIMEOUT}s"
            except requests.exceptions.RequestException as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                total_elapsed += elapsed_ms
                if use_json_mode and "400" in str(e):
                    continue  # Retry without JSON mode
                return "", total_elapsed, str(e)
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                return "", elapsed_ms, f"Unexpected error: {e}"
        
        # If we get here, both attempts failed
        return "", total_elapsed, "Model does not support this request format"

    
    def run_single_case(self, model: str, test_case: Dict, run_idx: int) -> CaseResult:
        """Run a single test case for a model."""
        case_id = test_case.get("id", "unknown")
        expected_picks = test_case.get("expected_picks", [])
        
        # Build prompt
        prompt = self._build_prompt_for_case(test_case)
        
        # Get image for vision models
        image_b64 = None
        if is_vision_model(model) and test_case.get("image_file"):
            image_b64 = self._get_image_base64(test_case["image_file"])
        
        # Call API
        response, time_ms, error = self._call_api(model, prompt, image_b64)
        
        # Parse response
        if error:
            return CaseResult(
                case_id=case_id,
                model=model,
                run_index=run_idx,
                response_time_ms=time_ms,
                parse_success=False,
                error_message=error,
                expected_count=len(expected_picks),
                extracted_count=0,
                pick_matches=[]
            )
        
        extracted_picks = parse_ai_response(response)
        
        if not extracted_picks and expected_picks:
            return CaseResult(
                case_id=case_id,
                model=model,
                run_index=run_idx,
                response_time_ms=time_ms,
                parse_success=True,
                error_message="No picks extracted",
                expected_count=len(expected_picks),
                extracted_count=0,
                pick_matches=[]
            )
        
        # Match picks
        pick_matches = match_picks_for_case(expected_picks, extracted_picks)
        
        return CaseResult(
            case_id=case_id,
            model=model,
            run_index=run_idx,
            response_time_ms=time_ms,
            parse_success=True,
            error_message=None,
            expected_count=len(expected_picks),
            extracted_count=len(extracted_picks),
            pick_matches=pick_matches
        )
    
    def run_model(self, model: str) -> ModelResult:
        """Run all test cases for a single model."""
        logger.info(f"🔬 Testing model: {model}")
        result = ModelResult(model=model)
        
        for test_case in self.test_cases:
            for run_idx in range(self.runs):
                case_result = self.run_single_case(model, test_case, run_idx)
                result.case_results.append(case_result)
                
                self.completed_calls += 1
                self._print_progress(model, test_case.get("id", ""), run_idx, case_result)
                
                # Rate limiting delay
                time.sleep(RATE_LIMIT_DELAY)
        
        result.compute_aggregates()
        return result
    
    def _print_progress(self, model: str, case_id: str, run_idx: int, result: CaseResult):
        """Print progress update."""
        elapsed = time.time() - self.start_time
        pct = (self.completed_calls / self.total_calls) * 100
        
        status = "✓" if result.parse_success and result.f1_score > 0.5 else "✗"
        eta = (elapsed / self.completed_calls) * (self.total_calls - self.completed_calls) if self.completed_calls > 0 else 0
        
        logger.info(
            f"[{pct:5.1f}%] {status} {model[:40]:40} | "
            f"F1: {result.f1_score:.2f} | "
            f"Time: {result.response_time_ms:6.0f}ms | "
            f"ETA: {eta/60:.1f}min"
        )
    
    def run_all(self) -> Dict[str, ModelResult]:
        """Run benchmarks for all models."""
        logger.info(f"🚀 Starting benchmark: {len(self.models)} models × {len(self.test_cases)} cases × {self.runs} runs = {self.total_calls} API calls")
        self.start_time = time.time()
        
        for model in self.models:
            try:
                result = self.run_model(model)
                self.results[model] = result
                
                # Save intermediate results after each model
                self._save_results()
                
                logger.info(f"📊 {model}: F1={result.avg_f1:.3f}, Accuracy={result.avg_accuracy:.3f}, Time={result.avg_response_time_ms:.0f}ms")
                
            except Exception as e:
                logger.error(f"❌ Failed to benchmark {model}: {e}")
                self.results[model] = ModelResult(model=model)
        
        total_time = time.time() - self.start_time
        logger.info(f"✅ Benchmark complete in {total_time/60:.1f} minutes")
        
        return self.results
    
    def _save_results(self):
        """Save current results to JSON."""
        output_file = self.output_dir / "raw_results.json"
        
        # Convert dataclasses to dicts
        serializable = {}
        for model, result in self.results.items():
            serializable[model] = {
                "model": result.model,
                "avg_accuracy": result.avg_accuracy,
                "avg_f1": result.avg_f1,
                "avg_response_time_ms": result.avg_response_time_ms,
                "median_response_time_ms": result.median_response_time_ms,
                "p95_response_time_ms": result.p95_response_time_ms,
                "total_time_ms": result.total_time_ms,
                "parse_success_rate": result.parse_success_rate,
                "consistency_score": result.consistency_score,
                "field_accuracy": result.field_accuracy,
                "composite_score": calculate_composite_score(result),
                "num_cases": len(result.case_results),
                "case_results": [
                    {
                        "case_id": cr.case_id,
                        "run_index": cr.run_index,
                        "response_time_ms": cr.response_time_ms,
                        "parse_success": cr.parse_success,
                        "error_message": cr.error_message,
                        "expected_count": cr.expected_count,
                        "extracted_count": cr.extracted_count,
                        "precision": cr.precision,
                        "recall": cr.recall,
                        "f1_score": cr.f1_score
                    }
                    for cr in result.case_results
                ]
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2)
        
        logger.info(f"💾 Results saved to {output_file}")


def run_benchmark(
    models: List[str] = None,
    runs: int = DEFAULT_RUNS,
    cases: int = None,
    output_dir: str = "benchmark_results"
) -> Dict[str, ModelResult]:
    """
    Convenience function to run benchmark.
    
    Args:
        models: List of model names to test (None = all)
        runs: Number of runs per test case
        cases: Max number of test cases to use (None = all)
        output_dir: Directory to save results
    """
    runner = BenchmarkRunner(models=models, runs=runs, output_dir=output_dir)
    
    if cases:
        runner.test_cases = runner.test_cases[:cases]
        runner.total_calls = len(runner.models) * len(runner.test_cases) * runner.runs
    
    return runner.run_all()
