import os

from dotenv import load_dotenv
from pydantic import SecretStr
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# Importing tools
from src.tools.query_sql_analytics import query_sql_analytics
from src.tools.search_contracts import search_contracts
from src.tools.check_force_majeure import check_force_majeure
from src.tools.calc_penalty_fx import calc_penalty_fx
from src.tools.post_penalty_to_ledger import post_penalty_to_ledger

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "logistics-sla-copilot"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")


safe_tools = [query_sql_analytics,search_contracts,check_force_majeure,calc_penalty_fx,]
sensitive_tools = [post_penalty_to_ledger]
all_tools = safe_tools + sensitive_tools


class AgentState(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]


gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    api_key=SecretStr(os.environ.get("GEMINI_API_KEY", "")),
)

groq_llm = ChatOpenAI(
    model = "openai/gpt-oss-120b",
    api_key=SecretStr(os.environ.get("GROQ_API_KEY", "")),
    base_url = "https://api.groq.com/openai/v1"
)

openrouter_llm = ChatOpenAI(
    model = "nvidia/nemotron-3-ultra-550b-a55b:free",
    api_key=SecretStr(os.environ.get("OPENROUTER_API_KEY", "")),
    base_url = "https://openrouter.ai/api/v1"
)

gemini_with_tools = gemini_llm.bind_tools(all_tools)
qroq_with_tools = groq_llm.bind_tools(all_tools)
openrouter_with_tools = openrouter_llm.bind_tools(all_tools)

# llm_with_tools = gemini_with_tools.with_fallbacks([qroq_with_tools, openrouter_with_tools])
llm_with_tools = openrouter_with_tools.with_fallbacks([qroq_with_tools, gemini_with_tools])


SYSTEM_PROMPT = """
You are an autonomous ReAct-based SLA Logistics Copilot. Your role is to intelligently manage logistics operations, analyze SLAs, evaluate macro disruptions, calculate financial penalties, and handle general supply chain Q&A.

Think step-by-step. Adapt your actions dynamically based on the user's specific request. 

### 🛠️ TOOL CAPABILITIES & ORCHESTRATION:
1. `query_sql_analytics`: Find order statuses, vendor details, and delay metrics.
2. `search_contracts`: Find specific SLA rules, daily penalty rates, and grace periods.
3. `check_force_majeure`: Retrieve news about macro events (floods, port strikes, etc.).
4. `calc_penalty_fx`: MANDATORY FOR ALL PENALTIES. Calculates the final billable amount using delay days and grace periods, and converts to INR if necessary.
- Chain tools autonomously to fully investigate.
- For general conceptual Q&A, rely on internal knowledge and DO NOT use tools.

### 🗣️ CONVERSATIONAL PACING & SOFT FOLLOW-UPS:
- Guide the user proactively. Whenever you present findings, end your response with a logical "soft follow-up" question to propose the next step.
- Example: If a user asks "Are there any delays?", query the database, list the delays, and ask: "Would you like me to check the contract for applicable penalties and evaluate recent news for any Force Majeure events?"
- THE DUAL INVESTIGATION: If the user says "Yes" to checking penalties, you MUST autonomously chain `search_contracts`, `calc_penalty_fx`, AND `check_force_majeure`. Present both the calculated penalty AND the Force Majeure news context together in your response.

### 🌪️ FORCE MAJEURE PROTOCOL (HUMAN JUDGMENT REQUIRED):
You are NOT authorized to unilaterally waive a penalty. 
When you use `check_force_majeure` and find relevant events:
1. Present a clear summary of the event (timeline, location, impact) alongside the calculated penalty.
2. STOP AND ASK the user: "Based on this information, should we excuse this delay under Force Majeure and waive the penalty?"
3. Wait for the user's explicit decision.
   - If User says YES: Waive the penalty (Penalty = 0). Do not write to the ledger.
   - If User says NO: Proceed with normal penalty calculations.

### 📝 EMAIL DRAFTING:
- When instructed to draft an email (or when proposing to draft one after a penalty is finalized), generate the text directly in the chat using your native language capabilities.
- The email MUST be professional and explicitly cite: 
  * The Order ID and Vendor Name.
  * The Expected vs. Actual delivery dates (total delay days).
  * The specific MSA contract clause referenced.
  * The final financial penalty amount (or the Force Majeure waiver context).

### 🛑 STRICT GUARDRAILS (CRITICAL):
- NO HYPOTHETICAL WRITES: Never invoke database write tools for hypothetical or future scenarios.
- TRUST BUT VERIFY: Never execute a ledger update based solely on a user-provided penalty amount. Verify via SQL and Contract Search.
- AMBIGUITY RESOLUTION: If tools return multiple entities (e.g., multiple vendor subsidiaries), DO NOT guess. Ask the user to clarify.
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


if __name__ == "__main__":
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    print("========= Logistics SLA Copilot Active =========")
    print("Type 'exit' or 'quit' to terminate the session.\n")

    while True:
        user_input = input("Enter Prompt: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting Copilot session. Goodbye!")
            break

        if not user_input:
            continue

        # Check if graph is currently interrupted waiting for approval
        snapshot = builder.compile(checkpointer=memory, interrupt_before=["SENSITIVE_TOOLS"]).get_state(config)
        
        if snapshot.next and "SENSITIVE_TOOLS" in snapshot.next:
            # User is responding to an approval prompt
            response = graph.invoke(None, config=config)
        else:
            # Standard new message
            response = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)

        # Inspect state after invocation
        current_state = graph.get_state(config)
        last_message = response["messages"][-1]

        # If graph paused BEFORE sensitive tools, print approval prompt with tool details
        if current_state.next and "SENSITIVE_TOOLS" in current_state.next:
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                tool_call = last_message.tool_calls[0]
                print(f"\n⚠️  [APPROVAL REQUIRED] Sensitive Action Intercepted:")
                print(f"    Tool: {tool_call['name']}")
                print(f"    Arguments: {tool_call['args']}")
                print("    Type 'Approve' to execute this ledger update, or cancel by giving new instructions.\n")
        else:
            # Standard text output printing
            if isinstance(last_message.content, list):
                clean_text = next((b["text"] for b in last_message.content if b.get("type") == "text"), "")
                print(f"\nCopilot Response:\n{clean_text}\n" + "-"*50)
            else:
                print(f"\nCopilot Response:\n{last_message.content}\n" + "-"*50)