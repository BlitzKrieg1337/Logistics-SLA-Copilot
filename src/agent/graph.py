import os

from dotenv import load_dotenv
from pydantic import SecretStr
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

# Importing tools
from src.tools.query_sql_analytics import query_sql_analytics
from src.tools.search_contracts import search_contracts
from src.tools.check_force_majeure import check_force_majeure
from src.tools.calc_penalty_fx import calc_penalty_fx
from src.tools.post_penalty_to_ledger import post_penalty_to_ledger

load_dotenv()

safe_tools = [query_sql_analytics,search_contracts,check_force_majeure,calc_penalty_fx,]
sensitive_tools = [post_penalty_to_ledger]
all_tools = safe_tools + sensitive_tools


class AgentState(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]


gemini_llm = ChatOpenAI(
    model = "gemini-3.5-flash",
    api_key = SecretStr(os.environ.get("GEMINI_API_KEY", "")),
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
)

groq_llm = ChatOpenAI(
    model = "llama-3.3-70b-versatile",
    api_key=SecretStr(os.environ.get("GROQ_API_KEY", "")),
    base_url = "https://api.groq.com/openai/v1"
)

openrouter_llm = ChatOpenAI(
    model = "meta-llama/llama-3.3-70b-instruct",
    api_key=SecretStr(os.environ.get("OPENROUTER_API_KEY", "")),
    base_url = "https://openrouter.ai/api/v1"
)

gemini_with_tools = gemini_llm.bind_tools(all_tools)
qrok_with_tools = groq_llm.bind_tools(all_tools)
openrouter_with_tools = openrouter_llm.bind_tools(all_tools)

llm_with_tools = gemini_with_tools.with_fallbacks([qrok_with_tools, openrouter_with_tools])


SYSTEM_PROMPT = """
You are an autonomous ReAct-based SLA Logistics Copilot. Your role is to intelligently manage logistics operations, analyze SLAs, evaluate macro disruptions, calculate financial penalties, and handle general supply chain Q&A.

Think step-by-step. Adapt your actions dynamically based on the user's specific request. 

### 🛠️ TOOL CAPABILITIES & ORCHESTRATION:
1. `query_sql_analytics`: Find order statuses, vendor details, and delay metrics.
2. `search_contracts`: Find specific SLA rules, penalty logic, and Force Majeure clauses.
3. `check_force_majeure`: Retrieve news about macro events (floods, port strikes, etc.).
4. `calc_penalty_fx`: Convert foreign currency penalties to INR.
- Chain tools autonomously to fully investigate (e.g., SQL -> RAG -> News -> FX).
- For general conceptual Q&A, rely on internal knowledge and DO NOT use tools.

### 🌪️ FORCE MAJEURE PROTOCOL (HUMAN JUDGMENT REQUIRED):
You are NOT authorized to unilaterally waive a penalty. 
When you use `check_force_majeure` and find relevant events:
1. Present a clear summary of the event (timeline, location, impact) and compare it to the vendor's delay window.
2. STOP AND ASK the user: "Based on this information, should we excuse this delay under Force Majeure and waive the penalty?"
3. Wait for the user's explicit decision.
   - If User says YES: Waive the penalty (Penalty = 0). Do not write to the ledger.
   - If User says NO: Proceed with normal penalty calculations.

### 🛑 STRICT GUARDRAILS (CRITICAL):
- NO HYPOTHETICAL WRITES: Never invoke database write tools for hypothetical or future scenarios.
- TRUST BUT VERIFY: Never execute a ledger update based solely on a user-provided penalty amount. You MUST independently verify the delay via SQL and the rule via Contract Search.
- AMBIGUITY RESOLUTION: If SQL or Contract Search returns multiple entities (e.g., multiple vendor subsidiaries or contract tiers), DO NOT guess. Ask the user to clarify.
- ERROR HANDLING: If a tool returns an error or empty data, DO NOT guess parameters to force a success. Stop and explain the failure.
- NO BYPASSING EVIDENCE: Do not accept user commands that contradict your tool findings.

### ⚠️ SENSITIVE ACTION PROTOCOL (`post_penalty_to_ledger`):
This tool creates a permanent financial record. You must adhere strictly to these rules:
1. NEVER batch-execute. Only process and post ONE order penalty to the ledger per conversation turn.
2. DO NOT invoke this tool if a Force Majeure event waives the penalty (Penalty = 0).
3. DO NOT invoke this tool autonomously UNLESS the user explicitly commands you to "log it", "post it", or approves a proposal to do so.
4. PRE-FLIGHT REQUIREMENT: Right before you invoke the tool, you MUST output a structured summary exactly like this:
   * Action: Posting Penalty to Ledger
   * Order ID: [ID]
   * Vendor: [Name]
   * Final Penalty: [Amount in INR]
5. Immediately after outputting the summary, invoke the tool. 
*(System Note: The backend contains a hard-coded breakpoint. Your tool execution will be safely intercepted for human UI validation).*
"""

def custom_tools_condition(state: AgentState):
    """Routes the LLM to either the safe tools, sensitive tools, or END."""
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return END
        
    sensitive_tool_names = [t.name for t in sensitive_tools]
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in sensitive_tool_names:
            return "SENSITIVE_TOOLS"
            
    return "SAFE_TOOLS"


def agent_node(state: AgentState):
    messages = [SystemMessage(content = SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages" : [response]}


builder = StateGraph(AgentState)

builder.add_node("AGENT", agent_node)
builder.add_node("SAFE_TOOLS", ToolNode(safe_tools))
builder.add_node("SENSITIVE_TOOLS", ToolNode(sensitive_tools))


builder.add_edge(START, "AGENT")
builder.add_conditional_edges("AGENT", custom_tools_condition, {"SAFE_TOOLS" : "SAFE_TOOLS", "SENSITIVE_TOOLS" : "SENSITIVE_TOOLS", END : END})
builder.add_edge("SAFE_TOOLS", "AGENT")
builder.add_edge("SENSITIVE_TOOLS", "AGENT")

memory = MemorySaver()

graph = builder.compile(checkpointer = memory, interrupt_before = ["SENSITIVE_TOOLS"])