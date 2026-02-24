"""Livigy UPS integration."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_TIMEOUT, DOMAIN
from .coordinator import LivigyUpsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


def _normalize_host(value: str) -> str:
    host = value.strip()
    if "://" in host:
        parsed = urlsplit(host)
        host = parsed.hostname or host
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host.count(":") == 1 and host.rsplit(":", 1)[1].isdigit():
        host = host.rsplit(":", 1)[0]
    return host.strip()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = _normalize_host(str(entry.data[CONF_HOST]))
    if host != entry.data[CONF_HOST]:
        data = dict(entry.data)
        data[CONF_HOST] = host
        hass.config_entries.async_update_entry(entry, data=data)
    port = entry.data[CONF_PORT]
    timeout = entry.options.get(CONF_TIMEOUT, entry.data[CONF_TIMEOUT])
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data[CONF_SCAN_INTERVAL])

    coordinator = LivigyUpsCoordinator(hass, host, port, timeout, scan_interval)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Initial UPS poll failed for %s:%s. Integration will keep retrying in background.",
            host,
            port,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
