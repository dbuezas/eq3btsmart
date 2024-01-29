from datetime import datetime, time, timedelta

import pytest

from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.adapter.eq3_serial import Eq3Serial
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.const import (
    DEFAULT_AWAY_HOURS,
    EQ3BT_ON_TEMP,
    Command,
    Eq3Preset,
    OperationMode,
    WeekDay,
)
from eq3btsmart.models.presets import Presets
from eq3btsmart.models.schedule import Schedule
from eq3btsmart.models.schedule_day import ScheduleDay
from eq3btsmart.models.schedule_hour import ScheduleHour
from eq3btsmart.models.status import Status
from eq3btsmart.structures import Eq3Command, ScheduleDayStruct, ScheduleHourStruct
from eq3btsmart.thermostat import Thermostat
from tests.mock_client import MockClient


@pytest.mark.asyncio
async def test_connect_disconnect(mock_thermostat: Thermostat):
    assert isinstance(mock_thermostat._conn, MockClient)
    assert not mock_thermostat._conn.is_connected

    await mock_thermostat.async_connect()

    assert mock_thermostat._conn.is_connected

    await mock_thermostat.async_disconnect()

    assert not mock_thermostat._conn.is_connected


@pytest.mark.asyncio
async def test_update_callback(mock_thermostat: Thermostat):
    assert mock_thermostat._on_update_callbacks == []

    called: bool = False

    def on_update():
        nonlocal called
        called = True

    mock_thermostat.register_update_callback(on_update)

    assert mock_thermostat._on_update_callbacks == [on_update]

    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert called


@pytest.mark.asyncio
async def test_connection_callback(mock_thermostat: Thermostat):
    assert mock_thermostat._on_connection_callbacks == []

    called: bool = False

    def on_connection():
        nonlocal called
        called = True

    mock_thermostat.register_connection_callback(on_connection)

    assert mock_thermostat._on_connection_callbacks == [on_connection]

    await mock_thermostat.async_connect()

    assert called


