from datetime import datetime, timedelta
from Backend.calendar.cal_api import create_event



DAY_PHASES_MAPPING ={
    "MORNING": {
        "start": (9, 0),
        "end": (9, 10)
    },
    "AFTERNOON": {
        "start": (13, 0),
        "end": (13, 10)
    },
    "EVENING": {
        "start": (18, 0),
        "end": (18, 10)
    }
}


def create_recurring_events(calendar_id, title, start_dt, end_dt, occurrences=5, hour_interval=24, description=None, location=None):
    """
    Create recurring events in a calendar.

    Parameters:
    - calendar_id: ID of the calendar
    - title: Event title
    - start_dt: datetime object for the first event start
    - end_dt: datetime object for the first event end
    - occurrences: Number of events to create
    - hour_interval: Number of hours between each event
    - description: Optional event description
    - location: Optional event location
    """
    for i in range(occurrences):
        current_start = start_dt + timedelta(hours=i*hour_interval)
        current_end   = end_dt + timedelta(hours=i*hour_interval)
        
        event = create_event(
            calendar_id,
            title=title,
            start_dt=current_start,
            end_dt=current_end,
            description=description,
            location=location
        )
        
        if event:
            print(f"Created event {i+1}/{occurrences}: {event['title']} on {current_start.date()}")
        else:
            print(f"Failed to create event {i+1}/{occurrences}")


def create_recurring_event_medication(calendar_id, title, phase, start_dt, end_dt, occurrences, hour_interval, description=None, location=None):
    """
    Create a recurring event for medication.
    Parameters:
    - calendar_id: ID of the calendar
    - title: Medication title
    - phase: Phase of the day (MORNING, AFTERNOON, EVENING)
    - start_dt: datetime object for the first medication start
    - end_dt: datetime object for the first medication end
    - occurrences: Number of medications to create
    - hour_interval: Number of hours between each medication
    """
    assert phase in DAY_PHASES_MAPPING, "Invalid phase"
    start_hm = DAY_PHASES_MAPPING[phase]["start"]
    end_hm = DAY_PHASES_MAPPING[phase]["end"]
    start_dt = datetime(start_dt.year, start_dt.month, start_dt.day, start_hm[0], start_hm[1])
    end_dt = datetime(end_dt.year, end_dt.month, end_dt.day, end_hm[0], end_hm[1])
    create_recurring_events(calendar_id, title, start_dt, end_dt, occurrences, hour_interval, description, location)
