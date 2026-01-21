"""Provides the backend for a Cudy router"""
import hashlib
import time
import logging
import requests
from typing import Any
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from .const import MODULE_DEVICES, MODULE_LAN, MODULE_SYSTEM, OPTIONS_DEVICELIST, MODULE_MESH, MODULE_WAN
from .parser import parse_devices, parse_lan_info, parse_system_info, parse_mesh_info, parse_wan_info, parse_device_list

_LOGGER = logging.getLogger(__name__)

class CudyRouter:
    def __init__(self, hass, protocol, host, username, password):
        self.protocol = protocol
        self.host = host
        self.username = username
        self.password = password
        self.hass = hass
        self.auth_cookie = None

    def get_cookie_header(self, force_auth: bool) -> str:
        if not force_auth and self.auth_cookie:
            return f"sysauth={self.auth_cookie}"
        if self.authenticate():
            return f"sysauth={self.auth_cookie}"
        return ""

    def authenticate(self) -> bool:
        login_url = f"{self.protocol}://{self.host}/cgi-bin/luci"
        try:
            resp = requests.get(login_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            def extract(name):
                tag = soup.find("input", {"name": name})
                return tag["value"] if tag and tag.has_attr("value") else ""
            _csrf = extract("_csrf")
            token = extract("token")
            salt = extract("salt")
        except Exception as e:
            _LOGGER.error("Error retrieving login page: %s", e)
            return False

        zonename = str(dt_util.DEFAULT_TIME_ZONE)
        timeclock = str(int(time.time()))
        
        if salt:
            hashed = hashlib.sha256((self.password + salt).encode()).hexdigest()
            if token:
                hashed = hashlib.sha256((hashed + token).encode()).hexdigest()
            luci_password = hashed
        else:
            luci_password = self.password

        body = {"_csrf": _csrf, "token": token, "salt": salt, "zonename": zonename, 
                "timeclock": timeclock, "luci_language": "en", "luci_username": self.username, 
                "luci_password": luci_password}
        body = {k: v for k, v in body.items() if v}

        try:
            response = requests.post(login_url, timeout=30, data=body, allow_redirects=False)
            if response.ok:
                cookie = SimpleCookie()
                cookie.load(response.headers.get("set-cookie"))
                if cookie.get("sysauth"):
                     self.auth_cookie = cookie.get("sysauth").value
                     return True
        except: pass
        return False

    def get(self, url: str) -> str:
        retries = 2
        while retries > 0:
            retries -= 1
            data_url = f"{self.protocol}://{self.host}/cgi-bin/luci/{url}"
            headers = {"Cookie": self.get_cookie_header(False)}
            try:
                response = requests.get(data_url, timeout=30, headers=headers, allow_redirects=False)
                if response.status_code == 403:
                    if self.authenticate(): continue
                    else: break
                if response.ok: return response.text
            except: pass
        return ""

    async def get_data(self, hass, options: dict[str, Any], previous_data: dict[str, Any] = None) -> dict[str, Any]:
        data = {}

        raw_system_page = await hass.async_add_executor_job(self.get, "admin/system/status?detail=1")
        data[MODULE_SYSTEM] = parse_system_info(raw_system_page)
        raw_mesh_status = await hass.async_add_executor_job(self.get, "admin/network/mesh/status?detail=1")
        data[MODULE_MESH] = parse_mesh_info(raw_mesh_status)
        raw_wan_status = await hass.async_add_executor_job(self.get, "admin/network/wan/status?detail=1")
        data[MODULE_WAN] = parse_wan_info(raw_wan_status)
        raw_lan_status = await hass.async_add_executor_job(self.get, "admin/network/lan/status?detail=1")
        data[MODULE_LAN] = parse_lan_info(raw_lan_status)
        raw_devices_status = await hass.async_add_executor_job(self.get, "admin/network/devices/status?detail=1")
        data[MODULE_DEVICES] = parse_devices(raw_devices_status)
        raw_dev = await hass.async_add_executor_job(self.get, "admin/network/devices/status?detail=1")
        data[MODULE_DEVICES] = parse_devices(raw_dev)
        raw_device_list = await hass.async_add_executor_job(self.get, "admin/network/devices/devlist?detail=1")
        data[MODULE_DEVICES][OPTIONS_DEVICELIST] = parse_device_list(raw_device_list)

        return data

    def post(self, url: str, data: dict[str, Any]) -> bool:
        """POST to a LuCI endpoint with authentication."""
        headers = {"Cookie": self.get_cookie_header(False)}

        try:
            response = requests.post(
                f"{self.protocol}://{self.host}{url}",
                headers=headers,
                data=data,
                timeout=30,
                allow_redirects=False,
            )
            return response.ok or response.status_code in (301, 302, 303)
        except Exception as err:
            _LOGGER.error("POST request failed: %s", err)
            return False

    def reboot(self) -> bool:
        """Trigger a router reboot via LuCI."""
        try:
            html = self.get("admin/system/reboot")
            soup = BeautifulSoup(html, "html.parser")

            token_input = soup.find("input", {"name": "token"})
            token = token_input.get("value") if token_input else None
            if not token:
                return False

            payload = {
                "token": token,
                "timeclock": str(int(time.time())),
                "cbi.submit": "1",
                "cbi.apply": "OK",
            }

            return self.post("/cgi-bin/luci/admin/system/reboot/reboot", payload)

        except Exception as err:
            _LOGGER.error("Failed to reboot router: %s", err)
            return False

    async def async_reboot(self, hass: HomeAssistant) -> bool:
        """Async wrapper for reboot()."""
        return await hass.async_add_executor_job(self.reboot)

