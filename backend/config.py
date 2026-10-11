"""AmbientOps Configuration Module."""

import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    app_name: str = "AmbientOps"
    version: str = "1.0.0"
    mcp_protocol_version: str = "2025-11-25"
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # AWS Bedrock
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    use_bedrock_mock: bool = os.getenv("USE_BEDROCK_MOCK", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    
    # Ring Simulator
    ring_webhook_secret: str = os.getenv(
        "RING_WEBHOOK_SECRET", "ambient_ops_secret_token_2026"
    )


settings = Settings()
