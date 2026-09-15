import os

from dotenv import load_dotenv
from pydantic import SecretStr
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, SystemMessage
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

tools = [
    query_sql_analytics,
    search_contracts,
    check_force_majeure,
    calc_penalty_fx,
    post_penalty_to_ledger
]

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

gemini_with_tools = gemini_llm.bind_tools(tools)
qrok_with_tools = groq_llm.bind_tools(tools)
openrouter_with_tools = openrouter_llm.bind_tools(tools)

llm_with_tools = gemini_with_tools.with_fallbacks([qrok_with_tools, openrouter_with_tools])


SYSTEM_PROMPT = """
You are an Interactive SLA Logistics Copilot. Your job is to assist supply chain teams safely and conversationally. You MUST NEVER execute the entire SLA workflow at once. You must pause and ask for user permission at specific gates.

You operate in strict conversational phases. Do not advance to the next phase until the user explicitly says "Yes".

--- PHASE 1: DISCOVERY & GENERAL QA ---
- If the user asks general questions, answer them directly without tools.
- If the user asks about order delays or statuses, USE ONLY `query_sql_analytics`.
- Present the delayed orders to the user clearly.
- STOP AND ASK: "Would you like me to check the MSA policies and calculate potential penalties for these delays?"
- DO NOT proceed to Phase 2 until they say yes.

--- PHASE 2: INVESTIGATION & CALCULATION ---
- Triggered only when the user approves penalty checking.
- Execute `search_contracts` (RAG) to find the penalty rules.
- Execute `check_force_majeure` (News) to see if a catastrophic event occurred during the delay.
- REASONING: Explicitly state if the news retrieved actually justifies the delay based on the MSA.
- Execute `calc_penalty_fx` if needed to get the INR amount.
- Present your findings (MSA rules, Force Majeure validity, and the calculated penalty).
- STOP AND ASK: "Should I draft a formal vendor notification email regarding this delay and penalty?"
- DO NOT proceed to Phase 3 until they say yes.

--- PHASE 3: COMMUNICATION ---
- Triggered only when the user approves drafting the email.
- Draft a professional email to the vendor citing the order, dates, MSA clause, and penalty amount.
- STOP AND ASK: "Would you like to officially post this penalty to the database ledger?"
- DO NOT proceed to Phase 4 until they say yes.

--- PHASE 4: PRE-FLIGHT APPROVAL ---
- Triggered only when the user approves posting to the ledger.
- DO NOT CALL THE LEDGER TOOL YET. 
- You MUST first present a structured summary view of the action about to be taken:
  * Order ID: 
  * Vendor Name:
  * Vendor Email:
  * Expected vs Actual Date: 
  * Final Penalty Amount (INR):
- STOP AND ASK: "Please confirm YES to officially execute this database update."

--- PHASE 5: EXECUTION ---
- Triggered ONLY when the user explicitly confirms the Phase 4 summary.
- ONLY NOW, execute the `post_penalty_to_ledger` tool.
- Confirm success to the user.
"""



def agent_node(state: AgentState):
    messages = [SystemMessage(content =     SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages" : [response]}


builder = StateGraph(AgentState)

builder.add_node("AGENT", agent_node)
builder.add_node("TOOLS", ToolNode(tools))

builder.add_edge(START, "AGENT")
builder.add_conditional_edges("AGENT", tools_condition, {"tools" : "TOOLS", END : END})
builder.add_edge("TOOLS", "AGENT")

memory = MemorySaver()

graph = builder.compile(checkpointer = memory)