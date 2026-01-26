import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TARGET_TELEGRAM_CHANNEL_ID, OUTPUT_DIR, LOG_DIR
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager
from src.deduplicator import Deduplicator
from src.ocr_handler import extract_text_batch
from src.auto_processor import auto_select_messages
from src.prompt_builder import generate_ai_prompt
from src.provider_pool import pooled_completion
from src.utils import clean_text_for_ai, backfill_odds
from src.two_pass_verifier import TwoPassVerifier
from src.semantic_validator import SemanticValidator
from src.multi_pick_validator import validate_and_flag_missing
from src.multi_capper_verifier import verify_all_picks
from src.pick_deduplicator import deduplicate_by_capper
from src.game_enricher import enrich_picks
from src.rule_based_extractor import RuleBasedExtractor

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "cli_scraper.log")),
        logging.StreamHandler(sys.stdout),
    ],
)


async def main():
    print("=" * 50)
    print("   TELEGRAM & TWITTER SCRAPER CLI   ")
    print("=" * 50)

    # 1. INITIALIZATION
    logging.info("Initializing Clients...")

    # Telegram
    from config import API_ID, API_HASH

    tg = TelegramManager()

    if not API_ID or not API_HASH:
        logging.warning(
            "Telegram credentials missing (API_ID/API_HASH). Skipping Telegram fetch."
        )
        tg_msgs = []
    else:
        tg_connected = await tg.connect_client()
        if not tg_connected:
            logging.info(
                "Session not found or expired. Starting interactive authentication..."
            )
            try:
                client = await tg.get_client()
                # Interactive login in the terminal
                await client.start()

                if not await client.is_user_authorized():
                    logging.error("Authentication failed. Please try again.")
                    return
                logging.info("Authentication successful!")
            except Exception as e:
                logging.error(f"Authentication Error: {e}")
                return

    # Twitter
    tw = TwitterManager()

    # 2. FETCH DATA (Yesterday in Eastern Time)
    ET = timezone(timedelta(hours=-5))  # EST (use -4 for EDT if needed)
    now_et = datetime.now(ET)
    yesterday_et = now_et - timedelta(days=1)
    target_date = yesterday_et.strftime("%Y-%m-%d")
    logging.info(
        f"Target Date: {target_date} (Eastern Time, now ET: {now_et.strftime('%Y-%m-%d %H:%M')})"
    )

    # Fetch Telegram
    if not API_ID or not API_HASH:
        logging.info("Skipping Telegram fetch (Missing Credentials).")
        tg_msgs = []
    else:
        # Support multiple comma-separated channel IDs from env
        target_ids = []
        if TARGET_TELEGRAM_CHANNEL_ID:
            target_ids = [
                tid.strip()
                for tid in TARGET_TELEGRAM_CHANNEL_ID.split(",")
                if tid.strip()
            ]

        if target_ids:
            logging.info(
                f"Fetching Telegram messages from {len(target_ids)} channels: {target_ids}..."
            )
            tg_msgs = await tg.fetch_messages(target_ids, target_date)
            logging.info(f"Fetched {len(tg_msgs)} Telegram messages.")
        else:
            logging.warning("No TARGET_TELEGRAM_CHANNEL_ID configured.")
            tg_msgs = []

    # Fetch Twitter
    logging.info("Fetching Tweets...")
    tw_msgs = await tw.fetch_tweets(target_date=target_date)
    logging.info(f"Fetched {len(tw_msgs)} Tweets.")

    # Combine
    all_msgs = tg_msgs + tw_msgs

    # 3. DEDUPLICATION
    logging.info("Deduplicating messages...")
    unique_msgs = Deduplicator.merge_messages(all_msgs)
    logging.info(f"Unique Messages: {len(unique_msgs)}")

    if not unique_msgs:
        logging.warning("No messages found. Exiting.")
        return

    # 4. OCR & IMAGE PROCESSING
    logging.info("Starting OCR processing (Smart Mode)...")

    # Prepare batch
    ocr_tasks = []  # (msg_index, image_path)

    for i, msg in enumerate(unique_msgs):
        msg["ocr_texts"] = []

        # Get all images
        images = []
        if msg.get("images"):
            images = msg["images"]
        elif msg.get("image"):
            images = [msg["image"]]

        if msg.get("do_ocr") and images:
            for img_path in images:
                ocr_tasks.append((i, img_path))

    if ocr_tasks:
        image_paths = [t[1] for t in ocr_tasks]
        logging.info(f"Processing {len(image_paths)} images...")

        # Run Batch OCR
        results = extract_text_batch(image_paths)

        # Map results back
        for t_idx, text_result in enumerate(results):
            original_msg_idx = ocr_tasks[t_idx][0]
            if text_result and not text_result.startswith("[Error"):
                cleaned = clean_text_for_ai(text_result)
                unique_msgs[original_msg_idx]["ocr_texts"].append(cleaned)
                # Combine into main ocr_text field for prompts
                unique_msgs[original_msg_idx]["ocr_text"] = "\n".join(
                    unique_msgs[original_msg_idx]["ocr_texts"]
                )

    logging.info("OCR Complete.")

    # 5. AUTO-CLASSIFICATION
    logging.info("Classifying messages...")
    classified_msgs = auto_select_messages(unique_msgs, use_ai=True)

    # Filter only "selected" messages (likely picks)
    selected_msgs = [m for m in classified_msgs if m.get("selected")]
    logging.info(
        f"Selected {len(selected_msgs)} likely pick messages out of {len(classified_msgs)}."
    )

    if not selected_msgs:
        logging.warning("No picks detected after classification.")
        return

    # 5.5 RULE-BASED EXTRACTION (FAST PATH)
    logging.info("Attempting Rule-Based Extraction (Fast Path)...")
    rule_picks, messages_for_ai = RuleBasedExtractor.extract(selected_msgs)

    # Initialize master picks list with rule-based picks
    picks = rule_picks

    if not messages_for_ai:
        logging.info(
            "All messages handled by Rule-Based Extractor! Skipping AI pipeline."
        )
    else:
        # 6. PARSING (AI FILL) - HYBRID PARALLEL STRATEGY
        logging.info(
            f"Generating AI Prompts for {len(messages_for_ai)} remaining messages..."
        )

        # Configuration
        BATCH_SIZE = 10  # Messages per batch

        # Split into batches
        batches = [
            messages_for_ai[i : i + BATCH_SIZE]
            for i in range(0, len(messages_for_ai), BATCH_SIZE)
        ]
        logging.info(
            f"Processing {len(batches)} batches ({BATCH_SIZE} msgs each) across all available providers..."
        )

        # Use the new Parallel Batch Processor
        from src.parallel_batch_processor import parallel_processor

        try:
            # This handles distribution across Cerebras, Groq, Mistral, Gemini, OpenRouter
            all_raw_picks = parallel_processor.process_batches(batches)
            logging.info(f"Total extracted batches: {len(all_raw_picks)}")

        except Exception as e:
            logging.error(f"Parallel processing failed: {e}")
            all_raw_picks = []

        # Remap compact keys to full keys using the decoder module
        from src.prompts.decoder import normalize_response

        try:
            # Process raw AI response strings into expanded pick objects
            # CRITICAL: Track which message IDs were in each batch to prevent cross-contamination
            # picks = [] # REMOVED: We append to existing picks list
            for batch_idx, raw_response_str in enumerate(all_raw_picks):
                # Get the valid message IDs for this batch
                valid_ids = None
                if batch_idx < len(batches):
                    valid_ids = [
                        int(m.get("id"))
                        for m in batches[batch_idx]
                        if m.get("id") is not None
                    ]

                # normalize_response handles:
                # 1. JSON extraction from string (removing <think> blocks, markdown)
                # 2. Compact key expansion (p -> pick, l -> league) via expand=True
                # 3. Message ID filtering to prevent hallucination/cross-contamination
                batch_picks = normalize_response(
                    raw_response_str, expand=True, valid_message_ids=valid_ids
                )
                picks.extend(batch_picks)

            picks = backfill_odds(picks)
            picks = enrich_picks(picks, target_date)

            logging.info(f"Extracted {len(picks)} total picks (Rule-Based + AI).")

            # 6.5 POST-PARSE DEDUPLICATION
            # Different leakers often repost the same capper's picks with different formatting
            # Deduplicate by normalized (capper_name, pick) after parsing
            logging.info("Deduplicating parsed picks...")
            picks = deduplicate_by_capper(picks)
            logging.info(f"After dedup: {len(picks)} unique picks.")

            # 7. VALIDATION & REFINEMENT
            logging.info("Validating and Refining picks (The Auditor)...")

            # Create map of message ID to message object for context checks
            msg_map = {}
            for m in selected_msgs:
                if m.get("id") is not None:
                    msg_map[int(m["id"])] = m

            reparse_ids = set()
            semantic_issues = {}

            # First pass: Check for missing picks (Multi-Pick Validator)
            _, missing_ids = validate_and_flag_missing(selected_msgs, picks)
            reparse_ids.update(missing_ids)
            if missing_ids:
                logging.warning(
                    f"Potential missing picks in {len(missing_ids)} messages."
                )

            # Second pass: Semantic & Confidence Checks
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
                        # Attempt heuristic fix first
                        fixed_p = SemanticValidator.fix_pick(p, reason)
                        is_valid_now, reason_now = SemanticValidator.validate(fixed_p)

                        if is_valid_now:
                            p.update(fixed_p)
                            logging.info(f"Auto-fixed pick: {reason}")
                        else:
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Pick '{p.get('pick')}' invalid: {reason}"
                            )
                            reparse_ids.add(mid_int)

                    # B. Confidence Check
                    conf = p.get("confidence")
                    if conf is not None:
                        try:
                            conf_val = float(conf)
                            if conf_val < 8:  # Threshold
                                if mid_int not in semantic_issues:
                                    semantic_issues[mid_int] = []
                                semantic_issues[mid_int].append(
                                    f"Low confidence ({conf_val}/10)."
                                )
                                reparse_ids.add(mid_int)
                        except ValueError:
                            pass

                    # C. Contextual Logic Checks (Unit/Parlay Mismatch)
                    msg = msg_map.get(mid_int)
                    if msg:
                        text_upper = (
                            msg.get("text", "") + "\n" + msg.get("ocr_text", "")
                        ).upper()

                        # C1. Unit Header Mismatch
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
                        if "PARLAY" in text_upper and p.get("type") not in [
                            "Parlay",
                            "Unknown",
                        ]:
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Text mentions 'PARLAY' but pick is type '{p.get('type')}'."
                            )
                            reparse_ids.add(mid_int)

            # Execute Refinement if needed
            reparse_ids_list = list(reparse_ids)
            if reparse_ids_list:
                logging.info(
                    f"Refining {len(reparse_ids_list)} messages based on validation flags..."
                )

                reparse_batch = []
                for m in selected_msgs:
                    if int(m.get("id")) in reparse_ids:
                        # Clone and add hints
                        retry_msg = m.copy()

                        m_id = int(m.get("id"))
                        msg_picks = [p for p in picks if p.get("message_id") == m_id]

                        ocr_text = retry_msg.get("ocr_text", "")
                        if not ocr_text and retry_msg.get("ocr_texts"):
                            ocr_text = "\n".join(retry_msg["ocr_texts"])

                        hints = []
                        # Multi-Pick Hint
                        from src.multi_pick_validator import MultiPickValidator

                        if m_id in missing_ids:  # reusing previous list
                            hints.append(
                                MultiPickValidator.get_reparse_hint(
                                    ocr_text, msg_picks, retry_msg.get("text", "")
                                )
                            )

                        # Semantic Hints
                        if m_id in semantic_issues:
                            hints.append("\n### CORRECTION NEEDED")
                            hints.append("The following issues were flagged:")
                            for issue in semantic_issues[m_id]:
                                hints.append(f"- {issue}")
                            hints.append(
                                "Please fix these errors in your re-extraction."
                            )

                        full_hint = "\n\n".join(hints)
                        retry_msg["text"] = (
                            retry_msg.get("text", "") + "\n\n" + full_hint
                        )[:3500]
                        reparse_batch.append(retry_msg)

                if reparse_batch:
                    try:
                        # Reprocess with high priority (or just normal batching)
                        reparse_batches = [
                            reparse_batch[i : i + BATCH_SIZE]
                            for i in range(0, len(reparse_batch), BATCH_SIZE)
                        ]
                        reparse_results = parallel_processor.process_batches(
                            reparse_batches
                        )

                        new_picks_count = 0
                        for batch_idx, raw_response_str in enumerate(reparse_results):
                            valid_ids = None
                            if batch_idx < len(reparse_batches):
                                valid_ids = [
                                    int(m.get("id"))
                                    for m in reparse_batches[batch_idx]
                                    if m.get("id") is not None
                                ]

                            new_batch_picks = normalize_response(
                                raw_response_str,
                                expand=True,
                                valid_message_ids=valid_ids,
                            )

                            # Replace old picks
                            new_picks_by_id = {}
                            for p in new_batch_picks:
                                mid = p.get("message_id")
                                if mid not in new_picks_by_id:
                                    new_picks_by_id[mid] = []
                                new_picks_by_id[mid].append(p)

                            for mid, msg_new_picks in new_picks_by_id.items():
                                if msg_new_picks:
                                    # Remove old picks
                                    picks = [
                                        p
                                        for p in picks
                                        if str(p.get("message_id")) != str(mid)
                                    ]
                                    # Add new picks
                                    picks.extend(msg_new_picks)
                                    new_picks_count += len(msg_new_picks)

                        logging.info(
                            f"Refinement complete. Replaced with {new_picks_count} refined picks."
                        )
                        picks = backfill_odds(picks)
                        picks = enrich_picks(picks, target_date)
                        picks = deduplicate_by_capper(picks)  # Re-deduplicate

                    except Exception as e:
                        logging.error(f"Refinement failed: {e}")

            # Two-Pass Verification (Parsing Check)
            if not TwoPassVerifier.verify_parsing_result(picks):
                logging.warning("Low confidence in parsing result structure.")

            # 7.4 Verification Report (Pre-Grading)
            report_file = os.path.join(
                OUTPUT_DIR, f"verification_report_{target_date}.md"
            )
            logging.info(f"Generating verification report: {report_file}")

            # Ensure msg_map exists
            if "msg_map" not in locals():
                msg_map = {}
                for m in selected_msgs:
                    if m.get("id") is not None:
                        msg_map[int(m["id"])] = m

            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(f"# Pick Verification Report - {target_date}\n\n")
                    f.write(f"**Total Picks:** {len(picks)}\n\n")

                    picks_by_msg = {}
                    for p in picks:
                        mid = p.get("message_id")
                        if mid:
                            try:
                                mid_int = int(mid)
                                if mid_int not in picks_by_msg:
                                    picks_by_msg[mid_int] = []
                                picks_by_msg[mid_int].append(p)
                            except:
                                pass

                    # Sort by message ID
                    for mid in sorted(picks_by_msg.keys()):
                        msg_picks = picks_by_msg[mid]
                        msg = msg_map.get(mid)

                        f.write(f"---\n\n")
                        f.write(f"## Message ID: {mid}\n\n")

                        if msg:
                            f.write("### 📝 Source Message\n")
                            if msg.get("author"):
                                f.write(f"**Author:** {msg['author']}\n")

                            raw_text = msg.get("text", "").strip()
                            if raw_text:
                                formatted_text = raw_text.replace("\n", "\n> ")
                                f.write(f"**Text:**\n> {formatted_text}\n\n")

                            ocr = msg.get("ocr_text", "").strip()
                            if ocr:
                                formatted_ocr = ocr.replace("\n", "\n> ")
                                f.write(f"**OCR:**\n> {formatted_ocr}\n\n")

                            images = msg.get("images") or (
                                [msg.get("image")] if msg.get("image") else []
                            )
                            if images:
                                f.write(f"**Images:**\n")
                                for img in images:
                                    f.write(f"- `{img}`\n")
                                f.write("\n")
                        else:
                            f.write("**⚠️ Source Message Not Found**\n\n")

                        f.write(f"### 🎯 Parsed Picks\n")
                        f.write("| Pick | Odds | Units | Type | Result |\n")
                        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                        for p in msg_picks:
                            pick_str = str(p.get("pick", "-")).replace("|", "\|")
                            odds_str = str(p.get("odds", "-"))
                            units_str = str(p.get("units", "-"))
                            type_str = str(p.get("type", "-"))
                            result_str = str(p.get("result", "-"))
                            f.write(
                                f"| {pick_str} | {odds_str} | {units_str} | {type_str} | {result_str} |\n"
                            )
                        f.write("\n")
                logging.info(f"Verification report saved to: {report_file}")
            except Exception as e:
                logging.error(f"Failed to generate verification report: {e}")

            # 7.5 GRADING
            logging.info("Grading picks against ESPN scores...")
            try:
                from src.grader import grade_picks
                from src.score_fetcher import fetch_scores_for_date
                from src.grading.constants import LEAGUE_ALIASES_MAP

                # OPTIMIZATION: Extract leagues from picks to fetch only what's needed
                relevant_leagues = set()
                for p in picks:
                    lg = (p.get("league") or p.get("lg") or "").lower()
                    if lg:
                        # Normalize to canonical league name
                        relevant_leagues.add(LEAGUE_ALIASES_MAP.get(lg, lg))

                logging.info(
                    f"Fetching scores for leagues: {', '.join(sorted(relevant_leagues)) or 'all'}"
                )
                scores = fetch_scores_for_date(
                    target_date,
                    requested_leagues=list(relevant_leagues)
                    if relevant_leagues
                    else None,
                )
                logging.info(f"Fetched {len(scores)} game scores")

                picks = grade_picks(picks, scores)

                # Count results
                wins = sum(1 for p in picks if p.get("result") == "Win")
                losses = sum(1 for p in picks if p.get("result") == "Loss")
                pending = sum(
                    1
                    for p in picks
                    if p.get("result") in ["Pending", "Pending/Unknown", None, ""]
                )

                logging.info(
                    f"Grading complete: {wins} Wins, {losses} Losses, {pending} Pending"
                )
            except Exception as e:
                logging.error(f"Grading failed: {e}")

        except Exception as e:
            logging.error(f"Parsing/Grading failed: {e}", exc_info=True)
            return

    # 6. PARSING (AI FILL) - HYBRID PARALLEL STRATEGY
    logging.info("Generating AI Prompts and Parsing (Parallel Multi-Provider Mode)...")

    # Configuration
    BATCH_SIZE = 10  # Messages per batch

    # Split into batches
    batches = [
        selected_msgs[i : i + BATCH_SIZE]
        for i in range(0, len(selected_msgs), BATCH_SIZE)
    ]
    logging.info(
        f"Processing {len(batches)} batches ({BATCH_SIZE} msgs each) across all available providers..."
    )

    # Use the new Parallel Batch Processor
    from src.parallel_batch_processor import parallel_processor

    try:
        # This handles distribution across Cerebras, Groq, Mistral, Gemini, OpenRouter
        all_raw_picks = parallel_processor.process_batches(batches)
        logging.info(f"Total extracted batches: {len(all_raw_picks)}")

    except Exception as e:
        logging.error(f"Parallel processing failed: {e}")
        all_raw_picks = []

    # Remap compact keys to full keys using the decoder module
    from src.prompts.decoder import normalize_response

    try:
        # Process raw AI response strings into expanded pick objects
        # CRITICAL: Track which message IDs were in each batch to prevent cross-contamination
        picks = []
        for batch_idx, raw_response_str in enumerate(all_raw_picks):
            # Get the valid message IDs for this batch
            valid_ids = None
            if batch_idx < len(batches):
                valid_ids = [
                    int(m.get("id"))
                    for m in batches[batch_idx]
                    if m.get("id") is not None
                ]

            # normalize_response handles:
            # 1. JSON extraction from string (removing <think> blocks, markdown)
            # 2. Compact key expansion (p -> pick, l -> league) via expand=True
            # 3. Message ID filtering to prevent hallucination/cross-contamination
            batch_picks = normalize_response(
                raw_response_str, expand=True, valid_message_ids=valid_ids
            )
            picks.extend(batch_picks)

        picks = backfill_odds(picks)
        picks = enrich_picks(picks, target_date)

        logging.info(f"Extracted {len(picks)} raw picks.")

        # 6.5 POST-PARSE DEDUPLICATION
        # Different leakers often repost the same capper's picks with different formatting
        # Deduplicate by normalized (capper_name, pick) after parsing
        logging.info("Deduplicating parsed picks...")
        picks = deduplicate_by_capper(picks)
        logging.info(f"After dedup: {len(picks)} unique picks.")

        # 7. VALIDATION & REFINEMENT
        logging.info("Validating and Refining picks (The Auditor)...")

        # Create map of message ID to message object for context checks
        msg_map = {}
        for m in selected_msgs:
            if m.get("id") is not None:
                msg_map[int(m["id"])] = m

        reparse_ids = set()
        semantic_issues = {}

        # First pass: Check for missing picks (Multi-Pick Validator)
        _, missing_ids = validate_and_flag_missing(selected_msgs, picks)
        reparse_ids.update(missing_ids)
        if missing_ids:
            logging.warning(f"Potential missing picks in {len(missing_ids)} messages.")

        # Second pass: Semantic & Confidence Checks
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
                    # Attempt heuristic fix first
                    fixed_p = SemanticValidator.fix_pick(p, reason)
                    is_valid_now, reason_now = SemanticValidator.validate(fixed_p)

                    if is_valid_now:
                        p.update(fixed_p)
                        logging.info(f"Auto-fixed pick: {reason}")
                    else:
                        if mid_int not in semantic_issues:
                            semantic_issues[mid_int] = []
                        semantic_issues[mid_int].append(
                            f"Pick '{p.get('pick')}' invalid: {reason}"
                        )
                        reparse_ids.add(mid_int)

                # B. Confidence Check
                conf = p.get("confidence")
                if conf is not None:
                    try:
                        conf_val = float(conf)
                        if conf_val < 8:  # Threshold
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Low confidence ({conf_val}/10)."
                            )
                            reparse_ids.add(mid_int)
                    except ValueError:
                        pass

                # C. Contextual Logic Checks (Unit/Parlay Mismatch)
                msg = msg_map.get(mid_int)
                if msg:
                    text_upper = (
                        msg.get("text", "") + "\n" + msg.get("ocr_text", "")
                    ).upper()

                    # C1. Unit Header Mismatch
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
                    if "PARLAY" in text_upper and p.get("type") not in [
                        "Parlay",
                        "Unknown",
                    ]:
                        if mid_int not in semantic_issues:
                            semantic_issues[mid_int] = []
                        semantic_issues[mid_int].append(
                            f"Text mentions 'PARLAY' but pick is type '{p.get('type')}'."
                        )
                        reparse_ids.add(mid_int)

        # Execute Refinement if needed
        reparse_ids_list = list(reparse_ids)
        if reparse_ids_list:
            logging.info(
                f"Refining {len(reparse_ids_list)} messages based on validation flags..."
            )

            reparse_batch = []
            for m in selected_msgs:
                if int(m.get("id")) in reparse_ids:
                    # Clone and add hints
                    retry_msg = m.copy()

                    m_id = int(m.get("id"))
                    msg_picks = [p for p in picks if p.get("message_id") == m_id]

                    ocr_text = retry_msg.get("ocr_text", "")
                    if not ocr_text and retry_msg.get("ocr_texts"):
                        ocr_text = "\n".join(retry_msg["ocr_texts"])

                    hints = []
                    # Multi-Pick Hint
                    from src.multi_pick_validator import MultiPickValidator

                    if m_id in missing_ids:  # reusing previous list
                        hints.append(
                            MultiPickValidator.get_reparse_hint(
                                ocr_text, msg_picks, retry_msg.get("text", "")
                            )
                        )

                    # Semantic Hints
                    if m_id in semantic_issues:
                        hints.append("\n### CORRECTION NEEDED")
                        hints.append("The following issues were flagged:")
                        for issue in semantic_issues[m_id]:
                            hints.append(f"- {issue}")
                        hints.append("Please fix these errors in your re-extraction.")

                    full_hint = "\n\n".join(hints)
                    retry_msg["text"] = (
                        retry_msg.get("text", "") + "\n\n" + full_hint
                    )[:3500]
                    reparse_batch.append(retry_msg)

            if reparse_batch:
                try:
                    # Reprocess with high priority (or just normal batching)
                    reparse_batches = [
                        reparse_batch[i : i + BATCH_SIZE]
                        for i in range(0, len(reparse_batch), BATCH_SIZE)
                    ]
                    reparse_results = parallel_processor.process_batches(
                        reparse_batches
                    )

                    new_picks_count = 0
                    for batch_idx, raw_response_str in enumerate(reparse_results):
                        valid_ids = None
                        if batch_idx < len(reparse_batches):
                            valid_ids = [
                                int(m.get("id"))
                                for m in reparse_batches[batch_idx]
                                if m.get("id") is not None
                            ]

                        new_batch_picks = normalize_response(
                            raw_response_str, expand=True, valid_message_ids=valid_ids
                        )

                        # Replace old picks
                        new_picks_by_id = {}
                        for p in new_batch_picks:
                            mid = p.get("message_id")
                            if mid not in new_picks_by_id:
                                new_picks_by_id[mid] = []
                            new_picks_by_id[mid].append(p)

                        for mid, msg_new_picks in new_picks_by_id.items():
                            if msg_new_picks:
                                # Remove old picks
                                picks = [
                                    p
                                    for p in picks
                                    if str(p.get("message_id")) != str(mid)
                                ]
                                # Add new picks
                                picks.extend(msg_new_picks)
                                new_picks_count += len(msg_new_picks)

                    logging.info(
                        f"Refinement complete. Replaced with {new_picks_count} refined picks."
                    )
                    picks = backfill_odds(picks)
                    picks = enrich_picks(picks, target_date)
                    picks = deduplicate_by_capper(picks)  # Re-deduplicate

                except Exception as e:
                    logging.error(f"Refinement failed: {e}")

        # Two-Pass Verification (Parsing Check)
        if not TwoPassVerifier.verify_parsing_result(picks):
            logging.warning("Low confidence in parsing result structure.")

        # 7.5 GRADING
        logging.info("Grading picks against ESPN scores...")
        try:
            from src.grader import grade_picks
            from src.score_fetcher import fetch_scores_for_date
            from src.grading.constants import LEAGUE_ALIASES_MAP

            # OPTIMIZATION: Extract leagues from picks to fetch only what's needed
            relevant_leagues = set()
            for p in picks:
                lg = (p.get("league") or p.get("lg") or "").lower()
                if lg:
                    # Normalize to canonical league name
                    relevant_leagues.add(LEAGUE_ALIASES_MAP.get(lg, lg))

            logging.info(
                f"Fetching scores for leagues: {', '.join(sorted(relevant_leagues)) or 'all'}"
            )
            scores = fetch_scores_for_date(
                target_date,
                requested_leagues=list(relevant_leagues) if relevant_leagues else None,
            )
            logging.info(f"Fetched {len(scores)} game scores")

            picks = grade_picks(picks, scores)

            # Count results
            wins = sum(1 for p in picks if p.get("result") == "Win")
            losses = sum(1 for p in picks if p.get("result") == "Loss")
            pending = sum(
                1
                for p in picks
                if p.get("result") in ["Pending", "Pending/Unknown", None, ""]
            )

            logging.info(
                f"Grading complete: {wins} Wins, {losses} Losses, {pending} Pending"
            )
        except Exception as e:
            logging.error(f"Grading failed: {e}")

    except Exception as e:
        logging.error(f"Parsing/Grading failed: {e}", exc_info=True)
        return

    # 8. OUTPUT
    output_file = os.path.join(OUTPUT_DIR, f"picks_{target_date}.json")
    with open(output_file, "w") as f:
        json.dump(picks, f, indent=2)

    print("\n" + "=" * 50)
    print("   RESULTS   ")
    print("=" * 50)
    print(f"Total Unique Messages: {len(unique_msgs)}")
    print(f"Messages with Picks: {len(selected_msgs)}")
    print(f"Extracted Picks: {len(picks)}")
    print(f"Saved to: {output_file}")

    # Simple Table Output
    print(
        f"{'CAPPER':<20} | {'SPORT':<10} | {'PICK':<35} | {'ODDS':<6} | {'RESULT':<8}"
    )
    print("-" * 95)
    for p in picks:
        capper_raw = p.get("capper_name") or "Unknown"
        capper = capper_raw.encode("ascii", "replace").decode("ascii")[:19]

        sport = (p.get("league") or "Unknown")[:9]

        pick_raw = p.get("pick") or "Unknown"
        pick_val = pick_raw.encode("ascii", "replace").decode("ascii")[:34]

        odds = str(p.get("odds") or "")[:5]
        result = (p.get("result") or "")[:7]
        print(f"{capper:<20} | {sport:<10} | {pick_val:<35} | {odds:<6} | {result:<8}")
    print("-" * 95)

    # 9. SUPABASE UPLOAD
    # Check for --dry-run or --no-upload flag
    # FORCE DRY RUN per user instruction
    dry_run = True  # '--dry-run' in sys.argv or '--no-upload' in sys.argv

    if dry_run:
        logging.info("Skipping Supabase upload (--dry-run mode)")
        print(
            "\n[DRY RUN] Supabase upload skipped. Review picks above and run without --dry-run to upload."
        )
    else:
        logging.info("Uploading picks to Supabase...")
        try:
            from src.supabase_client import upload_picks

            result = upload_picks(picks, target_date)

            if result.get("success"):
                logging.info(
                    f"Successfully uploaded {result.get('count', 0)} picks to Supabase"
                )
                print(
                    f"\n[SUPABASE] Uploaded {result.get('count', 0)} picks successfully!"
                )
            else:
                logging.error(f"Supabase upload failed: {result.get('error')}")
                if result.get("details"):
                    for detail in result["details"][:5]:
                        logging.warning(f"  {detail}")
        except Exception as e:
            logging.error(f"Supabase upload error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScraper stopped by user.")
    except Exception as e:
        logging.error(f"Fatal Error: {e}", exc_info=True)
