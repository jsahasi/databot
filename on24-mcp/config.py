from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""
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
