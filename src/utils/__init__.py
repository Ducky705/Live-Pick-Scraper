from .message_chunker import MessageChunker

# Copying content from legacy utils directly here because 
# src/utils.py (file) and src/utils/ (folder) conflict.
# By making src/utils a package, we must put the utility functions in __init__.py
# or a submodule exposed here.

import glob
import os
import re
import unicodedata
from collections import Counter

def normalize_string(text: str | None, remove_spaces: bool = False) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if remove_spaces:
        text = text.replace(" ", "")
    return text

def cleanup_temp_images(directory):
    if not os.path.exists(directory):
        return
    files = glob.glob(os.path.join(directory, "*.jpg"))
    if files:
        print(f"[System] Cleaning up {len(files)} old temporary images...")
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Error deleting {f}: {e}")

def detect_common_watermark(messages_ocr_text):
    if not messages_ocr_text:
        return ""
    all_lines = []
    for text in messages_ocr_text:
        lines = [l.strip().lower() for l in text.split("\n") if len(l.strip()) > 3]
        all_lines.extend(lines)
    if not all_lines:
        return ""
    counts = Counter(all_lines)
    detected = []
    for line, count in counts.most_common(10):
        if count > 1 and ("@" in line or "dm" in line or "join" in line):
            detected.append(line)
    return ", ".join(detected[:3])

def filter_text(original_text, watermark_input):
    if not original_text:
        return ""
    terms = [t.strip() for t in watermark_input.split(",") if t.strip()]
    cleaned = original_text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    noise_patterns = [
        r"DM\**\W+\**@cappersfree.*",
        r"@cappers(free|tree).*",
        r"➖➖+",
        r"✅",
        r"Join The BEST Team.*",
        r"Let\'s crush it.*",
        r"EXCLUSIVE PACKAGE.*",
    ]
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    return "\n".join(lines)

def is_ad_content(text):
    if not text:
        return False
    text_upper = text.upper()
    ad_triggers = [
        "HUGE PROMO ALLERT",
        "DAYS FOR THE PRICE OF",
        "EXCLUSIVE PACKAGE",
        "CHEAPEST PRICES",
    ]
    if any(trigger in text_upper for trigger in ad_triggers):
        if not re.search(r"\d", text):
            return True
    return False

def backfill_odds(picks):
    odds_map = {}
    def normalize(s):
        return str(s).lower().replace(" ", "").strip()
    for p in picks:
        p_text = normalize(p.get("pick", ""))
        p_odds = p.get("odds")
        isValidOdds = p_odds is not None and str(p_odds).strip() != "" and str(p_odds).lower() != "none"
        if isValidOdds and p_text:
            if p_text not in odds_map:
                odds_map[p_text] = p_odds
    for p in picks:
        if p.get("capper_name"):
            name = str(p["capper_name"]).strip()
            if len(name) > 3 and name.isupper():
                p["capper_name"] = name.title()
            elif name.lower() == "n/a":
                p["capper_name"] = "Unknown"
            else:
                p["capper_name"] = p["capper_name"]
        else:
            p["capper_name"] = "Unknown"
        if not p.get("league"):
            p["league"] = "Other"
        current_odds = p.get("odds")
        is_missing = current_odds is None or str(current_odds).strip() == "" or str(current_odds).lower() == "none"
        if is_missing:
            p_text = normalize(p.get("pick", ""))
            if p_text in odds_map:
                p["odds"] = odds_map[p_text]
            else:
                p_type = str(p.get("type")).lower()
                if p_type in ["spread", "total", "over", "under"]:
                    p["odds"] = None
                else:
                    p["odds"] = None
        raw_unit = p.get("units")
        if raw_unit is None or str(raw_unit).strip() in ["", "null", "None"]:
            p["units"] = 1.0
        else:
            try:
                clean_str = str(raw_unit).lower().replace("units", "").replace("unit", "").replace("u", "").strip()
                val = float(clean_str)
                p["units"] = 1.0 if val > 25 else val
            except ValueError:
                p["units"] = 1.0
    return picks

