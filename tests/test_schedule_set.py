from datetime import time

from eq3btsmart.const import WeekDay
from eq3btsmart.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.eq3_temperature import Eq3Temperature
from eq3btsmart.models import Schedule, ScheduleDay, ScheduleHour
from eq3btsmart.structures import ScheduleHourStruct, ScheduleSetCommand


def test_schedule_set():
    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        target_temperature=Eq3Temperature(20),
                        next_change_at=Eq3ScheduleTime(time(hour=6, minute=0)),
                    ),
                ],
            )
        ]
    )

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

        command.to_bytes()
