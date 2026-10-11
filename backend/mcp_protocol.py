"""Model Context Protocol (MCP) JSON-RPC 2.0 Specification Schemas.
Conforms to MCP standard v2025-11-25.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Standard JSON-RPC Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field("2.0", pattern="^2.0$")
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None


# MCP Specific Types
class ToolParameterProperty(BaseModel):
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None


class ToolInputSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: Optional[List[str]] = None


class McpTool(BaseModel):
    name: str
    description: str
    inputSchema: ToolInputSchema


class McpResource(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = "application/json"


class McpPrompt(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class ServerCapabilities(BaseModel):
    tools: Dict[str, Any] = Field(default_factory=lambda: {"listChanged": True})
    resources: Dict[str, Any] = Field(default_factory=lambda: {"subscribe": False, "listChanged": True})
    prompts: Dict[str, Any] = Field(default_factory=lambda: {"listChanged": True})
    logging: Dict[str, Any] = Field(default_factory=dict)


class ServerInfo(BaseModel):
    name: str = "AmbientOps-AlexaPlus-MCP"
    version: str = "1.0.0"


class InitializeResult(BaseModel):
    protocolVersion: str = "2025-11-25"
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    serverInfo: ServerInfo = Field(default_factory=ServerInfo)
