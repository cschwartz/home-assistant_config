from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from xml.etree import ElementTree
import logging
from datetime import timedelta

from .fritzboxconnector import FritzBoxConnector

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)


class FritzCometThermostatState:
    def __init__(self, description):
        self._description = description

        self._id = self._description.get("identifier")
        self._name = self._description.find("name").text
        self._present = self._description.get("present") == "1"

        if self._present:
            self._currentTemperature = self._fromDescription("hkr/tist")
            self._targetTemperature = self._fromDescription("hkr/tsoll")
            self._comfortTemperature = self._fromDescription("hkr/komfort")
            self._economyTemperature = self._fromDescription("hkr/absenk")

    @property
    def is_thermostat(self):
        return True

    @property
    def is_present(self):
        return self._present

    @property
    def name(self):
        return self._name

    @property
    def currentTemperature(self):
        return self._currentTemperature

    @property
    def targetTemperature(self):
        return self._targetTemperature

    @property
    def comfortTemperature(self):
        return self._comfortTemperature

    @property
    def economyTemperature(self):
        return self._economyTemperature

    def _fromDescription(self, name, scale=2.0):
        return int(self._description.find(name).text) / scale

class FritzCometThermostatData(FritzBoxConnector):
    THERMOSTAT_BITMASK = 320

    def __init__(self, hostname, username, password):
        super().__init__(hostname, username, password)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        reply = self._get("/webservices/homeautoswitch.lua", params={
            "switchcmd": "getdevicelistinfos",
        })
        xml = ElementTree.fromstring(reply.text)

        self._devices = {d.get("identifier"): self.createDevice(d) for d in xml.findall("./device")}

    def createDevice(self, description):
        if int(description.get("functionbitmask")) == self.THERMOSTAT_BITMASK:
            return FritzCometThermostatState(description)
        else:
            return None

    def thermostatIds(self):
        return [k for (k, v) in self._devices.items() if v.is_thermostat]

    def device(self, searchId):
        return self._devices.get(searchId)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    hostname = config["hostname"]
    user = config["user"]
    password = config["password"]

    fritzBox = FritzCometThermostatData(hostname, user, password)

    sensors = []
    for deviceId in fritzBox.thermostatIds():
        sensors.append(FritzCometThermostatSensor(fritzBox, deviceId))

    try:
        fritzBox.update()
    except ValueError as e:
        _LOGGER.error("Error while updating Comet thermostats: %s", e)

    add_devices(sensors)

    return True


class FritzCometThermostatSensor(Entity):
    def __init__(self, data, deviceId):
        self._deviceId = deviceId
        self._data = data

        self.update()

    def update(self):
        self._data.update()
        self._device = self._data.device(self._deviceId)

    @property
    def name(self):
        return self._device.name

    @property
    def state(self):
        if self._device.is_present:
            return self._device.currentTemperature
        else:
            return "Offline"

    @property
    def unit_of_measurement(self):
        return TEMP_CELSIUS
