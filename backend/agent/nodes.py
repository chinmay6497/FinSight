import json
import os
import re
from datetime import datetime
from typing import Literal, List, Dict, Any, Tuple
from urllib.parse import urlparse

import requests
import yfinance as yf
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from .models import AnalystState

# --- Setup ---
# Use a default key or expect one in env. Ideally user provides one.
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    # Fallback to a placeholder or raise warning. 
    # For demo, we assume user will provide it.
    pass

# Allow model override via env to avoid deprecations.
model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
model = ChatGroq(model=model_name, temperature=0)

# Search setup
wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)

# --- Helpers ---
def _get_last_user_text(state: AnalystState) -> str:
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            return m.content
    return state.get("messages", [])[-1].content if state.get("messages") else ""

_COMMON_WORDS = {
    "I", "A", "AN", "THE", "SHOULD", "INVEST", "IN", "BUY", "SELL",
    "FOR", "IS", "IT", "NOW", "STOCK", "SHARES", "PRICE", "ANALYZE"
}

def _extract_ticker(question: str) -> str:
    match = re.search(r"\$([A-Z]{1,5})\b", question)
    if match:
        return match.group(1)
    match = re.search(r"\(([A-Z]{1,5})\)", question)
    if match:
        return match.group(1)
    raw_tokens = [t.strip(".,!?()[]{}") for t in question.split()]
    tickers = []
    for raw in raw_tokens:
        if not raw.isalpha():
            continue
        if raw != raw.upper():
            continue
        if not (2 <= len(raw) <= 5):
            continue
        if raw in _COMMON_WORDS:
            continue
        tickers.append(raw)
    return tickers[0] if tickers else ""

def _resolve_ticker_and_name(question: str) -> Tuple[str, str]:
    ticker = _extract_ticker(question)
    if ticker:
        return ticker, ""
    company_query = ""
    upper_words = re.findall(r"\b[A-Z]{2,6}\b", question)
    if upper_words:
        company_query = max(upper_words, key=len)
    else:
        words = re.findall(r"[A-Za-z0-9&.]+", question)
        if words:
            lower_stop = {w.lower() for w in _COMMON_WORDS}
            filtered = [w for w in words if w.lower() not in lower_stop]
            company_query = filtered[-1] if filtered else max(words, key=len)
    search_cls = getattr(yf, "Search", None)
    if search_cls:
        try:
            search = search_cls(company_query or question)
            quotes = getattr(search, "quotes", [])
            if quotes:
                first = quotes[0]
                return first.get("symbol", ""), first.get("shortname", "") or first.get("longname", "")
        except Exception:
            return "", ""
    return "", ""

def _fetch_quote_yahoo(ticker: str) -> Dict[str, Any]:
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": ticker},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("quoteResponse", {}).get("result", [])
        if not results:
            return {}
        q = results[0]
        price = q.get("regularMarketPrice")
        prev_close = q.get("regularMarketPreviousClose")
        change_pct = None
        if price is not None and prev_close:
            try:
                change_pct = ((price - prev_close) / prev_close) * 100
            except Exception:
                change_pct = None
        return {
            "currency": q.get("currency", "USD"),
            "current_price": price,
            "change_1d_pct": change_pct,
            "source": "yahoo_finance",
            "ticker": q.get("symbol", ticker),
            "company_name": q.get("longName") or q.get("shortName") or ticker
        }
    except Exception:
        return {}

