"""AmbientOps Model Context Protocol (MCP) Server.
RFC-compliant implementation of MCP specification v2025-11-25 for Alexa+ and Ring.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from .mcp_protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    InitializeResult,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    McpPrompt,
    McpResource,
    McpTool,
    ToolInputSchema,
)
from .ring_simulator import ring_simulator
from .bedrock_agent import bedrock_agent


class McpServer:
    """Manages MCP tool execution, resource subscriptions, prompts, and JSON-RPC dispatch."""

    def __init__(self):
        self.protocol_history: List[Dict[str, Any]] = []
        self._tools: Dict[str, McpTool] = {}
        self._resources: Dict[str, McpResource] = {}
        self._prompts: Dict[str, McpPrompt] = {}
        self._register_defaults()

    def _register_defaults(self):
        # Register Tools
        self.register_tool(
            McpTool(
                name="ring_poll_events",
                description="Retrieve recent smart home motion, linger, and doorbell events from Ring cameras.",
                inputSchema=ToolInputSchema(
                    properties={
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to fetch (default: 5).",
                        }
                    }
                ),
            )
        )
        self.register_tool(
            McpTool(
                name="ring_trigger_scenario",
                description="Simulate a Ring camera event scenario (e.g. delivery_weather_risk, elder_immobility_alert, pet_escape_risk).",
                inputSchema=ToolInputSchema(
                    properties={
                        "scenario_id": {
                            "type": "string",
                            "description": "ID of scenario to trigger.",
                            "enum": list(ring_simulator.SCENARIOS.keys()),
                        }
                    },
                    required=["scenario_id"],
                ),
            )
        )
        self.register_tool(
            McpTool(
                name="bedrock_reason_triage",
                description="Invoke Amazon Bedrock (Claude 3.5 Sonnet / Converse API) to evaluate risk, determine if resident should be interrupted, and craft spoken dialogue.",
                inputSchema=ToolInputSchema(
                    properties={
                        "event_id": {
                            "type": "string",
                            "description": "ID of the Ring event to evaluate.",
                        }
                    },
                    required=["event_id"],
                ),
            )
        )
        self.register_tool(
            McpTool(
                name="alexa_proactive_dispatch",
                description="Dispatch a spoken voice announcement or chime to target Alexa+ ambient endpoint.",
                inputSchema=ToolInputSchema(
                    properties={
                        "spoken_text": {
                            "type": "string",
                            "description": "The exact conversational speech to announce.",
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "moderate", "critical"],
                        },
                        "target_room": {
                            "type": "string",
                            "description": "Room or device to sound the prompt in (e.g. Living Room, All).",
                        },
                    },
                    required=["spoken_text", "urgency"],
                ),
            )
        )
        self.register_tool(
            McpTool(
                name="household_action_execute",
                description="Execute an automated smart home remediation action (e.g. unlock_porch, turn_on_lights, sound_chime).",
                inputSchema=ToolInputSchema(
                    properties={
                        "action_name": {
                            "type": "string",
                            "description": "Name of action to execute.",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional action parameters.",
                        },
                    },
                    required=["action_name"],
                ),
            )
        )

        # Register Resources
        self.register_resource(
            McpResource(
                uri="ambient://devices/ring/live",
                name="Ring Device Network",
                description="Live status, battery, and signal telemetry of connected Ring video cameras.",
            )
        )
        self.register_resource(
            McpResource(
                uri="ambient://household/context",
                name="Household Resident Context",
                description="Resident schedules, preferences, quiet hour rules, and emergency contacts.",
            )
        )
        self.register_resource(
            McpResource(
                uri="ambient://telemetry/mcp",
                name="MCP Protocol Telemetry",
                description="Bidirectional message rate, latency metrics, and error rates.",
            )
        )

        # Register Prompts
        self.register_prompt(
            McpPrompt(
                name="triage_incident",
                description="Standard prompt template for Amazon Bedrock smart home scene reasoning.",
            )
        )
        self.register_prompt(
            McpPrompt(
                name="daily_ambient_brief",
                description="Generates an Alexa+ morning ambient summary of overnight perimeter security events.",
            )
        )

    def register_tool(self, tool: McpTool):
        self._tools[tool.name] = tool

    def register_resource(self, resource: McpResource):
        self._resources[resource.uri] = resource

    def register_prompt(self, prompt: McpPrompt):
        self._prompts[prompt.name] = prompt

    def log_protocol_message(
        self,
        direction: str,  # inbound / outbound
        payload: Dict[str, Any],
        latency_ms: Optional[float] = None,
    ):
        entry = {
            "timestamp": time.time(),
            "direction": direction,
            "payload": payload,
            "latency_ms": latency_ms,
        }
        self.protocol_history.insert(0, entry)
        if len(self.protocol_history) > 100:
            self.protocol_history = self.protocol_history[:100]

    def handle_request(self, raw_req: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an incoming JSON-RPC 2.0 MCP request."""
        t0 = time.time()
        self.log_protocol_message("inbound", raw_req)

        try:
            req = JsonRpcRequest(**raw_req)
        except ValidationError as e:
            res = JsonRpcResponse(
                id=raw_req.get("id"),
                error=JsonRpcError(code=INVALID_REQUEST, message=f"Invalid JSON-RPC request: {str(e)}"),
            )
            out = res.model_dump(exclude_none=True)
            self.log_protocol_message("outbound", out, round((time.time() - t0) * 1000, 2))
            return out

        method = req.method
        params = req.params or {}

        try:
            if method == "initialize":
                result = InitializeResult().model_dump()
            elif method == "notifications/initialized":
                result = {"status": "ok", "initialized": True}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [t.model_dump() for t in self._tools.values()]
                }
            elif method == "tools/call":
                result = self._execute_tool_call(params)
            elif method == "resources/list":
                result = {
                    "resources": [r.model_dump() for r in self._resources.values()]
                }
            elif method == "resources/read":
                result = self._read_resource(params)
            elif method == "prompts/list":
                result = {
                    "prompts": [p.model_dump() for p in self._prompts.values()]
                }
            elif method == "prompts/get":
                result = self._get_prompt(params)
            else:
                response = JsonRpcResponse(
                    id=req.id,
                    error=JsonRpcError(code=METHOD_NOT_FOUND, message=f"Method not found: {method}"),
                )
                out = response.model_dump(exclude_none=True)
                self.log_protocol_message("outbound", out, round((time.time() - t0) * 1000, 2))
                return out

            response = JsonRpcResponse(id=req.id, result=result)
        except Exception as ex:
            response = JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(code=INTERNAL_ERROR, message=f"Internal MCP server error: {str(ex)}"),
            )

        out = response.model_dump(exclude_none=True)
        self.log_protocol_message("outbound", out, round((time.time() - t0) * 1000, 2))
        return out

    def _execute_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name or tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")

        if tool_name == "ring_poll_events":
            limit = int(arguments.get("limit", 5))
            events = ring_simulator.get_latest_events(limit)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Retrieved {len(events)} Ring events.",
                        "data": [e.model_dump() for e in events],
                    }
                ]
            }

        elif tool_name == "ring_trigger_scenario":
            scenario_id = arguments.get("scenario_id")
            event = ring_simulator.trigger_scenario(scenario_id)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Triggered Ring scenario: {event.summary}",
                        "event": event.model_dump(),
                    }
                ]
            }

        elif tool_name == "bedrock_reason_triage":
            event_id = arguments.get("event_id")
            event = ring_simulator.get_event_by_id(event_id)
            if not event:
                # If not found, use latest
                latest = ring_simulator.get_latest_events(1)
                event = latest[0] if latest else None

            if not event:
                raise ValueError("No Ring event found to analyze.")

            decision = bedrock_agent.triage_ambient_event(
                event_summary=event.summary,
                device_name=event.device_name,
                detections=[d.model_dump() for d in event.detections],
                ambient_conditions=event.ambient_conditions,
            )
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Bedrock triage complete (Risk {decision.risk_score}/100, Severity: {decision.severity}).",
                        "decision": decision.model_dump(),
                    }
                ]
            }

        elif tool_name == "alexa_proactive_dispatch":
            spoken_text = arguments.get("spoken_text")
            urgency = arguments.get("urgency", "moderate")
            target_room = arguments.get("target_room", "Living Room")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Dispatched Alexa+ voice prompt to [{target_room}] with urgency [{urgency}].",
                        "dispatch": {
                            "spoken_text": spoken_text,
                            "urgency": urgency,
                            "target_room": target_room,
                            "dispatched_at": time.time(),
                        },
                    }
                ]
            }

        elif tool_name == "household_action_execute":
            action_name = arguments.get("action_name")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed household automation action: {action_name}",
                        "status": "success",
                        "executed_at": time.time(),
                    }
                ]
            }

        raise ValueError(f"Execution handler not implemented for tool '{tool_name}'.")

    def _read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri")
        if uri == "ambient://devices/ring/live":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": str(ring_simulator.get_device_catalog()),
                    }
                ]
            }
        elif uri == "ambient://household/context":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": str(
                            {
                                "resident": "Abhijeet Nardele",
                                "timezone": "Asia/Kolkata",
                                "quiet_hours": "23:00 - 06:30",
                                "emergency_contacts": ["+1-555-019-2831"],
                                "preferred_voice": "Alexa Pro (Warm & Concise)",
                            }
                        ),
                    }
                ]
            }
        elif uri == "ambient://telemetry/mcp":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": str(
                            {
                                "total_messages": len(self.protocol_history),
                                "registered_tools": len(self._tools),
                                "active_transport": "Streamable HTTP/SSE",
                                "uptime_sec": 3600,
                            }
                        ),
                    }
                ]
            }
        raise ValueError(f"Resource '{uri}' not found.")

    def _get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if name == "triage_incident":
            return {
                "description": "Standard Bedrock smart home incident evaluation prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Analyze the following Ring event detections and determine whether to interrupt the resident via Alexa+.",
                        },
                    }
                ],
            }
        elif name == "daily_ambient_brief":
            return {
                "description": "Morning ambient recap prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Summarize all Ring security and motion events from 11 PM to 7 AM into a 30-second Alexa+ verbal briefing.",
                        },
                    }
                ],
            }
        raise ValueError(f"Prompt '{name}' not found.")


# Singleton instance
mcp_server = McpServer()
