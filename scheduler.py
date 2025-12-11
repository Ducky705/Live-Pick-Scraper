import datetime
import os
import re

# ==============================================================================
# 🧠 THE BRAIN: SEASONAL LOGIC
# ==============================================================================
def get_optimized_schedule():
    today = datetime.date.today()
    month = today.month

    # ------------------------------------------------------------------
    # SEASON 1: THE "FULL SEND" (September - January)
    # Active: NFL, NCAAF, NBA, NHL, CBB
    # Strategy: Heavy Weekend Mornings (Football) + Heavy Daily Evenings
    # ------------------------------------------------------------------
    if month in [9, 10, 11, 12, 1]:
        print(f"📅 Month {month}: Detected FOOTBALL/WINTER Season. Loading Max Schedule.")
        return [
            "- cron: '0 14-23,0-4 * * *'",       # Baseline: Hourly 10am-12am ET
            "- cron: '15,30,45 21-23 * * 1-5'",  # Weekdays: Every 15m 5pm-8pm ET (NBA/NHL/MNF)
            "- cron: '15,30,45 15-20 * * 0,6'"   # Weekends: Every 15m 11am-4pm ET (NFL/NCAAF Kickoffs)
        ]

    # ------------------------------------------------------------------
    # SEASON 2: MARCH MADNESS (March)
    # Active: NCAA Tournament, NBA, NHL
    # Strategy: Heavy All Day on Weekends
    # ------------------------------------------------------------------
    elif month == 3:
        print(f"📅 Month {month}: Detected MARCH MADNESS. Loading Tournament Schedule.")
        return [
            "- cron: '0 14-23,0-4 * * *'",       # Baseline: Hourly
            "- cron: '15,30,45 16-23 * * 4-7'"   # Thu-Sun: Every 15m 12pm-7pm ET (Tournament Games)
        ]

    # ------------------------------------------------------------------
    # SEASON 3: PLAYOFFS & BASEBALL (February, April, May, June)
    # Active: NBA/NHL Playoffs, MLB
    # Strategy: Focus on Evenings. No Weekend Morning Blitz needed (No Football).
    # ------------------------------------------------------------------
    elif month in [2, 4, 5, 6]:
        print(f"📅 Month {month}: Detected SPRING/PLAYOFF Season. Loading Evening Schedule.")
        return [
            "- cron: '0 15-23,0-4 * * *'",       # Baseline: Hourly
            "- cron: '15,30,45 22-23 * * *'"     # Daily: Every 15m 6pm-8pm ET (Playoff Tipoffs/First Pitch)
        ]

    # ------------------------------------------------------------------
    # SEASON 4: THE DEAD ZONE (July - August)
    # Active: MLB Only
    # Strategy: Save Money. Hourly only. No 15-minute blitzes.
    # ------------------------------------------------------------------
    else:
        print(f"📅 Month {month}: Detected SUMMER/OFF-SEASON. Loading Economy Schedule.")
        return [
            "- cron: '0 16-23,0-4 * * *'"        # Baseline: Hourly 12pm-12am ET only
        ]

# ==============================================================================
# 📝 THE WRITER: YAML UPDATER
# ==============================================================================
def update_workflow_file():
    workflow_path = '.github/workflows/scrape_and_process.yml'
    
    if not os.path.exists(workflow_path):
        print("❌ Workflow file not found.")
        return

    with open(workflow_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_cron_lines = get_optimized_schedule()
    
    # Regex to find the existing schedule block and replace it
    # Looks for "schedule:" followed by any indented lines starting with "- cron:"
    pattern = r"(schedule:\s*\n)(\s*- cron:.*\n)+"
    
    # Construct the replacement string
    replacement = "\\1" + "\n".join([f"    {line}" for line in new_cron_lines]) + "\n"
    
    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Schedule updated successfully.")
        # Create a flag file so the GitHub Action knows to commit
        with open("schedule_updated.flag", "w") as f:
            f.write("true")
    else:
        print("⚡ Schedule is already optimized for this month. No changes.")

if __name__ == "__main__":
    update_workflow_file()
