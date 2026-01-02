# benchmark/metrics.py
"""
Accuracy and Performance Metrics for Model Benchmarking.
ACCURACY IS KING - This module focuses on precise measurement.
"""

import json
import re
from difflib import SequenceMatcher
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from statistics import mean, median, stdev


@dataclass
class PickMatchResult:
    """Result of matching a single extracted pick against expected."""
    expected_pick: Dict[str, Any]
    extracted_pick: Optional[Dict[str, Any]]
    field_scores: Dict[str, float]  # Per-field accuracy (0.0 to 1.0)
    overall_score: float  # Weighted average


@dataclass
class CaseResult:
    """Result of a single test case run."""
    case_id: str
    model: str
    run_index: int
    response_time_ms: float
    parse_success: bool
    error_message: Optional[str]
    expected_count: int
    extracted_count: int
    pick_matches: List[PickMatchResult]
    
    # Aggregate scores
    precision: float = 0.0  # Correct extractions / Total extractions
    recall: float = 0.0     # Correct extractions / Expected picks
    f1_score: float = 0.0   # Harmonic mean of precision & recall
    
    def __post_init__(self):
        if self.parse_success and self.pick_matches:
            # Calculate precision/recall with 0.5 threshold for "correct"
            correct = sum(1 for m in self.pick_matches if m.overall_score >= 0.5)
            self.precision = correct / self.extracted_count if self.extracted_count > 0 else 0.0
            self.recall = correct / self.expected_count if self.expected_count > 0 else 0.0
            if self.precision + self.recall > 0:
                self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)


@dataclass
class ModelResult:
    """Aggregated results for a single model across all test cases."""
    model: str
    case_results: List[CaseResult] = field(default_factory=list)
    
    # Computed metrics
    avg_accuracy: float = 0.0
    avg_f1: float = 0.0
    avg_response_time_ms: float = 0.0
    median_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    total_time_ms: float = 0.0
    parse_success_rate: float = 0.0
    consistency_score: float = 0.0  # How consistent across runs (lower variance = higher)
    
    # Field-level accuracy
    field_accuracy: Dict[str, float] = field(default_factory=dict)
    
    def compute_aggregates(self):
        """Calculate aggregate metrics from case results."""
        if not self.case_results:
            return
            
        successful = [r for r in self.case_results if r.parse_success]
        self.parse_success_rate = len(successful) / len(self.case_results)
        
        if successful:
            # Accuracy metrics (KING)
            f1_scores = [r.f1_score for r in successful]
            self.avg_f1 = mean(f1_scores)
            self.avg_accuracy = mean([r.recall for r in successful])  # Recall = finding all picks
            
            # Time metrics (secondary)
            times = [r.response_time_ms for r in successful]
            self.avg_response_time_ms = mean(times)
            self.median_response_time_ms = median(times)
            self.total_time_ms = sum(times)
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            self.p95_response_time_ms = sorted_times[min(p95_idx, len(sorted_times)-1)]
            
            # Consistency (how stable across runs)
            if len(f1_scores) > 1:
                variance = stdev(f1_scores) if len(f1_scores) > 1 else 0
                self.consistency_score = max(0, 1.0 - variance)  # Lower variance = higher consistency
            else:
                self.consistency_score = 1.0
            
            # Field-level accuracy aggregation
            field_scores = {"cn": [], "lg": [], "ty": [], "p": [], "od": [], "u": []}
            for r in successful:
                for match in r.pick_matches:
                    for field, score in match.field_scores.items():
                        if field in field_scores:
                            field_scores[field].append(score)
            
            self.field_accuracy = {f: mean(scores) if scores else 0.0 for f, scores in field_scores.items()}


def normalize_string(s: str) -> str:
    """Normalize string for comparison."""
    if not s:
        return ""
    # Lowercase, remove extra spaces, normalize common variations
    s = str(s).lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('los angeles', 'la').replace('new york', 'ny')
    return s


