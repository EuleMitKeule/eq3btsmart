from eq3btsmart._structures import _DeviceDataStruct
from eq3btsmart.models import DeviceData


def test_device_data_from_bytes() -> None:
    mock_struct = _DeviceDataStruct(
        version=1, serial="OEQ1750973", unknown_1=0, unknown_2=0, unknown_3=0
    )
    mock_bytes = mock_struct.to_bytes()

    device_data = DeviceData._from_bytes(mock_bytes)

    assert device_data.firmware_version == 1
    assert device_data.device_serial == "OEQ1750973"
