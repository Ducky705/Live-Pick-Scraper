"""
OCR Cascade Engine
==================
Smart OCR with RapidOCR fast-path and parallel Vision API fallback.

UPDATED: Now uses RapidOCR (ONNX-based PaddleOCR) instead of Tesseract
for significantly better local OCR accuracy on complex betting images.

BENCHMARK RESULTS (Jan 21, 2026):
| Model                | Avg Time | Picks/Img | Success | Status      |
|----------------------|----------|-----------|---------|-------------|
| Mistral Pixtral Large| 16,242ms | 4.2       | 100%    | BEST        |
| OR Gemma 3 27B       | 16,475ms | 4.4       | 100%    | GOOD        |
| OR Gemma 3 12B       | 19,189ms | 4.2       | 100%    | GOOD        |
| OR Gemini 2.0 Flash  | 58,029ms | 2.2       | 100%    | RATE-LIMITED|
| Groq (all models)    | <500ms   | 0.0       | 0%      | NO VISION   |
| Cerebras (all models)| <500ms   | 0.0       | 0%      | NO VISION   |

FINDINGS:
- Groq: HTTP 400 "content must be a string" - does NOT support vision
- Cerebras: HTTP 422 "image content type not supported" - NO vision
- Gemini 2.0 Flash: Heavily rate-limited on free tier (429 errors)
- Mistral Pixtral Large: Most reliable, best pick extraction

Architecture:
1. RAPIDOCR (local, ~0.5-2s) - Uses preprocess_for_rapidocr, validates with ocr_validator
2. VISION RACE (parallel providers) - First success wins
   - Mistral (Pixtral Large) - MOST RELIABLE
   - OpenRouter (Gemma 3 models) - Good fallback
   - Gemini Direct (if configured)

Usage:
    from src.ocr_cascade import OCRCascade, extract_text_cascade
    
    # Single image
    text = extract_text_cascade(image_path)
    
    # Batch with provider distribution
    results = extract_batch_cascade(image_paths)
"""

import os
import sys
import logging
import time
import base64
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

# Setup paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.ocr_validator import is_usable_ocr, validate_ocr_detailed, OCRQuality


class OCRMethod(Enum):
    """OCR method used."""
    RAPIDOCR = "rapidocr"
    TESSERACT = "tesseract"  # Kept for backward compatibility (now aliases RAPIDOCR)
    GEMINI = "gemini"
    MISTRAL = "mistral"
    OPENROUTER = "openrouter"
    FAILED = "failed"


@dataclass
class OCRResult:
    """Result from OCR operation."""
    text: str
    method: OCRMethod
    confidence: float
    time_ms: int
    prompt_type: str  # "structured" or "raw"
    error: Optional[str] = None


# --- PROMPTS ---

STRUCTURED_PROMPT = """Extract betting information from this image.

Return JSON:
{
  "capper": "name if visible, else null",
  "text": "all readable text from the image",
  "picks": ["pick 1 exactly as written", "pick 2"]
}

IMPORTANT:
- Extract ALL text, especially team names, spreads (+/-X.X), totals (over/under), odds
- IGNORE watermarks like @cappersfree
- IGNORE promotional text like "DM for picks"
- If multiple picks, list them all in the picks array"""

RAW_PROMPT = """Extract all text from this image exactly as written.
Return only the text content, preserve line breaks.
Do not add any commentary or explanation."""


# --- LOCAL OCR (RapidOCR) ---

