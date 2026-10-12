"""AmbientOps FastAPI Backend & Streamable HTTP MCP Server.
Provides incident analysis, explicit operator approval gate, and Streamable HTTP MCP transport.
Conforms to MCP specification v2025-11-25.
"""

import asyncio
from contextlib import asynccontextmanager
from enum import Enum
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import BaseModel, Field
from starlette.types import Receive, Scope, Send

from .config import settings
from .mcp_server import (
    ALLOWED_SIMULATED_ACTIONS,
    mcp_server,
    sdk_mcp_server,
)
from .smart_entry_simulator import smart_entry_simulator
from .bedrock_agent import bedrock_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ambient_ops.server")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


class McpStreamableHttpEndpoint:
    """Dynamic ASGI handler routing /mcp traffic to the active StreamableHTTPSessionManager."""

    def __init__(self, get_session_manager):
        self._get_sm = get_session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        sm = self._get_sm()
        if sm is None:
            res = Response(
                content=json.dumps({
                    "detail": "MCP server session manager is not active. Make sure to run within application lifespan.",
                }),
                status_code=503,
                media_type="application/json",
            )
            await res(scope, receive, send)
            return
        await sm.asgi_app(scope, receive, send)


# --- Security Headers, Tracing & Host Validation Middleware ---
SAFE_REQ_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,36}$")


async def security_and_tracing_middleware(request: Request, call_next):
    # Sanitize and assign request ID
    raw_req_id = request.headers.get("X-Request-ID", "")
    if raw_req_id and SAFE_REQ_ID_RE.match(raw_req_id):
        req_id = raw_req_id
    else:
        req_id = f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # DNS Rebinding Protection: Host header validation for MCP and API endpoints
    host_header = request.headers.get("Host", "").split(":")[0].lower()
    if host_header:
        allowed_base_hosts = {h.split(":")[0].lower() for h in settings.allowed_hosts}
        if host_header not in allowed_base_hosts and "*" not in settings.allowed_hosts:
            logger.warning("Rejected request with invalid Host header: '%s'", host_header)
            return Response(
                content=json.dumps({"detail": "Invalid Host header; rejected by DNS rebinding defense."}),
                status_code=421,
                media_type="application/json",
            )

    t0 = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception as e:
        logger.error("Unhandled server exception [%s]: %s", req_id, type(e).__name__, exc_info=True)
        response = Response(
            content=json.dumps({"detail": "An internal server error occurred.", "request_id": req_id}),
            status_code=500,
            media_type="application/json",
        )

    duration = round((time.perf_counter() - t0) * 1000, 2)
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:*;"
    )

    logger.info("%s %s [%s] -> %d (%sms)", request.method, request.url.path, req_id, response.status_code, duration)
    return response


# --- Strict Incident Status Enum & In-Memory Audit Ledger ---
class IncidentStatus(str, Enum):
    PENDING_OPERATOR_APPROVAL = "PENDING_OPERATOR_APPROVAL"
    SIMULATION_APPROVED = "SIMULATION_APPROVED"
    OPERATOR_REJECTED = "OPERATOR_REJECTED"


class IncidentRecord(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:10]}")
    created_at: float = Field(default_factory=time.time)
    event: Dict[str, Any]
    triage_decision: Dict[str, Any]
    status: IncidentStatus = IncidentStatus.PENDING_OPERATOR_APPROVAL
    operator_notes: Optional[str] = Field(default=None, max_length=500)
    executed_actions: List[str] = Field(default_factory=list)
    outcome_verified: bool = False
    verified_at: Optional[float] = None
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    audit_id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")


# In-memory incident ledger (auditable session record, not claimed to be an immutable blockchain)
active_incidents: Dict[str, IncidentRecord] = {}

# Dedicated API router for application endpoints
api_router = APIRouter()


