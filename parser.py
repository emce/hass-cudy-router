"""Helper methods to parse HTML returned by Cudy routers"""
import re
import logging
from typing import Any
from bs4 import BeautifulSoup
from datetime import datetime

from .const import SECTION_DETAILED, MODULE_LAN, MODULE_BANDWIDTH, MODULE_SYSTEM

_LOGGER = logging.getLogger(__name__)

def parse_speed(input_string: str) -> float:
    """Parses transfer speed string (universal)."""
    if not input_string:
        return 0.0
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
        if div:
            # Hledame prvni <p> tag, abychom se vyhli duplicitam (mobile vs desktop view)
            p = div.find("p")
            if p:
                return p.get_text(strip=True)
            # Fallback pokud tam <p> neni
            return div.get_text(strip=True)
        return "Unknown"

    data["ip_address"] = get_text_by_id("cbi-table-1-data")
    data["subnet_mask"] = get_text_by_id("cbi-table-2-data")
    data["gateway"] = get_text_by_id("cbi-table-3-data")
    data["dns"] = get_text_by_id("cbi-table-4-data")
    data["connected_time"] = get_text_by_id("cbi-table-5-data")
    return data

def parse_system_info(input_html: str) -> dict[str, Any]:
    """Parses Firmware and Hardware version by finding specific text nodes."""
    if not input_html: return {"firmware": "Unknown", "hardware": "Unknown"}
    soup = BeautifulSoup(input_html, "html.parser")
    data = {"firmware": "Unknown", "hardware": "Unknown"}
    
    # Hledáme přímo element obsahující text "HW:"
    # Používáme lambda funkci pro vyhledání textu, který obsahuje 'HW:'
    hw_elem = soup.find(string=lambda text: text and "HW:" in text)
    if hw_elem:
        # Odstraníme "HW:" a mezery okolo
        # Příklad: "HW: WR1200E V1.0" -> "WR1200E V1.0"
        clean_text = hw_elem.replace("HW:", "").strip()
        if clean_text:
            data["hardware"] = clean_text

    # Hledáme přímo element obsahující text "FW:"
    fw_elem = soup.find(string=lambda text: text and "FW:" in text)
    if fw_elem:
        # Příklad: "FW: 2.4.12-20250704..." -> "2.4.12-20250704..."
        clean_text = fw_elem.replace("FW:", "").strip()
        if clean_text:
            data["firmware"] = clean_text
            
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
        
        # Structure: [TIME, RXB, RXP, TXB, TXP]
        
        # 1. Calculate Speed
        time_delta = last[0] - prev[0]
        if time_delta > 0:
            rx_rate = (last[1] - prev[1]) * 1_000_000 / time_delta
            tx_rate = (last[3] - prev[3]) * 1_000_000 / time_delta
            rx_mbps = round((rx_rate * 8) / 1_000_000, 2)
            tx_mbps = round((tx_rate * 8) / 1_000_000, 2)
        else:
            rx_mbps = 0.0
            tx_mbps = 0.0
            
        # 2. Calculate Total (GB)
        total_rx_gb = round(last[1] / 1024 / 1024 / 1024, 2)
        total_tx_gb = round(last[3] / 1024 / 1024 / 1024, 2)

        return {
            "download_mbps": rx_mbps,
            "upload_mbps": tx_mbps,
            "download_total_gb": total_rx_gb,
            "upload_total_gb": total_tx_gb
        }

    except Exception as e:
        _LOGGER.error("Error parsing bandwidth JSON: %s", e)
        return {
            "upload_mbps": 0.0, "download_mbps": 0.0,
            "upload_total_gb": 0.0, "download_total_gb": 0.0
        }

