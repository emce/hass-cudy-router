from __future__ import annotations
import os
import sys

from custom_components.hass_cudy_router.const import OPTIONS_DEVICELIST

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from custom_components.hass_cudy_router.parser import *


from pathlib import Path

import pytest

# Adjust this import if your parser lives elsewhere
from custom_components.hass_cudy_router.parser import parse_system_info


def _read_fixture(rel_path: str) -> str:
    """Read an HTML fixture as UTF-8 text."""
    root = Path(__file__).resolve().parent.parent  # project root (…/hass-cudy-router)
    return (root / rel_path).read_text(encoding="utf-8")


def test_parse_system_info_from_fixture_system_html():
    html = _read_fixture("tests/html/system.html")

    data = parse_system_info(html)

    assert isinstance(data, dict), "parse_system_info() should return a dict"
    assert data, "parse_system_info() returned an empty dict"
    possible_keys = {
        "firmware",
        "hardware",
        "uptime"
    }
    assert (
        possible_keys.intersection(data.keys())
    ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"

    assert data["firmware"] == "2.3.15-20250805-113843"
    assert data["hardware"] == "WR6500 V1.0"
    assert data["uptime"] == "08:09:48"


def test_parse_mesh_info_from_fixture_system_html():
    html = _read_fixture("tests/html/mesh.html")

    data = parse_mesh_info(html)

    assert isinstance(data, dict), "parse_mesh_info() should return a dict"
    assert data, "parse_mesh_info() returned an empty dict"
    possible_keys = {
        "mesh_network",
        "mesh_units"
    }
    assert (
        possible_keys.intersection(data.keys())
    ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"

    assert data["mesh_network"] == "Mesh_5456"
    assert data["mesh_units"] == "2"


def test_parse_lan_info_from_fixture_system_html():
    html = _read_fixture("tests/html/lan.html")

    data = parse_lan_info(html)

    assert isinstance(data, dict), "parse_lan_info() should return a dict"
    assert data, "parse_lan_info() returned an empty dict"
    possible_keys = {
        "lan_ip"
    }
    assert (
        possible_keys.intersection(data.keys())
    ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"

    assert data["lan_ip"] == "192.168.178.1"


def test_parse_wan_info_from_fixture_system_html():
    html = _read_fixture("tests/html/wan.html")

    data = parse_wan_info(html)

    assert isinstance(data, dict), "parse_wan_info() should return a dict"
    assert data, "parse_wan_info() returned an empty dict"
    possible_keys = {
        "wan_type",
        "wan_ip",
        "wan_uptime",
        "wan_public_ip",
        "wan_dns"
    }
    assert (
        possible_keys.intersection(data.keys())
    ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"

    assert data["wan_type"] == "DHCP client"
    assert data["wan_ip"] == "192.168.10.150"
    assert data["wan_uptime"] == "08:26:31"
    assert data["wan_public_ip"] == "83.238.165.41 *"
    assert data["wan_dns"] == "8.8.8.8/62.233.233.233"


def test_parse_devices_info_from_fixture_system_html():
    html = _read_fixture("tests/html/devices.html")

    data = parse_devices(html)

    assert isinstance(data, dict), "parse_devices() should return a dict"
    assert data, "parse_devices() returned an empty dict"
    possible_keys = {
        "device_count",
        "wifi_24_device_count",
        "wifi_5_device_count",
        "wired_device_count",
        "mesh_device_count"
    }
    assert (
        possible_keys.intersection(data.keys())
    ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"

    assert data["device_count"] == "30"
    assert data["wifi_24_device_count"] == "4"
    assert data["wifi_5_device_count"] == "2"
    assert data["wired_device_count"] == "5"
    assert data["mesh_device_count"] == "19"


def test_parse_device_list_from_fixture_system_html():
    html = _read_fixture("tests/html/device_list.html")

    data = parse_device_list(html)

    assert isinstance(data, list), "parse_device_list() should return a list"
    assert data, "parse_device_list() returned an empty list"
    possible_keys = {
        "hostname",
        "ip",
        "mac",
        "upload_speed",
        "download_speed",
        "signal",
        "online_time",
        "connection",
        "connection_type"
    }

    assert len(data) == 31
    for device in data:
        assert (
            possible_keys.intersection(device.keys())
        ), f"Expected at least one of these keys to be parsed: {sorted(possible_keys)}"
