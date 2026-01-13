"""
Auto Processor Module
=====================
Intelligent pre-processing layer that classifies Telegram messages BEFORE 
the main OCR/parsing pipeline. This solves the user's core problems:

1. Auto-deselect promotional posts ("Join VIP", ads)
2. Auto-deselect recap posts (yesterday's results with checkmarks)
3. Auto-deselect "data dumps" (spreadsheets with 20+ rows of model outputs)
4. Handle congested images by using VLM for better accuracy

Uses the SAME models as the rest of the system (no new dependencies).
"""

import os
import sys
import json
import logging
import re
from typing import List, Dict, Any, Optional

# Add project root to path if needed
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from src.openrouter_client import openrouter_completion
from src.utils import clean_text_for_ai

# Use the same default model as the main pipeline
DEFAULT_CLASSIFIER_MODEL = "google/gemma-3-12b-it:free"  # Fast vision model for classification


class PostClassification:
    """Enum-like class for post classifications"""
    PICK = "PICK"           # Valid betting pick - should be selected
    PROMO = "PROMO"         # Advertisement/promotional - should be deselected
    RECAP = "RECAP"         # Yesterday's results recap - should be deselected  
    DATA = "DATA"           # Spreadsheet/model output dump - should be deselected
    NOISE = "NOISE"         # Irrelevant content - should be deselected
    UNKNOWN = "UNKNOWN"     # Could not classify - keep selected for manual review


# Heuristic patterns for FAST text-based classification (no AI needed)
# CONSERVATIVE: Only filter when we're VERY confident (100% accuracy goal)
PROMO_PATTERNS = [
    r'join\s*(our)?\s*vip\s*(channel|group)',  # More specific
    r'subscribe\s*(to|for)\s*(our|the)\s*(channel|group)',
    r'limited\s*time\s*offer',
    r'\$\d+\s*(off|discount)',
    r'use\s*code\s*[A-Z0-9]+\s*for',  # More specific
    r'free\s*trial\s*(available|now)',
    r'sign\s*up\s*(now|today)\s*(for|to)',
    r'click\s*(here|link)\s*to\s*(join|subscribe)',
    r'crypto\s*airdrop',
    r'nft\s*giveaway',
]

# RECAP patterns - VERY CONSERVATIVE to avoid false positives
# Only trigger on explicit past-tense recap indicators
RECAP_PATTERNS = [
    r'yesterday[\']?s?\s+results?\s*:',  # Explicit "yesterday's results:"
    r'last\s+night[\']?s?\s+results?\s*:',
    r'^recap\s*:',  # Must start with "Recap:" 
    r'final\s+results?\s+for\s+(yesterday|last\s+night)',
    r'[✅❌]{5,}',  # 5+ consecutive result indicators = definitely recap
]

# DATA DUMP patterns - for spreadsheet/model output detection
DATA_DUMP_PATTERNS = [
    r'model\s+output\s*:',
    r'ai\s+model\s+results?\s*:',
    r'spreadsheet\s+data',
    r'expected\s+value\s+analysis',
    r'ev\s*:\s*[\+\-]?\d+.*\n.*ev\s*:',  # Multiple EV lines = data dump
]


def classify_by_text_heuristics(text: str) -> Optional[str]:
    """
    Fast text-based classification using regex patterns.
    Returns classification or None if no match.
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Check for PROMO patterns
    for pattern in PROMO_PATTERNS:
        if re.search(pattern, text_lower):
            return PostClassification.PROMO
    
    # Check for RECAP patterns  
    for pattern in RECAP_PATTERNS:
        if re.search(pattern, text_lower):
            return PostClassification.RECAP
    
    # Check for DATA DUMP patterns
    for pattern in DATA_DUMP_PATTERNS:
        if re.search(pattern, text_lower):
            return PostClassification.DATA
    
    return None


def count_result_indicators(text: str) -> int:
    """Count checkmarks/crosses that indicate a recap."""
    indicators = re.findall(r'[✅❌✓✗☑️🔴🟢]', text)
    return len(indicators)


def classify_message_fast(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fast classification using text heuristics only (no AI call).
    Returns a classification result dict.
    """
    text = message.get('text', '') or ''
    
    # First try text heuristics
    classification = classify_by_text_heuristics(text)
    
    if classification:
        return {
            "class": classification,
            "confidence": 0.8,
            "reason": f"Text pattern match",
            "method": "heuristic"
        }
    
    # Check for high number of result indicators (likely recap)
    # CONSERVATIVE: Require 5+ indicators to avoid false positives
    indicator_count = count_result_indicators(text)
    if indicator_count >= 5:
        return {
            "class": PostClassification.RECAP,
            "confidence": 0.7,
            "reason": f"Found {indicator_count} result indicators",
            "method": "heuristic"
        }
    
    # If no clear pattern, return UNKNOWN (needs AI or manual review)
    return {
        "class": PostClassification.UNKNOWN,
        "confidence": 0.5,
        "reason": "No clear pattern detected",
        "method": "heuristic"
    }


