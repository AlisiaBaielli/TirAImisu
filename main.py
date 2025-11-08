from Backend.calendar.cal_api import *
from Backend.calendar.cal_tools import *
from Backend.medications.medication import Medication
from Backend.medications.repository import get_current_medications

calendar_id = "cal_OODZTUtc1Y"

# create_recurring_events(calendar_id, "Test Meeting", datetime(2025, 11, 9, 10, 0), datetime(2025, 11, 9, 10, 10), occurrences=5, hour_interval=24)

medications = get_current_medications()
for medication in medications:
    create_recurring_event_medication(calendar_id, medication, medication.time, datetime(2025, 11, 10, 9, 0), datetime(2025, 11, 10, 9, 10), 30)