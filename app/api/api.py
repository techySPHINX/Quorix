from fastapi import APIRouter
from .endpoints import auth, users, events, bookings, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
