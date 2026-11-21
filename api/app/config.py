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

    # Accounts. auth_mode: "cognito" (default, fails closed), "local" (local dev issuer + real
    # users table, for development and tests) or "dev" (no auth at all: everyone is an admin).
    # Phase 5 changes only the issuer, client id and JWKS URL to Cognito's.
    auth_issuer: str = ""  # empty: Cognito's URL for the pool; in local mode the dev issuer
    auth_jwks_url: str = ""  # empty: <issuer>/.well-known/jwks.json
    auth_token_minutes: int = 60
    dev_issuer_key_path: str = "data/local/dev_issuer_key.pem"
    sign_in_max_failures: int = 5
    sign_in_window_minutes: int = 15
    request_access_per_hour: int = 3

    # Q&A engine. The kill switch is OFF until Viktoriia approves live model calls.
    qa_enabled: bool = False
    llm_mode: str = "bedrock"  # "fake" = local stand-in model (never with Cognito auth)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"  # comma separated
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
