import logging
import re

logger = logging.getLogger(__name__)

class MessageChunker:
    """
    Splits long messages into smaller, logical chunks while preserving context headers.
    Essential for improving recall on models with limited attention span/context windows.
    """

    def __init__(self, max_lines=15, overlap=0):
        self.max_lines = max_lines
        self.overlap = overlap

    def chunk_message(self, text: str) -> list[str]:
        """
        Splits a message into chunks.
        
        Algorithm:
        1. Identify "Global Headers" (Capper Name, Unit Size) at the start of the message.
        2. Split the remaining body into chunks of `max_lines`.
        3. Prepend the Global Headers to *every* chunk.
        """
        if not text:
            return []

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if len(lines) <= self.max_lines:
            return [text]

        # 1. Detect Global Headers
        # We assume the first few lines might be headers if they:
        # - Are short (< 40 chars)
        # - Contain special keywords (Units, Capper Name patterns)
        # - Don't look like a bet (No odds like -110, +150)

        headers = []
        body_start_index = 0

        for i, line in enumerate(lines[:5]): # Only check first 5 lines
            if self._is_header_line(line):
                headers.append(line)
                body_start_index = i + 1
            else:
                # If we hit a bet line, stop looking for headers
                break

        # 2. Chunk the Body
        body_lines = lines[body_start_index:]
        chunks = []

        header_text = "\n".join(headers) + "\n" if headers else ""

        # Create separate chunks
        current_chunk = []

        for i, line in enumerate(body_lines):
            current_chunk.append(line)

            # Check if chunk is full
            # But try not to break in the middle of a related block if possible?
            # For iteration 1, strict line count is safer than complex logic
            if len(current_chunk) >= self.max_lines:
                chunk_text = header_text + "\n".join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []

        # Add remaining lines
        if current_chunk:
            chunk_text = header_text + "\n".join(current_chunk)
            chunks.append(chunk_text)

        logger.debug(f"Chunked message into {len(chunks)} parts (Headers: {len(headers)} lines)")
        return chunks

    def _is_header_line(self, line: str) -> bool:
        """
        Determines if a line is likely a header (context) rather than a pick.
        """
        line_upper = line.upper()

        # 1. Check for Odds (If it has odds, it's a PICK, not a header)
        # Regex for -110, +140, 1.95, etc.
        if re.search(r'[+\-]\d{3}', line) or re.search(r'\d\.\d{2}', line):
            return False

        # 2. Check for Keywords
        header_keywords = [
            "UNIT", "PLAY", "SYSTEM", "CAPPER", "PICKS", "CARD", "SLATE",
            "WHALE", "LOCK", "POD", "POTD"
        ]
        if any(k in line_upper for k in header_keywords):
            return True

        # 3. Short lines (Capper Names often short) or Emoji Headers
        # Relaxed length text to 50 chars to catch "Fivestar Sports Picks Channel..."
        if len(line) < 50 and not any(char.isdigit() for char in line):
            return True

        # 4. Starting with Emoji (very common for headers)
        # If it starts with non-alphanumeric (likely emoji) and has no odds
        if not line[0].isalnum() and not re.search(r'\d', line):
            # Check if it's just punctuation like "..." or "---"
            if not all(c in "-=_.*" for c in line):
                return True

        return False
