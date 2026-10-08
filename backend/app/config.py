"""Runtime configuration, read from environment variables prefixed with ``R53_``."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="R53_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/route53.db"

    session_cookie_name: str = "r53_session"
    session_ttl_hours: int = 24 * 14
    cookie_secure: bool = False

    demo_email: str = "demo@example.com"
    demo_password: str = "Route53Demo!"
    demo_display_name: str = "demo-admin"
    demo_account_id: str = "111122223333"
    seed_demo_data: bool = True
    # Let the sign-in page show the demo credentials. Turn off for a private deployment.
    demo_credentials_public: bool = True

    @property
    def session_ttl_seconds(self) -> int:
        return self.session_ttl_hours * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
