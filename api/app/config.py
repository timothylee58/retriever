from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://apple@localhost:5432/retriever"
    web_origin: str = "http://localhost:3000"
    dry_run: bool = True
    demo_password: str = "retriever-demo"
    hitpay_api_key: str = ""
    hitpay_webhook_salt: str = "sandbox-salt"
    hitpay_env: str = "sandbox"
    hitpay_api_base: str = "https://api.sandbox.hit-pay.com"
    # Public HTTPS URL from `hitpay listen`. Sent on each payment request.
    # Localhost is rejected, and a link created without this URL does not call Retriever.
    hitpay_webhook_url: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = "whsec_test"
    xai_api_key: str = ""
    llm_model: str = "grok-4-fast"
    llm_base_url: str = "https://api.x.ai/v1"
    churn_after_days: int = 7
    abandon_after_minutes: int = 30


def get_settings() -> Settings:
    return Settings()
