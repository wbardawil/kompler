"""In-process async event bus.

The backbone of Kompler's agentic architecture. Every state change emits an event.
Agents, webhooks, and audit loggers subscribe to events they care about.

Usage:
    bus = EventBus()
    bus.on("document.uploaded", handle_new_document)
    await bus.emit("document.uploaded", {"document_id": "...", "tenant_id": "..."})
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type for async event handlers
EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Async in-process event bus with topic-based routing."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[dict] = []  # Recent events for debugging
        self._max_history = 100

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for {event_type}: {handler.__name__}")

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Emit an event to all registered handlers.

        Handlers run concurrently. Failures in one handler don't block others.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }

        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"Event {event_type} emitted, no handlers registered")
            return

        logger.info(
            f"Event {event_type} → {len(handlers)} handler(s)",
            extra={"event_id": event["event_id"], **payload} if payload else {},
        )

        # Run all handlers concurrently, catch individual failures
        results = await asyncio.gather(
            *[self._safe_call(h, event) for h in handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Handler {handlers[i].__name__} failed for {event_type}: {result}"
                )

    async def _safe_call(self, handler: EventHandler, event: dict) -> None:
        """Call a handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.exception(f"Event handler error: {e}")
            raise

    def get_recent_events(self, event_type: str | None = None, limit: int = 20) -> list[dict]:
        """Get recent events for debugging."""
        events = self._history
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        return events[-limit:]


# Singleton event bus instance
event_bus = EventBus()
