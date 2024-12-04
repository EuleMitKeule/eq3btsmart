from datetime import time

from eq3btsmart._structures import _ScheduleDayStruct, _ScheduleHourStruct
from eq3btsmart.const import Eq3WeekDay
from eq3btsmart.models import Schedule, ScheduleDay, ScheduleHour


def test_schedule_initialization() -> None:
    schedule = Schedule()
    assert schedule.schedule_days == [], "Initial schedule_days should be empty"


def test_schedule_merge() -> None:
    schedule1 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            )
        ]
    )
    schedule2 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            )
        ]
    )
    schedule3 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=2, minute=0),
                        target_temperature=21,
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
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=2, minute=0),
                        target_temperature=21,
                    ),
                ],
            ),
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
        ]
    )


def test_schedule_from_bytes() -> None:
    schedule_day_structs = [
        _ScheduleDayStruct(
            day=Eq3WeekDay.MONDAY,
            hours=[
                _ScheduleHourStruct(
                    target_temp=20,
                    next_change_at=time(hour=1, minute=0),
                ),
            ],
        )
    ]
    schedule_days_bytes = [
        schedule_day_struct.to_bytes() for schedule_day_struct in schedule_day_structs
    ]
    schedule_day_structs_from_bytes = [
        ScheduleDay._from_bytes(schedule_day_bytes)
        for schedule_day_bytes in schedule_days_bytes
    ]

    assert [
        ScheduleDay(
            week_day=Eq3WeekDay.MONDAY,
            schedule_hours=[
                ScheduleHour(
                    next_change_at=time(hour=1, minute=0),
                    target_temperature=20,
                ),
            ],
        )
    ] == schedule_day_structs_from_bytes


def test_schedule_delete_day() -> None:
    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
        ]
    )
    schedule.schedule_days = [
        day for day in schedule.schedule_days if day.week_day != Eq3WeekDay.MONDAY
    ]

    assert schedule == Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
        ]
    )


def test_eq() -> None:
    schedule1 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            )
        ]
    )
    schedule2 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            )
        ]
    )
    schedule3 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[],
            ),
        ]
    )
    schedule4 = Schedule(
        schedule_days=[
            ScheduleDay(
                week_day=Eq3WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
                    ),
                ],
            ),
            ScheduleDay(
                week_day=Eq3WeekDay.TUESDAY,
                schedule_hours=[
                    ScheduleHour(
                        next_change_at=time(hour=1, minute=0),
                        target_temperature=20,
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
