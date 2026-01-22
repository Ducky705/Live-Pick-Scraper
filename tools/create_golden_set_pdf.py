#!/usr/bin/env python3
"""
Golden Set PDF Generator
========================
Creates a PDF with all images from temp_images/ and a prompt file for AI annotation.

Usage:
    python tools/create_golden_set_pdf.py [--limit 50]

Output:
    - golden_set/images.pdf - All images combined
    - golden_set/prompt.txt - Copy this to AI
    - golden_set/image_list.json - Image paths for reference
    - golden_set/response.json - Paste AI response here
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

def create_pdf_with_pillow(image_paths: list[Path], output_path: Path):
    """Create PDF using Pillow (no external dependencies)."""
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow")
        sys.exit(1)
    
    if not image_paths:
        print("No images found!")
        return False
    
    # Convert images to RGB (required for PDF)
    images = []
    for i, path in enumerate(image_paths):
        try:
            img = Image.open(path)
            if img.mode == 'RGBA':
                # Convert RGBA to RGB with white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
            print(f"  [{i+1}/{len(image_paths)}] {path.name}")
        except Exception as e:
            print(f"  [SKIP] {path.name}: {e}")
    
    if not images:
        print("No valid images to process!")
        return False
    
    # Save as PDF
    first_image = images[0]
    if len(images) > 1:
        first_image.save(output_path, save_all=True, append_images=images[1:])
    else:
        first_image.save(output_path)
    
    print(f"\nPDF created: {output_path}")
    print(f"Total images: {len(images)}")
    return True


def generate_prompt(image_paths: list[Path]) -> str:
    """Generate the AI prompt for golden set annotation."""
    
    image_list = "\n".join([f"  {i+1}. {p.name}" for i, p in enumerate(image_paths)])
    
    return f"""# Golden Set Annotation Task

You are annotating {len(image_paths)} sports betting images to create ground-truth training data.

## Your Task
For EACH image, extract ALL betting picks visible. Output a JSON array.

## Image List
{image_list}

## Output Format
Return a JSON object with this structure:

```json
{{
  "annotations": [
    {{
      "image": "filename.jpg",
      "picks": [
        {{
          "lg": "NBA",
          "ty": "Spread",
          "p": "Lakers -5.5",
          "od": -110,
          "u": 1.0,
          "sub": "Los Angeles Lakers",
          "mkt": "Spread",
          "ln": -5.5,
          "side": null
        }}
      ]
    }}
  ]
}}
```

## Field Definitions

### Core Fields (Required)
| Field | Description | Example |
|-------|-------------|---------|
| `lg` | League code | `NBA`, `NFL`, `MLB`, `NHL`, `NCAAB`, `NCAAF`, `UFC`, `TENNIS`, `Other` |
| `ty` | Bet type | `Moneyline`, `Spread`, `Total`, `Player Prop`, `Team Prop`, `Period`, `Parlay`, `Future` |
| `p` | Pick string (NO ODDS!) | `Lakers -5.5`, `LeBron James: Pts Over 25.5` |
| `od` | American odds (int or null) | `-110`, `150`, `null` |
| `u` | Units (default 1.0) | `1.0`, `2.0` |

### Structured Fields (Required for non-parlays)
| Field | Description | Example |
|-------|-------------|---------|
| `sub` | Subject (team/player full name) | `Los Angeles Lakers`, `LeBron James` |
| `mkt` | Market type | `Spread`, `ML`, `Pts`, `PassYds`, `Total` |
| `ln` | Line (float or null) | `-5.5`, `25.5`, `null` for ML |
| `side` | For O/U only | `Over`, `Under`, `null` |

## Pick Format by Type

### Moneyline
- Format: `Team ML` or `Player ML`
- Example: `Los Angeles Lakers ML`
- Structured: sub=`Los Angeles Lakers`, mkt=`ML`, ln=`null`, side=`null`

### Spread  
- Format: `Team +/-Line`
- Example: `Chiefs -7.5`
- Structured: sub=`Kansas City Chiefs`, mkt=`Spread`, ln=`-7.5`, side=`null`

### Total
- Format: `Away vs Home Over/Under Number`
- Example: `Lakers vs Celtics Over 220.5`
- Structured: sub=`Lakers vs Celtics`, mkt=`Total`, ln=`220.5`, side=`Over`

