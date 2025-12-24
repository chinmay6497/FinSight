from typing import TypedDict, Literal, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

# --- Domain Models ---

class UserProfile(TypedDict, total=False):
    budget: float
    risk_level: Literal["low", "medium", "high"]
    horizon: str
    country: str

class ValidationResult(TypedDict, total=False):
    status: Literal["PASS", "FAIL"]
    reasons: List[str]
    suggested_route: Literal["WEB", "LLM", "DOC", "YFINANCE", "INTAKE"]

class AnalystState(TypedDict, total=False):
    messages: List[BaseMessage]
    
    # Decisions
    route: Literal["WEB", "LLM", "DOC", "YFINANCE", "INTAKE"]
    plan: str
    
    # Data
    user_profile: UserProfile
    missing_fields: List[str]
    web_evidence: List[Dict[str, Any]]
    price_data: Dict[str, Any]
    fundamentals: Dict[str, Any]
    last_quarter: Dict[str, Any]
    
    # Outputs
    frame: str
    draft: str
    shortlist: List[Dict[str, Any]]
    validation: ValidationResult
    
    # Retry logic
    retry_count: int
    reminder: str

# --- API Models ---

class ProfileRequest(BaseModel):
    budget: float
    risk: Literal["low", "medium", "high"]
    horizon: str = "6m"

class AnalyzeRequest(BaseModel):
    question: str
    profile: ProfileRequest
