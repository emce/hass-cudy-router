"""Provides the backend for a Cudy router"""
import hashlib
import time
import json
import logging
import requests
from typing import Any  # <--- TADY BYLA TA CHYBA
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
import homeassistant.util.dt as dt_util

from .const import MODULE_DEVICES, MODULE_LAN, MODULE_BANDWIDTH, MODULE_SYSTEM, OPTIONS_DEVICELIST
from .parser import parse_devices, parse_lan_info, parse_bandwidth_json, parse_system_info

_LOGGER = logging.getLogger(__name__)

class CudyRouter:
    """Represents a router and provides functions for communication."""

    def __init__(self, hass, host, username, password):
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
        login_url = f"http://{self.host}/cgi-bin/luci"
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
        
        plain_password = self.password
        if salt:
            hashed = hashlib.sha256((plain_password + salt).encode()).hexdigest()
            if token:
                hashed = hashlib.sha256((hashed + token).encode()).hexdigest()
            luci_password = hashed
        else:
            luci_password = plain_password

        body = {
            "_csrf": _csrf, "token": token, "salt": salt,
            "zonename": zonename, "timeclock": timeclock,
            "luci_language": "en", "luci_username": self.username,
            "luci_password": luci_password,
        }
        body = {k: v for k, v in body.items() if v}

        try:
            response = requests.post(
                login_url, timeout=30, 
                headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": ""}, 
                data=body, allow_redirects=False
            )
            if response.ok:
                cookie = SimpleCookie()
                cookie.load(response.headers.get("set-cookie"))
                if cookie.get("sysauth"):
                     self.auth_cookie = cookie.get("sysauth").value
                     return True
        except Exception:
            pass
        return False

    def get(self, url: str) -> str:
        retries = 2
        while retries > 0:
            retries -= 1
            data_url = f"http://{self.host}/cgi-bin/luci/{url}"
            headers = {"Cookie": f"{self.get_cookie_header(False)}"}
            try:
                response = requests.get(data_url, timeout=30, headers=headers, allow_redirects=False)
                if response.status_code == 403:
                    if self.authenticate(): continue
                    else: break
                if response.ok: return response.text
                else: break
            except Exception: pass
        return ""

    async def get_data(self, hass, options: dict[str, Any], previous_data: dict[str, Any] = None) -> dict[str, Any]:
        data = {}

        # 1. Connected Devices
        raw_dev = await hass.async_add_executor_job(self.get, "admin/network/devices/devlist?detail=1")
        prev_dev = previous_data.get(MODULE_DEVICES) if previous_data else None
        data[MODULE_DEVICES] = parse_devices(raw_dev, options and options.get(OPTIONS_DEVICELIST), prev_dev)

        # 2. LAN Status
        raw_lan = await hass.async_add_executor_job(self.get, "admin/network/lan/status?detail=1")
        data[MODULE_LAN] = parse_lan_info(raw_lan)

        # 3. System Info (z plné stránky)
        raw_system = await hass.async_add_executor_job(self.get, "admin/system/system")
        data[MODULE_SYSTEM] = parse_system_info(raw_system)

        # 4. Bandwidth
        try:
             raw_bw = await hass.async_add_executor_job(self.get, "admin/status/bandwidth?iface=eth0")
             if raw_bw:
                 data[MODULE_BANDWIDTH] = parse_bandwidth_json(json.loads(raw_bw))
             else:
                 data[MODULE_BANDWIDTH] = {}
        except Exception as e:
             _LOGGER.error("Failed to fetch bandwidth: %s", e)
             data[MODULE_BANDWIDTH] = {}

        return data
