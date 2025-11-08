from Backend.calendar.cal_api import *
from Backend.calendar.cal_tools import *


calendar_id = "cal_OODZTUtc1Y"

create_recurring_events(calendar_id, "Test Meeting", datetime(2025, 11, 9, 9, 0), datetime(2025, 11, 9, 9, 10), occurrences=5, hour_interval=24)

