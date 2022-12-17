"""
Support for eq3 Bluetooth Smart thermostats.

All temperatures in Celsius.

To get the current state, update() has to be called for powersaving reasons.
Schedule needs to be requested with query_schedule() before accessing for similar reasons.
"""

import codecs
import logging
import struct
from datetime import datetime, timedelta
from enum import IntEnum

from construct import Byte

from homeassistant.core import HomeAssistant
from .structures import AwayDataAdapter, DeviceId, ModeFlags, Schedule, Status

_LOGGER = logging.getLogger(__name__)

PROP_ID_QUERY = 0
PROP_ID_RETURN = 1
PROP_INFO_QUERY = 3
PROP_INFO_RETURN = 2
PROP_COMFORT_ECO_CONFIG = 0x11
PROP_OFFSET = 0x13
PROP_WINDOW_OPEN_CONFIG = 0x14
PROP_SCHEDULE_QUERY = 0x20
PROP_SCHEDULE_RETURN = 0x21

PROP_MODE_WRITE = 0x40
PROP_TEMPERATURE_WRITE = 0x41
PROP_COMFORT = 0x43
PROP_ECO = 0x44
PROP_BOOST = 0x45
PROP_LOCK = 0x80

EQ3BT_AWAY_TEMP = 12.0
EQ3BT_MIN_TEMP = 5.0
EQ3BT_MAX_TEMP = 29.5
EQ3BT_OFF_TEMP = 4.5
EQ3BT_ON_TEMP = 30.0
EQ3BT_MIN_OFFSET = -3.5
EQ3BT_MAX_OFFSET = 3.5


class Mode(IntEnum):
    """Thermostat modes."""

    Unknown = 0
    Off = 0
    On = 1
    Auto = 2
    Manual = 3


class TemperatureException(Exception):
    """Temperature out of range error."""

    pass