### Player Prop
- Format: `Player: Stat Over/Under Number`
- Example: `LeBron James: Pts Over 25.5`
- Structured: sub=`LeBron James`, mkt=`Pts`, ln=`25.5`, side=`Over`

### Period
- Format: `Period Identifier + Standard Format`
- Identifiers: `1H`, `2H`, `1Q`, `F5`, `P1`
- Example: `1H Chiefs -3.5`

### Parlay
- Format: `Leg / Leg / Leg` (NO league prefixes!)
- Example: `Cowboys -7 / Lakers ML / Duke -3`
- League field: Use `Other` for multi-sport, single league code for same-sport

### Teaser
- Format: `Teaser Xpt: Leg / Leg`
- Example: `Teaser 6pt: Chiefs -1 / Eagles +10`

## Rules

1. **NO ODDS IN PICK STRING** - Odds go in `od` field only
2. **NO LEAGUE IN PARLAY LEGS** - League is in `lg` field
3. **Full team names** - `Los Angeles Lakers` not `LAL`
4. **Skip non-picks** - Ignore "DM for picks", records, sportsbook names
5. **Multiple picks per image** - Extract ALL picks you see
6. **If no picks visible** - Use empty array: `"picks": []`

## Example Output

```json
{{
  "annotations": [
    {{
      "image": "-1001206097796_18400.jpg",
      "picks": [
        {{
          "lg": "NBA",
          "ty": "Spread", 
          "p": "Los Angeles Lakers -5.5",
          "od": -110,
          "u": 1.0,
          "sub": "Los Angeles Lakers",
          "mkt": "Spread",
          "ln": -5.5,
          "side": null
        }},
        {{
          "lg": "NFL",
          "ty": "Player Prop",
          "p": "Patrick Mahomes: PassYds Over 275.5",
          "od": -115,
          "u": 1.0,
          "sub": "Patrick Mahomes",
          "mkt": "PassYds",
          "ln": 275.5,
          "side": "Over"
        }}
      ]
    }},
    {{
      "image": "-1001206097796_18401.jpg",
      "picks": []
    }}
  ]
}}
```

Now analyze all {len(image_paths)} images and return the complete JSON.
"""


def main():
    parser = argparse.ArgumentParser(description="Create golden set PDF and prompt")
    parser.add_argument("--limit", type=int, default=50, help="Max images to include")
    parser.add_argument("--output", type=Path, default=Path("golden_set"), help="Output directory")
    args = parser.parse_args()
    
    # Find images
    project_root = Path(__file__).parent.parent
    temp_images = project_root / "temp_images"
    
    if not temp_images.exists():
        print(f"ERROR: temp_images directory not found at {temp_images}")
        sys.exit(1)
    
    # Get image files
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    image_paths = sorted([
        p for p in temp_images.iterdir() 
        if p.suffix.lower() in extensions
    ])[:args.limit]
    
    print(f"Found {len(image_paths)} images (limit: {args.limit})")
    
    if not image_paths:
        print("No images found!")
        sys.exit(1)
    
    # Create output directory
    output_dir = project_root / args.output
    output_dir.mkdir(exist_ok=True)
    
    # Generate PDF
    print("\nCreating PDF...")
    pdf_path = output_dir / "images.pdf"
    create_pdf_with_pillow(image_paths, pdf_path)
    
    # Generate prompt
    print("\nGenerating prompt...")
    prompt = generate_prompt(image_paths)
    prompt_path = output_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding='utf-8')
    print(f"Prompt saved: {prompt_path}")
    
    # Save image list for reference
    image_list = [{"index": i+1, "filename": p.name, "path": str(p)} for i, p in enumerate(image_paths)]
    list_path = output_dir / "image_list.json"
    list_path.write_text(json.dumps(image_list, indent=2), encoding='utf-8')
    print(f"Image list saved: {list_path}")
    
    # Create empty response file
    response_path = output_dir / "response.json"
    if not response_path.exists():
        response_path.write_text('{\n  "annotations": []\n}', encoding='utf-8')
    print(f"Response file: {response_path}")
    
    print(f"""
================================================================================
GOLDEN SET CREATED
================================================================================

1. PDF: {pdf_path}
   - Upload this to your AI (Claude, GPT-4V, Gemini)

2. PROMPT: {prompt_path}
   - Copy/paste this as the text prompt

3. RESPONSE: {response_path}
   - Paste the AI's JSON response here

4. After pasting, run:
   python tools/convert_golden_response.py

================================================================================
""")


if __name__ == "__main__":
    main()
