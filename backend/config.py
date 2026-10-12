"""AmbientOps Configuration Module.
Strict configuration settings adhering to security and provider standards.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    app_name: str = "AmbientOps"
    version: str = "1.2.0"
    mcp_protocol_version: str = "2025-11-25"
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Privacy & Resident Configuration
    resident_display_name: str = os.getenv("RESIDENT_DISPLAY_NAME", "Resident")
    household_name: str = os.getenv("HOUSEHOLD_NAME", "Demo Household")

    # Security & CORS
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://testserver",
            ).split(",")
            if origin.strip()
        ]
    )
    allowed_hosts: List[str] = Field(
        default_factory=lambda: [
            host.strip()
            for host in os.getenv(
                "ALLOWED_HOSTS",
                "localhost,localhost:8000,127.0.0.1,127.0.0.1:8000,testserver,0.0.0.0:8000",
            ).split(",")
            if host.strip()
        ]
    )
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))

    # AWS Bedrock Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    bedrock_connect_timeout: float = float(os.getenv("BEDROCK_CONNECT_TIMEOUT", "5.0"))
    bedrock_read_timeout: float = float(os.getenv("BEDROCK_READ_TIMEOUT", "15.0"))
    bedrock_max_retries: int = int(os.getenv("BEDROCK_MAX_RETRIES", "2"))

    # Explicit opt-in required for live AWS Bedrock invocation
    enable_live_bedrock: bool = os.getenv(
        "ENABLE_LIVE_BEDROCK", "false"
    ).lower() in ("true", "1", "yes")

    # Safe Docker/demo default: deterministic simulator (requires explicit opt-in for live AWS)
    force_bedrock_simulator: bool = os.getenv(
        "FORCE_BEDROCK_SIMULATOR", "true"
    ).lower() in ("true", "1", "yes")

    # Simulation Telemetry Secret (optional webhook verification - no insecure default)
    simulator_webhook_token: Optional[str] = os.getenv("SIMULATOR_WEBHOOK_TOKEN", None)


settings = Settings()
