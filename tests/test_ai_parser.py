import pytest
import json
from unittest.mock import MagicMock, patch
from ai_parser import parse_with_ai, _repair_json
from models import RawPick

def test_json_repair():
    dirty = '```json\n[{"test": 1}]\n```'
    assert _repair_json(dirty) == '[{"test": 1}]'

@patch('ai_parser.client')
def test_ai_parser_context(mock_client, sample_raw_pick):
    # Mock Response
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps([{"raw_pick_id": 1, "pick_value": "Test", "league": "NFL", "bet_type": "Spread"}])
    mock_client.chat.completions.create.return_value = mock_resp
    
    results = parse_with_ai([sample_raw_pick])
    
    # Check if context was passed to call
    call_args = mock_client.chat.completions.create.call_args
    sent_prompt = call_args.kwargs['messages'][0]['content']
    
    assert "capper_name" in sent_prompt
    assert "pick_date" in sent_prompt
    assert len(results) == 1