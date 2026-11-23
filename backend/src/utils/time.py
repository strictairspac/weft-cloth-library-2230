from datetime import UTC, datetime, timedelta


def utc_time(seconds=0):
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec='seconds')
