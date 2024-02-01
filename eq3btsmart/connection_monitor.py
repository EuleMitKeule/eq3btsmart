import asyncio
from collections.abc import Callable

from bleak import BleakClient

from eq3btsmart.const import MONITOR_INTERVAL


class ConnectionMonitor:
    def __init__(self, client: BleakClient):
        self._client = client
        self._run: bool = False
        self._last_connection_state: bool = False
        self._connection_changed_callbacks: list[Callable] = []
        self._client.set_disconnected_callback(lambda client: self._on_disconnected())

    def register_connection_changed_callback(self, callback: Callable):
        self._connection_changed_callbacks.append(callback)

    def _on_disconnected(self):
        asyncio.create_task(self._check_connection())

    async def run(self):
        self._run = True

        while self._run:
            await self._check_connection()

            await asyncio.sleep(MONITOR_INTERVAL)

    async def _check_connection(self):
        if self._run:
            if self._client.is_connected != self._last_connection_state:
                self._last_connection_state = self._client.is_connected

                for callback in self._connection_changed_callbacks:
                    callback(self._last_connection_state)

            try:
                if not self._client.is_connected:
                    await self._client.connect()
            except Exception:
                pass

    async def stop(self):
        self._run = False
