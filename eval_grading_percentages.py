import json
from src.score_fetcher import fetch_scores_for_date
from src.grading.engine import GraderEngine
from src.grading.parser import PickParser
from src.grading.ai_resolver import AIResolver

# Mock AI to avoid waiting on rate limits and test purely deterministic layer
AIResolver.resolve_pick = lambda text, league, scores: None
AIResolver.parse_pick = lambda text, league: None

def main():
    with open('benchmark/dataset/parsing_golden_set.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    scores = fetch_scores_for_date('2026-02-14')
    grader = GraderEngine(scores)

    results = {'WIN': 0, 'LOSS': 0, 'PUSH': 0, 'PENDING': 0, 'VOID': 0, 'ERROR': 0}
    total_picks = 0
    unmatched_reasons = []

    for msg_id, picks in ground_truth.items():
        for pick_data in picks:
            total_picks += 1
            raw_text = pick_data.get('p', '')
            league = pick_data.get('lg', 'Other')
            
            parsed = PickParser.parse(raw_text, league, '2026-02-14')
            if not parsed:
                results['ERROR'] += 1
                unmatched_reasons.append(f"ERROR: {raw_text} - Failed to initial parse")
                continue
                
            graded = grader.grade(parsed, league_hint=league)
            status = graded.grade.name
            results[status] = results.get(status, 0) + 1
            
            if status in ['PENDING', 'VOID', 'ERROR']:
                unmatched_reasons.append(f"{status}: {raw_text} - {graded.details}")

    graded_count = results['WIN'] + results['LOSS'] + results['PUSH']
    print(f'\nTotal Picks: {total_picks}')
    print(f'Successfully Graded: {graded_count} ({(graded_count/total_picks)*100:.1f}%)')
    print(f'Breakdown: {results}')

    if unmatched_reasons:
        print('\nWhy it missed the rest:')
        for r in unmatched_reasons:
            print(r)

if __name__ == "__main__":
    main()
