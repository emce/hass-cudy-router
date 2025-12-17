# Cudy Router Integration for Home Assistant (Universal AC/AX)

This is an enhanced custom integration for Cudy routers, specifically optimized and tested for **AC1200 (WR1200)** and **AX3000 (WR3000)** models. 

It features a smart `parser.py` that automatically detects the hardware version and adjusts data processing (scaling factors, JSON indexes, and HTML parsing) to provide accurate real-time statistics regardless of the router's architecture.

## 🚀 Enhanced Features & Sensors

Beyond basic device tracking, this integration provides dedicated entities for comprehensive network analysis:

### **Network Performance**
* **Dynamic Bandwidth Scaling:** Automatically detects if the router reports data in Bytes (AC series) or uses hardware-accelerated reporting (AX series).
* **Download/Upload Speed:** Real-time aggregate throughput in Mbps.
* **Total Data:** `sensor.download_total` & `sensor.upload_total` — Accumulative counters in GB.

### **Traffic Analysis**
* **Top Downloader/Uploader:** Identifies the device currently consuming the most bandwidth.
* **Detailed Device Tracker:** Monitoring connection type (2.4G/5G/Wired), signal strength ($dBm$), and session duration.

### **System Health & Info**
* **Uptime:** `sensor.connected_time` — How long the router has been running.
* **Hardware/Firmware Info:** Version tracking and LAN IP monitoring.

## 🛠 Installation

1. Open your Home Assistant `config/custom_components` directory.
2. Create a folder named `cudy_router`.
3. Copy all files from this repository into that folder.
   - The structure should look like:
     ```
     custom_components/
       cudy_router/
         __init__.py
         config_flow.py
         const.py
         coordinator.py
         device_tracker.py
         manifest.json
         parser.py
         router.py
         sensor.py
         strings.json
         translations/
           en.json
     ```
4. **Restart Home Assistant.**

## ⚙️ Configuration

1. Navigate to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Cudy Router**.
3. Enter the router's IP (default: `192.168.10.1`), username, and password.

## 📋 Dashboard Example (Wireless Clients)
To create a clean list of wireless devices (filtering out wired ones and avoiding duplicate IPs in the name), use a **Markdown Card**:

```yaml
type: markdown
content: |-
  | Zařízení (IP) | Typ | Signál | Čas |
  | :--- | :--- | :--- | :--- |
  {% for device in state_attr('sensor.connected_devices', 'devices') -%}
    {%- if device.connection != 'Wired' -%}
    | **{{ device.hostname }}** | {{ device.connection }} | {{ device.signal }} | {{ device.online_time }} |
    {% endif -%}
  {%- endfor %}
title: Cudy AP Kidsroom
```

## ⚠️ Model Specific Notes

* AX3000 (WR3000): Uses specific scaling factors to compensate for PPE hardware offload reporting.
* AC1200 (WR1200): Standardized Byte-level HTML/JSON parsing.
* LTE-specific sensors (SIM, 4G signal) are automatically hidden for standard Wi-Fi models to keep your entity list clean.

##  Credits
Based on the original work by [armendkadrija](https://github.com/armendkadrija/hass-cudy-router-wr3600). Enhanced with universal AC/AX parsing and advanced traffic sensors.
