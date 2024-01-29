import asyncio
from datetime import datetime, timedelta
from typing import Callable, Type

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from eq3btsmart.adapter.eq3_away_time import Eq3AwayTime
from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_serial import Eq3Serial
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.const import (
    NOTIFY_CHARACTERISTIC_UUID,
    WRITE_CHARACTERISTIC_UUID,
    StatusFlags,
)
from eq3btsmart.structures import (
    AwaySetCommand,
    BoostSetCommand,
    ComfortEcoConfigureCommand,
    ComfortSetCommand,
    DeviceDataStruct,
    EcoSetCommand,
    Eq3Struct,
    IdGetCommand,
    InfoGetCommand,
    LockSetCommand,
    ModeSetCommand,
    OffsetConfigureCommand,
    PresetsStruct,
    ScheduleDayStruct,
    ScheduleGetCommand,
    ScheduleSetCommand,
    StatusStruct,
    TemperatureSetCommand,
    WindowOpenConfigureCommand,
)

mock_id = DeviceDataStruct(
    version=1, unknown_1=0, unknown_2=0, serial=Eq3Serial("serial1234"), unknown_3=0
)


mock_status = StatusStruct(
    mode=StatusFlags.MANUAL,
    valve=0x10,
    target_temp=Eq3Temperature(21),
)
mock_status.away = Eq3AwayTime(datetime.now() - timedelta(days=1))
mock_status.presets = PresetsStruct(
    comfort_temp=Eq3Temperature(21),
    eco_temp=Eq3Temperature(17),
    window_open_temp=Eq3Temperature(12),
    window_open_time=Eq3Duration(timedelta(minutes=5)),
    offset=Eq3TemperatureOffset(0),
)


mock_schedule_days: list[ScheduleDayStruct] = []


