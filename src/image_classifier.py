
import logging
import os

import cv2
import numpy as np

logger = logging.getLogger(__name__)

class ImageClassifier:
    """
    Classifies images to determine if they are potential betting slips
    before running expensive OCR.
    """

    @staticmethod
    def is_betting_slip(image_path: str) -> bool:
        """
        Heuristic check to see if image is likely a betting slip.
        Betting slips usually have:
        1. High text density (edges)
        2. Reasonable variance (not a solid color)
        3. Specific aspect ratios (usually vertical for mobile screenshots) - optional
        """
        try:
            if not os.path.exists(image_path):
                return False

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False

            # 1. Check Variance (Skip solid colors/blank images)
            variance = cv2.meanStdDev(img)[1]**2
            if variance[0][0] < 100: # Threshold for very low contrast/blank images
                logger.debug(f"Image rejected: Low variance ({variance[0][0]:.2f})")
                return False

            # 2. Edge Density (Canny) - Proxy for text density
            edges = cv2.Canny(img, 100, 200)
            edge_density = np.count_nonzero(edges) / edges.size

            # Text-heavy images usually have higher edge density than memes/photos
            # Betting slips are effectively lists of text.
            if edge_density < 0.02: # < 2% edges is likely an object/face/photo without much text
                logger.debug(f"Image rejected: Low edge density ({edge_density:.4f})")
                return False

            return True

        except Exception as e:
            logger.error(f"Error in image classifier: {e}")
            # Fail open (allow OCR if check fails)
            return True

# Singleton/Convenience
classifier = ImageClassifier()
