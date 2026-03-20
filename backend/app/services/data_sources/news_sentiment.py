import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
sentiment_pipeline = None

def get_pipeline():
    global sentiment_pipeline
    if sentiment_pipeline is None:
        try:
            from transformers import pipeline
            sentiment_pipeline = pipeline("sentiment-analysis")
        except Exception as e:
            logger.error(f"Failed to load HuggingFace pipeline: {e}")
            sentiment_pipeline = "fallback"
    return sentiment_pipeline

async def get_news_sentiment(vendor_name: str):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": vendor_name,
        "from": "2026-02-01",  # last 30 days
        "sortBy": "relevancy",
        "apiKey": settings.newsapi_key
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            articles = data.get('articles', [])[:5]
    except Exception as e:
        logger.error(f"News API error: {e}")
        return 0.0
    
    if not articles:
        return 0.0
    
    pipe = get_pipeline()
    if pipe == "fallback":
        return 0.0
        
    scores = []
    for article in articles:
        try:
            result = pipe(article['title'])[0]
            score = result['score'] if result['label'] == 'POSITIVE' else -result['score']
            scores.append(score)
        except Exception:
            pass
            
    return sum(scores)/len(scores) if scores else 0.0