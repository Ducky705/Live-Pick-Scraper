import logging
from typing import Any

from src.game_enricher import enrich_picks
from src.multi_pick_validator import MultiPickValidator, validate_and_flag_missing
from src.parallel_batch_processor import parallel_processor
from src.pick_deduplicator import deduplicate_by_capper
from src.prompts.decoder import normalize_response
from src.semantic_validator import SemanticValidator
from src.two_pass_verifier import TwoPassVerifier
from src.utils import auto_group_parlays, backfill_odds, normalize_to_ascii, safe_write_progress


logger = logging.getLogger(__name__)


class ExtractionPipeline:
    @staticmethod
    def run(
        messages: list[dict[str, Any]],
        target_date: str,
        batch_size: int = 20,  # US-006: Increased to 20 for throughput
        strategy: str = "groq",
    ) -> list[dict[str, Any]]:
        """
        Runs the full AI extraction pipeline:
        1. Parallel AI Processing
        2. Normalization
        3. Enrichment
        4. Deduplication
        5. Validation (The Auditor) & Refinement
        """
        if not messages:
            return []

        # Initialize progress log (US-202)
        progress_log = [f"# Extraction Pipeline Progress - {target_date}", f"Started with {len(messages)} messages."]
        safe_write_progress("\n".join(progress_log))

        # US-001: Normalize Unicode characters (St Mary's, etc.)
        for m in messages:
            if m.get("text"):
                m["text"] = normalize_to_ascii(m["text"])
            if m.get("ocr_text"):
                m["ocr_text"] = normalize_to_ascii(m["ocr_text"])
            if m.get("ocr_texts"):
                m["ocr_texts"] = [normalize_to_ascii(t) for t in m["ocr_texts"]]

        # 0. Rule Based Extraction (Fast Path)

        from src.rule_based_extractor import RuleBasedExtractor

        rule_picks, messages_for_ai = RuleBasedExtractor.extract(messages)
        picks = list(rule_picks)  # Initialize with rule picks

        # US-001: Validate Rule-Based Picks
        # If RuleBased found SOME picks but Validator expects MORE, send to AI.
        if rule_picks:
            # Identify messages handled by RuleBased
            all_msg_ids = {str(m.get("id")) for m in messages if m.get("id") is not None}
            ai_msg_ids = {str(m.get("id")) for m in messages_for_ai if m.get("id") is not None}
            rule_handled_ids = all_msg_ids - ai_msg_ids

            if rule_handled_ids:
                msg_map = {str(m.get("id")): m for m in messages if m.get("id") is not None}
                rule_handled_msgs = [msg_map[mid] for mid in rule_handled_ids if mid in msg_map]

                # Run validation on just the rule-based outcomes
                _, missing_ids = validate_and_flag_missing(rule_handled_msgs, picks)

                if missing_ids:
                    logger.info(
                        f"Rule-Based Validation: {len(missing_ids)} messages flagged as incomplete. Escalating to AI."
                    )

                    # US-001 Safety Net: Do NOT delete picks yet.
                    # We will replace them only if AI returns a valid result.
                    # Just add messages to AI queue.

                    # 2. Add messages back to AI queue
                    current_ai_ids = {str(m.get("id")) for m in messages_for_ai}
                    for mid in missing_ids:
                        mid_str = str(mid)
                        if mid_str not in current_ai_ids and mid_str in msg_map:
                            messages_for_ai.append(msg_map[mid_str])

        if not messages_for_ai:
            logger.info("All messages handled by Rule-Based Extractor! Skipping AI pipeline.")
        else:
            logger.info(f"Generating AI Prompts for {len(messages_for_ai)} remaining messages...")
            # Split into batches
            batches = [messages_for_ai[i : i + batch_size] for i in range(0, len(messages_for_ai), batch_size)]

            # 1. AI Processing
            try:
                if strategy == "round_robin":
                    logger.info("Using Strategy: ROUND ROBIN (Mixed Providers)")
                    all_raw_picks = parallel_processor.process_batches(batches)
                else:
                    logger.info("Using Strategy: GROQ PRIORITY (16 concurrent)")
                    all_raw_picks = parallel_processor.process_batches_groq_priority(batches)
            except Exception as e:
                logger.error(f"Parallel processing failed: {e}")
                all_raw_picks = []

            # 2. Normalization
            # Prepare message context for anti-hallucination (ID -> Text+OCR)
            message_context = {}
            for m in messages_for_ai:
                mid = m.get("id")
                if mid:
                    try:
                        text = m.get("text", "")
                        ocr = m.get("ocr_text", "")
                        # Combine text + OCR for full context search
                        full_text = f"{text}\n{ocr}"
                        # Store context by string ID (not int)
                        message_context[str(mid)] = full_text
                    except (ValueError, TypeError):
                        pass

            for batch_idx, raw_response_str in enumerate(all_raw_picks):
                if raw_response_str is None:
                    continue

                valid_ids = None
                if batch_idx < len(batches):
                    # Remove int() cast to support string IDs (e.g., synthetic)
                    valid_ids = [str(m.get("id")) for m in batches[batch_idx] if m.get("id") is not None]

                batch_picks = normalize_response(
                    raw_response_str,
                    expand=True,
                    valid_message_ids=valid_ids,
                    message_context=message_context,
                )
                picks.extend(batch_picks)

            progress_log.append(f"- [x] AI Processing complete. Total picks so far: {len(picks)}")
            safe_write_progress("\n".join(progress_log))

        # 2.5 Auto-Group Parlays
        # Ensure we have context for all messages (even rule-based ones)
        full_message_context = {}
        msg_author_map = {}
        for m in messages:
            if m.get("id"):
                str_id = str(m["id"])
                try:
                    text = m.get("text", "")
                    ocr = m.get("ocr_text", "")
                    # Store by string ID
                    full_message_context[str_id] = f"{text}\n{ocr}"
                except:
                    pass

                if m.get("author"):
                    msg_author_map[str_id] = m.get("author")

        # US-004: Ensure capper_name is populated from message author if missing
        # This prevents "Unknown" cappers from different messages being merged.
        for p in picks:
            mid = str(p.get("message_id", ""))
            if mid in msg_author_map:
                current_capper = p.get("capper_name", "Unknown")
                # Trust the source metadata if the pick doesn't have a specific capper
                if current_capper.lower() == "unknown":
                    p["capper_name"] = msg_author_map[mid]

        picks = auto_group_parlays(picks, full_message_context)

        # 3. Enrichment & Basic Dedup
        picks = backfill_odds(picks)
        picks = enrich_picks(picks, target_date)
        picks = deduplicate_by_capper(picks)

        logger.info(f"Initial extraction yielded {len(picks)} picks.")

        # 4. Validation & Refinement (The Auditor)
        # Use string IDs for map
        msg_map = {str(m["id"]): m for m in messages if m.get("id") is not None}
        reparse_ids = set()
        semantic_issues: dict[str, list[str]] = {}

        # 4a. Check for missing picks
        _, missing_ids = validate_and_flag_missing(messages, picks)
        reparse_ids.update({str(mid) for mid in missing_ids})

        # Identify messages that have at least one High Confidence (Rule-Based) pick
        high_conf_msg_ids = set()
        for p in picks:
            if p.get("confidence") is not None and float(p.get("confidence", 0)) > 9.0:
                mid = p.get("message_id")
                if mid:
                    try:
                        # Store as string
                        high_conf_msg_ids.add(str(mid))
                    except:
                        pass

        # 4b. Semantic & Confidence Checks
        for p in picks:
            mid = p.get("message_id")
            if mid:
                try:
                    # Treat as string
                    mid_str = str(mid)
                except (ValueError, TypeError):
                    continue

                # Semantic Validation
                is_valid, reason = SemanticValidator.validate(p)
                if not is_valid:
                    fixed_p = SemanticValidator.fix_pick(p, reason or "Unknown validation error")
                    is_valid_now, reason_now = SemanticValidator.validate(fixed_p)

                    if is_valid_now:
                        p.update(fixed_p)
                    else:
                        if mid_str not in semantic_issues:
                            semantic_issues[mid_str] = []
                        semantic_issues[mid_str].append(f"Pick '{p.get('pick')}' invalid: {reason}")
                        reparse_ids.add(mid_str)

                # Confidence Check
                conf = p.get("confidence")
                if conf is not None:
                    try:
                        if float(conf) < 8:
                            if mid_str not in semantic_issues:
                                semantic_issues[mid_str] = []
                            semantic_issues[mid_str].append(f"Low confidence ({conf}/10).")
                            reparse_ids.add(mid_str)
                    except ValueError:
                        pass

                # Contextual Checks
                # Skip contextual checks if confidence is very high (Rule-Based)
                if conf is not None and float(conf) > 9.0:
                    pass
                else:
                    # If this message ALREADY has a high confidence pick, ignore low confidence issues
                    # This prevents duplicates from AI tainting the message
                    if mid_str in high_conf_msg_ids:
                        continue

                    msg = msg_map.get(mid_str)
                    if msg:
                        text_upper = (msg.get("text", "") + "\n" + msg.get("ocr_text", "")).upper()

                        # Unit Mismatch
                        # CRITICAL OPTIMIZATION: Only run global unit check if there's only 1 pick.
                        # Otherwise, "5U" appearing anywhere flags ALL 1U picks in a multi-pick message.
                        picks_for_msg = [p for p in picks if str(p.get("message_id")) == mid_str]

                        if p.get("units", 1.0) == 1.0 and len(picks_for_msg) == 1:
                            potential_units = 0
                            if "10U" in text_upper or "MAX BET" in text_upper:
                                potential_units = 10
                            elif "5U" in text_upper:
                                potential_units = 5
                            elif "3U" in text_upper:
                                potential_units = 3

                            if potential_units > 1:
                                if mid_str not in semantic_issues:
                                    semantic_issues[mid_str] = []
                                semantic_issues[mid_str].append(
                                    f"Possible Unit Mismatch: Text implies {potential_units}U, pick has 1U."
                                )
                                reparse_ids.add(mid_str)

                        # Parlay Mismatch
                        if "PARLAY" in text_upper and p.get("type") not in [
                            "Parlay",
                            "Unknown",
                        ]:
                            if mid_str not in semantic_issues:
                                semantic_issues[mid_str] = []
                            semantic_issues[mid_str].append(
                                f"Text mentions 'PARLAY' but pick is type '{p.get('type')}'."
                            )
                            reparse_ids.add(mid_str)

        # 5. Execute Refinement
        reparse_ids_list = list(reparse_ids)
        if reparse_ids_list:
            logger.info(f"Refining {len(reparse_ids_list)} messages...")

            reparse_batch = []
            for m in messages:
                m_id_str = str(m.get("id"))
                if m_id_str in reparse_ids:
                    retry_msg = m.copy()
                    msg_picks = [p for p in picks if str(p.get("message_id")) == m_id_str]

                    ocr_text = retry_msg.get("ocr_text", "")
                    if not ocr_text and retry_msg.get("ocr_texts"):
                        ocr_text = "\n".join(retry_msg["ocr_texts"])

                    hints = []
                    # Check if missing
                    is_missing = False
                    for p in picks:
                        # logic for checking missing ids was removed/simplified above in `missing_ids` set
                        pass

                    if m_id_str in missing_ids:  # checking against set of strings
                        hints.append(
                            MultiPickValidator.get_reparse_hint(ocr_text, msg_picks, retry_msg.get("text", ""))
                        )

                    if m_id_str in semantic_issues:
                        hints.append("\n### CORRECTION NEEDED")
                        hints.append("The following issues were flagged:")
                        for issue in semantic_issues[m_id_str]:
                            hints.append(f"- {issue}")
                        hints.append("Please fix these errors in your re-extraction.")

                    full_hint = "\n\n".join(hints)

                    # DEBUG LOG
                    logger.debug(f"[DEBUG] Reparsing Msg {m_id_str} because: {full_hint}")

                    retry_msg["text"] = (retry_msg.get("text", "") + "\n\n" + full_hint)[:3500]
                    reparse_batch.append(retry_msg)

            if reparse_batch:
                try:
                    # Refinement Batching (US-001: Optimization)
                    refine_batch_sz = 5  # US-200: Optimized for throughput (fewer requests)
                    reparse_batches = [
                        reparse_batch[i : i + refine_batch_sz] for i in range(0, len(reparse_batch), refine_batch_sz)
                    ]
                    reparse_results = parallel_processor.process_batches(
                        reparse_batches,
                        allowed_providers=[
                            # "groq", # US-200: Disabled to avoid 429s
                            "cerebras",  # US-200: Primary for refinement (Stable 2s delay)
                            # "mistral", # US-200: Disabled to avoid latency spikes
                        ],
                    )

                    new_picks_count = 0
                    for batch_idx, raw_response_str in enumerate(reparse_results):
                        if raw_response_str is None:
                            continue

                        valid_ids = None
                        if batch_idx < len(reparse_batches):
                            valid_ids = [
                                str(m.get("id"))  # Keep as string/any
                                for m in reparse_batches[batch_idx]
                                if m.get("id") is not None
                            ]

                        new_batch_picks = normalize_response(raw_response_str, expand=True, valid_message_ids=valid_ids)

                        # Replace picks
                        new_picks_by_id: dict[Any, list[dict[str, Any]]] = {}
                        for p in new_batch_picks:
                            mid = p.get("message_id")
                            # Normalize key to string
                            mid_key = str(mid) if mid is not None else None
                            if mid_key:
                                if mid_key not in new_picks_by_id:
                                    new_picks_by_id[mid_key] = []
                                new_picks_by_id[mid_key].append(p)

                        for mid_key_str, msg_new_picks in new_picks_by_id.items():
                            if msg_new_picks:
                                # US-003: Protect high-confidence rule-based picks (> 9.0)
                                # We remove all picks for this message EXCEPT those with high confidence.
                                # These high-conf picks will then be merged with AI results during deduplication.
                                picks = [
                                    p
                                    for p in picks
                                    if str(p.get("message_id")) != mid_key_str or float(p.get("confidence") or 0) > 9.0
                                ]
                                picks.extend(msg_new_picks)
                                new_picks_count += len(msg_new_picks)

                    logger.info(f"Refinement complete. Replaced with {new_picks_count} refined picks.")
                    picks = backfill_odds(picks)
                    picks = enrich_picks(picks, target_date)
                    picks = deduplicate_by_capper(picks)

                except Exception as e:
                    logger.error(f"Refinement failed: {e}")

        # Final Verification
        if not TwoPassVerifier.verify_parsing_result(picks):
            logger.warning("Low confidence in parsing result structure.")

        # US-012: Final Filtering (False Positive Cleanup)
        # Remove picks that are still invalid after refinement (Impossible Odds, No Team Name)
        try:
            final_valid_picks = []
            dropped_count = 0
            for p in picks:
                is_valid, reason = SemanticValidator.validate(p)
                if is_valid:
                    final_valid_picks.append(p)
                else:
                    # Log the drop
                    dropped_count += 1
                    mid = p.get("message_id", "unknown")
                    logger.info(f"Dropping Invalid Pick (Msg {mid}): '{p.get('pick')}' - Reason: {reason}")

            if dropped_count > 0:
                logger.info(f"Final Filtering dropped {dropped_count} invalid picks.")
                picks = final_valid_picks

            progress_log.append(f"- [x] Final Filtering complete. Dropped {dropped_count} picks.")
        except Exception as e:
            logger.error(f"Final Filtering crashed: {e}", exc_info=True)
            progress_log.append(f"- [!] Final Filtering crashed: {e}")
            # Resilience: Continue with original picks

        safe_write_progress("\n".join(progress_log))

        # 7.4 Verification Report (Pre-Grading)
        # GENERATE REPORT FOR ALL MESSAGES (Even those with no picks)
        # This is essential for the "Audit Dry Run" the user requested.
        import os

        from config import OUTPUT_DIR

        report_file = os.path.join(OUTPUT_DIR, f"verification_report_{target_date}.md")
        logger.info(f"Generating verification report: {report_file}")

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(f"# Pick Verification Report - {target_date}\n\n")
                f.write(f"**Total Messages Processed:** {len(msg_map)}\n")
                f.write(f"**Total Picks Extracted:** {len(picks)}\n\n")

                picks_by_msg: dict[str, list[dict[str, Any]]] = {}
                for p in picks:
                    mid = p.get("message_id")
                    if mid:
                        try:
                            # Use string for consistent lookup
                            mid_str = str(mid)
                            if mid_str not in picks_by_msg:
                                picks_by_msg[mid_str] = []
                            picks_by_msg[mid_str].append(p)
                        except:
                            pass

                # Sort by message ID
                # CRITICAL: Iterate over ALL messages to show "No Picks Found" cases as requested
                all_msg_ids = sorted(msg_map.keys())

                for mid in all_msg_ids:
                    msg_picks = picks_by_msg.get(mid, [])
                    msg = msg_map.get(mid)

                    f.write("---\n\n")
                    f.write(f"## Message ID: {mid}\n\n")

                    if msg:
                        f.write("### 📝 Source Message\n")
                        if msg.get("author"):
                            f.write(f"**Author:** {msg['author']}\n")

                        # Source Info (Channel/Date)
                        if msg.get("channel_name"):
                            f.write(f"**Channel:** {msg['channel_name']}\n")
                        if msg.get("date"):
                            f.write(f"**Date:** {msg['date']}\n")

                        raw_text = msg.get("text", "").strip()
                        if raw_text:
                            formatted_text = raw_text.replace("\n", "\n> ")
                            f.write(f"**Text:**\n> {formatted_text}\n\n")

                        ocr = msg.get("ocr_text", "").strip()
                        if ocr:
                            formatted_ocr = ocr.replace("\n", "\n> ")
                            f.write(f"**OCR:**\n> {formatted_ocr}\n\n")

                        images = msg.get("images") or ([msg.get("image")] if msg.get("image") else [])
                        if images:
                            f.write("**Images:**\n")
                            for img in images:
                                f.write(f"- `{img}`\n")
                            f.write("\n")
                    else:
                        f.write("**⚠️ Source Message Not Found**\n\n")

                    f.write("### 🎯 Parsed Picks\n")
                    if msg_picks:
                        f.write("| Pick | Odds | Units | Type | Result |\n")
                        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                        for p in msg_picks:
                            pick_str = str(p.get("pick", "-")).replace("|", r"\|")
                            odds_str = str(p.get("odds", "-"))
                            units_str = str(p.get("units", "-"))
                            type_str = str(p.get("type", "-"))
                            result_str = str(p.get("result", "-"))
                            f.write(f"| {pick_str} | {odds_str} | {units_str} | {type_str} | {result_str} |\n")
                    else:
                        f.write("> *No picks extracted from this message.*\n")

                    f.write("\n")

            logger.info(f"Verification report saved to: {report_file}")
            progress_log.append(f"- [x] Verification report generated: {report_file}")
        except Exception as e:
            logger.error(f"Failed to generate verification report: {e}")
            progress_log.append(f"- [!] Verification report generation failed: {e}")

        safe_write_progress("\n".join(progress_log))

        return picks
