from fastapi import Header
from typing import Optional


async def get_session_id(x_session_id: Optional[str] = Header(default=None)):
    # Accept session id from header for conversational continuity
    return x_session_id or "anonymous"
