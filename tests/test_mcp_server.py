"""Test Suite for MCP Server JSON-RPC 2.0 Compliance & Tools Logic."""

import json
import pytest
from backend.mcp_server import (
    mcp_server,
    smart_entry_poll_events as sdk_poll,
    smart_entry_trigger_scenario as sdk_trigger,
    ring_poll_events as sdk_ring_poll,
    ring_trigger_scenario as sdk_ring_trigger,
    bedrock_reason_triage as sdk_triage,
    alexa_proactive_dispatch as sdk_alexa,
    household_action_execute as sdk_action,
    get_sensor_fleet_resource,
    get_ring_sensors_alias,
    get_household_context_resource,
    get_telemetry_resource,
    triage_incident_prompt,
    daily_ambient_brief_prompt,
)


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


def test_mcp_notification_initialized_returns_none():
    notif_req = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    res = mcp_server.handle_request(notif_req)
    # Specification requirement: notifications receive NO JSON-RPC response body
    assert res is None


def test_mcp_tools_list():
    req = {"jsonrpc": "2.0", "id": "req-2", "method": "tools/list"}
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "smart_entry_poll_events" in tool_names
    assert "smart_entry_trigger_scenario" in tool_names
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
    trig_req = {
        "jsonrpc": "2.0",
        "id": "trig-1",
        "method": "tools/call",
        "params": {
            "name": "smart_entry_trigger_scenario",
            "arguments": {"scenario_id": "delivery_weather_risk"},
        },
    }
    trig_res = mcp_server.handle_request(trig_req)
    event_id = trig_res["result"]["content"][0]["event"]["event_id"]

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


def test_mcp_tool_call_alexa_dispatch_and_household_actions():
    # Alexa dispatch
    alexa_req = {
        "jsonrpc": "2.0",
        "id": "req-alexa",
        "method": "tools/call",
        "params": {
            "name": "alexa_proactive_dispatch",
            "arguments": {"spoken_text": "Hello Resident", "urgency": "low"},
        },
    }
    alexa_res = mcp_server.handle_request(alexa_req)
    assert alexa_res["jsonrpc"] == "2.0"
    assert alexa_res["result"]["content"][0]["dispatch"]["is_simulated"] is True

    # Allowed action
    act_req = {
        "jsonrpc": "2.0",
        "id": "req-act",
        "method": "tools/call",
        "params": {
            "name": "household_action_execute",
            "arguments": {"action_name": "unlock_porch_storage"},
        },
    }
    act_res = mcp_server.handle_request(act_req)
    assert act_res["result"]["content"][0]["status"] == "success"

    # Disallowed action
    bad_act_req = {
        "jsonrpc": "2.0",
        "id": "req-bad-act",
        "method": "tools/call",
        "params": {
            "name": "household_action_execute",
            "arguments": {"action_name": "arbitrary_unauthorized_action"},
        },
    }
    bad_act_res = mcp_server.handle_request(bad_act_req)
    assert "error" in bad_act_res
    assert bad_act_res["error"]["code"] == -32602


def test_mcp_resources_list_and_read():
    list_req = {"jsonrpc": "2.0", "id": "res-1", "method": "resources/list"}
    list_res = mcp_server.handle_request(list_req)
    uris = [r["uri"] for r in list_res["result"]["resources"]]
    assert "ambient://devices/sensors/live" in uris
    assert "ambient://household/context" in uris

    # Read sensor fleet
    read_req = {
        "jsonrpc": "2.0",
        "id": "res-2",
        "method": "resources/read",
        "params": {"uri": "ambient://devices/sensors/live"},
    }
    read_res = mcp_server.handle_request(read_req)
    assert "Front Porch" in read_res["result"]["contents"][0]["text"]

    # Read household context
    read_ctx = {
        "jsonrpc": "2.0",
        "id": "res-3",
        "method": "resources/read",
        "params": {"uri": "ambient://household/context"},
    }
    ctx_res = mcp_server.handle_request(read_ctx)
    assert "Demo Household" in ctx_res["result"]["contents"][0]["text"]


def test_mcp_prompts_list_and_get():
    p_list = mcp_server.handle_request({"jsonrpc": "2.0", "id": "p-1", "method": "prompts/list"})
    assert len(p_list["result"]["prompts"]) >= 2

    p_get = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": "p-2",
        "method": "prompts/get",
        "params": {"name": "triage_incident"},
    })
    assert "messages" in p_get["result"]


def test_mcp_invalid_method():
    req = {"jsonrpc": "2.0", "id": "err-1", "method": "non_existent_method"}
    res = mcp_server.handle_request(req)
    assert res["jsonrpc"] == "2.0"
    assert "error" in res
    assert res["error"]["code"] == -32601


def test_sdk_tool_functions_directly():
    # Direct tests of the registered tool handlers
    res_poll = sdk_poll(3)
    parsed_poll = json.loads(res_poll)
    assert parsed_poll["count"] == 3
    assert parsed_poll["is_simulated"] is True

    res_alias_poll = sdk_ring_poll(1)
    assert json.loads(res_alias_poll)["count"] == 1

    res_trig = sdk_trigger("pet_escape_risk")
    assert json.loads(res_trig)["is_simulated"] is True

    res_alias_trig = sdk_ring_trigger("routine_postal_visit")
    assert json.loads(res_alias_trig)["scenario_id"] == "routine_postal_visit"

    event_id = json.loads(res_trig)["event"]["event_id"]
    res_triage = sdk_triage(event_id)
    assert json.loads(res_triage)["status"] == "success"

    res_alexa = sdk_alexa("Resident alert", "critical")
    assert json.loads(res_alexa)["is_simulated"] is True

    res_act = sdk_action("sound_backyard_chime")
    assert json.loads(res_act)["status"] == "success"

    with pytest.raises(ValueError):
        sdk_action("unauthorized_action_name")

    with pytest.raises(ValueError):
        sdk_poll(25)  # Out of range

    # Direct tests of resources
    assert "sim_entry_doorbell_01" in get_sensor_fleet_resource()
    assert "sim_entry_doorbell_01" in get_ring_sensors_alias()
    assert "Demo Household" in get_household_context_resource()
    assert "Streamable HTTP" in get_telemetry_resource()

    # Direct tests of prompts
    assert "smart device sensor" in triage_incident_prompt()
    assert "verbal briefing" in daily_ambient_brief_prompt()
