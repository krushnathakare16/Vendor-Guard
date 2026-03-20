# import pandas as pd
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.model_selection import train_test_split
# import joblib
# from app.utils.synthetic_data import create_training_dataset

# # Generate data
# df = create_training_dataset(n_vendors=100, months=24)
# df.to_csv('training_data.csv', index=False)

# # Feature engineering: create lagged features (3 months)
# features = ['security_score', 'financial_score', 'news_sentiment',
#             'negative_mentions', 'layoff_detected']
# lags = 3
# for vendor in df['vendor_id'].unique():
#     mask = df['vendor_id'] == vendor
#     for feat in features:
#         df.loc[mask, f'{feat}_lag3'] = df.loc[mask, feat].shift(lags)

# df = df.dropna()
# X = df[[f'{feat}_lag3' for feat in features]]
# y = df['incident_next_90d']

# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
# model.fit(X_train, y_train)

# joblib.dump(model, r'app/models/vendor_risk_model.pkl')
# print("Model trained and saved.")



"""
Train ML model for vendor risk prediction
Run with: python -m app.models.train_model
"""

import sys
import os
from pathlib import Path

# Add the backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# Now import from app
from app.utils.synthetic_data import create_training_dataset

def train_model():
    """Train the vendor risk prediction model"""
    print("🚀 Starting model training...")
    
    # Generate synthetic training data
    print("📊 Generating synthetic data...")
    df = create_training_dataset(n_vendors=100, months=24)
    df.to_csv('training_data.csv', index=False)
    print(f"✅ Generated {len(df)} records")
    
    # Feature engineering: create lagged features (3 months)
    print("🔧 Engineering features...")
    features = ['security_score', 'financial_score', 'news_sentiment',
                'negative_mentions', 'layoff_detected']
    lags = 3
    
    for vendor in df['vendor_id'].unique():
        mask = df['vendor_id'] == vendor
        for feat in features:
            df.loc[mask, f'{feat}_lag3'] = df.loc[mask, feat].shift(lags)
    
    # Drop rows with NaN (first 3 months)
    df = df.dropna()
    
    # Prepare features and target
    feature_cols = [f'{feat}_lag3' for feat in features]
    X = df[feature_cols]
    y = df['incident_next_90d']
    
    print(f"📈 Feature matrix shape: {X.shape}")
    print(f"🎯 Target distribution: {y.value_counts().to_dict()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train model
    print("🤖 Training Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'  # Handle imbalanced classes
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"✅ Training accuracy: {train_acc:.3f}")
    print(f"✅ Test accuracy: {test_acc:.3f}")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n📊 Top 5 features:")
    print(importance.head().to_string(index=False))
    
    # Save model
    model_path = backend_dir / 'app' / 'models' / 'vendor_risk_model.pkl'
    joblib.dump(model, model_path)
    print(f"💾 Model saved to: {model_path}")
    
    return model

if __name__ == "__main__":
    train_model()