"""AmbientOps Model Context Protocol (MCP) Server.
Implementation conforming to MCP specification v2025-11-25 for Alexa+ and Smart Device Telemetry.
Uses the official MCP Python SDK with Streamable HTTP transport and DNS rebinding protection.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .config import settings
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

logger = logging.getLogger("ambient_ops.mcp")

ALLOWED_SIMULATED_ACTIONS = {
    "unlock_porch_storage",
    "log_delivery_ledger",
    "remind_in_10_minutes",
    "initiate_voice_dialogue",
    "prepare_emergency_contact_sms",
    "illuminate_hallway_safety_path",
    "sound_backyard_chime",
    "notify_mobile_push",
    "trigger_smart_lock_latch",
    "latch_gate_lock",
    "illuminate_driveway_spotlight_100pct",
    "record_cloud_evidence_clip",
    "prompt_siren_confirmation",
    "log_silent_timeline_event",
    "log_degraded_warning",
}


# --- Official MCP SDK Server Instance ---
sdk_mcp_server = MCPServer(
    name="AmbientOps-AlexaPlus-MCP",
    version=settings.version,
)


@sdk_mcp_server.tool(
    name="smart_entry_poll_events",
    description="Retrieve recent smart home motion, dwell, and entry sensor events from simulated cameras.",
)
def smart_entry_poll_events(limit: int = 5) -> str:
    """Retrieve recent smart entry sensor events."""
    if limit < 1 or limit > 20:
        raise ValueError("Parameter 'limit' must be between 1 and 20.")
    events = smart_entry_simulator.get_latest_events(limit)
    return json.dumps({
        "status": "success",
        "count": len(events),
        "is_simulated": True,
        "events": [e.model_dump() for e in events],
    })


@sdk_mcp_server.tool(
    name="ring_poll_events",
    description="[Compatibility Alias] Retrieve smart home entry sensor events.",
)
def ring_poll_events(limit: int = 5) -> str:
    return smart_entry_poll_events(limit)


@sdk_mcp_server.tool(
    name="smart_entry_trigger_scenario",
    description="Simulate an entry camera event scenario (e.g. delivery_weather_risk, elder_immobility_alert, pet_escape_risk).",
)
def smart_entry_trigger_scenario(scenario_id: str) -> str:
    """Simulate a camera event scenario."""
    if not scenario_id:
        raise ValueError("Missing required argument: 'scenario_id'.")
    event = smart_entry_simulator.trigger_scenario(scenario_id)
    return json.dumps({
        "status": "success",
        "scenario_id": scenario_id,
        "summary": event.summary,
        "is_simulated": True,
        "event": event.model_dump(),
    })


@sdk_mcp_server.tool(
    name="ring_trigger_scenario",
    description="[Compatibility Alias] Simulate a smart camera event scenario.",
)
def ring_trigger_scenario(scenario_id: str) -> str:
    return smart_entry_trigger_scenario(scenario_id)


@sdk_mcp_server.tool(
    name="bedrock_reason_triage",
    description="Invoke Amazon Bedrock (Claude 3.5 Sonnet / Converse API) to evaluate risk, determine if resident should be interrupted, and craft spoken dialogue.",
)
def bedrock_reason_triage(event_id: str) -> str:
    """Evaluate risk and create triage decision via Amazon Bedrock."""
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
    return json.dumps({
        "status": "success",
        "risk_score": decision.risk_score,
        "severity": decision.severity,
        "provider_mode": decision.provider_mode,
        "should_interrupt": decision.should_interrupt_user,
        "recommended_action": decision.recommended_action,
        "spoken_prompt": decision.spoken_alexa_prompt,
        "decision": decision.model_dump(),
    })


@sdk_mcp_server.tool(
    name="alexa_proactive_dispatch",
    description="Dispatch a spoken voice announcement or chime to target Alexa+ ambient endpoint (Simulated).",
)
def alexa_proactive_dispatch(
    spoken_text: str,
    urgency: str = "moderate",
    target_room: str = "Living Room Alexa+ Station",
) -> str:
    """Dispatch voice announcement with explicit simulation markers."""
    if not spoken_text:
        raise ValueError("Missing required argument: 'spoken_text'.")
    if urgency not in ("low", "moderate", "critical"):
        raise ValueError("Parameter 'urgency' must be 'low', 'moderate', or 'critical'.")

    return json.dumps({
        "status": "dispatched",
        "spoken_text": spoken_text[:500],
        "urgency": urgency,
        "target_room": target_room[:80],
        "is_simulated": True,
        "simulation_method": "browser_web_speech_or_simulated_endpoint",
        "dispatched_at": time.time(),
    })


@sdk_mcp_server.tool(
    name="household_action_execute",
    description="Execute an approved simulated smart home remediation action after human approval.",
)
def household_action_execute(
    action_name: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """Execute remediation action guarded by strict allowlist."""
    if not action_name:
        raise ValueError("Missing required argument: 'action_name'.")

    if action_name not in ALLOWED_SIMULATED_ACTIONS:
        raise ValueError(
            f"Action '{action_name}' is not in the allowed simulated actions list: {sorted(list(ALLOWED_SIMULATED_ACTIONS))}"
        )

    return json.dumps({
        "status": "success",
        "action_name": action_name,
        "parameters": parameters or {},
        "is_simulated": True,
        "executed_at": time.time(),
    })


# Register Resources on SDK Server
@sdk_mcp_server.resource(uri="ambient://devices/sensors/live")
def get_sensor_fleet_resource() -> str:
    return json.dumps(smart_entry_simulator.get_device_catalog())


@sdk_mcp_server.resource(uri="ambient://devices/ring/live")
def get_ring_sensors_alias() -> str:
    return json.dumps(smart_entry_simulator.get_device_catalog())


@sdk_mcp_server.resource(uri="ambient://household/context")
def get_household_context_resource() -> str:
    return json.dumps({
        "household_name": settings.household_name,
        "resident": settings.resident_display_name,
        "timezone": "UTC",
        "quiet_hours": "23:00 - 06:30",
        "preferred_voice": "Alexa Pro (Warm & Concise)",
    })


@sdk_mcp_server.resource(uri="ambient://telemetry/mcp")
def get_telemetry_resource() -> str:
    return json.dumps({
        "active_transport": "Streamable HTTP (MCP v2025-11-25)",
        "protocol_version": settings.mcp_protocol_version,
        "official_sdk": "mcp==2.3.0",
        "registered_tools": 5,
    })


# Register Prompts on SDK Server
@sdk_mcp_server.prompt(name="triage_incident")
def triage_incident_prompt() -> str:
    return "Analyze the following smart device sensor detections and determine whether to interrupt the resident via Alexa+."


@sdk_mcp_server.prompt(name="daily_ambient_brief")
def daily_ambient_brief_prompt() -> str:
    return "Summarize all smart entry security and motion events from 11 PM to 7 AM into a 30-second Alexa+ verbal briefing."


# --- Unified MCP Server Controller & History Logger ---
class McpServer:
    """Manages MCP tool execution, protocol telemetry, and JSON-RPC dispatch."""

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
                description="Dispatch a spoken voice announcement or chime to target Alexa+ ambient endpoint (Simulated).",
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
                description="Execute an approved smart home remediation simulation after human approval.",
                inputSchema=ToolInputSchema(
                    properties={
                        "action_name": {
                            "type": "string",
                            "description": "Name of remediation action to execute.",
                            "enum": sorted(list(ALLOWED_SIMULATED_ACTIONS)),
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
                description="Resident preferences, quiet hour rules, and general household context (Sanitized).",
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

    def create_transport_security(self) -> TransportSecuritySettings:
        """Configures DNS rebinding protection according to official specification."""
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                "127.0.0.1",
                "127.0.0.1:*",
                "localhost",
                "localhost:*",
                "testserver",
                "0.0.0.0",
                "0.0.0.0:*",
            ],
            allowed_origins=[
                "http://127.0.0.1",
                "http://127.0.0.1:*",
                "http://localhost",
                "http://localhost:*",
                "http://testserver",
            ],
        )

    def create_streamable_http_app(self):
        """Creates the official Starlette Streamable HTTP transport application."""
        sec = self.create_transport_security()
        return sdk_mcp_server.streamable_http_app(
            streamable_http_path="/mcp",
            transport_security=sec,
        )

    def handle_request(self, raw_req: Any) -> Optional[Dict[str, Any]]:
        """Dispatches an incoming JSON-RPC 2.0 MCP request.
        Notifications return None (NO JSON-RPC response body).
        """
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

        # Notification handling: per JSON-RPC 2.0 and MCP spec, NO response body is returned
        if req_id is None and method.startswith("notifications/"):
            if method == "notifications/initialized":
                self.is_initialized = True
            logger.info("Processed MCP notification '%s' (no response returned)", method)
            return None

        try:
            if method == "initialize":
                self.is_initialized = True
                result = InitializeResult().model_dump()
            elif method == "notifications/initialized":
                self.is_initialized = True
                # If called with an ID (non-compliant client), return empty result or None
                if req_id is None:
                    return None
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
                error=JsonRpcError(code=INTERNAL_ERROR, message=f"Internal MCP server error: {type(ex).__name__}"),
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
                        "text": f"Dispatched Alexa+ voice prompt to [{target_room}] with urgency [{urgency}] (Simulated).",
                        "dispatch": {
                            "spoken_text": spoken_text,
                            "urgency": urgency,
                            "target_room": target_room,
                            "is_simulated": True,
                            "simulation_method": "browser_web_speech_or_simulated_endpoint",
                            "dispatched_at": time.time(),
                        },
                    }
                ]
            }

        elif tool_name == "household_action_execute":
            action_name = arguments.get("action_name")
            if not action_name:
                raise ValueError("Missing required argument: 'action_name'.")

            if action_name not in ALLOWED_SIMULATED_ACTIONS:
                raise ValueError(
                    f"Action '{action_name}' is not in the allowed simulated actions list: {sorted(list(ALLOWED_SIMULATED_ACTIONS))}"
                )

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
                        "text": json.dumps(
                            {
                                "household_name": settings.household_name,
                                "resident": settings.resident_display_name,
                                "timezone": "UTC",
                                "quiet_hours": "23:00 - 06:30",
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
                        "text": json.dumps(
                            {
                                "total_messages": len(self.protocol_history),
                                "registered_tools": len(self._tools),
                                "active_transport": "Streamable HTTP (MCP v2025-11-25)",
                                "protocol_version": settings.mcp_protocol_version,
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
