from src.schedule_manager import ScheduleManager
import sys

def check_schedule():
    target_date = "2026-02-14"
    print(f"Fetching schedule for {target_date}...")
    try:
        context = ScheduleManager.get_context_string(target_date)
        print(f"Schedule Context Length: {len(context)}")
        print(f"First 500 chars:\n{context[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schedule()
