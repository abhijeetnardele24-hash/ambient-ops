"""AmbientOps Configuration Module.
Strict configuration settings adhering to security and provider standards.
"""

import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    app_name: str = "AmbientOps"
    version: str = "1.1.0"
    mcp_protocol_version: str = "2025-11-25"
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Security & CORS
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000",
            ).split(",")
            if origin.strip()
        ]
    )
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))

    # AWS Bedrock Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    # If explicitly set to true, force simulator mode regardless of credentials
    force_bedrock_simulator: bool = os.getenv(
        "FORCE_BEDROCK_SIMULATOR", "false"
    ).lower() in ("true", "1", "yes")

    # Simulation Telemetry Secret (optional webhook verification)
    simulator_webhook_token: str = os.getenv(
        "SIMULATOR_WEBHOOK_TOKEN", "ambient_sim_token_local"
    )


settings = Settings()
