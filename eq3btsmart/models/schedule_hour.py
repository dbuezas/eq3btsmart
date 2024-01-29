from dataclasses import dataclass

from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature


@dataclass
class ScheduleHour:
    target_temperature: Eq3Temperature
    next_change_at: Eq3ScheduleTime
