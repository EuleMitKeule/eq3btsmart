"""Constants for the eq3btsmart library."""

from enum import IntEnum, StrEnum, auto
from typing import Self

from construct_typed import EnumBase, FlagsEnumBase

__all__ = [
    "EQ3_DEFAULT_AWAY_TEMP",
    "EQ3_DEFAULT_COMFORT_TEMP",
    "EQ3_DEFAULT_ECO_TEMP",
    "EQ3_DEFAULT_WINDOW_OPEN_TEMP",
    "EQ3_DEFAULT_WINDOW_OPEN_DURATION",
    "EQ3_DEFAULT_OFFSET_TEMP",
    "EQ3_MIN_TEMP",
    "EQ3_MAX_TEMP",
    "EQ3_OFF_TEMP",
    "EQ3_ON_TEMP",
    "EQ3_MIN_OFFSET",
    "EQ3_MAX_OFFSET",
    "DEFAULT_CONNECTION_TIMEOUT",
    "DEFAULT_COMMAND_TIMEOUT",
    "Eq3WeekDay",
    "Eq3OperationMode",
    "Eq3Preset",
    "Eq3Event",
]

"""The initial away temperature in degrees Celsius."""
EQ3_DEFAULT_AWAY_TEMP = 12.0

"""The initial comfort temperature in degrees Celsius."""
EQ3_DEFAULT_COMFORT_TEMP = 21.0

"""The initial eco temperature in degrees Celsius."""
EQ3_DEFAULT_ECO_TEMP = 17.0

"""The initial window open temperature in degrees Celsius."""
EQ3_DEFAULT_WINDOW_OPEN_TEMP = 12.0

"""The initial window open duration in minutes."""
EQ3_DEFAULT_WINDOW_OPEN_DURATION = 15

"""The initial offset temperature in degrees Celsius."""
EQ3_DEFAULT_OFFSET_TEMP = 0.0

"""The minimum temperature that is still displayed as a temperature in degrees Celsius."""
EQ3_MIN_TEMP = 5.0

"""The maximum temperature that is still displayed as a temperature in degrees Celsius."""
EQ3_MAX_TEMP = 29.5

"""The off temperature in degrees Celsius."""
EQ3_OFF_TEMP = 4.5

"""The on temperature in degrees Celsius."""
EQ3_ON_TEMP = 30.0

"""The minimum offset temperature in degrees Celsius."""
EQ3_MIN_OFFSET = -3.5

"""The maximum offset temperature in degrees Celsius."""
EQ3_MAX_OFFSET = 3.5

"""The default connection timeout in seconds."""
DEFAULT_CONNECTION_TIMEOUT = 10

"""The default command timeout in seconds."""
DEFAULT_COMMAND_TIMEOUT = 5


class Eq3Event(StrEnum):
    """Event type enumeration."""

    CONNECTED = auto()
    DISCONNECTED = auto()
    DEVICE_DATA_RECEIVED = auto()
    STATUS_RECEIVED = auto()
    SCHEDULE_RECEIVED = auto()


class Eq3OperationMode(IntEnum):
    """Operation mode enumeration."""

    AUTO = 0x00
    MANUAL = 0x40
    OFF = 0x49
    ON = 0x7B
    AWAY = 0x80


class Eq3Preset(IntEnum):
    """Preset mode enumeration."""

    COMFORT = 0
    ECO = 1


class Eq3WeekDay(EnumBase):
    """Week day enumeration."""

    SATURDAY = 0
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 3
    WEDNESDAY = 4
    THURSDAY = 5
    FRIDAY = 6

    @classmethod
    def from_index(cls, index: int) -> Self:
        """Return the enum value for the given index.

        Args:
            index: The index of the week day starting with 0 for Monday.

        Returns:
            The corresponding enum value.
        """
        adjusted_index = index + 2 if index < 5 else index - 5
        return cls(adjusted_index)


class _Eq3Characteristic(StrEnum):
    """Characteristics enumeration."""

    WRITE = "3fa4585a-ce4a-3bad-db4b-b8df8179ea09"
    NOTIFY = "d0e8434d-cd29-0996-af41-6c90f4e0eb2a"


class _Eq3Command(EnumBase):
    """Command type enumeration."""

    ID_GET = 0x00
    ID_RETURN = 0x01
    INFO_RETURN = 0x02
    INFO_GET = 0x03
    SCHEDULE_SET = 0x10
    COMFORT_ECO_CONFIGURE = 0x11
    OFFSET_CONFIGURE = 0x13
    WINDOW_OPEN_CONFIGURE = 0x14
    SCHEDULE_GET = 0x20
    SCHEDULE_RETURN = 0x21
    MODE_SET = 0x40
    TEMPERATURE_SET = 0x41
    COMFORT_SET = 0x43
    ECO_SET = 0x44
    BOOST_SET = 0x45
    LOCK_SET = 0x80


class _Eq3StatusFlags(FlagsEnumBase):
    """Status flag enumeration."""

    AUTO = 0x00
    MANUAL = 0x01
    AWAY = 0x02
    BOOST = 0x04
    DST = 0x08
    WINDOW = 0x10
    LOCKED = 0x20
    UNKNOWN = 0x40
    LOW_BATTERY = 0x80
