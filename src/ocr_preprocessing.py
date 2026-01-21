
import cv2
import numpy as np
from PIL import Image
import os

def deskew_image(gray):
    """
    Detect and correct image rotation/skew.
    Uses minAreaRect on contours to find the dominant angle.
    """
    # Find all contours
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) < 10:
        return gray  # Not enough points to deskew
    
    # Get the minimum area rectangle
    angle = cv2.minAreaRect(coords)[-1]
    
    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Only rotate if angle is significant (> 0.5 degrees)
    if abs(angle) < 0.5:
        return gray
    
    # Rotate the image
    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def preprocess_image_v3(img, use_deskew=False, use_sharpen=True, use_nlm_denoise=True, remove_watermark=True, use_red_channel=True):
    """
    BEST preprocessing pipeline with:
    - RED CHANNEL extraction (best for sports betting images - +10.7% improvement)
    - Red watermark removal (@cappersfree)
    - Unsharp Masking (sharpen edges)
    - Non-Local Means Denoising (better noise removal)
    - Deskewing DISABLED by default (images are always straight)
    
    Plus all v2 improvements (Lanczos4, padding, gamma, CLAHE).
    """
    
    # Convert Input to OpenCV format (BGR)
    if isinstance(img, np.ndarray):
        # Already numpy, assume BGR if 3 channels, or Grayscale
        cv_img = img.copy()
    else:
        # Assume PIL Image
        if img.mode != 'RGB':
            img = img.convert('RGB')
        cv_img = np.array(img)
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    
    # 0. REMOVE RED WATERMARK (@cappersfree) - do this FIRST before any processing
    if remove_watermark:
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
        
        # Red spans across hue 0 and 180 in HSV, need two masks
        # Target: RGB(233, 9, 3) which is pure red
        # HSV red is around hue 0-10 and 170-180
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Dilate mask slightly to catch edges
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.dilate(red_mask, kernel, iterations=1)
        
        # Replace red pixels with white (or could use inpainting)
        cv_img[red_mask > 0] = [255, 255, 255]
    
    # 1. UPSCALE using Lanczos4
    min_width = 1600
    if cv_img.shape[1] < min_width:
        scale = min_width / cv_img.shape[1]
        cv_img = cv2.resize(cv_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Add PADDING
    pad = 50
    cv_img = cv2.copyMakeBorder(cv_img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # 3. Convert to Grayscale - USE RED CHANNEL for best results
    if use_red_channel:
        # Red channel is index 2 in BGR format
        gray = cv_img[:, :, 2]
    else:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    
    # 4. SHARPENING (Unsharp Mask) - before other processing
    if use_sharpen:
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
    
    # 7. DENOISING - Non-Local Means (better but slower) or Bilateral
    if use_nlm_denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    else:
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 8. DESKEW - correct rotation
    if use_deskew:
        gray = deskew_image(gray)
    
    # 9. ADAPTIVE THRESHOLDING (Otsu's method)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 10. Invert if background is dark
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.3:
        binary = cv2.bitwise_not(binary)
    
    # 11. Morphological cleanup
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to PIL
    return Image.fromarray(binary)
