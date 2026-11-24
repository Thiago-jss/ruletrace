import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database: str
    ollama_url: str
    chat_model: str
    embed_model: str

    @classmethod
    def local(cls) -> "Settings":
        return cls(
            os.environ["RULETRACE_DATABASE_URL"],
            os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b-instruct-2507-q4_K_M"),
            os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma"),
        )