class MockClient:
    def __init__(
        self,
        device: BLEDevice,
        disconnected_callback: Callable | None = None,
        timeout: int = 10,
    ):
        self.device = device
        self._is_connected: bool = False
        self._notify_callbacks: list[Callable] = []
        self._disconnected_callback: Callable | None = disconnected_callback
        self._timeout: int = timeout
        self._last_command: Eq3Struct | None = None
        self._loop = asyncio.get_event_loop()
        self._fail_on_connect: bool = False

    @property
    def is_connected(self):
        return self._is_connected

    async def connect(self, **kwargs):
        if self._fail_on_connect:
            raise BleakError()

        self._is_connected = True

    async def disconnect(self):
        self._is_connected = False
        if self._disconnected_callback:
            self._disconnected_callback(self)

    async def start_notify(self, char: str, callback: Callable):
        if char != NOTIFY_CHARACTERISTIC_UUID:
            raise BleakError()

        self._notify_callbacks.append(callback)

    async def write_gatt_char(self, char: str, data: bytes):
        if char != WRITE_CHARACTERISTIC_UUID:
            raise BleakError()

        command_types: list[Type[Eq3Struct]] = [
            IdGetCommand,
            InfoGetCommand,
            ComfortEcoConfigureCommand,
            OffsetConfigureCommand,
            WindowOpenConfigureCommand,
            ScheduleGetCommand,
            AwaySetCommand,
            ModeSetCommand,
            TemperatureSetCommand,
            ScheduleSetCommand,
            ComfortSetCommand,
            EcoSetCommand,
            BoostSetCommand,
            LockSetCommand,
        ]

        for command_type in command_types:
            try:
                command = command_type.from_bytes(data)
                break
            except Exception:
                continue

        if isinstance(
            command,
            (
                ComfortEcoConfigureCommand,
                OffsetConfigureCommand,
                WindowOpenConfigureCommand,
            ),
        ):
            if mock_status.away is None:
                mock_status.away = Eq3AwayTime(datetime.now() + timedelta(days=1))

            if mock_status.presets is None:
                mock_status.presets = PresetsStruct(
                    comfort_temp=Eq3Temperature(21),
                    eco_temp=Eq3Temperature(17),
                    window_open_temp=Eq3Temperature(12),
                    window_open_time=Eq3Duration(timedelta(minutes=5)),
                    offset=Eq3TemperatureOffset(0),
                )

        if isinstance(command, WindowOpenConfigureCommand):
            if mock_status.presets is None:
                raise Exception("Presets not set")

            window_open_configure_command: WindowOpenConfigureCommand = command

            mock_status.presets.window_open_temp = (
                window_open_configure_command.window_open_temperature
            )
            mock_status.presets.window_open_time = (
                window_open_configure_command.window_open_time
            )

        if isinstance(command, ComfortEcoConfigureCommand):
            if mock_status.presets is None:
                raise Exception("Presets not set")

            comfort_eco_configure_command: ComfortEcoConfigureCommand = command

            mock_status.presets.comfort_temp = (
                comfort_eco_configure_command.comfort_temperature
            )
            mock_status.presets.eco_temp = comfort_eco_configure_command.eco_temperature

        if isinstance(command, OffsetConfigureCommand):
            if mock_status.presets is None:
                raise Exception("Presets not set")

            offset_configure_command: OffsetConfigureCommand = command

            mock_status.presets.offset = offset_configure_command.offset

        if isinstance(command, ModeSetCommand):
            mode_set_command: ModeSetCommand = command
            mode_int = mode_set_command.mode
            temp: int | None = None

            if 0x3C <= mode_int <= 0x80:
                mode_int -= 0x40
                mode = StatusFlags.MANUAL
                temp = mode_int
            elif mode_int >= 0x80:
                mode_int -= 0x80
                mode = StatusFlags.AWAY
                temp = mode_int
            else:
                mode = StatusFlags(mode_int)

            mock_status.mode = mode

            if temp is not None:
                mock_status.target_temp = Eq3Temperature(temp / 2)

        if isinstance(command, AwaySetCommand):
            if mock_status.away is None:
                mock_status.away = command.away_until

        if isinstance(command, TemperatureSetCommand):
            mock_status.target_temp = command.temperature

        if isinstance(command, ComfortSetCommand):
            if mock_status.presets is None:
                raise Exception("Presets not set")

            mock_status.target_temp = mock_status.presets.comfort_temp

        if isinstance(command, EcoSetCommand):
            if mock_status.presets is None:
                raise Exception("Presets not set")

            mock_status.target_temp = mock_status.presets.eco_temp

        if isinstance(command, BoostSetCommand):
            if command.enable:
                mock_status.mode |= StatusFlags.BOOST
            else:
                mock_status.mode &= ~StatusFlags.BOOST

        if isinstance(command, LockSetCommand):
            if command.enable:
                mock_status.mode |= StatusFlags.LOCKED
            else:
                mock_status.mode &= ~StatusFlags.LOCKED

        if isinstance(command, ScheduleSetCommand):
            schedule_day = next(
                (
                    schedule_day
                    for schedule_day in mock_schedule_days
                    if schedule_day.day == command.day
                ),
                None,
            )

            if schedule_day is None:
                schedule_day = ScheduleDayStruct(
                    day=command.day,
                    hours=command.hours,
                )
                mock_schedule_days.append(schedule_day)
            else:
                schedule_day.hours = command.hours

        self._last_command = command

        await self.respond()

    async def respond(self):
        if not self._is_connected:
            return

        if self._last_command is None:
            return

        if isinstance(self._last_command, (ScheduleGetCommand, ScheduleSetCommand)):
            for mock_schedule in mock_schedule_days:
                data = mock_schedule.to_bytes()
                for callback in self._notify_callbacks:
                    callback(
                        NOTIFY_CHARACTERISTIC_UUID,
                        data,
                    )
            return

        if isinstance(self._last_command, IdGetCommand):
            data = mock_id.to_bytes()

        elif isinstance(
            self._last_command,
            (
                InfoGetCommand,
                ComfortEcoConfigureCommand,
                OffsetConfigureCommand,
                WindowOpenConfigureCommand,
                ModeSetCommand,
                AwaySetCommand,
                TemperatureSetCommand,
                ComfortSetCommand,
                EcoSetCommand,
                BoostSetCommand,
                LockSetCommand,
            ),
        ):
            data = mock_status.to_bytes()

        for callback in self._notify_callbacks:
            callback(
                NOTIFY_CHARACTERISTIC_UUID,
                data,
            )

        self._last_command = None
