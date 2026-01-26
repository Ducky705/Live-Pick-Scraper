from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Any
from datetime import datetime

class TelegramMessage(BaseModel):
    id: int
    text: Optional[str] = ""
    date: str # "YYYY-MM-DD HH:MM ET"
    channel_id: int
    channel_name: str
    images: List[str] = []
    video: Optional[str] = None
    ocr_text: Optional[str] = ""
    ocr_texts: List[str] = []

class BetPick(BaseModel):
    message_id: Union[int, str]
    capper_name: str = "Unknown"
    league: str = "Other"
    type: str = "Unknown"
    pick: str
    odds: Optional[Union[int, str]] = None
    units: float = 1.0
    date: Optional[str] = None
    result: Optional[str] = "Pending"
    score_summary: Optional[str] = ""
    ai_reasoning: Optional[str] = None # Stores "confidence | reason"
    tags: List[str] = [] # e.g. ["Live", "AltLine", "Hedge"]
    warning: Optional[str] = None # e.g. "Odds Mismatch", "Stat Anomaly"
    is_update: bool = False # True if this is an update to a previous play
    
    # Enrichment Fields
    opponent: Optional[str] = None
    game_date: Optional[str] = None
    
    # Phase 3: Granular Props
    subject: Optional[str] = None # "LeBron James"
    market: Optional[str] = None # "Points"
    line: Optional[float] = None # 25.5
    prop_side: Optional[str] = None # "Over", "Under"
    deduction_source: Optional[str] = "Explicit" # "Explicit", "Implied", "Visual"
    
    @field_validator('units', mode='before')
    def parse_units(cls, v):
        if v is None: return 1.0
        try:
            return float(str(v).replace('u','').strip())
        except:
            return 1.0

class GradingResult(BaseModel):
    id: Union[int, str]
    result: str # Win, Loss, Push, Unknown
    score: str

class APIResponse(BaseModel):
    success: bool = True
    error: Optional[str] = None
    data: Any = None