def _pick_mentions_team(pick_text, team_name):
    if not team_name or not pick_text:
        return False
    if team_name in pick_text:
        return True
    words = team_name.split()
    if len(words) > 1:
        last_word = words[-1]
        if len(last_word) > 2 and last_word in pick_text:
            return True
    return False

def _extract_appropriate_odds(pick, odds_data):
    pick_text = (pick.get("pick") or "").lower()
    pick_type = (pick.get("type") or "").lower()
    if pick_type == "spread" or re.search(r"[+-]\d+\.?\d*", pick_text):
        home = (odds_data.get("home_team") or "").lower()
        if _pick_mentions_team(pick_text, home):
            return odds_data.get("spread_home_odds")
        return odds_data.get("spread_away_odds")
    if pick_type == "moneyline" or "ml" in pick_text:
        home = (odds_data.get("home_team") or "").lower()
        if _pick_mentions_team(pick_text, home):
            return odds_data.get("moneyline_home")
        return odds_data.get("moneyline_away")
    if pick_type == "total" or "over" in pick_text or "under" in pick_text:
        if "over" in pick_text:
            return odds_data.get("over_odds")
        return odds_data.get("under_odds")
    return odds_data.get("moneyline_home") or odds_data.get("moneyline_away")

def smart_backfill_odds(picks, target_date):
    import logging
    logger = logging.getLogger(__name__)
    picks = backfill_odds(picks)
    missing_odds_picks = []
    leagues_needed = set()
    for p in picks:
        current_odds = p.get("odds")
        is_missing = current_odds is None or str(current_odds).strip() == "" or str(current_odds).lower() == "none"
        if is_missing:
            league = (p.get("league") or p.get("lg") or "").lower()
            if league and league != "other":
                missing_odds_picks.append(p)
                leagues_needed.add(league)
    if not missing_odds_picks:
        logger.debug("All picks have odds, no ESPN fetch needed")
        return picks
    logger.info(f"Fetching ESPN odds for {len(leagues_needed)} leagues: {', '.join(sorted(leagues_needed))}")
    try:
        from src.score_cache import get_cache
        from src.score_fetcher import fetch_odds_for_leagues
        cache = get_cache()
        import datetime
        if "-" in target_date:
            d = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        else:
            d = datetime.datetime.strptime(target_date, "%m/%d/%Y")
        api_date = d.strftime("%Y%m%d")
        all_odds = {}
        leagues_to_fetch = []
        for league in leagues_needed:
            cached_odds = cache.get_odds(api_date, league)
            if cached_odds:
                all_odds.update(cached_odds)
            else:
                leagues_to_fetch.append(league)
        if leagues_to_fetch:
            fetched_odds = fetch_odds_for_leagues(target_date, leagues_to_fetch)
            all_odds.update(fetched_odds)
            for league in leagues_to_fetch:
                league_odds = {k: v for k, v in fetched_odds.items() if k.startswith(f"{league}:")}
                if league_odds:
                    cache.set_odds(api_date, league, league_odds)
        matched_count = 0
        for p in missing_odds_picks:
            pick_text = (p.get("pick") or "").lower()
            league = (p.get("league") or p.get("lg") or "").lower()
            for game_key, odds_data in all_odds.items():
                if not game_key.startswith(f"{league}:"):
                    continue
                home = (odds_data.get("home_team") or "").lower()
                away = (odds_data.get("away_team") or "").lower()
                if _pick_mentions_team(pick_text, home) or _pick_mentions_team(pick_text, away):
                    p["odds"] = _extract_appropriate_odds(p, odds_data)
                    if p["odds"]:
                        matched_count += 1
                    break
        logger.info(f"Backfilled odds for {matched_count}/{len(missing_odds_picks)} picks from ESPN")
    except Exception as e:
        logger.warning(f"Smart odds backfill failed: {e}")
    return picks

