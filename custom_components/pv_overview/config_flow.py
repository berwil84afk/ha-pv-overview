"""Config Flow für PV Summary."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_INITIAL_TOTAL,
    CONF_SOURCE,
    CONF_THRESHOLD,
    DEFAULT_NAME,
    DEFAULT_THRESHOLD,
    DOMAIN,
)

SOURCE_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
THRESHOLD_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0, max=10_000, step=1, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
    )
)


class PVOverviewConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung über die Oberfläche."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOURCE])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_SOURCE): SOURCE_SELECTOR,
                vol.Required(CONF_THRESHOLD, default=DEFAULT_THRESHOLD): THRESHOLD_SELECTOR,
                vol.Required(CONF_INITIAL_TOTAL, default=0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100_000_000,
                        step=0.001,
                        unit_of_measurement="kWh",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PVOverviewOptionsFlow()


class PVOverviewOptionsFlow(OptionsFlow):
    """Sensor und Schwellwert nachträglich ändern."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        config = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE, default=config[CONF_SOURCE]): SOURCE_SELECTOR,
                vol.Required(
                    CONF_THRESHOLD, default=config.get(CONF_THRESHOLD, DEFAULT_THRESHOLD)
                ): THRESHOLD_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
