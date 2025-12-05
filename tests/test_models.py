from models import ParsedPick

def test_unit_normalization():
    # 2u -> 2.0
    assert ParsedPick(raw_pick_id=1, league="X", bet_type="Y", pick_value="Z", unit="2u").unit == 2.0
    # Max Bet -> 5.0
    assert ParsedPick(raw_pick_id=1, league="X", bet_type="Y", pick_value="Z", unit="Max Bet").unit == 5.0
    # Whale -> 5.0
    assert ParsedPick(raw_pick_id=1, league="X", bet_type="Y", pick_value="Z", unit="Whale Play").unit == 5.0
    # Bomb -> 3.0
    assert ParsedPick(raw_pick_id=1, league="X", bet_type="Y", pick_value="Z", unit="Bomb").unit == 3.0
    # Garbage -> 1.0
    assert ParsedPick(raw_pick_id=1, league="X", bet_type="Y", pick_value="Z", unit="info").unit == 1.0