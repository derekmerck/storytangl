from datetime import datetime, timedelta

start_time = datetime.now()

def app_uptime() -> timedelta:
    return datetime.now() - start_time
