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
from typing import Any, Callable

from construct import Byte, Container
from homeassistant.core import HomeAssistant

from eq3btsmart.bleakconnection import BleakConnection
from eq3btsmart.const import (
    DEFAULT_AWAY_HOURS,
    DEFAULT_AWAY_TEMP,
    EQ3BT_MAX_OFFSET,
    EQ3BT_MAX_TEMP,
    EQ3BT_MIN_OFFSET,
    EQ3BT_MIN_TEMP,
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
    PROP_BOOST,
    PROP_COMFORT,
    PROP_COMFORT_ECO_CONFIG,
    PROP_ECO,
    PROP_ID_QUERY,
    PROP_ID_RETURN,
    PROP_INFO_QUERY,
    PROP_INFO_RETURN,
    PROP_LOCK,
    PROP_MODE_WRITE,
    PROP_OFFSET,
    PROP_SCHEDULE_QUERY,
    PROP_SCHEDULE_RETURN,
    PROP_TEMPERATURE_WRITE,
    PROP_WINDOW_OPEN_CONFIG,
    Mode,
)
from eq3btsmart.exceptions import TemperatureException
from eq3btsmart.structures import AwayDataAdapter, DeviceId, Schedule, Status

_LOGGER = logging.getLogger(__name__)


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
        self._status: Container[Any] | None = None
        self._presets: Container[Any] | None = None
        self._device_data: Container[Any] | None = None
        self._schedule: dict[str, Container[Any]] = {}
        self.default_away_hours: float = DEFAULT_AWAY_HOURS
        self.default_away_temp: float = DEFAULT_AWAY_TEMP
        self._on_update_callbacks: list[Callable] = []
        self._conn = BleakConnection(
            mac=mac,
            name=name,
            adapter=adapter,
            stay_connected=stay_connected,
            hass=hass,
            callback=self.handle_notification,
        )

    def register_update_callback(self, on_update: Callable) -> None:
        self._on_update_callbacks.append(on_update)

    def shutdown(self) -> None:
        self._conn.shutdown()

    def _verify_temperature(self, temp: float) -> None:
        """Verifies that the temperature is valid.
        :raises TemperatureException: On invalid temperature.
        """
        if temp < EQ3BT_MIN_TEMP or temp > EQ3BT_MAX_TEMP:
            raise TemperatureException(
                "Temperature {} out of range [{}, {}]".format(
                    temp, EQ3BT_MIN_TEMP, EQ3BT_MAX_TEMP
                )
            )

    def parse_schedule(self, data) -> Container[Any]:
        """Parses the device sent schedule."""
        sched = Schedule.parse(data)
        if sched is None:
            raise Exception("Parsed empty schedule data")
        _LOGGER.debug("[%s] Got schedule data for day '%s'", self.name, sched.day)

        return sched

    def handle_notification(self, data: bytearray) -> None:
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("[%s] Received notification from the device.", self.name)
        updated = True
        if data[0] == PROP_INFO_RETURN and data[1] == 1:
            _LOGGER.debug("[%s] Got status: %s", self.name, codecs.encode(data, "hex"))
            self._status = Status.parse(data)

            if self._status is None:
                raise Exception("Parsed empty status data")

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

    async def async_query_id(self) -> None:
        """Query device identification information, e.g. the serial number."""
        _LOGGER.debug("[%s] Querying id..", self.name)
        value = struct.pack("B", PROP_ID_QUERY)
        await self._conn.async_make_request(value)
        _LOGGER.debug("[%s] Finished Querying id..", self.name)

    async def async_update(self) -> None:
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

    async def async_query_schedule(self, day: int) -> None:
        _LOGGER.debug("[%s] Querying schedule..", self.name)

        if day < 0 or day > 6:
            _LOGGER.error("[%s] Invalid day: %s", self.name, day)

        value = struct.pack("BB", PROP_SCHEDULE_QUERY, day)

        await self._conn.async_make_request(value)

    @property
    def schedule(self) -> dict[str, Container[Any]]:
        """Returns previously fetched schedule.
        :return: Schedule structure or None if not fetched.
        """
        return self._schedule

    async def async_set_schedule(self, day, hours) -> None:
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
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._status.target_temp if self._status else -1

    async def async_set_target_temperature(self, temperature: float) -> None:
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
    def mode(self) -> Mode:
        """Return the current operation mode"""
        if self._status is None:
            return Mode.Unknown
        if self.target_temperature == EQ3BT_OFF_TEMP:
            return Mode.Off
        if self.target_temperature == EQ3BT_ON_TEMP:
            return Mode.On
        if self._status.mode.MANUAL:
            return Mode.Manual
        return Mode.Auto

    async def async_set_mode(self, mode: Mode) -> None:
        """Set the operation mode."""
        _LOGGER.debug("[%s] Setting new mode: %s", self.name, mode)

        match mode:
            case Mode.Off:
                await self.async_set_target_temperature(EQ3BT_OFF_TEMP)
            case Mode.On:
                await self.async_set_target_temperature(EQ3BT_ON_TEMP)
            case Mode.Auto:
                await self._async_set_mode(0)
            case Mode.Manual:
                temperature = max(
                    min(self.target_temperature, EQ3BT_MAX_TEMP), EQ3BT_MIN_TEMP
                )
                await self._async_set_mode(0x40 | int(temperature * 2))

    @property
    def away(self) -> bool | None:
        """Returns True if the thermostat is in away mode."""

        if self._status is None:
            return None

        return self.away_end is not None

    @property
    def away_end(self) -> datetime | None:
        """Returns the end datetime of the away mode."""
        if self._status is None:
            return None

        if not isinstance(self._status.away, datetime):
            return None

        return self._status.away

    async def async_set_away_until(
        self, away_end: datetime, temperature: float
    ) -> None:
        """Sets away mode with default temperature."""

        # rounding
        away_end = away_end + timedelta(minutes=15)
        away_end = away_end - timedelta(minutes=away_end.minute % 30)

        _LOGGER.debug(
            "[%s] Setting away until %s, temp %s", self.name, away_end, temperature
        )
        adapter = AwayDataAdapter(Byte[4])
        packed = adapter.build(away_end)

        await self._async_set_mode(0x80 | int(temperature * 2), packed)

    async def async_set_away(self, away: bool) -> None:
        """Sets away mode with default temperature."""
        if not away:
            _LOGGER.debug("[%s] Disabling away, going to auto mode.", self.name)
            return await self._async_set_mode(0x00)

        away_end = datetime.now() + timedelta(hours=self.default_away_hours)

        await self.async_set_away_until(away_end, self.default_away_temp)

    async def _async_set_mode(self, mode: int, payload: bytes | None = None) -> None:
        value = struct.pack("BB", PROP_MODE_WRITE, mode)
        if payload:
            value += payload
        await self._conn.async_make_request(value)

    @property
    def boost(self) -> bool | None:
        """Returns True if the thermostat is in boost mode."""

        if self._status is None:
            return None

        return self._status.mode.BOOST

    async def async_set_boost(self, boost: bool) -> None:
        """Sets boost mode."""
        _LOGGER.debug("[%s] Setting boost mode: %s", self.name, boost)
        value = struct.pack("BB", PROP_BOOST, boost)
        await self._conn.async_make_request(value)

    @property
    def valve_state(self) -> int | None:
        """Returns the valve state. Probably reported as percent open."""

        if self._status is None:
            return None

        return self._status.valve

    @property
    def window_open(self) -> bool | None:
        """Returns True if the thermostat reports a open window
        (detected by sudden drop of temperature)"""

        if self._status is None:
            return False

        return self._status.mode.WINDOW

    async def async_window_open_config(
        self, temperature: float, duration: timedelta
    ) -> None:
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
    def window_open_temperature(self) -> float | None:
        """The temperature to set when an open window is detected."""

        if self._presets is None:
            return None

        return self._presets.window_open_temp

    @property
    def window_open_time(self) -> timedelta | None:
        """Timeout to reset the thermostat after an open window is detected."""

        if self._presets is None:
            return None

        return self._presets.window_open_time

    @property
    def dst(self) -> bool | None:
        """Returns True if the thermostat is in Daylight Saving Time."""

        if self._status is None:
            return None

        return self._status.mode.DST

    @property
    def locked(self) -> bool | None:
        """Returns True if the thermostat is locked."""

        if self._status is None:
            return None

        return self._status.mode.LOCKED

    async def async_set_locked(self, lock: bool) -> None:
        """Locks or unlocks the thermostat."""
        _LOGGER.debug("[%s] Setting the lock: %s", self.name, lock)
        value = struct.pack("BB", PROP_LOCK, lock)
        await self._conn.async_make_request(value)

    @property
    def low_battery(self) -> bool | None:
        """Returns True if the thermostat reports a low battery."""

        if self._status is None:
            return None

        return self._status.mode.LOW_BATTERY

    async def async_temperature_presets(self, comfort: float, eco: float) -> None:
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
    def comfort_temperature(self) -> float | None:
        """Returns the comfort temperature preset of the thermostat."""

        if self._presets is None:
            return None

        return self._presets.comfort_temp

    @property
    def eco_temperature(self) -> float | None:
        """Returns the eco temperature preset of the thermostat."""

        if self._presets is None:
            return None

        return self._presets.eco_temp

    @property
    def temperature_offset(self) -> float | None:
        """Returns the thermostat's temperature offset."""

        if self._presets is None:
            return None

        return self._presets.offset

    async def async_set_temperature_offset(self, offset: float) -> None:
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

    async def async_activate_comfort(self) -> None:
        """Activates the comfort temperature."""
        value = struct.pack("B", PROP_COMFORT)
        await self._conn.async_make_request(value)

    async def async_activate_eco(self) -> None:
        """Activates the comfort temperature."""
        value = struct.pack("B", PROP_ECO)
        await self._conn.async_make_request(value)

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version."""

        if self._device_data is None:
            return None

        return self._device_data.version

    @property
    def device_serial(self) -> str | None:
        """Return the device serial number."""

        if self._device_data is None:
            return None

        return self._device_data.serial

    @property
    def mac(self) -> str:
        """Return the mac address."""

        return self._conn._mac
