"""Data update coordinator for Livigy UPS."""

from __future__ import annotations

import logging
import socket
import ssl
import time
from urllib import parse, request
from datetime import timedelta
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .parser import parse_f, parse_i, parse_q1, parse_qgs, parse_qmd, parse_qmod, parse_qri, parse_qvfw

_LOGGER = logging.getLogger(DOMAIN)


class LivigyUpsCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Fetches UPS data over TCP-serial adapter (Centurion or Megatec)."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        timeout: float,
        scan_interval: int,
        site_id: str,
        unit_id: str,
        entry_id: str,
        influx_enabled: bool,
        influx_url: str,
        influx_org: str,
        influx_bucket: str,
        influx_token: str,
        influx_verify_ssl: bool,
        influx_measurement: str,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.timeout = timeout
        self.site_id = site_id
        self.unit_id = unit_id
        self.entry_id = entry_id
        self.influx_enabled = influx_enabled
        self.influx_url = influx_url.rstrip("/")
        self.influx_org = influx_org
        self.influx_bucket = influx_bucket
        self.influx_token = influx_token
        self.influx_verify_ssl = influx_verify_ssl
        self.influx_measurement = influx_measurement

    def _drain_socket(self, sock: socket.socket) -> None:
        """Drain any stale bytes the adapter may send on connect."""
        sock.settimeout(0.05)
        while True:
            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                break
            if not chunk:
                break
        sock.settimeout(self.timeout)

    def _read_frame(self, sock: socket.socket) -> str:
        """Read one UPS frame. Most devices terminate with CR/LF."""
        buffer = bytearray()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(1)
            except TimeoutError:
                break
            if not chunk:
                break
            if chunk in (b"\r", b"\n"):
                if buffer:
                    break
                continue
            buffer.extend(chunk)
            if len(buffer) >= 4096:
                break
        return bytes(buffer).decode("ascii", errors="ignore").strip()

    def _exchange_with_retry(
        self,
        cmd: str,
        parser: Callable[[str], dict[str, object]],
        retries: int = 4,
        frames_per_try: int = 6,
    ) -> tuple[str, dict[str, object]]:
        payloads = [
            f"{cmd}\r".encode("ascii"),
            f"{cmd}\r\n".encode("ascii"),
            f"{cmd}\n".encode("ascii"),
        ]
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    sock.settimeout(self.timeout)
                    self._drain_socket(sock)

                    for payload in payloads:
                        sock.sendall(payload)
                        for frame_idx in range(1, frames_per_try + 1):
                            raw = self._read_frame(sock)
                            if not raw:
                                last_error = ValueError(f"Empty response for {cmd}")
                                continue
                            try:
                                return raw, parser(raw)
                            except Exception as err:
                                last_error = err
                                _LOGGER.debug(
                                    "Ignoring non-matching frame for %s attempt %s/%s frame %s/%s: %r (%s)",
                                    cmd,
                                    attempt,
                                    retries,
                                    frame_idx,
                                    frames_per_try,
                                    raw,
                                    err,
                                )
            except Exception as err:
                last_error = err
                _LOGGER.debug("Transport error for %s attempt %s/%s: %s", cmd, attempt, retries, err)
        raise ValueError(f"Failed to parse {cmd} response after {retries} attempts: {last_error}")

    def _poll_once(self) -> dict[str, object]:
        qgs_err: Exception | None = None
        q1_err: Exception | None = None
        live_data: dict[str, object] | None = None

        try:
            _, live_data = self._exchange_with_retry("QGS", parse_qgs)
        except Exception as err:
            qgs_err = err
            _LOGGER.debug("QGS poll failed, falling back to Q1: %s", err)

        if live_data is None:
            try:
                _, live_data = self._exchange_with_retry("Q1", parse_q1)
            except Exception as err:
                q1_err = err
                raise ValueError(f"QGS failed ({qgs_err}); Q1 failed ({q1_err})") from err

        protocol = str(live_data.get("protocol_family", "unknown"))
        identity_data: dict[str, object] = {}
        ratings_data: dict[str, object] = {}
        mode_data: dict[str, object] = {}
        firmware_data: dict[str, object] = {}

        if protocol == "centurion":
            try:
                # Some Centurion units still answer Q1, which provides fault voltage.
                _, q1_legacy = self._exchange_with_retry("Q1", parse_q1, retries=1, frames_per_try=2)
                if q1_legacy.get("fault_voltage") is not None:
                    live_data["fault_voltage"] = q1_legacy["fault_voltage"]
            except Exception as err:
                _LOGGER.debug("Optional Q1 fault-voltage fallback failed: %s", err)
            try:
                _, identity_data = self._exchange_with_retry("QMD", parse_qmd)
            except Exception as err:
                _LOGGER.debug("Optional QMD poll failed: %s", err)
            try:
                _, ratings_data = self._exchange_with_retry("QRI", parse_qri)
            except Exception as err:
                _LOGGER.debug("Optional QRI poll failed: %s", err)
            try:
                _, mode_data = self._exchange_with_retry("QMOD", parse_qmod)
            except Exception as err:
                _LOGGER.debug("Optional QMOD poll failed: %s", err)
            try:
                _, firmware_data = self._exchange_with_retry("QVFW", parse_qvfw)
            except Exception as err:
                _LOGGER.debug("Optional QVFW poll failed: %s", err)
        else:
            try:
                _, identity_data = self._exchange_with_retry("I", parse_i)
            except Exception as err:
                _LOGGER.debug("Optional I poll failed: %s", err)
            try:
                _, ratings_data = self._exchange_with_retry("F", parse_f)
            except Exception as err:
                _LOGGER.debug("Optional F poll failed: %s", err)

        data: dict[str, object] = {}
        data.update(live_data)
        data.update(identity_data)
        data.update(ratings_data)
        data.update(mode_data)
        data.update(firmware_data)
        data["adapter_connected"] = True
        data["ups_responding"] = True
        load_percent = data.get("load_percent")
        ups_mode = str(data.get("ups_mode", "")).lower()
        data["on_battery"] = ups_mode in {"battery", "battery_test", "battery test"} or bool(data.get("utility_fail"))
        try:
            data["overload_warning"] = float(load_percent) >= 100.0 if load_percent is not None else None
        except (TypeError, ValueError):
            data["overload_warning"] = None
        if not data.get("adapter_connected"):
            data["status_summary"] = "Adapter Disconnected"
        elif not data.get("ups_responding"):
            data["status_summary"] = "UPS Not Responding"
        elif data.get("ups_failed"):
            data["status_summary"] = "UPS Fault"
        elif data.get("utility_fail"):
            data["status_summary"] = "On Battery"
        elif data.get("battery_low"):
            data["status_summary"] = "Battery Low"
        elif data.get("overload_warning"):
            data["status_summary"] = "Overload"
        else:
            data["status_summary"] = "Normal"
        return data

    def _check_adapter_connected(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=min(2.0, self.timeout)):
                return True
        except OSError:
            return False

    def _send_command_once(self, command: str, frames_per_try: int = 6) -> str:
        payloads = [
            f"{command}\r".encode("ascii"),
            f"{command}\r\n".encode("ascii"),
            f"{command}\n".encode("ascii"),
        ]
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            self._drain_socket(sock)
            for payload in payloads:
                sock.sendall(payload)
                for _ in range(frames_per_try):
                    raw = self._read_frame(sock)
                    if raw:
                        return raw
        return ""

    def _send_command_with_retry(self, command: str, retries: int = 3) -> str:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                raw = self._send_command_once(command)
                if raw:
                    return raw
                return "NO_RESPONSE"
            except Exception as err:
                last_error = err
                _LOGGER.debug("Command %s transport error attempt %s/%s: %s", command, attempt, retries, err)
        raise ValueError(f"Failed to send command {command}: {last_error}")

    async def async_send_command(self, command: str) -> str:
        return await self.hass.async_add_executor_job(self._send_command_with_retry, command)

    @staticmethod
    def _escape_tag(value: str) -> str:
        return value.replace("\\", "\\\\").replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")

    @staticmethod
    def _escape_field_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _to_line_protocol(self, data: dict[str, object]) -> str:
        tags = {
            "site_id": self.site_id or "unknown",
            "unit_id": self.unit_id or "unknown",
            "entry_id": self.entry_id,
            "host": self.host,
        }
        tag_part = ",".join(f"{k}={self._escape_tag(str(v))}" for k, v in tags.items())

        field_tokens: list[str] = []
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, bool):
                field_tokens.append(f"{key}={'true' if value else 'false'}")
            elif isinstance(value, int):
                field_tokens.append(f"{key}={value}i")
            elif isinstance(value, float):
                field_tokens.append(f"{key}={value}")
            else:
                field_tokens.append(f'{key}="{self._escape_field_string(str(value))}"')
        if not field_tokens:
            return ""
        return f"{self.influx_measurement},{tag_part} " + ",".join(field_tokens)

    def _write_influx(self, data: dict[str, object]) -> None:
        if not self.influx_enabled:
            return
        if not (self.influx_url and self.influx_org and self.influx_bucket and self.influx_token):
            _LOGGER.debug("Influx export enabled but config is incomplete; skipping write")
            return

        line = self._to_line_protocol(data)
        if not line:
            return

        query = parse.urlencode({"org": self.influx_org, "bucket": self.influx_bucket, "precision": "s"})
        url = f"{self.influx_url}/api/v2/write?{query}"
        req = request.Request(
            url=url,
            data=line.encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Token {self.influx_token}",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        context = ssl.create_default_context() if self.influx_verify_ssl else ssl._create_unverified_context()  # noqa: SLF001
        with request.urlopen(req, timeout=10, context=context):
            pass

    async def _async_update_data(self) -> dict[str, object]:
        try:
            data = await self.hass.async_add_executor_job(self._poll_once)
            await self.hass.async_add_executor_job(self._write_influx, data)
            return data
        except Exception as err:
            adapter_connected = await self.hass.async_add_executor_job(self._check_adapter_connected)
            data = dict(self.data or {})
            data["adapter_connected"] = adapter_connected
            data["ups_responding"] = False
            data["status_summary"] = "UPS Not Responding" if adapter_connected else "Adapter Disconnected"
            _LOGGER.warning("UPS poll failed: %s (adapter_connected=%s)", err, adapter_connected)
            await self.hass.async_add_executor_job(self._write_influx, data)
            return data
