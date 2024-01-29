from datetime import time

from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import WeekDay
from eq3btsmart.models import Schedule, ScheduleDay
from eq3btsmart.models.schedule_hour import ScheduleHour
from eq3btsmart.structures import ScheduleDayStruct, ScheduleHourStruct


def test_schedule_initialization():
    schedule = Schedule()
    assert schedule.schedule_days == [], "Initial schedule_days should be empty"


def test_schedule_merge():
    schedule1 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            )
        ]
    )
    schedule2 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            )
        ]
    )
    schedule3 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=2, minute=0)),
                        target_temperature=Eq3Temperature(21),
                    ),
                ],
            )
        ]
    )

    schedule1.merge(schedule2)
    schedule1.merge(schedule3)

    assert schedule1 == Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=2, minute=0)),
                        target_temperature=Eq3Temperature(21),
                    ),
                ],
            ),
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
        ]
    )


def test_schedule_from_bytes():
    schedule_day_structs = [
        ScheduleDayStruct(
            day=WeekDay.MONDAY,
            hours=[
                ScheduleHourStruct(
                    target_temp=Eq3Temperature(20),
                    next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                ),
            ],
        )
    ]
    schedule_days_bytes = [
        schedule_day_struct.to_bytes() for schedule_day_struct in schedule_day_structs
    ]
    schedule_day_structs_from_bytes = [
        ScheduleDay.from_bytes(schedule_day_bytes)
        for schedule_day_bytes in schedule_days_bytes
    ]

    assert [
        ScheduleDay(
            week_day=WeekDay.MONDAY,
            schedule_hours=[
                ScheduleHour(
                    next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                    target_temperature=Eq3Temperature(20),
                ),
            ],
        )
    ] == schedule_day_structs_from_bytes


def test_schedule_delete_day():
    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
        ]
    )
    schedule.delete_day(WeekDay.MONDAY)

    assert schedule == Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
        ]
    )


def test_eq():
    schedule1 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            )
        ]
    )
    schedule2 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            )
        ]
    )
    schedule3 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[],
            ),
        ]
    )
    schedule4 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
            ScheduleDay(
                week_day=WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=Eq3ScheduleTime(time(hour=1, minute=0)),
                        target_temperature=Eq3Temperature(20),
                    ),
                ],
            ),
        ]
    )

    assert schedule1 == schedule2
    assert not schedule1 == "foo"
    assert not schedule1 == Schedule(schedule_days=[])
    assert schedule1 == schedule3
    assert schedule3 != schedule4
