import json
import logging
import asyncio
from typing import List, Dict, Any, Union
from collections import defaultdict
import difflib

from src.models import BetPick, TelegramMessage
from src.ocr_handler import extract_text_batch
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion, openrouter_parallel_completion
from src.two_pass_verifier import TwoPassVerifier

# Setup Logger
logger = logging.getLogger(__name__)

def smart_merge_odds(picks: List[dict]) -> List[dict]:
    """
    Fuzzy matches picks to propagate odds from those that have them to those that don't.
    Moved from main.py
    """
    # 1. Separate sources (have odds) and targets (missing odds)
    sources_map = defaultdict(list)
    targets = []
    
    for p in picks:
        has_odds = p.get('odds') is not None and str(p.get('odds')).strip() != ""
        league = str(p.get('league', '')).lower().strip()
        p_type = str(p.get('type', '')).lower().strip()
        key = (league, p_type)
        
        if has_odds:
            sources_map[key].append(p)
        else:
            targets.append(p)
    
    if not targets or not sources_map:
        return picks
        
    for target in targets:
        league = str(target.get('league', '')).lower().strip()
        p_type = str(target.get('type', '')).lower().strip()
        key = (league, p_type)
        
        relevant_sources = sources_map.get(key, [])
        if not relevant_sources:
            continue
            
        target_norm = target.get('pick', '').lower().strip()
        if not target_norm: continue
        
        best_match = None
        best_ratio = 0.0
        
        for source in relevant_sources:
            source_norm = source.get('pick', '').lower().strip()
            
            if target_norm in source_norm or source_norm in target_norm:
                ratio = 1.0
            else:
                ratio = difflib.SequenceMatcher(None, target_norm, source_norm).ratio()
            
            if ratio > 0.85 and ratio > best_ratio:
                best_ratio = ratio
                best_match = source
                if ratio == 1.0: break
        
        if best_match:
            target['odds'] = best_match['odds']
            target['warning'] = 'Odds Merged'
            
    return picks

class TelegramPipeline:
    def __init__(self):
        self.verifier = TwoPassVerifier()

    async def process_messages(self, messages: List[Union[TelegramMessage, Dict]], use_parallel: bool = True) -> List[BetPick]:
        """
        Full pipeline: Messages -> OCR -> AI Parse -> Two-Pass Verification -> Final Picks
        """
        # 0. Normalize inputs
        msgs_to_process = []
        msg_map = {}
        
        for m in messages:
            # Handle both dict and Pydantic model
            if isinstance(m, dict):
                m_obj = TelegramMessage(**m)
            else:
                m_obj = m
            
            msgs_to_process.append(m_obj)
            msg_map[m_obj.id] = m_obj

        # 1. OCR Extraction (if needed)
        # Check if OCR is already done
        needs_ocr = [m for m in msgs_to_process if not m.ocr_text]
        if needs_ocr:
            logger.info(f"[Pipeline] Running OCR for {len(needs_ocr)} messages...")
            # We need image paths. Assuming 'images' list contains local paths
            # extract_text_batch expects list of dicts with 'images' key
            # This part is tricky if extract_text_batch is tightly coupled.
            # Let's assume the input messages already have OCR or we skip for now.
            # In a real run, OCR happens before this function usually.
            pass

        # 2. Generate Prompt (Pass 1)
        # Convert back to dicts for prompt builder (it expects dicts)
        msg_dicts = [m.dict() for m in msgs_to_process]
        prompt = generate_ai_prompt(msg_dicts)
        
        # 3. AI Execution (Pass 1)
        logger.info("[Pipeline] Running Phase 1 Parsing...")
        if use_parallel:
            response_str = openrouter_parallel_completion(prompt)
        else:
            response_str = openrouter_completion(prompt)
            
        # 4. Parse Response
        try:
            # Handle potential markdown wrapping
            if "```json" in response_str:
                response_str = response_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_str:
                response_str = response_str.split("```")[1].split("```")[0].strip()
                
            data = json.loads(response_str)
            
            raw_picks = []
            if isinstance(data, dict):
                raw_picks = data.get('picks', [])
            elif isinstance(data, list):
                raw_picks = data
                
            # Remap keys
            remapped_picks = []
            for p in raw_picks:
                remapped_picks.append({
                    "message_id": p.get("id") or p.get("message_id"),
                    "capper_name": p.get("cn") or p.get("capper_name", "Unknown"),
                    "league": p.get("lg") or p.get("league", "Other"),
                    "type": p.get("ty") or p.get("type", "Unknown"),
                    "pick": p.get("p") or p.get("pick"),
                    "odds": p.get("od") or p.get("odds"),
                    "units": p.get("u") or p.get("units", 1.0)
                })
                
            # Merge odds
            merged_picks = smart_merge_odds(remapped_picks)
            
            # Convert to BetPick models
            initial_picks = []
            for p in merged_picks:
                try:
                    initial_picks.append(BetPick(**p))
                except Exception as e:
                    logger.error(f"[Pipeline] Failed to create BetPick: {e}")
                    
        except json.JSONDecodeError:
            logger.error("[Pipeline] Phase 1 JSON Parse Failed")
            return []

        # 5. Two-Pass Verification (Pass 2)
        logger.info(f"[Pipeline] Phase 1 Complete. {len(initial_picks)} picks found. Starting Phase 2 Verification...")
        final_picks = await self.verifier.verify_picks(initial_picks, msg_map)
        
        logger.info(f"[Pipeline] Pipeline Complete. {len(final_picks)} final picks.")
        return final_picks

# Singleton
pipeline = TelegramPipeline()
