from eq3btsmart.const import WeekDay


def test_from_index():
    assert WeekDay.from_index(0) == WeekDay.MONDAY
    assert WeekDay.from_index(1) == WeekDay.TUESDAY
    assert WeekDay.from_index(2) == WeekDay.WEDNESDAY
    assert WeekDay.from_index(3) == WeekDay.THURSDAY
    assert WeekDay.from_index(4) == WeekDay.FRIDAY
    assert WeekDay.from_index(5) == WeekDay.SATURDAY
    assert WeekDay.from_index(6) == WeekDay.SUNDAY
