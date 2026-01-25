# Invisia Home Assistant Integration

This Home Assistant custom integration provides first‑class support for **Invisia EV charging infrastructure**, with a focus on **RFID‑based charging**, **explicit entity modelling**, and **robust handling of backend edge cases**.

The integration is designed to align closely with the Invisia data model while presenting clean, predictable entities in Home Assistant. All entities are clearly namespaced with the `invisia_` prefix to avoid ambiguity and collisions with other integrations.

---

## Key Design Goals

- Clear, explicit entity names (no generic `sensor.status`)
- Accurate modelling of Invisia charging modes
- Centralised API access via a coordinator
- Graceful handling of partial API failures
- Stable behaviour across Home Assistant restarts and upgrades

---

## Supported Platforms

The integration currently provides the following Home Assistant platforms:

```python
PLATFORMS = ["sensor", "select"]
```

Binary switches have been intentionally removed in favour of a proper multi‑state control model.

---

## Entities

All entities are prefixed with **`invisia_`**.

### Charging Mode Control

Charging mode is exposed as a **select entity**, reflecting the true three‑state nature of the Invisia system.

```
select.invisia_charging_mode
```

Supported options:
- `instant`
- `optimized`
- `disabled`

Changing the selected option immediately updates the RFID charging profile through the Invisia API.

---

### Sensors

#### Charging Status

```
sensor.invisia_charging_status
```

Represents the current charging state as reported by Invisia.

Typical values:
- `charging`
- `carPluggedIn`
- `idle`
- `unknown`

This sensor is intended to be used for Lovelace conditionals and automations.

---

#### Charging Power

```
sensor.invisia_charging_power
```

- Unit: **kW**
- Updated continuously while charging
- Reports `0` when no power is flowing

The conversion from watts to kilowatts is handled inside the integration.

---

#### Energy Charged

```
sensor.invisia_energy_charged
```

- Unit: **kWh**
- Total energy charged during the current session, when available

---

## Architecture

### Data Update Coordinator

All API interaction is handled by a single `DataUpdateCoordinator`.

- Entities subscribe to coordinator updates
- No entity performs direct API calls
- Partial API failures do not block other data from updating

This ensures consistent behaviour even when parts of the Invisia backend are unavailable.

---

## API Error Handling

The Invisia backend may occasionally return:
- HTTP 500 responses
- HTML error pages instead of JSON

The integration handles this by:
- Ignoring non‑JSON responses for statistics endpoints
- Logging warnings instead of raising fatal errors
- Continuing to update core charging status

Expected log message example:

```
Invisia stats returned non‑JSON (status=500). Ignoring.
```

This behaviour is intentional and considered normal.

---

## Installation

### HACS (Recommended)

1. Add this repository as a **custom HACS integration**
2. Install **Invisia**
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

---

## Configuration

The configuration flow will prompt for:

- Invisia account email
- Invisia account password
- Installation ID
- RFID ID
- Optional user ID
- Optional charging station ID

Credentials are stored securely using Home Assistant config entries.

---

## Migration

The integration includes a migration handler.

When upgrading from earlier versions:
- Legacy switch entities are removed
- Generic entity names are replaced with `invisia_*`
- Select entities replace binary controls

Successful migration is logged explicitly.

---

## Lovelace Usage Notes

### Google Nest / Cast Dashboards

Google Nest Hub dashboards rendered via Cast support **only core Lovelace cards**.

Custom cards such as:
- `custom:button-card`
- `card-mod`

will not render.

For Nest displays, use built‑in cards such as:
- `tile`
- `button`
- `entities`

---

## Logging

To enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.invisia: debug
    custom_components.invisia.coordinator: debug
```

---

## Limitations

- Availability of historical statistics depends on Invisia backend stability
- Google Cast dashboards cannot render custom cards
- Some statistics may be temporarily unavailable during backend maintenance

---

## Disclaimer

This is an unofficial Home Assistant integration and is not affiliated with Invisia AG.
---

## Getting the IDs from the Invisia portal (installation / RFID / charging station)

The portal UI does not consistently show the internal IDs you need for API calls, but they *are* visible in the browser's Network log.

1. Log in to https://app.invisia.ch
2. Open Developer Tools → **Network**
3. Reload the page, then filter requests for: `statistics`, `rfid`, `charging`

### Installation ID
Look for a request like:

`/api/statistics/<installation_id>/rfid/<rfid_id>?start=...&end=...`

The number after `/api/statistics/` is the **installation ID**.

### RFID ID
Either:
- it’s shown in the UI name (e.g. “Invisia RFID 2476”), or
- it appears in URLs as `/rfid/<rfid_id>`.

### Charging station ID (optional)
If you want the **Car plugged in** binary sensor, find charging-station calls such as:
- `/api/v2/installations/<installation_id>/charging-stations`
- `/api/v2/charging-stations/<charging_station_id>`

The station `id` is the **charging station ID**.

---

## Installation via HACS

1. In Home Assistant, open **HACS → Integrations**
2. Menu (⋮) → **Custom repositories**
3. Add the repo: https://github.com/peachy-ch/invisia/ (Category: **Integration**)
4. Install **Invisia** and restart Home Assistant
5. Add the integration: **Settings → Devices & Services → Add integration → Invisia**
6. Enter: email, password, installation ID, RFID ID (and optionally charging station ID)

---

## Entities

The integration creates two devices when configured with both RFID and charging station IDs:

### Invisia RFID <rfid_id>
- **Select:** charging mode
- **Sensors:** charging power (kW), energy charged (kWh), RFID profile, status
- Attributes may include “energy sourced today” and recent journal entries (when available)

### Invisia Charging Station <charging_station_id> (optional)
- **Binary sensor:** car plugged in

---

## Example dashboard card (button-card)

A minimal example that cycles charging mode on tap:

```yaml
tap_action:
  action: call-service
  service: select.select_option
  service_data:
    entity_id: select.invisia_rfid_2476_charging_mode
    option: |
      [[[
        const cur = (states['select.invisia_rfid_2476_charging_mode']?.state || '').toLowerCase();
        if (cur === 'instant') return 'optimized';
        if (cur === 'optimized') return 'disabled';
        return 'instant';
      ]]]
```

---

## Troubleshooting

### Stats endpoint returns HTML / 500
The Invisia statistics endpoint can sometimes return an HTML error page (500). The integration logs a warning and continues; core status/power should still update.

### Old/orphaned entities
If you previously had legacy entities (e.g. `sensor.rfid_power`) they can remain in the entity registry.

Preferred cleanup:
- **Settings → Devices & Services → Entities**, search for the old entity IDs, then delete/disable them.

If the UI won’t let you (or they’re invisible):
1. Stop Home Assistant
2. Back up `.storage/`
3. Remove the stale entries from `.storage/core.entity_registry`
4. Start Home Assistant

### Polling interval / rate limits
The coordinator polls every 30 seconds by default. If your Invisia account is rate-limited to 1 request/minute, increase the interval (see `coordinator.py`).

---

## Disclaimer

Unofficial integration. Invisia can change their portal API at any time.
