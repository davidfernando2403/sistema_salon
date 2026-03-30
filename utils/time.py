from datetime import datetime
from zoneinfo import ZoneInfo

PERU_TZ = ZoneInfo("America/Lima")

def ahora_peru():
    dt = datetime.now(PERU_TZ)
    return dt.replace(tzinfo=None)

def hoy_peru():
    return ahora_peru().date()