import os
import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from typing import Any,List
from langchain_core.runnables import RunnableConfig

from src.agent.graph import graph, AgentState
from src.api.schemas import ChatRequest, ChatResponse, MessageSchma, ApproveRequest


app = FastAPI(title = "Logistics SLA Copilot API")
logger = logging.getLogger(__name__)

origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def get_pending_action(state: Any) -> Any:
    """Returns the interrupted tool call so the UI can recover after refresh."""
    if not state.next:
        return None

    messages = state.values.get("messages", [])
    last_message = messages[-1] if messages else None

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return last_message.tool_calls[0]

    return None

@app.get("/test")
def testing():
    if graph:
        return "SUCCESS!"


@app.post("/chat")
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    config : RunnableConfig = {"configurable" : {"thread_id" : payload.thread_id}}
    input_data : AgentState = {"messages": [HumanMessage(content=payload.messages)]}

    try:
        graph.invoke(input_data, config)
        state = graph.get_state(config)

        is_paused = bool(state.next)
        pending_action = get_pending_action(state)

        formatted_history = format_messages(state.values.get("messages", []))

        return ChatResponse(
            thread_id = payload.thread_id,
            messages = formatted_history,
            is_paused = is_paused,
            pending_action = pending_action, 
        )

    except Exception:
        logger.exception("Agent execution failed in /chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The assistant could not complete that request. Please try again.",
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

            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No pending tool call to reject.",
                )

            tool_call_id = last_message.tool_calls[0]["id"]

            rejection_message = ToolMessage(
                content=f"User rejected the penalty application. Reason: {payload.reason or 'User manually declined in UI.'}",
                tool_call_id=tool_call_id,
            )

            graph.update_state(config, {"messages": [rejection_message]}, as_node="SENSITIVE_TOOLS")
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

    except Exception:
        logger.exception("Agent execution failed in /action")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The requested action could not be completed. Please try again.",
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
        is_paused = bool(state.next),
        pending_action = get_pending_action(state),
    )
