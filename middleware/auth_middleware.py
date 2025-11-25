from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

class UserRoleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Create DB session manually for middleware
        db: Session = SessionLocal()

        request.state.current_user = None
        request.state.current_role = None

        try:
            # Example: get user_id from session
            user_id = request.session.get("user_id")

            if user_id:
                user = db.query(User).filter(
                    User.id == user_id,
                    User.status == "Y"
                ).first()
                
                if user:
                    request.state.current_user = user
                    request.state.current_role = user.role

            response = await call_next(request)
        finally:
            db.close()

        return response
