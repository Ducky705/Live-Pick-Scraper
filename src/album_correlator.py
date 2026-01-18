# src/album_correlator.py
"""
Album Correlator: Maps capper names from captions to images in album posts.

Problem:
- User posts 5 images with caption: "@Capper1, @Capper2, @Capper3, @Capper4, @Capper5"
- Each image belongs to a different capper
- Current system treats them as unrelated

Solution:
- Extract capper names from caption (ordered)
- Map each name to corresponding image by position
- Pass this mapping to the AI for correct attribution
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class CapperImageMapping:
    """Mapping between capper names and their image indices."""
    capper_names: List[str]       # Extracted names in order
    image_count: int              # Number of images in album
    mappings: Dict[int, str]      # image_index -> capper_name
    confidence: float             # 0-1 confidence in mapping
    is_album: bool                # True if this is a multi-image album
    raw_caption: str              # Original caption text


class AlbumCorrelator:
    """
    Extracts and correlates capper names from captions to album images.
    
    Detection patterns:
    1. @mention lists: "@Capper1, @Capper2, @Capper3"
    2. Numbered lists: "1. Capper1  2. Capper2  3. Capper3"
    3. Name + emoji separators: "Capper1 🔥 Capper2 🔥 Capper3"
    4. Pipe/dash separators: "Capper1 | Capper2 | Capper3"
    5. Line breaks: "Capper1\nCapper2\nCapper3"
    """
    
    # Common watermarks to EXCLUDE from capper detection
    WATERMARKS = {
        'cappersfree', 'capperstree', 'freepicks', 'vippicks', 
        'bettingpicks', 'freeplays', 'potd', 'lock', 'whale',
        'su', 'card', 'picks', 'plays', 'tips', 'free'
    }
    
    # Patterns for extracting capper names
    MENTION_PATTERN = re.compile(r'@(\w+)', re.IGNORECASE)
    NUMBERED_PATTERN = re.compile(r'(?:^|\n)\s*\d+[.)\-:]\s*(.+?)(?=\n\d+[.)\-:]|\n|$)', re.MULTILINE)
    EMOJI_SEPARATOR = re.compile(r'[\U0001F300-\U0001F9FF]')  # Unicode emoji range
    
    @classmethod
    def extract_and_correlate(
        cls, 
        caption: str, 
        image_paths: List[str],
        channel_name: Optional[str] = None
    ) -> CapperImageMapping:
        """
        Main entry point: Extract capper names and map to images.
        
        Args:
            caption: The message caption/text
            image_paths: List of image paths in album (in order)
            channel_name: Optional channel name for context
            
        Returns:
            CapperImageMapping with extracted names and correlations
        """
        if not caption or not image_paths:
            return cls._empty_mapping(caption, len(image_paths))
        
        image_count = len(image_paths)
        
        # Single image = no correlation needed
        if image_count == 1:
            return cls._single_image_mapping(caption, image_paths)
        
        # Try multiple extraction strategies
        capper_names = cls._extract_capper_names(caption)
        
        if not capper_names:
            return cls._empty_mapping(caption, image_count)
        
        # Correlate names to images
        mappings, confidence = cls._correlate_names_to_images(capper_names, image_count)
        
        return CapperImageMapping(
            capper_names=capper_names,
            image_count=image_count,
            mappings=mappings,
            confidence=confidence,
            is_album=True,
            raw_caption=caption
        )
    
    @classmethod
    def _extract_capper_names(cls, caption: str) -> List[str]:
        """
        Extract capper names from caption using multiple strategies.
        Returns names in order of appearance.
        """
        names = []
        
        # Strategy 1: @mentions (most reliable)
        mentions = cls.MENTION_PATTERN.findall(caption)
        if mentions:
            names = cls._filter_watermarks(mentions)
            if names:
                logging.info(f"[AlbumCorrelator] Extracted {len(names)} names via @mentions")
                return names
        
        # Strategy 2: Numbered list
        numbered = cls.NUMBERED_PATTERN.findall(caption)
        if numbered:
            names = [cls._clean_name(n) for n in numbered]
            names = cls._filter_watermarks(names)
            if names:
                logging.info(f"[AlbumCorrelator] Extracted {len(names)} names via numbered list")
                return names
        
        # Strategy 3: Emoji separators (🔥, ⚡, 💰, etc.)
        if cls.EMOJI_SEPARATOR.search(caption):
            parts = cls.EMOJI_SEPARATOR.split(caption)
            parts = [cls._clean_name(p) for p in parts if p.strip()]
            names = cls._filter_watermarks(parts)
            if names and len(names) > 1:
                logging.info(f"[AlbumCorrelator] Extracted {len(names)} names via emoji separators")
                return names
        
        # Strategy 4: Pipe/dash/comma separators
        for sep in ['|', ' - ', ' / ', ', ']:
            if sep in caption:
                parts = caption.split(sep)
                parts = [cls._clean_name(p) for p in parts if len(p.strip()) > 2]
                names = cls._filter_watermarks(parts)
                if names and len(names) > 1:
                    logging.info(f"[AlbumCorrelator] Extracted {len(names)} names via '{sep}' separator")
                    return names
        
        # Strategy 5: Line breaks
        lines = caption.strip().split('\n')
        lines = [cls._clean_name(l) for l in lines if len(l.strip()) > 2]
        names = cls._filter_watermarks(lines)
        if names and len(names) > 1:
            logging.info(f"[AlbumCorrelator] Extracted {len(names)} names via line breaks")
            return names
        
        return []
    
    @classmethod
    def _clean_name(cls, name: str) -> str:
        """Clean a potential capper name."""
        # Remove common prefixes/suffixes
        name = name.strip()
        name = re.sub(r'^[@#]', '', name)  # Remove @ or #
        name = re.sub(r'\s*\(.*?\)\s*$', '', name)  # Remove trailing (...)
        name = re.sub(r'\s*\[.*?\]\s*$', '', name)  # Remove trailing [...]
        name = re.sub(r'[^\w\s\-_]', '', name)  # Keep only alphanumeric, space, dash, underscore
        return name.strip()
    
    @classmethod
    def _filter_watermarks(cls, names: List[str]) -> List[str]:
        """Remove known watermarks from name list."""
        filtered = []
        for name in names:
            name_lower = name.lower().replace(' ', '').replace('_', '')
            if name_lower and name_lower not in cls.WATERMARKS:
                # Additional heuristics
                if len(name) >= 3 and not name.isdigit():
                    filtered.append(name)
        return filtered
    
    @classmethod
    def _correlate_names_to_images(
        cls, 
        names: List[str], 
        image_count: int
    ) -> Tuple[Dict[int, str], float]:
        """
        Map extracted names to image indices.
        
        Returns (mappings, confidence)
        """
        mappings = {}
        
        # Perfect match: same number of names and images
        if len(names) == image_count:
            for i, name in enumerate(names):
                mappings[i] = name
            return mappings, 1.0
        
        # More names than images: some cappers might share images
        # Map what we can, note the mismatch
        if len(names) > image_count:
            for i in range(image_count):
                mappings[i] = names[i]
            logging.warning(f"[AlbumCorrelator] More names ({len(names)}) than images ({image_count})")
            return mappings, 0.6
        
        # Fewer names than images: some images might not have identified cappers
        if len(names) < image_count:
            for i, name in enumerate(names):
                mappings[i] = name
            logging.warning(f"[AlbumCorrelator] Fewer names ({len(names)}) than images ({image_count})")
            return mappings, 0.7
        
        return mappings, 0.5
    
    @classmethod
    def _empty_mapping(cls, caption: str, image_count: int) -> CapperImageMapping:
        """Return empty mapping when no correlation can be established."""
        return CapperImageMapping(
            capper_names=[],
            image_count=image_count,
            mappings={},
            confidence=0.0,
            is_album=image_count > 1,
            raw_caption=caption or ""
        )
    
    @classmethod
    def _single_image_mapping(cls, caption: str, image_paths: List[str]) -> CapperImageMapping:
        """Handle single-image case."""
        # Try to extract a single capper name
        names = cls._extract_capper_names(caption)
        
        if names:
            return CapperImageMapping(
                capper_names=[names[0]],
                image_count=1,
                mappings={0: names[0]},
                confidence=0.8,
                is_album=False,
                raw_caption=caption
            )
        
        return cls._empty_mapping(caption, 1)


def generate_album_context(
    caption: str,
    ocr_texts: List[str],
    image_paths: List[str],
    channel_name: Optional[str] = None
) -> str:
    """
    Generate enhanced context for AI prompt when processing album posts.
    
    This adds explicit image-to-capper mapping instructions to the prompt.
    """
    correlation = AlbumCorrelator.extract_and_correlate(caption, image_paths, channel_name)
    
    if not correlation.is_album or not correlation.mappings:
        # Single image or no correlation found
        return ""
    
    # Build context string
    lines = [
        "### ALBUM CORRELATION CONTEXT",
        f"This post contains {correlation.image_count} images from an album.",
        f"Caption lists {len(correlation.capper_names)} capper names in order.",
        "",
        "**IMAGE TO CAPPER MAPPING:**"
    ]
    
    for img_idx, capper_name in correlation.mappings.items():
        lines.append(f"- [OCR {img_idx + 1}] belongs to capper: **{capper_name}**")
    
    if len(correlation.capper_names) != correlation.image_count:
        lines.append("")
        lines.append(f"**WARNING:** Name count ({len(correlation.capper_names)}) != image count ({correlation.image_count}). Use visual cues for unmapped images.")
    
    lines.append("")
    lines.append("**INSTRUCTION:** When outputting picks, use the capper name from this mapping for each [OCR N] block.")
    
    return "\n".join(lines)
