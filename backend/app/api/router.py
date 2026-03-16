from fastapi import APIRouter

from app.api import admins, analytics, brand_templates, calendar, chat, events, feedback, hierarchy, prefetch, shares, sync, upload

api_router = APIRouter()
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(calendar.router, tags=["calendar"])
api_router.include_router(hierarchy.router, tags=["hierarchy"])
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(admins.router, tags=["admins"])
api_router.include_router(shares.router, prefix="/shares", tags=["shares"])
api_router.include_router(brand_templates.router, prefix="/brand-templates", tags=["brand-templates"])
api_router.include_router(prefetch.router, prefix="/prefetch", tags=["prefetch"])
