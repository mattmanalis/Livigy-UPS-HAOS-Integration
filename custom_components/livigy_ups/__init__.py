"""Livigy UPS integration."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_TIMEOUT, DOMAIN
from .const import (
    SERVICE_CANCEL_BATTERY_TEST,
    SERVICE_CANCEL_SHUTDOWN,
    SERVICE_SEND_COMMAND,
    SERVICE_SHUTDOWN,
    SERVICE_START_BATTERY_TEST,
    SERVICE_TOGGLE_BEEPER,
)
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


def _build_test_command(minutes: int | None, until_low: bool) -> str:
    if until_low:
        return "TL"
    if minutes is not None:
        if minutes < 1 or minutes > 99:
            raise vol.Invalid("minutes must be between 1 and 99")
        return f"T{minutes:02d}"
    return "T"


def _build_shutdown_command(delay_minutes: int, restart_minutes: int | None) -> str:
    if delay_minutes < 0 or delay_minutes > 9999:
        raise vol.Invalid("delay_minutes must be between 0 and 9999")
    if restart_minutes is None:
        return f"S{delay_minutes:04d}"
    if restart_minutes < 0 or restart_minutes > 9999:
        raise vol.Invalid("restart_minutes must be between 0 and 9999")
    return f"S{delay_minutes:04d}R{restart_minutes:04d}"


def _get_target_coordinator(hass: HomeAssistant, call: ServiceCall) -> LivigyUpsCoordinator:
    entries = hass.data.get(DOMAIN, {})
    coordinators = {k: v for k, v in entries.items() if not str(k).startswith("_")}
    if not coordinators:
        raise vol.Invalid("No Livigy UPS entries are loaded")
    entry_id = call.data.get("entry_id")
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if not coordinator:
            raise vol.Invalid(f"Unknown entry_id: {entry_id}")
        return coordinator
    if len(coordinators) > 1:
        selected_entry_id = sorted(coordinators.keys())[0]
        _LOGGER.warning(
            "Multiple Livigy UPS entries found. No entry_id provided, defaulting to %s",
            selected_entry_id,
        )
        return coordinators[selected_entry_id]
    return next(iter(coordinators.values()))


def _register_services(hass: HomeAssistant) -> None:
    if hass.data.get(DOMAIN, {}).get("_services_registered"):
        return

    send_command_schema = vol.Schema(
        {
            vol.Required("command"): str,
            vol.Optional("entry_id"): str,
        }
    )
    test_schema = vol.Schema(
        {
            vol.Optional("minutes"): vol.Coerce(int),
            vol.Optional("until_low", default=False): bool,
            vol.Optional("entry_id"): str,
        }
    )
    shutdown_schema = vol.Schema(
        {
            vol.Required("delay_minutes"): vol.Coerce(int),
            vol.Optional("restart_minutes"): vol.Coerce(int),
            vol.Optional("entry_id"): str,
        }
    )
    basic_schema = vol.Schema({vol.Optional("entry_id"): str})

    async def async_send_command(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        command = str(call.data["command"]).strip()
        if not command:
            raise vol.Invalid("command cannot be empty")
        raw = await coordinator.async_send_command(command)
        _LOGGER.info("Sent command %s, response=%s", command, raw)
        await coordinator.async_request_refresh()

    async def async_toggle_beeper(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        raw = await coordinator.async_send_command("Q")
        _LOGGER.info("Sent command Q (toggle beeper), response=%s", raw)
        await coordinator.async_request_refresh()

    async def async_start_battery_test(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        command = _build_test_command(call.data.get("minutes"), bool(call.data.get("until_low", False)))
        raw = await coordinator.async_send_command(command)
        _LOGGER.info("Sent command %s (battery test), response=%s", command, raw)
        await coordinator.async_request_refresh()

    async def async_cancel_battery_test(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        raw = await coordinator.async_send_command("CT")
        _LOGGER.info("Sent command CT (cancel battery test), response=%s", raw)
        await coordinator.async_request_refresh()

    async def async_shutdown(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        command = _build_shutdown_command(call.data["delay_minutes"], call.data.get("restart_minutes"))
        raw = await coordinator.async_send_command(command)
        _LOGGER.info("Sent command %s (shutdown), response=%s", command, raw)
        await coordinator.async_request_refresh()

    async def async_cancel_shutdown(call: ServiceCall) -> None:
        coordinator = _get_target_coordinator(hass, call)
        raw = await coordinator.async_send_command("C")
        _LOGGER.info("Sent command C (cancel shutdown), response=%s", raw)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_SEND_COMMAND, async_send_command, schema=send_command_schema)
    hass.services.async_register(DOMAIN, SERVICE_TOGGLE_BEEPER, async_toggle_beeper, schema=basic_schema)
    hass.services.async_register(DOMAIN, SERVICE_START_BATTERY_TEST, async_start_battery_test, schema=test_schema)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_BATTERY_TEST, async_cancel_battery_test, schema=basic_schema)
    hass.services.async_register(DOMAIN, SERVICE_SHUTDOWN, async_shutdown, schema=shutdown_schema)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_SHUTDOWN, async_cancel_shutdown, schema=basic_schema)
    hass.data.setdefault(DOMAIN, {})["_services_registered"] = True


def _unregister_services_if_unused(hass: HomeAssistant) -> None:
    entries = hass.data.get(DOMAIN, {})
    active_entries = [key for key in entries if not key.startswith("_")]
    if active_entries:
        return
    for service in (
        SERVICE_SEND_COMMAND,
        SERVICE_TOGGLE_BEEPER,
        SERVICE_START_BATTERY_TEST,
        SERVICE_CANCEL_BATTERY_TEST,
        SERVICE_SHUTDOWN,
        SERVICE_CANCEL_SHUTDOWN,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
    entries.pop("_services_registered", None)


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
    _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Do not block integration setup on initial poll; run refresh in background.
    hass.async_create_task(coordinator.async_request_refresh())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _unregister_services_if_unused(hass)
    return unload_ok
