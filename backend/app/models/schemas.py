from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class VendorProfile(BaseModel):
    vendor_id: str
    name: str
    domain: Optional[str] = None
    risk_score: float
    risk_level: str
    security_score: float
    financial_score: float
    news_sentiment: float
    subcontractors: List[str]
    onboarding_time_sec: float
    data_sources: Dict[str, str]
    message: str
