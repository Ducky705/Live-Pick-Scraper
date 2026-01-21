# src/image_classifier.py
"""
Smart Image Classifier for OCR Routing.

Analyzes image characteristics to determine the optimal OCR strategy:
- TESSERACT_LIKELY: Clean document-style images (sportsbook screenshots, receipts)
- VISION_AI_REQUIRED: Stylized cards, overlays, multi-section layouts, dark backgrounds

This replaces the naive "2 keyword" threshold with visual heuristics.
"""

import cv2
import numpy as np
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, List, Optional


class OCRStrategy(Enum):
    """Recommended OCR strategy for an image."""
    TESSERACT_LIKELY = "tesseract"      # Clean, high-contrast, document-like
    VISION_AI_REQUIRED = "vision_ai"    # Complex, styled, multi-section


@dataclass
class ImageAnalysis:
    """Analysis results for an image."""
    strategy: OCRStrategy
    confidence: float  # 0-1
    reasons: List[str]
    
    # Detailed metrics
    is_dark_background: bool
    has_gradients: bool
    has_multiple_sections: bool
    has_styled_text: bool
    has_overlays: bool
    color_complexity: float  # 0-1


class ImageClassifier:
    """
    Analyzes images to determine optimal OCR routing.
    
    Key heuristics:
    1. Background darkness (dark bg = harder for Tesseract)
    2. Color complexity (gradients, multiple colors = styled)
    3. Edge density (lots of edges = complex layout)
    4. Section detection (multiple distinct regions = multi-capper)
    5. Text contrast ratio (low contrast = AI needed)
    """
    
    # Thresholds (tuned for betting card images)
    DARK_BG_THRESHOLD = 80          # Mean brightness below this = dark
    GRADIENT_VARIANCE_THRESHOLD = 1500  # High variance = gradients
    EDGE_DENSITY_THRESHOLD = 0.15   # Edge pixels / total pixels
    COLOR_COMPLEXITY_THRESHOLD = 0.6
    SECTION_MIN_HEIGHT = 50         # Minimum height for a distinct section
    
    @classmethod
    def classify(cls, image_path: str) -> ImageAnalysis:
        """
        Analyze an image and recommend OCR strategy.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ImageAnalysis with strategy recommendation and detailed metrics
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return cls._default_vision_ai("Could not read image")
            
            return cls._analyze_image(img)
            
        except Exception as e:
            logging.warning(f"[ImageClassifier] Analysis failed: {e}")
            return cls._default_vision_ai(f"Analysis error: {e}")
    
    @classmethod
    def classify_from_array(cls, img: np.ndarray) -> ImageAnalysis:
        """Classify from an already-loaded numpy array (BGR format)."""
        try:
            return cls._analyze_image(img)
        except Exception as e:
            logging.warning(f"[ImageClassifier] Analysis failed: {e}")
            return cls._default_vision_ai(f"Analysis error: {e}")
    
    @classmethod
    def _analyze_image(cls, img: np.ndarray) -> ImageAnalysis:
        """Core analysis logic."""
        reasons = []
        
        # Convert to grayscale for some analyses
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. BACKGROUND DARKNESS
        mean_brightness = np.mean(gray)
        is_dark = mean_brightness < cls.DARK_BG_THRESHOLD
        if is_dark:
            reasons.append(f"Dark background (brightness={mean_brightness:.0f})")
        
        # 2. GRADIENT DETECTION (high variance in brightness)
        brightness_variance = np.var(gray)
        has_gradients = brightness_variance > cls.GRADIENT_VARIANCE_THRESHOLD
        if has_gradients:
            reasons.append(f"Gradients detected (variance={brightness_variance:.0f})")
        
        # 3. EDGE DENSITY (complex layouts have more edges)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        is_complex_layout = edge_density > cls.EDGE_DENSITY_THRESHOLD
        if is_complex_layout:
            reasons.append(f"Complex layout (edge_density={edge_density:.2%})")
        
        # 4. COLOR COMPLEXITY (betting cards often have multiple colors)
        color_complexity = cls._calculate_color_complexity(img)
        is_colorful = color_complexity > cls.COLOR_COMPLEXITY_THRESHOLD
        if is_colorful:
            reasons.append(f"High color complexity ({color_complexity:.2f})")
        
        # 5. MULTI-SECTION DETECTION (horizontal lines separating cappers)
        has_multiple_sections, section_count = cls._detect_sections(gray)
        if has_multiple_sections:
            reasons.append(f"Multiple sections detected ({section_count} regions)")
        
        # 6. STYLED TEXT DETECTION (non-standard fonts, decorations)
        # We detect this by looking for low text contrast or unusual patterns
        has_styled_text = cls._detect_styled_text(gray, edges)
        if has_styled_text:
            reasons.append("Styled/decorative text detected")
        
        # 7. OVERLAY DETECTION (watermarks, logos)
        has_overlays = cls._detect_overlays(img, gray)
        if has_overlays:
            reasons.append("Overlays/watermarks detected")
        
        # DECISION LOGIC
        # Count "vision AI" indicators
        vision_indicators = sum([
            is_dark,
            has_gradients,
            is_complex_layout,
            is_colorful,
            has_multiple_sections,
            has_styled_text,
            has_overlays
        ])
        
        # Weighted scoring
        score = 0.0
        if is_dark:
            score += 0.25  # Dark backgrounds are very hard for Tesseract
        if has_gradients:
            score += 0.15
        if is_complex_layout:
            score += 0.15
        if is_colorful:
            score += 0.10
        if has_multiple_sections:
            score += 0.20  # Multi-capper = critical to get right
        if has_styled_text:
            score += 0.15
        if has_overlays:
            score += 0.10
        
        # Normalize to 0-1 confidence
        confidence = min(1.0, score / 0.7)  # 0.7 is "definitely vision AI"
        
        # Decision: If score > 0.2, use Vision AI (lowered from 0.3)
        # Dark backgrounds alone should trigger Vision AI since Tesseract struggles
        if score > 0.2 or vision_indicators >= 2:
            strategy = OCRStrategy.VISION_AI_REQUIRED
        else:
            strategy = OCRStrategy.TESSERACT_LIKELY
            confidence = 1.0 - confidence  # Invert for Tesseract confidence
            if not reasons:
                reasons.append("Clean document-style image")
        
        return ImageAnalysis(
            strategy=strategy,
            confidence=confidence,
            reasons=reasons,
            is_dark_background=is_dark,
            has_gradients=has_gradients,
            has_multiple_sections=has_multiple_sections,
            has_styled_text=has_styled_text,
            has_overlays=has_overlays,
            color_complexity=color_complexity
        )
    
    @classmethod
    def _calculate_color_complexity(cls, img: np.ndarray) -> float:
        """
        Calculate color complexity using histogram analysis.
        Returns 0-1 where 1 = very colorful/complex.
        """
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Calculate hue histogram (ignoring very dark/light pixels)
        mask = (hsv[:, :, 2] > 30) & (hsv[:, :, 2] < 225)  # Avoid black/white
        
        if not np.any(mask):
            return 0.0
        
        hue_values = hsv[:, :, 0][mask]
        
        # Count unique hue bins (divided into 18 bins of 10 degrees each)
        hist, _ = np.histogram(hue_values, bins=18, range=(0, 180))
        
        # Normalize and calculate entropy-like metric
        hist_normalized = hist / hist.sum() if hist.sum() > 0 else hist
        
        # Count significant bins (> 5% of pixels)
        significant_bins = np.sum(hist_normalized > 0.05)
        
        # Normalize to 0-1 (1-2 bins = simple, 6+ bins = complex)
        return min(1.0, (significant_bins - 1) / 5)
    
    @classmethod
    def _detect_sections(cls, gray: np.ndarray) -> Tuple[bool, int]:
        """
        Detect if image has multiple distinct horizontal sections.
        This is crucial for multi-capper cards.
        
        Returns (has_sections, count)
        """
        height, width = gray.shape
        
        # Look for horizontal lines (potential section dividers)
        # Use Sobel to find horizontal edges
        sobel_h = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_h = np.abs(sobel_h)
        
        # Project onto Y-axis (sum across width)
        row_projection = np.sum(sobel_h, axis=1)
        
        # Normalize
        row_projection = row_projection / row_projection.max() if row_projection.max() > 0 else row_projection
        
        # Find peaks (potential section boundaries)
        # A peak is where the projection is > 0.3 of max
        threshold = 0.3
        peaks = np.where(row_projection > threshold)[0]
        
        if len(peaks) == 0:
            return False, 1
        
        # Cluster peaks into distinct boundaries
        # (peaks close together are the same boundary)
        boundaries = []
        current_cluster = [peaks[0]]
        
        for p in peaks[1:]:
            if p - current_cluster[-1] < 20:  # Within 20px = same boundary
                current_cluster.append(p)
            else:
                boundaries.append(int(np.mean(current_cluster)))
                current_cluster = [p]
        boundaries.append(int(np.mean(current_cluster)))
        
        # Filter boundaries that are too close to edges
        margin = height * 0.1
        boundaries = [b for b in boundaries if margin < b < height - margin]
        
        # Count sections (boundaries + 1)
        section_count = len(boundaries) + 1
        
        # Validate: each section should be at least SECTION_MIN_HEIGHT
        if section_count > 1:
            # Check if boundaries create reasonably sized sections
            all_bounds = [0] + boundaries + [height]
            min_section = min(all_bounds[i+1] - all_bounds[i] for i in range(len(all_bounds)-1))
            
            if min_section < cls.SECTION_MIN_HEIGHT:
                # Sections too small, likely noise
                return False, 1
        
        return section_count > 1, section_count
    
    @classmethod
    def _detect_styled_text(cls, gray: np.ndarray, edges: np.ndarray) -> bool:
        """
        Detect if the image likely contains styled/decorative text.
        Styled text has irregular edge patterns compared to clean fonts.
        """
        # Calculate local edge density variance
        # Styled text has more variable edge density
        
        # Divide image into a grid
        h, w = gray.shape
        grid_size = 50
        
        densities = []
        for y in range(0, h - grid_size, grid_size):
            for x in range(0, w - grid_size, grid_size):
                cell = edges[y:y+grid_size, x:x+grid_size]
                density = np.sum(cell > 0) / cell.size
                densities.append(density)
        
        if len(densities) < 4:
            return False
        
        # High variance in local edge density = styled text
        density_variance = np.var(densities)
        
        return density_variance > 0.01
    
    @classmethod
    def _detect_overlays(cls, img: np.ndarray, gray: np.ndarray) -> bool:
        """
        Detect overlays like watermarks or logos.
        These are often semi-transparent or in specific colors (red watermarks).
        """
        # Check for red channel dominance (common watermark color)
        b, g, r = cv2.split(img)
        
        # Red watermark detection (same logic as in preprocess_image_v3)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # If more than 0.5% of pixels are red, likely a watermark
        red_ratio = np.sum(red_mask > 0) / red_mask.size
        
        if red_ratio > 0.005:
            return True
        
        # Check for semi-transparent overlays (uniform brightness bands)
        # This is a simplified heuristic
        row_means = np.mean(gray, axis=1)
        sudden_changes = np.abs(np.diff(row_means))
        
        # If there are sudden uniform changes, might be overlay
        return np.max(sudden_changes) > 50
    
    @classmethod
    def _default_vision_ai(cls, reason: str) -> ImageAnalysis:
        """Return a default Vision AI recommendation when analysis fails."""
        return ImageAnalysis(
            strategy=OCRStrategy.VISION_AI_REQUIRED,
            confidence=0.5,
            reasons=[reason],
            is_dark_background=False,
            has_gradients=False,
            has_multiple_sections=False,
            has_styled_text=False,
            has_overlays=False,
            color_complexity=0.0
        )


def should_use_vision_ai(image_path: str) -> bool:
    """
    Simple helper function for quick routing decisions.
    Returns True if Vision AI should be used, False for Tesseract.
    """
    analysis = ImageClassifier.classify(image_path)
    return analysis.strategy == OCRStrategy.VISION_AI_REQUIRED
