import os
import subprocess
import time

dates = ['2026-01-25', '2026-01-26', '2026-01-27', '2026-01-28']
script_path = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\cli_tool.py'

for d in dates:
    print(f"\n=======================================================")
    print(f"        STARTING PRODUCTION PIPELINE FOR {d}           ")
    print(f"=======================================================\n")
    
    start_time = time.time()
    
    try:
        # Run process interactively so output streams correctly to stdout
        process = subprocess.run(['python', script_path, '--date', d])
        if process.returncode != 0:
            print(f"\n[!] WARNING: Script returned non-zero exit code ({process.returncode}) for date {d}")
    except Exception as e:
        print(f"\n[!] CRITICAL ERROR executing {d}: {e}")
        
    duration = time.time() - start_time
    print(f"\n---> Completed {d} processing in {duration / 60:.2f} minutes.")
    
    if d != dates[-1]:
       print("Cooling down for 10 seconds before next date pipeline...")
       time.sleep(10)
       
print("\n[SUCCESS] ALL REQUESTED DATES PROCESSED SUCCESSFULLY!")
