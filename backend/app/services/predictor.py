import joblib
import numpy as np
from app.core.config import settings

class RiskPredictor:
    def __init__(self):
        self.model = joblib.load(settings.model_path)
        self.features = ['security_score_lag3', 'financial_score_lag3',
                         'news_sentiment_lag3', 'negative_mentions_lag3',
                         'layoff_detected_lag3']

    def predict(self, vendor_data: dict) -> float:
        """vendor_data should contain current values for the features."""
        # Build feature vector in correct order
        X = np.array([[vendor_data[f] for f in self.features]])
        prob = self.model.predict_proba(X)[0][1]  # probability of incident
        return prob * 100  # return as percentage