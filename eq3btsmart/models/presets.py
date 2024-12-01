from dataclasses import dataclass
from datetime import timedelta
from typing import Self

from eq3btsmart.models.base_model import BaseModel
from eq3btsmart.structures import PresetsStruct


@dataclass
class Presets(BaseModel[PresetsStruct]):
    window_open_temperature: float
    window_open_time: timedelta
    comfort_temperature: float
    eco_temperature: float
    offset_temperature: float

    @classmethod
    def from_struct(cls, struct: PresetsStruct) -> Self:
        return cls(
            window_open_temperature=struct.window_open_temp,
            window_open_time=struct.window_open_time,
            comfort_temperature=struct.comfort_temp,
            eco_temperature=struct.eco_temp,
            offset_temperature=struct.offset,
        )

    @classmethod
    def struct_type(cls) -> type[PresetsStruct]:
        return PresetsStruct
