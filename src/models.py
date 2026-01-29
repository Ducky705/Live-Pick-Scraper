from typing import Any

from pydantic import BaseModel, field_validator


class TelegramMessage(BaseModel):
    id: int
    text: str | None = ""
    date: str  # "YYYY-MM-DD HH:MM ET"
    channel_id: int
    channel_name: str
    images: list[str] = []
    video: str | None = None
    ocr_text: str | None = ""
    ocr_texts: list[str] = []


class BetPick(BaseModel):
    message_id: int | str
    capper_name: str = "Unknown"
    league: str = "Other"
    type: str = "Unknown"
    pick: str
    odds: int | str | None = None
    units: float = 1.0
    date: str | None = None
    result: str | None = "Pending"
    score_summary: str | None = ""
    ai_reasoning: str | None = None  # Stores "confidence | reason"
    tags: list[str] = []  # e.g. ["Live", "AltLine", "Hedge"]
    warning: str | None = None  # e.g. "Odds Mismatch", "Stat Anomaly"
    is_update: bool = False  # True if this is an update to a previous play

    # Enrichment Fields
    opponent: str | None = None
    game_date: str | None = None

    # Phase 3: Granular Props
    subject: str | None = None  # "LeBron James"
    market: str | None = None  # "Points"
    line: float | None = None  # 25.5
    prop_side: str | None = None  # "Over", "Under"
    deduction_source: str | None = "Explicit"  # "Explicit", "Implied", "Visual"

    @field_validator("units", mode="before")
    def parse_units(cls, v):
        if v is None:
            return 1.0
        try:
            return float(str(v).replace("u", "").strip())
        except:
            return 1.0


class GradingResult(BaseModel):
    id: int | str
    result: str  # Win, Loss, Push, Unknown
    score: str


class APIResponse(BaseModel):
    success: bool = True
    error: str | None = None
    data: Any = None
