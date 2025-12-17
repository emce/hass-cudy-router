"""Helper methods to parse HTML returned by Cudy routers"""
import re
import logging
from typing import Any
from bs4 import BeautifulSoup
from datetime import datetime

from .const import SECTION_DETAILED, MODULE_LAN, MODULE_BANDWIDTH, MODULE_SYSTEM

_LOGGER = logging.getLogger(__name__)

def _get_clean_text(element) -> str:
    """Remove duplicity text"""
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
    """Parses transfer speed string and ALWAYS returns it in Mbps."""
    if not input_string:
        return 0.0
        
    if len(input_string) > 1 and len(input_string) % 2 == 0:
        mid = len(input_string) // 2
        if input_string[:mid] == input_string[mid:]:
            input_string = input_string[:mid]

    match = re.search(r"(\d+(?:\.\d+)?)\s*([kKmMgG]?)([bB])(?:ps|/s)?", input_string, re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            prefix = match.group(2).lower()
            unit_is_byte = match.group(3) == 'B' # 'B' = Byte, 'b' = bit
            
            if prefix == 'k': value *= 1000  # Pozor: u síťových rychlostí je k=1000, ne 1024
            elif prefix == 'm': value *= 1000000
            elif prefix == 'g': value *= 1000000000
            
            if unit_is_byte:
                value *= 8
                
            return round(value / 1000000.0, 2)
        except ValueError:
            pass
    return 0.0

def parse_lan_info(input_html: str) -> dict[str, Any]:
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

def parse_bandwidth_json(json_data: list, hw_version: str = "") -> dict[str, Any]:
    if not json_data or len(json_data) < 2:
        return {"upload_mbps": 0.0, "download_mbps": 0.0, "upload_total_gb": 0.0, "download_total_gb": 0.0}
    
    try:
        last, prev = json_data[-1], json_data[-2]
        delta_t = (last[0] - prev[0]) / 1000000.0
        if delta_t <= 0: delta_t = 1.0

        is_ax = "WR3000" in (hw_version or "")

        if is_ax:
            raw_rx_diff = last[3] - prev[3]
            raw_tx_diff = last[4] - prev[4]
            
            rx_mbps = round((raw_rx_diff * 8 * 45) / (delta_t * 1000), 2)
            tx_mbps = round((raw_tx_diff * 8 * 45) / (delta_t * 1000), 2)
            
            total_rx_gb = round(last[3] / 1024, 2)
            total_tx_gb = round(last[4] / 1024, 2)
        else:
            raw_rx_diff = last[1] - prev[1]
            raw_tx_diff = last[3] - prev[3]
            rx_mbps = round((raw_rx_diff * 8) / (delta_t * 1000000.0), 2)
            tx_mbps = round((raw_tx_diff * 8) / (delta_t * 1000000.0), 2)
            total_rx_gb = round(last[1] / (1024**3), 2)
            total_tx_gb = round(last[3] / (1024**3), 2)

        return {
            "download_mbps": max(0.0, rx_mbps),
            "upload_mbps": max(0.0, tx_mbps),
            "download_total_gb": max(0.0, total_rx_gb),
            "upload_total_gb": max(0.0, total_tx_gb)
        }
    except Exception:
        return {"upload_mbps": 0.0, "download_mbps": 0.0, "upload_total_gb": 0.0, "download_total_gb": 0.0}

def _parse_ac1200_style(soup: BeautifulSoup) -> list[dict]:
    devices = []
    for br in soup.find_all("br"): br.replace_with("\n")
    rows = soup.find_all("tr", id=re.compile(r"^cbi-table-\d+"))
    for row in rows:
        try:
            ip, mac = "Unknown", "Unknown"
            ipmac_div = row.find("div", id=re.compile(r"-ipmac$"))
            if ipmac_div:
                parts = ipmac_div.get_text(strip=True, separator="\n").split("\n")
                def clean(s):
                    s = s.strip()
                    if len(s) > 1 and len(s) % 2 == 0 and s[:len(s)//2] == s[len(s)//2:]:
                        return s[:len(s)//2]
                    return s
                if len(parts) >= 1: ip = clean(parts[0])
                if len(parts) >= 2: mac = clean(parts[1])
            
            hostname_raw = _get_clean_text(row.find("div", id=re.compile(r"-hostnamexs$")))
            if not hostname_raw or "Unknown" in hostname_raw:
                hostname = ip
            else:
                hostname = hostname_raw

            speed_div = row.find("div", id=re.compile(r"-speed$"))
            up_s, down_s = "0", "0"
            if speed_div:
                s_parts = speed_div.get_text(strip=True, separator="\n").split("\n")
                if len(s_parts) >= 2: up_s, down_s = s_parts[0], s_parts[1]

            devices.append({
                "hostname": hostname, "ip": ip, "mac": mac,
                "up_speed": parse_speed(up_s), "down_speed": parse_speed(down_s),
                "signal": _get_clean_text(row.find("div", id=re.compile(r"-signal$"))),
                "online": _get_clean_text(row.find("div", id=re.compile(r"-online$"))),
                "connection": _get_clean_text(row.find("div", id=re.compile(r"-iface$"))),
            })
        except: continue
    return devices

def parse_devices(input_html: str, device_list_str: str, previous_devices: dict[str, Any] = None) -> dict[str, Any]:
    soup = BeautifulSoup(input_html, "html.parser")
    devices = _parse_ac1200_style(soup)
    data = {"device_count": {"value": len(devices)}}
    
    all_devs = []
    for d in devices:
        all_devs.append({
            "hostname": d["hostname"], "ip": d["ip"], "mac": d["mac"],
            "upload_speed": d["up_speed"], "download_speed": d["down_speed"],
            "signal": d["signal"], "online_time": d["online"], "connection": d["connection"],
        })
    
    data["connected_devices"] = {
        "value": len(devices), 
        "attributes": {"devices": all_devs, "device_count": len(devices), "last_updated": datetime.now().isoformat()}
    }
    
    if devices:
        top_down = max(devices, key=lambda i: i.get("down_speed", 0))
        data["top_downloader_speed"] = {"value": top_down.get("down_speed")}
        data["top_downloader_hostname"] = {"value": top_down.get("hostname")}
        top_up = max(devices, key=lambda i: i.get("up_speed", 0))
        data["top_uploader_speed"] = {"value": top_up.get("up_speed")}
        data["top_uploader_hostname"] = {"value": top_up.get("hostname")}
        data["total_down_speed"] = {"value": sum(d.get("down_speed", 0) for d in devices)}
        data["total_up_speed"] = {"value": sum(d.get("up_speed", 0) for d in devices)}
    
    return data
