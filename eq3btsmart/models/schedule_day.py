from dataclasses import dataclass, field
from typing import Self

from eq3btsmart.const import WeekDay
from eq3btsmart.models.base_model import BaseModel
from eq3btsmart.models.schedule_hour import ScheduleHour
from eq3btsmart.structures import ScheduleDayStruct


@dataclass
class ScheduleDay(BaseModel[ScheduleDayStruct]):
    week_day: WeekDay
    schedule_hours: list[ScheduleHour] = field(default_factory=list)

    @classmethod
    def from_struct(cls, struct: ScheduleDayStruct) -> Self:
        return cls(
            week_day=struct.day,
            schedule_hours=[
                ScheduleHour(
                    target_temperature=hour.target_temp,
                    next_change_at=hour.next_change_at,
                )
                for hour in struct.hours
            ],
        )

    @classmethod
    def struct_type(cls) -> type[ScheduleDayStruct]:
        return ScheduleDayStruct

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, ScheduleDay):
            return False

        if self.week_day != __value.week_day:
            return False

        if len(self.schedule_hours) != len(__value.schedule_hours):
            return False

        return all(
            hour == other_hour
            for hour, other_hour in zip(self.schedule_hours, __value.schedule_hours)
        )
