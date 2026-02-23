from __future__ import annotations

import argparse
import json
import logging
import socket
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt
import yaml

from .parser import parse_f, parse_i, parse_q1

_LOG = logging.getLogger("livigy_ups_bridge")


@dataclass
class Config:
    ups_host: str
    ups_port: int
    ups_timeout_seconds: float
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id: str
    discovery_prefix: str
    state_topic_prefix: str
    poll_interval_seconds: int
    device_name: str
    device_identifier: str
    manufacturer: str


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(
        ups_host=data["ups"]["host"],
        ups_port=int(data["ups"]["port"]),
        ups_timeout_seconds=float(data["ups"].get("timeout_seconds", 2)),
        mqtt_host=data["mqtt"]["host"],
        mqtt_port=int(data["mqtt"].get("port", 1883)),
        mqtt_username=str(data["mqtt"].get("username", "")),
        mqtt_password=str(data["mqtt"].get("password", "")),
        mqtt_client_id=str(data["mqtt"].get("client_id", "livigy-ups-bridge")),
        discovery_prefix=str(data["mqtt"].get("discovery_prefix", "homeassistant")),
        state_topic_prefix=str(data["mqtt"].get("state_topic_prefix", "livigy_ups")),
        poll_interval_seconds=int(data["bridge"].get("poll_interval_seconds", 15)),
        device_name=str(data["bridge"].get("device_name", "Livigy UPS")),
        device_identifier=str(data["bridge"].get("device_identifier", "livigy_ups_main")),
        manufacturer=str(data["bridge"].get("manufacturer", "Livigy / PowerShield")),
    )


def send_ups_command(host: str, port: int, timeout_seconds: float, cmd: str) -> str:
    payload = f"{cmd}\r".encode("ascii")
    with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendall(payload)
        data = sock.recv(4096)
    return data.decode("ascii", errors="ignore").strip()


def mqtt_publish_json(client: mqtt.Client, topic: str, payload: dict) -> None:
    client.publish(topic, json.dumps(payload), retain=True)


def publish_discovery(client: mqtt.Client, cfg: Config) -> None:
    device = {
        "identifiers": [cfg.device_identifier],
        "name": cfg.device_name,
        "manufacturer": cfg.manufacturer,
    }

    sensors = [
        ("input_voltage", "Input Voltage", "V", "voltage"),
        ("fault_voltage", "Fault Voltage", "V", "voltage"),
        ("output_voltage", "Output Voltage", "V", "voltage"),
        ("load_percent", "UPS Load", "%", None),
        ("input_frequency_hz", "Input Frequency", "Hz", "frequency"),
        ("battery_voltage", "Battery Voltage", "V", "voltage"),
        ("temperature_c", "UPS Temperature", "\u00b0C", "temperature"),
        ("model", "UPS Model", None, None),
        ("firmware", "UPS Firmware", None, None),
        ("company", "UPS Company", None, None),
        ("rated_voltage", "Rated Voltage", "V", "voltage"),
        ("rated_current", "Rated Current", "A", "current"),
        ("rated_battery_voltage", "Rated Battery Voltage", "V", "voltage"),
        ("rated_frequency_hz", "Rated Frequency", "Hz", "frequency"),
    ]

    binary_sensors = [
        ("utility_fail", "Utility Fail"),
        ("battery_low", "Battery Low"),
        ("avr_active", "AVR Active"),
        ("ups_failed", "UPS Failed"),
        ("standby_type", "Standby Type"),
        ("test_in_progress", "Test In Progress"),
        ("shutdown_active", "Shutdown Active"),
        ("beeper_on", "Beeper On"),
    ]

    for key, name, unit, dev_class in sensors:
        uid = f"{cfg.device_identifier}_{key}"
        topic = f"{cfg.discovery_prefix}/sensor/{uid}/config"
        state_topic = f"{cfg.state_topic_prefix}/state/{key}"
        payload = {
            "name": name,
            "unique_id": uid,
            "state_topic": state_topic,
            "device": device,
        }
        if unit:
            payload["unit_of_measurement"] = unit
        if dev_class:
            payload["device_class"] = dev_class
        mqtt_publish_json(client, topic, payload)

    for key, name in binary_sensors:
        uid = f"{cfg.device_identifier}_{key}"
        topic = f"{cfg.discovery_prefix}/binary_sensor/{uid}/config"
        state_topic = f"{cfg.state_topic_prefix}/state/{key}"
        payload = {
            "name": name,
            "unique_id": uid,
            "state_topic": state_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device,
        }
        mqtt_publish_json(client, topic, payload)


def publish_state(client: mqtt.Client, cfg: Config, key: str, value: object) -> None:
    topic = f"{cfg.state_topic_prefix}/state/{key}"
    if isinstance(value, bool):
        payload = "ON" if value else "OFF"
    else:
        payload = str(value)
    client.publish(topic, payload, retain=True)


def run(cfg: Config) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.mqtt_client_id)
    if cfg.mqtt_username:
        client.username_pw_set(cfg.mqtt_username, cfg.mqtt_password)
    client.connect(cfg.mqtt_host, cfg.mqtt_port, keepalive=60)
    client.loop_start()

    publish_discovery(client, cfg)

    while True:
        try:
            q1_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "Q1")
            q1 = parse_q1(q1_raw)

            i_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "I")
            i_data = parse_i(i_raw)

            f_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "F")
            f_data = parse_f(f_raw)

            for key, value in q1.__dict__.items():
                publish_state(client, cfg, key, value)
            for key, value in i_data.items():
                publish_state(client, cfg, key, value)
            for key, value in f_data.items():
                publish_state(client, cfg, key, value)

            _LOG.info("Published UPS state successfully")
        except Exception as exc:  # pylint: disable=broad-except
            _LOG.exception("Bridge poll failed: %s", exc)

        time.sleep(cfg.poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Livigy UPS MQTT bridge")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config)
    run(cfg)


if __name__ == "__main__":
    main()