def _parse_ac1200_style(soup: BeautifulSoup) -> list[dict]:
    """Parser logic specific for Cudy AC1200 (table based with IDs)."""
    devices = []
    
    for br in soup.find_all("br"):
        br.replace_with("\n")

    rows = soup.find_all("tr", id=re.compile(r"^cbi-table-\d+"))
    if not rows: return [] 

    for row in rows:
        try:
            ip = "Unknown"
            mac = "Unknown"
            hostname = "Unknown"
            connection = "Unknown"
            up_speed_str = "0"
            down_speed_str = "0"
            signal = "---"
            online = "---"

            ipmac_div = row.find("div", id=re.compile(r"-ipmac$"))
            if ipmac_div:
                text = ipmac_div.get_text(strip=True, separator="\n")
                parts = text.split("\n")
                if len(parts) >= 1: ip = parts[0].strip()
                if len(parts) >= 2: mac = parts[1].strip()

            host_div = row.find("div", id=re.compile(r"-hostnamexs$"))
            if host_div:
                text = host_div.get_text(strip=True, separator="\n")
                parts = text.split("\n")
                if len(parts) > 0: hostname = parts[0].strip()

            if hostname.lower() == "unknown" and ip != "Unknown":
                hostname = ip

            speed_div = row.find("div", id=re.compile(r"-speed$"))
            if speed_div:
                text = speed_div.get_text(strip=True, separator="\n")
                parts = text.split("\n")
                if len(parts) >= 2:
                    up_speed_str = parts[0].strip()
                    down_speed_str = parts[1].strip()

            sig_div = row.find("div", id=re.compile(r"-signal$"))
            if sig_div: signal = sig_div.get_text(strip=True)

            online_div = row.find("div", id=re.compile(r"-online$"))
            if online_div: online = online_div.get_text(strip=True)

            iface_div = row.find("div", id=re.compile(r"-iface$"))
            if iface_div: connection = iface_div.get_text(strip=True)

            if mac != "Unknown" or ip != "Unknown":
                devices.append({
                    "hostname": hostname, "ip": ip, "mac": mac,
                    "up_speed": parse_speed(up_speed_str),
                    "down_speed": parse_speed(down_speed_str),
                    "signal": signal, "online": online, "connection": connection,
                })
        except Exception: continue
    return devices

def get_all_devices(input_html: str) -> list[dict[str, Any]]:
    if not input_html: return []
    soup = BeautifulSoup(input_html, "html.parser")
    devices = _parse_ac1200_style(soup)
    return devices if devices else []

def parse_devices(input_html: str, device_list_str: str, previous_devices: dict[str, Any] = None) -> dict[str, Any]:
    devices = get_all_devices(input_html)
    data = {"device_count": {"value": len(devices)}}
    
    def time_to_minutes(time_str):
        if not time_str or time_str == "---": return 999999
        try:
            parts = time_str.split(":")
            if len(parts) == 3: return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 2: return int(parts[0])
        except (ValueError, IndexError): pass
        return 999999
    
    devices.sort(key=lambda d: time_to_minutes(d.get("online", "---")))
    
    all_devices_formatted = []
    for device in devices:
        all_devices_formatted.append({
            "hostname": device.get("hostname", "Unknown"),
            "ip": device.get("ip", "Unknown"),
            "mac": device.get("mac", "Unknown"),
            "upload_speed": device.get("up_speed", 0),
            "download_speed": device.get("down_speed", 0),
            "signal": device.get("signal", "---"),
            "online_time": device.get("online", "---"),
            "connection": device.get("connection", "Unknown"),
        })
    
    data["connected_devices"] = {
        "value": len(devices), 
        "attributes": {
            "devices": all_devices_formatted,
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
        # Default empty values
        data["top_downloader_speed"] = {"value": 0}
        data["top_downloader_hostname"] = {"value": "None"}
        data["top_uploader_speed"] = {"value": 0}
        data["top_uploader_hostname"] = {"value": "None"}
        data["total_down_speed"] = {"value": 0}
        data["total_up_speed"] = {"value": 0}
        
    return data
