from eq3btsmart.models.device_data import DeviceData
from eq3btsmart.structures import DeviceDataStruct


def test_device_data_from_bytes() -> None:
    mock_struct = DeviceDataStruct(
        version=1, serial="OEQ1750973", unknown_1=0, unknown_2=0, unknown_3=0
    )
    mock_bytes = mock_struct.to_bytes()

    device_data = DeviceData.from_bytes(mock_bytes)

    assert device_data.firmware_version == 1
    assert device_data.device_serial == "OEQ1750973"
