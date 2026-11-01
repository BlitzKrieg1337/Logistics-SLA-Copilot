from typing import List, Optional, Dict, Any
from pydantic import BaseModel, model_validator


class ChatRequest(BaseModel):
    thread_id: str
    message: Optional[str] = None
    messages: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_message_field(cls, data: Any):
        if isinstance(data, dict):
            if "message" not in data and "messages" in data:
                data["message"] = data["messages"]
            elif "messages" not in data and "message" in data:
                data["messages"] = data["message"]
        return data


class MessageSchema(BaseModel):
    role: str
    content: str


# Backward-compatible alias
MessageSchma = MessageSchema


class ChatResponse(BaseModel):
    thread_id: str
    messages: List[MessageSchema]
    is_paused: bool = False
    pending_action: Optional[Dict[str, Any]] = None


class ApproveRequest(BaseModel):
    thread_id: str
    action: str
    reason: Optional[str] = None
