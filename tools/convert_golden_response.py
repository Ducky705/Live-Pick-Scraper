#!/usr/bin/env python3
"""
Convert Golden Set Response to JSONL
====================================
Converts the AI's JSON response into the golden_set.jsonl format.

Usage:
    python tools/convert_golden_response.py

Input:  golden_set/response.json
Output: golden_set/golden_set.jsonl
"""

import json
import sys
from pathlib import Path


def convert_response(response_path: Path, image_list_path: Path, output_path: Path):
    """Convert AI response to golden set JSONL format."""
    
    # Load response
    try:
        response = json.loads(response_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in response.json: {e}")
        sys.exit(1)
    
    # Load image list for path mapping
    image_list = json.loads(image_list_path.read_text(encoding='utf-8'))
    path_map = {item['filename']: item['path'] for item in image_list}
    
    # Get annotations
    annotations = response.get('annotations', [])
    if not annotations:
        print("ERROR: No annotations found in response.json")
        print("Expected format: { \"annotations\": [...] }")
        sys.exit(1)
    
    print(f"Processing {len(annotations)} image annotations...")
    
    # Convert to JSONL format
    lines = []
    total_picks = 0
    
    for ann in annotations:
        image_filename = ann.get('image', '')
        picks = ann.get('picks', [])
        
        # Get full path
        image_path = path_map.get(image_filename, f"temp_images/{image_filename}")
        
        # Convert picks to full field names
        expected_picks = []
        for pick in picks:
            converted = {
                "league": pick.get('lg', 'Other'),
                "type": pick.get('ty', 'Unknown'),
                "pick": pick.get('p', ''),
                "odds": pick.get('od'),
                "units": pick.get('u', 1.0),
                "subject": pick.get('sub'),
                "market": pick.get('mkt'),
                "line": pick.get('ln'),
                "prop_side": pick.get('side')
            }
            expected_picks.append(converted)
            total_picks += 1
        
        # Create JSONL entry
        entry = {
            "image_path": image_path,
            "expected_picks": expected_picks
        }
        lines.append(json.dumps(entry, separators=(',', ':')))
    
    # Write JSONL
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    
    print(f"\nConversion complete!")
    print(f"  Images: {len(annotations)}")
    print(f"  Total picks: {total_picks}")
    print(f"  Output: {output_path}")
    
    # Stats
    images_with_picks = sum(1 for ann in annotations if ann.get('picks'))
    images_empty = len(annotations) - images_with_picks
    print(f"\n  Images with picks: {images_with_picks}")
    print(f"  Images empty: {images_empty}")


def main():
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "golden_set"
    
    response_path = golden_dir / "response.json"
    image_list_path = golden_dir / "image_list.json"
    output_path = golden_dir / "golden_set.jsonl"
    
    if not response_path.exists():
        print(f"ERROR: response.json not found at {response_path}")
        print("Run create_golden_set_pdf.py first, then paste AI response into response.json")
        sys.exit(1)
    
    if not image_list_path.exists():
        print(f"ERROR: image_list.json not found at {image_list_path}")
        print("Run create_golden_set_pdf.py first")
        sys.exit(1)
    
    convert_response(response_path, image_list_path, output_path)
    
    print(f"""
================================================================================
NEXT STEPS
================================================================================

1. To evaluate your parser against this golden set:
   python tools/evaluate_golden_set.py golden_set/golden_set.jsonl --predictions predictions.jsonl

2. The golden set is ready at: {output_path}

================================================================================
""")


if __name__ == "__main__":
    main()
