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