def _normalize_evidence(results: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if isinstance(results, list):
        for i, item in enumerate(results):
            title = item.get("title") or item.get("heading") or item.get("text") or "News item"
            url = item.get("href") or item.get("link") or item.get("url") or ""
            snippet = item.get("body") or item.get("snippet") or item.get("text") or ""
            source = ""
            if url:
                try:
                    source = urlparse(url).netloc.replace("www.", "")
                except Exception:
                    source = ""
            items.append(
                {"id": i + 1, "title": title, "url": url, "snippet": snippet, "source": source}
            )
    else:
        items.append({"id": 1, "title": "Search results", "url": "", "snippet": str(results), "source": ""})
    return items

def _evidence_bullets(evidence: List[Dict[str, Any]]) -> List[str]:
    bullets = []
    for ev in evidence:
        title = ev.get("title", "News item")
        snippet = ev.get("snippet", "")
        url = ev.get("url", "")
        if url:
            bullets.append(f"{title}: {snippet} (source: {url})")
        else:
            bullets.append(f"{title}: {snippet}")
    return bullets

# --- Nodes ---

def intake_guard_node(state: AnalystState) -> AnalystState:
    profile = state.get("user_profile", {})
    missing = []
    if "budget" not in profile: missing.append("budget")
    if "risk_level" not in profile: missing.append("risk_level")
    
    state["missing_fields"] = missing
    
    if missing:
        state.setdefault("messages", []).append(AIMessage(content=f"Missing inputs: {', '.join(missing)}"))
        state["route"] = "INTAKE"
    return state

def supervisor_node(state: AnalystState) -> AnalystState:
    state.setdefault("retry_count", 0)
    profile = state.get("user_profile", {})
    
    if "budget" not in profile or "risk_level" not in profile:
        state["route"] = "INTAKE"
        state["plan"] = "Collect budget + risk."
        return state

    question = _get_last_user_text(state)
    reminder = state.get("reminder", "")
    
    template = """
    Classify query into ONE label: WEB, LLM, or DOC.
    Rules:
    - Time-sensitive/price/earnings => WEB
    - Explanation/definition => LLM
    - Internal docs => DOC
    
    Query: {input}
    Reminder: {reminder}
    
    Return ONLY: WEB, LLM, or DOC
    """
    
    prompt = PromptTemplate(template=template, input_variables=["input", "reminder"])
    chain = prompt | model | StrOutputParser()
    try:
        label = chain.invoke({"input": question, "reminder": reminder}).strip().upper()
    except Exception:
        label = "WEB" # Fallback

    if label not in {"WEB", "LLM", "DOC"}:
        label = "WEB"
        
    state["route"] = label
    state["plan"] = f"Route to {label}"
    return state

def llm_frame_node(state: AnalystState) -> AnalystState:
    question = _get_last_user_text(state)
    ticker, company_name = _resolve_ticker_and_name(question)
    target = ticker or company_name or question
    
    template = """
    Prepare analysis frame for: {question} (Target: {target})
    Return:
    1) Assumptions (max 5)
    2) Bull-case questions (max 5)
    3) Bear-case questions (max 5)
    4) Safety rules (max 5)
    """
    
    prompt = PromptTemplate(template=template, input_variables=["question", "target"])
    frame = (prompt | model | StrOutputParser()).invoke({"question": question, "target": target})
    state["frame"] = frame
    return state

def web_crawler_node(state: AnalystState) -> AnalystState:
    question = _get_last_user_text(state)
    ticker, company_name = _resolve_ticker_and_name(question)
    query_target = ticker or company_name or question
    query = f"{query_target} latest news earnings guidance risks"
    
    try:
        results = wrapper.results(query, max_results=5)
        state["web_evidence"] = _normalize_evidence(results)
    except Exception as e:
        state["web_evidence"] = [{"id": 1, "title": "Search error", "url": "", "snippet": str(e), "source": ""}]
    return state

def yfinance_node(state: AnalystState) -> AnalystState:
    question = _get_last_user_text(state)
    ticker, company_name = _resolve_ticker_and_name(question)
    
    if not ticker:
        state["price_data"] = {"error": "Ticker not detected"}
        return state
        
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        fast = getattr(stock, "fast_info", {}) or {}
        last_price = fast.get("last_price") or fast.get("lastPrice") or fast.get("regular_market_price")
        prev_close = fast.get("previous_close") or fast.get("previousClose")
        change_pct = None
        if last_price is not None and prev_close:
            try:
                change_pct = ((last_price - prev_close) / prev_close) * 100
            except Exception:
                change_pct = None
        if last_price is None:
            try:
                history = stock.history(period="5d")
                if not history.empty and "Close" in history:
                    closes = history["Close"].dropna()
                    if len(closes) >= 2:
                        last_price = float(closes.iloc[-1])
                        prev_close = float(closes.iloc[-2])
                        change_pct = ((last_price - prev_close) / prev_close) * 100
            except Exception:
                pass

        last_quarter = {}
        try:
            qe = stock.quarterly_earnings
            if hasattr(qe, "empty") and not qe.empty:
                last_row = qe.iloc[-1]
                period = qe.index[-1]
                if hasattr(period, "to_pydatetime"):
                    period = period.to_pydatetime().strftime("%Y-%m-%d")
                last_quarter = {
                    "period": str(period),
                    "revenue": float(last_row.get("Revenue")) if "Revenue" in last_row else None,
                    "earnings": float(last_row.get("Earnings")) if "Earnings" in last_row else None,
                }
        except Exception:
            last_quarter = {}
        
        data = {
            "currency": info.get("currency", "USD"),
            "current_price": last_price or info.get("currentPrice") or info.get("regularMarketPrice"),
            "change_1d_pct": change_pct if change_pct is not None else info.get("regularMarketChangePercent", 0),
            "source": "yfinance",
            "ticker": ticker,
            "company_name": info.get("longName") or company_name or ticker
        }
        if data.get("current_price") is None:
            fallback = _fetch_quote_yahoo(ticker)
            if fallback:
                data = fallback
        state["price_data"] = data
        state["last_quarter"] = last_quarter
    except Exception as e:
        fallback = _fetch_quote_yahoo(ticker)
        if fallback:
            state["price_data"] = fallback
        else:
            state["price_data"] = {"ticker": ticker, "error": str(e)}
    return state

def score_and_shortlist_node(state: AnalystState) -> AnalystState:
    profile = state.get("user_profile", {})
    risk = profile.get("risk_level", "medium")
    price_data = state.get("price_data", {})
    web_evidence = state.get("web_evidence", [])
    
    ticker = price_data.get("ticker", "UNKNOWN")
    
    score = 50
    breakdown = [{"label": "Base", "value": 50}]
    if "error" in price_data:
        score -= 10
        breakdown.append({"label": "Price data missing", "value": -10})
    else:
        score += 10
        breakdown.append({"label": "Price data available", "value": 10})
    news_count = len([e for e in web_evidence if e.get("url") or e.get("snippet")])
    news_points = min(news_count * 3, 15)
    if news_points:
        score += news_points
        breakdown.append({"label": "News coverage", "value": news_points})
    change_pct = price_data.get("change_1d_pct")
    if isinstance(change_pct, (int, float)):
        move = max(min(change_pct, 5), -5)
        if move:
            score += move
            breakdown.append({"label": "1D price move", "value": round(move, 2)})
    if risk == "low":
        score -= 5
        breakdown.append({"label": "Low risk profile", "value": -5})
    elif risk == "high":
        score += 5
        breakdown.append({"label": "High risk profile", "value": 5})
    
    item = {
        "ticker": ticker,
        "score": max(0, min(100, score)),
        "pros": ["Recent news reviewed"],
        "cons": ["Demo scoring model"],
        "risks": ["Market volatility"],
        "evidence_refs": ["web_evidence", "price_data"],
        "score_breakdown": breakdown
    }
    state["shortlist"] = [item]
    return state

def draft_writer_node(state: AnalystState) -> AnalystState:
    question = _get_last_user_text(state)
    profile = state.get("user_profile", {})
    ticker, company_name = _resolve_ticker_and_name(question)
    target = ticker or company_name or question
    evidence = state.get("web_evidence", [])
    evidence_bullets = _evidence_bullets(evidence)
    
    template = """
    You are a financial analyst. Use provided evidence.
    
    Profile: {budget}, {risk}, {horizon}
    Question: {question}
    Target: {target}
    Evidence: {web}
    Price: {price}
    Shortlist: {shortlist}
    
    Write JSON with keys:
    - executive_summary: string (no source links)
    - expected_return: string (timeframe-specific)
    - news_summary: list of descriptive strings
    - bull_case: list of descriptive strings
    - bear_case: list of descriptive strings
    - key_risks: list of descriptive strings
    - last_quarter_result: string
    Requirements:
    - Executive summary must include: Recommendation (YES/NO), Expected growth strength (High/Medium/Low),
      and Risk points (comma-separated). No source links in executive_summary.
    - expected_return should be a % range for the selected horizon ({horizon}).
    - Include sources by appending "(source: URL)" when referencing any news outside the executive summary.
    - Keep items descriptive (1-2 sentences).
    - Do not include markdown or extra keys.
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["budget", "risk", "horizon", "question", "target", "web", "price", "shortlist"]
    )
    draft_text = (prompt | model | StrOutputParser()).invoke({
        "budget": profile.get("budget"), 
        "risk": profile.get("risk_level"),
        "horizon": profile.get("horizon"),
        "question": question,
        "target": target,
        "web": evidence,
        "price": state.get("price_data"),
        "shortlist": state.get("shortlist")
    })
    draft = {
        "executive_summary": "",
        "expected_return": "",
        "news_summary": [],
        "bull_case": [],
        "bear_case": [],
        "key_risks": [],
        "last_quarter_result": ""
    }
    try:
        draft = json.loads(draft_text)
    except Exception:
        draft["news_summary"] = [draft_text]
    if evidence_bullets:
        draft.setdefault("bull_case", [])
        draft.setdefault("bear_case", [])
        draft.setdefault("key_risks", [])
        draft.setdefault("news_summary", [])
        for bullet in evidence_bullets:
            draft["bull_case"].append(f"News impact: {bullet}")
            draft["bear_case"].append(f"News impact: {bullet}")
            draft["key_risks"].append(f"News risk: {bullet}")
            if len(draft["news_summary"]) < 5:
                draft["news_summary"].append(f"Summary: {bullet}")
        if not draft["bull_case"]:
            draft["bull_case"] = [f"News impact: {b}" for b in evidence_bullets]
        if not draft["bear_case"]:
            draft["bear_case"] = [f"News impact: {b}" for b in evidence_bullets]
        if not draft["key_risks"]:
            draft["key_risks"] = [f"News risk: {b}" for b in evidence_bullets]
        if not draft["news_summary"]:
            draft["news_summary"] = [f"Summary: {b}" for b in evidence_bullets]
        if not draft.get("executive_summary"):
            draft["executive_summary"] = "Recommendation: NO; Expected growth strength: Medium; Risk points: news volatility, data gaps."
    last_quarter = state.get("last_quarter", {})
    if last_quarter and not draft.get("last_quarter_result"):
        period = last_quarter.get("period", "latest quarter")
        revenue = last_quarter.get("revenue")
        earnings = last_quarter.get("earnings")
        summary_parts = [f"Period: {period}"]
        if revenue is not None:
            summary_parts.append(f"Revenue: {revenue}")
        if earnings is not None:
            summary_parts.append(f"Earnings: {earnings}")
        draft["last_quarter_result"] = "; ".join(summary_parts)
    if not draft.get("last_quarter_result"):
        draft["last_quarter_result"] = "No recent quarterly results data available."
    if not draft.get("expected_return"):
        draft["expected_return"] = "Expected return not available."
    state["draft"] = draft
    return state

def validation_node(state: AnalystState) -> AnalystState:
    draft = state.get("draft", "")
    reasons = []
    if isinstance(draft, dict):
        if not draft.get("bull_case"): reasons.append("Missing Bull case")
        if not draft.get("bear_case"): reasons.append("Missing Bear case")
        if not draft.get("key_risks"): reasons.append("Missing Key risks")
    else:
        if "Bull" not in str(draft): reasons.append("Missing Bull case")
        if "Bear" not in str(draft): reasons.append("Missing Bear case")
    
    status = "PASS" if not reasons else "FAIL"
    suggested = "WEB" if "Missing" in str(reasons) else "LLM"
    
    state["validation"] = {"status": status, "reasons": reasons, "suggested_route": suggested}
    return state

def on_validation_fail(state: AnalystState) -> AnalystState:
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["reminder"] = f"Validation failed: {state['validation']['reasons']}"
    return state
