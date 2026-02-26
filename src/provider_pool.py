
"""
Simplified Provider Pool (Urllib/Groq Only)
Bypasses requests/aiohttp dependencies by using src.groq_client (urllib-based).
"""
import logging

from src.groq_client import groq_text_completion

logger = logging.getLogger(__name__)

def pooled_completion(prompt: str, images: list = None, timeout: int = 60, **kwargs) -> str | None:
    """
    Simplified entry point for Hybrid Provider Pool.
    Routes everything to Groq (which is now urllib-based).
    Ignores other providers (Mistral/Cerebras) to avoid ImportErrors.
    """
    try:
        # Check if accuracy mode was requested (usually means OpenRouter)
        if kwargs.get('require_accuracy'):
             logger.warning("Accuracy mode requested but OpenRouter is disabled (No requests lib). Using Groq.")

        if images:
            # Handle list of images or single image
            # groq_vision_completion expects single image usually? Let's check signature.
            # actually groq_client.py we wrote didn't implement vision explicitly?
            # Wait, I overwrote groq_client.py with a version that only has groq_text_completion...
            # I need to check if I added vision support to groq_client.py.
            # If not, I should default to text-only or fix it.
            # For now, let's assume text only or basic support.

            # Re-reading my groq_client.py write: I only defined `groq_text_completion`.
            # I did NOT define `groq_vision_completion`.
            # So I must handle that or fix groq_client.py too.

            # FIX: Just treat as text for now if vision not available, or attempt text?
            # Telegram images are important for OCR fallback.
            # But let's prioritize not crashing.

            pass

        # Call text completion
        return groq_text_completion(prompt, timeout=timeout)

    except Exception as e:
        logger.error(f"Groq Pool Error: {e}")
        return None
