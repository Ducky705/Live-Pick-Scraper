import json
import pytest
from unittest.mock import patch, MagicMock

from src.live_pipeline import build_openrouter_payload, clean_json_response, process_live_message

def test_build_openrouter_payload():
    text = "Hello World"
    channel = "TestChannel"
    
    payload = build_openrouter_payload(text, [], channel)
    
    assert payload["model"] == "google/gemini-2.5-flash"
    assert len(payload["messages"]) == 2
    assert "TestChannel" in payload["messages"][1]["content"][0]["text"]

def test_clean_json_response():
    raw_response = "```json\n{\"classification\": \"PICK\", \"picks\": []}\n```"
    cleaned = clean_json_response(raw_response)
    assert cleaned == "{\"classification\": \"PICK\", \"picks\": []}"

    parsed = json.loads(cleaned)
    assert parsed["classification"] == "PICK"

@patch("src.live_pipeline.post")
@patch("src.live_pipeline.get_or_create_capper_id")
def test_process_live_message(mock_get_capper, mock_post):
    # Setup mocks
    mock_get_capper.return_value = 123
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    sample_llm_json = {
        "classification": "PICK",
        "picks": [
            {
                "capper_name": "VIP Sports",
                "league": "NBA",
                "pick_value": "Lakers -5.5",
                "bet_type": "Spread",
                "unit": 2.0,
                "odds_american": -110
            }
        ]
    }
    
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(sample_llm_json)
                }
            }
        ]
    }
    mock_post.return_value = mock_response
    
    # Execute
    classification, picks = process_live_message(
        message_text="Lakers -5.5 2U -110",
        image_paths=[],
        channel_name="VIP Sports Channel",
        source_url="http://t.me/c/123/45",
        source_unique_id="tg_123_45",
        pick_date="2026-02-28"
    )
    
    # Verify
    assert classification == "PICK"
    assert len(picks) == 1
    assert picks[0]["capper_id"] == 123
    assert picks[0]["pick_value"] == "Lakers -5.5"
    assert picks[0]["unit"] == 2.0
    assert picks[0]["odds_american"] == -110
    assert picks[0]["source_unique_id"] == "tg_123_45"
