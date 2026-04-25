import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.dialogue import Message
from app.services.dialogue_engine import (
    chat as dialogue_chat,
    force_advance_dimension,
    _get_dimension_progress,
    DIMENSIONS,
    DIMENSION_LABELS,
)
from app.store.session_store import session_store

router = APIRouter(tags=["dialogue"])


class DialogueRequest(BaseModel):
    session_id: str
    content: str = Field(default="", max_length=5000)
    skip_to_next: bool = False


class DialogueResponse(BaseModel):
    content: str
    options: dict | None = None
    design_complete: bool = False
    dialogue_complete: bool = False
    dimension_progress: dict


class ErrorResponse(BaseModel):
    code: str
    message: str


@router.post("/dialogue/message", response_model=DialogueResponse)
async def send_message(req: DialogueRequest):
    session = session_store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    if req.skip_to_next:
        return await _handle_skip_to_next(req.session_id, session)

    if not req.content.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    user_msg = Message(role="user", content=req.content.strip())
    session.messages.append(user_msg)
    session_store.update(req.session_id, session)

    result = await dialogue_chat(session, req.content)

    if "code" in result:
        raise HTTPException(status_code=502, detail=result["message"])

    content = result["content"]
    options = result.get("options")
    dialogue_complete = result.get("dialogue_complete", False)
    dimension_progress = result.get("dimension_progress", _get_dimension_progress(session))

    assistant_msg = Message(role="assistant", content=content, timestamp=datetime.now())
    session.messages.append(assistant_msg)
    session_store.update(req.session_id, session)

    return DialogueResponse(
        content=content,
        options=options,
        design_complete=result.get("design_complete", False),
        dialogue_complete=dialogue_complete,
        dimension_progress=dimension_progress,
    )


async def _handle_skip_to_next(session_id: str, session) -> DialogueResponse:
    all_done = force_advance_dimension(session)
    session_store.update(session_id, session)

    if all_done:
        assistant_msg = Message(
            role="assistant",
            content="好的，我们已经完成了所有维度的信息收集。",
            timestamp=datetime.now(),
        )
        session.messages.append(assistant_msg)
        session_store.update(session_id, session)
        return DialogueResponse(
            content="好的，我们已经完成了所有维度的信息收集。",
            options=None,
            design_complete=True,
            dialogue_complete=True,
            dimension_progress=_get_dimension_progress(session),
        )

    next_label = DIMENSION_LABELS.get(session.current_dimension, "")
    transition_msg = Message(role="user", content=f"让我们聊聊{next_label}方面吧")
    session.messages.append(transition_msg)
    session_store.update(session_id, session)

    result = await dialogue_chat(session, transition_msg.content)

    if "code" in result:
        raise HTTPException(status_code=502, detail=result["message"])

    content = result["content"]
    options = result.get("options")
    dialogue_complete = result.get("dialogue_complete", False)
    dimension_progress = result.get("dimension_progress", _get_dimension_progress(session))

    assistant_msg = Message(role="assistant", content=content, timestamp=datetime.now())
    session.messages.append(assistant_msg)
    session_store.update(session_id, session)

    return DialogueResponse(
        content=content,
        options=options,
        design_complete=result.get("design_complete", False),
        dialogue_complete=dialogue_complete,
        dimension_progress=dimension_progress,
    )


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
    dimension_progress: dict
    dialogue_complete: bool


@router.get("/dialogue/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = [
        {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat() if m.timestamp else None}
        for m in session.messages
    ]

    return HistoryResponse(
        session_id=session_id,
        messages=messages,
        dimension_progress=_get_dimension_progress(session),
        dialogue_complete=len(session.completed_dimensions) >= len(DIMENSIONS),
    )
