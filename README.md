# Invisia Home Assistant Integration (Unofficial)

This is an **unofficial Home Assistant integration** for the Invisia EV charging platform.

It connects Home Assistant to the Invisia web backend, exposes charging and RFID data,
and allows switching between **Optimised** and **Immediate** charging modes.

This integration is based on **observed behaviour of the Invisia web application**
(`https://app.invisia.ch`). Invisia does **not** publish official API documentation.

⚠️ **All identifiers, IDs, emails, and examples in this document are fictitious.**

---

## Features

- Authenticates against Invisia cloud backend
- Reads:
  - RFID charging profile (`optimised` / `instant`)
  - Current charging power (W)
  - Energy charged (kWh)
  - Charging station state (`noCar`, charging, etc.)
  - Plugged-in state (from EVSE, not vehicle API)
- Exposes:
  - Sensors (power, energy, profile, status)
  - Binary sensor: **car plugged in**
  - Switch: **optimised charging**
- Designed for dashboards and wall displays (Google Nest / tablet friendly)

---

## Data Source

All data is fetched from the Invisia web application backend:

```
https://app.invisia.ch
```

---

## Installation

Copy the `invisia` folder into:

```
/config/custom_components/invisia
```

Restart Home Assistant and add the integration via the UI.

---

## Configuration

### Required Fields

| Field | Description |
|------|------------|
| Email | Invisia account email |
| Password | Invisia account password |
| Facility ID | Invisia installation ID |
| RFID ID | RFID identifier |

### Optional (Recommended)

| Field | Description |
|------|------------|
| user_id | Invisia user ID |
| charging_station_id | Charging station ID (required for plug detection) |

---

## Locating Configuration Values on invisia.ch

1. Log in at:

```
https://app.invisia.ch
```

2. Open browser developer tools:
   - Network tab
   - Enable *Preserve log*
   - Filter by **Fetch / XHR**

### Facility ID

Look for requests such as:

```
/api/cockpit/installations/1234/...
```

➡️ `1234` is the **Facility ID**.

---

### RFID ID

Look for:

```
/api/cockpit/installations/1234/rfids/5678
```

➡️ `5678` is the **RFID ID**.

---

### User ID (optional)

In the same responses you may see:

```json
"user": {
  "id": 42,
  "email": "user@example.com"
}
```

➡️ `42` is the **user_id**.

---

### Charging Station ID (important)

Look for requests like:

```
/api/cockpit/installations/1234/charging_stations/90001
```

or payloads containing:

```json
"charging_station": {
  "id": 90001,
  "device_id": 7
}
```

➡️ Use **`id`**, not `device_id`.

Without this value, the integration cannot determine whether a car is plugged in.

---

## Exposed Entities

### Sensors

- `sensor.invisia_rfid_profile`
- `sensor.invisia_rfid_power`
- `sensor.invisia_rfid_energy_charged`
- `sensor.invisia_rfid_status`

### Binary Sensors

- `binary_sensor.invisia_car_plugged_in`

### Switches

- `switch.invisia_optimised_charging`
  - **ON** → Optimised charging
  - **OFF** → Immediate charging

---

## Charging Logic

- **Plugged in**
  ```
  charging_status != "noCar"
  ```

- **Charging**
  ```
  current_power_flow > ~50 W
  ```

The logic reflects the **actual EVSE state**, not the vehicle API.

---

## Observed API (Unofficial)

### Base URL
```
https://app.invisia.ch
```

### Login
```
POST /api/authentication/token/
```

### RFID Status
```
GET /api/cockpit/installations/{installation_id}/rfids/{rfid_id}
```

### Update RFID Profile
```
PATCH /api/cockpit/installations/{installation_id}/rfids/{rfid_id}
```

### Charging Station Detail
```
GET /api/cockpit/installations/{installation_id}/charging_stations/{charging_station_id}
```

---

## Notes & Warnings

- Cloud-based integration
- No official API support
- API may change without notice
- Not affiliated with or endorsed by Invisia

---

## License

MIT
