import asyncio

from bleak import BleakClient


class Eq3ConnectionMonitor:
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

            await asyncio.sleep(5)

    async def stop(self):
        self._run = False
