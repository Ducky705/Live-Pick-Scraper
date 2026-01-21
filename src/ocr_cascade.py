"""
OCR Cascade Engine
==================
Smart OCR with Tesseract fast-path and parallel Vision API fallback.

Architecture:
1. TESSERACT (local, ~0.5s) - Uses preprocess_v3, validates with ocr_validator
2. VISION RACE (parallel providers) - First success wins
   - Gemini Direct
   - Groq (Llama 4 Scout)
   - Mistral (Pixtral)
   - OpenRouter fallback

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
    TESSERACT = "tesseract"
    GEMINI = "gemini"
    GROQ = "groq"
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


# --- TESSERACT ---

def _run_tesseract(image_path: str) -> OCRResult:
    """Run Tesseract OCR with v3 preprocessing."""
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    
    start = time.time()
    
    try:
        # Import preprocessing from new utility module
        from src.ocr_preprocessing import preprocess_image_v3
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return OCRResult(
                text="",
                method=OCRMethod.TESSERACT,
                confidence=0.0,
                time_ms=int((time.time() - start) * 1000),
                prompt_type="local",
                error="Could not read image"
            )
        
        # Preprocess
        processed = preprocess_image_v3(img)
        
        # Run Tesseract
        text = pytesseract.image_to_string(processed, config='--psm 6').strip()
        
        # Validate
        is_good, confidence, reasons = is_usable_ocr(text)
        
        elapsed = int((time.time() - start) * 1000)
        
        return OCRResult(
            text=text,
            method=OCRMethod.TESSERACT,
            confidence=confidence,
            time_ms=elapsed,
            prompt_type="local",
            error=None if is_good else "; ".join(reasons)
        )
        
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] Tesseract error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.TESSERACT,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type="local",
            error=str(e)
        )


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


def _call_groq(image_path: str, prompt: str, prompt_type: str) -> OCRResult:
    """Call Groq API with Llama 4 Vision."""
    start = time.time()
    
    try:
        from src.groq_client import groq_vision_completion, VISION_MODELS
        
        # Use Llama 4 Scout (faster)
        model = VISION_MODELS[0] if VISION_MODELS else "meta-llama/llama-4-scout-17b-16e-instruct"
        
        response = groq_vision_completion(prompt, image_path, model=model)
        elapsed = int((time.time() - start) * 1000)
        
        if response:
            text = _extract_text_from_response(response, prompt_type)
            is_good, confidence, _ = is_usable_ocr(text)
            
            return OCRResult(
                text=text,
                method=OCRMethod.GROQ,
                confidence=confidence,
                time_ms=elapsed,
                prompt_type=prompt_type
            )
        else:
            return OCRResult(
                text="",
                method=OCRMethod.GROQ,
                confidence=0.0,
                time_ms=elapsed,
                prompt_type=prompt_type,
                error="No response from Groq"
            )
            
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logging.error(f"[OCR Cascade] Groq error: {e}")
        return OCRResult(
            text="",
            method=OCRMethod.GROQ,
            confidence=0.0,
            time_ms=elapsed,
            prompt_type=prompt_type,
            error=str(e)
        )


def _call_mistral(image_path: str, prompt: str, prompt_type: str) -> OCRResult:
    """Call Mistral API with Pixtral."""
    start = time.time()
    
    try:
        from src.mistral_client import mistral_completion, PIXTRAL_12B
        
        response = mistral_completion(prompt, model=PIXTRAL_12B, image_input=image_path, validate_json=False)
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
    """Call OpenRouter as fallback."""
    start = time.time()
    
    try:
        from src.openrouter_client import openrouter_completion, VISION_MODELS
        
        model = VISION_MODELS[0] if VISION_MODELS else "google/gemini-2.0-flash-exp:free"
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
    Smart OCR engine with Tesseract fast-path and parallel Vision fallback.
    """
    
    def __init__(self, tesseract_threshold: float = 0.6):
        """
        Args:
            tesseract_threshold: Minimum confidence to accept Tesseract result (0.0-1.0)
        """
        self.tesseract_threshold = tesseract_threshold
        
        # Check which providers are available
        self.gemini_available = bool(os.getenv("GEMINI_TOKEN"))
        self.groq_available = bool(os.getenv("GROQ_TOKEN"))
        self.mistral_available = bool(os.getenv("MISTRAL_TOKEN"))
        self.openrouter_available = bool(os.getenv("OPENROUTER_API_KEY"))
        
        logging.info(f"[OCR Cascade] Initialized. Providers: "
                     f"Gemini={self.gemini_available}, Groq={self.groq_available}, "
                     f"Mistral={self.mistral_available}, OpenRouter={self.openrouter_available}")
    
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
        
        # Step 1: Try Tesseract (fast path)
        logging.debug(f"[OCR Cascade] Step 1: Tesseract for {os.path.basename(image_path)}")
        tess_result = _run_tesseract(image_path)
        
        if tess_result.confidence >= self.tesseract_threshold:
            logging.info(f"[OCR Cascade] Tesseract success (confidence={tess_result.confidence:.2f})")
            return tess_result
        
        logging.debug(f"[OCR Cascade] Tesseract low confidence ({tess_result.confidence:.2f}), trying Vision APIs")
        
        # Step 2: Race Vision providers in parallel
        prompt = STRUCTURED_PROMPT if prompt_type == "structured" else RAW_PROMPT
        vision_result = self._race_vision_providers(image_path, prompt, prompt_type)
        
        # Step 3: Return best result
        if vision_result.confidence > tess_result.confidence:
            return vision_result
        elif tess_result.confidence > 0.3:  # Tesseract has something
            return tess_result
        elif vision_result.text:  # Vision has something
            return vision_result
        else:
            return OCRResult(
                text=tess_result.text or vision_result.text or "",
                method=OCRMethod.FAILED,
                confidence=0.0,
                time_ms=tess_result.time_ms + vision_result.time_ms,
                prompt_type=prompt_type,
                error="All OCR methods failed"
            )
    
    def _race_vision_providers(self, image_path: str, prompt: str, prompt_type: str) -> OCRResult:
        """
        Race vision providers in parallel. First good result wins.
        """
        # Build list of available providers
        providers = []
        if self.gemini_available:
            providers.append(("gemini", _call_gemini))
        if self.groq_available:
            providers.append(("groq", _call_groq))
        if self.mistral_available:
            providers.append(("mistral", _call_mistral))
        if self.openrouter_available:
            providers.append(("openrouter", _call_openrouter))
        
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
        1. Run Tesseract on ALL images in parallel (fast)
        2. Distribute Vision API calls across providers (parallel across providers, sequential within)
        """
        results = [None] * len(image_paths)
        needs_vision = []  # (index, path) tuples
        
        logging.info(f"[OCR Cascade] Batch processing {len(image_paths)} images...")
        
        # Step 1: Parallel Tesseract
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run_tesseract, path): i
                for i, path in enumerate(image_paths)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    
                    if result.confidence >= self.tesseract_threshold:
                        results[idx] = result
                    else:
                        needs_vision.append((idx, image_paths[idx]))
                        results[idx] = result  # Store as fallback
                except Exception as e:
                    logging.error(f"[OCR Cascade] Tesseract batch error: {e}")
                    needs_vision.append((idx, image_paths[idx]))
        
        tess_success = len(image_paths) - len(needs_vision)
        logging.info(f"[OCR Cascade] Tesseract: {tess_success}/{len(image_paths)} success, {len(needs_vision)} need Vision")
        
        if not needs_vision:
            return results
        
        # Step 2: Distribute Vision calls across providers
        prompt = STRUCTURED_PROMPT if prompt_type == "structured" else RAW_PROMPT
        
        # Build provider list
        providers = []
        if self.gemini_available:
            providers.append(("gemini", _call_gemini))
        if self.groq_available:
            providers.append(("groq", _call_groq))
        if self.mistral_available:
            providers.append(("mistral", _call_mistral))
        if self.openrouter_available:
            providers.append(("openrouter", _call_openrouter))
        
        if not providers:
            logging.warning("[OCR Cascade] No vision providers available for batch")
            return results
        
        # Distribute images across providers (round-robin)
        provider_queues = {name: [] for name, _ in providers}
        for i, (idx, path) in enumerate(needs_vision):
            provider_name = providers[i % len(providers)][0]
            provider_queues[provider_name].append((idx, path))
        
        # Process each provider's queue in parallel (providers parallel, within sequential)
        def process_queue(provider_name: str, func, queue: List[Tuple[int, str]]) -> List[Tuple[int, OCRResult]]:
            results = []
            for idx, path in queue:
                try:
                    result = func(path, prompt, prompt_type)
                    results.append((idx, result))
                except Exception as e:
                    logging.error(f"[OCR Cascade] {provider_name} failed for {path}: {e}")
                    results.append((idx, OCRResult(
                        text="",
                        method=OCRMethod.FAILED,
                        confidence=0.0,
                        time_ms=0,
                        prompt_type=prompt_type,
                        error=str(e)
                    )))
            return results
        
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
                        if results[idx] is None or result.confidence > results[idx].confidence:
                            results[idx] = result
                except Exception as e:
                    logging.error(f"[OCR Cascade] Provider queue error: {e}")
        
        return results


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
