from langgraph.graph import StateGraph, END
from .models import AnalystState
from .nodes import (
    supervisor_node, intake_guard_node, llm_frame_node, 
    web_crawler_node, yfinance_node, score_and_shortlist_node,
    draft_writer_node, validation_node, on_validation_fail
)

def supervisor_router(state: AnalystState) -> str:
    return state.get("route", "WEB")

def retry_router(state: AnalystState) -> str:
    v = state.get("validation", {})
    if v.get("status") == "PASS": return "PASS"
    if state.get("retry_count", 0) >= 2: return "PASS" # Give up
    return "FAIL"

workflow = StateGraph(AnalystState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("intake_guard", intake_guard_node)
workflow.add_node("frame", llm_frame_node)
workflow.add_node("web", web_crawler_node)
workflow.add_node("yfinance", yfinance_node)
workflow.add_node("score", score_and_shortlist_node)
workflow.add_node("draft", draft_writer_node)
workflow.add_node("validate", validation_node)
workflow.add_node("on_fail", on_validation_fail)

workflow.set_entry_point("supervisor")

workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "INTAKE": "intake_guard",
        "WEB": "frame",
        "LLM": "frame",
        "DOC": "frame",
        "YFINANCE": "frame"
    }
)

workflow.add_edge("intake_guard", END)

workflow.add_edge("frame", "web")
workflow.add_edge("web", "yfinance")
workflow.add_edge("yfinance", "score")
workflow.add_edge("score", "draft")
workflow.add_edge("draft", "validate")

workflow.add_conditional_edges(
    "validate",
    retry_router,
    {"PASS": END, "FAIL": "on_fail"}
)

workflow.add_edge("on_fail", "supervisor")

graph = workflow.compile()
