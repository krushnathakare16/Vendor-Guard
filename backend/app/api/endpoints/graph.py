from fastapi import APIRouter, HTTPException
from app.services.graph_db import VendorGraph

router = APIRouter()
graph = VendorGraph()

@router.get("/vendors")
async def get_all_vendors():
    try:
        return graph.get_all_vendors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vendor/{vendor_id}")
async def get_vendor_detail(vendor_id: str):
    try:
        data = graph.get_vendor(vendor_id)
        if not data:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_graph_data():
    try:
        return graph.get_graph_elements()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