@pytest.mark.asyncio
async def test_get_id(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    assert mock_thermostat.device_data is None

    await mock_thermostat.async_get_id()

    assert mock_thermostat.device_data is not None
    assert isinstance(mock_thermostat.device_data.device_serial, Eq3Serial)


@pytest.mark.asyncio
async def test_get_status(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    assert mock_thermostat.status is None

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None


@pytest.mark.asyncio
async def test_get_schedule(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    assert len(mock_thermostat.schedule.schedule_days) == 0

    from tests.mock_client import mock_schedule_days

    mock_schedule_days.append(
        ScheduleDayStruct(
            day=WeekDay.MONDAY,
            hours=[
                ScheduleHourStruct(
                    target_temp=Eq3Temperature(20),
                    next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                ),
            ],
        )
    )

    await mock_thermostat.async_get_schedule()

    assert mock_thermostat.schedule is not None
    assert len(mock_thermostat.schedule.schedule_days) == 1


@pytest.mark.asyncio
async def test_configure_window_open(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_configure_window_open(6.5, timedelta(minutes=25))

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.presets is not None
    assert mock_thermostat.status.presets.window_open_temperature == Eq3Temperature(6.5)
    assert mock_thermostat.status.presets.window_open_time == Eq3Duration(
        timedelta(minutes=25)
    )


@pytest.mark.asyncio
async def test_configure_presets(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    await mock_thermostat.async_configure_presets(
        26.5,
        16,
    )

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.presets is not None
    assert mock_thermostat.status.presets.comfort_temperature == Eq3Temperature(26.5)
    assert mock_thermostat.status.presets.eco_temperature == Eq3Temperature(16.0)


@pytest.mark.asyncio
async def test_configure_presets_without_status(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    with pytest.raises(Exception):
        await mock_thermostat.async_configure_presets(
            26.5,
            16,
        )


@pytest.mark.asyncio
async def test_configure_presets_comfort(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=Eq3Temperature(21.0),
            eco_temperature=Eq3Temperature(17.0),
            window_open_temperature=Eq3Temperature(12.0),
            window_open_time=Eq3Duration(timedelta(minutes=5)),
            offset_temperature=Eq3TemperatureOffset(0.0),
        ),
    )

    await mock_thermostat.async_configure_presets(
        comfort_temperature=26.5,
    )

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.presets is not None
    assert mock_thermostat.status.presets.comfort_temperature == Eq3Temperature(26.5)
    assert mock_thermostat.status.presets.eco_temperature == Eq3Temperature(17.0)


@pytest.mark.asyncio
async def test_configure_presets_eco(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=Eq3Temperature(21.0),
            eco_temperature=Eq3Temperature(17.0),
            window_open_temperature=Eq3Temperature(12.0),
            window_open_time=Eq3Duration(timedelta(minutes=5)),
            offset_temperature=Eq3TemperatureOffset(0.0),
        ),
    )

    await mock_thermostat.async_configure_presets(
        eco_temperature=11.5,
    )

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.presets is not None
    assert mock_thermostat.status.presets.comfort_temperature == Eq3Temperature(21.0)
    assert mock_thermostat.status.presets.eco_temperature == Eq3Temperature(11.5)


@pytest.mark.asyncio
async def test_configure_presets_single_presets_none(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    with pytest.raises(Exception):
        await mock_thermostat.async_configure_presets(
            comfort_temperature=26.5,
        )


@pytest.mark.asyncio
async def test_configure_temperature_offset(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_configure_temperature_offset(2.5)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.presets is not None
    assert mock_thermostat.status.presets.offset_temperature == Eq3TemperatureOffset(
        2.5
    )


@pytest.mark.asyncio
async def test_set_mode(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    await mock_thermostat.async_set_mode(OperationMode.AUTO)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.operation_mode == OperationMode.AUTO


@pytest.mark.asyncio
async def test_set_mode_without_status(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    with pytest.raises(Exception):
        await mock_thermostat.async_set_mode(OperationMode.AUTO)


@pytest.mark.asyncio
async def test_set_mode_manual(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.AUTO,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    await mock_thermostat.async_set_mode(OperationMode.MANUAL)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.operation_mode == OperationMode.MANUAL
    assert mock_thermostat.status.target_temperature == Eq3Temperature(21.0)


@pytest.mark.asyncio
async def test_set_mode_off(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.AUTO,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    await mock_thermostat.async_set_mode(OperationMode.OFF)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.operation_mode == OperationMode.OFF
    assert mock_thermostat.status.target_temperature == Eq3Temperature(4.5)


@pytest.mark.asyncio
async def test_set_mode_on(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    mock_thermostat.status = Status(
        valve=10,
        target_temperature=Eq3Temperature(21.0),
        _operation_mode=OperationMode.AUTO,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )

    await mock_thermostat.async_set_mode(OperationMode.ON)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.operation_mode == OperationMode.ON
    assert mock_thermostat.status.target_temperature == Eq3Temperature(30)


@pytest.mark.asyncio
async def test_set_away(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    datetime_now = datetime.now()
    await mock_thermostat.async_set_away(True)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.is_away
    assert mock_thermostat.status.away_until is not None

    minute_difference = (
        mock_thermostat.status.away_until.value
        - (datetime_now + timedelta(hours=DEFAULT_AWAY_HOURS))
    ).total_seconds() / 60

    assert minute_difference <= 30


@pytest.mark.asyncio
async def test_set_away_disabled(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    await mock_thermostat.async_set_mode(OperationMode.MANUAL)

    await mock_thermostat.async_set_away(False)

    assert mock_thermostat.status is not None
    assert not mock_thermostat.status.is_away
    assert mock_thermostat.status.operation_mode == OperationMode.AUTO


@pytest.mark.asyncio
async def test_set_temperature(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature != Eq3Temperature(23.5)

    await mock_thermostat.async_set_temperature(23.5)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(23.5)


@pytest.mark.asyncio
async def test_set_temperature_off(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature != Eq3Temperature(4.5)
    assert mock_thermostat.status.operation_mode != OperationMode.OFF

    await mock_thermostat.async_set_temperature(4.5)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(4.5)
    assert mock_thermostat.status.operation_mode == OperationMode.OFF


@pytest.mark.asyncio
async def test_set_temperature_on(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature != Eq3Temperature(30)
    assert mock_thermostat.status.operation_mode != OperationMode.ON

    await mock_thermostat.async_set_temperature(EQ3BT_ON_TEMP)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(30)
    assert mock_thermostat.status.operation_mode == OperationMode.ON


@pytest.mark.asyncio
async def test_set_preset_comfort(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()
    await mock_thermostat.async_set_temperature(26)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(26.0)

    await mock_thermostat.async_configure_presets(
        comfort_temperature=21, eco_temperature=17
    )
    await mock_thermostat.async_set_preset(Eq3Preset.COMFORT)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(21.0)


@pytest.mark.asyncio
async def test_set_preset_eco(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()
    await mock_thermostat.async_set_temperature(26)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(26.0)

    await mock_thermostat.async_configure_presets(
        comfort_temperature=21, eco_temperature=17
    )
    await mock_thermostat.async_set_preset(Eq3Preset.ECO)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.target_temperature == Eq3Temperature(17.0)


@pytest.mark.asyncio
async def test_set_boost(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None
    assert not mock_thermostat.status.is_boost
    assert mock_thermostat.status.operation_mode == OperationMode.MANUAL

    await mock_thermostat.async_set_boost(True)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.is_boost
    assert mock_thermostat.status.operation_mode == OperationMode.MANUAL

    await mock_thermostat.async_set_boost(False)

    assert mock_thermostat.status is not None
    assert not mock_thermostat.status.is_boost
    assert mock_thermostat.status.operation_mode == OperationMode.MANUAL


@pytest.mark.asyncio
async def test_set_locked(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.status is not None
    assert not mock_thermostat.status.is_locked

    await mock_thermostat.async_set_locked(True)

    assert mock_thermostat.status is not None
    assert mock_thermostat.status.is_locked

    await mock_thermostat.async_set_locked(False)

    assert mock_thermostat.status is not None
    assert not mock_thermostat.status.is_locked


@pytest.mark.asyncio
async def test_set_schedule(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.schedule is not None

    assert len(mock_thermostat.schedule.schedule_days) == 0

    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        Eq3Temperature(21),
                        Eq3ScheduleTime(time(1, 0, 0)),
                    )
                ],
            )
        ]
    )

    await mock_thermostat.async_set_schedule(schedule)

    assert mock_thermostat.schedule is not None
    assert mock_thermostat.schedule == schedule


@pytest.mark.asyncio
async def test_delete_schedule(mock_thermostat: Thermostat):
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat.schedule is not None
    assert len(mock_thermostat.schedule.schedule_days) == 0

    await mock_thermostat.async_set_schedule(
        Schedule(
            schedule_days=[
                ScheduleDay(
                    WeekDay.MONDAY,
                    schedule_hours=[
                        ScheduleHour(
                            Eq3Temperature(21),
                            Eq3ScheduleTime(time(1, 0, 0)),
                        )
                    ],
                ),
                ScheduleDay(
                    WeekDay.TUESDAY,
                    schedule_hours=[
                        ScheduleHour(
                            Eq3Temperature(21),
                            Eq3ScheduleTime(time(1, 0, 0)),
                        )
                    ],
                ),
                ScheduleDay(
                    WeekDay.WEDNESDAY,
                    schedule_hours=[
                        ScheduleHour(
                            Eq3Temperature(21),
                            Eq3ScheduleTime(time(1, 0, 0)),
                        )
                    ],
                ),
            ]
        )
    )

    assert len(mock_thermostat.schedule.schedule_days) == 3
    assert len(mock_thermostat.schedule.schedule_days[0].schedule_hours) == 1

    await mock_thermostat.async_delete_schedule(WeekDay.MONDAY)

    assert len(mock_thermostat.schedule.schedule_days) == 3
    assert len(mock_thermostat.schedule.schedule_days[0].schedule_hours) == 0

    await mock_thermostat.async_delete_schedule()

    assert len(mock_thermostat.schedule.schedule_days) == 7
    for schedule_day in mock_thermostat.schedule.schedule_days:
        assert len(schedule_day.schedule_hours) == 0


@pytest.mark.asyncio
async def test_write_not_connected(mock_thermostat: Thermostat):
    with pytest.raises(Exception):
        await mock_thermostat.async_set_boost(True)


@pytest.mark.asyncio
async def test_fail_on_invalid_notification(mock_thermostat: Thermostat):
    with pytest.raises(Exception):
        mock_thermostat.on_notification(
            "invalid",  # type: ignore
            Eq3Command(cmd=Command.ID_RETURN, data=b"\x01").to_bytes(),
        )
