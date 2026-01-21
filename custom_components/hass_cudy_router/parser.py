"""Helper methods to parse HTML returned by Cudy routers"""
import re
import logging
from typing import Any
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)
_UP_RE = re.compile(r"↑\s*([\d.]+)\s*([A-Za-z/]+)")
_DOWN_RE = re.compile(r"↓\s*([\d.]+)\s*([A-Za-z/]+)")

def _get_clean_text(element) -> str:
    if element is None:
        return "Unknown"
    p_tag = element.find("p")
    text = p_tag.get_text(strip=True) if p_tag else element.get_text(strip=True)
    if not text:
        return "Unknown"
    if len(text) > 1 and len(text) % 2 == 0:
        mid = len(text) // 2
        if text[:mid] == text[mid:]:
            return text[:mid]
    return text

def parse_system_info(input_html: str) -> dict[str, Any]:
    data = {"firmware": "Unknown", "hardware": "Unknown"}
    if not input_html: return data

    soup = BeautifulSoup(input_html, "html.parser")
    text = soup.get_text()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    unique_lines = list(dict.fromkeys(lines))
    hw_match = _get_info(unique_lines, "Hardware")
    if hw_match:
        data["hardware"] = hw_match

    fw_match = re.search(r"Firmware Version\s*([^\s|]+)", text)
    if fw_match:
        data["firmware"] = fw_match.group(1).strip()

    ut_match = _get_info(unique_lines, "Uptime")
    if ut_match:
        data["uptime"] = ut_match

    return data

def parse_mesh_info(input_html: str) -> dict[str, Any]:
    return _parse_lines(
        input_html=input_html,
        keys={
            "mesh_network": "Device Name",
            "mesh_units": "Mesh Units",
        }
    )

def parse_lan_info(input_html: str) -> dict[str, Any]:
    return _parse_lines(
        input_html=input_html,
        keys={
            "lan_ip": "IP Address"
        }
    )

def parse_wan_info(input_html: str) -> dict[str, Any]:
    return _parse_lines(
        input_html=input_html,
        keys={
            "wan_type": "Protocol",
            "wan_ip": "IP Address",
            "wan_uptime": "Connected Time",
            "wan_public_ip": "Public IP",
            "wan_dns": "DNS",
        }
    )

def parse_devices(input_html: str) -> dict[str, Any]:
    data = _parse_lines(
        input_html=input_html,
        keys={
            "device_count": "Devices",
            "wifi_24_device_count": "2.4G WiFi",
            "wifi_5_device_count": "5G WiFi",
            "wired_device_count": "Wired",
            "mesh_device_count": "Mesh",
        }
    )
    soup = BeautifulSoup(input_html, "html.parser")
    text = soup.get_text()
    dc_match = re.search(r"Devices\s*([^\s|]+)", text)
    if dc_match:
        data["device_count"] = dc_match.group(1).strip()
    return data

def parse_device_list(input_html: str) -> list[dict]:
    data = []
    soup = BeautifulSoup(input_html, "html.parser")
    table = soup.find("table", class_="table table-striped")
    if not table:
        return data

    # All rows with ids like "cbi-table-1", "cbi-table-2", ...
    for row in table.select("tbody tr[id^='cbi-table-']"):
        cols = row.find_all("td")

        # 0: index (No.)
        idx_cell = cols[0]
        idx = idx_cell.get_text(strip=True)

        # 1: hostname + connection type (Mesh / 2.4G WiFi / etc.)
        hostname_cell = cols[1]
        # take only the "desktop" version (hidden-xs) to avoid duplicates
        host_p = hostname_cell.find("p", class_="form-control-static hidden-xs")
        hostname = None
        conn_type = None
        if host_p:
            parts = [t.strip() for t in host_p.stripped_strings]
            if parts:
                hostname = parts[0]
            if len(parts) > 1:
                conn_type = parts[1]

        # 4: IP / MAC address
        ipmac_cell = cols[4]
        ipmac_p = ipmac_cell.find("p", class_="form-control-static hidden-xs")
        ip = mac = None
        if ipmac_p:
            ipmac_parts = [t.strip() for t in ipmac_p.stripped_strings]
            if ipmac_parts:
                ip = ipmac_parts[0]
            if len(ipmac_parts) > 1:
                mac = ipmac_parts[1]

        # 5 Upload/Download
        speed_p = cols[5].find("p", class_="form-control-static hidden-xs")
        upload = download = None
        upload_unit = download_unit = None
        if speed_p:
            speed_text = speed_p.get_text(" ")
            # Example: "0.00 Kbps 0.00 Kbps" but with arrows in between depending on parsing
            up_m = _UP_RE.search(speed_text)
            down_m = _DOWN_RE.search(speed_text)
            if up_m:
                upload = float(up_m.group(1))
                upload_unit = up_m.group(2)
            if down_m:
                download = float(down_m.group(1))
                download_unit = down_m.group(2)

        # 6: Signal
        signal_cell = cols[6]
        signal_p = signal_cell.find("p", class_="form-control-static hidden-xs")
        signal = signal_p.get_text(strip=True) if signal_p else None

        # 7: Duration / online
        online_cell = cols[7]
        online_p = online_cell.find("p", class_="form-control-static hidden-xs")
        online = online_p.get_text(strip=True) if online_p else None

        # 8: Internet toggle (fa-toggle-on / fa-toggle-off)
        internet_cell = cols[8]
        toggle_icon = internet_cell.find("i", class_=["fa-toggle-on", "fa-toggle-off"])
        internet_enabled = None
        if toggle_icon:
            internet_enabled = "fa-toggle-on" in toggle_icon.get("class", [])

        data.append(
            {
                "hostname": hostname,
                "ip": ip,
                "mac": mac,
                "upload_speed": upload + upload_unit if upload is not None else "0.00Kbps",
                "download_speed": download + download_unit if download is not None else "0.00Kbps",
                "signal": signal,
                "online_time": online,
                "connection": internet_enabled,
                "connection_type": conn_type,
            }
        )

    return data

def _parse_lines(
    input_html: str,
    keys: dict[str, str]
) -> dict[str, Any]:
    if not input_html:
        return {}

    result = {}
    for output_key, label in keys.items():
        result[output_key] = "N/A"

    soup = BeautifulSoup(input_html, "html.parser")
    text = soup.get_text()

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    unique_lines = list(dict.fromkeys(lines))

    for output_key, label in keys.items():
        match = _get_info(unique_lines, label)
        if match is not None:
            result[output_key] = match

    return result

def _get_info(lines: list[str], key: str) -> str | None:
    try:
        idx = lines.index(key)
        return lines[idx + 1]
    except (ValueError, IndexError):
        return None