import asyncio

from bleak import BleakClient

from eq3btsmart.const import MONITOR_INTERVAL


class ConnectionMonitor:
    def __init__(self, client: BleakClient):
        self._client = client
        self._run = False

    async def run(self):
        self._run = True

        while self._run:
            try:
                if not self._client.is_connected:
                    await self._client.connect()
            except Exception:
                pass

            await asyncio.sleep(MONITOR_INTERVAL)

    async def stop(self):
        self._run = False
