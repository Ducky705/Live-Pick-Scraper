import logging
import time
from typing import List, Dict, Any
from src.parallel_batch_processor import parallel_processor
from src.prompts.decoder import normalize_response
from src.utils import backfill_odds
from src.game_enricher import enrich_picks
from src.pick_deduplicator import deduplicate_by_capper
from src.multi_pick_validator import validate_and_flag_missing, MultiPickValidator
from src.semantic_validator import SemanticValidator
from src.two_pass_verifier import TwoPassVerifier

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    @staticmethod
    def run(
        messages: List[Dict[str, Any]], target_date: str, batch_size: int = 10
    ) -> List[Dict[str, Any]]:
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

        # 0. Rule Based Extraction (Fast Path)
        from src.rule_based_extractor import RuleBasedExtractor

        rule_picks, messages_for_ai = RuleBasedExtractor.extract(messages)
        picks = list(rule_picks)  # Initialize with rule picks

        if not messages_for_ai:
            logger.info(
                "All messages handled by Rule-Based Extractor! Skipping AI pipeline."
            )
        else:
            logger.info(
                f"Generating AI Prompts for {len(messages_for_ai)} remaining messages..."
            )
            # Split into batches
            batches = [
                messages_for_ai[i : i + batch_size]
                for i in range(0, len(messages_for_ai), batch_size)
            ]

            # 1. AI Processing
            try:
                all_raw_picks = parallel_processor.process_batches(batches)
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
                        message_context[int(mid)] = full_text
                    except (ValueError, TypeError):
                        pass

            for batch_idx, raw_response_str in enumerate(all_raw_picks):
                valid_ids = None
                if batch_idx < len(batches):
                    valid_ids = [
                        int(m.get("id"))
                        for m in batches[batch_idx]
                        if m.get("id") is not None
                    ]

                batch_picks = normalize_response(
                    raw_response_str,
                    expand=True,
                    valid_message_ids=valid_ids,
                    message_context=message_context,
                )
                picks.extend(batch_picks)

        # 3. Enrichment & Basic Dedup
        picks = backfill_odds(picks)
        picks = enrich_picks(picks, target_date)
        picks = deduplicate_by_capper(picks)

        logger.info(f"Initial extraction yielded {len(picks)} picks.")

        # 4. Validation & Refinement (The Auditor)
        msg_map = {int(m["id"]): m for m in messages if m.get("id") is not None}
        reparse_ids = set()
        semantic_issues = {}

        # 4a. Check for missing picks
        _, missing_ids = validate_and_flag_missing(messages, picks)
        reparse_ids.update(missing_ids)

        # Identify messages that have at least one High Confidence (Rule-Based) pick
        high_conf_msg_ids = set()
        for p in picks:
            if p.get("confidence") is not None and float(p.get("confidence", 0)) > 9.0:
                mid = p.get("message_id")
                if mid:
                    try:
                        high_conf_msg_ids.add(int(mid))
                    except:
                        pass

        # 4b. Semantic & Confidence Checks
        for p in picks:
            mid = p.get("message_id")
            if mid:
                try:
                    mid_int = int(mid)
                except (ValueError, TypeError):
                    continue

                # Semantic Validation
                is_valid, reason = SemanticValidator.validate(p)
                if not is_valid:
                    fixed_p = SemanticValidator.fix_pick(p, reason)
                    is_valid_now, reason_now = SemanticValidator.validate(fixed_p)

                    if is_valid_now:
                        p.update(fixed_p)
                    else:
                        if mid_int not in semantic_issues:
                            semantic_issues[mid_int] = []
                        semantic_issues[mid_int].append(
                            f"Pick '{p.get('pick')}' invalid: {reason}"
                        )
                        reparse_ids.add(mid_int)

                # Confidence Check
                conf = p.get("confidence")
                if conf is not None:
                    try:
                        if float(conf) < 8:
                            if mid_int not in semantic_issues:
                                semantic_issues[mid_int] = []
                            semantic_issues[mid_int].append(
                                f"Low confidence ({conf}/10)."
                            )
                            reparse_ids.add(mid_int)
                    except ValueError:
                        pass

                # Contextual Checks
                # Skip contextual checks if confidence is very high (Rule-Based)
                if conf is not None and float(conf) > 9.0:
                    pass
                else:
                    # If this message ALREADY has a high confidence pick, ignore low confidence issues
                    # This prevents duplicates from AI tainting the message
                    if mid_int in high_conf_msg_ids:
                        continue

                    msg = msg_map.get(mid_int)
                    if msg:
                        text_upper = (
                            msg.get("text", "") + "\n" + msg.get("ocr_text", "")
                        ).upper()

                        # Unit Mismatch
                        if p.get("units", 1.0) == 1.0:
                            potential_units = 0
                            if "10U" in text_upper or "MAX BET" in text_upper:
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

                        # Parlay Mismatch
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

        # 5. Execute Refinement
        reparse_ids_list = list(reparse_ids)
        if reparse_ids_list:
            logger.info(f"Refining {len(reparse_ids_list)} messages...")

            reparse_batch = []
            for m in messages:
                if int(m.get("id")) in reparse_ids:
                    retry_msg = m.copy()
                    m_id = int(m.get("id"))
                    msg_picks = [p for p in picks if p.get("message_id") == m_id]

                    ocr_text = retry_msg.get("ocr_text", "")
                    if not ocr_text and retry_msg.get("ocr_texts"):
                        ocr_text = "\n".join(retry_msg["ocr_texts"])

                    hints = []
                    if m_id in missing_ids:
                        hints.append(
                            MultiPickValidator.get_reparse_hint(
                                ocr_text, msg_picks, retry_msg.get("text", "")
                            )
                        )

                    if m_id in semantic_issues:
                        hints.append("\n### CORRECTION NEEDED")
                        hints.append("The following issues were flagged:")
                        for issue in semantic_issues[m_id]:
                            hints.append(f"- {issue}")
                        hints.append("Please fix these errors in your re-extraction.")

                    full_hint = "\n\n".join(hints)

                    # DEBUG LOG
                    logger.warning(f"[DEBUG] Reparsing Msg {m_id} because: {full_hint}")

                    retry_msg["text"] = (
                        retry_msg.get("text", "") + "\n\n" + full_hint
                    )[:3500]
                    reparse_batch.append(retry_msg)

            if reparse_batch:
                try:
                    # CRITICAL: Use batch_size=1 for Refinement to ensure ID safety.
                    # If AI forgets the ID, the Decoder can auto-assign it since there's only 1 valid ID.
                    reparse_batches = [[m] for m in reparse_batch]
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

                        # Replace picks
                        new_picks_by_id = {}
                        for p in new_batch_picks:
                            mid = p.get("message_id")
                            if mid not in new_picks_by_id:
                                new_picks_by_id[mid] = []
                            new_picks_by_id[mid].append(p)

                        for mid, msg_new_picks in new_picks_by_id.items():
                            if msg_new_picks:
                                picks = [
                                    p
                                    for p in picks
                                    if str(p.get("message_id")) != str(mid)
                                ]
                                picks.extend(msg_new_picks)
                                new_picks_count += len(msg_new_picks)

                    logger.info(
                        f"Refinement complete. Replaced with {new_picks_count} refined picks."
                    )
                    picks = backfill_odds(picks)
                    picks = enrich_picks(picks, target_date)
                    picks = deduplicate_by_capper(picks)

                except Exception as e:
                    logger.error(f"Refinement failed: {e}")

        # Final Verification
        if not TwoPassVerifier.verify_parsing_result(picks):
            logger.warning("Low confidence in parsing result structure.")

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
                # CRITICAL: Iterate over ALL messages to show "No Picks Found" cases as requested
                all_msg_ids = sorted(msg_map.keys())

                for mid in all_msg_ids:
                    msg_picks = picks_by_msg.get(mid, [])
                    msg = msg_map.get(mid)

                    f.write(f"---\n\n")
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
                    if msg_picks:
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
                    else:
                        f.write("> *No picks extracted from this message.*\n")

                    f.write("\n")

            logger.info(f"Verification report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to generate verification report: {e}")

        return picks
