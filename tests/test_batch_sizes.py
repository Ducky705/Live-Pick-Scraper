"""
Batch Size Testing Script for AI Studio
Creates exports in different sizes to determine optimal batch limits.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont
from config import TEMP_IMG_DIR

def create_test_exports():
    """Create test exports at different batch sizes for AI Studio testing."""
    
    # Find all images in temp directory
    temp_dir = Path(TEMP_IMG_DIR)
    if not temp_dir.exists():
        print(f"ERROR: Temp directory not found: {temp_dir}")
        return
    
    all_images = list(temp_dir.glob("*.jpg")) + list(temp_dir.glob("*.png"))
    all_images.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Newest first
    
    print(f"Found {len(all_images)} images in {temp_dir}")
    
    if len(all_images) == 0:
        print("No images to export. Fetch messages first in the app.")
        return
    
    # Create output directory
    downloads = Path.home() / "Downloads"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = downloads / f"AI_Studio_Test_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Batch sizes to test
    batch_sizes = [20, 40, 60, 80, 100, len(all_images)]
    batch_sizes = [s for s in batch_sizes if s <= len(all_images)]
    batch_sizes = sorted(set(batch_sizes))  # Remove duplicates
    
    print(f"\nWill create exports for batch sizes: {batch_sizes}")
    print(f"Output directory: {output_dir}\n")
    
    for size in batch_sizes:
        images_subset = all_images[:size]
        
        # 1. Create FOLDER export
        folder_name = f"images_{size}"
        folder_path = output_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        
        for i, img_path in enumerate(images_subset):
            dst = folder_path / f"img_{i+1:03d}{img_path.suffix}"
            # Copy with size limit
            try:
                img = Image.open(img_path)
                # Resize if too large (max 2000px on longest side for speed)
                max_dim = 2000
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.save(str(dst), quality=85, optimize=True)
            except Exception as e:
                print(f"  Error processing {img_path.name}: {e}")
        
        print(f"✓ Created folder: {folder_name}/ ({size} images)")
        
        # 2. Create PDF export
        pdf_name = f"images_{size}.pdf"
        pdf_path = output_dir / pdf_name
        
        try:
            pdf_images = []
            for img_path in images_subset:
                img = Image.open(img_path)
                # Convert to RGB (required for PDF)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Resize for PDF (max 1500px to keep file size reasonable)
                max_dim = 1500
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                pdf_images.append(img)
            
            if pdf_images:
                # Save first image, append rest
                pdf_images[0].save(
                    str(pdf_path),
                    "PDF",
                    save_all=True,
                    append_images=pdf_images[1:],
                    resolution=100.0
                )
                pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                print(f"✓ Created PDF: {pdf_name} ({pdf_size_mb:.1f} MB)")
        except Exception as e:
            print(f"  Error creating PDF for {size}: {e}")
    
    print(f"\n{'='*50}")
    print(f"DONE! All exports created in:\n{output_dir}")
    print(f"\nTEST INSTRUCTIONS:")
    print(f"1. Open AI Studio (aistudio.google.com)")
    print(f"2. Start with smallest batch (images_20/)")
    print(f"3. Upload all images and paste test prompt")
    print(f"4. Note if it works or fails")
    print(f"5. Repeat with larger batches until you find the limit")
    print(f"\nAlso test PDFs - they may have different limits")
    print(f"{'='*50}")

# Simple test prompt to copy
TEST_PROMPT = """
I have uploaded betting pick images. For each image, extract:
- The pick (team/player and bet type)
- The odds if visible
- The league (NBA, NFL, etc)

Return as JSON array:
[{"pick": "...", "odds": ..., "league": "..."}]
"""

if __name__ == "__main__":
    print("="*50)
    print("AI STUDIO BATCH SIZE TESTER")
    print("="*50)
    create_test_exports()
    print(f"\nTEST PROMPT TO USE:\n{TEST_PROMPT}")
