import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "expense-tracker-api"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["https://*.elasticbeanstalk.com", "http://localhost:3000"]
    SERVER_HOST: Optional[str] = None

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
    DATABASE_URL: str = "postgresql+asyncpg://expensee-admin:npg_WZqh5DVEyv7w@ep-curly-butterfly-a1ne721w-pooler.ap-southeast-1.aws.neon.tech/expensee"
    POSTGRES_USER: str = "expensee-admin"
    POSTGRES_PASSWORD: str = "npg_WZqh5DVEyv7w"
    POSTGRES_DB: str = "expensee"
    POSTGRES_HOST: str = "ep-curly-butterfly-a1ne721w-pooler.ap-southeast-1.aws.neon.tech"
    POSTGRES_PORT: str = "5432"

    @model_validator(mode='before')
    def validate_database_url(cls, data: dict) -> dict:
        # Static database URL string
        db_url = "postgresql+asyncpg://expensee-admin:npg_WZqh5DVEyv7w@ep-curly-butterfly-a1ne721w-pooler.ap-southeast-1.aws.neon.tech/expensee"
        data['DATABASE_URL'] = db_url
        
        return data

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = "AKIAXYKJW2O22JPT7N74"
    AWS_SECRET_ACCESS_KEY: str = "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"
    AWS_REGION: str = "ap-southeast-1"
    RECEIPT_IMAGES_BUCKET: str = "expensee-receipts"
    
    # AWS SES Configuration
    SES_SENDER_EMAIL: str = "amdnabil2001@gmail.com"
    SES_SENDER_NAME: str = "Expense Tracker"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()