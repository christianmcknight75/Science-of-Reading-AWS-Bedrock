from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://sor:local-dev-only@localhost:5433/sor"
    # "cognito" (default, fails closed) or "dev" (local only: everyone is an admin)
    auth_mode: str = "cognito"
    cognito_region: str = "us-east-2"
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    admin_group: str = "admin"
    snapshot_dir: str = "data/local/license_snapshots"


def get_settings() -> Settings:
    return Settings()
