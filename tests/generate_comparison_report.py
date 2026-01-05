# tests/generate_comparison_report.py
"""
Generate visual comparison report for OCR preprocessing variants.
Now with multiple sample images for comprehensive comparison.
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
        ("v2_improved", preprocess_image_v2, {}),
        ("v3_standard", preprocess_image_v3, {"use_red_channel": False}),
        ("v3_red_channel", preprocess_image_v3, {"use_red_channel": True}),
    ]
    
    results = []
    
    for variant_name, preprocess_func, kwargs in variants:
        if preprocess_func is None:
            processed = img.convert('RGB')
            text = "[Original image - no OCR]"
        else:
            processed = preprocess_func(img, **kwargs) if kwargs else preprocess_func(img)
            config = '--psm 6 --oem 3'
            text = pytesseract.image_to_string(processed, config=config).strip()
        
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


def generate_multi_image_report(all_image_results: dict, output_dir: Path):
    """Generate HTML report with multiple images, each showing all variants."""
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Preprocessing Comparison Report</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; 
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        h1 { text-align: center; color: #00d4ff; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        h2 { color: #ffd700; margin-top: 50px; border-bottom: 2px solid #ffd700; padding-bottom: 10px; }
        .image-section {
            background: #16213e;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 40px;
        }
        .summary {
            background: #0f3460;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .summary table {
            width: 100%;
            border-collapse: collapse;
        }
        .summary th, .summary td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        .summary th { color: #00d4ff; }
        .best { background: rgba(0, 255, 0, 0.15); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 15px;
        }
        .card {
            background: #0a0a15;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #333;
        }
        .card img {
            width: 100%;
            height: auto;
            display: block;
        }
        .card-body {
            padding: 12px;
        }
        .card h4 {
            margin: 0 0 8px 0;
            color: #00d4ff;
            font-size: 14px;
        }
        .stats {
            display: flex;
            gap: 15px;
            margin-bottom: 8px;
        }
        .stat {
            background: #16213e;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .ocr-text {
            background: #16213e;
            padding: 8px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 11px;
            max-height: 150px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .legend {
            background: #0f3460;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .legend h3 { margin-top: 0; color: #ffd700; }
        .legend ul { margin: 0; padding-left: 20px; }
        .legend li { margin: 5px 0; }
    </style>
</head>
<body>
    <h1>🔬 OCR Preprocessing Comparison Report</h1>
    <p class="subtitle">Compare preprocessing variants across multiple sample images</p>
    
    <div class="legend">
        <h3>📋 Variant Descriptions</h3>
        <ul>
            <li><strong>original</strong> - Raw image, no processing</li>
            <li><strong>v1_baseline</strong> - Basic preprocessing (Cubic upscale, CLAHE, Otsu)</li>
            <li><strong>v2_improved</strong> - Lanczos4 upscale, padding, gamma, bilateral filter</li>
            <li><strong>v3_best</strong> - Full pipeline: Lanczos4 + sharpen + NLM denoise + watermark removal</li>
            <li><strong>v3_no_watermark</strong> - Same as v3_best but without watermark removal</li>
        </ul>
    </div>
"""
    
    for image_name, results in all_image_results.items():
        sorted_results = sorted(results, key=lambda x: x['word_count'], reverse=True)
        best_variant = sorted_results[0]['variant'] if sorted_results and sorted_results[0]['variant'] != 'original' else sorted_results[1]['variant'] if len(sorted_results) > 1 else ""
        
        html += f"""
    <div class="image-section">
        <h2>📸 {image_name}</h2>
        
        <div class="summary">
            <table>
                <tr>
                    <th>Variant</th>
                    <th>Words</th>
                    <th>Characters</th>
                </tr>
"""
        
        for r in sorted_results:
            is_best = 'class="best"' if r['variant'] == best_variant else ''
            html += f"""                <tr {is_best}>
                    <td>{r['variant']}</td>
                    <td>{r['word_count']}</td>
                    <td>{r['char_count']}</td>
                </tr>
"""
        
        html += """            </table>
        </div>
        
        <div class="grid">
"""
        
        for r in results:
            text_preview = r['text'][:300] + "..." if len(r['text']) > 300 else r['text']
            text_preview = text_preview.replace('<', '&lt;').replace('>', '&gt;')
            
            html += f"""            <div class="card">
                <img src="comparison_images/{r['image_path']}" alt="{r['variant']}">
                <div class="card-body">
                    <h4>{r['variant']}</h4>
                    <div class="stats">
                        <span class="stat">📝 {r['word_count']} words</span>
                        <span class="stat">🔤 {r['char_count']} chars</span>
                    </div>
                    <div class="ocr-text">{text_preview}</div>
                </div>
            </div>
"""
        
        html += """        </div>
    </div>
"""
    
    html += """</body>
</html>
"""
    
    report_path = output_dir / "ocr_comparison_report.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return report_path


def main():
    # 3 different sample images for comparison
    target_images = [
        "-1001900292133_55832",  # Problematic image
        "-1001900292133_55810",  # Different style
        "-1001900292133_55827",  # Another sample
    ]
    
    base_dir = Path(__file__).parent.parent
    samples_dir = base_dir / "tests" / "samples"
    output_dir = base_dir / "benchmark_results" / "comparison_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_image_results = {}
    
    for image_id in target_images:
        image_path = samples_dir / f"{image_id}.jpg"
        if not image_path.exists():
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📸 Processing: {image_id}")
        results = process_and_save(image_path, output_dir)
        all_image_results[image_id] = results
    
    # Generate combined report
    report_path = generate_multi_image_report(all_image_results, base_dir / "benchmark_results")
    print(f"\n✅ Report saved to: {report_path}")


if __name__ == "__main__":
    main()
