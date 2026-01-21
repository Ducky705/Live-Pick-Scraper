# src/grading/__init__.py
"""
Grading System V3 - Modular Pick Grading Engine

This package provides a comprehensive, ESPN-powered grading system for sports betting picks.
"""

from src.grading.schema import Pick, GradedPick, BetType, GradeResult
from src.grading.parser import PickParser
from src.grading.loader import DataLoader
from src.grading.matcher import Matcher
from src.grading.engine import GraderEngine

__all__ = [
    "Pick",
    "GradedPick", 
    "BetType",
    "GradeResult",
    "PickParser",
    "DataLoader",
    "Matcher",
    "GraderEngine",
]

def grade_picks(picks: list, date: str = None) -> list:
    """
    Convenience function to grade a list of pick dictionaries.
    
    Args:
        picks: List of dicts with 'pick' and 'league' keys
        date: Optional date string (YYYY-MM-DD)
        
    Returns:
        List of GradedPick objects
    """
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Collect leagues
    leagues = set()
    for p in picks:
        lg = p.get('league', p.get('lg', 'other')).lower()
        leagues.add(lg)
    
    # Fetch scores
    scores = DataLoader.fetch_scores([date], list(leagues))
    
    # Grade
    engine = GraderEngine(scores)
    results = []
    
    for p in picks:
        text = p.get('pick', p.get('p', ''))
        lg = p.get('league', p.get('lg', 'other'))
        parsed = PickParser.parse(text, lg, date)
        graded = engine.grade(parsed)
        results.append(graded)
    
    return results
