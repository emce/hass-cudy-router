# Cudy Router Integration for Home Assistant (Universal AC / AX)

A modern, fully UI-configured Home Assistant integration for Cudy routers, optimized and tested primarily with **WR6500**.

The integration is designed to work across AC and AX generations by automatically detecting router capabilities and adjusting parsing, scaling, and data interpretation accordingly.

WARNING:
This is a custom integration (not part of Home Assistant Core).
Home Assistant will display a warning about custom integrations — this is expected.

------------------------------------------------------------

KEY FEATURES

CONFIGURATION & UX
- UI Config Flow (no YAML required)
- Options Flow (change scan interval & tracked devices without re-adding)
- Multi-language UI (English & Polish included)
- Safe reboot action (button + service)

NETWORK & TRAFFIC MONITORING
- Real-time WAN throughput (download / upload speed in Mbps)
- Dynamic bandwidth scaling (AC vs AX models handled automatically)
- Total traffic counters (where supported)

DEVICE & CLIENT INTELLIGENCE
- Connected device counts:
  - Total
  - 2.4 GHz Wi-Fi
  - 5 GHz Wi-Fi
  - Wired
  - Mesh
- Detailed device tracker:
  - Connection type (2.4G / 5G / Wired)
  - Signal strength (dBm)
  - Online duration
- Optional per-device presence tracking (MAC-based)

SYSTEM & ROUTER HEALTH
- Router uptime
- Firmware version
- Hardware / mesh info
- LAN & WAN IPs
- WAN connection type & uptime

------------------------------------------------------------

INSTALLATION

IMPORTANT:
Integration domain: cudy_router
Folder name: hass_cudy_router

MANUAL INSTALLATION

1. Open Home Assistant config directory:
   config/custom_components/

2. Create folder:
   hass_cudy_router/

3. Copy repository files:

   custom_components/
     hass_cudy_router/
       __init__.py
       button.py
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
         pl.json

4. Restart Home Assistant.

------------------------------------------------------------

CONFIGURATION

INITIAL SETUP
1. Settings -> Devices & Services
2. Add Integration
3. Search for "Cudy Router"
4. Enter:
   - Protocol (http / https)
   - Router IP (default: 192.168.10.1)
   - Username
   - Password

OPTIONS (POST-SETUP)
After setup, click Configure on the integration to adjust:
- Scan interval (seconds)
- Tracked device MAC list (device_tracker)

------------------------------------------------------------

REBOOTING THE ROUTER

BUTTON ENTITY (RECOMMENDED)
- Entity: button.cudy_router_reboot
- Available on the router device page
- Manual action (safe UX)

SERVICE CALL
service: cudy_router.reboot

With multiple routers:
service: cudy_router.reboot
data:
  entry_id: YOUR_CONFIG_ENTRY_ID

------------------------------------------------------------

TRANSLATIONS

Included:
- English
- Polish

To add another language:
1. Copy translations/en.json
2. Rename to <lang>.json
3. Translate values only (keys must remain unchanged)

------------------------------------------------------------

CREDITS

Based on original work by:
https://github.com/armendkadrija/hass-cudy-router-wr3600

Extended with:
- Universal AC / AX parsing
- Modern Home Assistant architecture
- UI configuration & options flow
- Device tracker & reboot actions
- Full automated test coverage
