from app.matching import get_weekly_consistency as _weekly_consistency
from app.metrics import get_activities, get_monthly_volume, get_summary


def list_activities(limit: int = 100):
    return get_activities(limit=limit)


def summary():
    return get_summary()


def monthly_volume():
    return get_monthly_volume()


def weekly_consistency(tolerance_days: int = 1):
    return _weekly_consistency(tolerance_days=tolerance_days)
