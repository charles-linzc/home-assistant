"""
Support for ZoneMinder Sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.zoneminder/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.zoneminder import DOMAIN as ZONEMINDER_DOMAIN
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zoneminder']

CONF_INCLUDE_ARCHIVED = "include_archived"

DEFAULT_INCLUDE_ARCHIVED = False

SENSOR_TYPES = {
    'all': ['Events'],
    'hour': ['Events Last Hour'],
    'day': ['Events Last Day'],
    'week': ['Events Last Week'],
    'month': ['Events Last Month'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_INCLUDE_ARCHIVED, default=DEFAULT_INCLUDE_ARCHIVED):
        cv.boolean,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=['all']):
        vol.All(cv.ensure_list, [vol.In(list(SENSOR_TYPES))]),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the ZoneMinder sensor platform."""
    include_archived = config.get(CONF_INCLUDE_ARCHIVED)

    zm_client = hass.data[ZONEMINDER_DOMAIN]
    monitors = zm_client.get_monitors()
    if not monitors:
        _LOGGER.warning('Could not fetch any monitors from ZoneMinder')

    sensors = []
    for monitor in monitors:
        sensors.append(ZMSensorMonitors(monitor))

        for sensor in config[CONF_MONITORED_CONDITIONS]:
            sensors.append(ZMSensorEvents(monitor, include_archived, sensor))

    sensors.append(ZMSensorRunState(zm_client))
    add_entities(sensors)


class ZMSensorMonitors(Entity):
    """Get the status of each ZoneMinder monitor."""

    def __init__(self, monitor):
        """Initialize monitor sensor."""
        self._monitor = monitor
        self._state = monitor.function.value

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} Status'.format(self._monitor.name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Update the sensor."""
        state = self._monitor.function
        if not state:
            self._state = None
        else:
            self._state = state.value


class ZMSensorEvents(Entity):
    """Get the number of events for each monitor."""

    def __init__(self, monitor, include_archived, sensor_type):
        """Initialize event sensor."""
        from zoneminder.monitor import TimePeriod
        self._monitor = monitor
        self._include_archived = include_archived
        self.time_period = TimePeriod.get_time_period(sensor_type)
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._monitor.name, self.time_period.title)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return 'Events'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Update the sensor."""
        self._state = self._monitor.get_events(
            self.time_period, self._include_archived)


class ZMSensorRunState(Entity):
    """Get the ZoneMinder run state."""

    def __init__(self, client):
        """Initialize run state sensor."""
        self._state = None
        self._client = client

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Run State'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Update the sensor."""
        self._state = self._client.get_active_state()
