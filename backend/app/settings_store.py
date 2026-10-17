"""Read/write the supervisor-editable settings (stored in the settings table)."""
import copy

from .extensions import db
from .models import Setting

DEFAULTS = {
    # Thresholds the alert engine uses. Lightning defaults come from the brief.
    "alert_rules": {
        "lightningRadiusMiles": 10,
        "lightningAllClearMinutes": 30,
        "floodRainInches": 2,
        "heatIndexF": 105,
        "windMph": 35,
        "hazardIndexAlert": 7.5,
    },
    # Next-day briefing: sent at localTime in each site's own time zone.
    "briefing_settings": {
        "enabled": True,
        "localTime": "18:00",
        "channels": {"email": True, "sms": True, "push": True},
        "recipients": ["crew", "supervisor"],
    },
}


def get_setting(key):
    row = db.session.get(Setting, key)
    value = copy.deepcopy(DEFAULTS[key])
    if row:
        value.update(row.value)
    return value


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    db.session.commit()
    return value
