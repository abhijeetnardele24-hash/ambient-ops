"""AmbientOps FastAPI Backend & MCP SSE Transport Server.
Serves MCP endpoints, Ring Playground APIs, Bedrock reasoning, and static frontend.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .mcp_server import mcp_server
from .ring_simulator import ring_simulator
from .bedrock_agent import bedrock_agent

app = FastAPI(
    title="AmbientOps API",
    description="Autonomous Multi-Device MCP Agent for Alexa+ & Ring powered by Amazon Bedrock",
    version=settings.version,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# --- Health & Status ---
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "mcp_protocol_version": settings.mcp_protocol_version,
        "bedrock_mock": settings.use_bedrock_mock,
    }


# --- Model Context Protocol (MCP) Endpoints ---
@app.post("/mcp")
async def mcp_jsonrpc_endpoint(request: Request):
    """Standard MCP JSON-RPC 2.0 HTTP transport endpoint."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    response = mcp_server.handle_request(body)
    return response


@app.get("/mcp/sse")
async def mcp_sse_endpoint():
    """Streamable HTTP / Server-Sent Events (SSE) MCP Transport."""
    async def event_generator():
        # Send initial endpoint registration event
        init_event = {
            "type": "endpoint",
            "endpoint": "/mcp",
            "protocolVersion": settings.mcp_protocol_version,
        }
        yield f"event: endpoint\ndata: {json.dumps(init_event)}\n\n"

        # Stream recent telemetry ping every 5 seconds
        while True:
            await asyncio.sleep(5)
            ping_data = {
                "type": "ping",
                "active_devices": len(ring_simulator.get_device_catalog()),
                "mcp_messages": len(mcp_server.protocol_history),
            }
            yield f"event: ping\ndata: {json.dumps(ping_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Ring Simulator APIs ---
@app.get("/api/ring/scenarios")
def list_scenarios():
    return ring_simulator.SCENARIOS


@app.post("/api/ring/trigger/{scenario_id}")
def trigger_scenario(scenario_id: str):
    try:
        event = ring_simulator.trigger_scenario(scenario_id)
        return {"status": "success", "event": event.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ring/events")
def get_ring_events(limit: int = 10):
    events = ring_simulator.get_latest_events(limit)
    return [e.model_dump() for e in events]


@app.get("/api/ring/devices")
def get_ring_devices():
    return ring_simulator.get_device_catalog()


# --- Full Autonomous Agent Pipeline Execution ---
@app.post("/api/agent/triage/{scenario_id}")
async def run_autonomous_triage(scenario_id: str):
    """Executes the full chain:
    1. Triggers Ring scenario
    2. Logs MCP Tool Call: ring_poll_events
    3. Invokes Bedrock Converse reasoning
    4. Logs MCP Tool Call: alexa_proactive_dispatch
    5. Logs MCP Tool Call: household_action_execute
    """
    try:
        # 1. Trigger Scenario
        event = ring_simulator.trigger_scenario(scenario_id)

        # 2. Simulate MCP Tool: ring_poll_events
        mcp_server.log_protocol_message(
            "internal_agent",
            {
                "method": "tools/call",
                "params": {"name": "ring_poll_events", "arguments": {"limit": 1}},
            },
        )

        # 3. Bedrock Multimodal Reasoning
        decision = bedrock_agent.triage_ambient_event(
            event_summary=event.summary,
            device_name=event.device_name,
            detections=[d.model_dump() for d in event.detections],
            ambient_conditions=event.ambient_conditions,
        )

        # 4. Simulate MCP Tool: bedrock_reason_triage
        mcp_server.log_protocol_message(
            "internal_agent",
            {
                "method": "tools/call",
                "params": {
                    "name": "bedrock_reason_triage",
                    "arguments": {"event_id": event.event_id},
                },
            },
        )

        # 5. Simulate MCP Tool: alexa_proactive_dispatch
        if decision.should_interrupt_user:
            mcp_server.log_protocol_message(
                "internal_agent",
                {
                    "method": "tools/call",
                    "params": {
                        "name": "alexa_proactive_dispatch",
                        "arguments": {
                            "spoken_text": decision.spoken_alexa_prompt,
                            "urgency": decision.severity,
                            "target_room": "Living Room Alexa+ Station",
                        },
                    },
                },
            )

        # 6. Execute household actions
        executed_actions = []
        for act in decision.suggested_actions:
            mcp_server.log_protocol_message(
                "internal_agent",
                {
                    "method": "tools/call",
                    "params": {
                        "name": "household_action_execute",
                        "arguments": {"action_name": act},
                    },
                },
            )
            executed_actions.append(act)

        return {
            "status": "success",
            "event": event.model_dump(),
            "decision": decision.model_dump(),
            "executed_actions": executed_actions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Telemetry & Protocol History ---
@app.get("/api/mcp/history")
def get_mcp_history():
    return mcp_server.protocol_history


@app.get("/api/friction-log")
def get_friction_log():
    friction_log_path = BASE_DIR / "docs" / "FRICTION_LOG.md"
    if friction_log_path.exists():
        return {"content": friction_log_path.read_text(encoding="utf-8")}
    return {"content": "Friction log is being compiled."}


# --- Static Frontend Delivery ---
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>AmbientOps Server Running</h1>")
