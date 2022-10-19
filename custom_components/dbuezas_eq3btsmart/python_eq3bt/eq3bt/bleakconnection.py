"""
Bleak connection backend.
This creates a new event loop that is used to integrate bleak's
asyncio functions to synchronous architecture of python-eq3bt.
"""
import asyncio
import logging
import asyncio

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from homeassistant.components.esphome.bluetooth.characteristic import (
    BleakGATTCharacteristic,
)
from bleak_retry_connector import establish_connection
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth

from . import BackendException
import struct

REQUEST_TIMEOUT = 10
RETRIES = 10

# bleak backends are very loud on debug, this reduces the log spam when using --debug
# logging.getLogger("bleak.backends").setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)


class BleakConnection:
    """Representation of a BTLE Connection."""

    def __init__(
        self, mac: str, name: str, hass: HomeAssistant, notification_handle, callback
    ):
        """Initialize the connection."""
        self._mac = mac
        self._name = name
        self._hass = hass
        self._callback = callback
        self._notification_handle = notification_handle
        self._notifyevent = asyncio.Event()
        self._ble_device = None
        self.rssi = None
        self._lock = asyncio.Lock()

    def _on_disconnected(self, client: BleakClient) -> None:
        _LOGGER.debug("%s: Disconnected from device; rssi: %s", self._name, self.rssi)

    async def async_get_connection(self):
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._mac, connectable=True
        )
        if not ble_device:
            raise BackendException("Can't find device")
        self.rssi = ble_device.rssi
        _LOGGER.debug(
            "[%s] Connecting with ble_device, rssi: %s",
            self._name,
            ble_device.rssi,
        )
        conn = await establish_connection(
            BleakClient,
            ble_device,
            self._name,
            self._on_disconnected,
            MAX_ATTEMPTS=2,  # there is a retry loop on make_request
        )
        if conn.is_connected:
            _LOGGER.debug("[%s] connected", self._name)
        else:
            raise BackendException("Can't connect")
        return conn

    def set_ble_device(self, ble_device: BLEDevice):
        self._ble_device = ble_device

    async def on_notification(self, handle: BleakGATTCharacteristic, data: bytearray):
        """Handle Callback from a Bluetooth (GATT) request."""
        # The notification handles are off-by-one compared to gattlib and bluepy
        # service_handle = handle.handle + 1
        if handle.handle == self._notification_handle:
            self._notifyevent.set()
            self._callback(data)
        else:
            _LOGGER.error(
                "[%s] wrong charasteristic: %s",
                self._name,
                handle.handle,
            )

    async def async_make_request(self, handle: int, value):
        """Write a GATT Command without callback - not utf-8."""
        async with self._lock:  # only one concurrent request per thermostat
            i = 0
            while True:
                i += 1
                try:
                    conn = await self.async_get_connection()
                    self._notifyevent.clear()
                    await conn.start_notify(
                        self._notification_handle, self.on_notification
                    )
                    await conn.write_gatt_char(handle, value)
                    await asyncio.wait_for(self._notifyevent.wait(), REQUEST_TIMEOUT)
                    await conn.stop_notify(self._notification_handle)
                    return
                    # await conn.disconnect()
                except Exception as ex:
                    if i == RETRIES:
                        raise ex
                    await asyncio.sleep(1)
