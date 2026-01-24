import rapidfuzz
from rapidfuzz import process, fuzz


class CapperMatcher:
    def __init__(self):
        pass

    def match_name(self, raw_name, candidates, limit=5, threshold=90):
        """
        Returns a list of matches based on strict fuzzy matching rules.

        Args:
            raw_name (str): The name to match.
            candidates (list): List of dicts [{'name': 'Canonical', 'id': 1, 'type': 'canonical'|'variant', 'is_active': bool}].
            limit (int): Max number of results.
            threshold (int): Minimum score (0-100) to consider a match.

        Returns:
            list: List of dicts.
        """
        if not raw_name or not candidates:
            return []

        raw_lower = str(raw_name).lower().strip()
        matches = []

        # Optimize: Create name map for quick lookup
        # We process candidates to ensure keys are lowercase
        name_to_candidate = {}
        for c in candidates:
            k = c["name"].lower().strip()
            # Prioritize canonical if duplicates exist in list (shouldn't happen if list is well formed)
            if k not in name_to_candidate:
                name_to_candidate[k] = c
            elif c.get("type") == "canonical":
                name_to_candidate[k] = c

        # 1. Exact Match
        if raw_lower in name_to_candidate:
            cand = name_to_candidate[raw_lower]
            matches.append(
                {
                    "name": cand["name"],
                    "score": 100,
                    "type": f"exact_{cand.get('type', 'canonical')}",
                    "id": cand["id"],
                    "is_active": cand.get("is_active", False),
                }
            )
            return matches

        # 2. Fuzzy Match
        choices = list(name_to_candidate.keys())

        # Use WRatio as it handles partial matches and case well
        raw_matches = process.extract(
            raw_lower, choices, scorer=fuzz.WRatio, limit=limit, score_cutoff=threshold
        )

        for match_name, score, _ in raw_matches:
            cand = name_to_candidate[match_name]

            # Deduplicate by ID (keep highest score)
            existing = next((x for x in matches if x["id"] == cand["id"]), None)

            if existing:
                if score > existing["score"]:
                    existing["score"] = score
                    existing["name"] = cand["name"]
            else:
                matches.append(
                    {
                        "name": cand["name"],
                        "score": score,
                        "type": "fuzzy",
                        "id": cand["id"],
                        "is_active": cand.get("is_active", False),
                    }
                )

        # Sort by score desc
        matches.sort(key=lambda x: -x["score"])

        return matches

    def match_names_bulk(self, names, candidates):
        results = {}
        unique_names = set(str(n).strip() for n in names if n)
        for name in unique_names:
            results[name] = self.match_name(name, candidates)
        return results


capper_matcher = CapperMatcher()
