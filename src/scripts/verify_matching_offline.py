
import json
import logging
import os
from datetime import datetime

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("offline_verifier")

# --- MOCKING / UTILS ---

def normalize_string(s):
    """Normalize string for matching."""
    if not s:
        return ""
    return str(s).strip().lower()

# Try to import rapidfuzz, fallback to difflib
try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
    logger.info("Using rapidfuzz for matching.")
except ImportError:
    HAS_RAPIDFUZZ = False
    import difflib
    logger.warning("rapidfuzz not found. Using difflib (slower/less accurate).")

# --- MATCHING LOGIC (Copied & Adapted from capper_matcher.py) ---

AUTO_MATCH_THRESHOLD = 95
AI_VERIFY_THRESHOLD = 80

def smart_match(raw_name, candidates):
    """
    Offline version of smart_match.
    Skips AI verification and assumes 'No' for ambiguous cases to be safe.
    """
    if not raw_name or not candidates:
        return None

    clean_raw = normalize_string(raw_name)

    # 1. Exact Match
    for c in candidates:
        if normalize_string(c["name"]) == clean_raw:
            return {
                "name": c["name"],
                "id": c["id"],
                "score": 100,
                "type": "exact",
                "reason": "Exact string match"
            }

    # 2. Fuzzy Match
    choices = [c["name"] for c in candidates]

    best_candidate = None
    score = 0

    if HAS_RAPIDFUZZ:
        match = process.extractOne(clean_raw, choices, scorer=fuzz.WRatio, score_cutoff=AI_VERIFY_THRESHOLD)
        if match:
            matched_name, s, _ = match
            score = s
            # Find candidate obj
            for c in candidates:
                if c["name"] == matched_name:
                    best_candidate = c
                    break
    else:
        # Difflib fallback
        matches = difflib.get_close_matches(clean_raw, choices, n=1, cutoff=AI_VERIFY_THRESHOLD/100.0)
        if matches:
            matched_name = matches[0]
            # Calculate a rough score
            s = difflib.SequenceMatcher(None, clean_raw, normalize_string(matched_name)).ratio() * 100
            score = s
            for c in candidates:
                if c["name"] == matched_name:
                    best_candidate = c
                    break

    if not best_candidate:
        return None

    if score >= AUTO_MATCH_THRESHOLD:
        return {
            "name": best_candidate["name"],
            "id": best_candidate["id"],
            "score": score,
            "type": "fuzzy_auto",
            "reason": f"High confidence fuzzy match ({score:.1f})"
        }

    # 3. Ambiguous (would trigger AI)
    # in offline mode, we treat this as "Potential Match" but return None to simulate "New Capper"
    # OR we can flag it.
    logger.info(f"[Offline] Ambiguous matche skipped (would ask AI): {raw_name} ~ {best_candidate['name']} ({score:.1f})")
    return None

# --- MAIN EXECUTION ---

def main():
    print("Starting Offline Capper Matching Verification...")

    # 1. Load Picks
    picks_file = "src/data/output/picks_2026-02-14_raw.json" # Adjust path if needed
    if not os.path.exists(picks_file):
        print(f"Error: Picks file not found: {picks_file}")
        # Try finding any picks file
        import glob
        files = glob.glob("src/data/output/picks_*.json")
        if files:
            picks_file = files[0]
            print(f"Found alternative picks file: {picks_file}")
        else:
            return

    try:
        with open(picks_file) as f:
            picks_data = json.load(f)
            # Handle different formats (list of dicts or dict with 'picks' key)
            if isinstance(picks_data, dict):
                picks = picks_data.get("picks", [])
            else:
                picks = picks_data

            print(f"Loaded {len(picks)} picks from {picks_file}")
    except Exception as e:
        print(f"Failed to load picks: {e}")
        return

    # 2. Mock Candidates (Since we can't connect to DB)
    # We create a list of likely cappers based on common names found in data
    # In a real scenario, this would come from `get_matcher_candidates()`
    candidates = [
        {"name": "Don Best", "id": 1, "is_active": True},
        {"name": "Dr. Bob", "id": 2, "is_active": True},
        {"name": "Right Angle Sports", "id": 3, "is_active": True},
        {"name": "RAS", "id": 3, "is_active": True, "type": "variant"}, # RAS = Right Angle Sports
        {"name": "Marco D'Angelo", "id": 4, "is_active": True},
        {"name": "Vegas Dave", "id": 5, "is_active": False},
        {"name": "Sharp Rank", "id": 6, "is_active": True},
        # Add some random ones to test non-matches
        {"name": "Existing Capper A", "id": 100, "is_active": True},
        {"name": "Existing Capper B", "id": 101, "is_active": True},
    ]
    print(f"Loaded {len(candidates)} mock candidates for matching.")

    # 3. Process
    results = {
        "matched": 0,
        "new_capper": 0,
        "details": []
    }

    print("\n--- Matching Results ---")
    for p in picks:
        raw_name = p.get("capper_name")
        if not raw_name:
            continue

        match = smart_match(raw_name, candidates)

        status = "MATCHED" if match else "NEW_CAPPER"

        if status == "MATCHED":
            results["matched"] += 1
            log_str = f"[MATCH] '{raw_name}' -> '{match['name']}' ({match['score']:.1f}%)"
        else:
            results["new_capper"] += 1
            log_str = f"[NEW]   '{raw_name}' (No match found)"

        print(log_str)

        results["details"].append({
            "raw": raw_name,
            "status": status,
            "match": match
        })

    # 4. Save Report
    report_file = "src/data/output/offline_verification_report.md"
    with open(report_file, "w") as f:
        f.write("# Offline Capper Matching Verification\n\n")
        f.write(f"**Date:** {datetime.now()}\n")
        f.write(f"**Picks Processed:** {len(picks)}\n")
        f.write(f"**Matched:** {results['matched']}\n")
        f.write(f"**New Cappers:** {results['new_capper']}\n\n")
        f.write("## Detailed Log\n\n")
        f.write("| Raw Name | Status | Matched Candidate | Score |\n")
        f.write("|---|---|---|---|\n")
        for item in results["details"]:
            m = item["match"]
            m_name = m["name"] if m else "-"
            m_score = f"{m['score']:.1f}" if m else "-"
            f.write(f"| {item['raw']} | {item['status']} | {m_name} | {m_score} |\n")

    print(f"\nReport saved to {report_file}")

if __name__ == "__main__":
    main()
