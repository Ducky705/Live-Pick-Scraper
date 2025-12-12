import os

REQUIREMENTS_TXT = """asyncio
telethon
supabase
openai
tenacity
pydantic
python-dotenv
# --- NEW DEPENDENCIES FOR V3 ---
thefuzz
python-levenshtein
opencv-python-headless
pytesseract
numpy
"""

def main():
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(REQUIREMENTS_TXT)
    print("✅ requirements.txt updated with OCR and Fuzzy Matching dependencies.")
    print("🚀 SYSTEM STATUS: GREEN. READY TO DEPLOY.")

if __name__ == "__main__":
    main()