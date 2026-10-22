"""
Central configuration for the scheduler.
Edit dates / time slots / people here; everything else derives from this file.
"""

from datetime import date

DRP = {
    "student_name": "Neil Sharma",
    "title": "Machine Unlearning via Curvature-Aware Gradient Ascent",
    "short_title": "Caffeine",
    "department": "Department of Computer Science",
    "school": "School of Computer and Data Sciences, University of Oregon",
    "advisor": "Dr. Suyash Gupta",
    "committee": [
        {"name": "Dr. Ram Durairajan", "role": "Committee Member"},
        {"name": "Dr. Thanh H. Nguyen", "role": "Committee Member"},
        {"name": "Dr. Suyash Gupta", "role": "Advisor & Committee Member"},
    ],
    "format": (
        "A public presentation open to the department, followed by a "
        "private questioning session with the committee."
    ),
    "duration_hours": 2,
    "contact_email": "neilshar@uoregon.edu",
}

# Window in which committee members can mark availability.
SCHEDULE_WINDOW = {
    "start": date(2026, 11, 2),
    "end": date(2026, 12, 8),
    # Monday=0 … Sunday=6 (Python convention). Mon–Thu (advisor unavailable Fridays).
    "allowed_weekdays": {0, 1, 2, 3},
    # Holidays / days to skip: the whole Thanksgiving week (Nov 23–27).
    "excluded_dates": {date(2026, 11, d) for d in range(23, 28)},
}

# Members mark availability in 1-hour cells between DAY_START and DAY_END (24h).
# 9 / 17 => cells 9–10 AM through 4–5 PM. The dashboard then finds every
# `duration_hours`-long window (e.g. 10 AM–12 PM) where everyone is free.
DAY_START_HOUR = 9
DAY_END_HOUR = 17

# Start hour of each 1-hour cell: 9, 10, …, 16.
SLOT_START_HOURS = list(range(DAY_START_HOUR, DAY_END_HOUR))

TIME_ZONE_LABEL = "Pacific Time (Eugene, OR)"
