"""
Bleak connection backend.
This creates a new event loop that is used to integrate bleak's
asyncio functions to synchronous architecture of python-eq3bt.
"""
import asyncio
import logging
import asyncio

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth

from . import BackendException
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
REQUEST_TIMEOUT = 1
RETRY_BACK_OFF = 1
RETRIES = 14

# Handles in linux and BTProxy are off by 1. Using UUIDs instead for consistency
PROP_WRITE_UUID = "3fa4585a-ce4a-3bad-db4b-b8df8179ea09"
PROP_NTFY_UUID = "d0e8434d-cd29-0996-af41-6c90f4e0eb2a"

# bleak backends are very loud on debug, this reduces the log spam when using --debug
# logging.getLogger("bleak.backends").setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)


class BleakConnection:
    """Representation of a BTLE Connection."""

    def __init__(
        self,
        mac: str,
        name: str,
        hass: HomeAssistant,
        callback,
    ):
        """Initialize the connection."""
        self._mac = mac
        self._name = name
        self._hass = hass
        self._callback = callback
        self._notify_event = asyncio.Event()
        self._terminate_event = asyncio.Event()
        self.rssi = None
        self._lock = asyncio.Lock()
        self._conn: BleakClient | None = None
        self._ble_device: BLEDevice | None = None
        self._connection_callbacks = []
        self.retries = 0

    def register_connection_callback(self, callback) -> None:
        self._connection_callbacks.append(callback)

    def _on_connection_event(self) -> None:
        for callback in self._connection_callbacks:
            callback()

    def shutdown(self):
        _LOGGER.debug(
            "[%s] closing connections",
            self._name,
        )
        self._terminate_event.set()
        self._notify_event.set()

    def throw_if_terminating(self):
        if self._terminate_event.is_set():
            raise Exception("Connection cancelled by shutdown")

    async def async_get_connection(self):
        self._ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._mac, connectable=True
        )
        if self._ble_device:
            self.rssi = self._ble_device.rssi

            _LOGGER.debug(
                "[%s] details: %s",
                self._name,
                self._ble_device.details,
            )
            _LOGGER.debug(
                "[%s] Connecting with ble_device, rssi: %s",
                self._name,
                self._ble_device.rssi,
            )
            self._on_connection_event()
            self._conn = await establish_connection(
                client_class=BleakClient,
                device=self._ble_device,
                name=self._name,
                disconnected_callback=lambda client: self._on_connection_event(),
                max_attempts=2,
                # cached_services: BleakGATTServiceCollection | None = None,
                # ble_device_callback:Callable[[], BLEDevice] | None = None,
                use_services_cache=True,
            )
            self._on_connection_event()

        else:
            _LOGGER.debug(
                "[%s]NO ble_device found",
                self._name,
            )
            raise Exception("Device not found")

        if self._conn.is_connected:
            _LOGGER.debug("[%s] Connected", self._name)
            try:
                # TODO: verify that this
                paired = await self._conn.pair(
                    1  # 1 = pairing with no protection https://bleak.readthedocs.io/en/latest/backends/windows.html?highlight=pair#bleak.backends.winrt.client.BleakClientWinRT.pair
                )
                _LOGGER.debug("[%s] Paired: %s ", self._name, paired)
            except Exception as ex:
                _LOGGER.warn("[%s] Failed paring: %s ", self._name, ex)
        else:
            raise BackendException("Can't connect")
        return self._conn

    async def on_notification(self, handle: BleakGATTCharacteristic, data: bytearray):
        """Handle Callback from a Bluetooth (GATT) request."""
        if PROP_NTFY_UUID == handle.uuid:
            self._notify_event.set()
            self._callback(data)
        else:
            _LOGGER.error(
                "[%s] wrong charasteristic: %s, %s",
                self._name,
                handle.handle,
                handle.uuid,
            )

    async def async_make_request(self, value, retries=RETRIES):
        """Write a GATT Command without callback - not utf-8."""
        async with self._lock:  # only one concurrent request per thermostat
            try:
                await self._async_make_request_try(value, retries)
            finally:
                self.retries = 0
                self._on_connection_event()

    async def _async_make_request_try(self, value, retries):
        self.retries = 0
        while True:
            self.retries += 1
            self._on_connection_event()
            try:
                self.throw_if_terminating()
                conn = await self.async_get_connection()
                self._notify_event.clear()
                if value != "ONLY CONNECT":
                    await conn.start_notify(PROP_NTFY_UUID, self.on_notification)
                    await conn.write_gatt_char(PROP_WRITE_UUID, value)
                    await asyncio.wait_for(self._notify_event.wait(), REQUEST_TIMEOUT)
                    self.throw_if_terminating()
                    await conn.stop_notify(PROP_NTFY_UUID)
                return
            except Exception as ex:
                self.throw_if_terminating()
                _LOGGER.warning(
                    "[%s] Broken connection [retry %s/%s]: %s",
                    self._name,
                    self.retries,
                    retries,
                    ex,
                )
                if self.retries >= retries:
                    raise ex
                await asyncio.sleep(RETRY_BACK_OFF)
