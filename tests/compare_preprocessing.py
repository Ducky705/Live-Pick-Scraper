"""
Compare AI OCR with different preprocessing options:
1. Full v3 preprocessing (upscaling, padding, gamma, CLAHE, red removal, etc.)
2. Only red watermark removal (minimal preprocessing)
3. Raw image (no preprocessing - baseline)
"""
import os
import sys
import tempfile
from PIL import Image
import cv2
import numpy as np

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.openrouter_client import openrouter_completion
from config import TEMP_IMG_DIR

# --- PREPROCESSING FUNCTIONS ---

def preprocess_red_removal_only(img):
    """Minimal preprocessing: Only remove red watermark (@cappersfree)"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # Convert to HSV for red detection
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    
    # Red spans across hue 0 and 180 in HSV
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)
    
    # Dilate mask slightly
    kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.dilate(red_mask, kernel, iterations=1)
    
    # Replace red pixels with white
    cv_img[red_mask > 0] = [255, 255, 255]
    
    # Convert back to PIL RGB
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv_img)


def preprocess_full_v3(img):
    """Full v3 preprocessing with all enhancements"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    cv_img = np.array(img)
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # 0. REMOVE RED WATERMARK
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.dilate(red_mask, kernel, iterations=1)
    cv_img[red_mask > 0] = [255, 255, 255]
    
    # 1. UPSCALE using Lanczos4
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Add PADDING
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # 3. Use RED CHANNEL for grayscale
    gray = cv_img[:, :, 2]
    
    # 4. SHARPENING (Unsharp Mask)
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    
    # 5. GAMMA CORRECTION
    gamma = 1.2
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
    gray = cv2.LUT(gray, table)
    
    # 6. CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # 7. NLM DENOISING
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # 8. ADAPTIVE THRESHOLDING (Otsu's method)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 9. Invert if background is dark
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    # 10. Morphological cleanup
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return Image.fromarray(binary)


def run_ai_ocr(image_path, preprocess_func=None):
    """Run AI OCR with optional preprocessing"""
    img = Image.open(image_path)
    
    if preprocess_func:
        img = preprocess_func(img)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
        img.save(temp_path)
    
    try:
        prompt = "Extract all text from this image exactly as it appears. Do not add any markdown formatting or commentary. Just return the text."
        result = openrouter_completion(prompt, model="google/gemma-3-12b-it:free", images=[temp_path])
        return result
    finally:
        os.unlink(temp_path)


def main():
    # Get sample images
    sample_images = []
    for f in os.listdir(TEMP_IMG_DIR):
        if f.startswith('-') and f.endswith('.jpg'):  # Message images
            sample_images.append(os.path.join(TEMP_IMG_DIR, f))
        if len(sample_images) >= 3:  # Test with 3 images
            break
    
    if not sample_images:
        print("No sample images found!")
        return
    
    print(f"Testing with {len(sample_images)} images...\n")
    print("=" * 80)
    
    results = []
    
    for img_path in sample_images:
        img_name = os.path.basename(img_path)
        print(f"\n📷 Image: {img_name}")
        print("-" * 60)
        
        # 1. Raw (no preprocessing)
        print("\n[1] RAW (no preprocessing):")
        try:
            raw_result = run_ai_ocr(img_path, preprocess_func=None)
            print(f"   {raw_result[:200]}..." if len(raw_result) > 200 else f"   {raw_result}")
        except Exception as e:
            raw_result = f"Error: {e}"
            print(f"   Error: {e}")
        
        # 2. Red removal only
        print("\n[2] RED REMOVAL ONLY:")
        try:
            red_only_result = run_ai_ocr(img_path, preprocess_func=preprocess_red_removal_only)
            print(f"   {red_only_result[:200]}..." if len(red_only_result) > 200 else f"   {red_only_result}")
        except Exception as e:
            red_only_result = f"Error: {e}"
            print(f"   Error: {e}")
        
        # 3. Full v3 preprocessing
        print("\n[3] FULL V3 PREPROCESSING:")
        try:
            full_v3_result = run_ai_ocr(img_path, preprocess_func=preprocess_full_v3)
            print(f"   {full_v3_result[:200]}..." if len(full_v3_result) > 200 else f"   {full_v3_result}")
        except Exception as e:
            full_v3_result = f"Error: {e}"
            print(f"   Error: {e}")
        
        results.append({
            'image': img_name,
            'raw': raw_result,
            'red_only': red_only_result,
            'full_v3': full_v3_result
        })
        
        print("\n" + "=" * 80)
    
    # Summary
    print("\n\n📊 SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"\n{r['image']}:")
        print(f"  RAW chars:      {len(r['raw'])}")
        print(f"  RED ONLY chars: {len(r['red_only'])}")
        print(f"  FULL V3 chars:  {len(r['full_v3'])}")


if __name__ == "__main__":
    main()
