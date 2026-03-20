import httpx
from transformers import pipeline
from app.core.config import settings

# Load sentiment pipeline once (at module level)
sentiment_pipeline = pipeline("sentiment-analysis")

async def get_news_sentiment(vendor_name: str):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": vendor_name,
        "from": "2026-02-01",  # last 30 days
        "sortBy": "relevancy",
        "apiKey": settings.newsapi_key
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        articles = data.get('articles', [])[:5]
    
    if not articles:
        return 0.0
    
    scores = []
    for article in articles:
        result = sentiment_pipeline(article['title'])[0]
        score = result['score'] if result['label'] == 'POSITIVE' else -result['score']
        scores.append(score)
    return sum(scores)/len(scores)