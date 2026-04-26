import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.store.session_store import session_store

router = APIRouter(tags=["session"])


class CreateSessionRequest(BaseModel):
    initial_idea: str = Field(..., min_length=1, max_length=2000)


class SessionResponse(BaseModel):
    session_id: str
    status: str


@router.post("/session", response_model=SessionResponse)
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    session = session_store.create(session_id, req.initial_idea)
    return SessionResponse(session_id=session_id, status=session.status)


class SessionStateResponse(BaseModel):
    session_id: str
    status: str
    initial_idea: str
    current_dimension: str
    completed_dimensions: list[str]
    dialogue_complete: bool


@router.get("/session/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    from app.services.dialogue_engine import DIMENSIONS
    dialogue_complete = len(session.completed_dimensions) >= len(DIMENSIONS)

    return SessionStateResponse(
        session_id=session.id,
        status=session.status,
        initial_idea=session.initial_idea,
        current_dimension=session.current_dimension,
        completed_dimensions=session.completed_dimensions,
        dialogue_complete=dialogue_complete,
    )


class SessionListItem(BaseModel):
    session_id: str
    initial_idea: str
    status: str
    created_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionListItem]


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    sessions = session_store.list_all()
    items = [
        SessionListItem(
            session_id=s.id,
            initial_idea=s.initial_idea,
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=items)


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session_store.delete(session_id)
    return {"message": "ok"}
