import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_LIGEN, DOMAIN, LIGEN, STANDARD_LIGEN


def _schema(vorgabe: list[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LIGEN, default=vorgabe): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=k, label=v) for k, v in LIGEN.items()],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        }
    )


class BundesligaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            if not user_input[CONF_LIGEN]:
                errors["base"] = "keine_liga"
            else:
                return self.async_create_entry(title="Bundesliga", data={}, options=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(STANDARD_LIGEN), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BundesligaOptionsFlow()


class BundesligaOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input[CONF_LIGEN]:
                errors["base"] = "keine_liga"
            else:
                return self.async_create_entry(data=user_input)
        vorgabe = self.config_entry.options.get(CONF_LIGEN, STANDARD_LIGEN)
        return self.async_show_form(step_id="init", data_schema=_schema(vorgabe), errors=errors)
