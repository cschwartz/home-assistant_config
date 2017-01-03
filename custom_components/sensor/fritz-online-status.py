from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import logging
from datetime import timedelta

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)
REQUIREMENTS = ['https://bitbucket.org/kbr/fritzconnection/get/'
                '8171434b964b.zip'
                '#fritzconnection==0.5.1']

_LOGGER = logging.getLogger(__name__)

class FritzOnlineStatus(Entity):
    def __init__(self, data, name, attribute):
        self._data = data
        self._name = name
        self._attribute = attribute
        self.update()

    def update(self):
        self._data.update()
        self._value = self._data.attribute(self._attribute)

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._value

class FritzOnlineStatusData:
    def __init__(self, username, password, service, action):
        import fritzconnection
        self._service = service
        self._action = action
        self._fritzconnection = fritzconnection.FritzConnection(user=username, password = password)

        self.update()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self._data = self._fritzconnection.call_action(self._service, self._action)

    def attribute(self, attribute):
        return self._data[attribute]

def setup_platform(hass, config, add_devices, discovery_info=None):
    username = config["user"]
    password = config["password"]

    sensors = []

    for service, actions in config["metrics"].items():
        for action, fields in actions.items():
            data = FritzOnlineStatusData(username, password, service, action)
            for field, name in fields.items():
                sensors.append(FritzOnlineStatus(data, name, field))

    add_devices(sensors)
