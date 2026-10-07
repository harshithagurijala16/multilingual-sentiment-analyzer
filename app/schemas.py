from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    org_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    org_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

# --- Product Schemas ---
class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None

class ProductOut(BaseModel):
    id: int
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True

# --- Review Schemas ---
class ReviewAnalyzeRequest(BaseModel):
    review: str = Field(..., min_length=1)
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    save: bool = True
    source: str = "single"

class ReviewAnalyzeResponse(BaseModel):
    id: Optional[int] = None
    saved_id: Optional[int] = None
    original_text: str
    language: str
    script: str
    is_romanized: bool
    is_code_mixed: bool
    transliterated_text: str
    sentiment: str
    confidence: float
    prob_pos: float
    prob_neg: float
    prob_neu: float
    low_confidence: bool
    aspects: List[str]
    product_name: Optional[str] = None
    review_date: Optional[datetime] = None

class ReviewOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    original_text: str
    language: str
    script: str
    is_romanized: bool
    transliterated_text: Optional[str] = None
    sentiment: str
    confidence: float
    prob_pos: float
    prob_neg: float
    prob_neu: float
    aspects: List[str] = []
    source: str
    review_date: datetime
    created_at: datetime
    corrected_label: Optional[str] = None

    class Config:
        from_attributes = True

class ReviewListResponse(BaseModel):
    total: int
    page: int
    limit: int
    reviews: List[ReviewOut]

class ReviewCorrectRequest(BaseModel):
    corrected_label: str = Field(..., pattern="^(Positive|Negative|Neutral)$")

class BulkUploadResponse(BaseModel):
    total_processed: int
    total_rows: Optional[int] = None
    saved_count: int
    skipped_count: int
    skipped_rows: List[Dict[str, Any]]
    sentiment_counts: Dict[str, int]
    language_counts: Dict[str, int]
    average_confidence: float

# --- Analytics Schemas ---
class AnalyticsSummary(BaseModel):
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    average_confidence: float
    nps_score: float # (% Positive - % Negative)
    total_languages: int
    total_products: int
