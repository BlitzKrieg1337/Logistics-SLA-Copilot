from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    thread_id : str
    messages : str

class MessageSchma(BaseModel):
    role : str
    content : str 

class ChatResponse(BaseModel):
    thread_id : str
    messages : List[MessageSchma]
    is_paused : bool = False
    pending_action : Optional[Dict[str, Any]] = None

class ApproveRequest(BaseModel):
    thread_id : str
    action : str
    reason : Optional[str] = None
