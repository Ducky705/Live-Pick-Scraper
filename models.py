from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
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
    unit: Optional[float] = None
    odds_american: Optional[int] = None

    @field_validator('unit', mode='before')
    @classmethod
    def validate_unit(cls, v):
        if v is None: return None
        if isinstance(v, (float, int)): 
            # Allow high units (e.g. 150, 500) as per user requirement
            return float(v)
            
        s = str(v).lower().strip()
        clean = re.sub(r'[^\d.]', '', s)
        try:
            val = float(clean)
            return round(val, 2)
        except:
            return None

    @field_validator('odds_american', mode='before')
    @classmethod
    def validate_odds(cls, v):
        if v is None: return None
        try:
            val = int(v)
            # Odds range sanity check
            if val < -20000 or val > 20000: return None 
            # Odds usually aren't single digits (except maybe very weird formats, but standard US odds are >100 or <-100)
            if -100 < val < 100: return None
            return val
        except:
            return None

class StandardizedPick(BaseModel):
    capper_id: int
    pick_date: date
    league: str
    pick_value: str
    bet_type: str
    unit: Optional[float] = None
    odds_american: Optional[int] = None
    source_url: str
    source_unique_id: str
    result: str = 'pending'
