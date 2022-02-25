"""Constants for the PID trip resolver integration."""

from datetime import timedelta
from typing import Final

RESOURCE: Final = "https://api.golemio.cz/v2/departureboards"
STATION_ID: Final = "station_id"
WALK_DELAY: Final = "walk_delay"
LIMIT: Final = "limit"
ROUTES: Final = "routes"
ATTRIBUTION: Final = "Data provided by golemio.cz"
DEFAULT_NAME: Final = "PID trip resolver"
MIN_TIME_BETWEEN_UPDATES: Final = timedelta(seconds=30)
