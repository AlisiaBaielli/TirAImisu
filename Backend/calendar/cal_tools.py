from datetime import datetime, timedelta
from Backend.calendar.cal_api import create_event
from Backend.medications.medication import Medication


DAY_PHASES_MAPPING = {
    "MORNING": {"start": (9, 0), "end": (9, 10)},
    "AFTERNOON": {"start": (13, 0), "end": (13, 10)},
    "EVENING": {"start": (18, 0), "end": (18, 10)},
}


def create_recurring_events(
    calendar_id,
    title,
    start_dt,
    end_dt,
    occurrences=5,
    hour_interval=24,
    description=None,
    location=None,
):
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
        current_start = start_dt + timedelta(hours=i * hour_interval)
        current_end = end_dt + timedelta(hours=i * hour_interval)

        event = create_event(
            calendar_id,
            title=title,
            start_dt=current_start,
            end_dt=current_end,
            description=description,
            location=location,
        )

        if event:
            print(
                f"Created event {i+1}/{occurrences}: {event['title']} on {current_start.date()}"
            )
        else:
            print(f"Failed to create event {i+1}/{occurrences}")


# TODO: THIS IS NOT NEEDED WE WILL SWITCH TO OUR JSON STUFF
def create_recurring_event_medication(
    calendar_id,
    medication: Medication,
    phase: str | int,
    start_dt: datetime,
    end_dt: datetime,
    occurrences,
    location=None,
):
    """
    Create a recurring event for medication.
    Parameters:
    - calendar_id: ID of the calendar
    - medication: Medication object (name, hour_interval, etc.)
    - phase: Phase of the day (MORNING, AFTERNOON, EVENING) or hour
    - occurrences: Number of medications to create
    - start_dt: datetime object for the first medication start
    - end_dt: datetime object for the first medication end
    - location: Optional event location
    """
    if isinstance(phase, int):
        start_hm = (phase, 0)
        end_hm = (phase, 10)
    else:
        assert phase in DAY_PHASES_MAPPING, "Invalid phase"
        start_hm = DAY_PHASES_MAPPING[phase]["start"]
        end_hm = DAY_PHASES_MAPPING[phase]["end"]
    start_dt = datetime(
        start_dt.year, start_dt.month, start_dt.day, start_hm[0], start_hm[1]
    )
    end_dt = datetime(end_dt.year, end_dt.month, end_dt.day, end_hm[0], end_hm[1])

    print(
        f"Creating recurring event for {medication.name} from {start_dt} to {end_dt} with {occurrences} occurrences, hour interval {medication.hour_interval}"
    )
    create_recurring_events(
        calendar_id,
        medication.name,
        start_dt,
        end_dt,
        occurrences,
        medication.hour_interval,
        medication.description,
        location,
    )
