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

    # Q&A engine. The kill switch is OFF until Viktoriia approves live model calls.
    qa_enabled: bool = False
    aws_profile: str = ""  # local dev only (sor-dev); empty = default credential chain
    guardrail_id: str = ""  # Bedrock Guardrail (PII + denied topics); empty = not attached yet
    guardrail_version: str = "DRAFT"
    rate_limit_per_minute: int = 6
    max_output_tokens: int = 900
    claim_check_max_tokens: int = 500
    retrieval_top_k: int = 6
    min_similarity: float = 0.62  # provisional: calibrated on 38 questions (see DECISIONS.md)
    recent_years: int = 10  # studies/meta-analyses older than this are dropped unless allow-listed


def get_settings() -> Settings:
    return Settings()
