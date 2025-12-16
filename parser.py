"""Helper methods to parse HTML returned by Cudy routers"""
import re
import logging
from typing import Any
from bs4 import BeautifulSoup
from datetime import datetime

from .const import SECTION_DETAILED, MODULE_LAN, MODULE_BANDWIDTH, MODULE_SYSTEM

_LOGGER = logging.getLogger(__name__)

def _get_clean_text(element) -> str:
    """Pomocná funkce pro odstranění duplicitního textu (pro mobilní/desktop zobrazení)."""
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

def parse_speed(input_string: str) -> float:
    """Parses transfer speed string (universal)."""
    if not input_string:
        return 0.0
        
    if len(input_string) > 1 and len(input_string) % 2 == 0:
        mid = len(input_string) // 2
        if input_string[:mid] == input_string[mid:]:
            input_string = input_string[:mid]

    match = re.search(r"(\d+(?:\.\d+)?)\s*([kKmMgG]?bps)", input_string, re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            unit = match.group(2).lower()
            if "mbps" in unit: return value
            if "gbps" in unit: return value * 1024
            if "kbps" in unit: return round(value / 1024, 2)
            if "bps" in unit: return round(value / 1024 / 1024, 2)
        except ValueError:
            pass
    return 0.0

def parse_lan_info(input_html: str) -> dict[str, Any]:
    """Parses LAN status table from HTML."""
    if not input_html: return {}
    soup = BeautifulSoup(input_html, "html.parser")
    data = {}
    
    def get_text_by_id(element_id):
        div = soup.find("div", id=element_id)
        return _get_clean_text(div)

    data["ip_address"] = get_text_by_id("cbi-table-1-data")
    data["subnet_mask"] = get_text_by_id("cbi-table-2-data")
    data["gateway"] = get_text_by_id("cbi-table-3-data")
    data["dns"] = get_text_by_id("cbi-table-4-data")
    data["connected_time"] = get_text_by_id("cbi-table-5-data")
    return data

def parse_system_info(input_html: str) -> dict[str, Any]:
    """Parses Firmware and Hardware version from footer spans."""
    data = {"firmware": "Unknown", "hardware": "Unknown"}
    if not input_html: return data
    
    soup = BeautifulSoup(input_html, "html.parser")
    for span in soup.find_all("span"):
        text = span.get_text(strip=True)
        if "HW:" in text:
            data["hardware"] = text.replace("HW:", "").replace("|", "").strip()
        elif "FW:" in text:
            data["firmware"] = text.replace("FW:", "").replace("|", "").strip()
            
    return data

def parse_bandwidth_json(json_data: list) -> dict[str, Any]:
    """Calculates current speed AND total bytes from history JSON."""
    if not json_data or len(json_data) < 2:
        return {
            "upload_mbps": 0.0, "download_mbps": 0.0,
            "upload_total_gb": 0.0, "download_total_gb": 0.0
        }

    try:
        last = json_data[-1]
        prev = json_data[-2]
        time_delta = last[0] - prev[0]
        if time_delta > 0:
            rx_rate = (last[1] - prev[1]) * 1_000_000 / time_delta
            tx_rate = (last[3] - prev[3]) * 1_000_000 / time_delta
            rx_mbps = round((rx_rate * 8) / 1_000_000, 2)
            tx_mbps = round((tx_rate * 8) / 1_000_000, 2)
        else:
            rx_mbps = tx_mbps = 0.0
            
        total_rx_gb = round(last[1] / 1024 / 1024 / 1024, 2)
        total_tx_gb = round(last[3] / 1024 / 1024 / 1024, 2)

        return {
            "download_mbps": rx_mbps, "upload_mbps": tx_mbps,
            "download_total_gb": total_rx_gb, "upload_total_gb": total_tx_gb
        }
    except Exception as e:
        _LOGGER.error("Error parsing bandwidth JSON: %s", e)
        return {"upload_mbps": 0.0, "download_mbps": 0.0, "upload_total_gb": 0.0, "download_total_gb": 0.0}

def _parse_ac1200_style(soup: BeautifulSoup) -> list[dict]:
    """Parser logic for devices."""
    devices = []
    for br in soup.find_all("br"):
        br.replace_with("\n")

    rows = soup.find_all("tr", id=re.compile(r"^cbi-table-\d+"))
    for row in rows:
        try:
            ip = "Unknown"
            mac = "Unknown"
            
            ipmac_div = row.find("div", id=re.compile(r"-ipmac$"))
            if ipmac_div:
                text = ipmac_div.get_text(strip=True, separator="\n")
                parts = text.split("\n")
                def clean(s):
                    s = s.strip()
                    if len(s) > 1 and len(s) % 2 == 0 and s[:len(s)//2] == s[len(s)//2:]:
                        return s[:len(s)//2]
                    return s
                if len(parts) >= 1: ip = clean(parts[0])
                if len(parts) >= 2: mac = clean(parts[1])

            hostname = _get_clean_text(row.find("div", id=re.compile(r"-hostnamexs$")))
            
            # OPRAVA: Pokud je hostname "Unknown" nebo obsahuje "Unknown", použijeme jen IP
            if not hostname or hostname == "Unknown" or "Unknown" in hostname:
                hostname = ip

            speed_div = row.find("div", id=re.compile(r"-speed$"))
            up_s, down_s = "0", "0"
            if speed_div:
                s_parts = speed_div.get_text(strip=True, separator="\n").split("\n")
                if len(s_parts) >= 2:
                    up_s, down_s = s_parts[0], s_parts[1]

            devices.append({
                "hostname": hostname, "ip": ip, "mac": mac,
                "up_speed": parse_speed(up_s),
                "down_speed": parse_speed(down_s),
                "signal": _get_clean_text(row.find("div", id=re.compile(r"-signal$"))),
                "online": _get_clean_text(row.find("div", id=re.compile(r"-online$"))),
                "connection": _get_clean_text(row.find("div", id=re.compile(r"-iface$"))),
            })
        except Exception: continue
    return devices

def get_all_devices(input_html: str) -> list[dict[str, Any]]:
    if not input_html: return []
    soup = BeautifulSoup(input_html, "html.parser")
    return _parse_ac1200_style(soup)

def parse_devices(input_html: str, device_list_str: str, previous_devices: dict[str, Any] = None) -> dict[str, Any]:
    devices = get_all_devices(input_html)
    data = {"device_count": {"value": len(devices)}}
    
    def time_to_minutes(time_str):
        if not time_str or time_str == "Unknown" or time_str == "---": return 999999
        try:
            parts = time_str.split(":")
            if len(parts) == 3: return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 2: return int(parts[0])
        except (ValueError, IndexError): pass
        return 999999
    
    devices.sort(key=lambda d: time_to_minutes(d.get("online", "---")))
    
    all_devs = []
    for d in devices:
        all_devs.append({
            "hostname": d["hostname"],
            "ip": d["ip"],
            "mac": d["mac"],
            "upload_speed": d["up_speed"],
            "download_speed": d["down_speed"],
            "signal": d["signal"],
            "online_time": d["online"],
            "connection": d["connection"],
        })
    
    data["connected_devices"] = {
        "value": len(devices), 
        "attributes": {
            "devices": all_devs,
            "device_count": len(devices),
            "last_updated": datetime.now().isoformat(),
        }
    }
    
    if devices:
        top_down = max(devices, key=lambda i: i.get("down_speed", 0))
        data["top_downloader_speed"] = {"value": top_down.get("down_speed")}
        data["top_downloader_mac"] = {"value": top_down.get("mac")}
        data["top_downloader_hostname"] = {"value": top_down.get("hostname")}
        
        top_up = max(devices, key=lambda i: i.get("up_speed", 0))
        data["top_uploader_speed"] = {"value": top_up.get("up_speed")}
        data["top_uploader_mac"] = {"value": top_up.get("mac")}
        data["top_uploader_hostname"] = {"value": top_up.get("hostname")}

        data[SECTION_DETAILED] = {}
        device_list = [x.strip() for x in (device_list_str or "").split(",")]
        now_ts = datetime.now().timestamp()
        previous_detailed = (previous_devices or {}).get(SECTION_DETAILED, {}) if previous_devices else {}
        
        for device in devices:
            key = device.get("mac")
            if key not in device_list and device.get("hostname") in device_list:
                key = device.get("hostname")

            if key and key in device_list:
                prev = previous_detailed.get(key, {})
                device["last_seen"] = now_ts
                if prev.get("last_seen") and prev["last_seen"] > device["last_seen"]:
                      device["last_seen"] = prev["last_seen"]
                data[SECTION_DETAILED][key] = device
                
        for key in device_list:
            if key not in data[SECTION_DETAILED] and key in previous_detailed:
                data[SECTION_DETAILED][key] = previous_detailed[key]
                
        data["total_down_speed"] = {"value": sum(d.get("down_speed", 0) for d in devices)}
        data["total_up_speed"] = {"value": sum(d.get("up_speed", 0) for d in devices)}
    else:
        data["top_downloader_speed"] = {"value": 0}
        data["top_downloader_hostname"] = {"value": "None"}
        data["top_uploader_speed"] = {"value": 0}
        data["top_uploader_hostname"] = {"value": "None"}
        data["total_down_speed"] = {"value": 0}
        data["total_up_speed"] = {"value": 0}
        
    return data
