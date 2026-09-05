from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    generation_model: str = "claude-sonnet-5"

    pinecone_api_key: str
    pinecone_index_name: str = "rag-project"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    top_k: int = 5


settings = Settings()
