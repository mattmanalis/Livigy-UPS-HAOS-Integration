"""Data update coordinator for Livigy UPS."""

from __future__ import annotations

import logging
import socket
from datetime import timedelta

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

    def _send_cmd(self, cmd: str) -> str:
        payload = f"{cmd}\r".encode("ascii")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(payload)
            data = sock.recv(4096)
        return data.decode("ascii", errors="ignore").strip()

    async def _async_update_data(self) -> dict[str, object]:
        try:
            q1_raw = await self.hass.async_add_executor_job(self._send_cmd, "Q1")
            i_raw = await self.hass.async_add_executor_job(self._send_cmd, "I")
            f_raw = await self.hass.async_add_executor_job(self._send_cmd, "F")

            data: dict[str, object] = {}
            data.update(parse_q1(q1_raw))
            data.update(parse_i(i_raw))
            data.update(parse_f(f_raw))
            return data
        except Exception as err:
            raise UpdateFailed(f"Failed to poll UPS: {err}") from err
