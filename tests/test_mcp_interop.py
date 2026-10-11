"""Automated MCP Interoperability & Conformance Test Suite.
Validates MCP specification v2025-11-25 handshake, tool discovery, execution, and error handling.
"""

import pytest
from backend.mcp_server import mcp_server


def test_mcp_full_interop_lifecycle():
    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": "interop-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "alexa-plus-client", "version": "2.0"},
        },
    }
    init_res = mcp_server.handle_request(init_req)
    assert init_res["jsonrpc"] == "2.0"
    assert init_res["id"] == "interop-1"
    assert init_res["result"]["protocolVersion"] == "2025-11-25"
    assert "tools" in init_res["result"]["capabilities"]
    assert mcp_server.is_initialized is True

    # 2. Initialized Notification
    notif_req = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    notif_res = mcp_server.handle_request(notif_req)
    assert notif_res["result"]["initialized"] is True

    # 3. Ping
    ping_req = {"jsonrpc": "2.0", "id": "ping-1", "method": "ping"}
    ping_res = mcp_server.handle_request(ping_req)
    assert ping_res["result"] == {}

    # 4. Tools List
    list_req = {"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list"}
    list_res = mcp_server.handle_request(list_req)
    tool_names = [t["name"] for t in list_res["result"]["tools"]]
    assert "smart_entry_poll_events" in tool_names
    assert "smart_entry_trigger_scenario" in tool_names
    assert "bedrock_reason_triage" in tool_names
    assert "alexa_proactive_dispatch" in tool_names
    assert "household_action_execute" in tool_names


def test_mcp_tools_call_execution_paths():
    # Trigger scenario
    trig_req = {
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {
            "name": "smart_entry_trigger_scenario",
            "arguments": {"scenario_id": "pet_escape_risk"},
        },
    }
    trig_res = mcp_server.handle_request(trig_req)
    assert trig_res["result"]["content"][0]["event"]["scenario_id"] == "pet_escape_risk"
    event_id = trig_res["result"]["content"][0]["event"]["event_id"]

    # Poll events
    poll_req = {
        "jsonrpc": "2.0",
        "id": "call-2",
        "method": "tools/call",
        "params": {
            "name": "smart_entry_poll_events",
            "arguments": {"limit": 3},
        },
    }
    poll_res = mcp_server.handle_request(poll_req)
    assert len(poll_res["result"]["content"][0]["data"]) <= 3

    # Triage via Bedrock tool
    triage_req = {
        "jsonrpc": "2.0",
        "id": "call-3",
        "method": "tools/call",
        "params": {
            "name": "bedrock_reason_triage",
            "arguments": {"event_id": event_id},
        },
    }
    triage_res = mcp_server.handle_request(triage_req)
    decision = triage_res["result"]["content"][0]["decision"]
    assert "decision_rationale" in decision
    assert decision["risk_score"] > 50

    # Dispatch Alexa+ voice prompt
    dispatch_req = {
        "jsonrpc": "2.0",
        "id": "call-4",
        "method": "tools/call",
        "params": {
            "name": "alexa_proactive_dispatch",
            "arguments": {
                "spoken_text": "Perimeter alert: Pet near back gate.",
                "urgency": "moderate",
                "target_room": "Kitchen Echo Show",
            },
        },
    }
    dispatch_res = mcp_server.handle_request(dispatch_req)
    assert "dispatched_at" in dispatch_res["result"]["content"][0]["dispatch"]

    # Execute Household Action Simulation
    action_req = {
        "jsonrpc": "2.0",
        "id": "call-5",
        "method": "tools/call",
        "params": {
            "name": "household_action_execute",
            "arguments": {"action_name": "latch_gate_lock"},
        },
    }
    action_res = mcp_server.handle_request(action_req)
    assert action_res["result"]["content"][0]["status"] == "success"
    assert action_res["result"]["content"][0]["is_simulated"] is True


def test_mcp_error_paths():
    # 1. Non-dict parse error
    raw_bad = "NOT_A_DICT"
    res1 = mcp_server.handle_request(raw_bad)
    assert res1["error"]["code"] == -32700

    # 2. Invalid JSON-RPC structure (missing method)
    res2 = mcp_server.handle_request({"jsonrpc": "2.0", "id": 99})
    assert res2["error"]["code"] == -32600

    # 3. Method not found
    res3 = mcp_server.handle_request({"jsonrpc": "2.0", "id": 100, "method": "unsupported_func"})
    assert res3["error"]["code"] == -32601

    # 4. Unknown tool
    res4 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/call",
        "params": {"name": "ghost_tool"},
    })
    assert res4["error"]["code"] == -32602
    assert "not registered" in res4["error"]["message"]

    # 5. Invalid arguments
    res5 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "smart_entry_poll_events",
            "arguments": {"limit": 999},  # exceeds limit
        },
    })
    assert res5["error"]["code"] == -32602

    # 6. Missing required arguments
    res6 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 103,
        "method": "tools/call",
        "params": {
            "name": "alexa_proactive_dispatch",
            "arguments": {"urgency": "critical"},  # missing spoken_text
        },
    })
    assert res6["error"]["code"] == -32602

    # 7. Invalid resource URI
    res7 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 104,
        "method": "resources/read",
        "params": {"uri": "ambient://invalid/path"},
    })
    assert res7["error"]["code"] == -32602

    # 8. Invalid prompt name
    res8 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 105,
        "method": "prompts/get",
        "params": {"name": "non_existent_prompt"},
    })
    assert res8["error"]["code"] == -32602


def test_mcp_prompts_and_resources_full_coverage():
    # Prompts list & get
    p_list = mcp_server.handle_request({"jsonrpc": "2.0", "id": 201, "method": "prompts/list"})
    assert len(p_list["result"]["prompts"]) >= 2

    p_get1 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 202,
        "method": "prompts/get",
        "params": {"name": "triage_incident"},
    })
    assert "messages" in p_get1["result"]

    p_get2 = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 203,
        "method": "prompts/get",
        "params": {"name": "daily_ambient_brief"},
    })
    assert "messages" in p_get2["result"]

    # Resources read
    r_ctx = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 204,
        "method": "resources/read",
        "params": {"uri": "ambient://household/context"},
    })
    assert "Abhijeet" in r_ctx["result"]["contents"][0]["text"]

    r_tel = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 205,
        "method": "resources/read",
        "params": {"uri": "ambient://telemetry/mcp"},
    })
    assert "total_messages" in r_tel["result"]["contents"][0]["text"]

