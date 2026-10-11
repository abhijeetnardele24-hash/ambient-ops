"""AmbientOps Model Context Protocol (MCP) Server.
RFC-compliant implementation of MCP specification v2025-11-25 for Alexa+ and Smart Device Telemetry.
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
from .smart_entry_simulator import smart_entry_simulator
from .bedrock_agent import bedrock_agent


class McpServer:
    """Manages MCP tool execution, resource subscriptions, prompts, and JSON-RPC dispatch."""

    def __init__(self):
        self.protocol_history: List[Dict[str, Any]] = []
        self._tools: Dict[str, McpTool] = {}
        self._resources: Dict[str, McpResource] = {}
        self._prompts: Dict[str, McpPrompt] = {}
        self.is_initialized: bool = False
        self._register_defaults()

    def _register_defaults(self):
        # 1. smart_entry_poll_events (with legacy ring alias)
        poll_tool = McpTool(
            name="smart_entry_poll_events",
            description="Retrieve recent smart home motion, dwell, and entry sensor events from simulated cameras.",
            inputSchema=ToolInputSchema(
                properties={
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of events to fetch (default: 5, max: 20).",
                    }
                }
            ),
        )
        self.register_tool(poll_tool)
        # Register ring_poll_events as alias for backwards compatibility
        self.register_tool(
            McpTool(
                name="ring_poll_events",
                description="[Compatibility Alias] Retrieve smart home entry sensor events.",
                inputSchema=poll_tool.inputSchema,
            )
        )

        # 2. smart_entry_trigger_scenario (with legacy ring alias)
        trigger_tool = McpTool(
            name="smart_entry_trigger_scenario",
            description="Simulate an entry camera event scenario (e.g. delivery_weather_risk, elder_immobility_alert, pet_escape_risk).",
            inputSchema=ToolInputSchema(
                properties={
                    "scenario_id": {
                        "type": "string",
                        "description": "ID of scenario to trigger.",
                        "enum": list(smart_entry_simulator.SCENARIOS.keys()),
                    }
                },
                required=["scenario_id"],
            ),
        )
        self.register_tool(trigger_tool)
        self.register_tool(
            McpTool(
                name="ring_trigger_scenario",
                description="[Compatibility Alias] Simulate a smart camera event scenario.",
                inputSchema=trigger_tool.inputSchema,
            )
        )

        # 3. bedrock_reason_triage
        self.register_tool(
            McpTool(
                name="bedrock_reason_triage",
                description="Invoke Amazon Bedrock (Claude 3.5 Sonnet / Converse API) to evaluate risk, determine if resident should be interrupted, and craft spoken dialogue.",
                inputSchema=ToolInputSchema(
                    properties={
                        "event_id": {
                            "type": "string",
                            "description": "ID of the entry event to evaluate.",
                        }
                    },
                    required=["event_id"],
                ),
            )
        )

        # 4. alexa_proactive_dispatch
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

        # 5. household_action_execute
        self.register_tool(
            McpTool(
                name="household_action_execute",
                description="Execute a verified smart home remediation simulation after human approval.",
                inputSchema=ToolInputSchema(
                    properties={
                        "action_name": {
                            "type": "string",
                            "description": "Name of remediation action to execute.",
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
                uri="ambient://devices/sensors/live",
                name="Smart Entry Sensor Fleet",
                description="Live status, battery, and signal telemetry of simulated entry cameras and motion sensors.",
            )
        )
        self.register_resource(
            McpResource(
                uri="ambient://devices/ring/live",
                name="[Alias] Smart Entry Sensor Fleet",
                description="Compatibility alias for connected simulated cameras.",
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
        direction: str,
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

    def handle_request(self, raw_req: Any) -> Dict[str, Any]:
        """Dispatches an incoming JSON-RPC 2.0 MCP request."""
        t0 = time.perf_counter()
        self.log_protocol_message("inbound", raw_req if isinstance(raw_req, dict) else {"raw": str(raw_req)})

        if not isinstance(raw_req, dict):
            res = JsonRpcResponse(
                id=None,
                error=JsonRpcError(code=PARSE_ERROR, message="Invalid JSON format: payload must be a JSON object."),
            )
            out = res.model_dump(exclude_none=True)
            self.log_protocol_message("outbound", out, round((time.perf_counter() - t0) * 1000, 2))
            return out

        req_id = raw_req.get("id")

        try:
            req = JsonRpcRequest(**raw_req)
        except ValidationError as e:
            res = JsonRpcResponse(
                id=req_id,
                error=JsonRpcError(code=INVALID_REQUEST, message=f"Invalid JSON-RPC 2.0 request: {str(e)}"),
            )
            out = res.model_dump(exclude_none=True)
            self.log_protocol_message("outbound", out, round((time.perf_counter() - t0) * 1000, 2))
            return out

        method = req.method
        params = req.params or {}

        try:
            if method == "initialize":
                self.is_initialized = True
                result = InitializeResult().model_dump()
            elif method == "notifications/initialized":
                self.is_initialized = True
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
                    id=req_id,
                    error=JsonRpcError(code=METHOD_NOT_FOUND, message=f"Method not found: '{method}'"),
                )
                out = response.model_dump(exclude_none=True)
                self.log_protocol_message("outbound", out, round((time.perf_counter() - t0) * 1000, 2))
                return out

            response = JsonRpcResponse(id=req_id, result=result)
        except ValueError as val_err:
            response = JsonRpcResponse(
                id=req_id,
                error=JsonRpcError(code=INVALID_PARAMS, message=str(val_err)),
            )
        except Exception as ex:
            response = JsonRpcResponse(
                id=req_id,
                error=JsonRpcError(code=INTERNAL_ERROR, message=f"Internal MCP server error: {str(ex)}"),
            )

        out = response.model_dump(exclude_none=True)
        self.log_protocol_message("outbound", out, round((time.perf_counter() - t0) * 1000, 2))
        return out

    def _execute_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Missing required parameter: 'name'.")
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")

        if tool_name in ("smart_entry_poll_events", "ring_poll_events"):
            limit = int(arguments.get("limit", 5))
            if limit < 1 or limit > 20:
                raise ValueError("Parameter 'limit' must be between 1 and 20.")
            events = smart_entry_simulator.get_latest_events(limit)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Retrieved {len(events)} smart entry events (Simulated).",
                        "data": [e.model_dump() for e in events],
                    }
                ]
            }

        elif tool_name in ("smart_entry_trigger_scenario", "ring_trigger_scenario"):
            scenario_id = arguments.get("scenario_id")
            if not scenario_id:
                raise ValueError("Missing required argument: 'scenario_id'.")
            event = smart_entry_simulator.trigger_scenario(scenario_id)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Triggered smart entry scenario: {event.summary}",
                        "event": event.model_dump(),
                    }
                ]
            }

        elif tool_name == "bedrock_reason_triage":
            event_id = arguments.get("event_id")
            if not event_id:
                raise ValueError("Missing required argument: 'event_id'.")

            event = smart_entry_simulator.get_event_by_id(event_id)
            if not event:
                latest = smart_entry_simulator.get_latest_events(1)
                event = latest[0] if latest else None

            if not event:
                raise ValueError("No entry event found to analyze.")

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
                        "text": f"Bedrock triage complete (Risk {decision.risk_score}/100, Severity: {decision.severity}, Mode: {decision.provider_mode}).",
                        "decision": decision.model_dump(),
                    }
                ]
            }

        elif tool_name == "alexa_proactive_dispatch":
            spoken_text = arguments.get("spoken_text")
            urgency = arguments.get("urgency", "moderate")
            target_room = arguments.get("target_room", "Living Room Alexa+ Station")

            if not spoken_text:
                raise ValueError("Missing required argument: 'spoken_text'.")
            if urgency not in ("low", "moderate", "critical"):
                raise ValueError("Parameter 'urgency' must be 'low', 'moderate', or 'critical'.")

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
            if not action_name:
                raise ValueError("Missing required argument: 'action_name'.")

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed household automation simulation: {action_name}",
                        "status": "success",
                        "is_simulated": True,
                        "executed_at": time.time(),
                    }
                ]
            }

        raise ValueError(f"Execution handler not implemented for tool '{tool_name}'.")

    def _read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: 'uri'.")

        if uri in ("ambient://devices/sensors/live", "ambient://devices/ring/live"):
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": str(smart_entry_simulator.get_device_catalog()),
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
                                "protocol_version": "2025-11-25",
                                "is_initialized": self.is_initialized,
                            }
                        ),
                    }
                ]
            }
        raise ValueError(f"Resource '{uri}' not found.")

    def _get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not name:
            raise ValueError("Missing required parameter: 'name'.")

        if name == "triage_incident":
            return {
                "description": "Standard Bedrock smart home incident evaluation prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Analyze the following smart device sensor detections and determine whether to interrupt the resident via Alexa+.",
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
                            "text": "Summarize all smart entry security and motion events from 11 PM to 7 AM into a 30-second Alexa+ verbal briefing.",
                        },
                    }
                ],
            }
        raise ValueError(f"Prompt '{name}' not found.")


mcp_server = McpServer()