# pylint: disable=too-many-instance-attributes
class Thermostat:
    """Representation of a EQ3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        mac: str,
        name: str,
        adapter: str,
        stay_connected: bool,
        hass: HomeAssistant,
    ):
        """Initialize the thermostat."""

        self.name = name
        self._status = None
        self._presets = None
        self._device_data = None
        self._schedule = {}
        self.default_away_days: float = 30
        self.default_away_temp: float = 12

        from .bleakconnection import BleakConnection

        self._on_update_callbacks = []
        self._conn = BleakConnection(
            mac=mac,
            name=name,
            adapter=adapter,
            stay_connected=stay_connected,
            hass=hass,
            callback=self.handle_notification,
        )

    def register_update_callback(self, on_update):
        self._on_update_callbacks.append(on_update)

    def shutdown(self):
        self._conn.shutdown()

    def _verify_temperature(self, temp):
        """Verifies that the temperature is valid.
        :raises TemperatureException: On invalid temperature.
        """
        if temp < EQ3BT_MIN_TEMP or temp > EQ3BT_MAX_TEMP:
            raise TemperatureException(
                "Temperature {} out of range [{}, {}]".format(
                    temp, EQ3BT_MIN_TEMP, EQ3BT_MAX_TEMP
                )
            )

    def parse_schedule(self, data):
        """Parses the device sent schedule."""
        sched = Schedule.parse(data)
        if sched == None:
            raise Exception("Parsed empty schedule data")
        _LOGGER.debug("[%s] Got schedule data for day '%s'", self.name, sched.day)

        return sched

    def handle_notification(self, data: bytearray):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("[%s] Received notification from the device.", self.name)
        updated = True
        if data[0] == PROP_INFO_RETURN and data[1] == 1:
            _LOGGER.debug("[%s] Got status: %s", self.name, codecs.encode(data, "hex"))
            self._status = Status.parse(data)
            assert self._status
            self._presets = self._status.presets
            _LOGGER.debug("[%s] Parsed status: %s", self.name, self._status)

        elif data[0] == PROP_SCHEDULE_RETURN:
            parsed = self.parse_schedule(data)
            self._schedule[parsed.day] = parsed

        elif data[0] == PROP_ID_RETURN:
            self._device_data = DeviceId.parse(data)
            _LOGGER.debug("[%s] Parsed device data: %s", self.name, self._device_data)

        else:
            updated = False
            _LOGGER.debug(
                "[%s] Unknown notification %s (%s)",
                self.name,
                data[0],
                codecs.encode(data, "hex"),
            )
        if updated:
            for callback in self._on_update_callbacks:
                callback()

    async def async_query_id(self):
        """Query device identification information, e.g. the serial number."""
        _LOGGER.debug("[%s] Querying id..", self.name)
        value = struct.pack("B", PROP_ID_QUERY)
        await self._conn.async_make_request(value)
        _LOGGER.debug("[%s] Finished Querying id..", self.name)

    async def async_update(self):
        """Update the data from the thermostat. Always sets the current time."""
        _LOGGER.debug("[%s] Querying the device..", self.name)
        time = datetime.now()
        value = struct.pack(
            "BBBBBBB",
            PROP_INFO_QUERY,
            time.year % 100,
            time.month,
            time.day,
            time.hour,
            time.minute,
            time.second,
        )

        await self._conn.async_make_request(value)

    async def async_query_schedule(self, day):
        _LOGGER.debug("[%s] Querying schedule..", self.name)

        if day < 0 or day > 6:
            _LOGGER.error("[%s] Invalid day: %s", self.name, day)

        value = struct.pack("BB", PROP_SCHEDULE_QUERY, day)

        await self._conn.async_make_request(value)

    @property
    def schedule(self):
        """Returns previously fetched schedule.
        :return: Schedule structure or None if not fetched.
        """
        return self._schedule

    async def async_set_schedule(self, day, hours):
        _LOGGER.debug(
            "[%s] Setting schedule day=[%s], hours=[%s]", self.name, day, hours
        )

        """Sets the schedule for the given day."""
        data = Schedule.build(
            {
                "cmd": "write",
                "day": day,
                "hours": hours,
            }
        )
        await self._conn.async_make_request(data)

        parsed = self.parse_schedule(data)
        self._schedule[parsed.day] = parsed
        for callback in self._on_update_callbacks:
            callback()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._status.target_temp if self._status else -1

    async def async_set_target_temperature(self, temperature):
        """Set new target temperature."""
        dev_temp = int(temperature * 2)
        if temperature == EQ3BT_OFF_TEMP or temperature == EQ3BT_ON_TEMP:
            dev_temp |= 0x40
            value = struct.pack("BB", PROP_MODE_WRITE, dev_temp)
        else:
            self._verify_temperature(temperature)
            value = struct.pack("BB", PROP_TEMPERATURE_WRITE, dev_temp)

        await self._conn.async_make_request(value)

    @property
    def mode(self):
        """Return the current operation mode"""
        if self._status == None:
            return Mode.Unknown
        if self.target_temperature == EQ3BT_OFF_TEMP:
            return Mode.Off
        if self.target_temperature == EQ3BT_ON_TEMP:
            return Mode.On
        if self._status.mode.MANUAL:
            return Mode.Manual
        return Mode.Auto

    async def async_set_mode(self, mode):
        """Set the operation mode."""
        _LOGGER.debug("[%s] Setting new mode: %s", self.name, mode)

        if mode == Mode.Off:
            return await self.async_set_target_temperature(EQ3BT_OFF_TEMP)
        if mode == Mode.On:
            return await self.async_set_target_temperature(EQ3BT_ON_TEMP)
        if mode == Mode.Auto:
            return await self._async_set_mode(0)
        if mode == Mode.Manual:
            temperature = max(
                min(self.target_temperature, EQ3BT_MAX_TEMP), EQ3BT_MIN_TEMP
            )
            return await self._async_set_mode(0x40 | int(temperature * 2))

    @property
    def away(self) -> bool | None:
        """Returns True if the thermostat is in boost mode."""
        return self._status and self._status.mode.AWAY  # type: ignore

    @property
    def away_end(self) -> datetime | None:
        return self._status and self._status.away  # type: ignore

    async def async_set_away(self, away: bool):
        """Sets away mode with default temperature."""
        if not away:
            _LOGGER.debug("[%s] Disabling away, going to auto mode.", self.name)
            return await self._async_set_mode(0x00)

        away_end = datetime.now() + timedelta(days=self.default_away_days)
        temperature = self.default_away_temp
        _LOGGER.debug(
            "[%s] Setting away until %s, temp %s", self.name, away_end, temperature
        )
        adapter = AwayDataAdapter(Byte[4])  # type: ignore
        packed = adapter.build(away_end)

        await self._async_set_mode(0x80 | int(temperature * 2), packed)

    async def _async_set_mode(self, mode, payload=None):
        value = struct.pack("BB", PROP_MODE_WRITE, mode)
        if payload:
            value += payload
        await self._conn.async_make_request(value)

    @property
    def boost(self) -> bool | None:
        """Returns True if the thermostat is in boost mode."""
        return self._status and self._status.mode.BOOST  # type: ignore

    async def async_set_boost(self, boost):
        """Sets boost mode."""
        _LOGGER.debug("[%s] Setting boost mode: %s", self.name, boost)
        value = struct.pack("BB", PROP_BOOST, bool(boost))
        await self._conn.async_make_request(value)

    @property
    def valve_state(self) -> int | None:
        """Returns the valve state. Probably reported as percent open."""
        return self._status and self._status.valve  # type: ignore

    @property
    def window_open(self) -> bool | None:
        """Returns True if the thermostat reports a open window
        (detected by sudden drop of temperature)"""
        return self._status and self._status.mode.WINDOW  # type: ignore

    async def async_window_open_config(self, temperature, duration):
        """Configures the window open behavior. The duration is specified in
        5 minute increments."""
        _LOGGER.debug(
            "[%s] Window open config, temperature: %s duration: %s",
            self.name,
            temperature,
            duration,
        )
        self._verify_temperature(temperature)
        if duration.seconds < 0 and duration.seconds > 3600:
            raise ValueError

        value = struct.pack(
            "BBB",
            PROP_WINDOW_OPEN_CONFIG,
            int(temperature * 2),
            int(duration.seconds / 300),
        )
        await self._conn.async_make_request(value)

    @property
    def window_open_temperature(self):
        """The temperature to set when an open window is detected."""
        return self._presets and self._presets.window_open_temp

    @property
    def window_open_time(self) -> timedelta | None:
        """Timeout to reset the thermostat after an open window is detected."""
        return self._presets and self._presets.window_open_time  # type: ignore

    @property
    def dst(self) -> bool | None:
        """Returns True if the thermostat is in Daylight Saving Time."""
        return self._status and self._status.mode.DST  # type: ignore

    @property
    def locked(self) -> bool | None:
        """Returns True if the thermostat is locked."""
        return self._status and self._status.mode.LOCKED  # type: ignore

    async def async_set_locked(self, lock):
        """Locks or unlocks the thermostat."""
        _LOGGER.debug("[%s] Setting the lock: %s", self.name, lock)
        value = struct.pack("BB", PROP_LOCK, bool(lock))
        await self._conn.async_make_request(value)

    @property
    def low_battery(self) -> bool | None:
        """Returns True if the thermostat reports a low battery."""
        return self._status and self._status.mode.LOW_BATTERY  # type: ignore

    async def async_temperature_presets(self, comfort, eco):
        """Set the thermostats preset temperatures comfort (sun) and
        eco (moon)."""
        _LOGGER.debug(
            "[%s] Setting temperature presets, comfort: %s eco: %s",
            self.name,
            comfort,
            eco,
        )
        self._verify_temperature(comfort)
        self._verify_temperature(eco)
        value = struct.pack(
            "BBB", PROP_COMFORT_ECO_CONFIG, int(comfort * 2), int(eco * 2)
        )
        await self._conn.async_make_request(value)

    @property
    def comfort_temperature(self):
        """Returns the comfort temperature preset of the thermostat."""
        return self._presets and self._presets.comfort_temp

    @property
    def eco_temperature(self):
        """Returns the eco temperature preset of the thermostat."""
        return self._presets and self._presets.eco_temp

    @property
    def temperature_offset(self):
        """Returns the thermostat's temperature offset."""
        return self._presets and self._presets.offset

    async def async_set_temperature_offset(self, offset):
        """Sets the thermostat's temperature offset."""
        _LOGGER.debug("[%s] Setting offset: %s", self.name, offset)
        # [-3,5 .. 0  .. 3,5 ]
        # [00   .. 07 .. 0e ]
        if offset < EQ3BT_MIN_OFFSET or offset > EQ3BT_MAX_OFFSET:
            raise TemperatureException("Invalid value: %s" % offset)

        current = -3.5
        values = {}
        for i in range(15):
            values[current] = i
            current += 0.5

        value = struct.pack("BB", PROP_OFFSET, values[offset])
        await self._conn.async_make_request(value)

    async def async_activate_comfort(self):
        """Activates the comfort temperature."""
        value = struct.pack("B", PROP_COMFORT)
        await self._conn.async_make_request(value)

    async def async_activate_eco(self):
        """Activates the comfort temperature."""
        value = struct.pack("B", PROP_ECO)
        await self._conn.async_make_request(value)

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version."""
        return self._device_data and self._device_data.version  # type: ignore

    @property
    def device_serial(self) -> str | None:
        """Return the device serial number."""
        return self._device_data and self._device_data.serial  # type: ignore

    @property
    def mac(self):
        """Return the mac address."""
        return self._conn._mac
