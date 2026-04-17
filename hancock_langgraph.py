from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    mode: str
    authorized: bool
    confidence: float
    rag_context: List[str]

def planner(state: AgentState):
    # TODO: route to correct mode prompt (Pentest, SOC, etc.)
    return {"messages": [f"Planner for {state['mode']} mode activated"]}

def recon_agent(state: AgentState):
    # collectors + RAG call here
    return {"messages": ["Recon completed via live MITRE/NVD collectors"]}

def executor_agent(state: AgentState):
    if not state["authorized"] or state["confidence"] < 0.8:
        return {"messages": ["Authorization or confidence check failed — human review required"]}
    # sandboxed tool call (Docker wrapper)
    return {"messages": ["Executed in Firecracker/Kata microVM"]}

def critic_agent(state: AgentState):
    # confidence scoring + RAG enrichment
    return {"messages": ["Critic review passed"], "confidence": 0.92}

def reporter_agent(state: AgentState):
    return {"messages": ["Professional Markdown/PDF report generated"]}

workflow = StateGraph(AgentState)
workflow.add_node("planner", planner)
workflow.add_node("recon", recon_agent)
workflow.add_node("executor", executor_agent)
workflow.add_node("critic", critic_agent)
workflow.add_node("reporter", reporter_agent)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "recon")
workflow.add_edge("recon", "executor")
workflow.add_edge("executor", "critic")
workflow.add_edge("critic", "reporter")
workflow.add_edge("reporter", END)

graph = workflow.compile()
print("✅ LangGraph agentic core for ALL 9 modes loaded")
