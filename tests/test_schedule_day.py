from datetime import time

from eq3btsmart._structures import _ScheduleDayStruct, _ScheduleHourStruct
from eq3btsmart.const import Eq3WeekDay
from eq3btsmart.models import ScheduleDay, ScheduleHour


def test_schedule_day_initialization() -> None:
    schedule_day = ScheduleDay(
        week_day=Eq3WeekDay.MONDAY,
        schedule_hours=[ScheduleHour(21.5, time(hour=22, minute=0))],
    )
    assert schedule_day.week_day == Eq3WeekDay.MONDAY
    assert len(schedule_day.schedule_hours) == 1
    assert schedule_day.schedule_hours[0].target_temperature == 21.5


def test_schedule_day_from_struct() -> None:
    struct = _ScheduleDayStruct(
        day=Eq3WeekDay.TUESDAY,
        hours=[
            _ScheduleHourStruct(
                next_change_at=time(hour=22, minute=0),
                target_temp=22,
            )
        ],
    )

    schedule_day = ScheduleDay._from_struct(struct)

    assert schedule_day.week_day == Eq3WeekDay.TUESDAY
    assert len(schedule_day.schedule_hours) == 1
    assert schedule_day.schedule_hours[0].target_temperature == 22


def test_schedule_day_equality() -> None:
    day1 = ScheduleDay(
        week_day=Eq3WeekDay.WEDNESDAY,
        schedule_hours=[ScheduleHour(20.0, time(hour=22, minute=0))],
    )
    day2 = ScheduleDay(
        week_day=Eq3WeekDay.WEDNESDAY,
        schedule_hours=[ScheduleHour(20.0, time(hour=22, minute=0))],
    )
    day3 = ScheduleDay(
        week_day=Eq3WeekDay.THURSDAY,
        schedule_hours=[],
    )
    day4 = ScheduleDay(
        week_day=Eq3WeekDay.WEDNESDAY,
        schedule_hours=[],
    )

    assert day1 == day2
    assert day1 != day3
    assert day1 != day4
    assert day1 != "not a schedule day"
