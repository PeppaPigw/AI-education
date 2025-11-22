from typing import Optional, Dict, Any
import secrets
from datetime import datetime, timedelta


class SessionManager:
    def __init__(self):
        self._sessions = {}
        self._session_timeout = timedelta(hours=24)

    def create_session(self, username: str, user_type: str, user_data: Dict[str, Any]) -> str:
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = {
            "username": username,
            "user_type": user_type,
            "user_data": user_data,
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        if datetime.now() - session["last_accessed"] > self._session_timeout:
            del self._sessions[session_id]
            return None
        
        session["last_accessed"] = datetime.now()
        return session

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

    def cleanup_expired_sessions(self):
        expired = [
            sid for sid, session in self._sessions.items()
            if datetime.now() - session["last_accessed"] > self._session_timeout
        ]
        for sid in expired:
            del self._sessions[sid]


_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    return _session_manager

