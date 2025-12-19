import difflib
from src.supabase_client import get_capper_cache, get_or_create_capper_id

class CapperMatcher:
    def __init__(self):
        pass

    def match_name(self, raw_name, limit=5):
        """
        Returns a list of matches:
        [
            {'name': 'Canonical Name', 'score': 100, 'type': 'exact', 'id': 1},
            {'name': 'Canonical Name', 'score': 85, 'type': 'fuzzy_variant', 'id': 1}
        ]
        """
        if not raw_name: return []
        
        raw_lower = str(raw_name).lower().strip()
        capper_map, variant_map = get_capper_cache()
        
        matches = []
        
        # 1. Exact Match (Canonical)
        if raw_lower in capper_map:
            # Reconstruct original case if possible, but map only has ID.
            # We'll return title case for display
            matches.append({
                'name': raw_lower.title(),
                'score': 100,
                'type': 'exact_canonical',
                'id': capper_map[raw_lower]
            })
            return matches

        # 2. Exact Match (Variant)
        if raw_lower in variant_map:
            capper_id = variant_map[raw_lower]
            # Find canonical name for this ID
            canonical = next((k for k, v in capper_map.items() if v == capper_id), "Unknown")
            matches.append({
                'name': canonical.title(),
                'score': 100,
                'type': 'exact_variant',
                'id': capper_id
            })
            return matches

        # 3. Fuzzy Match
        # We search against both canonical names and variants
        candidates = list(capper_map.keys()) + list(variant_map.keys())
        
        # Difflib get_close_matches is good but doesn't return scores easily.
        # We will iterate and map ratio.
        
        scored = []
        for cand in candidates:
            ratio = difflib.SequenceMatcher(None, raw_lower, cand).ratio()
            if ratio > 0.4: # Filter garbage
                score = int(ratio * 100)
                
                # Resolve ID
                if cand in capper_map:
                    cid = capper_map[cand]
                    cname = cand
                else:
                    cid = variant_map[cand]
                    cname = next((k for k, v in capper_map.items() if v == cid), cand)
                
                # Check if we already have this capper in list (deduplicate by ID, keep highest score)
                existing = next((x for x in scored if x['id'] == cid), None)
                if existing:
                    if score > existing['score']:
                        existing['score'] = score
                else:
                    scored.append({
                        'name': cname.title(),
                        'score': score,
                        'type': 'fuzzy',
                        'id': cid
                    })
        
        # Sort by score desc, then name
        scored.sort(key=lambda x: (-x['score'], x['name']))
        
        return scored[:limit]

    def match_names_bulk(self, names):
        results = {}
        unique_names = set(str(n).strip() for n in names if n)
        for name in unique_names:
            results[name] = self.match_name(name)
        return results

capper_matcher = CapperMatcher()
