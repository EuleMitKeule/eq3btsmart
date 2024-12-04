from eq3btsmart.const import Eq3WeekDay


def test_from_index() -> None:
    assert Eq3WeekDay.from_index(0) == Eq3WeekDay.MONDAY
    assert Eq3WeekDay.from_index(1) == Eq3WeekDay.TUESDAY
    assert Eq3WeekDay.from_index(2) == Eq3WeekDay.WEDNESDAY
    assert Eq3WeekDay.from_index(3) == Eq3WeekDay.THURSDAY
    assert Eq3WeekDay.from_index(4) == Eq3WeekDay.FRIDAY
    assert Eq3WeekDay.from_index(5) == Eq3WeekDay.SATURDAY
    assert Eq3WeekDay.from_index(6) == Eq3WeekDay.SUNDAY
