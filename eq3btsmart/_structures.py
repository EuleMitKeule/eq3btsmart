"""Structures for the eQ-3 Bluetooth Smart Thermostat."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Self

from construct import (
    Bytes,
    Const,
    Flag,
    GreedyBytes,
    GreedyRange,
    Int8ub,
    Optional,
)
from construct_typed import DataclassMixin, DataclassStruct, TEnum, TFlagsEnum, csfield

from eq3btsmart._adapters import (
    _Eq3AwayTime,
    _Eq3Duration,
    _Eq3ScheduleTime,
    _Eq3Serial,
    _Eq3Temperature,
    _Eq3TemperatureOffset,
    _Eq3Time,
)
from eq3btsmart.const import (
    Eq3WeekDay,
    _Eq3Command,
    _Eq3StatusFlags,
)

__all__: list[str] = []


class _Eq3Struct(DataclassMixin):
    """Structure for eQ-3 data."""

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Convert the data to a structure."""
        return DataclassStruct(cls).parse(data)

    def to_bytes(self) -> bytes:
        """Convert the structure to bytes."""
        return DataclassStruct(self.__class__).build(self)


@dataclass
class _DeviceDataStruct(_Eq3Struct):
    """Structure for device data."""

    cmd: int = csfield(Const(_Eq3Command.ID_RETURN, Int8ub))
    version: int = csfield(Int8ub)
    unknown_1: int = csfield(Int8ub)
    unknown_2: int = csfield(Int8ub)
    serial: str = csfield(_Eq3Serial(Bytes(10)))
    unknown_3: int = csfield(Int8ub)


@dataclass
class _PresetsStruct(_Eq3Struct):
    """Structure for presets data."""

    window_open_temp: float = csfield(_Eq3Temperature(Int8ub))
    window_open_time: timedelta = csfield(_Eq3Duration(Int8ub))
    comfort_temp: float = csfield(_Eq3Temperature(Int8ub))
    eco_temp: float = csfield(_Eq3Temperature(Int8ub))
    offset: float = csfield(_Eq3TemperatureOffset(Int8ub))


@dataclass
class _StatusStruct(_Eq3Struct):
    """Structure for status data."""

    cmd: int = csfield(Const(_Eq3Command.INFO_RETURN, Int8ub))
    const_1: int = csfield(Const(0x01, Int8ub))
    mode: _Eq3StatusFlags = csfield(TFlagsEnum(Int8ub, _Eq3StatusFlags))
    valve: int = csfield(Int8ub)
    const_2: int = csfield(Const(0x04, Int8ub))
    target_temp: float = csfield(_Eq3Temperature(Int8ub))
    away: datetime | None = csfield(Optional(_Eq3AwayTime(Bytes(4))))
    presets: _PresetsStruct | None = csfield(Optional(DataclassStruct(_PresetsStruct)))


@dataclass
class _ScheduleHourStruct(_Eq3Struct):
    """Structure for schedule entry data."""

    target_temp: float = csfield(_Eq3Temperature(Int8ub))
    next_change_at: time = csfield(_Eq3ScheduleTime(Int8ub))


@dataclass
class _ScheduleDayStruct(_Eq3Struct):
    """Structure for schedule data."""

    cmd: int = csfield(Const(_Eq3Command.SCHEDULE_RETURN, Int8ub))
    day: Eq3WeekDay = csfield(TEnum(Int8ub, Eq3WeekDay))
    hours: list[_ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(_ScheduleHourStruct))
    )


@dataclass
class _Eq3Message(_Eq3Struct):
    """Structure for eQ-3 message."""

    cmd: int = csfield(Int8ub)
    is_status_command: bool = csfield(Flag)
    data: bytes = csfield(GreedyBytes)


@dataclass
class _IdGetCommand(_Eq3Struct):
    """Structure for ID get command."""

    cmd: int = csfield(Const(_Eq3Command.ID_GET, Int8ub))


@dataclass
class _InfoGetCommand(_Eq3Struct):
    """Structure for info get command."""

    cmd: int = csfield(Const(_Eq3Command.INFO_GET, Int8ub))
    time: datetime = csfield(_Eq3Time(Bytes(6)))


@dataclass
class _ComfortEcoConfigureCommand(_Eq3Struct):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(_Eq3Command.COMFORT_ECO_CONFIGURE, Int8ub))
    comfort_temperature: float = csfield(_Eq3Temperature(Int8ub))
    eco_temperature: float = csfield(_Eq3Temperature(Int8ub))


@dataclass
class _OffsetConfigureCommand(_Eq3Struct):
    """Structure for offset configure command."""

    cmd: int = csfield(Const(_Eq3Command.OFFSET_CONFIGURE, Int8ub))
    offset: float = csfield(_Eq3TemperatureOffset(Int8ub))


@dataclass
class _WindowOpenConfigureCommand(_Eq3Struct):
    """Structure for window open configure command."""

    cmd: int = csfield(Const(_Eq3Command.WINDOW_OPEN_CONFIGURE, Int8ub))
    window_open_temperature: float = csfield(_Eq3Temperature(Int8ub))
    window_open_time: timedelta = csfield(_Eq3Duration(Int8ub))


@dataclass
class _ScheduleGetCommand(_Eq3Struct):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(_Eq3Command.SCHEDULE_GET, Int8ub))
    day: Eq3WeekDay = csfield(TEnum(Int8ub, Eq3WeekDay))


@dataclass
class _ModeSetCommand(_Eq3Struct):
    """Structure for mode set command."""

    cmd: int = csfield(Const(_Eq3Command.MODE_SET, Int8ub))
    mode: int = csfield(Int8ub)


@dataclass
class _AwaySetCommand(_ModeSetCommand):
    """Structure for away set command."""

    away_until: datetime = csfield(_Eq3AwayTime(Bytes(4)))


@dataclass
class _TemperatureSetCommand(_Eq3Struct):
    """Structure for temperature set command."""

    cmd: int = csfield(Const(_Eq3Command.TEMPERATURE_SET, Int8ub))
    temperature: float = csfield(_Eq3Temperature(Int8ub))


@dataclass
class _ScheduleSetCommand(_Eq3Struct):
    """Structure for schedule set command."""

    cmd: int = csfield(Const(_Eq3Command.SCHEDULE_SET, Int8ub))
    day: Eq3WeekDay = csfield(TEnum(Int8ub, Eq3WeekDay))
    hours: list[_ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(_ScheduleHourStruct))
    )


@dataclass
class _ComfortSetCommand(_Eq3Struct):
    """Structure for comfort set command."""

    cmd: int = csfield(Const(_Eq3Command.COMFORT_SET, Int8ub))


@dataclass
class _EcoSetCommand(_Eq3Struct):
    """Structure for eco set command."""

    cmd: int = csfield(Const(_Eq3Command.ECO_SET, Int8ub))


@dataclass
class _BoostSetCommand(_Eq3Struct):
    """Structure for boost set command."""

    cmd: int = csfield(Const(_Eq3Command.BOOST_SET, Int8ub))
    enable: bool = csfield(Flag)


@dataclass
class _LockSetCommand(_Eq3Struct):
    """Structure for lock set command."""

    cmd: int = csfield(Const(_Eq3Command.LOCK_SET, Int8ub))
    enable: bool = csfield(Flag)