def classify_messages_with_ai(messages: List[Dict[str, Any]], 
                               model: str = DEFAULT_CLASSIFIER_MODEL) -> Dict[str, Dict]:
    """
    Classify messages using Vision AI for images that couldn't be classified by heuristics.
    Batches messages for efficiency.
    
    Args:
        messages: List of message dicts with 'id', 'text', 'images' keys
        model: Model to use for classification
        
    Returns:
        Dict mapping message_id -> classification result
    """
    results = {}
    
    # First pass: fast heuristic classification
    needs_ai = []
    for msg in messages:
        msg_id = msg.get('id')
        fast_result = classify_message_fast(msg)
        
        if fast_result["class"] != PostClassification.UNKNOWN:
            results[msg_id] = fast_result
        else:
            # Check if has images - only use AI for messages with images
            has_images = msg.get('images') or msg.get('image')
            if has_images:
                needs_ai.append(msg)
            else:
                # Text-only message with no pattern - assume PICK
                results[msg_id] = {
                    "class": PostClassification.PICK,
                    "confidence": 0.6,
                    "reason": "Text message with no negative indicators",
                    "method": "heuristic_default"
                }
    
    # Second pass: AI classification for remaining messages with images
    if needs_ai:
        try:
            ai_results = _batch_classify_with_ai(needs_ai, model)
            results.update(ai_results)
        except Exception as e:
            logging.error(f"[AutoProcessor] AI classification failed: {e}")
            # Fallback: mark all as PICK for safety
            for msg in needs_ai:
                results[msg.get('id')] = {
                    "class": PostClassification.PICK,
                    "confidence": 0.5,
                    "reason": "AI classification failed, defaulting to PICK",
                    "method": "fallback"
                }
    
    return results


