"""SQL access layer.

Plain functions that take an open ``sqlite3.Connection`` as first argument.
They never open, commit or close connections: the caller (service) owns the
transaction. All SQL in the app lives here and in ``app.db``.
"""
from . import activities, calendar_feeds, garmin_accounts, planned_runs, smashrun_accounts, strava_accounts, sync_state, user_state, users, webhook_events

__all__ = ["activities", "calendar_feeds", "garmin_accounts", "planned_runs", "smashrun_accounts", "strava_accounts", "sync_state", "user_state", "users", "webhook_events"]
