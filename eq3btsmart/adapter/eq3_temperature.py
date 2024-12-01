from construct_typed import Adapter, Context

from eq3btsmart.const import (
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
)
from eq3btsmart.exceptions import Eq3InvalidDataException


class Eq3Temperature(Adapter[int, int, float, float]):
    """Adapter to encode and decode temperature data."""

    def _encode(self, obj: float, ctx: Context, path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, ctx: Context, path: str) -> float:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: float) -> int:
        if value < EQ3BT_OFF_TEMP or value > EQ3BT_ON_TEMP:
            raise Eq3InvalidDataException(
                f"Temperature {value} out of range [{EQ3BT_OFF_TEMP}, {EQ3BT_ON_TEMP}]"
            )

        return int(value * 2)

    @classmethod
    def decode(cls, value: int) -> float:
        return float(value / 2)