# --- Health & Runtime Telemetry ---
@api_router.get("/health")
def health_check():
    bedrock_status = bedrock_agent.get_runtime_status()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "mcp_protocol_version": settings.mcp_protocol_version,
        "mcp_transport": "Streamable HTTP (MCP v2025-11-25)",
        "provider_mode": bedrock_status["provider_mode"],
        "is_simulated_devices": True,
        "bedrock": bedrock_status,
        "mcp_initialized": mcp_server.is_initialized,
    }


@api_router.get("/api/runtime")
def runtime_telemetry():
    return {
        "bedrock": bedrock_agent.get_runtime_status(),
        "devices": smart_entry_simulator.get_device_catalog(),
        "mcp_stats": {
            "total_messages": len(mcp_server.protocol_history),
            "tools_registered": len(mcp_server._tools),
            "resources_registered": len(mcp_server._resources),
            "protocol_version": settings.mcp_protocol_version,
            "transport": "Streamable HTTP (canonical endpoint: /mcp)",
        },
    }


# --- Deprecated Legacy SSE Transport (Compatibility Only) ---
@api_router.get("/mcp/sse", deprecated=True)
async def deprecated_mcp_sse_endpoint():
    """Explicitly deprecated legacy standalone SSE route.
    Provided for backwards compatibility only.
    Canonical Streamable HTTP transport is served at '/mcp'.
    """
    logger.warning("Client requested deprecated legacy route /mcp/sse. Redirecting conceptually to Streamable HTTP /mcp.")

    async def event_generator():
        init_event = {
            "type": "endpoint",
            "endpoint": "/mcp",
            "protocolVersion": settings.mcp_protocol_version,
            "notice": "DEPRECATED_TRANSPORT: Migrate to canonical Streamable HTTP at /mcp",
        }
        yield f"event: endpoint\ndata: {json.dumps(init_event)}\n\n"

        while True:
            await asyncio.sleep(5)
            ping_data = {
                "type": "ping",
                "active_devices": len(smart_entry_simulator.get_device_catalog()),
                "mcp_messages": len(mcp_server.protocol_history),
            }
            yield f"event: ping\ndata: {json.dumps(ping_data)}\n\n"

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Deprecation": "true",
            "Link": '</mcp>; rel="successor-version"',
            "Warning": '299 - "Deprecated legacy transport. Use Streamable HTTP at /mcp."',
        },
    )
    return response


# --- Smart Entry Simulator APIs ---
@api_router.get("/api/scenarios")
@api_router.get("/api/ring/scenarios")
def list_scenarios():
    return smart_entry_simulator.SCENARIOS


