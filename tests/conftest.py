from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice

from eq3btsmart.thermostat import Thermostat


@pytest.fixture(scope="function")
def thermostat() -> Thermostat:
    # Create mock details with adv attribute that Windows backend expects
    mock_details = MagicMock()
    mock_details.adv = MagicMock()  # Required for Windows backend

    thermostat_instance = Thermostat(
        BLEDevice("00:11:22:33:44:55", name="Test Device", details=mock_details)
    )
    dummy_client = MagicMock()
    dummy_client.connect = AsyncMock()
    dummy_client.start_notify = AsyncMock()
    dummy_client.disconnect = AsyncMock()
    dummy_client.write_gatt_char = AsyncMock()
    dummy_client.is_connected = False
    thermostat_instance._conn = dummy_client
    return thermostat_instance
