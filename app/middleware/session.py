from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.sessions = {}
        self.session_cookie = "session_id"
        self.session_expiry = timedelta(days=1)

    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get(self.session_cookie)
        
        # Create new session if none exists or if session expired
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                "created_at": datetime.now(),
                "data": {}
            }
        
        # Store session in request state
        request.state.session = self.sessions[session_id]["data"]
        
        # Process the request
        response = await call_next(request)
        
        # Set session cookie in response
        response.set_cookie(
            key=self.session_cookie,
            value=session_id,
            expires=self.session_expiry.total_seconds(),
            httponly=True
        )
        
        return response

    def get_session(self, request: Request) -> Dict[str, Any]:
        """Get session data for a request"""
        if not hasattr(request, "state"):
            session_id = request.cookies.get(self.session_cookie)
            if not session_id or session_id not in self.sessions:
                session_id = str(uuid.uuid4())
                self.sessions[session_id] = {
                    "created_at": datetime.now(),
                    "data": {}
                }
            request.state.session = self.sessions[session_id]["data"]
        return request.state.session