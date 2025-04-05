import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "expense-tracker-api"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ALGORITHM: str = "HS256"
    # BACKEND_CORS_ORIGINS is a comma-separated list of origins
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Tesseract configuration
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    TEMP_DIR: str = "/app/temp"

    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    @model_validator(mode='before')
    def validate_database_url(cls, data: dict) -> dict:
        if data.get('DATABASE_URL') is not None:
            return data
        
        # Construct URL using environment variables
        db_url = f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:{data.get('POSTGRES_PORT') or '5432'}/{data.get('POSTGRES_DB') or 'expense_tracker'}"
        data['DATABASE_URL'] = db_url
        
        return data

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    RECEIPT_IMAGES_BUCKET: str
    
    # AWS SES Configuration
    SES_SENDER_EMAIL: str
    SES_SENDER_NAME: str

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()