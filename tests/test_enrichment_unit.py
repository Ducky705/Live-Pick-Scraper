import asyncio

import pytest
from src.enrichment.engine import EnrichmentEngine
from src.models import BetPick

@pytest.mark.asyncio
async def test_specific_enrichment():
    engine = EnrichmentEngine()

    # Test case that was failing grading: "Oklahoma St UNDER 163"
    pick = BetPick(
        message_id=123,
        pick="Oklahoma St UNDER 163",
        league="NCAAB",
        type="Total",
        date="2026-01-24 12:00 ET",
    )

    print(f"Original: {pick.pick} (League: {pick.league})")

    enriched = engine.enrich_picks([pick])

    print(f"Enriched: {enriched[0].pick}")
    print(f"Opponent: {enriched[0].opponent}")
    print(f"Odds: {enriched[0].odds}")

    # Another Test: "Oilers -175" (Moneyline implied)
    pick2 = BetPick(
        message_id=124,
        pick="Oilers -175",
        league="NHL",
        type="Moneyline",
        date="2026-01-24 12:00 ET",
    )
    enriched2 = engine.enrich_picks([pick2])
    print(f"\nOriginal: {pick2.pick}")
    print(f"Enriched: {enriched2[0].pick}")
    print(f"Odds: {enriched2[0].odds}")

    # Another Test: "Cal St Fullerton Under 172.5"
    pick3 = BetPick(
        message_id=125,
        pick="Cal St Fullerton Under 172.5",
        league="NCAAB",
        type="Total",
        date="2026-01-24 12:00 ET",
    )
    enriched3 = engine.enrich_picks([pick3])
    print(f"\nOriginal: {pick3.pick}")
    print(f"Enriched: {enriched3[0].pick}")
    print(f"Opponent: {enriched3[0].opponent}")


if __name__ == "__main__":
    asyncio.run(test_specific_enrichment())
