import pytest

from eq3btsmart.thermostat import Thermostat
from tests.const import MAC_ADDRESS
from tests.mock_client import MockClient


@pytest.fixture(scope="function")
def mock_thermostat(monkeypatch: pytest.MonkeyPatch) -> Thermostat:
    monkeypatch.setattr("bleak.BleakClient", MockClient)
    monkeypatch.setattr("eq3btsmart.thermostat.BleakClient", MockClient)
    from bleak import BleakClient

    client = BleakClient(MAC_ADDRESS)

    assert isinstance(client, MockClient)
    assert not client.is_connected

    return Thermostat(MAC_ADDRESS)
