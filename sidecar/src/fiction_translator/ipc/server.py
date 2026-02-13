"""JSON-RPC server reading from stdin, writing to stdout."""
from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from .protocol import (
    INTERNAL_ERROR,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    parse_message,
)

logger = logging.getLogger(__name__)


class JsonRpcServer:
    """Async JSON-RPC 2.0 server over stdin/stdout."""

    def __init__(self):
        self._handlers: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._running = False
        self._write_lock = asyncio.Lock()

        # Register handlers eagerly
        from .handlers import get_all_handlers, set_server
        self.register_all(get_all_handlers())
        set_server(self)

    def register(self, method: str, handler: Callable[..., Awaitable[Any]]):
        """Register a method handler."""
        self._handlers[method] = handler

    def register_all(self, handlers: dict[str, Callable[..., Awaitable[Any]]]):
        """Register multiple handlers."""
        self._handlers.update(handlers)

    async def send_notification(self, method: str, params: dict[str, Any] | None = None):
        """Send a notification to the Tauri host."""
        notification = JsonRpcNotification(method=method, params=params)
        await self._write(notification.to_json())

    async def _write(self, message: str):
        """Write a message to stdout (non-blocking)."""
        async with self._write_lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_write, message)

    @staticmethod
    def _sync_write(message: str):
        """Synchronous write helper for run_in_executor."""
        sys.stdout.write(message + "\n")
        sys.stdout.flush()

    async def _handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse | None:
        """Process a single request."""
        # Notifications have no id and expect no response
        if request.id is None:
            handler = self._handlers.get(request.method)
            if handler:
                try:
                    await handler(**(request.params or {}))
                except Exception as e:
                    logger.error(f"Notification handler error: {request.method}: {e}")
            return None

        handler = self._handlers.get(request.method)
        if handler is None:
            return JsonRpcResponse(
                id=request.id,
                error=JsonRpcError(code=METHOD_NOT_FOUND, message=f"Method not found: {request.method}"),
            )

        try:
            params = request.params or {}
            if isinstance(params, dict):
                result = await handler(**params)
            else:
                result = await handler(*params)
            return JsonRpcResponse(id=request.id, result=result)
        except Exception as e:
            logger.exception(f"Handler error: {request.method}")
            return JsonRpcResponse(
                id=request.id,
                error=JsonRpcError(code=INTERNAL_ERROR, message=str(e)),
            )

    async def run(self):
        """Main loop: read from stdin, dispatch, write to stdout."""
        logger.info("JSON-RPC server starting on stdin/stdout")
        self._running = True

        # Handlers registered in __init__

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while self._running:
            try:
                line = await reader.readline()
                if not line:
                    logger.info("Stdin closed, shutting down")
                    break

                raw = line.decode("utf-8").strip()
                if not raw:
                    continue

                request = parse_message(raw)
                if request is None:
                    error_resp = JsonRpcResponse(
                        id=None,
                        error=JsonRpcError(code=PARSE_ERROR, message="Parse error"),
                    )
                    await self._write(error_resp.to_json())
                    continue

                response = await self._handle_request(request)
                if response is not None:
                    await self._write(response.to_json())

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Server loop error: {e}")

        logger.info("JSON-RPC server stopped")

    def stop(self):
        """Signal the server to stop."""
        self._running = False
