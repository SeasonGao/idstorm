from typing import Optional

from app.models.session import Session


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, session_id: str, initial_idea: str) -> Session:
        session = Session(id=session_id, initial_idea=initial_idea)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update(self, session_id: str, session: Session) -> None:
        self._sessions[session_id] = session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_store = SessionStore()
