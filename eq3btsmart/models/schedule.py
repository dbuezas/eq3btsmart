from dataclasses import dataclass, field
from typing import Self

from eq3btsmart.const import WeekDay
from eq3btsmart.models.schedule_day import ScheduleDay


@dataclass
class Schedule:
    schedule_days: list[ScheduleDay] = field(default_factory=list)

    def merge(self, other_schedule: Self) -> None:
        for other_schedule_day in other_schedule.schedule_days:
            schedule_day = next(
                (
                    schedule_day
                    for schedule_day in self.schedule_days
                    if schedule_day.week_day == other_schedule_day.week_day
                ),
                None,
            )

            if not schedule_day:
                self.schedule_days.append(other_schedule_day)
                continue

            schedule_day.schedule_hours = other_schedule_day.schedule_hours

    def delete_day(self, week_day: WeekDay) -> None:
        self.schedule_days = [
            schedule_day
            for schedule_day in self.schedule_days
            if schedule_day.week_day != week_day
        ]

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls(schedule_days=[ScheduleDay.from_bytes(data)])

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Schedule):
            return False

        week_days_to_compare = [
            schedule_day.week_day
            for schedule_day in self.schedule_days
            if len(schedule_day.schedule_hours) > 0
        ]
        week_days_to_compare.extend(
            [
                schedule_day.week_day
                for schedule_day in __value.schedule_days
                if len(schedule_day.schedule_hours) > 0
            ]
        )

        for week_day in week_days_to_compare:
            schedule_day = next(
                (
                    schedule_day
                    for schedule_day in self.schedule_days
                    if schedule_day.week_day == week_day
                ),
                None,
            )
            other_schedule_day = next(
                (
                    schedule_day
                    for schedule_day in __value.schedule_days
                    if schedule_day.week_day == week_day
                ),
                None,
            )

            if schedule_day is None or other_schedule_day is None:
                return False

            other_schedule_day = next(
                (
                    other_schedule_day
                    for other_schedule_day in __value.schedule_days
                    if other_schedule_day.week_day == schedule_day.week_day
                ),
                None,
            )

            if not schedule_day == other_schedule_day:
                return False

        return True
