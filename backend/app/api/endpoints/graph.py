from fastapi import APIRouter, HTTPException
from app.services.graph_db import VendorGraph
from app.api.endpoints.ws import manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
graph = VendorGraph()

@router.get("/vendors")
async def get_all_vendors():
    try:
        return graph.get_all_vendors()
    except Exception as e:
        logger.error(f"Database error in get_all_vendors: {e}")
        return []

@router.get("/vendor/{vendor_id}")
async def get_vendor_detail(vendor_id: str):
    try:
        data = graph.get_vendor(vendor_id)
        if not data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in get_vendor_detail: {e}")
        return {
            "id": vendor_id, 
            "name": "Unknown (DB Offline)", 
            "risk_score": 0, 
            "tier": "low", 
            "subcontractors": []
        }

@router.get("/")
async def get_graph_data():
    try:
        return graph.get_graph_elements()
    except Exception as e:
        logger.error(f"Database error in get_graph_data: {e}")
        return {"nodes": [], "edges": []}

@router.post("/simulate/{subcontractor_id}")
async def simulate_risk_event(subcontractor_id: str):
    try:
        vendor = graph.get_vendor(subcontractor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Subcontractor not found")
            
        # Example simulation logic: add 30 to risk, cap at 99.99
        new_risk = min(99.99, float(vendor.get("risk_score", 50)) + 30.0)
        
        if new_risk >= 70:
            tier = "critical"
        elif new_risk >= 40:
            tier = "medium"
        else:
            tier = "low"
            
        graph.add_vendor(
            subcontractor_id, 
            vendor.get("name", "Unknown"), 
            round(new_risk, 2), 
            tier, 
            vendor.get("type", "subvendor")
        )
        
        await manager.broadcast({"type": "graph_updated"})
        return {"message": f"Simulation executed for {subcontractor_id}", "new_risk": round(new_risk, 2)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simulate_risk_event: {e}")
        raise HTTPException(status_code=500, detail="Simulation failed")
