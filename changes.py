import os
import shutil

def clean_project():
    print("="*60)
    print("🧹 SPORTS BETTING SCRAPER: FINAL CLEANUP")
    print("="*60)

    # 1. Define files to remove (Temporary artifacts & Scripts)
    files_to_delete = [
        # The Rapid Test Suite
        "rapid_test.py",
        "tests/real_world_data.py",
        "setup_rapid_env.py",
        
        # Data Dumps & Reports
        "raw_samples.txt",
        "backtest_report.csv",
        "backtest_report_v2.csv",
        "capper_debug_report.csv",
        "schedule_updated.flag",
        
        # Temporary "Apply" and "Fix" scripts from previous steps
        # (Listing common names used in this session just in case they exist)
        "apply_accuracy_fix.py",
        "apply_accuracy_upgrade.py",
        "apply_final_fix.py",
        "apply_final_polish.py",
        "apply_su_fix.py",
        "dump_raw_samples.py",
        "fix_parlay_logic.py",
        "fix_parsers.py",
        "reset_queue.py",
        "upgrade_capper_logic.py",
        "upgrade_scrapers.py"
    ]

    # 2. Delete Files
    print("🔹 Removing temporary files...")
    for file_path in files_to_delete:
        # Handle Windows/Linux path separators
        norm_path = os.path.normpath(file_path)
        
        if os.path.exists(norm_path):
            try:
                os.remove(norm_path)
                print(f"   ✅ Deleted: {norm_path}")
            except Exception as e:
                print(f"   ❌ Error deleting {norm_path}: {e}")
        else:
            # Silent skip if file was already deleted or never created
            pass

    # 3. Clean __pycache__ (Forces fresh compilation of new logic)
    print("\n🔹 Cleaning Python cache (__pycache__)...")
    cache_count = 0
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                path = os.path.join(root, d)
                try:
                    shutil.rmtree(path)
                    cache_count += 1
                except Exception as e:
                    print(f"   ❌ Error removing {path}: {e}")
    print(f"   ✅ Removed {cache_count} cache directories.")

    print("\n" + "="*60)
    print("✨ CLEANUP COMPLETE")
    print("="*60)
    print("Your project is now lean and production-ready.")
    print("Files kept: changes.py, copy_code.py, and all core logic.")
    print("\n👉 To start the scraper: python main.py")

if __name__ == "__main__":
    clean_project()