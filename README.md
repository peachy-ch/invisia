# Invisia Home Assistant Integration

Custom Home Assistant integration for **Invisia EV charging stations** with RFID support.

This integration exposes **clean, stable Home Assistant entities** for charging status, power, energy, and charging mode.
It follows modern HA patterns (`DataUpdateCoordinator`, `select` entities, config flows, migrations).

It explicitly avoids dumping raw Invisia API payloads into entity states, because that breaks Home Assistant.

---

## Features

### Charging Mode Control (Select Entity)

Charging mode is controlled via a **select entity**:

```
select.charging_mode
```

Available options:
- `instant`
- `optimized`
- `disabled`

This replaces the old switch-based implementation.

The old switch entity is **deprecated and removed**.

---

### Sensors

| Entity | Description | Unit |
|------|------------|------|
| `sensor.charging_power` | Current charging power | kW |
| `sensor.energy_charged` | Total energy charged | kWh |
| `sensor.status` | Charger status (charging / plugged / idle) | – |
| `sensor.rfid_profile` | Active RFID profile | – |

Design goals:
- Short, stable state values
- No oversized states
- Detailed data only in attributes

---

### API Resilience

The Invisia backend frequently returns HTML error pages (500 / 400) instead of JSON.

This integration:
- Detects non-JSON responses
- Logs a warning
- Keeps the last valid data
- Does **not** mark entities unavailable

This prevents dashboard flicker and entity churn.

---

## Installation

### Manual

1. Copy the integration to:
   ```
   config/custom_components/invisia
   ```
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **Invisia**

---

## Configuration

Configured entirely via the UI.

Required:
- Invisia account email
- Invisia account password
- Installation ID
- RFID ID

Credentials are stored securely in Home Assistant’s config entry storage.

---

## Dashboard Example

```yaml
tap_action:
  action: call-service
  service: select.select_option
  service_data:
    entity_id: select.charging_mode
    option: optimized
```

---

## Migration Notes

### v1 → v2
- Switch entities removed
- `select.charging_mode` introduced
- Sensors simplified and stabilised
- Migration handler included

If you still see orphaned entities, Home Assistant is remembering your past mistakes.

---

## Debugging

```bash
grep -i invisia home-assistant.log
```

Warnings about non-JSON responses are expected.

---

## Disclaimer

Community integration.
Not affiliated with Invisia.
The charger is fine. The API is moody.

---

## License

MIT
