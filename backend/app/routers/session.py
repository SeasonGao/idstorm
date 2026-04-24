import uuid

from fastapi import APIRouter
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
