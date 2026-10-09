import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .apifootball import ApiFootballFehler, schluessel_pruefen
from .const import CONF_API_KEY, CONF_LIGEN, DOMAIN, LIGEN, STANDARD_LIGEN


def _schema(ligen: list[str], schluessel: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LIGEN, default=ligen): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=k, label=v) for k, v in LIGEN.items()],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_API_KEY, description={"suggested_value": schluessel}): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


async def _pruefen(hass, user_input: dict) -> tuple[dict, dict]:
    """Eingaben prüfen; liefert (bereinigte Optionen, Fehler)."""
    errors: dict = {}
    if not user_input.get(CONF_LIGEN):
        errors["base"] = "keine_liga"
    schluessel = (user_input.get(CONF_API_KEY) or "").strip()
    if schluessel and not errors:
        try:
            await schluessel_pruefen(async_get_clientsession(hass), schluessel)
        except ApiFootballFehler:
            errors[CONF_API_KEY] = "api_key_ungueltig"
    optionen = {CONF_LIGEN: user_input.get(CONF_LIGEN, []), CONF_API_KEY: schluessel}
    return optionen, errors


class BundesligaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            optionen, errors = await _pruefen(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="Bundesliga", data={}, options=optionen)
        vorgabe = (user_input or {}).get(CONF_LIGEN, STANDARD_LIGEN)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(vorgabe, (user_input or {}).get(CONF_API_KEY, "")),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BundesligaOptionsFlow()


class BundesligaOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            optionen, errors = await _pruefen(self.hass, user_input)
            if not errors:
                return self.async_create_entry(data=optionen)
        aktuell = user_input or self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                aktuell.get(CONF_LIGEN, STANDARD_LIGEN), aktuell.get(CONF_API_KEY, "")
            ),
            errors=errors,
        )
