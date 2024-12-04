"""Models for the eQ-3 Bluetooth Smart Thermostat library."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Self

from eq3btsmart._structures import (
    _DeviceDataStruct,
    _Eq3Struct,
    _PresetsStruct,
    _ScheduleDayStruct,
    _StatusStruct,
)
from eq3btsmart.const import EQ3_OFF_TEMP, EQ3_ON_TEMP, Eq3OperationMode, Eq3WeekDay

__all__ = [
    "DeviceData",
    "Presets",
    "Schedule",
    "ScheduleDay",
    "ScheduleHour",
    "Status",
]


@dataclass
class _BaseModel[StructType: _Eq3Struct](ABC):
    @classmethod
    @abstractmethod
    def _from_struct(cls: type[Self], struct: StructType) -> Self:
        """Convert the structure to a model."""

    @classmethod
    @abstractmethod
    def _struct_type(cls: type[Self]) -> type[StructType]:
        """Return the structure type associated with the model."""

    @classmethod
    def _from_bytes(cls: type[Self], data: bytes) -> Self:
        """Convert the data to a model."""
        return cls._from_struct(cls._struct_type().from_bytes(data))


@dataclass
class DeviceData(_BaseModel[_DeviceDataStruct]):
    """Device data model.

    Contains general information about the device that is affected by commands scheduled by the user.

    Attributes:
        firmware_version(int): The firmware version of the device.
        device_serial(str): The serial number of the device.
    """

    firmware_version: int
    device_serial: str

    @classmethod
    def _from_struct(cls, struct: _DeviceDataStruct) -> Self:
        return cls(
            firmware_version=struct.version,
            device_serial=struct.serial,
        )

    @classmethod
    def _struct_type(cls) -> type[_DeviceDataStruct]:
        return _DeviceDataStruct


@dataclass
class Status(_BaseModel[_StatusStruct]):
    """Status model.

    Contains the current status of the device.

    Attributes:
        valve(int): The current valve position.
        target_temperature(float): The target temperature.
        operation_mode(Eq3OperationMode): The operation mode.
        is_away(bool): Whether the device is in away mode.
        is_boost(bool): Whether the device is in boost mode.
        is_dst(bool): Whether the device is in daylight saving time.
        is_window_open(bool): Whether the window is open.
        is_locked(bool): Whether the device is locked.
        is_low_battery(bool): Whether the battery is low.
        away_until(datetime | None): The time until the device is in away mode.
        presets(Presets | None): The presets of the device.
    """

    valve: int
    target_temperature: float
    _operation_mode: Eq3OperationMode
    is_away: bool
    is_boost: bool
    is_dst: bool
    is_window_open: bool
    is_locked: bool
    is_low_battery: bool
    away_until: datetime | None = None
    presets: Presets | None = None

    @property
    def operation_mode(self) -> Eq3OperationMode:
        """The operation mode."""
        if self.target_temperature == EQ3_OFF_TEMP:
            return Eq3OperationMode.OFF

        if self.target_temperature == EQ3_ON_TEMP:
            return Eq3OperationMode.ON

        return self._operation_mode

    @property
    def valve_temperature(self) -> float:
        """The valve temperature.

        The valve temperature is calculated based on the valve position and the target temperature.
        """
        return (1 - self.valve / 100) * 2 + self.target_temperature - 2

    @classmethod
    def _from_struct(cls, struct: _StatusStruct) -> Self:
        return cls(
            valve=struct.valve,
            target_temperature=struct.target_temp,
            _operation_mode=Eq3OperationMode.MANUAL
            if struct.mode & struct.mode.MANUAL
            else Eq3OperationMode.AUTO,
            is_away=bool(struct.mode & struct.mode.AWAY),
            is_boost=bool(struct.mode & struct.mode.BOOST),
            is_dst=bool(struct.mode & struct.mode.DST),
            is_window_open=bool(struct.mode & struct.mode.WINDOW),
            is_locked=bool(struct.mode & struct.mode.LOCKED),
            is_low_battery=bool(struct.mode & struct.mode.LOW_BATTERY),
            away_until=struct.away,
            presets=Presets._from_struct(struct.presets) if struct.presets else None,
        )

    @classmethod
    def _struct_type(cls) -> type[_StatusStruct]:
        return _StatusStruct


@dataclass
class Presets(_BaseModel[_PresetsStruct]):
    """Presets model.

    Contains the presets of the device.

    Attributes:
        window_open_temperature(float): The temperature when the window is open.
        window_open_time(timedelta): The time the window is open.
        comfort_temperature(float): The comfort temperature.
        eco_temperature(float): The eco temperature.
        offset_temperature(float): The offset temperature.
    """

    window_open_temperature: float
    window_open_time: timedelta
    comfort_temperature: float
    eco_temperature: float
    offset_temperature: float

    @classmethod
    def _from_struct(cls, struct: _PresetsStruct) -> Self:
        return cls(
            window_open_temperature=struct.window_open_temp,
            window_open_time=struct.window_open_time,
            comfort_temperature=struct.comfort_temp,
            eco_temperature=struct.eco_temp,
            offset_temperature=struct.offset,
        )

    @classmethod
    def _struct_type(cls) -> type[_PresetsStruct]:
        return _PresetsStruct


@dataclass
class Schedule:
    """Schedule model.

    The schedule is a list of days with a list of hours for each day.
    Each hour contains the target temperature and the time when the next change occurs.

    Attributes:
        schedule_days(list[ScheduleDay]): The schedule days.
    """

    schedule_days: list[ScheduleDay] = field(default_factory=list)

    def merge(self, other_schedule: Self) -> None:
        """Merge another schedule into this schedule.

        Args:
            other_schedule(Schedule): The other schedule to merge.
        """
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

    @classmethod
    def _from_bytes(cls, data: bytes) -> Self:
        return cls(schedule_days=[ScheduleDay._from_bytes(data)])

    def __eq__(self, __value: object) -> bool:
        """Check if the schedule is equal to another schedule.

        Args:
            __value(object): The value to compare.
        """
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

            if schedule_day != other_schedule_day:
                return False

        return True


@dataclass
class ScheduleDay(_BaseModel[_ScheduleDayStruct]):
    """Schedule day model.

    Attributes:
        week_day(Eq3WeekDay): The week day.
        schedule_hours(list[ScheduleHour]): The schedule hours.
    """

    week_day: Eq3WeekDay
    schedule_hours: list[ScheduleHour] = field(default_factory=list)

    @classmethod
    def _from_struct(cls, struct: _ScheduleDayStruct) -> Self:
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
    def _struct_type(cls) -> type[_ScheduleDayStruct]:
        return _ScheduleDayStruct

    def __eq__(self, __value: object) -> bool:
        """Check if the schedule day is equal to another schedule day.

        Args:
            __value(object): The value to compare.
        """
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


@dataclass
class ScheduleHour:
    """Schedule hour model.

    Attributes:
        target_temperature(float): The target temperature.
        next_change_at(time): The time when the next change occurs.
    """

    target_temperature: float
    next_change_at: time
