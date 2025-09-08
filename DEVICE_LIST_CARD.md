# Connected Devices Card

This integration now includes a `connected devices` sensor that provides a list of all devices connected to your Cudy router. You can use this sensor to create custom cards that display your connected devices.

## Sensor Information

The sensor entity will be named: `sensor.<router_name>_connected_devices`

- **State**: Number of connected devices
- **Attributes**: Contains detailed information about all connected devices

## Device Information Available

Each device in the list includes:
- `hostname`: Device name
- `ip`: IP address
- `mac`: MAC address  
- `upload_speed`: Current upload speed (Mbps)
- `download_speed`: Current download speed (Mbps)
- `signal`: WiFi signal strength (for wireless devices)
- `online_time`: How long the device has been online
- `connection`: Connection type (wired/wireless)

## ⭐ Recommended: Clean List with Icons

```yaml
🌐 Connected Devices ({{ states('sensor.<entityId>') }})

{% set devices = state_attr('sensor.<entityId>', 'devices') %}
{% if devices %}
{% for device in devices %}
  {% set ot = device.online_time %}
  {% set time_display = '' %}

  {# Case: "X Day HH:MM:SS" format #}
  {% if 'Day' in ot %}
    {% set parts = ot.split() %}
    {% if parts | length >= 3 %}
      {% set days = parts[0] | int %}
      {% set time_parts = parts[2].split(':') %}
      {% set hours = (time_parts[0] | int(0)) %}
      {% set minutes = (time_parts[1] | int(0)) %}
      {# days #}
      {% if days > 0 %}{% set time_display = days|string + 'd' %}{% endif %}
      {# hours #}
      {% if hours > 0 %}
        {% if time_display %}{% set time_display = time_display + ' ' %}{% endif %}
        {% set time_display = time_display + hours|string + 'h' %}
      {% endif %}
      {# minutes #}
      {% if minutes > 0 %}
        {% if time_display %}{% set time_display = time_display + ' ' %}{% endif %}
        {% set time_display = time_display + minutes|string + 'm' %}
      {% endif %}
      {% if time_display == '' %}{% set time_display = '<1m' %}{% endif %}
    {% else %}
      {% set time_display = ot %}
    {% endif %}

  {# Case: "HH:MM" format #}
  {% elif ':' in ot %}
    {% set time_parts = ot.split(':') %}
    {% if time_parts | length >= 2 %}
      {% set hours = (time_parts[0] | int(0)) %}
      {% set minutes = (time_parts[1] | int(0)) %}
      {% if hours > 0 %}{% set time_display = hours|string + 'h' %}{% endif %}
      {% if minutes > 0 %}
        {% if time_display %}{% set time_display = time_display + ' ' %}{% endif %}
        {% set time_display = time_display + minutes|string + 'm' %}
      {% endif %}
      {% if time_display == '' %}{% set time_display = '<1m' %}{% endif %}
    {% else %}
      {% set time_display = ot %}
    {% endif %}
  {% else %}
    {% set time_display = ot %}
  {% endif %}

  {% set connection_lower = device.connection.lower() %}
  {% if 'wired' in connection_lower %}
    {% set connection_icon = 'mdi:ethernet' %}
  {% elif '2.4' in connection_lower or '2g' in connection_lower %}
    {% set connection_icon = 'mdi:signal-2g' %}
  {% else %}
    {% set connection_icon = 'mdi:signal-5g' %}
  {% endif %}
- <ha-icon icon="{{ connection_icon }}" style="width: 16px; height: 16px;"></ha-icon> **{{ device.hostname }}** ({{ device.ip }}) - {{ time_display }}
{% endfor %}
{% else %}
📵 No devices connected
{% endif %}
```



## Example Card Configurations

### 1. Simple Entities Card
```yaml
type: entities
title: Connected Devices
entities:
  - sensor.cudy_router_connected_devices
```

### 2. Custom Template Card (using card-templater)
```yaml
type: custom:card-templater
card:
  type: entities
  title: "Connected Devices ({{ states('sensor.cudy_router_connected_devices') }})"
  entities:
    - entity: sensor.cudy_router_connected_devices
      name: "Device Count"
entities:
  - this
```

### 3. Markdown Card with Device List
```yaml
type: markdown
title: Connected Devices
content: |
  {% set devices = state_attr('sensor.cudy_router_connected_devices', 'devices') %}
  {% if devices %}
  **Connected Devices: {{ states('sensor.cudy_router_connected_devices') }}**
  
  | Device | IP | Connection | Speed (↓/↑) |
  |--------|----|-----------:|------------:|
  {% for device in devices %}
  | {{ device.hostname }} | {{ device.ip }} | {{ device.connection }} | {{ device.download_speed }}/{{ device.upload_speed }} Mbps |
  {% endfor %}
  {% else %}
  No devices connected.
  {% endif %}
```

### 4. Custom Button Card (requires custom:button-card)
```yaml
type: custom:button-card
entity: sensor.cudy_router_connected_devices
name: Connected Devices
show_state: true
show_icon: true
icon: mdi:devices
styles:
  card:
    - height: auto
  custom_fields:
    devices:
      - position: absolute
      - top: 50px
      - left: 10px
      - width: calc(100% - 20px)
custom_fields:
  devices: |
    [[[
      const devices = entity.attributes.devices || [];
      let html = '<div style="font-size: 12px; text-align: left;">';
      devices.forEach(device => {
        html += `<div style="margin: 2px 0; padding: 4px; background: rgba(0,0,0,0.1); border-radius: 4px;">`;
        html += `<strong>${device.hostname}</strong> (${device.ip})<br>`;
        html += `${device.connection} - ↓${device.download_speed} ↑${device.upload_speed} Mbps`;
        if (device.signal && device.signal !== '---') {
          html += ` - Signal: ${device.signal}`;
        }
        html += '</div>';
      });
      html += '</div>';
      return html;
    ]]]
```

### 5. Auto-entities Card (requires custom:auto-entities)
```yaml
type: custom:auto-entities
card:
  type: entities
  title: Connected Devices
  show_header_toggle: false
filter:
  template: |
    {% set devices = state_attr('sensor.cudy_router_connected_devices', 'devices') %}
    {% for device in devices %}
    {%- set entity_id = 'sensor.cudy_router_connected_devices' -%}
    {{- {
      'entity': entity_id,
      'name': device.hostname + ' (' + device.ip + ')',
      'secondary_info': device.connection + ' - ↓' + (device.download_speed|string) + ' ↑' + (device.upload_speed|string) + ' Mbps',
      'icon': 'mdi:' + ('ethernet' if device.connection == 'wired' else 'wifi')
    } }},
    {% endfor %}
```

## Automation Example

You can also use this sensor in automations, for example to notify when a new device connects:

```yaml
automation:
  - alias: "New Device Connected"
    trigger:
      - platform: state
        entity_id: sensor.cudy_router_connected_devices
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state|int > trigger.from_state.state|int }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "New Device Connected"
          message: "Device count increased from {{ trigger.from_state.state }} to {{ trigger.to_state.state }}"
```

## Notes

- The sensor updates according to your configured scan interval (default: 15 seconds)
- Device information is cached to avoid excessive API calls
- The `last_updated` attribute shows when the data was last refreshed
- All speeds are shown in Mbps (Megabits per second)
