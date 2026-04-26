import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.session import Session
from app.models.dialogue import Message
from app.models.requirement import DesignRequirement, Dimension, DimensionField

logger = logging.getLogger(__name__)

STORE_DIR = Path(__file__).parent.parent.parent / "data" / "sessions"


def _serialize_session(session: Session) -> dict:
    messages = []
    for m in session.messages:
        msg = {"role": m.role, "content": m.content}
        if m.timestamp:
            msg["timestamp"] = m.timestamp.isoformat()
        messages.append(msg)

    requirement = None
    if session.requirement:
        dims = []
        for d in session.requirement.dimensions:
            fields = [{"key": f.key, "label": f.label, "value": f.value, "editable": f.editable} for f in d.fields]
            dims.append({"key": d.key, "label": d.label, "fields": fields})
        requirement = {"dimensions": dims, "version": session.requirement.version}

    return {
        "id": session.id,
        "initial_idea": session.initial_idea,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "messages": messages,
        "requirement": requirement,
        "candidates": session.candidates,
        "current_dimension": session.current_dimension,
        "completed_dimensions": session.completed_dimensions,
        "dimension_summaries": session.dimension_summaries,
        "dimension_message_start": session.dimension_message_start,
    }


def _deserialize_session(data: dict) -> Session:
    messages = []
    for m in data.get("messages", []):
        ts = m.get("timestamp")
        messages.append(Message(
            role=m["role"],
            content=m["content"],
            timestamp=datetime.fromisoformat(ts) if ts else None,
        ))

    requirement = None
    req_data = data.get("requirement")
    if req_data:
        dims = []
        for d in req_data.get("dimensions", []):
            fields = [DimensionField(**f) for f in d.get("fields", [])]
            dims.append(Dimension(key=d["key"], label=d["label"], fields=fields))
        requirement = DesignRequirement(dimensions=dims, version=req_data.get("version", 1))

    return Session(
        id=data["id"],
        initial_idea=data.get("initial_idea", ""),
        status=data.get("status", "dialogue"),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        messages=messages,
        requirement=requirement,
        candidates=data.get("candidates"),
        current_dimension=data.get("current_dimension", "form_size"),
        completed_dimensions=data.get("completed_dimensions", []),
        dimension_summaries=data.get("dimension_summaries", {}),
        dimension_message_start=data.get("dimension_message_start", 0),
    )


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _session_file(self, session_id: str) -> Path:
        return STORE_DIR / f"{session_id}.json"

    def _load_all(self):
        if not STORE_DIR.exists():
            return
        for f in STORE_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                session = _deserialize_session(data)
                self._sessions[session.id] = session
            except Exception:
                logger.exception("Failed to load session from %s", f)

    def _persist(self, session_id: str):
        session = self._sessions.get(session_id)
        if not session:
            return
        try:
            path = self._session_file(session_id)
            path.write_text(
                json.dumps(_serialize_session(session), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist session %s", session_id)

    def create(self, session_id: str, initial_idea: str) -> Session:
        session = Session(id=session_id, initial_idea=initial_idea)
        self._sessions[session_id] = session
        self._persist(session_id)
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update(self, session_id: str, session: Session) -> None:
        self._sessions[session_id] = session
        self._persist(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        path = self._session_file(session_id)
        if path.exists():
            path.unlink()

    def list_all(self) -> list[Session]:
        sessions = sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)
        return sessions


session_store = SessionStore()
