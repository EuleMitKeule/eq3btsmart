from dataclasses import dataclass
from datetime import time


@dataclass
class ScheduleHour:
    target_temperature: float
    next_change_at: time
