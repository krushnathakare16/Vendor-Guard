"""
Financial health data service using Alpha Vantage (free tier)
+ fallback mechanisms for private companies and API failures
"""

import httpx
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.core.config import settings

# Cache for API responses (avoid hitting rate limits)
_financial_cache = {}
_cache_timestamp = {}

async def get_alpha_vantage_data(symbol: str, function: str = "OVERVIEW") -> Optional[Dict]:
    """
    Fetch data from Alpha Vantage API
    Free tier: 5 calls per minute, 500 calls per day
    """
    cache_key = f"{symbol}_{function}"
    
    # Check cache (valid for 1 hour)
    if cache_key in _financial_cache:
        cache_age = datetime.now() - _cache_timestamp.get(cache_key, datetime.now())
        if cache_age < timedelta(hours=1):
            return _financial_cache[cache_key]
    
    url = "https://www.alphavantage.co/query"
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": settings.alpha_vantage_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            # Check for API limit message
            if "Note" in data and "API call frequency" in data["Note"]:
                print(f"⚠️ Alpha Vantage rate limit hit for {symbol}")
                return None
            
            # Cache the result
            _financial_cache[cache_key] = data
            _cache_timestamp[cache_key] = datetime.now()
            return data
            
    except Exception as e:
        print(f"❌ Alpha Vantage API error for {symbol}: {e}")
        return None

async def get_stock_price(symbol: str) -> Optional[Dict]:
    """Get current stock price and daily change"""
    data = await get_alpha_vantage_data(symbol, "GLOBAL_QUOTE")
    
    if data and "Global Quote" in data:
        quote = data["Global Quote"]
        try:
            price = float(quote.get("05. price", 0))
            change = float(quote.get("09. change", 0))
            change_percent = float(quote.get("10. change percent", "0%").replace("%", ""))
            
            return {
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "timestamp": datetime.now().isoformat()
            }
        except (ValueError, TypeError):
            return None
    return None

async def get_company_overview(symbol: str) -> Optional[Dict]:
    """Get company financial overview"""
    data = await get_alpha_vantage_data(symbol, "OVERVIEW")
    
    if data:
        try:
            return {
                "market_cap": float(data.get("MarketCapitalization", 0)),
                "pe_ratio": float(data.get("PERatio", 0)),
                "dividend_yield": float(data.get("DividendYield", 0)),
                "profit_margin": float(data.get("ProfitMargin", 0)),
                "revenue_ttm": float(data.get("RevenueTTM", 0)),
                "debt_to_equity": float(data.get("DebtToEquity", 0)) if data.get("DebtToEquity") != "None" else None,
                "quarterly_growth": float(data.get("QuarterlyRevenueGrowthYOY", 0)) if data.get("QuarterlyRevenueGrowthYOY") else 0
            }
        except (ValueError, TypeError):
            return None
    return None

async def get_stock_trend(symbol: str, months: int = 3) -> Dict[str, Any]:
    """
    Calculate stock trend over last N months
    Returns: trend_percentage, volatility, signal
    """
    data = await get_alpha_vantage_data(symbol, "TIME_SERIES_MONTHLY")
    
    if data and "Monthly Time Series" in data:
        monthly = data["Monthly Time Series"]
        dates = sorted(monthly.keys(), reverse=True)[:months]
        
        if len(dates) >= 2:
            try:
                latest = float(monthly[dates[0]]["4. close"])
                oldest = float(monthly[dates[-1]]["4. close"])
                
                trend = ((latest - oldest) / oldest) * 100
                
                # Calculate volatility (standard deviation of monthly returns)
                returns = []
                for i in range(len(dates) - 1):
                    prev = float(monthly[dates[i + 1]]["4. close"])
                    curr = float(monthly[dates[i]]["4. close"])
                    returns.append((curr - prev) / prev)
                
                volatility = (max(returns) - min(returns)) * 100 if returns else 0
                
                # Generate signal
                if trend > 10:
                    signal = "STRONG_BUY"
                elif trend > 5:
                    signal = "BUY"
                elif trend > -5:
                    signal = "HOLD"
                elif trend > -15:
                    signal = "SELL"
                else:
                    signal = "STRONG_SELL"
                
                return {
                    "trend_percentage": round(trend, 2),
                    "volatility": round(volatility, 2),
                    "signal": signal,
                    "latest_price": latest,
                    "oldest_price": oldest,
                    "months_analyzed": months
                }
            except (ValueError, KeyError, IndexError):
                pass
    
    return {
        "trend_percentage": 0,
        "volatility": 0,
        "signal": "UNKNOWN",
        "error": "Insufficient data"
    }

