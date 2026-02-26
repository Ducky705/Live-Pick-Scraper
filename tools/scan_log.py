import os

log_file = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\logs\cli_scraper.log'
with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for line in lines[-200:]:
    if 'Supabase' in line or 'upload' in line.lower() or '[SmartMatch]' in line:
        print(line.strip())