def _batch_classify_with_ai(messages: List[Dict[str, Any]], 
                            model: str,
                            batch_size: int = 5) -> Dict[str, Dict]:
    """
    Internal function to classify messages with images using VLM.
    """
    results = {}
    
    # Process in batches
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        
        # Collect images and build context
        images_to_send = []
        context_parts = []
        
        for msg in batch:
            msg_id = msg.get('id')
            text = clean_text_for_ai(msg.get('text', ''))
            
            # Get image paths
            imgs = []
            if msg.get('images'):
                imgs = msg['images']
            elif msg.get('image'):
                imgs = [msg['image']]
            
            # Resolve paths
            for img_path in imgs:
                if img_path.startswith('/static/'):
                    clean_path = img_path.lstrip('/').replace('/', os.sep)
                    abs_path = os.path.join(BASE_DIR, clean_path)
                else:
                    abs_path = img_path
                
                if os.path.exists(abs_path):
                    images_to_send.append(abs_path)
            
            context_parts.append(f"[Message {msg_id}] Caption: {text[:200]}")
        
        if not images_to_send:
            continue
        
        # Build classification prompt
        prompt = """You are a Sports Betting Content Classifier. Analyze each image and classify it.

CLASSIFICATIONS:
- PICK: Contains specific betting picks (Team + Line/Odds). SELECT this.
- PROMO: Advertisements, "Join VIP", subscription offers. DESELECT this.
- RECAP: Yesterday's results with ✅/❌, "we went 5-0". DESELECT this.
- DATA: Spreadsheets, model outputs with 10+ rows, raw projections. DESELECT this.

CONTEXT FOR IMAGES:
""" + "\n".join(context_parts) + """

OUTPUT: Return a JSON object mapping message IDs to classifications:
{
  "123": {"class": "PICK", "reason": "Shows Lakers -5 bet slip"},
  "124": {"class": "RECAP", "reason": "Shows checkmarks for yesterday's results"}
}

Return ONLY valid JSON, no markdown."""

        try:
            response = openrouter_completion(prompt, model=model, images=images_to_send, timeout=60)
            
            # Parse response
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            
            parsed = json.loads(cleaned)
            
            # Map results back
            for msg in batch:
                msg_id = str(msg.get('id'))
                if msg_id in parsed:
                    ai_result = parsed[msg_id]
                    results[msg.get('id')] = {
                        "class": ai_result.get("class", PostClassification.PICK),
                        "confidence": 0.9,
                        "reason": ai_result.get("reason", "AI classified"),
                        "method": "ai_vision"
                    }
                else:
                    # Not in response - default to PICK
                    results[msg.get('id')] = {
                        "class": PostClassification.PICK,
                        "confidence": 0.6,
                        "reason": "Not classified by AI, defaulting to PICK",
                        "method": "ai_default"
                    }
                    
        except json.JSONDecodeError as e:
            logging.error(f"[AutoProcessor] JSON parse error: {e}")
            # Default all to PICK
            for msg in batch:
                results[msg.get('id')] = {
                    "class": PostClassification.PICK,
                    "confidence": 0.5,
                    "reason": "JSON parse failed",
                    "method": "fallback"
                }
        except Exception as e:
            logging.error(f"[AutoProcessor] Batch AI error: {e}")
            for msg in batch:
                results[msg.get('id')] = {
                    "class": PostClassification.PICK,
                    "confidence": 0.5,
                    "reason": f"Error: {str(e)[:50]}",
                    "method": "fallback"
                }
    
    return results


def auto_select_messages(messages: List[Dict[str, Any]], 
                         use_ai: bool = True,
                         model: str = DEFAULT_CLASSIFIER_MODEL) -> List[Dict[str, Any]]:
    """
    Main entry point: Automatically set 'selected' field based on classification.
    
    Args:
        messages: List of message dicts from Telegram
        use_ai: Whether to use AI for uncertain cases (recommended for accuracy)
        model: Model to use for AI classification
        
    Returns:
        Same messages list with 'selected', 'classification', and 'classification_reason' fields updated
    """
    if not messages:
        return messages
    
    logging.info(f"[AutoProcessor] Processing {len(messages)} messages...")
    
    if use_ai:
        classifications = classify_messages_with_ai(messages, model)
    else:
        classifications = {}
        for msg in messages:
            classifications[msg.get('id')] = classify_message_fast(msg)
    
    # Apply classifications
    selected_count = 0
    deselected_count = 0
    
    for msg in messages:
        msg_id = msg.get('id')
        result = classifications.get(msg_id, {})
        
        classification = result.get("class", PostClassification.UNKNOWN)
        
        # Set selection based on classification
        should_select = classification in [PostClassification.PICK, PostClassification.UNKNOWN]
        
        msg['selected'] = should_select
        msg['classification'] = classification
        msg['classification_reason'] = result.get("reason", "")
        msg['classification_confidence'] = result.get("confidence", 0.5)
        
        if should_select:
            selected_count += 1
        else:
            deselected_count += 1
    
    logging.info(f"[AutoProcessor] Results: {selected_count} selected, {deselected_count} auto-deselected")
    
    return messages


def check_for_congestion(text: str, image_count: int = 0) -> bool:
    """
    Check if a post appears to be "congested" (too much data for reliable OCR).
    These should use VLM extraction instead of standard OCR.
    """
    if not text:
        return False
    
    # Count newlines - high count suggests list/table
    newline_count = text.count('\n')
    if newline_count > 15:
        return True
    
    # Count numbers - high count suggests data table
    numbers = re.findall(r'\d+\.?\d*', text)
    if len(numbers) > 30:
        return True
    
    # Multiple images in one message can be congested
    if image_count >= 4:
        return True
    
    return False
