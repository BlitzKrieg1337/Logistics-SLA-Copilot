from fastapi import FastAPI, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from typing import Any,List
from langchain_core.runnables import RunnableConfig

from src.agent.graph import graph, AgentState
from src.api.schemas import ChatRequest, ChatResponse, MessageSchma, ApproveRequest


app = FastAPI(title = "Logistics SLA Copilot API")

def format_messages(raw_messages: List[Any]) -> List[MessageSchma]:

    formatted = []
    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            formatted.append(MessageSchma(role = "user", content = str(msg.content)))
        elif isinstance(msg, AIMessage):
            formatted.append(MessageSchma(role = "assistant", content = str(msg.content)))
        elif isinstance(msg, ToolMessage):
            formatted.append(MessageSchma(role = "tool", content = str(msg.content)))
    return formatted


@app.get("/test")
def testing():
    if graph:
        return "TEST SUCCESS! Graph Imported"


@app.post("/chat")
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    config : RunnableConfig = {"configurable" : {"thread_id" : payload.thread_id}}
    input_data : AgentState = {"messages": [HumanMessage(content=payload.messages)]}

    try:
        graph.invoke(input_data, config)
        state = graph.get_state(config)

        is_paused = bool(state.next)
        pending_action = None

        if is_paused:
            last_message = state.values["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                pending_action = last_message.tool_calls[0]

        formatted_history = format_messages(state.values.get("messages", []))

        return ChatResponse(
            thread_id = payload.thread_id,
            messages = formatted_history,
            is_paused = is_paused,
            pending_action = pending_action, 
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution error: {str(e)}",
        )

@app.post("/action")
def handle_approval(payload : ApproveRequest) -> ChatResponse:

    config : RunnableConfig = {"configurable" : {"thread_id" : payload.thread_id}}
    state = graph.get_state(config)

    if not state.next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending approval found for this thread.",
        )

    try: 
        if payload.action.lower() == "approve":
            graph.invoke(None, config)

        elif payload.action.lower() == "reject":
            last_message = state.values["messages"][-1]
            tool_call_id = last_message.tool_call_id[0]["id"] if hasattr(last_message, "tool_calls" and last_message.tool_call_id) else "cancelled"

            rejection_message = ToolMessage(
                content = f"User rejected the penalty application. Reason: {payload.reason or 'User manually declined in UI.'}",
                tool_call_id = tool_call_id
            )

            graph.update_state(config, {"messages" : [rejection_message]}, as_node = "post_penalty_to_ledger")
            graph.invoke(None, config)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Must be 'approve' or 'reject'.",
            )

        updated_state = graph.get_state(config)
        formatted_history = format_messages(updated_state.values.get("messages", []))

        return ChatResponse(
            thread_id = payload.thread_id,
            messages = formatted_history,
            is_paused = bool(updated_state.next),
            pending_action = None
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution error: {str(e)}",
        )

@app.get("/history/{thread_id}")
def get_history(thread_id : str) -> ChatResponse:

    config :RunnableConfig = {"configurable" : {"thread_id" : thread_id}}
    state = graph.get_state(config)

    if not state.values:
        return ChatResponse(thread_id = thread_id, messages = [], is_paused = False)

    formatted_history = format_messages(state.values.get("messages", []))
    return ChatResponse(
        thread_id = thread_id,
        messages = formatted_history,
        is_paused = bool(state.next)
    )
    