def _run_local_ocr(image_path: str) -> OCRResult:
    """
    Run local OCR using RapidOCR with optimized preprocessing.
    
    RapidOCR is a ONNX-based implementation of PaddleOCR that provides
    significantly better accuracy than Tesseract on complex images.
    """
    import cv2
    from src.ocr_engine import get_ocr_engine
    from src.ocr_preprocessing import preprocess_for_rapidocr
    
    start = time.time()
    
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return OCRResult(
                text="",
                method=OCRMethod.RAPIDOCR,
                confidence=0.0,
                time_ms=int((time.time() - start) * 1000),
                prompt_type="local",
                error="Could not read image"
            )
        
        # Preprocess for RapidOCR (grayscale with contrast, NOT binary)
        processed = preprocess_for_rapidocr(img)
        
        # Run RapidOCR
        ocr_engine = get_ocr_engine()
        if not ocr_engine.is_available():
            return OCRResult(
                text="",
                method=OCRMethod.RAPIDOCR,
                confidence=0.0,
                time_ms=int((time.time() - start) * 1000),
                prompt_type="local",
                error="RapidOCR not available"
            )
        
        text, confidence = ocr_engine.extract_text_with_confidence(processed)
        text = text.strip()
        
        # Validate with our OCR validator
        is_good, val_confidence, reasons = is_usable_ocr(text)
        
        # Use the lower of RapidOCR confidence and validator confidence
        final_confidence = min(confidence, val_confidence)
        
        elapsed = int((time.time() - start) * 1000)
        
        return OCRResult(
            text=text,
            method=OCRMethod.RAPIDOCR,
            confidence=final_confidence,
            time_ms=elapsed,
            prompt_type="local",
            error=None if is_good else "; ".join(reasons)
        )
        
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] RapidOCR error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.RAPIDOCR,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type="local",
            error=str(e)
        )


# Alias for backward compatibility
_run_tesseract = _run_local_ocr


# --- VISION PROVIDERS ---

