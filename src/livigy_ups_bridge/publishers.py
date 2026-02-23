from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import request

import paho.mqtt.client as mqtt


SENSOR_META: dict[str, dict[str, str]] = {
    "input_voltage": {"name": "Input Voltage", "unit": "V", "device_class": "voltage"},
    "fault_voltage": {"name": "Fault Voltage", "unit": "V", "device_class": "voltage"},
    "output_voltage": {"name": "Output Voltage", "unit": "V", "device_class": "voltage"},
    "load_percent": {"name": "UPS Load", "unit": "%"},
    "input_frequency_hz": {"name": "Input Frequency", "unit": "Hz", "device_class": "frequency"},
    "battery_voltage": {"name": "Battery Voltage", "unit": "V", "device_class": "voltage"},
    "temperature_c": {"name": "UPS Temperature", "unit": "\u00b0C", "device_class": "temperature"},
    "model": {"name": "UPS Model"},
    "firmware": {"name": "UPS Firmware"},
    "company": {"name": "UPS Company"},
    "rated_voltage": {"name": "Rated Voltage", "unit": "V", "device_class": "voltage"},
    "rated_current": {"name": "Rated Current", "unit": "A", "device_class": "current"},
    "rated_battery_voltage": {"name": "Rated Battery Voltage", "unit": "V", "device_class": "voltage"},
    "rated_frequency_hz": {"name": "Rated Frequency", "unit": "Hz", "device_class": "frequency"},
}

BINARY_SENSOR_META: dict[str, str] = {
    "utility_fail": "Utility Fail",
    "battery_low": "Battery Low",
    "avr_active": "AVR Active",
    "ups_failed": "UPS Failed",
    "standby_type": "Standby Type",
    "test_in_progress": "Test In Progress",
    "shutdown_active": "Shutdown Active",
    "beeper_on": "Beeper On",
}


@dataclass
class PublisherConfig:
    mode: str
    device_name: str
    device_identifier: str
    manufacturer: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id: str
    discovery_prefix: str
    state_topic_prefix: str
    ha_base_url: str
    ha_token: str
    ha_verify_ssl: bool


class Publisher:
    def setup(self) -> None:
        raise NotImplementedError

    def publish_state(self, key: str, value: Any) -> None:
        raise NotImplementedError


class MqttPublisher(Publisher):
    def __init__(self, cfg: PublisherConfig) -> None:
        self.cfg = cfg
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.mqtt_client_id)

    def setup(self) -> None:
        if self.cfg.mqtt_username:
            self.client.username_pw_set(self.cfg.mqtt_username, self.cfg.mqtt_password)
        self.client.connect(self.cfg.mqtt_host, self.cfg.mqtt_port, keepalive=60)
        self.client.loop_start()
        self._publish_discovery()

    def _publish_json(self, topic: str, payload: dict[str, Any]) -> None:
        self.client.publish(topic, json.dumps(payload), retain=True)

    def _publish_discovery(self) -> None:
        device = {
            "identifiers": [self.cfg.device_identifier],
            "name": self.cfg.device_name,
            "manufacturer": self.cfg.manufacturer,
        }

        for key, meta in SENSOR_META.items():
            uid = f"{self.cfg.device_identifier}_{key}"
            topic = f"{self.cfg.discovery_prefix}/sensor/{uid}/config"
            state_topic = f"{self.cfg.state_topic_prefix}/state/{key}"
            payload: dict[str, Any] = {
                "name": meta["name"],
                "unique_id": uid,
                "state_topic": state_topic,
                "device": device,
            }
            if "unit" in meta:
                payload["unit_of_measurement"] = meta["unit"]
            if "device_class" in meta:
                payload["device_class"] = meta["device_class"]
            self._publish_json(topic, payload)

        for key, name in BINARY_SENSOR_META.items():
            uid = f"{self.cfg.device_identifier}_{key}"
            topic = f"{self.cfg.discovery_prefix}/binary_sensor/{uid}/config"
            state_topic = f"{self.cfg.state_topic_prefix}/state/{key}"
            payload = {
                "name": name,
                "unique_id": uid,
                "state_topic": state_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "device": device,
            }
            self._publish_json(topic, payload)

    def publish_state(self, key: str, value: Any) -> None:
        topic = f"{self.cfg.state_topic_prefix}/state/{key}"
        payload = "ON" if isinstance(value, bool) and value else "OFF" if isinstance(value, bool) else str(value)
        self.client.publish(topic, payload, retain=True)


class HomeAssistantApiPublisher(Publisher):
    def __init__(self, cfg: PublisherConfig) -> None:
        self.cfg = cfg
        base_url = cfg.ha_base_url.rstrip("/")
        if not base_url:
            raise ValueError("ha_api.base_url is required when output.mode=ha_api")
        if not cfg.ha_token:
            raise ValueError("ha_api.token is required when output.mode=ha_api")
        self.base_url = base_url
        if cfg.ha_verify_ssl:
            self.ssl_context = ssl.create_default_context()
        else:
            self.ssl_context = ssl._create_unverified_context()  # noqa: SLF001

    def setup(self) -> None:
        # No discovery endpoint exists for REST states; entities are created by POSTing state.
        return

    def _entity_meta(self, key: str, is_binary: bool) -> tuple[str, dict[str, Any], Any]:
        if is_binary:
            name = BINARY_SENSOR_META[key]
            entity_id = f"binary_sensor.{self.cfg.device_identifier}_{key}"
            attrs: dict[str, Any] = {
                "friendly_name": f"{self.cfg.device_name} {name}",
                "device_class": "problem" if key in {"utility_fail", "battery_low", "ups_failed"} else None,
            }
            return entity_id, {k: v for k, v in attrs.items() if v is not None}, None

        meta = SENSOR_META[key]
        entity_id = f"sensor.{self.cfg.device_identifier}_{key}"
        attrs = {
            "friendly_name": f"{self.cfg.device_name} {meta['name']}",
            "unit_of_measurement": meta.get("unit"),
            "device_class": meta.get("device_class"),
            "state_class": "measurement" if key in {
                "input_voltage",
                "fault_voltage",
                "output_voltage",
                "load_percent",
                "input_frequency_hz",
                "battery_voltage",
                "temperature_c",
                "rated_voltage",
                "rated_current",
                "rated_battery_voltage",
                "rated_frequency_hz",
            } else None,
            "manufacturer": self.cfg.manufacturer,
            "device_name": self.cfg.device_name,
        }
        return entity_id, {k: v for k, v in attrs.items() if v is not None}, None

    def publish_state(self, key: str, value: Any) -> None:
        is_binary = key in BINARY_SENSOR_META
        if is_binary:
            entity_id, attrs, _ = self._entity_meta(key, True)
            state = "on" if bool(value) else "off"
        elif key in SENSOR_META:
            entity_id, attrs, _ = self._entity_meta(key, False)
            state = value
        else:
            return

        payload = json.dumps({"state": state, "attributes": attrs}).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/api/states/{entity_id}",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.cfg.ha_token}",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, context=self.ssl_context, timeout=10):
            pass


def build_publisher(cfg: PublisherConfig) -> Publisher:
    mode = cfg.mode.strip().lower()
    if mode == "mqtt":
        return MqttPublisher(cfg)
    if mode == "ha_api":
        return HomeAssistantApiPublisher(cfg)
    raise ValueError("output.mode must be 'mqtt' or 'ha_api'")
