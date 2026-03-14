from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App database (local PostgreSQL in Docker)
    database_url: str = "postgresql+asyncpg://databot:databot@localhost:5432/databot"

    # ON24 master database (direct read-only access)
    on24_db_url: str = ""
    on24_db_url_qa: str = ""

    # PostgreSQL SSL (Google Cloud SQL)
    db_pg_ssl_root_cert_content: str = ""
    db_pg_ssl_cert_content: str = ""
    db_pg_ssl_key_content: str = ""

    # ON24 QA database SSL (separate certs if different)
    db_pg_ssl_cert_content_qa: str = ""
    db_pg_ssl_key_content_qa: str = ""
    postgres_password_qa: str = ""

    # ON24 API
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI (embeddings)
    openai_api_key: str = ""

    # Brand voice — company website for blog scraping (optional)
    company_website_url: str = ""

    # Redis (response cache)
    redis_url: str = "redis://redis:6379/0"
    response_cache_ttl: int = 120  # seconds (2 min)

    # App
    app_name: str = "DataBot"
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # MCP server integration
    use_mcp: str = "N"           # "Y" to route admin write ops through on24-mcp server
    use_mcp_blocklist: str = ""  # comma-separated tool names to block even if use_mcp=Y
    mcp_server_url: str = "http://on24-mcp:8001"  # Docker service name

    @property
    def mcp_enabled(self) -> bool:
        return self.use_mcp.upper() == "Y"

    @property
    def mcp_blocklist(self) -> set[str]:
        return {t.strip() for t in self.use_mcp_blocklist.split(",") if t.strip()}

    # Sync
    sync_interval_hours: int = 4
    active_event_sync_minutes: int = 15

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