def clean_text_for_ai(text):
    if not text:
        return ""
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"(?i)(gambling\sproblem|1-800-\d{3}-\d{4}|call\s*1-800).*", "", text)
    text = re.sub(r"[-=_]{3,}", " ", text)
    text = re.sub(r"(?i)(join\s*us|subscribe|link\s*in\s*bio|click\s*here|t\.me\/).*", "", text)
    watermarks = [
        r"@?cappersfree",
        r"@?capperstree",
        r"@?cappers_free",
        r"@?freecappers",
        r"@?vippicks",
        r"@?freepicks",
        r"@?sportsbetting",
        r"DM\s*@\w+",
        r"\bDK\b(?![a-z])",
        r"\bFD\b(?![a-z])",
        r"\bMGM\b",
    ]
    for wm in watermarks:
        text = re.sub(wm, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("½", ".5")
    text = text.replace("1/2", ".5")
    text = text.replace("||", " / ")
    return text[:5000]

def auto_group_parlays(picks, message_context):
    if not picks or not message_context:
        return picks
    picks_by_id = {}
    other_picks = []
    for p in picks:
        mid = p.get("message_id")
        if mid:
            try:
                mid_int = int(mid)
                if mid_int not in picks_by_id:
                    picks_by_id[mid_int] = []
                picks_by_id[mid_int].append(p)
            except (ValueError, TypeError):
                other_picks.append(p)
        else:
            other_picks.append(p)
    final_picks = []
    final_picks.extend(other_picks)
    for mid, msg_picks in picks_by_id.items():
        context = message_context.get(mid, "").upper()
        is_parlay_text = "PARLAY" in context or "BUILDER" in context
        candidates = []
        for p in msg_picks:
            p_type = str(p.get("type")).lower()
            p_pick = str(p.get("pick", ""))
            if p_type == "parlay" and ("/" in p_pick or " + " in p_pick):
                continue
            if p_type == "unknown":
                continue
            candidates.append(p)
        existing_parlays = [
            p for p in msg_picks
            if str(p.get("type")).lower() == "parlay" and ("/" in p.get("pick", "") or " + " in p.get("pick", ""))
        ]
        unknowns = [p for p in msg_picks if str(p.get("type")).lower() in ["unknown"]]
        if is_parlay_text and len(candidates) > 1:
            merged_pick_text = " / ".join([str(p.get("pick", "")) for p in candidates])
            base = candidates[0]
            new_pick = {
                "message_id": mid,
                "pick": merged_pick_text,
                "type": "Parlay",
                "odds": None,
                "units": base.get("units", 1.0),
                "league": base.get("league", "Other"),
                "capper_name": base.get("capper_name", "Unknown"),
                "confidence": 0.9,
                "reasoning": "Auto-grouped based on Parlay keyword in text.",
                "_source_text": base.get("_source_text", ""),
            }
            final_picks.append(new_pick)
            final_picks.extend(existing_parlays)
            final_picks.extend(unknowns)
        else:
            final_picks.extend(msg_picks)
    return final_picks

def safe_write_progress(content: str, filename: str = "progress.md"):
    temp_filename = f"{filename}.tmp"
    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_filename, filename)
    except Exception as e:
        print(f"Failed to write progress: {e}")

def clean_sauce_text(text: str) -> str:
    if not text:
        return ""
    import re
    pattern = r'\b(Sauce|DirtybubbleBets|Bankrollbill|Pardonmypick|BulliesPicks|MRBIGBETS|MrBigBets|Analyticscapper|Alternate Line|LADDER CHALLENGE|MAX PLAY|EXCLUSIVE|Official Play|WHALEPLAY|Glitch Whale)\b'
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+\s+TO\s+[\d,]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\(\d+/\d+\)', '', cleaned)
    cleaned = re.sub(r'PLAY\s*#\d+:?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
