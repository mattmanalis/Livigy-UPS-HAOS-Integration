"""Config flow for Livigy UPS integration."""

from __future__ import annotations

from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)


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


class LivigyUpsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Livigy UPS."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_HOST] = _normalize_host(str(user_input[CONF_HOST]))
            if not user_input[CONF_HOST]:
                errors["base"] = "invalid_host"
                schema = vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                        vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(float),
                        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                    }
                )
                return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Livigy UPS ({user_input[CONF_HOST]})", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(float),
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return LivigyUpsOptionsFlow()


class LivigyUpsOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Livigy UPS integration."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMEOUT,
                    default=self.config_entry.options.get(CONF_TIMEOUT, self.config_entry.data[CONF_TIMEOUT]),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self.config_entry.data[CONF_SCAN_INTERVAL],
                    ),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
