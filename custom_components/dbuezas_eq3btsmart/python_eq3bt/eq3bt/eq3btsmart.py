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
from .structures import AwayDataAdapter, DeviceId, Schedule, Status

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

    Unknown = -1
    Closed = 0
    Open = 1
    Auto = 2
    Manual = 3
    Away = 4
    Boost = 5


class TemperatureException(Exception):
    """Temperature out of range error."""

    pass


# pylint: disable=too-many-instance-attributes
class Thermostat:
    """Representation of a EQ3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        _mac: str,
        name: str,
        _hass: HomeAssistant,
    ):
        """Initialize the thermostat."""

        self._target_temperature = Mode.Unknown
        self.name = name
        self._mode = Mode.Unknown
        self._valve_state = None
        self._raw_mode = None

        self._schedule = {}

        self._window_open_temperature = None
        self._window_open_time = None
        self._comfort_temperature = None
        self._eco_temperature = None
        self._temperature_offset = None

        self._away_temp = EQ3BT_AWAY_TEMP
        self._away_duration = timedelta(days=30)
        self._away_end = None

        self._firmware_version = None
        self._device_serial = None
        from .bleakconnection import BleakConnection

        self._on_update_callbacks = []
        self._conn = BleakConnection(_mac, name, _hass, self.handle_notification)

    def register_update_callback(self, on_update):
        self._on_update_callbacks.append(on_update)

    def shutdown(self):
        self._conn.shutdown()

    def __str__(self):
        away_end = "no"
        if self.away_end:
            away_end = "end: %s" % self._away_end

        return "[{}] Target {} (mode: {}, away: {})".format(
            self.name, self.target_temperature, self.mode_readable, away_end
        )

    def _verify_temperature(self, temp):
        """Verifies that the temperature is valid.
        :raises TemperatureException: On invalid temperature.
        """
        if temp < self.min_temp or temp > self.max_temp:
            raise TemperatureException(
                "Temperature {} out of range [{}, {}]".format(
                    temp, self.min_temp, self.max_temp
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

        if data[0] == PROP_INFO_RETURN and data[1] == 1:
            _LOGGER.debug("[%s] Got status: %s", self.name, codecs.encode(data, "hex"))
            status = Status.parse(data)
            _LOGGER.debug("[%s] Parsed status: %s", self.name, status)
            if status == None:
                raise Exception("Received empty status data")
            self._raw_mode = status.mode
            self._valve_state = status.valve
            self._target_temperature = status.target_temp

            if status.mode.BOOST:
                self._mode = Mode.Boost
            elif status.mode.AWAY:
                self._mode = Mode.Away
                self._away_end = status.away
            elif status.mode.MANUAL:
                if status.target_temp == EQ3BT_OFF_TEMP:
                    self._mode = Mode.Closed
                elif status.target_temp == EQ3BT_ON_TEMP:
                    self._mode = Mode.Open
                else:
                    self._mode = Mode.Manual
            else:
                self._mode = Mode.Auto

            presets = status.presets
            if presets:
                self._window_open_temperature = presets.window_open_temp
                self._window_open_time = presets.window_open_time
                self._comfort_temperature = presets.comfort_temp
                self._eco_temperature = presets.eco_temp
                self._temperature_offset = presets.offset
            else:
                self._window_open_temperature = None
                self._window_open_time = None
                self._comfort_temperature = None
                self._eco_temperature = None
                self._temperature_offset = None

            _LOGGER.debug("[%s] Valve state:      %s", self.name, self._valve_state)
            _LOGGER.debug("[%s] Mode:             %s", self.name, self.mode_readable)
            _LOGGER.debug(
                "[%s] Target temp:      %s", self.name, self._target_temperature
            )
            _LOGGER.debug("[%s] Away end:         %s", self.name, self._away_end)
            _LOGGER.debug(
                "[%s] Window open temp: %s", self.name, self._window_open_temperature
            )
            _LOGGER.debug(
                "[%s] Window open time: %s", self.name, self._window_open_time
            )
            _LOGGER.debug(
                "[%s] Comfort temp:     %s", self.name, self._comfort_temperature
            )
            _LOGGER.debug("[%s] Eco temp:         %s", self.name, self._eco_temperature)
            _LOGGER.debug(
                "[%s] Temp offset:      %s", self.name, self._temperature_offset
            )

        elif data[0] == PROP_SCHEDULE_RETURN:
            parsed = self.parse_schedule(data)
            self._schedule[parsed.day] = parsed

        elif data[0] == PROP_ID_RETURN:
            parsed = DeviceId.parse(data)
            _LOGGER.debug("[%s] Parsed device data: %s", self.name, parsed)
            if parsed is None:
                raise Exception("Parsed empty DeviceID data")
            self._firmware_version = parsed.version
            self._device_serial = parsed.serial

        else:
            _LOGGER.debug(
                "[%s] Unknown notification %s (%s)",
                self.name,
                data[0],
                codecs.encode(data, "hex"),
            )
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

    async def async_set_schedule(self, data):
        """Sets the schedule for the given day."""
        value = Schedule.build(data)
        await self._conn.async_make_request(value)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

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
        return self._mode

    async def async_set_mode(self, mode):
        """Set the operation mode."""
        _LOGGER.debug("[%s] Setting new mode: %s", self.name, mode)

        if self.mode == Mode.Boost and mode != Mode.Boost:
            await self.async_set_boost(False)

        if mode == Mode.Boost:
            await self.async_set_boost(True)
            return
        elif mode == Mode.Away:
            end = datetime.now() + self._away_duration
            return await self.async_set_away(end, self._away_temp)
        elif mode == Mode.Closed:
            return await self._async_set_mode(0x40 | int(EQ3BT_OFF_TEMP * 2))
        elif mode == Mode.Open:
            return await self._async_set_mode(0x40 | int(EQ3BT_ON_TEMP * 2))

        if mode == Mode.Manual:
            temperature = max(
                min(self._target_temperature, self.max_temp), self.min_temp
            )
            return await self._async_set_mode(0x40 | int(temperature * 2))
        else:
            return await self._async_set_mode(0)

    @property
    def away_end(self):
        return self._away_end

    async def async_set_away(self, away_end=None, temperature=EQ3BT_AWAY_TEMP):
        """Sets away mode with target temperature.
        When called without parameters disables away mode."""
        if not away_end:
            _LOGGER.debug("[%s] Disabling away, going to auto mode.", self.name)
            return await self._async_set_mode(0x00)

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
    def mode_readable(self):
        """Return a readable representation of the mode.."""
        ret = ""
        mode = self._raw_mode
        if mode == None:
            raise Exception("_raw_mode is empty")
        if mode.MANUAL:
            ret = "manual"
            if self.target_temperature < self.min_temp:
                ret += " off"
            elif self.target_temperature >= self.max_temp:
                ret += " on"
            else:
                ret += " (%sC)" % self.target_temperature
        else:
            ret = "auto"

        if mode.AWAY:
            ret += " holiday"
        if mode.BOOST:
            ret += " boost"
        if mode.DST:
            ret += " dst"
        if mode.WINDOW:
            ret += " window"
        if mode.LOCKED:
            ret += " locked"
        if mode.LOW_BATTERY:
            ret += " low battery"

        return ret

    @property
    def boost(self):
        """Returns True if the thermostat is in boost mode."""
        return self.mode == Mode.Boost

    async def async_set_boost(self, boost):
        """Sets boost mode."""
        _LOGGER.debug("[%s] Setting boost mode: %s", self.name, boost)
        value = struct.pack("BB", PROP_BOOST, bool(boost))
        await self._conn.async_make_request(value)

    @property
    def valve_state(self):
        """Returns the valve state. Probably reported as percent open."""
        return self._valve_state

    @property
    def window_open(self):
        """Returns True if the thermostat reports a open window
        (detected by sudden drop of temperature)"""
        return self._raw_mode and self._raw_mode.WINDOW

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
        return self._window_open_temperature

    @property
    def window_open_time(self) -> timedelta | None:
        """Timeout to reset the thermostat after an open window is detected."""
        return self._window_open_time

    @property
    def locked(self):
        """Returns True if the thermostat is locked."""
        return self._raw_mode and self._raw_mode.LOCKED

    async def async_set_locked(self, lock):
        """Locks or unlocks the thermostat."""
        _LOGGER.debug("[%s] Setting the lock: %s", self.name, lock)
        value = struct.pack("BB", PROP_LOCK, bool(lock))
        await self._conn.async_make_request(value)

    @property
    def low_battery(self):
        """Returns True if the thermostat reports a low battery."""
        return self._raw_mode and self._raw_mode.LOW_BATTERY

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
        return self._comfort_temperature

    @property
    def eco_temperature(self):
        """Returns the eco temperature preset of the thermostat."""
        return self._eco_temperature

    @property
    def temperature_offset(self):
        """Returns the thermostat's temperature offset."""
        return self._temperature_offset

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
    def min_temp(self):
        """Return the minimum temperature."""
        return EQ3BT_MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return EQ3BT_MAX_TEMP

    @property
    def firmware_version(self):
        """Return the firmware version."""
        return self._firmware_version

    @property
    def device_serial(self):
        """Return the device serial number."""
        return self._device_serial

    @property
    def mac(self):
        """Return the mac address."""
        return self._conn._mac
