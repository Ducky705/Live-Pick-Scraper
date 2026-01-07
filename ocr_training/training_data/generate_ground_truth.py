# training_data/generate_ground_truth.py
"""
Generate ground truth files for Tesseract training.
Uses current best OCR to create initial .gt.txt files that user will review/correct.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract

from src.ocr_handler import preprocess_image_v3, TESSERACT_BIN

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN


def get_samples():
    manifest_path = Path(__file__).parent.parent / "tests" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_ground_truth():
    """Generate ground truth files for all sample images."""
    
    base_dir = Path(__file__).parent.parent
    samples_dir = base_dir / "tests" / "samples"
    images_dir = Path(__file__).parent / "images"
    gt_dir = Path(__file__).parent / "ground_truth"
    
    images_dir.mkdir(exist_ok=True)
    gt_dir.mkdir(exist_ok=True)
    
    cases = get_samples()
    
    print(f"\n📚 Generating Ground Truth for {len(cases)} images")
    print("="*60)
    
    for i, case in enumerate(cases, 1):
        image_file = case.get("image_file", "")
        if not image_file:
            continue
        
        image_path = samples_dir / image_file.replace("samples/", "")
        if not image_path.exists():
            print(f"  ❌ Not found: {image_path}")
            continue
        
        # Create base name
        base_name = image_path.stem
        
        # Load and preprocess image
        img = Image.open(image_path)
        processed = preprocess_image_v3(img)
        
        # Save as .tif (Tesseract training format)
        tif_path = images_dir / f"{base_name}.tif"
        processed.save(tif_path)
        
        # Run OCR to get initial ground truth
        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(processed, config=config).strip()
        
        # Save ground truth
        gt_path = gt_dir / f"{base_name}.gt.txt"
        with open(gt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"  [{i:2d}/{len(cases)}] {base_name}: {len(text.split())} words")
    
    print("\n" + "="*60)
    print(f"✅ Generated {len(cases)} ground truth files")
    print(f"   Images: {images_dir}")
    print(f"   Ground truth: {gt_dir}")
    print("\n⚠️  IMPORTANT: Review and correct the .gt.txt files!")
    print("   Each file should contain the EXACT text from the image.")


def create_user_words():
    """Create user words file with sports betting vocabulary."""
    
    words = [
        # Bet types
        "Spread", "Moneyline", "ML", "Over", "Under", "Parlay", "Teaser",
        "Prop", "Total", "Pick", "ATS", "OU", "PK",
        
        # NBA Teams
        "Lakers", "Celtics", "Warriors", "Nets", "Heat", "Bucks", "Suns",
        "Clippers", "Nuggets", "76ers", "Sixers", "Mavericks", "Grizzlies",
        "Cavaliers", "Knicks", "Bulls", "Hawks", "Pacers", "Pistons",
        "Hornets", "Magic", "Wizards", "Raptors", "Timberwolves", "Thunder",
        "Trail Blazers", "Blazers", "Kings", "Pelicans", "Spurs", "Jazz", "Rockets",
        
        # NFL Teams
        "Chiefs", "Eagles", "Bills", "Cowboys", "49ers", "Dolphins", "Lions",
        "Ravens", "Bengals", "Jaguars", "Chargers", "Seahawks", "Vikings",
        "Packers", "Bears", "Saints", "Falcons", "Panthers", "Buccaneers",
        "Commanders", "Giants", "Jets", "Patriots", "Steelers", "Browns",
        "Texans", "Colts", "Titans", "Broncos", "Raiders", "Cardinals", "Rams",
        
        # NCAAB (common)
        "Duke", "Kentucky", "Kansas", "UNC", "Carolina", "UCLA", "Gonzaga",
        "Villanova", "Michigan", "Ohio State", "Purdue", "Indiana", "Illinois",
        "Arizona", "Auburn", "Alabama", "Tennessee", "Florida", "Syracuse",
        "Louisville", "UConn", "Stanford", "Oregon", "Baylor", "Texas", "Houston",
        "Wake Forest", "Virginia", "Notre Dame", "Georgetown", "Marquette",
        
        # Common words
        "unit", "units", "pick", "picks", "bet", "bets", "play", "plays",
        "free", "lock", "winner", "winning", "today", "tonight", "game",
        "Team", "line", "odds", "stake", "risk", "profit", "ROI",
        
        # Capper names
        "BankrollBill", "cappersfree",
    ]
    
    words_path = Path(__file__).parent / "user_words.txt"
    with open(words_path, 'w', encoding='utf-8') as f:
        for word in sorted(set(words)):
            f.write(word + '\n')
    
    print(f"✅ Created user_words.txt with {len(words)} words")


def create_user_patterns():
    """Create user patterns file for odds/spreads."""
    
    patterns = [
        r"\+\d{3}",     # +150
        r"\-\d{3}",     # -110
        r"\+\d{2}",     # +10
        r"\-\d{2}",     # -10
        r"\d+\.\d",     # 5.5
        r"\d+-Team",    # 2-Team
        r"\d+ unit",    # 1 unit
    ]
    
    patterns_path = Path(__file__).parent / "user_patterns.txt"
    with open(patterns_path, 'w', encoding='utf-8') as f:
        for pattern in patterns:
            f.write(pattern + '\n')
    
    print(f"✅ Created user_patterns.txt with {len(patterns)} patterns")


if __name__ == "__main__":
    generate_ground_truth()
    create_user_words()
    create_user_patterns()
