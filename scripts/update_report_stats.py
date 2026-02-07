
import sys
import os
import re
import json
from collections import Counter
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.grading.parser import PickParser
from src.grading.engine import GraderEngine
from src.grading.schema import GradeResult, BetType

from src.grading.ai_resolver import AIResolver

# DISABLE AI for speed
AIResolver.resolve_pick = lambda text, league, scores: None

REPORT_PATH = "src/data/output/dry_run_analysis_2026-02-05.md"
FIXTURE_PATH = "tests/fixtures/goldenset_scores.json"

def main():
    print(f"Updating report: {REPORT_PATH}")
    
    # 1. Load Scores
    with open(FIXTURE_PATH) as f:
        scores = json.load(f)
    print(f"Loaded {len(scores)} scores from fixture.")
    
    engine = GraderEngine(scores)
    
    # 2. Read Report
    with open(REPORT_PATH, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    in_table = False
    table_header_idx = -1
    
    stats = Counter()
    gradable_count = 0
    
    # Regex to capture table row
    # | Capper | League | Pick | Odds | Grade | Summary |
    # We care about index 2 (Pick), 4 (Grade), 5 (Summary), 1 (League)
    
    for i, line in enumerate(lines):
        if "| Capper | League | Pick |" in line:
            in_table = True
            table_header_idx = i
            new_lines.append(line)
            continue
            
        if in_table and line.strip().startswith("|") and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            # parts[0] is empty (before first |)
            # parts[1] = Capper, parts[2] = League, parts[3] = Pick, etc.
            
            if len(parts) >= 7:
                league = parts[2]
                pick_text = parts[3]
                odds_str = parts[4]
                # grade_str = parts[5] 
                
                # Re-grade
                try:
                    # Clean markdown bolding if present in pick text (e.g. ** **)
                    clean_pick = pick_text.replace("**", "").strip()
                    parsed = PickParser.parse(clean_pick)
                    graded = engine.grade(parsed)
                    
                    # Update League if Parser detected newly (e.g. 1Q -> NBA)
                    if parsed.league and parsed.league != "UNKNOWN" and parsed.league != "OTHER":
                         league = parsed.league
                    
                    # Determine Grade String
                    grade_icon = ""
                    if graded.grade == GradeResult.WIN:
                        grade_icon = "✅ WIN"
                        stats["WIN"] += 1
                        gradable_count += 1
                    elif graded.grade == GradeResult.LOSS:
                        grade_icon = "❌ LOSS"
                        stats["LOSS"] += 1
                        gradable_count += 1
                    elif graded.grade == GradeResult.PUSH:
                        grade_icon = "➖ PUSH"
                        stats["PUSH"] += 1
                        gradable_count += 1
                    elif graded.grade == GradeResult.VOID:
                        grade_icon = "VOID"
                        stats["VOID"] += 1
                        gradable_count += 1
                    else:
                        grade_icon = "PENDING"
                        stats["PENDING"] += 1
                        # Pending is technically not "Graded" in terms of accuracy denominator usually?
                        # Or per existing report "Gradable Picks" implies those that *can* be graded?
                        # User's stats: 608 picks, 366 gradable. 
                        # 167+199 = 366. So PENDING are NOT gradable.
                        
                    summary = graded.score_summary if graded.score_summary else ""
                    
                    # Reconstruct Line
                    # | Capper | League | Pick | Odds | Grade | Summary |
                    new_line = f"| {parts[1]} | {league} | {pick_text} | {odds_str} | {grade_icon} | {summary} |\n"
                    new_lines.append(new_line)
                    
                except Exception as e:
                    print(f"Error grading {pick_text}: {e}")
                    new_lines.append(line) # Keep original if error
            else:
                new_lines.append(line)
        else:
            # Check if we just exited table
            if in_table and not line.strip().startswith("|"):
                in_table = False
            new_lines.append(line)

    # 3. Update Statistics in Header
    # Need to replace the sections in new_lines
    # Logic: iterate new_lines, replace regex matches for counters
    
    # Calculate Accuracy: Win / (Win + Loss)
    total_decided = stats["WIN"] + stats["LOSS"]
    accuracy = (stats["WIN"] / total_decided * 100) if total_decided > 0 else 0.0
    
    print("New Stats:", stats)
    print(f"Accuracy: {accuracy:.2f}%")
    
    final_output = []
    skip_stats = False
    
    for line in new_lines:
        if "**Gradable Picks:**" in line:
            final_output.append(f"- **Gradable Picks:** {total_decided}\n")
        elif "**Accuracy:**" in line:
            final_output.append(f"- **Accuracy:** {accuracy:.2f}%\n")
        elif "## 2. Grading Statistics" in line:
            final_output.append(line)
            skip_stats = True
            # Construct new stats table immediately
            final_output.append("| Grade | Count |\n")
            final_output.append("| :--- | :---: |\n")
            final_output.append(f"| WIN | {stats['WIN']} |\n")
            final_output.append(f"| LOSS | {stats['LOSS']} |\n")
            final_output.append(f"| PUSH | {stats['PUSH']} |\n")
            final_output.append(f"| VOID | {stats['VOID']} |\n")
            final_output.append(f"| PENDING | {stats['PENDING']} |\n")
            final_output.append(f"| ERROR | {stats['ERROR']} |\n")
        elif skip_stats:
            # Skip old table lines until we hit a blank line or new header
            if not line.strip().startswith("|") and line.strip() != "":
                skip_stats = False
                final_output.append(line)
        else:
            final_output.append(line)

    with open(REPORT_PATH, "w") as f:
        f.writelines(final_output)
    
    print("Report updated.")

if __name__ == "__main__":
    main()
