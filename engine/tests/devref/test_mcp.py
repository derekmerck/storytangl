from __future__ import annotations

from io import BytesIO

import pytest

from tangl.devref.mcp import DevRefMcpServer, ParseError, _read_message
from tangl.devref.query import build_context_pack, get_topic_map, search_topics


def test_mcp_tool_calls_match_backend_models(devref_db_path) -> None:
    server = DevRefMcpServer(db_path=str(devref_db_path))

    assert server.call_tool("find_topics", {"query": "entity", "limit": 5}) == search_topics(
        "entity",
        limit=5,
        db_path=devref_db_path,
    ).model_dump(mode="python")
    assert server.call_tool("get_topic_map", {"topic_id": "ledger", "limit": 6}) == get_topic_map(
        "ledger",
        limit=6,
        db_path=devref_db_path,
    ).model_dump(mode="python")
    assert server.call_tool(
        "build_context_pack",
        {"topic_ids": ["phase_ctx"], "limit": 6},
    ) == build_context_pack(
        ["phase_ctx"],
        limit=6,
        db_path=devref_db_path,
    ).model_dump(mode="python")


def test_mcp_handle_request_lists_tools(devref_db_path) -> None:
    server = DevRefMcpServer(db_path=str(devref_db_path))

    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
    )

    assert response is not None
    assert [tool["name"] for tool in response["result"]["tools"]] == [
        "find_topics",
        "get_topic_map",
        "build_context_pack",
    ]


def test_mcp_unknown_notification_does_not_respond(devref_db_path) -> None:
    server = DevRefMcpServer(db_path=str(devref_db_path))

    assert server.handle_request({"jsonrpc": "2.0", "method": "unknown"}) is None


def test_mcp_read_message_rejects_bad_content_length() -> None:
    stream = BytesIO(b"Content-Length: nope\r\n\r\n{}")

    with pytest.raises(ParseError):
        _read_message(stream)


def test_mcp_read_message_rejects_bad_json() -> None:
    stream = BytesIO(b"Content-Length: 1\r\n\r\n{")

    with pytest.raises(ParseError):
        _read_message(stream)
