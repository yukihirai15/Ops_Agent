"""
OpsAgent — LangGraph state machine for autonomous DevOps incident response.
Flow: Prometheus alert → diagnose → query logs → suggest fix → notify Slack
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
#from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
#from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from tools.prometheus import query_prometheus
from tools.logs import check_logs
from tools.remediation import suggest_fix
from tools.slack import notify_slack
from config.settings import settings


# ─── Agent State ────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    alert: dict
    diagnosis: str
    fix: str
    notified: bool


# # ─── LLM + Tools ────────────────────────────────────────────────────────────

# tools = [query_prometheus, check_logs, suggest_fix, notify_slack]

# llm = ChatAnthropic(
#     model="claude-sonnet-4-6",
#     api_key=settings.anthropic_api_key,
#     temperature=0,
# ).bind_tools(tools)

# tool_node = ToolNode(tools)


# ─── ( Gloq ) LLM + Tools ────────────────────────────────────────────────────────────

tools = [query_prometheus, check_logs, suggest_fix, notify_slack]

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.groq_api_key,
    temperature=0,
).bind_tools(tools)

tool_node = ToolNode(tools)

MAX_STEPS = 8

# ─── Agent Node ─────────────────────────────────────────────────────────────

def agent_node(state: AgentState) -> AgentState:
    """Core reasoning node — LLM decides which tool to call next."""
    response = llm.invoke(state["messages"])
    return {
        "messages": [response],
        "step_count": state.get("step_count", 0) + 1,
    }
 
 
def should_continue(state: AgentState) -> str:
    """Route: call tools if LLM requested one, else end. Hard stop at MAX_STEPS."""
    if state.get("step_count", 0) >= MAX_STEPS:
        return END
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

# ─── Graph Assembly ─────────────────────────────────────────────────────────

def build_agent() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# ─── Entry Point ────────────────────────────────────────────────────────────

def run_agent(alert: dict) -> dict:
    agent = build_agent()
 
    instance = alert.get("instance", "unknown")
    service = instance.split(":")[0]
    alertname = alert.get("alertname", "Unknown")
    severity = alert.get("severity", "unknown")
    summary = alert.get("summary", "No summary provided")
 
    system_prompt = f"""You are OpsAgent, an autonomous DevOps incident-response agent.
 
A Prometheus alert has fired. You MUST call these 4 tools in EXACTLY this order, ONE AT A TIME:
 
TOOL 1 — query_prometheus
  Call with: metric='up{{instance="{instance}"}}'
 
TOOL 2 — check_logs
  Call with: service='{service}'
 
TOOL 3 — suggest_fix
  Call with: diagnosis='<your diagnosis based on steps 1 and 2>', service='{service}'
 
TOOL 4 — notify_slack
  Call with:
    alert_name='{alertname}'
    severity='{severity}'
    diagnosis='<same diagnosis from step 3>'
    fix_summary='<summary of the fix from step 3>'
    instance='{instance}'
 
ALERT DETAILS:
  - Alert Name : {alertname}
  - Severity   : {severity}
  - Instance   : {instance}
  - Summary    : {summary}
 
RULES:
- Call each tool EXACTLY ONCE
- Do NOT call query_prometheus more than once
- Do NOT skip any tool
- After calling notify_slack, stop immediately and do not call any more tools
"""
 
    initial_state: AgentState = {
        "messages": [HumanMessage(content=system_prompt)],
        "alert": alert,
        "diagnosis": "",
        "fix": "",
        "notified": False,
        "step_count": 0,
    }
 
    result = agent.invoke(initial_state)
    return result

