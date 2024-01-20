"""Bleak connection backend."""
import asyncio
import logging
from typing import Callable, cast

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from eq3btsmart.const import (
    PROP_NTFY_UUID,
    PROP_WRITE_UUID,
    REQUEST_TIMEOUT,
    RETRIES,
    RETRY_BACK_OFF_FACTOR,
    Adapter,
)
from eq3btsmart.exceptions import BackendException
from eq3btsmart.thermostat_config import ThermostatConfig

# bleak backends are very loud on debug, this reduces the log spam when using --debug
# logging.getLogger("bleak.backends").setLevel(logging.WARNING)
_LOGGER = logging.getLogger(__name__)


class BleakConnection:
    """Representation of a BTLE Connection."""

    def __init__(
        self,
        thermostat_config: ThermostatConfig,
        device: BLEDevice,
        callback: Callable,
    ):
        """Initialize the connection."""

        self.thermostat_config = thermostat_config
        self._callback = callback
        self._notify_event = asyncio.Event()
        self._terminate_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._conn: BleakClient | None = None
        self._device: BLEDevice = device
        self._connection_callbacks: list[Callable] = []
        self.retries = 0
        self._round_robin = 0

    def register_connection_callback(self, callback: Callable) -> None:
        self._connection_callbacks.append(callback)

    async def async_connect(self) -> None:
        match self.thermostat_config.adapter:
            case Adapter.AUTO:
                self._conn = await establish_connection(
                    client_class=BleakClient,
                    device=self._device,
                    name=self.thermostat_config.name,
                    disconnected_callback=lambda client: self._on_connection_event(),
                    max_attempts=2,
                    use_services_cache=True,
                )

            case Adapter.LOCAL:
                UnwrappedBleakClient = cast(type[BleakClient], BleakClient.__bases__[0])
                self._conn = UnwrappedBleakClient(
                    self._device,
                    disconnected_callback=lambda client: self._on_connection_event(),
                    dangerous_use_bleak_cache=True,
                )
                await self._conn.connect()

        if self._conn is None or not self._conn.is_connected:
            raise BackendException("Can't connect")

    def disconnect(self) -> None:
        self._terminate_event.set()
        self._notify_event.set()

    async def throw_if_terminating(self) -> None:
        if self._terminate_event.is_set():
            if self._conn:
                await self._conn.disconnect()
            raise Exception("Connection cancelled by shutdown")

    async def on_notification(
        self, handle: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle Callback from a Bluetooth (GATT) request."""
        if PROP_NTFY_UUID == handle.uuid:
            self._notify_event.set()
            data_bytes = bytes(data)
            self._callback(data_bytes)
        else:
            _LOGGER.error(
                "[%s] wrong charasteristic: %s, %s",
                self.thermostat_config.name,
                handle.handle,
                handle.uuid,
            )

    async def async_make_request(
        self, value: bytes | None = None, retries: int = RETRIES
    ) -> None:
        """Write a GATT Command with callback - not utf-8."""
        async with self._lock:  # only one concurrent request per thermostat
            try:
                await self._async_make_request_try(value, retries)
            finally:
                self.retries = 0
                self._on_connection_event()

    async def _async_make_request_try(
        self, value: bytes | None = None, retries: int = RETRIES
    ) -> None:
        self.retries = 0
        while True:
            self.retries += 1
            self._on_connection_event()
            try:
                await self.throw_if_terminating()
                await self.async_connect()

                if self._conn is None:
                    raise BackendException("Can't connect")

                self._notify_event.clear()
                if value is not None:
                    try:
                        await self._conn.start_notify(
                            PROP_NTFY_UUID, self.on_notification
                        )
                        await self._conn.write_gatt_char(
                            PROP_WRITE_UUID, value, response=True
                        )
                        await asyncio.wait_for(
                            self._notify_event.wait(), REQUEST_TIMEOUT
                        )
                    finally:
                        if self.thermostat_config.stay_connected:
                            await self._conn.stop_notify(PROP_NTFY_UUID)
                        else:
                            await self._conn.disconnect()
                return
            except Exception as ex:
                await self.throw_if_terminating()

                self._round_robin = self._round_robin + 1

                if self.retries >= retries:
                    raise ex

                await asyncio.sleep(RETRY_BACK_OFF_FACTOR * self.retries)

    def _on_connection_event(self) -> None:
        for callback in self._connection_callbacks:
            callback()
