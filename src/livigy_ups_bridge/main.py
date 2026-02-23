from __future__ import annotations

import argparse
import logging
import socket
import time
from dataclasses import dataclass

import yaml

from .parser import parse_f, parse_i, parse_q1
from .publishers import PublisherConfig, build_publisher

_LOG = logging.getLogger("livigy_ups_bridge")


@dataclass
class Config:
    ups_host: str
    ups_port: int
    ups_timeout_seconds: float
    poll_interval_seconds: int
    output: PublisherConfig


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    output = data.get("output", {})
    mqtt_cfg = data.get("mqtt", {})
    ha_api_cfg = data.get("ha_api", {})
    bridge_cfg = data.get("bridge", {})

    publisher_cfg = PublisherConfig(
        mode=str(output.get("mode", "mqtt")),
        device_name=str(bridge_cfg.get("device_name", "Livigy UPS")),
        device_identifier=str(bridge_cfg.get("device_identifier", "livigy_ups_main")),
        manufacturer=str(bridge_cfg.get("manufacturer", "Livigy / PowerShield")),
        mqtt_host=str(mqtt_cfg.get("host", "")),
        mqtt_port=int(mqtt_cfg.get("port", 1883)),
        mqtt_username=str(mqtt_cfg.get("username", "")),
        mqtt_password=str(mqtt_cfg.get("password", "")),
        mqtt_client_id=str(mqtt_cfg.get("client_id", "livigy-ups-bridge")),
        discovery_prefix=str(mqtt_cfg.get("discovery_prefix", "homeassistant")),
        state_topic_prefix=str(mqtt_cfg.get("state_topic_prefix", "livigy_ups")),
        ha_base_url=str(ha_api_cfg.get("base_url", "")),
        ha_token=str(ha_api_cfg.get("token", "")),
        ha_verify_ssl=bool(ha_api_cfg.get("verify_ssl", True)),
    )

    return Config(
        ups_host=data["ups"]["host"],
        ups_port=int(data["ups"]["port"]),
        ups_timeout_seconds=float(data["ups"].get("timeout_seconds", 2)),
        poll_interval_seconds=int(bridge_cfg.get("poll_interval_seconds", 15)),
        output=publisher_cfg,
    )


def send_ups_command(host: str, port: int, timeout_seconds: float, cmd: str) -> str:
    payload = f"{cmd}\r".encode("ascii")
    with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendall(payload)
        data = sock.recv(4096)
    return data.decode("ascii", errors="ignore").strip()


def run(cfg: Config) -> None:
    publisher = build_publisher(cfg.output)
    publisher.setup()

    while True:
        try:
            q1_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "Q1")
            q1 = parse_q1(q1_raw)

            i_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "I")
            i_data = parse_i(i_raw)

            f_raw = send_ups_command(cfg.ups_host, cfg.ups_port, cfg.ups_timeout_seconds, "F")
            f_data = parse_f(f_raw)

            for key, value in q1.__dict__.items():
                publisher.publish_state(key, value)
            for key, value in i_data.items():
                publisher.publish_state(key, value)
            for key, value in f_data.items():
                publisher.publish_state(key, value)

            _LOG.info("Published UPS state successfully")
        except Exception as exc:  # pylint: disable=broad-except
            _LOG.exception("Bridge poll failed: %s", exc)

        time.sleep(cfg.poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Livigy UPS HAOS bridge")
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
