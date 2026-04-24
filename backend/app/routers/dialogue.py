import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
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


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
    dimension_progress: dict
    dialogue_complete: bool


@router.post("/dialogue/message")
async def send_message(req: DialogueRequest, request: Request) -> StreamingResponse:
    """Stream a dialogue response as SSE events."""
    session = session_store.get(req.session_id)
    if session is None:
        return StreamingResponse(
            iter([
                f"event: error\ndata: {json.dumps({'code': 'not_found', 'message': '会话不存在'}, ensure_ascii=False)}\n\n"
            ]),
            media_type="text/event-stream",
        )

    # Handle skip_to_next: force-advance dimension
    if req.skip_to_next:
        return await _handle_skip_to_next(req.session_id, session)

    if not req.content.strip():
        return StreamingResponse(
            iter([
                f"event: error\ndata: {json.dumps({'code': 'empty_message', 'message': '消息不能为空'}, ensure_ascii=False)}\n\n"
            ]),
            media_type="text/event-stream",
        )

    # Add user message to session
    user_msg = Message(role="user", content=req.content.strip())
    session.messages.append(user_msg)

    async def _stream_and_save():
        full_content = ""
        async for event in dialogue_chat(session, req.content):
            if event.startswith("event: done"):
                try:
                    data_str = event.split("data: ", 1)[1].strip()
                    data = json.loads(data_str)
                    full_content = data.get("message", {}).get("content", "")
                except (IndexError, json.JSONDecodeError):
                    pass
            yield event

        if full_content:
            assistant_msg = Message(
                role="assistant",
                content=full_content,
                timestamp=datetime.now(),
            )
            session.messages.append(assistant_msg)
            session_store.update(req.session_id, session)

    return StreamingResponse(
        _stream_and_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _handle_skip_to_next(session_id: str, session) -> StreamingResponse:
    """Force-advance to the next dimension and generate an opening question."""
    all_done = force_advance_dimension(session)
    session_store.update(session_id, session)

    if all_done:
        async def _done_stream():
            metadata = {
                "dimension_progress": _get_dimension_progress(session),
                "dialogue_complete": True,
            }
            yield f"event: metadata\ndata: {json.dumps(metadata, ensure_ascii=False)}\n\n"
            done_data = {
                "message": {"role": "assistant", "content": "好的，我们已经完成了所有维度的信息收集。"},
                "options": None,
                "dimension_progress": _get_dimension_progress(session),
                "dialogue_complete": True,
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            assistant_msg = Message(
                role="assistant",
                content="好的，我们已经完成了所有维度的信息收集。",
                timestamp=datetime.now(),
            )
            session.messages.append(assistant_msg)
            session_store.update(session_id, session)

        return StreamingResponse(
            _done_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    # Not all done — generate opening question for the new dimension
    next_label = DIMENSION_LABELS.get(session.current_dimension, "")
    transition_msg = Message(role="user", content=f"让我们聊聊{next_label}方面吧")
    session.messages.append(transition_msg)
    session_store.update(session_id, session)

    async def _stream_new_dimension():
        full_content = ""
        async for event in dialogue_chat(session, transition_msg.content):
            if event.startswith("event: done"):
                try:
                    data_str = event.split("data: ", 1)[1].strip()
                    data = json.loads(data_str)
                    full_content = data.get("message", {}).get("content", "")
                except (IndexError, json.JSONDecodeError):
                    pass
            yield event

        if full_content:
            assistant_msg = Message(
                role="assistant",
                content=full_content,
                timestamp=datetime.now(),
            )
            session.messages.append(assistant_msg)
            session_store.update(session_id, session)

    return StreamingResponse(
        _stream_new_dimension(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/dialogue/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Return full message history and dimension progress for a session."""
    session = session_store.get(session_id)
    if session is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")

    from app.services.dialogue_engine import _get_dimension_progress, DIMENSIONS

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
