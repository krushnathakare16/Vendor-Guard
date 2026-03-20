from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import time
from app.services.data_sources import security_score, news_sentiment, financial, subcontractor
from app.services.graph_db import VendorGraph
from app.services.predictor import RiskPredictor
from app.models.schemas import VendorProfile

router = APIRouter()
predictor = RiskPredictor()
graph = VendorGraph()

class OnboardRequest(BaseModel):
    vendor_name: str
    domain: str = None

@router.post("/seed")
async def seed_data():
    # Clear existing data optionally? We'll just merge it.
    vendors = [
        {"id": "V0001", "name": "Acme Finance", "risk": 45.2, "tier": "medium", "type": "vendor"},
        {"id": "V0002", "name": "Amazon Web Services", "risk": 15.1, "tier": "low", "type": "subvendor"},
        {"id": "V0003", "name": "Stripe Payments", "risk": 22.4, "tier": "low", "type": "subvendor"},
        {"id": "V0004", "name": "Global Support Solutions", "risk": 78.9, "tier": "critical", "type": "vendor"},
        {"id": "V0005", "name": "Twilio SMS", "risk": 28.5, "tier": "low", "type": "subvendor"},
        {"id": "V0006", "name": "DarkMarket APIs", "risk": 92.1, "tier": "critical", "type": "subvendor"}
    ]
    for v in vendors:
        graph.add_vendor(v["id"], v["name"], v["risk"], v["tier"], v.get("type", "vendor"))
    
    # Dependencies
    deps = [
        ("V0001", "V0002", 1.0), # Acme uses AWS
        ("V0001", "V0003", 0.9), # Acme uses Stripe
        ("V0003", "V0002", 1.0), # Stripe uses AWS
        ("V0001", "V0004", 0.5), # Acme uses Global Support
        ("V0001", "V0005", 0.4), # Acme uses Twilio
        ("V0004", "V0006", 0.9), # Support uses DarkMarket APIs
    ]
    for s, t, c in deps:
        graph.add_dependency(s, t, c)
        
    return {"message": "Ecosystem data successfully seeded!"}

@router.post("/")
async def onboard_vendor(req: OnboardRequest):
    start_time = time.time()
    
    # Use provided domain or construct from vendor name
    domain = req.domain or f"{req.vendor_name.lower().replace(' ', '')}.com"
    
    # Step 1: Gather data from multiple sources in parallel
    tasks = [
        security_score.get_security_score(domain),
        news_sentiment.get_news_sentiment(req.vendor_name),
        financial.get_financial_health(req.vendor_name),
        subcontractor.discover_subcontractors_simple(req.vendor_name)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle errors gracefully (use fallback values)
    security = results[0] if not isinstance(results[0], Exception) else 65
    sentiment = results[1] if not isinstance(results[1], Exception) else 0.0
    
    # Financial might fail for private companies
    if isinstance(results[2], Exception) or results[2] is None:
        financial_health = 60  # Default moderate score
    else:
        financial_health = results[2].get("financial_score", 60)
    
    subs = results[3] if not isinstance(results[3], Exception) else []

    # Step 2: Build feature vector for prediction
    # For hackathon, we'll simulate lagged features using current values
    feature_vector = {
        'security_score_lag3': security,
        'financial_score_lag3': financial_health,
        'news_sentiment_lag3': sentiment,
        'negative_mentions_lag3': 0,  # Would need history
        'layoff_detected_lag3': 0
    }
    
    risk_prob = predictor.predict(feature_vector)

    # Step 3: Store in graph DB
    import hashlib
    vendor_id = f"V{int(hashlib.md5(req.vendor_name.encode()).hexdigest()[:8], 16) % 10000:04d}"
    
    # Determine exact 3-level risk tier based on numerical thresholds
    if risk_prob >= 70:
        tier = "critical"
    elif risk_prob >= 40:
        tier = "medium"
    else:
        tier = "low"
    
    graph.add_vendor(vendor_id, req.vendor_name, risk_prob, tier, "vendor")
    
    # Add subcontractors
    for sub in subs[:5]:  # Limit to 5 for demo
        sub_id = f"S{int(hashlib.md5(sub.encode()).hexdigest()[:8], 16) % 10000:04d}"
        graph.add_vendor(sub_id, sub, 50, "medium", "subvendor")  # Standardize placeholder risk to medium
        graph.add_dependency(vendor_id, sub_id, 0.8)

    elapsed = round(time.time() - start_time, 1)
    
    # Step 4: Return profile
    return {
        "id": vendor_id,
        "name": req.vendor_name,
        "domain": domain,
        "risk_score": round(risk_prob, 1),
        "risk_level": tier.upper(),
        "security_score": security,
        "financial_score": financial_health,
        "news_sentiment": round(sentiment, 2),
        "subcontractors": subs[:5],
        "onboarding_time_sec": elapsed,
        "data_sources": {
            "security": "Mozilla Observatory + SSL Labs + Basic Checks",
            "news": "NewsAPI + Hugging Face",
            "financial": "Alpha Vantage (public) / Synthetic (private)",
            "subcontractors": "Crunchbase + NLP"
        },
        "message": f"✅ {req.vendor_name} onboarded successfully in {elapsed} seconds"
    }