from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lyftr AI Chatbot"

    database_url: str = "sqlite:///./app.db"

    allowed_origins: str = "http://localhost:3000"

    enable_failure_simulation: bool = True

    llm_api_keys: str = ""

    llm_model: str = "gemini/gemini-3.5-flash-lite"

    default_system_prompt: str = (
        "You are a helpful AI assistant."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_keys(self) -> list[str]:
        return [
            key.strip()
            for key in self.llm_api_keys.split(",")
            if key.strip()
        ]


settings = Settings()