import logging
import re
from datetime import datetime

class Deduplicator:
    @staticmethod
    def normalize_text(text):
        """
        Normalize text for comparison:
        - Lowercase
        - Remove whitespace
        - Remove special characters
        """
        if not text: return ""
        # Keep only alphanumeric
        return re.sub(r'[^a-z0-9]', '', text.lower())

    @staticmethod
    def is_same_date(date_str1, date_str2):
        """
        Check if two date strings represent the same day.
        Format expected: "YYYY-MM-DD HH:MM ET"
        """
        try:
            d1 = date_str1.split(' ')[0]
            d2 = date_str2.split(' ')[0]
            return d1 == d2
        except:
            return False

    @staticmethod
    def merge_messages(messages):
        """
        Deduplicate messages from mixed sources (Telegram, Twitter).
        
        Logic:
        1. Group by Capper Name (normalized)
        2. Within Capper, compare messages on the same date.
        3. If texts are very similar OR exact image match (not implemented here, assuming text/content prox), treat as duplicate.
        4. Strategy: Keep the one with MORE info (e.g. has image > no image, longer text > shorter text).
        """
        
        # 1. Group by Capper
        grouped = {}
        for msg in messages:
            # Normalize capper name
            # Twitter names are usually clean. Telegram might be channel name.
            # We try to map them if possible, or just strict match.
            c_name = msg.get('capper_name', 'Unknown')
            if not c_name: c_name = msg.get('channel_name', 'Unknown')
            
            # Simple normalization of capper name
            clean_name = re.sub(r'[^a-z0-9]', '', c_name.lower())
            
            if clean_name not in grouped:
                grouped[clean_name] = []
            grouped[clean_name].append(msg)
            
        final_list = []
        
        for capper, msgs in grouped.items():
            # If only one message for this capper, keep it
            if len(msgs) == 1:
                final_list.append(msgs[0])
                continue
                
            # Compare within capper
            # We'll use a simple "consumed" set
            consumed_indices = set()
            
            for i in range(len(msgs)):
                if i in consumed_indices: continue
                
                base_msg = msgs[i]
                best_version = base_msg
                
                # Compare with subsequent messages
                for j in range(i + 1, len(msgs)):
                    if j in consumed_indices: continue
                    
                    candidate = msgs[j]
                    
                    # CHECK 1: Must be same date
                    if not Deduplicator.is_same_date(base_msg.get('date', ''), candidate.get('date', '')):
                        continue
                        
                    # CHECK 2: Content Similarity
                    # If both have images, we assume they might be the same if from same capper on same day?
                    # That's risky. Cappers post multiple picks.
                    # We need text similarity or just "duplicate post" detection.
                    
                    text1 = Deduplicator.normalize_text(base_msg.get('text', ''))
                    text2 = Deduplicator.normalize_text(candidate.get('text', ''))
                    
                    is_duplicate = False
                    
                    # A. Exact Text Match (or subset)
                    if text1 and text2:
                        if text1 == text2 or (len(text1) > 20 and text1 in text2) or (len(text2) > 20 and text2 in text1):
                            is_duplicate = True
                    
                    # B. If texts are empty but both have images?
                    # Hard to say without vision comparison. 
                    # For now, we only dedupe if text overlaps significantly.
                    
                    if is_duplicate:
                        consumed_indices.add(j)
                        
                        # DECIDE WHICH TO KEEP
                        # 1. Prefer Image over No Image
                        base_has_img = bool(best_version.get('images') or best_version.get('image'))
                        cand_has_img = bool(candidate.get('images') or candidate.get('image'))
                        
                        if cand_has_img and not base_has_img:
                            best_version = candidate
                        elif cand_has_img == base_has_img:
                            # 2. Prefer longer text
                            if len(candidate.get('text', '')) > len(best_version.get('text', '')):
                                best_version = candidate
                                
                final_list.append(best_version)
                
        logging.info(f"Deduplication: Reduced {len(messages)} -> {len(final_list)} messages.")
        return final_list
