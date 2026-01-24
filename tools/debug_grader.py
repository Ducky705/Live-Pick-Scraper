#!/usr/bin/env python3
"""
Debug Grader Tool
==================
Runs the full pipeline for yesterday (Eastern Time), collects raw data
and scraper results, then generates a grading prompt for external AI
models (ChatGPT, Claude, etc.) and copies it to clipboard.

Usage:
    python tools/debug_grader.py [--sample N]

NO SUPABASE WRITES - debug/evaluation mode only.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env BEFORE any config imports
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --- CONFIGURATION ---
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Hard-coded channel
DEBUG_CHANNEL_ID = -1001900292133
DEBUG_CHANNEL_NAME = "CappersFree"


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log(msg: str, color: str = Colors.WHITE):
    print(f"{color}{msg}{Colors.RESET}")


def log_header(title: str):
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")


def log_success(msg: str):
    log(f"[OK] {msg}", Colors.GREEN)


def log_error(msg: str):
    log(f"[ERROR] {msg}", Colors.RED)


def log_info(msg: str):
    log(f"[INFO] {msg}", Colors.BLUE)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Cross-platform."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    # Windows fallback
    if sys.platform == "win32":
        try:
            import subprocess

            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, text=True, encoding="utf-8"
            )
            process.communicate(text)
            return True
        except Exception:
            pass

    # macOS fallback
    if sys.platform == "darwin":
        try:
            import subprocess

            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            process.communicate(text)
            return True
        except Exception:
            pass

    return False


def get_yesterday_eastern() -> str:
    """Get yesterday's date in Eastern Time as YYYY-MM-DD."""
    ET = timezone(timedelta(hours=-5))  # EST
    now_et = datetime.now(ET)
    yesterday = now_et - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def load_from_cache():
    """Try to load messages and picks from cache files."""
    messages_cache = CACHE_DIR / "messages.json"
    ocr_cache = CACHE_DIR / "ocr_results.json"
    parse_cache = CACHE_DIR / "ai_response.json"

    messages = []
    picks = []

    # Load messages
    if messages_cache.exists():
        try:
            with open(messages_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
                messages = data.get("messages", [])
                log_success(f"Loaded {len(messages)} messages from cache")
        except Exception as e:
            log_error(f"Failed to load messages cache: {e}")

    # Merge OCR data into messages
    if ocr_cache.exists() and messages:
        try:
            with open(ocr_cache, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
                ocr_results = ocr_data.get("results", {})

                for msg in messages:
                    msg_id = msg.get("id")
                    msg["ocr_texts"] = []

                    # Find OCR results for this message's images
                    for img_path in msg.get("images", []):
                        if img_path in ocr_results:
                            ocr_text = ocr_results[img_path].get("text", "")
                            if ocr_text:
                                msg["ocr_texts"].append(ocr_text)

                    # Also check by message ID
                    for path, ocr_info in ocr_results.items():
                        if ocr_info.get("msg_id") == msg_id and ocr_info.get("text"):
                            if ocr_info["text"] not in msg["ocr_texts"]:
                                msg["ocr_texts"].append(ocr_info["text"])

                ocr_merged = sum(1 for m in messages if m.get("ocr_texts"))
                log_success(f"Merged OCR data into {ocr_merged} messages")
        except Exception as e:
            log_error(f"Failed to merge OCR cache: {e}")

    # Load picks and expand compact keys
    if parse_cache.exists():
        try:
            with open(parse_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_picks = data.get("picks", [])

                # Expand compact keys to full field names
                picks = []
                for p in raw_picks:
                    expanded = {
                        "message_id": p.get("id", p.get("message_id", "N/A")),
                        "capper_name": p.get("cn", p.get("capper_name", "Unknown")),
                        "league": p.get("lg", p.get("league", "Other")),
                        "type": p.get("ty", p.get("type", "Unknown")),
                        "pick": p.get("p", p.get("pick", "N/A")),
                        "odds": p.get("od", p.get("odds")),
                        "units": p.get("u", p.get("units", 1.0)),
                        "result": p.get("result", "Pending"),
                        "subject": p.get("sub", p.get("subject")),
                        "market": p.get("mkt", p.get("market")),
                        "line": p.get("ln", p.get("line")),
                        "prop_side": p.get("side", p.get("prop_side")),
                    }
                    picks.append(expanded)

                log_success(f"Loaded {len(picks)} picks from cache")
        except Exception as e:
            log_error(f"Failed to load parse cache: {e}")

    return messages, picks


async def run_pipeline(
    target_date: str, sample_size: int = None, use_cache: bool = False
):
    """
    Run the full scraper pipeline without Supabase writes.
    Returns (raw_messages, processed_picks, metadata).
    """
    log_header("RUNNING PIPELINE (NO SUPABASE)")
    log_info(f"Target Date: {target_date}")

    from config import API_ID, API_HASH, TARGET_TELEGRAM_CHANNEL_ID
    from src.telegram_client import TelegramManager
    from src.deduplicator import Deduplicator
    from src.ocr_handler import extract_text_batch
    from src.auto_processor import auto_select_messages
    from src.utils import clean_text_for_ai, backfill_odds
    from src.pick_deduplicator import deduplicate_by_capper
    from src.prompts.decoder import normalize_response
    from src.parallel_batch_processor import parallel_processor
    from src.multi_pick_validator import validate_and_flag_missing, MultiPickValidator
    from src.semantic_validator import SemanticValidator

    metadata = {
        "target_date": target_date,
        "pipeline_start": datetime.now().isoformat(),
        "stages": {},
    }

    messages = []
    picks = []

    # Check for --cache flag
    if use_cache:
        log_info("Using cached data (--cache flag)")
        messages, picks = load_from_cache()

        # If we have picks, return immediately (full cache hit)
        if picks:
            metadata["source"] = "cache"
            metadata["stages"]["cache"] = {
                "messages": len(messages),
                "picks": len(picks),
            }
            return messages, picks, metadata

        # If no picks, continue to pipeline but skip fetch/dedup if messages exist
        if messages:
            log_info(
                "Cached messages found, but no picks. Proceeding to Parsing stage..."
            )

            log_info(
                "Cached messages found, but no picks. Proceeding to Parsing stage..."
            )

    # 1. FETCH
    if not messages:
        log_info("Stage 1: Fetching messages from Telegram...")
        tg = TelegramManager()

        if not API_ID or not API_HASH:
            log_error("Telegram credentials missing (API_ID/API_HASH not set)!")
            # Note: Cache fallback was attempted above
            log_error(
                "No cache available. Create a .env file with API_ID and API_HASH."
            )
            return [], [], metadata

        connected = await tg.connect_client()
        if not connected:
            log_error("Telegram not connected!")
            return [], [], metadata

        start = time.time()
        raw_messages = await tg.fetch_messages(
            [TARGET_TELEGRAM_CHANNEL_ID], target_date
        )
        metadata["stages"]["fetch"] = {
            "time": time.time() - start,
            "count": len(raw_messages),
        }
        log_success(
            f"Fetched {len(raw_messages)} messages in {metadata['stages']['fetch']['time']:.1f}s"
        )

        if sample_size and len(raw_messages) > sample_size:
            raw_messages = raw_messages[:sample_size]
            log_info(f"Sampled down to {sample_size} messages")
    else:
        log_info("Skipping fetch (using cached messages)")
        raw_messages = messages

    # 2. DEDUPLICATE
    log_info("Stage 2: Deduplicating...")
    unique_msgs = Deduplicator.merge_messages(raw_messages)
    metadata["stages"]["dedup"] = {
        "input": len(raw_messages),
        "output": len(unique_msgs),
    }
    log_success(f"Deduplicated: {len(raw_messages)} -> {len(unique_msgs)}")

    # 3. OCR
    log_info("Stage 3: Running OCR...")
    ocr_tasks = []
    for i, msg in enumerate(unique_msgs):
        # SKIP if we already have OCR text from cache
        if msg.get("ocr_texts") or msg.get("ocr_text"):
            continue

        msg["ocr_texts"] = []
        images = msg.get("images", []) or ([msg["image"]] if msg.get("image") else [])
        if msg.get("do_ocr") and images:
            for img in images:
                ocr_tasks.append((i, img))

    if ocr_tasks:
        start = time.time()
        image_paths = [t[1] for t in ocr_tasks]
        results = extract_text_batch(image_paths)

        for t_idx, text in enumerate(results):
            msg_idx = ocr_tasks[t_idx][0]
            if text and not text.startswith("[Error"):
                cleaned = clean_text_for_ai(text)
                unique_msgs[msg_idx]["ocr_texts"].append(cleaned)
                unique_msgs[msg_idx]["ocr_text"] = "\n".join(
                    unique_msgs[msg_idx]["ocr_texts"]
                )

        metadata["stages"]["ocr"] = {
            "time": time.time() - start,
            "images": len(ocr_tasks),
        }
        log_success(
            f"OCR complete: {len(ocr_tasks)} images in {metadata['stages']['ocr']['time']:.1f}s"
        )
    else:
        metadata["stages"]["ocr"] = {"time": 0, "images": 0}

    # 4. CLASSIFICATION
    log_info("Stage 4: Classifying messages...")
    classified = auto_select_messages(unique_msgs, use_ai=True)
    selected = [m for m in classified if m.get("selected")]
    metadata["stages"]["classify"] = {
        "input": len(unique_msgs),
        "selected": len(selected),
    }
    log_success(f"Selected {len(selected)}/{len(unique_msgs)} messages as picks")

    if not selected:
        log_error("No picks detected!")
        return unique_msgs, [], metadata

    # 5. PARSING
    log_info("Stage 5: AI Parsing (parallel multi-provider)...")
    BATCH_SIZE = 10
    batches = [
        selected[i : i + BATCH_SIZE] for i in range(0, len(selected), BATCH_SIZE)
    ]

    start = time.time()
    try:
        all_raw_picks = parallel_processor.process_batches(batches)

        picks = []
        for batch_idx, raw_response in enumerate(all_raw_picks):
            # Get the valid message IDs for this batch to prevent cross-contamination
            valid_ids = None
            msg_context = None

            if batch_idx < len(batches):
                current_batch = batches[batch_idx]
                valid_ids = [
                    int(m.get("id")) for m in current_batch if m.get("id") is not None
                ]

                # Build message context map for verification
                msg_context = {}
                for m in current_batch:
                    mid = m.get("id")
                    if mid:
                        # Combine caption and OCR for full context
                        full_text = (
                            (m.get("text", "") or "")
                            + "\n"
                            + (m.get("ocr_text", "") or "")
                        )
                        msg_context[int(mid)] = full_text

            batch_picks = normalize_response(
                raw_response,
                expand=True,
                valid_message_ids=valid_ids,
                message_context=msg_context,
            )
            picks.extend(batch_picks)

        # --- REFINEMENT PASS (Multi-Pick & Semantic Validation) ---
        log_info("Stage 5b: Refinement (Missing & Invalid Picks)...")

        # 1. Check for missing picks
        picks, reparse_ids_missing = validate_and_flag_missing(selected, picks)
        reparse_ids = set(reparse_ids_missing)

        # 2. Check for semantic errors & confidence
        semantic_issues = {}

        # Create map of message ID to message object for context checks
        msg_map = {}
        for m in selected:
            if m.get("id") is not None:
                msg_map[int(m["id"])] = m

        for p in picks:
            mid = p.get("message_id")
            if mid:
                try:
                    mid_int = int(mid)
                except (ValueError, TypeError):
                    continue

                # A. Basic Semantic Validation
                is_valid, reason = SemanticValidator.validate(p)
                if not is_valid:
                    if mid_int not in semantic_issues:
                        semantic_issues[mid_int] = []
                    semantic_issues[mid_int].append(
                        f"Pick '{p.get('pick')}' invalid: {reason}"
                    )
                    reparse_ids.add(mid_int)

                # B. Confidence Check (New Architectural Feature)
                conf = p.get("confidence")
                if conf is not None:
                    try:
                        conf_val = float(conf)
                        if conf_val < 8:  # Threshold for re-parsing
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Low confidence ({conf_val}/10). Verify extraction."
                            )
                            reparse_ids.add(mid_int)
                    except ValueError:
                        pass

                # C. "The Auditor" - Contextual Logic Checks
                msg = msg_map.get(mid_int)
                if msg:
                    text_upper = (
                        msg.get("text", "") + "\n" + msg.get("ocr_text", "")
                    ).upper()

                    # C1. Unit Header Mismatch
                    # Detect "10U" headers vs 1U picks
                    extracted_units = p.get("units", 1.0)
                    if extracted_units == 1.0:
                        potential_units = 0
                        if (
                            "10U" in text_upper
                            or "MAX BET" in text_upper
                            or "MAX PLAY" in text_upper
                        ):
                            potential_units = 10
                        elif "5U" in text_upper:
                            potential_units = 5
                        elif "3U" in text_upper:
                            potential_units = 3

                        if potential_units > 1:
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Possible Unit Mismatch: Text implies {potential_units}U, pick has 1U."
                            )
                            reparse_ids.add(mid_int)

                    # C2. Parlay Keyword Mismatch
                    # If text says "PARLAY" but we extracted a single ML/Spread/Total
                    if "PARLAY" in text_upper and p.get("type") not in [
                        "Parlay",
                        "Unknown",
                    ]:
                        # Only flag if we haven't extracted *any* parlays for this message yet
                        # (This check is per-pick, so slightly imperfect, but good signal)
                        if mid_int not in semantic_issues:
                            semantic_issues[mid_int] = []
                        semantic_issues[mid_int].append(
                            f"Text mentions 'PARLAY' but pick is type '{p.get('type')}'. Verify if this is part of a parlay."
                        )
                        reparse_ids.add(mid_int)

        reparse_ids = list(reparse_ids)

        reparse_ids = list(reparse_ids)

        if reparse_ids:
            log_info(f"Refinement: {len(reparse_ids)} messages flagged for re-parsing")

            reparse_batch = []

            # Find the message objects and prepare them
            for m in selected:
                m_id = m.get("id")
                if m_id in reparse_ids:
                    # Create a copy to avoid modifying original
                    retry_msg = m.copy()

                    # Generate hint
                    ocr_text = retry_msg.get("ocr_text", "")
                    if not ocr_text and retry_msg.get("ocr_texts"):
                        ocr_text = "\n".join(retry_msg["ocr_texts"])

                    msg_picks = [p for p in picks if p.get("message_id") == m_id]

                    hints = []

                    # Add Missing Pick hints
                    if m_id in reparse_ids_missing:
                        hints.append(
                            MultiPickValidator.get_reparse_hint(
                                ocr_text=ocr_text,
                                parsed_picks=msg_picks,
                                caption=retry_msg.get("text", ""),
                            )
                        )

                    # Add Semantic hints
                    if m_id in semantic_issues:
                        hints.append("\n### CORRECTION NEEDED")
                        hints.append("The following picks were flagged as invalid:")
                        for issue in semantic_issues[m_id]:
                            hints.append(f"- {issue}")
                        hints.append("Please fix these errors in your re-extraction.")

                    full_hint = "\n\n".join(hints)

                    # Append hint to text for AI
                    retry_msg["text"] = (
                        retry_msg.get("text", "") + "\n\n" + full_hint
                    )[:3500]
                    reparse_batch.append(retry_msg)

            if reparse_batch:
                log_info(f"Running refinement on {len(reparse_batch)} messages...")

                # Process in small batches
                reparse_batches = [
                    reparse_batch[i : i + BATCH_SIZE]
                    for i in range(0, len(reparse_batch), BATCH_SIZE)
                ]

                try:
                    # Use parallel processor for speed
                    reparse_results = parallel_processor.process_batches(
                        reparse_batches
                    )

                    # Process results
                    new_picks_count = 0

                    # Map results to message IDs
                    for batch_idx, raw_response in enumerate(reparse_results):
                        # Get IDs for this batch
                        valid_ids = None
                        if batch_idx < len(reparse_batches):
                            valid_ids = [
                                int(m.get("id"))
                                for m in reparse_batches[batch_idx]
                                if m.get("id") is not None
                            ]

                        new_batch_picks = normalize_response(
                            raw_response, expand=True, valid_message_ids=valid_ids
                        )

                        # Group new picks by ID
                        new_picks_by_id = {}
                        for p in new_batch_picks:
                            mid = p.get("message_id")
                            if mid not in new_picks_by_id:
                                new_picks_by_id[mid] = []
                            new_picks_by_id[mid].append(p)

                        # Update main list - Replace old picks with new refined ones
                        for mid, msg_new_picks in new_picks_by_id.items():
                            if msg_new_picks:
                                # Remove old picks for this message
                                # We convert to string/int safely for comparison
                                picks = [
                                    p
                                    for p in picks
                                    if str(p.get("message_id")) != str(mid)
                                ]
                                # Add new picks
                                picks.extend(msg_new_picks)
                                new_picks_count += len(msg_new_picks)

                    log_success(
                        f"Refinement complete: Replaced with {new_picks_count} refined picks"
                    )
                    metadata["stages"]["refine"] = {
                        "reparsed": len(reparse_batch),
                        "new_picks": new_picks_count,
                    }

                except Exception as e:
                    log_error(f"Refinement failed: {e}")
        else:
            log_info("No refinement needed.")

        picks = backfill_odds(picks)
        picks = deduplicate_by_capper(picks)

        metadata["stages"]["parse"] = {"time": time.time() - start, "picks": len(picks)}
        log_success(
            f"Parsed {len(picks)} picks in {metadata['stages']['parse']['time']:.1f}s"
        )

    except Exception as e:
        log_error(f"Parsing failed: {e}")
        picks = []
        metadata["stages"]["parse"] = {"error": str(e)}

    # 6. GRADING (optional, for context)
    log_info("Stage 6: Grading picks...")
    try:
        from src.grader import grade_picks
        from src.score_fetcher import fetch_scores_for_date

        scores = fetch_scores_for_date(target_date)
        picks = grade_picks(picks, scores)

        wins = sum(1 for p in picks if p.get("result") == "Win")
        losses = sum(1 for p in picks if p.get("result") == "Loss")
        pending = sum(
            1
            for p in picks
            if p.get("result") in ["Pending", "Pending/Unknown", None, ""]
        )

        metadata["stages"]["grade"] = {
            "wins": wins,
            "losses": losses,
            "pending": pending,
        }
        log_success(f"Graded: {wins} Wins, {losses} Losses, {pending} Pending")
    except Exception as e:
        log_error(f"Grading failed: {e}")
        metadata["stages"]["grade"] = {"error": str(e)}

    metadata["pipeline_end"] = datetime.now().isoformat()

    return unique_msgs, picks, metadata


def format_message_for_prompt(msg: dict, idx: int) -> str:
    """Format a single message for the grading prompt."""
    lines = [f"### MESSAGE {idx + 1} (ID: {msg.get('id', 'N/A')})"]

    # Channel info
    channel = msg.get("channel_name", "Unknown")
    lines.append(f"**Channel:** {channel}")
    lines.append(f"**Date:** {msg.get('date', 'N/A')}")

    # Text content
    text = msg.get("text", "").strip()
    if text:
        # Truncate very long texts
        if len(text) > 500:
            text = text[:500] + "... [truncated]"
        lines.append(f"**Caption/Text:**\n```\n{text}\n```")

    # OCR content
    ocr_texts = msg.get("ocr_texts", [])
    if ocr_texts:
        lines.append("**OCR from Image(s):**")
        for i, ocr in enumerate(ocr_texts):
            ocr_preview = ocr[:800] if len(ocr) > 800 else ocr
            if len(ocr) > 800:
                ocr_preview += "... [truncated]"
            lines.append(f"```\n{ocr_preview}\n```")

    # Image info
    images = msg.get("images", [])
    if images:
        lines.append(f"**Images:** {len(images)} image(s)")

    return "\n".join(lines)


def format_pick_for_prompt(pick: dict, idx: int) -> str:
    """Format a single pick for the grading prompt with all fields visible."""
    lines = [f"### PICK {idx + 1}"]

    # Core fields (always show)
    core_fields = [
        ("Message ID", pick.get("message_id", "N/A")),
        ("Capper", pick.get("capper_name", "Unknown")),
        ("League", pick.get("league", "Other")),
        ("Type", pick.get("type", "Unknown")),
        ("Pick", pick.get("pick", "N/A")),
    ]

    for label, value in core_fields:
        lines.append(f"- **{label}:** {value}")

    # Odds and units
    odds = pick.get("odds")
    units = pick.get("units", 1.0)
    lines.append(f"- **Odds:** {odds if odds is not None else 'N/A'}")
    lines.append(f"- **Units:** {units}")

    # Structured fields (show all, even if None, for completeness check)
    lines.append(f"- **Subject:** {pick.get('subject') or 'N/A'}")
    lines.append(f"- **Market:** {pick.get('market') or 'N/A'}")
    lines.append(
        f"- **Line:** {pick.get('line') if pick.get('line') is not None else 'N/A'}"
    )
    lines.append(f"- **Side:** {pick.get('prop_side') or 'N/A'}")

    # Result if present
    if pick.get("result"):
        lines.append(f"- **Result:** {pick.get('result')}")

    # Source snippet (for debugging attributions)
    if pick.get("_source_text"):
        snippet = pick["_source_text"].replace("\n", " ")[:100]
        lines.append(f"- **Source Snippet:** `{snippet}...`")

    return "\n".join(lines)


def load_pick_format_spec() -> str:
    """Load the pick_format.md specification file."""
    spec_path = PROJECT_ROOT / "docs" / "pick_format.md"
    if spec_path.exists():
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            log_error(f"Failed to load pick_format.md: {e}")
    return ""


def generate_grading_prompt(messages: list, picks: list, metadata: dict) -> str:
    """
    Generate a comprehensive prompt for external AI to grade the scraper output.
    Dynamically includes the full pick_format.md specification.
    """
    target_date = metadata.get("target_date", "Unknown")

    # Load the authoritative format specification
    format_spec = load_pick_format_spec()

    prompt = f"""# SPORTS BETTING SCRAPER OUTPUT EVALUATION

## TASK
You are a **strict evaluator** for an automated sports betting pick scraper. Your job is to grade how well the AI parser extracted and formatted picks from raw Telegram messages against the **official specification** provided below.

**Date Analyzed:** {target_date}
**Messages Processed:** {len(messages)}
**Picks Extracted:** {len(picks)}

---

## OFFICIAL FORMAT SPECIFICATION

**IMPORTANT:** All picks MUST conform to this specification. Use this as your ground truth for grading.

{format_spec}

---

## GRADING RUBRIC

Grade each dimension from 1-10 based on compliance with the specification above.

### 1. EXTRACTION ACCURACY (1-10)
- Did the parser find **ALL** picks in the messages? (Check for missed parlays, split plays, listed picks)
- Were any picks missed completely?
- Were any non-picks incorrectly extracted (false positives - promos, recaps, noise)?
- **Critical:** Each message's picks must be attributed to the correct `message_id`

### 2. PICK FORMATTING (1-10)
Grade against the **exact formats** in the specification:
- **Moneyline:** `Team Name ML` (e.g., "Los Angeles Lakers ML")
- **Spread:** `Team Name +/-X.X` (e.g., "Green Bay Packers -7.5")
- **Total:** `Team A vs Team B Over/Under X` (NOT "Team A/Team B" or "Team A & Team B")
- **Player Prop:** `Player Name: Stat Over/Under X` (e.g., "LeBron James: Pts Over 25.5")
- **Team Prop:** `Team Name: Stat Over/Under X`
- **Period:** `1H/1Q/F5 [Standard Format]` (e.g., "1H NYK vs BOS Total Over 110.5")
- **Parlay:** `(LEAGUE) Leg1 / (LEAGUE) Leg2` - League prefix is **MANDATORY**
- **Tennis:** Special formats per spec (sets, games, ML)
- **Future:** `Award or Event: Selection`

**Deductions for:**
- Using "/" instead of "vs" for totals
- Missing league prefixes on parlay legs
- Using "U" instead of "Under", "O" instead of "Over"
- Player props without colon format
- Odds or units embedded in pick string

### 3. CLASSIFICATION ACCURACY (1-10)
- Is `league` using official abbreviations? (NFL, NCAAB, etc. - see spec)
- Is `type` correct per specification?
  - **Critical:** "Team -7" = Spread, NOT Moneyline
  - **Critical:** "First Half"/"1H" picks = Period, NOT Spread
  - **Critical:** Multi-leg = Parlay, even if same league
  - Tennis set/game spreads = Spread (not Moneyline)
- Cross-league parlays should have `league: "Other"`

### 4. CAPPER ATTRIBUTION (1-10)
- Is `capper_name` the actual tipster, NOT the channel name?
- Are watermarks (@cappersfree, @vippicks) excluded?
- Are different cappers in the same message distinguished?
- Is capper name properly capitalized (not all caps)?

### 5. ODDS & UNITS EXTRACTION (1-10)
- Are American odds extracted correctly (-110, +150)?
- Are odds stored as integers in `odds` field, NOT in pick string?
- Are units parsed correctly (2u → 2.0, "80K" → 80000)?
- Default units = 1.0 when not specified

### 6. DATA COMPLETENESS (1-10)
- **Spreads:** Is `line` populated with the spread value?
- **Props:** Is `subject` (player/team name) and `market` (stat type) populated?
- **Props:** Is `prop_side` set to "Over" or "Under"?
- **Totals:** Is the total number captured in `line`?
- Are all required fields present (message_id, capper_name, league, type, pick)?

---

## RAW INPUT DATA (Source Messages)

Below are the original Telegram messages that were processed:

"""

    # Add messages (limit to reasonable number)
    max_messages = min(len(messages), 30)
    for i, msg in enumerate(messages[:max_messages]):
        prompt += format_message_for_prompt(msg, i) + "\n\n"

    if len(messages) > max_messages:
        prompt += (
            f"\n*[...{len(messages) - max_messages} more messages not shown...]*\n\n"
        )

    prompt += """---

## SCRAPER OUTPUT (Extracted Picks)

Below are the picks extracted by the AI parser:

"""

    # Add picks
    for i, pick in enumerate(picks):
        prompt += format_pick_for_prompt(pick, i) + "\n\n"

    prompt += """---

## YOUR EVALUATION

Provide a thorough evaluation following this exact structure:

### DIMENSION SCORES

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| 1. Extraction Accuracy | /10 | |
| 2. Pick Formatting | /10 | |
| 3. Classification Accuracy | /10 | |
| 4. Capper Attribution | /10 | |
| 5. Odds & Units Extraction | /10 | |
| 6. Data Completeness | /10 | |
| **OVERALL** | **/60** | |

---

### MISSED PICKS

List every pick in the raw messages that was NOT extracted. For each:
- **Message ID:** [ID]
- **Missed Pick:** [What the pick says in the source]
- **Expected Output:** [Correct formatted pick per specification]

---

### FALSE POSITIVES / HALLUCINATIONS

List any extracted "picks" that:
1. Are NOT actual betting picks (promos, recaps, commentary)
2. Have incorrect `message_id` (pick attributed to wrong message)
3. Were hallucinated (content from one message appearing in another)

For each:
- **Pick #:** [Number from extracted picks]
- **Issue:** [False positive / Hallucination / Wrong message_id]
- **Details:** [Explanation]

---

### CLASSIFICATION ERRORS

List picks with wrong `type` or `league`. For each:
- **Pick #:** [Number]
- **Current:** type="{current_type}", league="{current_league}"
- **Correct:** type="{correct_type}", league="{correct_league}"
- **Reason:** [Why this is wrong per specification]

**Pay special attention to:**
- Spreads misclassified as Moneyline (e.g., "Team -7" should be Spread)
- Period bets not marked as type="Period"
- Parlays not marked as type="Parlay"

---

### FORMATTING ERRORS

List picks that don't match the specification format. For each:
- **Pick #:** [Number]
- **Current Format:** [What was extracted]
- **Correct Format:** [What it should be per specification]
- **Rule Violated:** [Which formatting rule from the spec]

**Common violations to check:**
- Totals using "/" instead of "vs"
- Player props missing colon format
- Parlays missing (LEAGUE) prefix on each leg
- Over/Under abbreviated as O/U
- Odds embedded in pick string

---

### STRUCTURED FIELD ERRORS

List picks missing required structured fields:
- **Spreads:** Missing `line` field
- **Props:** Missing `subject`, `market`, or `prop_side`
- **Totals:** Missing `line` or `prop_side`

---

### SUMMARY

Provide a 3-5 sentence summary covering:
1. Overall performance assessment
2. The single most critical issue to fix
3. Pattern of errors (if any)
4. Recommended priority for fixes
"""

    return prompt


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Debug Grader - Generate AI evaluation prompt"
    )
    parser.add_argument("--sample", type=int, default=None, help="Limit to N messages")
    parser.add_argument(
        "--cache", action="store_true", help="Use cached data instead of fetching"
    )
    args = parser.parse_args()

    log_header("DEBUG GRADER TOOL")

    # Get yesterday Eastern Time
    target_date = get_yesterday_eastern()
    log_info(f"Target Date: {target_date} (Yesterday ET)")

    # Run pipeline
    messages, picks, metadata = await run_pipeline(target_date, args.sample, args.cache)

    if not messages:
        log_error("No messages available. Cannot generate prompt.")
        log_info("Options:")
        log_info("  1. Create .env file with API_ID and API_HASH")
        log_info("  2. Run 'python tools/debug_pipeline.py fetch' first to cache data")
        log_info("  3. Use --cache flag if you've already run the pipeline before")
        return

    # Generate the grading prompt
    log_header("GENERATING GRADING PROMPT")

    prompt = generate_grading_prompt(messages, picks, metadata)

    # Display stats
    log_info(f"Prompt length: {len(prompt):,} characters")
    log_info(f"Messages included: {min(len(messages), 30)}")
    log_info(f"Picks included: {len(picks)}")

    # Copy to clipboard
    log_header("COPYING TO CLIPBOARD")

    success = copy_to_clipboard(prompt)

    if success:
        log_success("Prompt copied to clipboard!")
        log_info("Paste into ChatGPT, Claude, or another AI model for evaluation.")
    else:
        log_error(
            "Could not copy to clipboard. Install pyperclip: pip install pyperclip"
        )

        # Save to file as fallback
        output_file = CACHE_DIR / "grading_prompt.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        log_info(f"Saved to: {output_file}")

    # Also save to file for reference
    output_file = CACHE_DIR / "grading_prompt.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(prompt)
    log_info(f"Also saved to: {output_file}")

    # Print preview
    log_header("PROMPT PREVIEW (first 2000 chars)")
    print(prompt[:2000])
    print(
        f"\n{Colors.YELLOW}[... {len(prompt) - 2000} more characters ...]{Colors.RESET}"
    )

    log_header("DONE")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        log_error(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
