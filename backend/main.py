import json
import os
import re
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

load_dotenv()

from agent.models import ProfileRequest, AnalyzeRequest
from agent.graph import graph

model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
reco_model = ChatGroq(model=model_name, temperature=0)

URL_RE = re.compile(r"https?://\\S+")

app = FastAPI(title="FinSight Demo", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/profile")
def save_profile(profile: ProfileRequest):
    return {**profile.dict(), "saved": True}

@app.post("/recommendations")
def recommendations(profile: ProfileRequest):
    risk = profile.risk
    horizon = profile.horizon
    stock_universe = [
        {"ticker": "AAPL", "name": "Apple Inc.", "market": "USA", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "MSFT", "name": "Microsoft Corp.", "market": "USA", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "market": "USA", "risk": "high", "horizon": ["1m", "6m", "1y"]},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "market": "USA", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "META", "name": "Meta Platforms Inc.", "market": "USA", "risk": "high", "horizon": ["1m", "6m", "1y"]},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "market": "USA", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "AVGO", "name": "Broadcom Inc.", "market": "USA", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "LLY", "name": "Eli Lilly and Co.", "market": "USA", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "JPM", "name": "JPMorgan Chase", "market": "USA", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "COST", "name": "Costco Wholesale", "market": "USA", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "SHOP", "name": "Shopify Inc.", "market": "Canada", "risk": "high", "horizon": ["1m", "6m", "1y"]},
        {"ticker": "CSU.TO", "name": "Constellation Software", "market": "Canada", "risk": "low", "horizon": ["1y"]},
        {"ticker": "LSPD.TO", "name": "Lightspeed Commerce", "market": "Canada", "risk": "high", "horizon": ["1m", "6m"]},
        {"ticker": "NTR.TO", "name": "Nutrien Ltd.", "market": "Canada", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "CP.TO", "name": "Canadian Pacific Kansas City", "market": "Canada", "risk": "medium", "horizon": ["6m", "1y"]},
        {"ticker": "BAM", "name": "Brookfield Asset Management", "market": "Canada", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "ENB.TO", "name": "Enbridge Inc.", "market": "Canada", "risk": "low", "horizon": ["6m", "1y"]},
        {"ticker": "SHOP.TO", "name": "Shopify (TSX)", "market": "Canada", "risk": "high", "horizon": ["6m", "1y"]}
    ]
    def score(item):
        s = 0
        if item["risk"] == risk:
            s += 3
        if horizon in item["horizon"]:
            s += 2
        if risk == "high" and item["risk"] == "medium":
            s += 1
        return s
    ranked = sorted(stock_universe, key=score, reverse=True)
    usa = [s for s in ranked if s["market"] == "USA"][:6]
    canada = [s for s in ranked if s["market"] == "Canada"][:6]
    items = usa + canada
    for item in items:
        item["rationale"] = f"Aligned with {risk} risk and {horizon} horizon."
        item.pop("risk", None)
        item.pop("horizon", None)
    return {"items": items}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    print(f"Analyzing: {request.question}")
    
    profile = request.profile.dict()
    if "risk" in profile and "risk_level" not in profile:
        profile["risk_level"] = profile.pop("risk")

    state = {
        "messages": [HumanMessage(content=request.question)],
        "user_profile": profile,
        "retry_count": 0
    }
    
    try:
        result = await graph.ainvoke(state)
        
        # Transform result to match frontend expectation
        # Note: In a real app we'd map this carefully. 
        # Here we extract key parts.
        
        price = result.get("price_data", {})
        shortlist = result.get("shortlist", [{}])[0]
        evidence = result.get("web_evidence", [])
        draft = result.get("draft", {})
        validation = result.get("validation", {})

        evidence_bullets = []
        for e in evidence:
            title = e.get("title", "News item")
            snippet = e.get("snippet", "")
            url = e.get("url", "")
            if url:
                evidence_bullets.append(f"{title}: {snippet} (source: {url})")
            else:
                evidence_bullets.append(f"{title}: {snippet}")

        def ensure_list(value, fallback):
            if isinstance(value, list) and value:
                return value
            if isinstance(value, str) and value.strip():
                return [value]
            return fallback

        def round_num(value):
            if isinstance(value, (int, float)):
                return round(float(value), 2)
            return value
        
        clean_summary = URL_RE.sub("", draft.get("executive_summary", "")).strip()
        clean_summary = re.sub(r"\(source:?\s*\)", "", clean_summary, flags=re.IGNORECASE).strip()
        if "Recommendation:" not in clean_summary:
            clean_summary = "Recommendation: NO; Expected growth strength: Medium; Risk points: news volatility, data gaps."
        return {
            "ticker": shortlist.get("ticker", "UNKNOWN"),
            "company_name": price.get("company_name", "Unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "price_data": price,
            "analysis": {
                "executive_summary": clean_summary,
                "expected_return": draft.get("expected_return", "Expected return not available."),
                "news_summary": ensure_list(draft.get("news_summary", []), [f"Summary: {b}" for b in evidence_bullets]),
                "bull_case": ensure_list(draft.get("bull_case", []), [f"News impact: {b}" for b in evidence_bullets]),
                "bear_case": ensure_list(draft.get("bear_case", []), [f"News impact: {b}" for b in evidence_bullets]),
                "key_risks": ensure_list(draft.get("key_risks", []), [f"News risk: {b}" for b in evidence_bullets]),
                "last_quarter_result": draft.get("last_quarter_result", "No recent quarterly results data available.")
            },
            "evidence_pack": [
                {
                    "date": "Recent",
                    "source": e.get("source", "Web"),
                    "title": e.get("title", ""),
                    "claim": e.get("snippet", ""),
                    "url": e.get("url", "")
                }
                for e in evidence
            ],
            "score": {
                "total": round_num(shortlist.get("score", 0)),
                "notes": "Score uses price data, news coverage, 1D move, and risk profile",
                "breakdown": [
                    {"label": b.get("label"), "value": round_num(b.get("value"))}
                    for b in shortlist.get("score_breakdown", [])
                ]
            },
            "validation": validation,
            "disclaimer": "Not financial advice. Educational demo only."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
