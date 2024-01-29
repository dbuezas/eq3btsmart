"""
Support for eq3 Bluetooth Smart thermostats.

All temperatures in Celsius.

To get the current state, update() has to be called for powersaving reasons.
Schedule needs to be requested with query_schedule() before accessing for similar reasons.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from construct_typed import DataclassStruct

from eq3btsmart.adapter.eq3_away_time import Eq3AwayTime
from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.adapter.eq3_time import Eq3Time
from eq3btsmart.connection_monitor import ConnectionMonitor
from eq3btsmart.const import (
    DEFAULT_AWAY_HOURS,
    DEFAULT_AWAY_TEMP,
    EQ3BT_MAX_TEMP,
    EQ3BT_MIN_TEMP,
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
    NOTIFY_CHARACTERISTIC_UUID,
    REQUEST_TIMEOUT,
    WRITE_CHARACTERISTIC_UUID,
    Command,
    Eq3Preset,
    OperationMode,
    WeekDay,
)
from eq3btsmart.models import DeviceData, Schedule, Status
from eq3btsmart.structures import (
    AwaySetCommand,
    BoostSetCommand,
    ComfortEcoConfigureCommand,
    ComfortSetCommand,
    EcoSetCommand,
    Eq3Command,
    Eq3Struct,
    IdGetCommand,
    InfoGetCommand,
    LockSetCommand,
    ModeSetCommand,
    OffsetConfigureCommand,
    ScheduleGetCommand,
    ScheduleHourStruct,
    ScheduleSetCommand,
    TemperatureSetCommand,
    WindowOpenConfigureCommand,
)
from eq3btsmart.thermostat_config import ThermostatConfig

_LOGGER = logging.getLogger(__name__)


class Thermostat:
    """Representation of a EQ3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        thermostat_config: ThermostatConfig,
        ble_device: BLEDevice,
    ):
        """Initialize the thermostat."""

        self.thermostat_config = thermostat_config
        self.status: Status | None = None
        self.device_data: DeviceData | None = None
        self.schedule: Schedule = Schedule()
        self._on_update_callbacks: list[Callable] = []
        self._on_connection_callbacks: list[Callable] = []
        self._device = ble_device
        self._conn: BleakClient = BleakClient(
            ble_device,
            disconnected_callback=lambda client: self.on_connection(),
            timeout=REQUEST_TIMEOUT,
        )
        self._lock = asyncio.Lock()
        self._monitor = ConnectionMonitor(self._conn)

    def register_connection_callback(self, on_connect: Callable) -> None:
        """Register a callback function that will be called when a connection is established."""

        self._on_connection_callbacks.append(on_connect)

    def register_update_callback(self, on_update: Callable) -> None:
        """Register a callback function that will be called when an update is received."""

        self._on_update_callbacks.append(on_update)

    async def async_connect(self) -> None:
        """Connect to the thermostat."""

        await self._conn.connect()
        await self._conn.start_notify(NOTIFY_CHARACTERISTIC_UUID, self.on_notification)

        self.on_connection()

        loop = asyncio.get_running_loop()
        loop.create_task(self._monitor.run())

    async def async_disconnect(self) -> None:
        """Shutdown the connection to the thermostat."""

        await self._monitor.stop()
        await self._conn.disconnect()

    async def async_get_id(self) -> None:
        """Query device identification information, e.g. the serial number."""

        await self._async_write_command(IdGetCommand())

    async def async_get_status(self) -> None:
        """Query the thermostat status."""

        eq3_time = Eq3Time(datetime.now())
        await self._async_write_command(InfoGetCommand(time=eq3_time))

    async def async_get_schedule(self) -> None:
        """Query the schedule."""

        for week_day in WeekDay:
            await self._async_write_command(ScheduleGetCommand(day=week_day))

    async def async_configure_window_open(
        self, temperature: float, duration: timedelta
    ) -> None:
        """Configures the window open behavior. The duration is specified in 5 minute increments."""

        eq3_temperature = Eq3Temperature(temperature)
        eq3_duration = Eq3Duration(duration)

        await self._async_write_command(
            WindowOpenConfigureCommand(
                window_open_temperature=eq3_temperature,
                window_open_time=eq3_duration,
            )
        )

    async def async_configure_presets(
        self,
        comfort_temperature: float | None = None,
        eco_temperature: float | None = None,
    ) -> None:
        """Set the thermostats preset temperatures comfort (sun) and eco (moon)."""

        if self.status is None:
            raise Exception("Status not set")

        if comfort_temperature is None and self.status.presets is not None:
            comfort_temperature = self.status.presets.comfort_temperature.value

        if eco_temperature is None and self.status.presets is not None:
            eco_temperature = self.status.presets.eco_temperature.value

        if comfort_temperature is None or eco_temperature is None:
            raise Exception("Comfort or eco temperature not set")

        eq3_comfort_temperature = Eq3Temperature(comfort_temperature)
        eq3_eco_temperature = Eq3Temperature(eco_temperature)

        await self._async_write_command(
            ComfortEcoConfigureCommand(
                comfort_temperature=eq3_comfort_temperature,
                eco_temperature=eq3_eco_temperature,
            )
        )

    async def async_configure_temperature_offset(
        self, temperature_offset: float
    ) -> None:
        """Sets the thermostat's temperature offset."""

        eq3_temperature_offset = Eq3TemperatureOffset(temperature_offset)
        await self._async_write_command(
            OffsetConfigureCommand(offset=eq3_temperature_offset)
        )

    async def async_set_mode(self, operation_mode: OperationMode) -> None:
        """Set new operation mode."""

        if self.status is None or self.status.target_temperature is None:
            raise Exception("Status not set")

        command: ModeSetCommand

        match operation_mode:
            case OperationMode.AUTO:
                command = ModeSetCommand(mode=OperationMode.AUTO)
            case OperationMode.MANUAL:
                temperature = max(
                    min(
                        self.status.target_temperature.value,
                        EQ3BT_MAX_TEMP,
                    ),
                    EQ3BT_MIN_TEMP,
                )
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL | Eq3Temperature(temperature).encode()
                )
            case OperationMode.OFF:
                off_temperature = Eq3Temperature(EQ3BT_OFF_TEMP)
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL | off_temperature.encode()
                )
            case OperationMode.ON:
                on_temperature = Eq3Temperature(EQ3BT_ON_TEMP)
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL | on_temperature.encode()
                )

        await self._async_write_command(command)

    async def async_set_away(
        self,
        enable: bool,
        away_until: datetime | None = None,
        temperature: float | None = None,
    ) -> None:
        if not enable:
            return await self.async_set_mode(OperationMode.AUTO)

        if away_until is None:
            away_until = datetime.now() + timedelta(hours=DEFAULT_AWAY_HOURS)

        if temperature is None:
            temperature = DEFAULT_AWAY_TEMP

        eq3_away_until = Eq3AwayTime(away_until)
        eq3_temperature = Eq3Temperature(temperature)

        await self._async_write_command(
            AwaySetCommand(
                mode=OperationMode.AWAY | eq3_temperature.encode(),
                away_until=eq3_away_until,
            )
        )

    async def async_set_temperature(self, temperature: float) -> None:
        """Set new target temperature."""

        if temperature == EQ3BT_OFF_TEMP:
            return await self.async_set_mode(OperationMode.OFF)

        if temperature == EQ3BT_ON_TEMP:
            return await self.async_set_mode(OperationMode.ON)

        eq3_temperature = Eq3Temperature(temperature)
        await self._async_write_command(
            TemperatureSetCommand(temperature=eq3_temperature)
        )

    async def async_set_preset(self, preset: Eq3Preset):
        """Sets the thermostat to the given preset."""

        command: ComfortSetCommand | EcoSetCommand

        match preset:
            case Eq3Preset.COMFORT:
                command = ComfortSetCommand()
            case Eq3Preset.ECO:
                command = EcoSetCommand()

        await self._async_write_command(command)

    async def async_set_boost(self, enable: bool) -> None:
        """Sets boost mode."""

        await self._async_write_command(BoostSetCommand(enable=enable))

    async def async_set_locked(self, enable: bool) -> None:
        """Locks or unlocks the thermostat."""

        await self._async_write_command(LockSetCommand(enable=enable))

    async def async_delete_schedule(self, week_day: WeekDay | None = None) -> None:
        """Deletes the schedule."""

        if week_day is not None:
            await self._async_write_command(ScheduleSetCommand(day=week_day, hours=[]))
        else:
            for week_day in WeekDay:
                await self._async_write_command(
                    ScheduleSetCommand(day=week_day, hours=[])
                )

    async def async_set_schedule(self, schedule: Schedule) -> None:
        """Sets the schedule for the given day."""

        for schedule_day in schedule.schedule_days:
            command = ScheduleSetCommand(
                day=schedule_day.week_day,
                hours=[
                    ScheduleHourStruct(
                        target_temp=schedule_hour.target_temperature,
                        next_change_at=schedule_hour.next_change_at,
                    )
                    for schedule_hour in schedule_day.schedule_hours
                ],
            )

            await self._async_write_command(command)

    async def _async_write_command(self, command: Eq3Struct) -> None:
        """Write a EQ3 command to the thermostat."""

        if not self._conn.is_connected:
            raise Exception("Not connected")

        data = command.to_bytes()

        async with self._lock:
            await self._conn.write_gatt_char(WRITE_CHARACTERISTIC_UUID, data)

            self.on_connection()

    def on_connection(self) -> None:
        for callback in self._on_connection_callbacks:
            callback()

    def on_notification(self, handle: BleakGATTCharacteristic, data: bytes) -> None:
        """Handle Callback from a Bluetooth (GATT) request."""

        data_bytes = bytes(data)

        command = DataclassStruct(Eq3Command).parse(data_bytes)

        is_status_command = command.data[0] == 0x01

        match command.cmd:
            case Command.ID_RETURN:
                self.device_data = DeviceData.from_bytes(data_bytes)
            case Command.INFO_RETURN:
                if is_status_command:
                    self.status = Status.from_bytes(data_bytes)
            case Command.SCHEDULE_RETURN:
                schedule = Schedule.from_bytes(data_bytes)
                self.schedule.merge(schedule)

        for callback in self._on_update_callbacks:
            callback()
