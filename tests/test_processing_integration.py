import pytest
from unittest.mock import MagicMock, patch
from processing_service import process_picks
from models import RawPick, ParsedPick

@patch('processing_service.db')
@patch('processing_service.simple_parser')
@patch('processing_service.ai_parser')
def test_processing_flow(mock_ai, mock_simple, mock_db):
    # Setup mock data
    raw = RawPick(id=1, source_unique_id="1", source_url="u", capper_name="Cap", raw_text="Lakers -5", pick_date="2024-01-01")
    mock_db.get_pending_raw_picks.return_value = [raw]
    mock_db.get_or_create_capper.return_value = 10
    
    parsed = ParsedPick(raw_pick_id=1, league="NBA", bet_type="Spread", pick_value="Lakers -5")
    mock_simple.parse_with_regex.return_value = [parsed]
    
    # Run service
    process_picks()
    
    # Verify results
    mock_db.insert_structured_picks.assert_called()
    mock_db.update_raw_status.assert_called_with([1], 'processed')
