from dataclasses import dataclass
from typing import Self

from eq3btsmart.models.base_model import BaseModel
from eq3btsmart.structures import DeviceDataStruct


@dataclass
class DeviceData(BaseModel[DeviceDataStruct]):
    firmware_version: int
    device_serial: str

    @classmethod
    def from_struct(cls, struct: DeviceDataStruct) -> Self:
        return cls(
            firmware_version=struct.version,
            device_serial=struct.serial,
        )

    @classmethod
    def struct_type(cls) -> type[DeviceDataStruct]:
        return DeviceDataStruct
