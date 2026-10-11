"""Test Suite for MCP Server JSON-RPC 2.0 Compliance."""

import pytest
from backend.mcp_server import mcp_server


def test_mcp_initialize():
    req = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == "req-1"
    assert "result" in res
    assert res["result"]["protocolVersion"] == "2025-11-25"
    assert "tools" in res["result"]["capabilities"]


def test_mcp_tools_list():
    req = {"jsonrpc": "2.0", "id": "req-2", "method": "tools/list"}
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "ring_poll_events" in tool_names
    assert "ring_trigger_scenario" in tool_names
    assert "bedrock_reason_triage" in tool_names
    assert "alexa_proactive_dispatch" in tool_names
    assert "household_action_execute" in tool_names


def test_mcp_tool_call_ring_poll():
    req = {
        "jsonrpc": "2.0",
        "id": "req-3",
        "method": "tools/call",
        "params": {"name": "ring_poll_events", "arguments": {"limit": 2}},
    }
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    assert "result" in res
    content = res["result"]["content"][0]
    assert "Retrieved" in content["text"]
    assert len(content["data"]) <= 2


def test_mcp_tool_call_bedrock_triage():
    # Trigger scenario first
    trig_req = {
        "jsonrpc": "2.0",
        "id": "trig-1",
        "method": "tools/call",
        "params": {
            "name": "ring_trigger_scenario",
            "arguments": {"scenario_id": "delivery_weather_risk"},
        },
    }
    trig_res = mcp_server.handle_request(trig_req)
    event_id = trig_res["result"]["content"][0]["event"]["event_id"]

    # Now triage
    triage_req = {
        "jsonrpc": "2.0",
        "id": "req-4",
        "method": "tools/call",
        "params": {
            "name": "bedrock_reason_triage",
            "arguments": {"event_id": event_id},
        },
    }
    res = mcp_server.handle_request(triage_req)
    assert res["jsonrpc"] == "2.0"
    decision = res["result"]["content"][0]["decision"]
    assert decision["risk_score"] > 50
    assert decision["should_interrupt_user"] is True
    assert len(decision["spoken_alexa_prompt"]) > 10


def test_mcp_resources_list_and_read():
    list_req = {"jsonrpc": "2.0", "id": "res-1", "method": "resources/list"}
    list_res = mcp_server.handle_request(list_req)
    uris = [r["uri"] for r in list_res["result"]["resources"]]
    assert "ambient://devices/ring/live" in uris

    read_req = {
        "jsonrpc": "2.0",
        "id": "res-2",
        "method": "resources/read",
        "params": {"uri": "ambient://devices/ring/live"},
    }
    read_res = mcp_server.handle_request(read_req)
    assert "Front Porch" in read_res["result"]["contents"][0]["text"]


def test_mcp_invalid_method():
    req = {"jsonrpc": "2.0", "id": "err-1", "method": "non_existent_method"}
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    assert "error" in res
    assert res["error"]["code"] == -32601
