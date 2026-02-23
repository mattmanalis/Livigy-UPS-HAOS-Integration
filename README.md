# Livigy UPS -> Home Assistant (HAOS) Bridge

MQTT bridge for Livigy UPS units rebadged from PowerShield devices that speak Megatec/Q1 serial protocol over an IP-to-serial adapter.

## What it does

- Connects to a TCP serial adapter (`adapter_ip:port`)
- Polls UPS commands: `Q1`, `I`, `F`
- Parses live telemetry and status bits
- Publishes Home Assistant MQTT Discovery sensors and binary sensors
- Publishes state updates to MQTT topics for HAOS

## Protocol assumptions

- Serial settings on adapter side: `2400 8N1`
- ASCII commands terminated by `\r`
- Response format compatible with Megatec `Q1` protocol

## Quick start

1. Ensure Home Assistant has MQTT configured.
2. Copy `config.example.yaml` to `config.yaml` and edit values.
3. Run bridge:

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
python -m livigy_ups_bridge.main --config config.yaml
```

## Docker run

```bash
docker build -t livigy-ups-ha-bridge .
docker run --rm -it \
  -v "$PWD/config.yaml:/app/config.yaml:ro" \
  livigy-ups-ha-bridge
```

## MQTT topics

- Discovery topics: `homeassistant/<component>/<unique_id>/config`
- State root: `<state_topic_prefix>/...` (default: `livigy_ups`)

## Entities published

Sensors:
- Input Voltage (`V`)
- Fault Voltage (`V`)
- Output Voltage (`V`)
- UPS Load (`%`)
- Input Frequency (`Hz`)
- Battery Voltage (`V`)
- UPS Temperature (`°C`)
- UPS Model
- UPS Firmware
- UPS Company
- Rated Voltage (`V`)
- Rated Current (`A`)
- Rated Battery Voltage (`V`)
- Rated Frequency (`Hz`)

Binary sensors:
- Utility Fail
- Battery Low
- AVR Active (Bypass/Boost/Buck)
- UPS Failed
- UPS Standby Type
- Test In Progress
- Shutdown Active
- Beeper On

## Config file

See `config.example.yaml`.

## Troubleshooting

- If no response, verify adapter is in raw TCP serial mode and serial settings are `2400 8N1`.
- Try manual probe:

```bash
printf 'I\r' | nc -w1 <adapter_ip> <port>
printf 'F\r' | nc -w1 <adapter_ip> <port>
printf 'Q1\r' | nc -w1 <adapter_ip> <port>
```

- If `Q1` parse fails, capture one raw line and update parser regex/format.
