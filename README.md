# Invisia Home Assistant Integration (Unofficial)

This is an **unofficial Home Assistant integration** for the Invisia EV charging platform.

It connects Home Assistant directly to the Invisia web backend, exposes charging and RFID data,
and allows switching between **Optimized** and **Instant** charging modes.

This integration is based on **observed and tested behaviour of the Invisia web application**
(`https://app.invisia.ch`). Invisia does **not** publish official API documentation.

---

## Features

- Authenticates against Invisia cloud backend
- Reads:
  - RFID charging profile (`optimized` / `instant`)
  - Current charging power (W)
  - Energy charged (kWh)
  - Charging station state (`noCar`, charging, etc.)
  - Plugged-in state (from EVSE, not vehicle API)
- Exposes:
  - Sensors (power, energy, profile, status)
  - Binary sensor: **car plugged in**
  - Switch: **optimized charging**
- Fully dashboard-compatible (Nest / tablet friendly)

---

## Data Source

All data is fetched from the Invisia web application backend:

```
https://app.invisia.ch
```

The integration uses the **same API endpoints as the official web UI**.
Authentication and requests behave like a browser session.

---

## Installation

### Manual Installation

1. Copy the `invisia` folder into:

```
/config/custom_components/invisia
```

2. Restart Home Assistant.

3. Go to:

```
Settings → Devices & Services → Add Integration → Invisia
```

---

## Configuration

### Required Fields

| Field | Description |
|-----|------------|
| Email | Invisia account email |
| Password | Invisia account password |
| Facility ID | Invisia installation ID |
| RFID ID | RFID identifier |

### Optional (Recommended)

| Field | Description |
|-----|------------|
| user_id | Invisia user ID |
| charging_station_id | Charging station ID (required for plug detection) |

---

## How to Find Configuration Values on invisia.ch

### 1. Log in to Invisia

```
https://app.invisia.ch
```

### 2. Open Developer Tools

- Chrome / Brave / Edge:
  - Right click → Inspect
  - Open **Network**
  - Enable **Preserve log**
  - Filter: **Fetch / XHR**

---

### Facility ID (installation_id)

Look for requests like:

```
/api/cockpit/installations/272/...
```

➡️ `272` is the Facility ID.

---

### RFID ID

Look for:

```
/api/cockpit/installations/272/rfids/2476
```

➡️ `2476` is the RFID ID.

---

### User ID (optional)

In the same response:

```json
"user": {
  "id": 1543,
  "email": "user@example.com"
}
```

➡️ `1543` is the user_id.

---

### Charging Station ID (important)

Look for:

```
/api/cockpit/installations/272/charging_stations/21401417
```

or payloads containing:

```json
"charging_station": {
  "id": 21401417,
  "device_id": 7
}
```

➡️ Use **`id`**, not `device_id`.

Without this value, the integration cannot detect whether a car is plugged in.

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

- `switch.invisia_optimized_charging`
  - **ON** → Optimized charging
  - **OFF** → Instant charging

---

## Charging Logic

- **Plugged in**
  - Derived from charging station status:
    ```
    charging_status != "noCar"
    ```

- **Charging**
  - Derived from measured power:
    ```
    current_power_flow > ~50 W
    ```

This reflects the **actual EVSE state**, independent of vehicle APIs.

---

## Observed API (Unofficial)

### Base URL

```
https://app.invisia.ch
```

---

### Authentication

#### Login

```
POST /api/authentication/token/
```

Body:
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Headers:
```
X-Installation-Id: <facility_id>
```

Response:
```json
{
  "access": "<JWT access token>"
}
```

---

#### Token Refresh

```
POST /api/authentication/token/refresh/
```

Uses HttpOnly cookies set during login.

---

### RFID Status

```
GET /api/cockpit/installations/{installation_id}/rfids/{rfid_id}
```

Payload may be returned either directly or wrapped:

```json
{
  "rfid": { ... },
  "stats": { ... }
}
```

Clients must normalize both forms.

---

### Set RFID Charging Profile

```
PATCH /api/cockpit/installations/{installation_id}/rfids/{rfid_id}
```

Body:
```json
{
  "id": 2476,
  "profile": "optimized"
}
```

Values:
- `optimized`
- `instant`

---

### Charging Station Detail

```
GET /api/cockpit/installations/{installation_id}/charging_stations/{charging_station_id}
```

Used to determine:
- Plugged-in state
- Charging mode
- EVSE limits

---

## Notes & Warnings

- This integration is **cloud-based**
- API behaviour may change without notice
- Use at your own risk
- Not affiliated with or endorsed by Invisia

---

## License

MIT (suggested)
