import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_vendor_history(vendor_id, months=24, will_fail=False, failure_month=18):
    """Generate realistic vendor history with optional failure pattern."""
    data = []
    base_security = np.random.uniform(70, 95)
    base_financial = np.random.uniform(70, 95)
    
    for month in range(months):
        if will_fail and month >= failure_month - 6:
            decline = (month - (failure_month - 6)) / 6
            security = base_security * (1 - 0.3 * decline) + np.random.normal(0, 2)
            financial = base_financial * (1 - 0.25 * decline) + np.random.normal(0, 2)
            sentiment = -0.3 * decline + np.random.normal(0, 0.1)
            negatives = int(5 * decline) + np.random.poisson(1)
            layoff = 1 if month >= failure_month - 3 and np.random.random() < 0.4 else 0
            incident = 1 if month >= failure_month - 3 else 0
        else:
            security = base_security + np.random.normal(0, 3)
            financial = base_financial + np.random.normal(0, 3)
            sentiment = np.random.normal(0.1, 0.2)
            negatives = np.random.poisson(0.5)
            layoff = 0
            incident = 0
        
        data.append({
            'vendor_id': vendor_id,
            'month': month,
            'security_score': max(0, min(100, security)),
            'financial_score': max(0, min(100, financial)),
            'news_sentiment': max(-1, min(1, sentiment)),
            'negative_mentions': negatives,
            'layoff_detected': layoff,
            'incident_next_90d': incident
        })
    
    return pd.DataFrame(data)

def create_training_dataset(n_vendors=100, months=24):
    """Create full dataset with some failing vendors."""
    all_dfs = []
    for i in range(n_vendors):
        will_fail = np.random.random() < 0.15  # 15% failure rate
        failure_month = np.random.randint(12, months) if will_fail else None
        df = generate_vendor_history(f"V{i:03d}", months, will_fail, failure_month)
        all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True)