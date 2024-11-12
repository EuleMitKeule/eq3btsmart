from dataclasses import dataclass

from eq3btsmart.const import DEFAULT_AWAY_TEMP


@dataclass
class ThermostatConfig:
    mac_address: str
    away_temperature: float = DEFAULT_AWAY_TEMP
