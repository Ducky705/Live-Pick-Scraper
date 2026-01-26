import logging
import re
from typing import List, Dict, Optional, Tuple
import difflib

from src.models import BetPick
from src.score_fetcher import fetch_scores_for_date, fetch_odds_for_date

logger = logging.getLogger("EnrichmentEngine")


class EnrichmentEngine:
    def __init__(self):
        # Cache for game data to avoid re-fetching within same batch
        self._games_cache = {}
        self._odds_cache = {}

    def enrich_picks(self, picks: List[BetPick]) -> List[BetPick]:
        """
        Main entry point. Enriches a list of picks with opponent, league, and odds data.
        """
        if not picks:
            return []

        # Group picks by date to minimize API calls
        picks_by_date = {}
        for p in picks:
            date_key = (
                p.date.split()[0] if p.date else "today"
            )  # simplistic date handling
            if date_key not in picks_by_date:
                picks_by_date[date_key] = []
            picks_by_date[date_key].append(p)

        enriched_picks = []
        for date_str, date_picks in picks_by_date.items():
            # 1. Fetch Context (Schedule & Odds)
            schedule = self._get_schedule(date_str)
            odds_data = self._get_odds(date_str)

            for pick in date_picks:
                try:
                    self._enrich_single_pick(pick, schedule, odds_data)
                except Exception as e:
                    logger.warning(f"Failed to enrich pick {pick.pick}: {e}")
                enriched_picks.append(pick)

        return enriched_picks

    def _get_schedule(self, date_str: str) -> List[Dict]:
        """Fetch games from ESPN via score_fetcher"""
        if date_str in self._games_cache:
            return self._games_cache[date_str]

        # We fetch ALL leagues to maximize matching chances
        games = fetch_scores_for_date(date_str, force_refresh=False, final_only=False)
        self._games_cache[date_str] = games
        return games

    def _get_odds(self, date_str: str) -> Dict:
        """Fetch odds from ESPN via score_fetcher"""
        if date_str in self._odds_cache:
            return self._odds_cache[date_str]

        odds = fetch_odds_for_date(date_str)
        self._odds_cache[date_str] = odds
        return odds

    def _enrich_single_pick(self, pick: BetPick, schedule: List[Dict], odds_data: Dict):
        """
        Core logic: Match pick to game -> Fill blanks -> Rewrite pick string.
        """
        # 1. Identify Team/Participant in the pick text
        # If "vs" is already present, we might skip, but let's verify context anyway

        matched_game = self._find_matching_game(pick, schedule)

        if matched_game:
            # 2. Enrich Metadata
            if pick.league == "Unknown" or pick.league == "Other":
                pick.league = matched_game["league"].upper()

            # Identify which team was picked
            team1 = matched_game["team1"]
            team2 = matched_game["team2"]

            # Determine extracted team from pick text
            picked_team = self._identify_team_in_text(pick.pick, team1, team2)
            opponent = team2 if picked_team == team1 else team1

            if picked_team:
                pick.opponent = opponent

                # 3. Rewrite Pick String (Normalization)
                # Rule: Totals MUST be "Team A vs Team B Over/Under X"
                if (
                    pick.type in ["Total", "TL"]
                    or "Over" in pick.pick
                    or "Under" in pick.pick
                ):
                    # Check if "vs" format is missing
                    if " vs " not in pick.pick:
                        # Construct proper Total string
                        # Preserve the line/side (e.g. "Under 163")
                        side_line = self._extract_side_line(pick.pick)
                        if side_line:
                            pick.pick = f"{picked_team} vs {opponent} {side_line}"
                            logger.info(f"Rewrote Total: {pick.pick}")

                # 4. Backfill Odds (only if missing)
                if pick.odds is None and odds_data:
                    self._backfill_odds(pick, matched_game, odds_data, picked_team)

    def _find_matching_game(
        self, pick: BetPick, schedule: List[Dict]
    ) -> Optional[Dict]:
        """Fuzzy match pick text against scheduled games"""
        # Quick filter by league if known
        candidates = schedule
        if pick.league and pick.league not in ["Unknown", "Other"]:
            candidates = [
                g for g in schedule if g["league"].lower() == pick.league.lower()
            ]

        best_match = None
        best_score = 0

        # Normalize pick text (e.g. St -> State)
        pick_text_norm = self._normalize_team_name(pick.pick.lower())

        for game in candidates:
            t1 = game.get("team1", "").lower()
            t2 = game.get("team2", "").lower()

            if not t1 or not t2:
                continue

            # Score match
            score = 0
            if t1 in pick_text_norm:
                score = 1.0
            elif t2 in pick_text_norm:
                score = 1.0
            else:
                # Partial match (e.g. "Okla St")
                # Using rapidfuzz or difflib here would be better but keeping it fast/simple first
                s1 = difflib.SequenceMatcher(
                    None, t1, pick_text_norm
                ).find_longest_match(0, len(t1), 0, len(pick_text_norm)).size / len(t1)
                s2 = difflib.SequenceMatcher(
                    None, t2, pick_text_norm
                ).find_longest_match(0, len(t2), 0, len(pick_text_norm)).size / len(t2)

                # Boost if words match
                if self._word_overlap_score(t1, pick_text_norm) > 0.8:
                    s1 += 0.2
                if self._word_overlap_score(t2, pick_text_norm) > 0.8:
                    s2 += 0.2

                score = max(s1, s2)

            if score > best_score and score > 0.6:  # Threshold
                best_score = score
                best_match = game

        return best_match

    def _normalize_team_name(self, text: str) -> str:
        """Expand common abbreviations for better matching"""
        replacements = {
            " st ": " state ",
            " st.": " state",
            " fla ": " florida ",
            " wash ": " washington ",
            " mich ": " michigan ",
            " minn ": " minnesota ",
            " ten ": " tennessee ",
            " az ": " arizona ",
            " hou ": " houston ",
            " phi ": " philadelphia ",
        }
        text = " " + text + " "  # Padding for boundary matching
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.strip()

    def _word_overlap_score(self, team_name: str, pick_text: str) -> float:
        """Calculate overlap of significant words"""
        ignore = {"the", "state", "university", "of", "tech", "a&m"}
        t_words = set(w for w in team_name.split() if w not in ignore and len(w) > 2)
        p_words = set(w for w in pick_text.split() if w not in ignore and len(w) > 2)

        if not t_words:
            return 0.0

        overlap = len(t_words.intersection(p_words))
        return overlap / len(t_words)

    def _identify_team_in_text(
        self, text: str, team1: str, team2: str
    ) -> Optional[str]:
        """Which of the two teams is mentioned in the text?"""
        text_lower = text.lower()

        # Simple containment check first
        if team1.lower() in text_lower:
            return team1
        if team2.lower() in text_lower:
            return team2

        # Word overlap check
        t1_parts = set(team1.lower().split())
        t2_parts = set(team2.lower().split())
        text_parts = set(text_lower.split())

        overlap1 = len(t1_parts.intersection(text_parts))
        overlap2 = len(t2_parts.intersection(text_parts))

        if overlap1 > overlap2:
            return team1
        if overlap2 > overlap1:
            return team2

        return None  # Ambiguous

    def _extract_side_line(self, text: str) -> str:
        """Extract 'Over 163.5' or 'Under 45' from text"""
        match = re.search(r"(Over|Under|O|U)\s*\d+\.?\d*", text, re.IGNORECASE)
        if match:
            s = match.group(0)
            # Normalize to full word
            s = s.replace("O ", "Over ").replace("U ", "Under ")
            if s.lower() == "o":
                s = "Over"  # Edge case
            return s
        return ""

    def _backfill_odds(
        self, pick: BetPick, game: Dict, odds_data: Dict, picked_team: str
    ):
        """Find odds for the specific game and market"""
        # Generate the odds key format used in fetch_odds_for_date
        # "league:event_id:comp_id" - wait, fetch_odds returns keys, but we have game['id']

        # Filter odds_data for matches with this game ID
        game_id = game.get("id")
        matched_odds = None

        for key, val in odds_data.items():
            if f":{game_id}:" in key or key.endswith(f":{game_id}"):
                matched_odds = val
                break

        if not matched_odds:
            return

        # Extract based on type
        # 1. Total
        if "Over" in pick.pick or "Under" in pick.pick:
            # We want the PRICE (odds), e.g. -110
            # Usually totals are -110 unless specified
            is_over = "Over" in pick.pick
            pick.odds = matched_odds.get("over_odds" if is_over else "under_odds")

        # 2. Spread
        elif "-" in pick.pick or "+" in pick.pick:
            is_home = picked_team == matched_odds.get("home_team")
            pick.odds = matched_odds.get(
                "spread_home_odds" if is_home else "spread_away_odds"
            )

        # 3. Moneyline
        elif "ML" in pick.pick:
            is_home = picked_team == matched_odds.get("home_team")
            pick.odds = matched_odds.get(
                "moneyline_home" if is_home else "moneyline_away"
            )

        if pick.odds is not None:
            logger.info(f"Backfilled odds for {pick.pick}: {pick.odds}")
