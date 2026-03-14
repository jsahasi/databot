from fastapi import APIRouter

from app.api import analytics, calendar, chat, events, feedback, hierarchy, sync

api_router = APIRouter()
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(calendar.router, tags=["calendar"])
api_router.include_router(hierarchy.router, tags=["hierarchy"])
