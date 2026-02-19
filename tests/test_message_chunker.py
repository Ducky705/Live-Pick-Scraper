
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.utils.message_chunker import MessageChunker

class TestMessageChunker(unittest.TestCase):

    def test_short_message_no_chunking(self):
        chunker = MessageChunker(max_lines=10)
        text = "This is a short message.\nLine 2.\nLine 3."
        chunks = chunker.chunk_message(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_message_chunking(self):
        chunker = MessageChunker(max_lines=3)
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        chunks = chunker.chunk_message(text)
        self.assertEqual(len(chunks), 2)
        # First chunk should have 3 lines
        self.assertEqual(chunks[0], "Line 1\nLine 2\nLine 3")
        # Second chunk should have 2 lines
        self.assertEqual(chunks[1], "Line 4\nLine 5")

    def test_header_preservation(self):
        chunker = MessageChunker(max_lines=3)
        text = "Capper: TestGuy\nUnits: 1u\nPick 1\nPick 2\nPick 3\nPick 4"
        # Lines:
        # 0: Capper (Header)
        # 1: Units (Header)
        # Body starts at Pick 1
        
        chunks = chunker.chunk_message(text)
        
        # Expected:
        # Chunk 1: Headers + Pick 1, Pick 2, Pick 3
        # Chunk 2: Headers + Pick 4
        
        self.assertEqual(len(chunks), 2)
        
        self.assertIn("Capper: TestGuy", chunks[0])
        self.assertIn("Pick 1", chunks[0])
        
        self.assertIn("Capper: TestGuy", chunks[1])
        self.assertIn("Pick 4", chunks[1])

    def test_header_detection_with_picks_at_start(self):
        chunker = MessageChunker(max_lines=3)
        text = "Lakers -5 (-110)\nBulls +3\nCeltics -2"
        # Should detect NO headers because line 1 has odds
        chunks = chunker.chunk_message(text)
        
        self.assertEqual(len(chunks), 1) # 3 lines <= 3 max lines
        
        # Test forced split
        chunker_small = MessageChunker(max_lines=2)
        chunks = chunker_small.chunk_message(text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "Lakers -5 (-110)\nBulls +3")
        # Second chunk should NOT have Lakers line prepended because it wasn't a header
        self.assertEqual(chunks[1], "Celtics -2")

if __name__ == '__main__':
    unittest.main()
