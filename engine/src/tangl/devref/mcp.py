"""Minimal stdio MCP server for the StoryTangl developer topic reference index."""

from __future__ import annotations

import json
import sys
from typing import Any

from .builder import DEFAULT_DB_PATH
from .query import build_context_pack, get_topic_map, search_topics


class ParseError(Exception):
    """Raised when a framed JSON-RPC message cannot be parsed."""


def _json_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _json_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


class DevRefMcpServer:
    """Very small MCP tool server over stdio content-length framing."""

    def __init__(self, *, db_path: str | None = None):
        self.db_path = db_path or str(DEFAULT_DB_PATH)

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "find_topics",
                "description": "Search StoryTangl developer topics and ranked artifacts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "facets": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_topic_map",
                "description": "Return one topic with related topics and linked artifacts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "required": ["topic_id"],
                },
            },
            {
                "name": "build_context_pack",
                "description": "Build a compact agent-oriented context pack for one or more topics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic_ids": {"type": "array", "items": {"type": "string"}},
                        "facets": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "required": ["topic_ids"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "find_topics":
            return search_topics(
                args["query"],
                facets=args.get("facets"),
                limit=args.get("limit", 20),
                db_path=self.db_path,
            ).model_dump(mode="python")
        if name == "get_topic_map":
            return get_topic_map(
                args["topic_id"],
                limit=args.get("limit", 24),
                db_path=self.db_path,
            ).model_dump(mode="python")
        if name == "build_context_pack":
            return build_context_pack(
                args["topic_ids"],
                facets=args.get("facets"),
                limit=args.get("limit", 12),
                db_path=self.db_path,
            ).model_dump(mode="python")
        raise KeyError(f"Unknown MCP tool: {name}")

    def handle_request(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        method = payload.get("method")
        request_id = payload.get("id")
        is_notification = "id" not in payload or request_id is None

        if is_notification:
            return None

        if method == "initialize":
            return _json_response(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "storytangl-devref",
                        "version": "1.0.0",
                    },
                },
            )
        if method == "ping":
            return _json_response(request_id, {})
        if method == "tools/list":
            return _json_response(request_id, {"tools": self.tool_definitions()})
        if method == "tools/call":
            params = payload.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                result = self.call_tool(tool_name, arguments)
            except Exception as exc:  # pragma: no cover - defensive transport boundary
                return _json_error(request_id, -32000, str(exc))
            return _json_response(
                request_id,
                {
                    "content": [
                        {
                            "type": "json",
                            "json": result,
                        }
                    ],
                    "isError": False,
                },
            )
        return _json_error(request_id, -32601, f"Method not found: {method}")


def _read_message(stream) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        try:
            name, _, value = line.decode("utf-8").partition(":")
        except UnicodeDecodeError as exc:
            raise ParseError("Invalid JSON-RPC header") from exc
        headers[name.strip().lower()] = value.strip()
    try:
        length = int(headers.get("content-length", "0"))
    except ValueError as exc:
        raise ParseError("Invalid Content-Length header") from exc
    if length <= 0:
        return None
    body = stream.read(length)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParseError("Invalid JSON-RPC payload") from exc


def _write_message(stream, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    stream.write(body)
    stream.flush()


def main() -> None:
    """Run the MCP server over stdio."""

    server = DevRefMcpServer()
    while True:
        try:
            payload = _read_message(sys.stdin.buffer)
        except ParseError:
            _write_message(sys.stdout.buffer, _json_error(None, -32700, "Parse error"))
            continue
        if payload is None:
            break
        response = server.handle_request(payload)
        if response is not None:
            _write_message(sys.stdout.buffer, response)


if __name__ == "__main__":
    main()
