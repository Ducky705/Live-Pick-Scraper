
import logging
from collections import Counter
from typing import Any

from src.parallel_batch_processor import parallel_processor
from src.prompts.decoder import normalize_response
from src.schedule_manager import ScheduleManager
from src.style_gallery import StyleGallery

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """
    Autonomous Consensus Engine (Proposal 3).
    Queries a "Council" of models in parallel and applies majority voting
    to resolve low-confidence or ambiguous picks.
    """

    COUNCIL_MEMBERS = ["groq", "mistral", "cerebras"]  # The Voting Council
    CONSENSUS_THRESHOLD = 2  # Majority rule (2/3)

    @staticmethod
    def run_consensus(
        messages: list[dict[str, Any]],
        target_date: str | None = None,
        batch_size: int = 5
    ) -> list[dict[str, Any]]:
        """
        Run consensus on a set of flagged messages.
        
        Args:
            messages: List of message dicts to process.
            target_date: Target date for schedule context.
            batch_size: Size of batches (smaller for consensus).
            
        Returns:
            List of refined picks receiving majority consensus.
        """
        if not messages:
            return []

        logger.info(f"ConsensusEngine: Convening Council for {len(messages)} messages...")

        # 0. Fetch contexts
        schedule_context = None
        if target_date:
            schedule_context = ScheduleManager.get_context_string(target_date)

        # 1. Group by Capper for Style Injection
        capper_groups = {}
        for msg in messages:
            capper = msg.get("channel_name", "Unknown")
            if capper not in capper_groups:
                capper_groups[capper] = []
            capper_groups[capper].append(msg)

        # 2. Prepare Batches with Context
        batches = []
        for capper, inputs in capper_groups.items():
            # Retrieve style context
            examples = StyleGallery.get_examples(capper)
            formatted_examples = StyleGallery.format_examples_for_prompt(examples)

            style_context_dict = {}
            if formatted_examples:
                style_context_dict["style_context"] = formatted_examples

            for i in range(0, len(inputs), batch_size):
                batch = inputs[i : i + batch_size]
                batches.append((batch, style_context_dict))

        # 3. Query Council Members in Parallel
        council_results = {}  # {provider: [results...]}

        for member in ConsensusEngine.COUNCIL_MEMBERS:
            try:
                # Enforce single provider via allowed_providers
                results = parallel_processor.process_batches(
                    batches,
                    allowed_providers=[member],
                    schedule_context=schedule_context
                )
                council_results[member] = results
            except Exception as e:
                logger.error(f"ConsensusEngine: Member {member} failed to vote: {e}")
                council_results[member] = [None] * len(batches)

        # 4. Aggregate and Vote
        refined_picks = []
        message_votes: dict[str, list[dict[str, Any]]] = {}

        # Flatten results: map message_id -> list of picks from different providers
        for member, batch_results in council_results.items():
            for i, raw_response in enumerate(batch_results):
                if not raw_response:
                    continue

                # Retrieve corresponding batch messages
                current_batch, _ = batches[i]
                valid_ids = [str(m.get("id")) for m in current_batch if m.get("id")]

                # Context for validation (if needed by normalize, current usage only needs ids)
                # But normalize_response handles the parsing
                try:
                    parsed_picks = normalize_response(
                        raw_response,
                        valid_message_ids=valid_ids,
                        expand=True
                    )

                    for pick in parsed_picks:
                        mid = str(pick.get("message_id"))
                        if mid not in message_votes:
                            message_votes[mid] = []

                        # Tag potential vote with provider
                        pick["_voter"] = member
                        message_votes[mid].append(pick)

                except Exception as e:
                    logger.warning(f"Failed to parse votes from {member} batch {i}: {e}")

        # 5. Strict Majority Vote
        # Count effective voters per message
        # Determine how many providers successfully returned a result for the batch containing this message
        # This is tricky because `council_results` is batch-based.

        # Mapping: Batch Index -> Active Voters Count
        batch_active_voters = {}
        for i in range(len(batches)):
            count = 0
            for member in ConsensusEngine.COUNCIL_MEMBERS:
                # Check if member returned a valid response for this batch
                res_list = council_results.get(member, [])
                if i < len(res_list) and res_list[i] is not None:
                    count += 1
            batch_active_voters[i] = count

        # Process votes
        for mid, votes in message_votes.items():
            # Find which batch this message belongs to
            # We need to map MID -> Batch Index
            # Inefficient search:
            batch_idx = 0
            found = False
            for idx, (batch, _) in enumerate(batches):
                for m in batch:
                    if str(m.get("id")) == mid:
                        batch_idx = idx
                        found = True
                        break
                if found:
                    break

            active_count = batch_active_voters.get(batch_idx, 0)

            consensus_picks = ConsensusEngine._tally_votes(votes, active_count)
            if consensus_picks:
                refined_picks.extend(consensus_picks)
            else:
                logger.info(f"Message {mid}: No consensus reached (Active Voters: {active_count}). Auto-discarding.")

        logger.info(f"ConsensusEngine: Approved {len(refined_picks)} picks via majority vote.")
        return refined_picks

    @staticmethod
    def _tally_votes(votes: list[dict[str, Any]], active_voters: int) -> list[dict[str, Any]]:
        """
        Determines if there is a majority consensus with hierarchical grouping.
        1. Exact Match (Team + Type)
        2. Team Match (Team only) - for Spread/ML mismatches
        """
        if not votes:
            return []

        threshold = 2
        # If fewer than 2 voters active (e.g. only 1 provider working), threshold is 1
        if active_voters < 2:
            threshold = 1

        # --- Normalization Helpers ---
        def normalize_team(t):
            t = (t or "").lower().strip()
            # Remove specific suffixes/prefixes
            t = t.replace("team total", "").strip()
            t = t.replace("1h", "").replace("2h", "").strip()
            # Remove common abbreviations or noise
            t = t.replace("the ", "").replace("fc", "").strip()
            return t

        def normalize_type(t):
            t = (t or "").lower().strip()
            if "spread" in t or "handicap" in t: return "spread"
            if "moneyline" in t or "ml" in t: return "moneyline"
            if "total" in t or "over" in t or "under" in t: return "total"
            if "prop" in t: return "prop"
            if "parlay" in t: return "parlay"
            if "period" in t: return "period"
            return t

        # Clean votes first
        cleaned_votes = []
        for pick in votes:
            p_copy = pick.copy()
            p_copy["_norm_team"] = normalize_team(pick.get("team"))
            p_copy["_norm_type"] = normalize_type(pick.get("type"))
            cleaned_votes.append(p_copy)

        accepted_picks = []

        # --- Strategy 1: Strict (Team + Type) ---
        grouped_strict = {}
        for p in cleaned_votes:
            key = (p["_norm_team"], p["_norm_type"])
            if key not in grouped_strict:
                grouped_strict[key] = []
            grouped_strict[key].append(p)

        # Track which teams/picks have been accepted to avoid duplicates
        accepted_keys = set()

        for (team, wager_type), group in grouped_strict.items():
            unique_voters = {p.get("_voter") for p in group if "_voter" in p}
            if len(unique_voters) >= threshold:
                # Success!
                accepted_keys.add(team)

                # Determine final line/odds via Mode
                lines = [p.get("line") for p in group]
                odds_list = [p.get("odds") for p in group]
                final_line = Counter(lines).most_common(1)[0][0]
                final_odds = Counter(odds_list).most_common(1)[0][0]

                best_pick = group[0].copy()
                best_pick["line"] = final_line
                best_pick["odds"] = final_odds

                # Remove debug keys
                for k in ["_norm_team", "_norm_type", "_voter"]:
                    best_pick.pop(k, None)

                accepted_picks.append(best_pick)
            else:
                 # Log strict rejection
                 print(f"DEBUG: Strict Consensus Failed: {team} {wager_type} | Voters: {len(unique_voters)}/{threshold}")

        # --- Strategy 2: Relaxed (Team Only) ---
        # Useful when one provider says "Spread" and another "Moneyline" for the same team
        grouped_relaxed = {}
        for p in cleaned_votes:
            team = p["_norm_team"]
            if team in accepted_keys:
                continue # Already accepted strict match for this team

            # Don't relax for Player Props (names are unique enough usually, but type matters)
            if p["_norm_type"] == "prop":
                continue

            if team not in grouped_relaxed:
                grouped_relaxed[team] = []
            grouped_relaxed[team].append(p)

        for team, group in grouped_relaxed.items():
            unique_voters = {p.get("_voter") for p in group if "_voter" in p}
            if len(unique_voters) >= threshold:
                # We have consensus on the TEAM, but disagreed on Type
                print(f"DEBUG: Relaxed Consensus Found for Team: {team} | Voters: {len(unique_voters)}")

                # Vote on best Type within this team-group
                types = [p["_norm_type"] for p in group]
                # Preferences: Spread > Moneyline > Total > Other
                # Just take commonest for now
                common_type = Counter(types).most_common(1)[0][0]

                # Filter group to only matches of this common type (or compatible?)
                # Actually, pick the specific pick that aligns with the chosen type
                chosen_subgroup = [p for p in group if p["_norm_type"] == common_type]

                # If chosen subgroup doesn't cover threshold, we might be forcing a type from 1 provider
                # But we ESTABLISHED consensus on the TEAM. So we trust the Team exists.
                # We interpret the disagreement as ambiguity in classification.
                # We accept the most likely classification.

                if not chosen_subgroup:
                    chosen_subgroup = group # Fallback

                best_pick = chosen_subgroup[0].copy()

                # Clean keys
                for k in ["_norm_team", "_norm_type", "_voter"]:
                    best_pick.pop(k, None)

                accepted_picks.append(best_pick)
            elif group:
                print(f"DEBUG: Relaxed Consensus Rejected: {team} | Voters: {len(unique_voters)}/{threshold}")
                for p in group:
                    print(f"   -> Voter: {p.get('_voter')} | Pick: {p.get('pick')}")

        return accepted_picks