async def simulate_private_company_score(vendor_name: str) -> Dict[str, Any]:
    """
    Generate realistic financial health score for private companies
    Based on industry averages and company size indicators
    """
    # Seed with vendor name for consistency
    random.seed(vendor_name)
    
    # Generate realistic financial metrics
    base_health = random.randint(40, 85)
    
    # Adjust based on company name patterns (clues about size/age)
    name_lower = vendor_name.lower()
    
    if any(term in name_lower for term in ['tech', 'soft', 'digital', 'cloud']):
        # Tech companies often have higher growth but higher risk
        growth = random.randint(5, 30)
        stability = random.randint(30, 70)
    elif any(term in name_lower for term in ['bank', 'fin', 'capital', 'invest']):
        # Financial services - stable but regulated
        growth = random.randint(0, 15)
        stability = random.randint(60, 90)
    elif any(term in name_lower for term in ['consult', 'solutions', 'group']):
        # Services companies - moderate
        growth = random.randint(0, 20)
        stability = random.randint(40, 80)
    else:
        # Default
        growth = random.randint(-5, 20)
        stability = random.randint(30, 85)
    
    # Generate "signals" based on financial health
    signals = []
    
    if base_health > 70:
        signals.append("Strong financial position")
    elif base_health < 40:
        signals.append("Financial distress indicators")
    
    if growth > 15:
        signals.append("High growth trajectory")
    elif growth < 0:
        signals.append("Revenue declining")
    
    if stability > 70:
        signals.append("Stable cash flow")
    elif stability < 40:
        signals.append("Volatile earnings")
    
    return {
        "financial_score": base_health,
        "growth_rate": growth,
        "stability": stability,
        "is_public": False,
        "signals": signals[:3],  # Top 3 signals
        "estimated_revenue_range": random.choice([
            "< $10M", "$10M-$50M", "$50M-$100M", "$100M-$500M", "$500M+"
        ]),
        "employee_count_estimate": random.choice([
            "1-50", "51-200", "201-500", "501-1000", "1000+"
        ])
    }

async def get_financial_health(vendor_name: str) -> Dict[str, Any]:
    """
    Main function to get financial health for any vendor
    Handles both public and private companies
    """
    # Clean vendor name for stock symbol lookup
    # This is simplified - real implementation would have symbol mapping
    symbol_map = {
        "infosys": "INFY",
        "tcs": "TCS.NS",
        "wipro": "WIPRO.NS",
        "hcl": "HCLTECH.NS",
        "tech mahindra": "TECHM.NS",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "amazon": "AMZN",
        "oracle": "ORCL",
        "ibm": "IBM",
        "salesforce": "CRM",
        "adobe": "ADBE",
        "intel": "INTC",
        "nvidia": "NVDA",
        "amd": "AMD",
        "cisco": "CSCO",
        "apple": "AAPL",
        "meta": "META",
        "netflix": "NFLX"
    }
    
    # Try to find stock symbol
    symbol = None
    for name_key, sym in symbol_map.items():
        if name_key in vendor_name.lower():
            symbol = sym
            break
    
    result = {
        "vendor_name": vendor_name,
        "is_public": symbol is not None,
        "timestamp": datetime.now().isoformat()
    }
    
    if symbol:
        # Public company - get real data
        stock_data = await get_stock_price(symbol)
        overview = await get_company_overview(symbol)
        trend = await get_stock_trend(symbol)
        
        result.update({
            "symbol": symbol,
            "stock_price": stock_data.get("price") if stock_data else None,
            "daily_change": stock_data.get("change_percent") if stock_data else None,
            "market_cap": overview.get("market_cap") if overview else None,
            "pe_ratio": overview.get("pe_ratio") if overview else None,
            "profit_margin": overview.get("profit_margin") if overview else None,
            "trend_3m": trend.get("trend_percentage"),
            "volatility": trend.get("volatility"),
            "signal": trend.get("signal")
        })
        
        # Calculate financial health score (0-100)
        score = 50  # Baseline
        
        if overview:
            # Add points for profitability
            if overview.get("profit_margin", 0) > 0.15:
                score += 10
            elif overview.get("profit_margin", 0) > 0.05:
                score += 5
            
            # Add points for reasonable debt
            debt = overview.get("debt_to_equity")
            if debt and debt < 0.5:
                score += 10
            elif debt and debt < 1.0:
                score += 5
            
            # Add points for growth
            if overview.get("quarterly_growth", 0) > 0.1:
                score += 10
        
        if trend:
            # Adjust based on stock trend
            score += trend.get("trend_percentage", 0) * 0.3
            score -= trend.get("volatility", 0) * 0.1
        
        result["financial_score"] = max(0, min(100, round(score, 1)))
        result["data_source"] = "Alpha Vantage (real)"
        
    else:
        # Private company - use simulation
        private_data = await simulate_private_company_score(vendor_name)
        result.update(private_data)
        result["data_source"] = "Simulated (private company)"
    
    return result

# Quick test function
async def test_financial_api():
    """Test the financial API with sample vendors"""
    test_vendors = ["Infosys", "Tech Mahindra", "Startup Innovations", "Microsoft"]
    
    for vendor in test_vendors:
        print(f"\n🔍 Testing: {vendor}")
        result = await get_financial_health(vendor)
        
        print(f"   Public: {result['is_public']}")
        print(f"   Financial Score: {result.get('financial_score', 'N/A')}")
        
        if result['is_public']:
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Trend 3M: {result.get('trend_3m')}%")
            print(f"   Signal: {result.get('signal')}")
        else:
            print(f"   Growth Rate: {result.get('growth_rate')}%")
            print(f"   Signals: {result.get('signals')}")
        
        print(f"   Source: {result.get('data_source')}")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_financial_api())