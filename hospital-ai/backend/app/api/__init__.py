"""API router aggregation.

Future domain routers (patients, appointments, agents, etc.)
will be registered here. No business routers in Week 1 Step 1.
"""

from fastapi import APIRouter

from app.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
