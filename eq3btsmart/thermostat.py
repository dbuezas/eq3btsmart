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
from typing import Callable

from construct import Byte
from construct_typed import DataclassStruct
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
    OperationMode,
    ScheduleCommand,
    WeekDay,
)
from eq3btsmart.exceptions import TemperatureException
from eq3btsmart.models import DeviceData, Schedule, Status
from eq3btsmart.structures import (
    AwayDataAdapter,
    ScheduleEntryStruct,
    ScheduleStruct,
)
from eq3btsmart.thermostat_config import ThermostatConfig

_LOGGER = logging.getLogger(__name__)


class Thermostat:
    """Representation of a EQ3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        thermostat_config: ThermostatConfig,
        hass: HomeAssistant,
    ):
        """Initialize the thermostat."""

        self.thermostat_config = thermostat_config
        self.status: Status | None = None
        self.device_data: DeviceData | None = None
        self.schedule: Schedule = Schedule()
        self._on_update_callbacks: list[Callable] = []
        self._conn = BleakConnection(
            thermostat_config=self.thermostat_config,
            hass=hass,
            callback=self.handle_notification,
        )

    def register_update_callback(self, on_update: Callable) -> None:
        """Register a callback function that will be called when an update is received."""

        self._on_update_callbacks.append(on_update)

    def shutdown(self) -> None:
        """Shutdown the connection to the thermostat."""

        self._conn.shutdown()

    def _verify_temperature(self, temp: float) -> None:
        """
        Verifies that the temperature is valid.
        :raises TemperatureException: On invalid temperature.
        """

        if temp < EQ3BT_MIN_TEMP or temp > EQ3BT_MAX_TEMP:
            raise TemperatureException(
                f"Temperature {temp} out of range [{EQ3BT_MIN_TEMP}, {EQ3BT_MAX_TEMP}]"
            )

    def handle_notification(self, data: bytearray) -> None:
        """Handle Callback from a Bluetooth (GATT) request."""

        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Received notification from the device.",
        )

        updated: bool = True

        if data[0] == PROP_INFO_RETURN and data[1] == 1:
            _LOGGER.debug(
                f"[{self.thermostat_config.name}] Got status: {codecs.encode(data, 'hex')!r}",
            )

            self.status = Status.from_bytes(data)

            _LOGGER.debug(
                f"[{self.thermostat_config.name}] Parsed status: {self.status}",
            )

        elif data[0] == PROP_SCHEDULE_RETURN:
            self.schedule.add_bytes(data)

        elif data[0] == PROP_ID_RETURN:
            self.device_data = DeviceData.from_bytearray(data)
            _LOGGER.debug(
                f"[{self.thermostat_config.name}] Parsed device data: {self.device_data}",
            )

        else:
            updated = False

            _LOGGER.debug(
                f"[{self.thermostat_config.name}] Unknown notification {data[0]} ({codecs.encode(data, 'hex')!r})",
            )

        if updated:
            for callback in self._on_update_callbacks:
                callback()

    async def async_query_id(self) -> None:
        """Query device identification information, e.g. the serial number."""

        _LOGGER.debug(f"[{self.thermostat_config.name}] Querying id..")

        value = struct.pack("B", PROP_ID_QUERY)
        await self._conn.async_make_request(value)

        _LOGGER.debug(f"[{self.thermostat_config.name}] Finished Querying id..")

    async def async_update(self) -> None:
        """Update the data from the thermostat. Always sets the current time."""

        _LOGGER.debug(f"[{self.thermostat_config.name}] Querying the device..")

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
        """Query the schedule for the given day."""

        _LOGGER.debug(f"[{self.thermostat_config.name}] Querying schedule..")

        if day < 0 or day > 6:
            raise ValueError(f"Invalid day: {day}")

        value = struct.pack("BB", PROP_SCHEDULE_QUERY, day)
        await self._conn.async_make_request(value)

    async def async_set_schedule(
        self, day: WeekDay, hours: list[ScheduleEntryStruct]
    ) -> None:
        """Sets the schedule for the given day."""

        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Setting schedule day=[{day}], hours=[{hours}]",
        )

        data = DataclassStruct(ScheduleStruct).build(
            ScheduleStruct(
                cmd=ScheduleCommand.WRITE,
                day=day,
                hours=hours,
            )
        )
        await self._conn.async_make_request(data)

        self.schedule.add_bytes(data)

        for callback in self._on_update_callbacks:
            callback()

    async def async_set_target_temperature(self, temperature: float | None) -> None:
        """Set new target temperature."""

        if temperature is None:
            return

        temperature_int = int(temperature * 2)
        if temperature == EQ3BT_OFF_TEMP or temperature == EQ3BT_ON_TEMP:
            temperature_int |= 0x40
            value = struct.pack("BB", PROP_MODE_WRITE, temperature_int)
        else:
            self._verify_temperature(temperature)
            value = struct.pack("BB", PROP_TEMPERATURE_WRITE, temperature_int)

        await self._conn.async_make_request(value)

    async def async_set_mode(self, operation_mode: OperationMode) -> None:
        """Set the operation mode."""

        if self.status is None:
            raise Exception("Status not set")

        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Setting new mode: {operation_mode}"
        )

        match operation_mode:
            case OperationMode.OFF:
                await self.async_set_target_temperature(EQ3BT_OFF_TEMP)
            case OperationMode.ON:
                await self.async_set_target_temperature(EQ3BT_ON_TEMP)
            case OperationMode.AUTO:
                await self._async_set_mode(0)
            case OperationMode.MANUAL:
                temperature = max(
                    min(self.status.target_temperature, EQ3BT_MAX_TEMP), EQ3BT_MIN_TEMP
                )
                await self._async_set_mode(0x40 | int(temperature * 2))

    async def async_set_away_until(
        self, away_end: datetime, temperature: float
    ) -> None:
        """Sets away mode with default temperature."""

        # rounding
        away_end = away_end + timedelta(minutes=15)
        away_end = away_end - timedelta(minutes=away_end.minute % 30)

        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Setting away until {away_end}, temp {temperature}",
        )
        adapter = AwayDataAdapter(Byte[4])
        packed = adapter.build(away_end)

        await self._async_set_mode(0x80 | int(temperature * 2), packed)

    async def async_set_away(self, away: bool) -> None:
        """Sets away mode with default temperature."""
        if not away:
            _LOGGER.debug(
                f"[{self.thermostat_config.name}] Disabling away, going to auto mode."
            )
            return await self._async_set_mode(0x00)

        away_end = datetime.now() + timedelta(hours=DEFAULT_AWAY_HOURS)

        await self.async_set_away_until(away_end, DEFAULT_AWAY_TEMP)

    async def _async_set_mode(self, mode: int, payload: bytes | None = None) -> None:
        value = struct.pack("BB", PROP_MODE_WRITE, mode)
        if payload:
            value += payload
        await self._conn.async_make_request(value)

    async def async_set_boost(self, boost: bool) -> None:
        """Sets boost mode."""

        _LOGGER.debug(f"[{self.thermostat_config.name}] Setting boost mode: {boost}")
        value = struct.pack("BB", PROP_BOOST, boost)
        await self._conn.async_make_request(value)

    async def async_window_open_config(
        self, temperature: float, duration: timedelta
    ) -> None:
        """Configures the window open behavior. The duration is specified in
        5 minute increments."""
        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Window open config, temperature: {temperature} duration: {duration}",
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

    async def async_set_locked(self, lock: bool) -> None:
        """Locks or unlocks the thermostat."""
        _LOGGER.debug(f"[{self.thermostat_config.name}] Setting the lock: {lock}")
        value = struct.pack("BB", PROP_LOCK, lock)
        await self._conn.async_make_request(value)

    async def async_temperature_presets(self, comfort: float, eco: float) -> None:
        """Set the thermostats preset temperatures comfort (sun) and
        eco (moon)."""
        _LOGGER.debug(
            f"[{self.thermostat_config.name}] Setting temperature presets, comfort: {comfort} eco: {eco}",
        )
        self._verify_temperature(comfort)
        self._verify_temperature(eco)
        value = struct.pack(
            "BBB", PROP_COMFORT_ECO_CONFIG, int(comfort * 2), int(eco * 2)
        )
        await self._conn.async_make_request(value)

    async def async_set_temperature_offset(self, offset: float) -> None:
        """Sets the thermostat's temperature offset."""
        _LOGGER.debug(f"[{self.thermostat_config.name}] Setting offset: {offset}")
        # [-3,5 .. 0  .. 3,5 ]
        # [00   .. 07 .. 0e ]
        if offset < EQ3BT_MIN_OFFSET or offset > EQ3BT_MAX_OFFSET:
            raise TemperatureException(f"Invalid value: {offset}")

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
