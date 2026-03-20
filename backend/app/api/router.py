from fastapi import APIRouter
from app.api.endpoints import onboarding, predict, graph

api_router = APIRouter()
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(predict.router, prefix="/predict", tags=["predict"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])