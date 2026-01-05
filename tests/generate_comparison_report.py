# tests/generate_comparison_report.py
"""
Generate visual comparison report for OCR preprocessing variants.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pytesseract

from src.ocr_handler import (
    preprocess_image, 
    preprocess_image_v2, 
    preprocess_image_v3,
    TESSERACT_BIN
)

if os.path.exists(TESSERACT_BIN):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN


def process_and_save(image_path: Path, output_dir: Path):
    """Process image with all variants and save results."""
    
    img = Image.open(image_path)
    base_name = image_path.stem
    
    variants = [
        ("original", None, {}),
        ("v1_baseline", preprocess_image, {}),
        ("v2_lanczos_pad_gamma", preprocess_image_v2, {}),
        ("v3_best", preprocess_image_v3, {"use_deskew": False, "use_sharpen": True, "use_nlm_denoise": True, "remove_watermark": True}),
        ("v3_no_watermark_removal", preprocess_image_v3, {"use_deskew": False, "use_sharpen": True, "use_nlm_denoise": True, "remove_watermark": False}),
    ]
    
    results = []
    
    for variant_name, preprocess_func, kwargs in variants:
        if preprocess_func is None:
            # Original - just save as-is
            processed = img.convert('RGB')
            text = "[Original image - no OCR]"
        else:
            processed = preprocess_func(img, **kwargs) if kwargs else preprocess_func(img)
            config = '--psm 6 --oem 3'
            text = pytesseract.image_to_string(processed, config=config).strip()
        
        # Save image
        save_path = output_dir / f"{base_name}_{variant_name}.png"
        processed.save(save_path)
        
        results.append({
            "variant": variant_name,
            "image_path": save_path.name,
            "text": text,
            "word_count": len(text.split()) if text else 0,
            "char_count": len(text) if text else 0
        })
        
        print(f"  ✓ {variant_name}: {len(text.split())} words")
    
    return results


def generate_html_report(results: list, image_name: str, output_dir: Path):
    """Generate HTML comparison report."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Preprocessing Comparison - {image_name}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; 
            color: #eee;
            margin: 0;
            padding: 20px;
        }}
        h1 {{ text-align: center; color: #00d4ff; }}
        h2 {{ color: #ffd700; margin-top: 40px; }}
        .summary {{
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .summary th, .summary td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        .summary th {{ color: #00d4ff; }}
        .best {{ background: rgba(0, 255, 0, 0.1); }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        .card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .card-body {{
            padding: 15px;
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #00d4ff;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 10px;
        }}
        .stat {{
            background: #0f3460;
            padding: 5px 10px;
            border-radius: 5px;
        }}
        .ocr-text {{
            background: #0a0a15;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
    </style>
</head>
<body>
    <h1>🔬 OCR Preprocessing Comparison</h1>
    <h2>Image: {image_name}</h2>
    
    <div class="summary">
        <h3>📊 Summary (sorted by word count)</h3>
        <table>
            <tr>
                <th>Variant</th>
                <th>Words</th>
                <th>Characters</th>
            </tr>
"""
    
    # Sort by word count
    sorted_results = sorted(results, key=lambda x: x['word_count'], reverse=True)
    best_variant = sorted_results[0]['variant'] if sorted_results else ""
    
    for r in sorted_results:
        is_best = 'class="best"' if r['variant'] == best_variant and r['variant'] != 'original' else ''
        html += f"""            <tr {is_best}>
                <td>{r['variant']}</td>
                <td>{r['word_count']}</td>
                <td>{r['char_count']}</td>
            </tr>
"""
    
    html += """        </table>
    </div>
    
    <h2>🖼️ Visual Comparison</h2>
    <div class="grid">
"""
    
    for r in results:
        text_preview = r['text'][:500] + "..." if len(r['text']) > 500 else r['text']
        text_preview = text_preview.replace('<', '&lt;').replace('>', '&gt;')
        
        html += f"""        <div class="card">
            <img src="comparison_images/{r['image_path']}" alt="{r['variant']}">
            <div class="card-body">
                <h3>{r['variant']}</h3>
                <div class="stats">
                    <span class="stat">📝 {r['word_count']} words</span>
                    <span class="stat">🔤 {r['char_count']} chars</span>
                </div>
                <div class="ocr-text">{text_preview}</div>
            </div>
        </div>
"""
    
    html += """    </div>
</body>
</html>
"""
    
    report_path = output_dir / "ocr_comparison_report.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return report_path


def main():
    # Target images to compare
    target_images = [
        "-1001900292133_55832",  # User-specified problematic image
    ]
    
    base_dir = Path(__file__).parent.parent
    samples_dir = base_dir / "tests" / "samples"
    output_dir = base_dir / "benchmark_results" / "comparison_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    for image_id in target_images:
        image_path = samples_dir / f"{image_id}.jpg"
        if not image_path.exists():
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📸 Processing: {image_id}")
        results = process_and_save(image_path, output_dir)
        all_results.extend(results)
        
        # Generate report
        report_path = generate_html_report(results, image_id, base_dir / "benchmark_results")
        print(f"\n✅ Report saved to: {report_path}")


if __name__ == "__main__":
    main()