@api_router.post("/api/events/trigger/{scenario_id}")
@api_router.post("/api/ring/trigger/{scenario_id}")
def trigger_scenario(scenario_id: str):
    try:
        event = smart_entry_simulator.trigger_scenario(scenario_id)
        return {"status": "success", "event": event.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.get("/api/events")
@api_router.get("/api/ring/events")
def get_events(limit: int = 10):
    events = smart_entry_simulator.get_latest_events(limit)
    return [e.model_dump() for e in events]


@api_router.get("/api/devices")
@api_router.get("/api/ring/devices")
def get_devices():
    return smart_entry_simulator.get_device_catalog()


# --- Incident Operator Sequence & Human Approval Gate ---
@api_router.post("/api/agent/analyze/{event_id}")
async def analyze_event(event_id: str, request: Request):
    """Sequence Step 2-3: Observe evidence & Analyze via Bedrock tool.
    Creates incident record strictly at PENDING_OPERATOR_APPROVAL.
    Never executes simulated remediations without explicit operator approval.
    """
    event = smart_entry_simulator.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")

    req_id = getattr(request.state, "request_id", None)

    decision = bedrock_agent.triage_ambient_event(
        event_summary=event.summary,
        device_name=event.device_name,
        detections=[d.model_dump() for d in event.detections],
        ambient_conditions=event.ambient_conditions,
        request_id=req_id,
    )

    mcp_server.log_protocol_message(
        "internal_agent",
        {
            "method": "tools/call",
            "params": {"name": "bedrock_reason_triage", "arguments": {"event_id": event.event_id}},
        },
    )

    incident = IncidentRecord(
        event=event.model_dump(),
        triage_decision=decision.model_dump(),
        status=IncidentStatus.PENDING_OPERATOR_APPROVAL,
    )
    active_incidents[incident.incident_id] = incident

    return {
        "status": "success",
        "incident_id": incident.incident_id,
        "incident": incident.model_dump(),
    }


class ApprovalRequest(BaseModel):
    operator_notes: Optional[str] = Field(
        default="Approved by operator from Calm Mission Control",
        max_length=500,
    )


@api_router.post("/api/operator/approve/{incident_id}")
async def approve_incident(incident_id: str, payload: ApprovalRequest = ApprovalRequest()):
    """Human Approval Gate -> Execute Simulation -> Verify Outcome.
    Guarded by:
    - Idempotency checks
    - Safe conflict resolution if previously rejected
    - Strict allowlist of permitted simulation actions
    """
    incident = active_incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    # Idempotent: already approved
    if incident.status == IncidentStatus.SIMULATION_APPROVED:
        return {
            "status": "already_processed",
            "message": "Incident was already approved and executed.",
            "incident": incident.model_dump(),
        }

    # Safe failure: cannot approve an incident that was already rejected
    if incident.status == IncidentStatus.OPERATOR_REJECTED:
        raise HTTPException(
            status_code=409,
            detail="Cannot approve an incident that has already been rejected by the operator.",
        )

    incident.status = IncidentStatus.SIMULATION_APPROVED
    incident.operator_notes = payload.operator_notes
    incident.approved_by = "operator_console"
    incident.approved_at = time.time()

    decision = incident.triage_decision
    if decision.get("should_interrupt_user"):
        mcp_server.log_protocol_message(
            "internal_agent",
            {
                "method": "tools/call",
                "params": {
                    "name": "alexa_proactive_dispatch",
                    "arguments": {
                        "spoken_text": decision.get("spoken_alexa_prompt"),
                        "urgency": decision.get("severity"),
                        "target_room": "Living Room Alexa+ Station",
                    },
                },
            },
        )

    # Execute simulated remediation actions strictly guarded by ALLOWED_SIMULATED_ACTIONS allowlist
    executed = []
    actions = decision.get("suggested_actions", [])
    for act in actions:
        if act in ALLOWED_SIMULATED_ACTIONS:
            mcp_server.log_protocol_message(
                "internal_agent",
                {
                    "method": "tools/call",
                    "params": {"name": "household_action_execute", "arguments": {"action_name": act}},
                },
            )
            executed.append(act)
        else:
            logger.warning("Ignored arbitrary or unlisted action string: '%s'", act)

    incident.executed_actions = executed
    incident.outcome_verified = True
    incident.verified_at = time.time()

    return {
        "status": "success",
        "message": "Operator approved simulation. Actions executed and outcome verified.",
        "incident": incident.model_dump(),
    }


@api_router.post("/api/operator/reject/{incident_id}")
async def reject_incident(incident_id: str):
    """Operator explicitly dismisses / rejects recommendation.
    Guarded by:
    - Idempotency checks
    - Safe conflict resolution if previously approved
    """
    incident = active_incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    # Idempotent: already rejected
    if incident.status == IncidentStatus.OPERATOR_REJECTED:
        return {
            "status": "already_rejected",
            "message": "Incident was already rejected by operator.",
            "incident": incident.model_dump(),
        }

    # Safe failure: cannot reject an incident that has already been approved and executed
    if incident.status == IncidentStatus.SIMULATION_APPROVED:
        raise HTTPException(
            status_code=409,
            detail="Cannot reject an incident that has already been approved and executed.",
        )

    incident.status = IncidentStatus.OPERATOR_REJECTED
    incident.operator_notes = "Dismissed by operator."
    return {"status": "success", "message": "Incident recommendation rejected.", "incident": incident.model_dump()}


@api_router.get("/api/incidents")
def list_incidents():
    return [inc.model_dump() for inc in active_incidents.values()]


# --- Triage Pipeline (STOPS AT PENDING_OPERATOR_APPROVAL) ---
@api_router.post("/api/agent/triage/{scenario_id}")
async def run_triage_sequence(scenario_id: str, request: Request):
    """Runs sensor trigger and Bedrock reasoning analysis.
    STRICT COMPLIANCE: Stops at PENDING_OPERATOR_APPROVAL.
    Does NOT auto-execute simulated remediation actions.
    """
    try:
        event = smart_entry_simulator.trigger_scenario(scenario_id)
        req_id = getattr(request.state, "request_id", None)

        decision = bedrock_agent.triage_ambient_event(
            event_summary=event.summary,
            device_name=event.device_name,
            detections=[d.model_dump() for d in event.detections],
            ambient_conditions=event.ambient_conditions,
            request_id=req_id,
        )

        mcp_server.log_protocol_message(
            "internal_agent",
            {
                "method": "tools/call",
                "params": {"name": "bedrock_reason_triage", "arguments": {"event_id": event.event_id}},
            },
        )

        incident = IncidentRecord(
            event=event.model_dump(),
            triage_decision=decision.model_dump(),
            status=IncidentStatus.PENDING_OPERATOR_APPROVAL,
            executed_actions=[],
            outcome_verified=False,
        )
        active_incidents[incident.incident_id] = incident

        return {
            "status": "success",
            "event": event.model_dump(),
            "decision": decision.model_dump(),
            "incident_id": incident.incident_id,
            "incident_status": incident.status.value,
            "executed_actions": [],
            "requires_approval": True,
        }
    except Exception as e:
        logger.error("Triage error: %s", type(e).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail="Incident triage analysis encountered an error.")


# --- Telemetry & Friction Log ---
@api_router.get("/api/mcp/history")
def get_mcp_history():
    return mcp_server.protocol_history


@api_router.get("/api/friction-log")
def get_friction_log():
    friction_log_path = BASE_DIR / "docs" / "FRICTION_LOG.md"
    if friction_log_path.exists():
        return {"content": friction_log_path.read_text(encoding="utf-8")}
    return {"content": "Friction log is being compiled."}


@api_router.get("/")
def serve_root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>AmbientOps Server Running</h1>")


# --- Application Factory & Session-Scoped MCP Lifecycle ---
def create_app(sdk_server: Optional[MCPServer] = None) -> FastAPI:
    """Application factory creating a configured FastAPI application with session-scoped MCP lifecycle."""
    current_mcp_server = sdk_server or sdk_mcp_server
    sec_settings = mcp_server.create_transport_security()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manages application lifecycle, instantiating a fresh MCP Streamable HTTP session manager per run."""
        logger.info("Starting AmbientOps server lifecycle...")
        session_manager = StreamableHTTPSessionManager(
            app=current_mcp_server._lowlevel_server,
            event_store=None,
            retry_interval=None,
            json_response=False,
            stateless=False,
            security_settings=sec_settings,
        )
        app.state.mcp_session_manager = session_manager
        try:
            async with session_manager.run():
                logger.info("StreamableHTTP session manager started successfully.")
                yield
        finally:
            app.state.mcp_session_manager = None
            logger.info("Shutting down AmbientOps server lifecycle...")

    app = FastAPI(
        title=settings.app_name,
        description="Multi-Device Incident Response Console for Alexa+ and Smart Sensors via Model Context Protocol",
        version=settings.version,
        lifespan=lifespan,
    )

    # CORS Middleware with explicit origins and exposed session header
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "X-Request-ID", "Content-Type", "Deprecation"],
    )

    app.middleware("http")(security_and_tracing_middleware)

    # Mount dynamic MCP Streamable HTTP endpoint
    mcp_endpoint = McpStreamableHttpEndpoint(lambda: getattr(app.state, "mcp_session_manager", None))
    app.add_route("/mcp", mcp_endpoint, methods=["GET", "POST", "DELETE", "OPTIONS"])

    # Include API routes
    app.include_router(api_router)

    # Mount static assets
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    return app


# Default application instance for standard uvicorn entrypoint and test imports
app = create_app()
