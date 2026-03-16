from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ON24 REST API
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""

    # ON24 master database (direct read-only, same env vars as backend)
    on24_db_url: str = ""
    on24_db_url_qa: str = ""

    # PostgreSQL SSL certs (Google Cloud SQL)
    db_pg_ssl_root_cert_content: str = ""
    db_pg_ssl_cert_content: str = ""
    db_pg_ssl_key_content: str = ""

    # Comma-separated tool names to never expose, e.g. "create_event,remove_registrant"
    use_mcp_blocklist: str = ""

    @property
    def blocklist(self) -> set[str]:
        return {t.strip() for t in self.use_mcp_blocklist.split(",") if t.strip()}

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
