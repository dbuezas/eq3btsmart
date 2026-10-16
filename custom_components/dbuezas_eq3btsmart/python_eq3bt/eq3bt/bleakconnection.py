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
from homeassistant.core import HomeAssistant, callback

from . import BackendException
from typing import TYPE_CHECKING, cast

from bleak.backends.device import BLEDevice

REQUEST_TIMEOUT = 5
RETRY_BACK_OFF_FACTOR = 0.25
RETRIES = 14
# TEST (eq3-firmware-mod HA205): with "stay connected" off, keep the link this many seconds after the
# last request, then disconnect -- so a burst of changes shares one connect, and an idle thermostat
# holds no link (a held link halves the advert rate a scanner receives, FINDINGS.md).
IDLE_DISCONNECT = 10

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
        self._idle_handle = None  # TEST HA205: pending idle disconnect

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
        # TEST HA205: an idle link was left open on unload/reload, holding the thermostat.
        self._cancel_idle()
        if self._conn is not None and self._conn.is_connected:
            self._hass.async_create_task(self._conn.disconnect())

    def _cancel_idle(self):
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None

    def _arm_idle(self):
        self._cancel_idle()
        self._idle_handle = self._hass.loop.call_later(
            IDLE_DISCONNECT, lambda: self._hass.async_create_task(self._async_idle_disconnect())
        )

    async def _async_idle_disconnect(self):
        async with self._lock:  # never in the middle of a request
            self._idle_handle = None
            if self._conn is not None and self._conn.is_connected:
                _LOGGER.debug("[%s] idle %s s, disconnecting", self._name, IDLE_DISCONNECT)
                self._notify_conn = None
                await self._conn.disconnect()

    async def throw_if_terminating(self):
        if self._terminate_event.is_set():
            if self._conn:
                await self._conn.disconnect()
            raise Exception("Connection cancelled by shutdown")

    async def async_get_connection(self):
        # TEST (eq3-firmware-mod HA191): reuse the open link; connecting again forces
        # habluetooth's fast connection preset on every poll.
        if self._conn is not None and self._conn.is_connected:
            return self._conn
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
            device_advertisement_datas = sorted(
                bluetooth.async_scanner_devices_by_address(
                    hass=self._hass,
                    address=self._mac,
                    connectable=True
                ),
                key=lambda device_advertisement_data: device_advertisement_data.advertisement.rssi
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
                    if (d := x.ble_device.details)
                    and d.get("props", {}).get("Adapter") == self._adapter
                ]
                if len(list) == 0:
                    raise Exception("Device not found")
                d_and_a = list[0]
            self.rssi = d_and_a.advertisement.rssi
            self._ble_device = d_and_a.ble_device
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
        """Write a GATT Command with callback - not utf-8."""
        async with self._lock:  # only one concurrent request per thermostat
            self._cancel_idle()
            try:
                await self._async_make_request_try(value, retries)
            finally:
                self.retries = 0
                if not self._stay_connected and not self._terminate_event.is_set():
                    self._arm_idle()  # TEST HA205: disconnect after IDLE_DISCONNECT s of quiet
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
                    if getattr(self, '_notify_conn', None) is not conn:   # TEST HA191: once per link
                        await conn.start_notify(PROP_NTFY_UUID, self.on_notification)
                        self._notify_conn = conn
                    await conn.write_gatt_char(PROP_WRITE_UUID, value, response=True)
                    await asyncio.wait_for(
                        self._notify_event.wait(), REQUEST_TIMEOUT
                    )
                    # TEST HA205: no disconnect here any more -- async_make_request arms the idle timer
                return
            except Exception as ex:
                await self.throw_if_terminating()
                # TEST HA205: a failed request must not leave a half-working link that the next try
                # (and every later poll) would reuse; drop it so the retry connects afresh.
                if self._conn is not None and self._conn.is_connected:
                    self._notify_conn = None
                    try:
                        await self._conn.disconnect()
                    except Exception:  # noqa: BLE001
                        pass
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
                await asyncio.sleep(RETRY_BACK_OFF_FACTOR * self.retries)