def _encode_image(image_path: str) -> Optional[str]:
    """Encode image to base64."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logging.error(f"[OCR Cascade] Failed to encode image: {e}")
        return None


def _call_gemini(image_path: str, prompt: str, prompt_type: str) -> OCRResult:
    """Call Gemini Direct API."""
    start = time.time()
    
    try:
        from src.gemini_client import gemini_vision_completion
        
        response = gemini_vision_completion(prompt, image_path)
        elapsed = int((time.time() - start) * 1000)
        
        if response:
            # Extract text from JSON if structured
            text = _extract_text_from_response(response, prompt_type)
            is_good, confidence, _ = is_usable_ocr(text)
            
            return OCRResult(
                text=text,
                method=OCRMethod.GEMINI,
                confidence=confidence,
                time_ms=elapsed,
                prompt_type=prompt_type
            )
        else:
            return OCRResult(
                text="",
                method=OCRMethod.GEMINI,
                confidence=0.0,
                time_ms=elapsed,
                prompt_type=prompt_type,
                error="No response from Gemini"
            )
            
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] Gemini error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.GEMINI,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type=prompt_type,
            error=str(e)
        )


def _call_mistral(image_path: str, prompt: str, prompt_type: str) -> OCRResult:
    """Call Mistral API with Pixtral Large (best vision model)."""
    start = time.time()
    
    try:
        from src.mistral_client import mistral_completion, PIXTRAL_LARGE
        
        response = mistral_completion(prompt, model=PIXTRAL_LARGE, image_input=image_path, validate_json=False)
        elapsed = int((time.time() - start) * 1000)
        
        if response:
            text = _extract_text_from_response(response, prompt_type)
            is_good, confidence, _ = is_usable_ocr(text)
            
            return OCRResult(
                text=text,
                method=OCRMethod.MISTRAL,
                confidence=confidence,
                time_ms=elapsed,
                prompt_type=prompt_type
            )
        else:
            return OCRResult(
                text="",
                method=OCRMethod.MISTRAL,
                confidence=0.0,
                time_ms=elapsed,
                prompt_type=prompt_type,
                error="No response from Mistral"
            )
            
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] Mistral error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.MISTRAL,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type=prompt_type,
            error=str(e)
        )


def _call_openrouter(image_path: str, prompt: str, prompt_type: str) -> OCRResult:
    """
    Call OpenRouter with Gemma 3 27B (reliable vision model).
    
    Benchmark (Jan 21, 2026):
    - Gemma 3 27B: 16.5s avg, 4.4 picks/image, 100% success
    - Gemini 2.0 Flash: Rate-limited on free tier (429 errors)
    """
    start = time.time()
    
    try:
        from src.openrouter_client import openrouter_completion
        
        # Gemma 3 27B is reliable - Gemini 2.0 Flash is rate-limited on free tier
        model = "google/gemma-3-27b-it:free"
        
        b64 = _encode_image(image_path)
        if not b64:
            return OCRResult(
                text="",
                method=OCRMethod.OPENROUTER,
                confidence=0.0,
                time_ms=int((time.time() - start) * 1000),
                prompt_type=prompt_type,
                error="Failed to encode image"
            )
        
        response = openrouter_completion(prompt, model=model, images=[b64], validate_json=False)
        elapsed = int((time.time() - start) * 1000)
        
        if response:
            text = _extract_text_from_response(response, prompt_type)
            is_good, confidence, _ = is_usable_ocr(text)
            
            return OCRResult(
                text=text,
                method=OCRMethod.OPENROUTER,
                confidence=confidence,
                time_ms=elapsed,
                prompt_type=prompt_type
            )
        else:
            return OCRResult(
                text="",
                method=OCRMethod.OPENROUTER,
                confidence=0.0,
                time_ms=elapsed,
                prompt_type=prompt_type,
                error="No response from OpenRouter"
            )
            
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] OpenRouter error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.OPENROUTER,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type=prompt_type,
            error=str(e)
        )


def _extract_text_from_response(response: str, prompt_type: str) -> str:
    """Extract text from API response based on prompt type."""
    import json
    
    if not response:
        return ""
    
    response = response.strip()
    
    # Clean markdown code blocks
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        response = response.split("```")[1].split("```")[0].strip()
    
    if prompt_type == "structured":
        try:
            data = json.loads(response)
            
            # Handle array response (just join elements)
            if isinstance(data, list):
                return "\n".join(str(item) for item in data if item)
            
            # Handle dict response
            if not isinstance(data, dict):
                return str(data)
            
            # Try to extract text field
            text_parts = []
            
            if data.get("text"):
                text_parts.append(data["text"])
            
            if data.get("capper"):
                text_parts.insert(0, data["capper"])
            
            if data.get("picks") and isinstance(data["picks"], list):
                text_parts.extend(data["picks"])
            
            return "\n".join(str(p) for p in text_parts if p)
            
        except json.JSONDecodeError:
            # Fallback to raw response
            return response
    else:
        # Raw prompt - return as-is
        return response


# --- CASCADE ENGINE ---

class OCRCascade:
    """
    Smart OCR engine with RapidOCR fast-path and parallel Vision fallback.
    
    Based on benchmarks (Jan 21, 2026), the provider priority is:
    1. Mistral (Pixtral Large) - 16.2s, 100% success, 4.2 picks/image - MOST RELIABLE
    2. OpenRouter (Gemma 3 models) - 16-19s, 100% success, 4.2-4.4 picks/image
    3. Gemini Direct (if available)
    
    NOTE: OpenRouter Gemini 2.0 Flash is rate-limited on free tier (429 errors)
    
    DISABLED providers (confirmed via API testing):
    - Groq: HTTP 400 - content must be a string (NO multimodal support)
    - Cerebras: HTTP 422 - image content type not supported (NO vision)
    """
    
    def __init__(self, local_threshold: float = 0.6):
        """
        Args:
            local_threshold: Minimum confidence to accept local OCR result (0.0-1.0)
        """
        self.local_threshold = local_threshold
        # Keep old name for backward compatibility
        self.tesseract_threshold = local_threshold
        
        # Check which providers are available
        self.gemini_available = bool(os.getenv("GEMINI_TOKEN"))
        self.mistral_available = bool(os.getenv("MISTRAL_TOKEN"))
        self.openrouter_available = bool(os.getenv("OPENROUTER_API_KEY"))
        
        # NOTE: Groq and Cerebras are DISABLED based on benchmarks
        # Groq: All vision models failed or are decommissioned
        # Cerebras: Text-only, cannot see images
        
        logging.info(f"[OCR Cascade] Initialized. Vision Providers: "
                     f"OpenRouter={self.openrouter_available}, "
                     f"Mistral={self.mistral_available}, "
                     f"Gemini={self.gemini_available}")
    
    def extract(self, image_path: str, prompt_type: str = "structured") -> OCRResult:
        """
        Extract text from image using cascade approach.
        
        Args:
            image_path: Path to image file
            prompt_type: "structured" or "raw" - which prompt style for vision APIs
        
        Returns:
            OCRResult with best extraction
        """
        if not os.path.exists(image_path):
            return OCRResult(
                text="",
                method=OCRMethod.FAILED,
                confidence=0.0,
                time_ms=0,
                prompt_type=prompt_type,
                error=f"Image not found: {image_path}"
            )
        
        # Step 1: Try RapidOCR (fast path)
        logging.debug(f"[OCR Cascade] Step 1: RapidOCR for {os.path.basename(image_path)}")
        local_result = _run_local_ocr(image_path)
        
        if local_result.confidence >= self.local_threshold:
            logging.info(f"[OCR Cascade] RapidOCR success (confidence={local_result.confidence:.2f})")
            return local_result
        
        logging.debug(f"[OCR Cascade] RapidOCR low confidence ({local_result.confidence:.2f}), trying Vision APIs")
        
        # Step 2: Race Vision providers in parallel
        prompt = STRUCTURED_PROMPT if prompt_type == "structured" else RAW_PROMPT
        vision_result = self._race_vision_providers(image_path, prompt, prompt_type)
        
        # Step 3: Return best result
        if vision_result.confidence > local_result.confidence:
            return vision_result
        elif local_result.confidence > 0.3:  # Local OCR has something
            return local_result
        elif vision_result.text:  # Vision has something
            return vision_result
        else:
            return OCRResult(
                text=local_result.text or vision_result.text or "",
                method=OCRMethod.FAILED,
                confidence=0.0,
                time_ms=local_result.time_ms + vision_result.time_ms,
                prompt_type=prompt_type,
                error="All OCR methods failed"
            )
    
    def _race_vision_providers(self, image_path: str, prompt: str, prompt_type: str) -> OCRResult:
        """
        Race vision providers in parallel. First good result wins.
        
        Provider priority (based on Jan 21, 2026 benchmarks):
        1. Mistral (Pixtral Large) - 16.2s, 100% success - MOST RELIABLE
        2. OpenRouter (Gemma 3 models) - 16-19s, 100% success - Good fallback
        3. Gemini Direct - if available
        
        NOTE: Gemini 2.0 Flash is rate-limited on free tier (429 errors)
        """
        # Build list of available providers (ordered by reliability)
        providers = []
        
        # Mistral Pixtral Large - MOST RELIABLE (16.2s, 100% success, 4.2 picks)
        if self.mistral_available:
            providers.append(("mistral", _call_mistral))
        
        # OpenRouter with Gemma 3 models - Good fallback (16-19s, 100% success)
        # Note: Gemini 2.0 Flash is rate-limited, Gemma models are more reliable
        if self.openrouter_available:
            providers.append(("openrouter", _call_openrouter))
        
        # Gemini Direct - Only if others unavailable
        if self.gemini_available:
            providers.append(("gemini", _call_gemini))
        
        if not providers:
            return OCRResult(
                text="",
                method=OCRMethod.FAILED,
                confidence=0.0,
                time_ms=0,
                prompt_type=prompt_type,
                error="No vision providers available"
            )
        
        logging.debug(f"[OCR Cascade] Racing {len(providers)} vision providers...")
        
        best_result = None
        
        # Run providers in parallel
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {
                executor.submit(func, image_path, prompt, prompt_type): name
                for name, func in providers
            }
            
            for future in as_completed(futures, timeout=120):
                provider_name = futures[future]
                try:
                    result = future.result()
                    
                    logging.debug(f"[OCR Cascade] {provider_name}: confidence={result.confidence:.2f}, time={result.time_ms}ms")
                    
                    # Accept first good result
                    if result.confidence >= 0.6:
                        logging.info(f"[OCR Cascade] {provider_name} won race (confidence={result.confidence:.2f})")
                        return result
                    
                    # Track best so far
                    if best_result is None or result.confidence > best_result.confidence:
                        best_result = result
                        
                except Exception as e:
                    logging.error(f"[OCR Cascade] {provider_name} error: {e}")
        
        # Return best result even if below threshold
        if best_result:
            return best_result
        
        return OCRResult(
            text="",
            method=OCRMethod.FAILED,
            confidence=0.0,
            time_ms=0,
            prompt_type=prompt_type,
            error="All vision providers failed"
        )
    
    def extract_batch(
        self, 
        image_paths: List[str], 
        prompt_type: str = "structured"
    ) -> List[OCRResult]:
        """
        Extract text from multiple images with smart provider distribution.
        
        Strategy:
        1. Run RapidOCR on ALL images in parallel (fast)
        2. Distribute Vision API calls across providers (parallel across providers, sequential within)
        """
        results: List[Optional[OCRResult]] = [None] * len(image_paths)
        needs_vision = []  # (index, path) tuples
        
        logging.info(f"[OCR Cascade] Batch processing {len(image_paths)} images...")
        
        # Step 1: Parallel RapidOCR
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run_local_ocr, path): i
                for i, path in enumerate(image_paths)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    
                    if result.confidence >= self.local_threshold:
                        results[idx] = result
                    else:
                        needs_vision.append((idx, image_paths[idx]))
                        results[idx] = result  # Store as fallback
                except Exception as e:
                    logging.error(f"[OCR Cascade] RapidOCR batch error: {e}")
                    needs_vision.append((idx, image_paths[idx]))
        
        local_success = len(image_paths) - len(needs_vision)
        logging.info(f"[OCR Cascade] RapidOCR: {local_success}/{len(image_paths)} success, {len(needs_vision)} need Vision")
        
        if not needs_vision:
            return [r for r in results if r is not None]
        
        # Step 2: Distribute Vision calls across providers
        prompt = STRUCTURED_PROMPT if prompt_type == "structured" else RAW_PROMPT
        
        # Build provider list (ordered by reliability from benchmarks)
        providers = []
        if self.mistral_available:
            providers.append(("mistral", _call_mistral))
        if self.openrouter_available:
            providers.append(("openrouter", _call_openrouter))
        if self.gemini_available:
            providers.append(("gemini", _call_gemini))
        
        if not providers:
            logging.warning("[OCR Cascade] No vision providers available for batch")
            return [r if r is not None else OCRResult(text="", method=OCRMethod.FAILED, confidence=0.0, time_ms=0, prompt_type=prompt_type, error="No provider") for r in results]
        
        # Distribute images across providers (round-robin)
        provider_queues: Dict[str, List[Tuple[int, str]]] = {name: [] for name, _ in providers}
        for i, (idx, path) in enumerate(needs_vision):
            provider_name = providers[i % len(providers)][0]
            provider_queues[provider_name].append((idx, path))
        
        # Process each provider's queue in parallel (providers parallel, within sequential)
        def process_queue(provider_name: str, func, queue: List[Tuple[int, str]]) -> List[Tuple[int, OCRResult]]:
            queue_results = []
            for idx, path in queue:
                try:
                    result = func(path, prompt, prompt_type)
                    queue_results.append((idx, result))
                except Exception as e:
                    logging.error(f"[OCR Cascade] {provider_name} failed for {path}: {e}")
                    queue_results.append((idx, OCRResult(
                        text="",
                        method=OCRMethod.FAILED,
                        confidence=0.0,
                        time_ms=0,
                        prompt_type=prompt_type,
                        error=str(e)
                    )))
            return queue_results
        
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = []
            for name, func in providers:
                if provider_queues[name]:
                    futures.append(executor.submit(process_queue, name, func, provider_queues[name]))
            
            for future in as_completed(futures):
                try:
                    queue_results = future.result()
                    for idx, result in queue_results:
                        # Use vision result if better than tesseract fallback
                        current = results[idx]
                        if current is None or result.confidence > current.confidence:
                            results[idx] = result
                except Exception as e:
                    logging.error(f"[OCR Cascade] Provider queue error: {e}")
        
        # Ensure no None values
        return [r if r is not None else OCRResult(text="", method=OCRMethod.FAILED, confidence=0.0, time_ms=0, prompt_type=prompt_type, error="Not processed") for r in results]


# --- CONVENIENCE FUNCTIONS ---

_cascade_instance = None


def get_cascade() -> OCRCascade:
    """Get or create singleton cascade instance."""
    global _cascade_instance
    if _cascade_instance is None:
        _cascade_instance = OCRCascade()
    return _cascade_instance


def extract_text_cascade(image_path: str, prompt_type: str = "structured") -> str:
    """
    Extract text from image using cascade OCR.
    
    This is the main entry point for single image OCR.
    
    Args:
        image_path: Path to image file
        prompt_type: "structured" or "raw"
    
    Returns:
        Extracted text string
    """
    cascade = get_cascade()
    result = cascade.extract(image_path, prompt_type)
    return result.text


def extract_batch_cascade(image_paths: List[str], prompt_type: str = "structured") -> List[str]:
    """
    Extract text from multiple images using cascade OCR.
    
    Args:
        image_paths: List of image paths
        prompt_type: "structured" or "raw"
    
    Returns:
        List of extracted text strings
    """
    cascade = get_cascade()
    results = cascade.extract_batch(image_paths, prompt_type)
    return [r.text if r else "" for r in results]
