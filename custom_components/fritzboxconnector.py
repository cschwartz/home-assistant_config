from requests import get
from xml.etree import ElementTree
import hashlib

class FritzBoxConnector:
    def __init__(self, hostname, username, password):
        self._hostname = hostname
        self._username = username
        self._password = password
        self._sid = self._obtain_sid()

        self.update()

    def _get(self, endpoint, params):
        url = "{0}{1}".format(self._hostname, endpoint)
        fullParams = {**params, "sid": self._sid}
        reply = get(url, fullParams)
        if not reply.ok:
            self._sid = self._obtain_sid()
            reply = get(url, params)

        return reply

    def _obtain_sid(self):
        url = self._hostname + "/login_sid.lua"
        reply = get(url)
        xml = ElementTree.fromstring(reply.text)
        challenge = xml.find("Challenge").text
        response = hashlib.md5((challenge + "-" + self._password).encode("UTF-16LE")).hexdigest()
        reply = get(url, params={
            "username": self._username,
            "response": "{0}-{1}".format(challenge, response)
        })
        xml = ElementTree.fromstring(reply.text)
        sid = xml.find("SID").text
        if sid == "0000000000000000":
            msg = "Failed to authenticate with FritzBox '{0}' as user '{1}'".format(self._hostname, self._username)
            raise Exception(msg)
        return sid