def fuzzy_match(s1: str, s2: str) -> float:
    """Fuzzy string matching score (0.0 to 1.0)."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    n1, n2 = normalize_string(s1), normalize_string(s2)
    if n1 == n2:
        return 1.0
    return SequenceMatcher(None, n1, n2).ratio()


def match_odds(expected: Any, extracted: Any) -> float:
    """Match odds values. Handles int, str, and null."""
    if expected is None and extracted is None:
        return 1.0
    if expected is None or extracted is None:
        return 0.5  # Partial credit if one is null
    try:
        e_val = int(str(expected).replace('+', ''))
        x_val = int(str(extracted).replace('+', ''))
        if e_val == x_val:
            return 1.0
        # Partial credit for close odds
        diff = abs(e_val - x_val)
        if diff <= 5:
            return 0.9
        if diff <= 15:
            return 0.7
        if diff <= 30:
            return 0.5
        return 0.0
    except (ValueError, TypeError):
        return fuzzy_match(str(expected), str(extracted))


def match_units(expected: Any, extracted: Any) -> float:
    """Match units values."""
    if expected is None:
        expected = 1.0
    if extracted is None:
        extracted = 1.0
    try:
        e_val = float(str(expected).replace('u', '').strip())
        x_val = float(str(extracted).replace('u', '').strip())
        if abs(e_val - x_val) < 0.01:
            return 1.0
        if abs(e_val - x_val) < 0.5:
            return 0.8
        if abs(e_val - x_val) < 1.0:
            return 0.6
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def match_pick(expected: Dict, extracted: Dict) -> PickMatchResult:
    """
    Match an extracted pick against expected. Returns detailed field scores.
    
    Field weights (ACCURACY IS KING):
    - pick (p): 40% - The actual bet is most important
    - league (lg): 20% - Gets the sport right
    - type (ty): 15% - Spread vs ML vs Total
    - capper_name (cn): 10% - Who made the pick
    - odds (od): 10% - The odds value
    - units (u): 5% - The stake
    """
    field_weights = {
        "p": 0.40,   # Pick is most important
        "lg": 0.20,  # League
        "ty": 0.15,  # Type
        "cn": 0.10,  # Capper name
        "od": 0.10,  # Odds
        "u": 0.05,   # Units
    }
    
    field_scores = {}
    
    # Capper name
    field_scores["cn"] = fuzzy_match(
        expected.get("cn", expected.get("capper_name", "")),
        extracted.get("cn", extracted.get("capper_name", ""))
    )
    
    # League
    exp_lg = expected.get("lg", expected.get("league", ""))
    ext_lg = extracted.get("lg", extracted.get("league", ""))
    field_scores["lg"] = 1.0 if normalize_string(exp_lg) == normalize_string(ext_lg) else 0.0
    
    # Type
    exp_ty = expected.get("ty", expected.get("type", ""))
    ext_ty = extracted.get("ty", extracted.get("type", ""))
    field_scores["ty"] = 1.0 if normalize_string(exp_ty) == normalize_string(ext_ty) else fuzzy_match(exp_ty, ext_ty)
    
    # Pick (THE MOST IMPORTANT)
    exp_p = expected.get("p", expected.get("pick", ""))
    ext_p = extracted.get("p", extracted.get("pick", ""))
    field_scores["p"] = fuzzy_match(exp_p, ext_p)
    
    # Odds
    field_scores["od"] = match_odds(
        expected.get("od", expected.get("odds")),
        extracted.get("od", extracted.get("odds"))
    )
    
    # Units
    field_scores["u"] = match_units(
        expected.get("u", expected.get("units")),
        extracted.get("u", extracted.get("units"))
    )
    
    # Calculate weighted overall score
    overall = sum(field_scores[f] * field_weights[f] for f in field_weights)
    
    return PickMatchResult(
        expected_pick=expected,
        extracted_pick=extracted,
        field_scores=field_scores,
        overall_score=overall
    )


def match_picks_for_case(expected_picks: List[Dict], extracted_picks: List[Dict]) -> List[PickMatchResult]:
    """
    Match extracted picks to expected picks using best-match pairing.
    Uses Hungarian algorithm approximation for optimal matching.
    """
    if not expected_picks:
        return []
    
    results = []
    used_extracted = set()
    
    for expected in expected_picks:
        best_match = None
        best_score = -1
        best_idx = -1
        
        for i, extracted in enumerate(extracted_picks):
            if i in used_extracted:
                continue
            
            match = match_pick(expected, extracted)
            if match.overall_score > best_score:
                best_score = match.overall_score
                best_match = match
                best_idx = i
        
        if best_match and best_score > 0.2:  # Lowered threshold for partial matches
            results.append(best_match)
            used_extracted.add(best_idx)
        else:
            # No match found - record as missed expected pick
            results.append(PickMatchResult(
                expected_pick=expected,
                extracted_pick=None,
                field_scores={"cn": 0, "lg": 0, "ty": 0, "p": 0, "od": 0, "u": 0},
                overall_score=0.0
            ))
    
    return results


def parse_ai_response(response: str) -> List[Dict]:
    """Parse AI response JSON to list of picks."""
    if not response:
        return []
    
    try:
        # Clean response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()
        
        data = json.loads(clean)
        
        # Handle various response formats
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "picks" in data:
                return data["picks"]
            # Single pick as dict
            return [data]
        return []
    except json.JSONDecodeError:
        return []


def calculate_composite_score(model_result: ModelResult) -> float:
    """
    Calculate final composite score for ranking.
    ACCURACY IS KING (85%), Time is secondary (15%).
    """
    accuracy_weight = 0.85
    time_weight = 0.15
    
    # Accuracy component (0-100 scale)
    accuracy_score = (
        model_result.avg_f1 * 0.5 +  # F1 score
        model_result.avg_accuracy * 0.3 +  # Recall (finding all picks)
        model_result.parse_success_rate * 0.1 +  # Didn't fail
        model_result.consistency_score * 0.1  # Consistent results
    ) * 100
    
    # Time component (faster = better, normalize to 0-100)
    # Assuming 120s is the worst case, 1s is the best
    max_time = 120000  # 120 seconds in ms
    time_normalized = max(0, 1 - (model_result.avg_response_time_ms / max_time))
    time_score = time_normalized * 100
    
    return accuracy_weight * accuracy_score + time_weight * time_score
