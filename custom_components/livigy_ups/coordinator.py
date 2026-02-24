"""Data update coordinator for Livigy UPS."""

from __future__ import annotations

import logging
import socket
import time
from datetime import timedelta
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .parser import parse_f, parse_i, parse_q1

_LOGGER = logging.getLogger(DOMAIN)


class LivigyUpsCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Fetches UPS data from Megatec/Q1 over TCP-serial adapter."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        timeout: float,
        scan_interval: int,
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
        sock: socket.socket,
        cmd: str,
        parser: Callable[[str], dict[str, object]],
        retries: int = 3,
        frames_per_try: int = 6,
    ) -> tuple[str, dict[str, object]]:
        payload = f"{cmd}\r".encode("ascii")
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
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
        raise ValueError(f"Failed to parse {cmd} response after {retries} attempts: {last_error}")

    def _poll_once(self) -> dict[str, object]:
        last_error: Exception | None = None
        for connect_attempt in range(1, 4):
            try:
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    sock.settimeout(self.timeout)
                    self._drain_socket(sock)

                    _, q1_data = self._exchange_with_retry(sock, "Q1", parse_q1)
                    _, i_data = self._exchange_with_retry(sock, "I", parse_i)
                    _, f_data = self._exchange_with_retry(sock, "F", parse_f)

                data: dict[str, object] = {}
                data.update(q1_data)
                data.update(i_data)
                data.update(f_data)
                return data
            except Exception as err:
                last_error = err
                _LOGGER.debug(
                    "Poll attempt %s/3 failed, retrying with new TCP connection: %s",
                    connect_attempt,
                    err,
                )
        raise ValueError(f"Polling failed after 3 connection attempts: {last_error}")

    async def _async_update_data(self) -> dict[str, object]:
        try:
            return await self.hass.async_add_executor_job(self._poll_once)
        except Exception as err:
            raise UpdateFailed(f"Failed to poll UPS: {err}") from err
