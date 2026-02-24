# Livigy UPS HAOS Integration

Home Assistant custom integration for Livigy UPS units (rebadged PowerShield) via an IP-to-serial adapter.

## HACS install

1. HACS -> Integrations -> Custom repositories.
2. Add this repo URL as category `Integration`:
   - `https://github.com/mattmanalis/Livigy-UPS-HAOS-Integration`
3. Install `Livigy UPS` from HACS.
4. Restart Home Assistant.
5. Add integration: Settings -> Devices & Services -> Add Integration -> `Livigy UPS`.

## Config flow fields

- `Adapter host/IP`: IP of your TCP serial adapter
- `Adapter TCP port`: usually `2001` (depends on adapter)
- `Timeout (seconds)`: socket timeout, default `5`
- `Poll interval (seconds)`: default `15`
- `Site ID`: required tag for central reporting
- `Unit/Residence ID`: required tag for central reporting
- `Enable InfluxDB export`: enable/disable writes to InfluxDB
- `InfluxDB URL`: e.g. `https://influx.example.com`
- `InfluxDB org`, `InfluxDB bucket`, `InfluxDB token`
- `Verify InfluxDB SSL certificate`
- `InfluxDB measurement`: default `livigy_ups`

## Protocol

- Auto-detects protocol family:
- Centurion protocol first: `QGS`, `QMD`, `QRI`, `QMOD`, `QVFW`
- Legacy Megatec fallback: `Q1`, `I`, `F`
- On Centurion, attempts optional `Q1` fallback to populate `Fault Voltage`
- Command terminator: `\r`
- Typical serial side settings on adapter serial side: `2400 8N1`

## Exposed entities

Sensors:
- Input Voltage
- Fault Voltage
- Output Voltage
- UPS Load
- Input Frequency
- Battery Voltage
- UPS Temperature
- UPS Company
- UPS Model
- UPS Firmware
- UPS Mode
- UPS Topology
- UPS Protocol
- UPS Status Summary
- Rated Voltage
- Rated Current
- Rated Battery Voltage
- Rated Frequency
- Rated Watts

Binary sensors:
- Utility Fail
- Battery Low
- AVR Active
- UPS Failed
- On Battery
- Overload Warning
- Standby Type
- Test In Progress
- Shutdown Active
- Beeper On

## Control services

The integration exposes these Home Assistant services:

- `livigy_ups.toggle_beeper` (uses `BZON/BZOFF` on Centurion, `Q` on legacy)
- `livigy_ups.start_battery_test` (`minutes` optional, `until_low` optional)
- `livigy_ups.cancel_battery_test`
- `livigy_ups.shutdown` (`delay_minutes` required, `restart_minutes` optional)
- `livigy_ups.cancel_shutdown` (uses `CS` on Centurion, `C` on legacy)
- `livigy_ups.send_command` (`command` raw)

If you have multiple Livigy UPS entries, include `entry_id` in service data.

## Dashboard

A ready Lovelace dashboard is included at:

- `dashboards/livigy_ups_dashboard.yaml`

Import it as a manual dashboard (or copy cards into your existing dashboard), then adjust entity IDs if needed.
