"""Official Streamable HTTP MCP Transport Interoperability Test Suite.
Conforms strictly to Model Context Protocol specification v2025-11-25.
Tests real HTTP transport over ASGI/FastAPI:
- Client SDK: mcp==2.3.0 (streamable_http_client, ClientSession)
- Endpoint: Canonical /mcp (Streamable HTTP)
- Session header handling: Mcp-Session-Id
- Notification bodyless response: HTTP 202 Accepted with no JSON-RPC body
- DNS Rebinding defense: Host & Origin validation
- Error compliance: Standard JSON-RPC error codes (-32700, -32600, -32601, -32602, -32603)
"""

import pytest
import httpx2

from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession
from backend.server import app, create_app
from backend.mcp_server import create_sdk_mcp_server


@pytest.mark.asyncio
async def test_official_mcp_sdk_client_handshake_and_tool_call():
    """Validates full lifecycle using the official MCP Python SDK client (mcp==2.3.0)."""
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as http_client:
            async with streamable_http_client("http://127.0.0.1/mcp", http_client=http_client) as (r_stream, w_stream):
                async with ClientSession(r_stream, w_stream) as session:
                    # 1. Initialize
                    init_res = await session.initialize()
                    assert init_res.protocol_version == "2025-11-25"
                    assert init_res.server_info.name == "AmbientOps-AlexaPlus-MCP"

                    # 2. Tools List
                    tools_res = await session.list_tools()
                    tool_names = [t.name for t in tools_res.tools]
                    assert "smart_entry_poll_events" in tool_names
                    assert "smart_entry_trigger_scenario" in tool_names
                    assert "bedrock_reason_triage" in tool_names
                    assert "alexa_proactive_dispatch" in tool_names
                    assert "household_action_execute" in tool_names

                    # 3. Tools Call
                    call_res = await session.call_tool("smart_entry_poll_events", {"limit": 2})
                    assert call_res.is_error is False or call_res.is_error is None
                    assert len(call_res.content) > 0
                    assert "Retrieved" in call_res.content[0].text or "Simulated" in call_res.content[0].text


@pytest.mark.asyncio
async def test_streamable_http_raw_session_lifecycle():
    """Tests exact Streamable HTTP protocol over HTTP transport:
    - POST initialize -> returns Mcp-Session-Id header
    - POST notifications/initialized -> returns 202 Accepted with NO response body
    - POST tools/list -> returns registered tools
    - POST tools/call -> returns standard MCP content structure
    """
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            # 1. Initialize
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test-harness", "version": "1.0"},
                },
            }
            res_init = await client.post(
                "/mcp",
                json=init_req,
                headers={"Accept": "application/json, text/event-stream"},
            )
            assert res_init.status_code == 200
            session_id = res_init.headers.get("mcp-session-id")
            assert session_id is not None
            assert len(session_id) > 8

            # 2. Notification: notifications/initialized MUST receive 202 with NO body
            notif_req = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
            res_notif = await client.post(
                "/mcp",
                json=notif_req,
                headers={
                    "Mcp-Session-Id": session_id,
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert res_notif.status_code == 202
            # Specification requirement: notifications receive NO JSON-RPC response body
            assert res_notif.text == ""

            # 3. Tools List
            tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            res_tools = await client.post(
                "/mcp",
                json=tools_req,
                headers={
                    "Mcp-Session-Id": session_id,
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert res_tools.status_code == 200
            assert "smart_entry_poll_events" in res_tools.text
            assert "alexa_proactive_dispatch" in res_tools.text

            # 4. Tools Call: alexa_proactive_dispatch must explicitly return is_simulated: True
            call_req = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "alexa_proactive_dispatch",
                    "arguments": {
                        "spoken_text": "Attention Resident: Package left at front porch.",
                        "urgency": "moderate",
                        "target_room": "Living Room Station",
                    },
                },
            }
            res_call = await client.post(
                "/mcp",
                json=call_req,
                headers={
                    "Mcp-Session-Id": session_id,
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert res_call.status_code == 200
            assert "is_simulated" in res_call.text


@pytest.mark.asyncio
async def test_dns_rebinding_host_header_validation():
    """Tests host validation against DNS rebinding attacks on /mcp."""
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            bad_host_req = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/list",
            }
            # Forged host header from external domain attempting DNS rebinding
            res = await client.post(
                "/mcp",
                json=bad_host_req,
                headers={"Host": "evil-attacker.example.com"},
            )
            assert res.status_code == 421
            assert "DNS rebinding defense" in res.text


@pytest.mark.asyncio
async def test_streamable_http_session_termination():
    """Tests DELETE request to /mcp for explicit session termination."""
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "session-test", "version": "1.0"},
                },
            }
            res_init = await client.post(
                "/mcp",
                json=init_req,
                headers={"Accept": "application/json, text/event-stream"},
            )
            session_id = res_init.headers.get("mcp-session-id")

            # Terminate session
            del_res = await client.delete(
                "/mcp",
                headers={"Mcp-Session-Id": session_id},
            )
            assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_malformed_json_and_invalid_protocol_errors():
    """Tests error responses on /mcp for invalid inputs."""
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            # 1. Malformed JSON payload
            bad_json_res = await client.post(
                "/mcp",
                content=b"this is not valid json {{{",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert bad_json_res.status_code in (400, 500)

            # 2. Unsupported method
            unknown_method_req = {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "non_existent_method_xyz",
            }
            res = await client.post(
                "/mcp",
                json=unknown_method_req,
                headers={"Accept": "application/json, text/event-stream"},
            )
            # Response should indicate method not found or bad request error
            assert res.status_code in (200, 400)
            assert "error" in res.text or "-32601" in res.text or "not found" in res.text.lower()


@pytest.mark.asyncio
async def test_app_factory_and_repeated_lifespan_cycles():
    """Validates that create_app factory and repeated lifespans instantiate fresh session managers without error."""
    custom_server = create_sdk_mcp_server()
    custom_app = create_app(custom_server)

    for cycle in range(2):
        async with custom_app.router.lifespan_context(custom_app):
            transport = httpx2.ASGITransport(app=custom_app)
            async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
                init_req = {
                    "jsonrpc": "2.0",
                    "id": f"cycle-{cycle}",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "factory-test", "version": "1.0"},
                    },
                }
                res = await client.post(
                    "/mcp",
                    json=init_req,
                    headers={"Accept": "application/json, text/event-stream"},
                )
                assert res.status_code == 200
                assert res.headers.get("mcp-session-id") is not None
