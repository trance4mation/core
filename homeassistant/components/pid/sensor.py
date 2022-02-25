"""PID trip resolver sensor."""
from __future__ import annotations

import datetime
from http import HTTPStatus
import logging

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_API_TOKEN, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    ATTRIBUTION,
    DEFAULT_NAME,
    LIMIT,
    MIN_TIME_BETWEEN_UPDATES,
    RESOURCE,
    ROUTES,
    STATION_ID,
    WALK_DELAY,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_TOKEN): cv.string,
        vol.Required(STATION_ID): cv.string,
        vol.Optional(ROUTES): cv.string,
        vol.Optional(LIMIT, default=10): cv.positive_int,
        vol.Optional(WALK_DELAY, default=0): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the PID sensor."""
    name = config.get(CONF_NAME)
    station_id = config.get(STATION_ID)
    api_token = config.get(CONF_API_TOKEN)
    routes = config.get(ROUTES)
    limit = config.get(LIMIT)
    walk_delay: int = config.get(WALK_DELAY) or 0

    parameters = {"ids": station_id, "limit": limit, "minutesBefore": -walk_delay}
    headers = {
        "x-access-token": api_token,
        "Content-Type": "application/json; charset=utf-8",
    }

    rest = PidData(RESOURCE, parameters, headers, routes)
    response = requests.get(RESOURCE, params=parameters, headers=headers, timeout=10)

    if response.status_code != HTTPStatus.OK:
        _LOGGER.error("Check API token and connection to Golemio: %s", response.text)
        return

    rest.update()
    add_entities(
        [
            PidNextDepartureTimeSensor(rest, name),
            PidAdditionalDepartureTimesSensor(rest, name),
        ],
        True,
    )


class PidNextDepartureTimeSensor(SensorEntity):
    """Representation of an PID sensor."""

    def __init__(self, rest, name):
        """Initialize the sensor."""
        self.rest = rest
        self._name = name + " (next departure)"
        self._state = None
        self._attrs = {"data_source": ATTRIBUTION}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return other attributes of the sensor."""
        return self._attrs

    def update(self):
        """Update current conditions."""
        self.rest.update()
        value = self.rest.data
        self._state = value[0]["arrival"]
        self._attrs["delay"] = value[0]["delay"]
        self._attrs["route"] = value[0]["route"]


class PidAdditionalDepartureTimesSensor(SensorEntity):
    """Representation of an PID sensor."""

    def __init__(self, rest, name):
        """Initialize the sensor."""
        self.rest = rest
        self._name = name + " (additional departures)"
        self._state = None
        self._attrs = {"data_source": ATTRIBUTION}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return other attributes of the sensor."""
        return self._attrs

    def update(self):
        """Update current conditions."""
        self.rest.update()
        value = self.rest.data
        self._state = value[1]["arrival"]
        self._attrs["delay"] = value[1]["delay"]
        self._attrs["route"] = value[1]["route"]


class PidData:
    """Get data from golemio.cz."""

    def __init__(self, resource, parameters, headers, routes):
        """Initialize the data object."""
        self._resource = resource
        self._parameters = parameters
        self._headers = headers
        self._routes_list = routes.split(" ")
        self.data = None

    @staticmethod
    def distiller(trip):
        """Map trip data to a more efficient form."""
        arrival = trip["arrival_timestamp"]["scheduled"]
        arrival_str = datetime.datetime.fromisoformat(arrival).strftime("%H:%M")
        return {
            "arrival": arrival_str,
            "route": trip["route"]["short_name"],
            "delay": trip["delay"]["minutes"] if trip["delay"]["is_available"] else 0,
        }

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from golemio.cz."""
        try:
            response = requests.get(
                self._resource,
                params=self._parameters,
                headers=self._headers,
                timeout=10,
            )
            if response.status_code != HTTPStatus.OK:
                response.raise_for_status()
            data = response.json()
            trips = [
                trip
                for trip in data
                if trip["route"]["short_name"] in self._routes_list
            ]
            result_iterator = map(PidData.distiller, trips)
            self.data = list(result_iterator)
        except requests.exceptions.HTTPError as err:
            _LOGGER.error("Check API token and connection to Golemio: %s", err)
            self.data = None
            return False
