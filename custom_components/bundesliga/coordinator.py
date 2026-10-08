import asyncio
import logging
from datetime import datetime

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    CONF_LIGEN,
    DOMAIN,
    INTERVALL_LIVE,
    INTERVALL_NORMAL,
    SPIELDAUER,
    STANDARD_LIGEN,
    VORLAUF,
)

_LOGGER = logging.getLogger(__name__)


def anstoss(spiel: dict) -> datetime | None:
    return dt_util.parse_datetime(spiel["anstoss"]) if spiel.get("anstoss") else None


def status(spiel: dict, jetzt: datetime) -> str:
    if spiel.get("beendet"):
        return "beendet"
    beginn = anstoss(spiel)
    if beginn and beginn <= jetzt <= beginn + SPIELDAUER:
        return "live"
    return "geplant"


def im_zeitfenster(spiel: dict, jetzt: datetime) -> bool:
    beginn = anstoss(spiel)
    return bool(beginn and beginn - VORLAUF <= jetzt <= beginn + SPIELDAUER)


class BundesligaCoordinator(DataUpdateCoordinator[dict]):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=INTERVALL_NORMAL, config_entry=entry,
        )
        self.ligen: list[str] = entry.options.get(CONF_LIGEN, STANDARD_LIGEN)

    async def _async_update_data(self) -> dict:
        session = async_get_clientsession(self.hass)
        daten: dict = {}
        for liga in self.ligen:
            try:
                async with session.get(
                    API_URL.format(liga), timeout=aiohttp.ClientTimeout(total=20)
                ) as antwort:
                    antwort.raise_for_status()
                    roh = await antwort.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
                if self.data and liga in self.data:
                    _LOGGER.debug("Abruf %s fehlgeschlagen, behalte alte Daten: %s", liga, err)
                    daten[liga] = self.data[liga]
                    continue
                raise UpdateFailed(f"OpenLigaDB nicht erreichbar ({liga}): {err}") from err
            daten[liga] = self._aufbereiten(roh if isinstance(roh, list) else [])

        jetzt = dt_util.utcnow()
        aktiv = any(
            im_zeitfenster(s, jetzt) and not s["beendet"]
            for liga in daten.values() for s in liga["spiele"]
        )
        self.update_interval = INTERVALL_LIVE if aktiv else INTERVALL_NORMAL
        return daten

    @staticmethod
    def _aufbereiten(roh: list) -> dict:
        spiele = []
        for m in roh:
            ergebnisse = m.get("matchResults") or []
            ende = [r for r in ergebnisse if r.get("resultTypeID") == 2]
            tore = m.get("goals") or []
            letztes = tore[-1] if tore else None
            if ende:
                heim, gast = ende[0].get("pointsTeam1"), ende[0].get("pointsTeam2")
            elif letztes:
                heim, gast = letztes.get("scoreTeam1"), letztes.get("scoreTeam2")
            else:
                heim = gast = None
            t1, t2 = m.get("team1") or {}, m.get("team2") or {}
            spiele.append(
                {
                    "heim": t1.get("shortName") or t1.get("teamName"),
                    "gast": t2.get("shortName") or t2.get("teamName"),
                    "heim_logo": t1.get("teamIconUrl"),
                    "gast_logo": t2.get("teamIconUrl"),
                    "anstoss": m.get("matchDateTimeUTC"),
                    "beendet": bool(m.get("matchIsFinished")),
                    "tore_heim": heim,
                    "tore_gast": gast,
                    "letztes_tor_minute": letztes.get("matchMinute") if letztes else None,
                    "letztes_tor_von": letztes.get("goalGetterName") if letztes else None,
                }
            )
        spiele.sort(key=lambda s: s["anstoss"] or "")
        spieltag = (roh[0].get("group") or {}).get("groupName") if roh else None
        return {"spieltag": spieltag, "spiele": spiele}
