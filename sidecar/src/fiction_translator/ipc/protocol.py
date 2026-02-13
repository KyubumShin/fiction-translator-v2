"""JSON-RPC 2.0 protocol types and helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 Request."""
    method: str
    params: dict[str, Any] | list[Any] | None = None
    id: int | str | None = None
    jsonrpc: str = "2.0"

    def to_json(self) -> str:
        d = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            d["params"] = self.params
        if self.id is not None:
            d["id"] = self.id
        return json.dumps(d)

    @classmethod
    def from_dict(cls, data: dict) -> JsonRpcRequest:
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 Response."""
    id: int | str | None
    result: Any = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    def to_json(self) -> str:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = {"code": self.error.code, "message": self.error.message}
            if self.error.data is not None:
                d["error"]["data"] = self.error.data
        else:
            d["result"] = self.result
        return json.dumps(d)


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 Error."""
    code: int
    message: str
    data: Any = None

# Standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class JsonRpcNotification:
    """JSON-RPC 2.0 Notification (no id, no response expected)."""
    method: str
    params: dict[str, Any] | None = None
    jsonrpc: str = "2.0"

    def to_json(self) -> str:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            d["params"] = self.params
        return json.dumps(d)


def parse_message(raw: str) -> JsonRpcRequest | None:
    """Parse a raw JSON string into a JsonRpcRequest."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "method" not in data:
        return None
    return JsonRpcRequest.from_dict(data)
