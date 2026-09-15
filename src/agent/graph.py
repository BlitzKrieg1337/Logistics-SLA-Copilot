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