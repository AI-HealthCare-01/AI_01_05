from pydantic import BaseModel


class OcrParsedItem(BaseModel):
    item_seq: str | None = None
    item_name: str
    dose_per_intake: float
    daily_frequency: int
    total_days: int
    confidence: str  # "HIGH" | "LOW"


class ParsedPrescriptionResponse(BaseModel):
    items: list[OcrParsedItem]
    raw_text: str
