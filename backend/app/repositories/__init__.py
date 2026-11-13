"""SQL access layer.

Plain functions that take an open ``sqlite3.Connection`` as first argument.
They never open, commit or close connections: the caller (service) owns the
transaction. All SQL in the app lives here and in ``app.db``.
"""
from . import activities, calendar_feeds, garmin_accounts, planned_runs, smashrun_accounts, user_state, users

__all__ = ["activities", "calendar_feeds", "garmin_accounts", "planned_runs", "smashrun_accounts", "user_state", "users"]
