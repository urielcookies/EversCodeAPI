"""
PostgreSQL LISTEN/NOTIFY realtime manager + SSE helper.

How it works:
  1. RealtimeManager opens a raw asyncpg connection (separate from SQLAlchemy pool).
  2. It calls LISTEN on a channel name, e.g. "app_one_updates".
  3. sse_generator() polls that connection and yields SSE-formatted strings.
  4. FastAPI's StreamingResponse streams those strings to the browser.

How to send notifications from PostgreSQL:
  -- Ad-hoc from psql:
  NOTIFY app_one_updates, '{"id": 1, "action": "created"}';

  -- From a trigger (fire on INSERT):
  CREATE OR REPLACE FUNCTION notify_app_one() RETURNS trigger AS $$
  BEGIN
    PERFORM pg_notify('app_one_updates', row_to_json(NEW)::text);
    RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;

  CREATE TRIGGER app_one_insert_notify
    AFTER INSERT ON items
    FOR EACH ROW EXECUTE FUNCTION notify_app_one();
"""

import asyncio
import asyncpg

from core.config import settings


class RealtimeManager:
    """
    Manages a single asyncpg connection per channel for LISTEN/NOTIFY.
    Call listen() during app startup and unlisten() on shutdown.
    """

    def __init__(self) -> None:
        # Maps channel name -> asyncpg Connection
        self._connections: dict[str, asyncpg.Connection] = {}
        # Maps channel name -> asyncio.Queue of incoming notification payloads
        self._queues: dict[str, asyncio.Queue] = {}

    async def listen(self, channel: str) -> None:
        """Open a dedicated asyncpg connection and start listening on `channel`."""
        # asyncpg uses the raw postgres:// DSN, not the sqlalchemy+asyncpg:// one
        raw_dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(raw_dsn)
        queue: asyncio.Queue = asyncio.Queue()

        def _on_notify(conn, pid, channel, payload):
            # Called by asyncpg on each NOTIFY; enqueue the payload for SSE consumers
            queue.put_nowait(payload)

        await conn.add_listener(channel, _on_notify)
        self._connections[channel] = conn
        self._queues[channel] = queue

    async def unlisten(self, channel: str) -> None:
        """Stop listening and close the connection for `channel`."""
        conn = self._connections.pop(channel, None)
        if conn:
            await conn.close()
        self._queues.pop(channel, None)

    async def sse_generator(self, channel: str):
        """
        Async generator that yields SSE-formatted strings for a given channel.
        Mount this as a StreamingResponse in your route handler.

        SSE wire format:
            data: <payload>\n\n
        """
        queue = self._queues.get(channel)
        if queue is None:
            # Channel not registered — send one error event then stop
            yield f"event: error\ndata: channel '{channel}' is not active\n\n"
            return

        # Send an initial connection event so the browser knows it's live
        yield f"event: connected\ndata: listening on {channel}\n\n"

        while True:
            # Wait for the next notification (poll every second to stay alive)
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat comment to keep the connection open through proxies
                yield ": heartbeat\n\n"


# Module-level singleton — imported by main.py and route handlers
realtime = RealtimeManager()
