from datetime import time

from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import WeekDay
from eq3btsmart.models import ScheduleDay, ScheduleHour
from eq3btsmart.structures import ScheduleDayStruct, ScheduleHourStruct


def test_schedule_day_initialization():
    schedule_day = ScheduleDay(
        week_day=WeekDay.MONDAY,
        schedule_hours=[
            ScheduleHour(Eq3Temperature(21.5), Eq3ScheduleTime(time(hour=22, minute=0)))
        ],
    )
    assert schedule_day.week_day == WeekDay.MONDAY
    assert len(schedule_day.schedule_hours) == 1
    assert schedule_day.schedule_hours[0].target_temperature == Eq3Temperature(21.5)


def test_schedule_day_from_struct():
    struct = ScheduleDayStruct(
        day=WeekDay.TUESDAY,
        hours=[
            ScheduleHourStruct(
                next_change_at=Eq3ScheduleTime(time(hour=22, minute=0)),
                target_temp=Eq3Temperature(22),
            )
        ],
    )

    schedule_day = ScheduleDay.from_struct(struct)

    assert schedule_day.week_day == WeekDay.TUESDAY
    assert len(schedule_day.schedule_hours) == 1
    assert schedule_day.schedule_hours[0].target_temperature == Eq3Temperature(22)


def test_schedule_day_equality():
    day1 = ScheduleDay(
        week_day=WeekDay.WEDNESDAY,
        schedule_hours=[
            ScheduleHour(Eq3Temperature(20.0), Eq3ScheduleTime(time(hour=22, minute=0)))
        ],
    )
    day2 = ScheduleDay(
        week_day=WeekDay.WEDNESDAY,
        schedule_hours=[
            ScheduleHour(Eq3Temperature(20.0), Eq3ScheduleTime(time(hour=22, minute=0)))
        ],
    )
    day3 = ScheduleDay(
        week_day=WeekDay.THURSDAY,
        schedule_hours=[],
    )
    day4 = ScheduleDay(
        week_day=WeekDay.WEDNESDAY,
        schedule_hours=[],
    )

    assert day1 == day2
    assert day1 != day3
    assert day1 != day4
    assert day1 != "not a schedule day"
