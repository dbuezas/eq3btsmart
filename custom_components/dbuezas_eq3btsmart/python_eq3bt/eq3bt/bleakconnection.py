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
from bleak_retry_connector import NO_RSSI_VALUE, establish_connection
from ...const import Adapter
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.const import DATA_MANAGER
from homeassistant.components.bluetooth.manager import BluetoothManager
from homeassistant.core import HomeAssistant, callback

from . import BackendException
from typing import TYPE_CHECKING, cast

from bleak.backends.device import BLEDevice

REQUEST_TIMEOUT = 1
RETRY_BACK_OFF = 0.25
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
        adapter: str,
        stay_connected: bool,
        hass: HomeAssistant,
        callback,
    ):
        """Initialize the connection."""
        self._mac = mac
        self._name = name
        self._adapter = adapter
        self._stay_connected = stay_connected
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
        self._round_robin = 0

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

    async def throw_if_terminating(self):
        if self._terminate_event.is_set():
            if self._conn:
                await self._conn.disconnect()
            raise Exception("Connection cancelled by shutdown")

    async def async_get_connection(self):
        if self._adapter == Adapter.AUTO:
            self._ble_device = bluetooth.async_ble_device_from_address(
                self._hass, self._mac, connectable=True
            )
            if self._ble_device == None:
                raise Exception("Device not found")

            self._conn = await establish_connection(
                client_class=BleakClient,
                device=self._ble_device,
                name=self._name,
                disconnected_callback=lambda client: self._on_connection_event(),
                max_attempts=2,
                use_services_cache=True,
            )
        else:
            MANAGER = cast(BluetoothManager, self._hass.data[DATA_MANAGER])

            device_advertisement_datas = sorted(
                MANAGER.async_get_scanner_discovered_devices_and_advertisement_data_by_address(
                    address=self._mac, connectable=True
                ),
                key=lambda device_advertisement_data: device_advertisement_data[1].rssi
                or NO_RSSI_VALUE,
                reverse=True,
            )
            if self._adapter == Adapter.LOCAL:
                if len(device_advertisement_datas) == 0:
                    raise Exception("Device not found")
                d_and_a = device_advertisement_datas[
                    self._round_robin % len(device_advertisement_datas)
                ]
            else:  # adapter is e.g /org/bluez/hci0
                list = [
                    x
                    for x in device_advertisement_datas
                    if (d := x[1].details)
                    and d.get("props", {}).get("Adapter") == self._adapter
                ]
                if len(list) == 0:
                    raise Exception("Device not found")
                d_and_a = list[0]
            self.rssi = d_and_a[2].rssi
            self._ble_device = d_and_a[1]
            UnwrappedBleakClient = cast(type[BleakClient], BleakClient.__bases__[0])
            self._conn = UnwrappedBleakClient(
                self._ble_device,
                disconnected_callback=lambda client: self._on_connection_event(),
                dangerous_use_bleak_cache=True,
            )
            await self._conn.connect()

        self._on_connection_event()

        if self._conn.is_connected:
            _LOGGER.debug("[%s] Connected", self._name)
            try:
                # only works with old firmwares w/o pairing pin.
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
                await self.throw_if_terminating()
                conn = await self.async_get_connection()
                self._notify_event.clear()
                if value != "ONLY CONNECT":
                    await conn.start_notify(PROP_NTFY_UUID, self.on_notification)
                    try:
                        await conn.write_gatt_char(PROP_WRITE_UUID, value)
                        await asyncio.wait_for(
                            self._notify_event.wait(), REQUEST_TIMEOUT
                        )
                    finally:
                        await conn.stop_notify(PROP_NTFY_UUID)
                    if not self._stay_connected:
                        await conn.disconnect()

                return
            except Exception as ex:
                await self.throw_if_terminating()
                _LOGGER.debug(
                    "[%s] Broken connection [retry %s/%s]: %s",
                    self._name,
                    self.retries,
                    retries,
                    ex,
                    exc_info=True,
                )
                self._round_robin = self._round_robin + 1
                if self.retries >= retries:
                    raise ex
                await asyncio.sleep(RETRY_BACK_OFF)
