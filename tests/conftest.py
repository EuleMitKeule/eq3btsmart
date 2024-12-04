import pytest

from eq3btsmart.thermostat import Thermostat


@pytest.fixture(scope="function")
def thermostat() -> Thermostat:
    return Thermostat("00:11:22:33:44:55")
