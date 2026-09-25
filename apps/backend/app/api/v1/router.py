"""Mounts every feature router under /api/v1. Features are added here as they're built."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# router.include_router(memories.router)
# router.include_router(reminders.router)
