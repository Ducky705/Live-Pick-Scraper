"""
Production-Accurate PDF Generator
Matches EXACTLY how main.py's api_prepare_manual_export creates PDFs.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BENCHMARK_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_DIR = os.path.join(BENCHMARK_DIR, 'dataset_v2')
IMAGES_DIR = os.path.join(DATASET_DIR, 'images')
METADATA_PATH = os.path.join(DATASET_DIR, 'benchmark_metadata.json')
OUTPUT_PDF = os.path.join(DATASET_DIR, 'production_format.pdf')
PROMPT_FILE = os.path.join(DATASET_DIR, 'production_prompt.txt')


def add_caption_overlay(img, caption_text, msg_id):
    """
    EXACT COPY from main.py api_prepare_manual_export.
    Overlays caption text at top of image for AI context matching.
    """
    try:
        # Ensure RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create header for caption
        header_height = 80 if len(caption_text) < 100 else 120
        new_height = img.height + header_height
        
        # New image with header space
        new_img = Image.new('RGB', (img.width, new_height), color=(30, 30, 30))
        new_img.paste(img, (0, header_height))
        
        # Draw caption text
        draw = ImageDraw.Draw(new_img)
        
        # Try to use a readable font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Truncate caption if too long
        max_chars = 200
        display_text = caption_text[:max_chars] + "..." if len(caption_text) > max_chars else caption_text
        display_text = f"[MSG {msg_id}] {display_text}"
        
        # Wrap text
        chars_per_line = max(50, img.width // 7)
        lines = []
        for i in range(0, len(display_text), chars_per_line):
            lines.append(display_text[i:i+chars_per_line])
        
        # Draw each line
        y_offset = 10
        for line in lines[:5]:  # Max 5 lines
            draw.text((10, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += 18
        
        return new_img
    except Exception as e:
        print(f"Caption overlay failed: {e}")
        return img


def create_production_pdf():
    """Generate PDF exactly like production app."""
    
    # Load metadata
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    data = metadata.get('data', [])
    print(f"📄 Creating Production PDF ({len(data)} images)...")
    
    pdf_pages = []
    
    for item in data:
        img_filename = item.get('image')
        caption = item.get('caption', '') or ''
        msg_id = item.get('original_msg_id', item.get('id'))
        
        if not img_filename:
            continue
        
        img_path = os.path.join(IMAGES_DIR, img_filename)
        if not os.path.exists(img_path):
            print(f"  ⚠️ Not found: {img_filename}")
            continue
        
        try:
            img = Image.open(img_path)
            
            # Ensure RGB for PDF
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (max 1200px width for PDF) - EXACTLY like production
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Add caption overlay - EXACTLY like production
            img_with_caption = add_caption_overlay(img, caption, msg_id)
            pdf_pages.append(img_with_caption)
            
        except Exception as e:
            print(f"  ❌ Error: {img_filename} - {e}")
    
    if not pdf_pages:
        print("❌ No pages!")
        return
    
    # Save as PDF - EXACTLY like production
    pdf_pages[0].save(
        OUTPUT_PDF,
        "PDF",
        save_all=True,
        append_images=pdf_pages[1:] if len(pdf_pages) > 1 else [],
        resolution=100.0
    )
    
    pdf_size_mb = os.path.getsize(OUTPUT_PDF) / (1024 * 1024)
    print(f"✅ PDF: {OUTPUT_PDF}")
    print(f"   Size: {pdf_size_mb:.1f} MB, Pages: {len(pdf_pages)}")
    
    # Generate EXACT production prompt
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""You are an expert sports betting data parser. I have uploaded a PDF containing betting pick images.

**IMPORTANT**: Each page has a HEADER showing the Message ID and Caption/Context text at the top (dark bar with white text).
Use this embedded context along with the image content to extract picks.

---
## FORMATTING RULES

### Leagues
Use: `NFL`, `NCAAF`, `NBA`, `NCAAB`, `WNBA`, `MLB`, `NHL`, `EPL`, `MLS`, `UCL`, `UFC`, `PFL`, `TENNIS`, `PGA`, `F1`, `Other`

### Types
Use: `Moneyline`, `Spread`, `Total`, `Player Prop`, `Team Prop`, `Game Prop`, `Period`, `Parlay`, `Teaser`, `Future`, `Unknown`

### Pick Value Formats (by Type)
- **Moneyline**: `Team Name ML` → `Los Angeles Lakers ML`
- **Spread**: `Team Name Spread` → `Green Bay Packers -7.5`
- **Total**: `Team A vs Team B Over/Under Number` → `Lakers vs Celtics Over 215.5`
- **Player Prop**: `Player Name: Stat Over/Under Value` → `LeBron James: Pts Over 25.5`
  - Stats: `Pts`, `Reb`, `Ast`, `PRA`, `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `K`, `H`, `HR`, `RBI`, `SOG`, `G`, `A`
- **Team Prop**: `Team Name: Stat Over/Under Value` → `Cowboys: Total Points Over 27.5`
- **Period**: `Identifier Format` → `1H NYK vs BOS Total Over 110.5`, `1Q Thunder -2`
  - Identifiers: `1H`, `2H`, `1Q`, `2Q`, `3Q`, `4Q`, `P1`, `P2`, `P3`, `F5`, `60 min`
- **Parlay**: `(League) Leg / (League) Leg` → `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
- **Teaser**: `(Teaser Xpt League) Leg / ...` → `(Teaser 6pt NFL) Chiefs -2.5 / (Teaser 6pt NFL) Eagles +8.5`
- **Future**: `Event: Selection` → `Super Bowl LIX Winner: Kansas City Chiefs`

### Key Rules
- Odds (-110, +150) go ONLY in the `od` field, NOT in pick value
- Omit trailing `.0` (use `48` not `48.0`, but keep `48.5`)
- Capper name is the person/brand, NOT watermarks like "@cappersfree"

---
## OUTPUT FORMAT
Return a JSON object:
{{
  "picks": [
    {{ "id": <message_id>, "cn": "<capper_name>", "lg": "<league>", "ty": "<type>", "p": "<pick_value>", "od": <odds_or_null>, "u": 1.0, "dt": "{current_date}" }}
  ]
}}

Extract ALL picks from ALL pages. Return ONLY valid JSON."""

    # Save prompt
    with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"📝 Prompt: {PROMPT_FILE}")
    
    return OUTPUT_PDF, PROMPT_FILE


if __name__ == "__main__":
    create_production_pdf()
