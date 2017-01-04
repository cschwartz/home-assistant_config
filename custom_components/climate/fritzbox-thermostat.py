from homeassistant.const import TEMP_CELSIUS
from homeassistant.components.climate import ClimateDevice
from homeassistant.util import Throttle
from homeassistant.util.temperature import convert as convert_temperature

from xml.etree import ElementTree
import logging
from datetime import timedelta

from custom_components.fritzboxconnector import FritzBoxConnector

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)


class FritzBoxThermostatState:
    def __init__(self, description):
        self._description = description

        self._ain = self._description.get("identifier")
        self._name = self._description.find("name").text
        self._present = self._description.find("present").text == "1"

        self._currentTemperature = self._fromDescription("hkr/tist")
        self._targetTemperature = self._fromDescription("hkr/tsoll")
        self._comfortTemperature = self._fromDescription("hkr/komfort")
        self._economyTemperature = self._fromDescription("hkr/absenk")

    @property
    def ain(self):
        return self._ain

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
        if self._present:
            return int(self._description.find(name).text) / scale
        else:
            return None

class FritzBoxThermostatData(FritzBoxConnector):
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
            return FritzBoxThermostatState(description)
        else:
            return None

    def thermostatIds(self):
        return [k for (k, v) in self._devices.items() if v.is_thermostat]

    def device(self, searchId):
        return self._devices.get(searchId)

    def setTargetTemperature(self, device, newTargetTemperature):
        reply = self._get("/webservices/homeautoswitch.lua", params={
            "switchcmd": "sethkrtsoll",
            "ain": device.ain,
            "param": newTargetTemperature * 2.0
        })

        print(reply)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    hostname = config["hostname"]
    user = config["user"]
    password = config["password"]

    fritzBox = FritzBoxThermostatData(hostname, user, password)

    sensors = []
    for deviceId in fritzBox.thermostatIds():
        sensors.append(FritzBoxThermostat(fritzBox, deviceId))

    try:
        fritzBox.update()
    except ValueError as e:
        _LOGGER.error("Error while updating FritzBox Thermostats: %s", e)

    add_devices(sensors)

    return True


class FritzBoxThermostat(ClimateDevice):
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
    def current_temperature(self):
        return self._device.currentTemperature

    @property
    def target_temperature(self):
        return self._device.targetTemperature

    @property
    def min_temp(self):
        return convert_temperature(self._device.economyTemperature, TEMP_CELSIUS, self.temperature_unit)

    @property
    def max_temp(self):
        return convert_temperature(self._device.comfortTemperature, TEMP_CELSIUS, self.temperature_unit)

    def set_temperature(self, **kwargs):
        newTargetTemperature = kwargs["temperature"]
        self._data.setTargetTemperature(self._device, newTargetTemperature)

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS
