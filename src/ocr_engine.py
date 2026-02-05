# src/ocr_engine.py
"""
RapidOCR Engine Wrapper.

Provides a unified interface to the RapidOCR (ONNX-based PaddleOCR) engine.
This replaces Tesseract for significantly improved accuracy on complex images.

Key Features:
- Lazy initialization (engine loads only when first used)
- Singleton pattern to avoid reloading models
- Handles numpy arrays, PIL images, and file paths
- Returns text with optional confidence scores
"""

import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class RapidOCREngine:
    """
    Singleton wrapper for RapidOCR.

    Usage:
        engine = RapidOCREngine.get_instance()
        text = engine.extract_text(image)
        text, confidence = engine.extract_text_with_confidence(image)
    """

    _instance = None
    _engine = None
    _initialized = False

    @classmethod
    def get_instance(cls) -> "RapidOCREngine":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = RapidOCREngine()
        return cls._instance

    def __init__(self):
        """Initialize engine on first access."""
        if not RapidOCREngine._initialized:
            self._initialize_engine()
            RapidOCREngine._initialized = True

    def _initialize_engine(self):
        """
        Lazy load RapidOCR to avoid import overhead.
        Falls back gracefully if not installed.
        """
        try:
            from rapidocr_onnxruntime import RapidOCR

            # Initialize with optimized settings for betting slips
            # - text_score: Lower threshold to catch faint text
            # - use_angle_cls: Disabled (betting slips are upright)
            self._engine = RapidOCR()

            logger.info("[RapidOCR] Engine initialized successfully (ONNX Runtime)")

        except ImportError:
            logger.error(
                "[RapidOCR] rapidocr-onnxruntime not installed. Install with: pip install rapidocr-onnxruntime"
            )
            self._engine = None
        except Exception as e:
            logger.error(f"[RapidOCR] Failed to initialize: {e}")
            self._engine = None

    def is_available(self) -> bool:
        """Check if the engine is ready to use."""
        return self._engine is not None

    def _prepare_image(self, img: str | np.ndarray | Image.Image) -> np.ndarray | None:
        """
        Convert input to numpy array in BGR format (OpenCV standard).

        Args:
            img: File path, numpy array (BGR), or PIL Image (RGB)

        Returns:
            numpy array in BGR format, or None on error
        """
        try:
            if isinstance(img, str):
                # File path - let RapidOCR handle it directly
                return img

            if isinstance(img, Image.Image):
                # PIL Image (RGB) -> numpy BGR
                import cv2

                arr = np.array(img)
                if len(arr.shape) == 3 and arr.shape[2] == 3:
                    arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                return arr

            if isinstance(img, np.ndarray):
                # Already numpy, assume BGR (OpenCV standard)
                return img

            logger.warning(f"[RapidOCR] Unsupported image type: {type(img)}")
            return None

        except Exception as e:
            logger.error(f"[RapidOCR] Image preparation failed: {e}")
            return None

    def extract_text(self, img: str | np.ndarray | Image.Image) -> str:
        """
        Extract all text from an image.

        Args:
            img: Image as file path, numpy array (BGR), or PIL Image

        Returns:
            Combined text string with lines separated by newlines
        """
        if not self.is_available():
            logger.warning("[RapidOCR] Engine not available, returning empty string")
            return ""

        prepared = self._prepare_image(img)
        if prepared is None:
            return ""

        try:
            # RapidOCR returns: (result, elapse_time)
            # result format: [[box_coords, text, confidence], ...]
            result, _ = self._engine(prepared)

            if not result:
                return ""

            # Extract text from each detection, sorted by vertical position
            # This preserves reading order (top to bottom)
            detections = []
            for item in result:
                box = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = item[1]
                # Use top-left Y coordinate for sorting
                y_pos = min(pt[1] for pt in box)
                detections.append((y_pos, text))

            # Sort by Y position (top to bottom)
            detections.sort(key=lambda x: x[0])

            # Combine texts
            texts = [d[1] for d in detections]
            return "\n".join(texts)

        except Exception as e:
            logger.error(f"[RapidOCR] Text extraction failed: {e}")
            return ""

    def extract_text_with_confidence(self, img: str | np.ndarray | Image.Image) -> tuple[str, float]:
        """
        Extract text with average confidence score.

        Args:
            img: Image as file path, numpy array (BGR), or PIL Image

        Returns:
            Tuple of (combined_text, average_confidence)
            Confidence is 0.0-1.0
        """
        if not self.is_available():
            return "", 0.0

        prepared = self._prepare_image(img)
        if prepared is None:
            return "", 0.0

        try:
            result, _ = self._engine(prepared)

            if not result:
                return "", 0.0

            detections = []
            confidences = []

            for item in result:
                box = item[0]
                text = item[1]
                conf = item[2]
                y_pos = min(pt[1] for pt in box)
                detections.append((y_pos, text))
                confidences.append(conf)

            detections.sort(key=lambda x: x[0])
            texts = [d[1] for d in detections]

            full_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return full_text, avg_confidence

        except Exception as e:
            logger.error(f"[RapidOCR] Extraction failed: {e}")
            return "", 0.0

    def extract_text_with_boxes(self, img: str | np.ndarray | Image.Image) -> list[dict]:
        """
        Extract text with bounding box information.
        Useful for layout analysis.

        Args:
            img: Image as file path, numpy array (BGR), or PIL Image

        Returns:
            List of dicts: [{"text": str, "box": [[x,y],...], "confidence": float}, ...]
        """
        if not self.is_available():
            return []

        prepared = self._prepare_image(img)
        if prepared is None:
            return []

        try:
            result, _ = self._engine(prepared)

            if not result:
                return []

            detections = []
            for item in result:
                detections.append({"box": item[0], "text": item[1], "confidence": item[2]})

            # Sort by vertical position
            detections.sort(key=lambda d: min(pt[1] for pt in d["box"]))

            return detections

        except Exception as e:
            logger.error(f"[RapidOCR] Box extraction failed: {e}")
            return []


# Module-level convenience functions
def get_ocr_engine() -> RapidOCREngine:
    """Get the singleton OCR engine instance."""
    return RapidOCREngine.get_instance()


def extract_text(img: str | np.ndarray | Image.Image) -> str:
    """Quick access to text extraction."""
    return get_ocr_engine().extract_text(img)


def extract_text_with_confidence(img: str | np.ndarray | Image.Image) -> tuple[str, float]:
    """Quick access to text extraction with confidence."""
    return get_ocr_engine().extract_text_with_confidence(img)
