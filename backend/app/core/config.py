from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    securityscorecard_api_key: str
    newsapi_key: str
    alpha_vantage_key: str
    vulners_api_key: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    model_path: str = "app/models/vendor_risk_model.pkl"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()