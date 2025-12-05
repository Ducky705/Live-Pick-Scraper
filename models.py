from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator
from typing import Optional, List, Literal, Any
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)

class RawPick(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    source_unique_id: str
    source_url: str
    capper_name: str
    raw_text: str
    pick_date: date
    status: str = 'pending'
    process_attempts: int = 0
    created_at: Optional[datetime] = None

class ParsedPick(BaseModel):
    raw_pick_id: int
    league: str = "Unknown"
    bet_type: str
    pick_value: str
    # CHANGED: Unit is now Optional, default is None (Blank)
    unit: Optional[float] = None
    odds_american: Optional[int] = None

    @field_validator('unit', mode='before')
    @classmethod
    def validate_unit(cls, v):
        if v is None: return None  # Allow blank
        if isinstance(v, (float, int)): return float(v)
        s = str(v).lower().strip()
        
        # Strict numerical extraction only
        clean = re.sub(r'[^\d.]', '', s)
        try:
            val = float(clean)
            if val > 100: return None # Sanity check for bad OCR
            return round(val, 2)
        except:
            return None # If we can't parse a number, return None

    @field_validator('odds_american', mode='before')
    @classmethod
    def validate_odds(cls, v):
        if v is None: return None
        try:
            val = int(v)
            if val < -20000 or val > 20000:
                return None 
            return val
        except:
            return None

class StandardizedPick(BaseModel):
    capper_id: int
    pick_date: date
    league: str
    pick_value: str
    bet_type: str
    # CHANGED: Unit is now Optional
    unit: Optional[float] = None
    odds_american: Optional[int] = None
    source_url: str
    source_unique_id: str
    result: str = 'pending'
