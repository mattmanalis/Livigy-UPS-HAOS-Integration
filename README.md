# Livigy UPS HAOS Integration

Home Assistant custom integration for Livigy UPS units (rebadged PowerShield) that support Megatec/Q1 serial protocol via an IP-to-serial adapter.

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
- `Timeout (seconds)`: socket timeout, default `2`
- `Poll interval (seconds)`: default `15`

## Protocol

- Commands used: `Q1`, `I`, `F`
- Command terminator: `\r`
- Typical serial side settings on the adapter: `2400 8N1`

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
- Rated Voltage
- Rated Current
- Rated Battery Voltage
- Rated Frequency

Binary sensors:
- Utility Fail
- Battery Low
- AVR Active
- UPS Failed
- Standby Type
- Test In Progress
- Shutdown Active
- Beeper On
