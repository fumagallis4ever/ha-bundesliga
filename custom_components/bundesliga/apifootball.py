"""Optionale Zweitquelle API-Football (api-sports.io) für Live-Stände und fehlende Ergebnisse.

OpenLigaDB bleibt die Hauptquelle (Spielplan, Logos, Spieltag). API-Football wird nur
abgefragt, wenn ein Spiel läuft oder ein Ergebnis bei OpenLigaDB noch fehlt – und dann
höchstens alle paar Minuten pro Liga, damit der Gratis-Tarif (100 Abrufe/Tag) reicht.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import aiohttp
from homeassistant.util import dt as dt_util

from .const import (
    APIF_ABGESAGT,
    APIF_BEENDET,
    APIF_INTERVALL,
    APIF_LIGEN,
    APIF_LIVE,
    APIF_NACHLAUF,
    APIF_RESERVE,
    APIF_STATUS_URL,
    APIF_URL,
)

_LOGGER = logging.getLogger(__name__)

# Wörter, die in Vereinsnamen nichts zur Unterscheidung beitragen
_FUELLWOERTER = {
    "fc", "sv", "sc", "vfl", "vfb", "tsg", "fsv", "spvgg", "bsc", "ssv", "tsv", "sg",
    "bv", "ev", "ac", "ksc", "dsc", "1", "04", "05", "07", "09", "96", "98", "1846",
    "1860", "1899", "1900", "1910", "1919", "e", "v", "von", "de",
}


class ApiFootballFehler(Exception):
    """Schlüssel ungültig oder Kontingent erschöpft."""


def saison(datum: datetime) -> int:
    """API-Football zählt eine Saison nach ihrem Startjahr (2026/27 → 2026)."""
    return datum.year if datum.month >= 7 else datum.year - 1


def _normalisiert(name: str | None) -> str:
    if not name:
        return ""
    name = name.lower().replace("ß", "ss")
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        name = name.replace(alt, neu)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    woerter = [w for w in re.split(r"[^a-z0-9]+", name) if w and w not in _FUELLWOERTER]
    return " ".join(woerter)


def _aehnlichkeit(namen: list[str | None], anderer: str | None) -> float:
    b = _normalisiert(anderer)
    if not b:
        return 0.0
    bester = 0.0
    for name in namen:
        a = _normalisiert(name)
        if not a:
            continue
        if a == b or a in b or b in a:
            return 1.0
        wa, wb = set(a.split()), set(b.split())
        ueberlappung = len(wa & wb) / max(len(wa | wb), 1)
        bester = max(bester, SequenceMatcher(None, a, b).ratio(), ueberlappung)
    return bester


async def schluessel_pruefen(session: aiohttp.ClientSession, schluessel: str) -> None:
    """Wirft ApiFootballFehler, wenn der Schlüssel nicht funktioniert. Kostet kein Kontingent."""
    try:
        async with session.get(
            APIF_STATUS_URL,
            headers={"x-apisports-key": schluessel},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as antwort:
            daten = await antwort.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
        raise ApiFootballFehler(f"API-Football nicht erreichbar: {err}") from err
    if daten.get("errors"):
        raise ApiFootballFehler(str(daten["errors"]))


class ApiFootball:
    """Holt Spiele pro Liga und Tag und ergänzt damit die OpenLigaDB-Daten."""

    def __init__(self, session: aiohttp.ClientSession, schluessel: str) -> None:
        self._session = session
        self._schluessel = schluessel
        self._cache: dict[tuple[str, str], tuple[datetime, list[dict]]] = {}
        self._endstaende: dict[tuple[str, str, str], dict] = {}
        self._pause_bis: datetime | None = None
        self.verbleibend: int | None = None

    @staticmethod
    def _schluessel_spiel(liga: str, s: dict) -> tuple[str, str, str]:
        return (liga, s.get("anstoss") or "", f"{s.get('heim')}|{s.get('gast')}")

    @staticmethod
    def _offen(s: dict, jetzt: datetime) -> bool:
        """Läuft gerade oder ist vorbei, aber OpenLigaDB kennt noch kein Endergebnis."""
        if s.get("beendet") or not s.get("anstoss"):
            return False
        beginn = dt_util.parse_datetime(s["anstoss"])
        return bool(beginn and beginn <= jetzt <= beginn + APIF_NACHLAUF)

    async def ergaenzen(self, daten: dict) -> None:
        jetzt = dt_util.utcnow()
        for liga, inhalt in daten.items():
            liga_id = APIF_LIGEN.get(liga)
            if liga_id is None:
                continue
            offen = []
            for s in inhalt["spiele"]:
                ende = self._endstaende.get(self._schluessel_spiel(liga, s))
                if s.get("beendet"):
                    continue
                if ende:
                    s.update(ende)
                elif self._offen(s, jetzt):
                    offen.append(s)
            if not offen:
                continue
            tage = sorted({dt_util.parse_datetime(s["anstoss"]).date().isoformat() for s in offen})
            for tag in tage:
                spiele_api = await self._abrufen(liga, liga_id, tag, jetzt)
                if spiele_api:
                    self._zuordnen(liga, [s for s in offen if s["anstoss"].startswith(tag)], spiele_api)

    async def _abrufen(self, liga: str, liga_id: int, tag: str, jetzt: datetime) -> list[dict]:
        cache = self._cache.get((liga, tag))
        if cache and jetzt - cache[0] < APIF_INTERVALL:
            return cache[1]
        if self._pause_bis and jetzt < self._pause_bis:
            return cache[1] if cache else []
        parameter = {
            "league": liga_id,
            "season": saison(dt_util.parse_datetime(f"{tag}T12:00:00+00:00")),
            "date": tag,
            "timezone": "UTC",
        }
        try:
            async with self._session.get(
                APIF_URL,
                params=parameter,
                headers={"x-apisports-key": self._schluessel},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as antwort:
                rest = antwort.headers.get("x-ratelimit-requests-remaining")
                roh = await antwort.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.debug("API-Football-Abruf %s %s fehlgeschlagen: %s", liga, tag, err)
            return cache[1] if cache else []

        if rest is not None and rest.isdigit():
            self.verbleibend = int(rest)
            if self.verbleibend <= APIF_RESERVE:
                morgen = (jetzt + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
                self._pause_bis = morgen
                _LOGGER.warning(
                    "API-Football: nur noch %s Abrufe heute – pausiere bis %s UTC",
                    self.verbleibend, morgen.strftime("%H:%M"),
                )
        if roh.get("errors"):
            _LOGGER.warning("API-Football meldet Fehler: %s", roh["errors"])
            return cache[1] if cache else []
        spiele = roh.get("response") or []
        self._cache[(liga, tag)] = (jetzt, spiele)
        return spiele

    def _zuordnen(self, liga: str, offen: list[dict], spiele_api: list[dict]) -> None:
        for s in offen:
            beginn = dt_util.parse_datetime(s["anstoss"])
            kandidaten = []
            for f in spiele_api:
                zeitstempel = (f.get("fixture") or {}).get("timestamp")
                if zeitstempel is None or abs(zeitstempel - beginn.timestamp()) > 15 * 60:
                    continue
                teams = f.get("teams") or {}
                wert = _aehnlichkeit([s.get("heim"), s.get("heim_name")], (teams.get("home") or {}).get("name")) + \
                    _aehnlichkeit([s.get("gast"), s.get("gast_name")], (teams.get("away") or {}).get("name"))
                kandidaten.append((wert, f))
            if not kandidaten:
                continue
            wert, f = max(kandidaten, key=lambda k: k[0])
            mindest = 0.6 if len(kandidaten) == 1 else 1.0
            if wert < mindest:
                _LOGGER.debug("Kein sicherer API-Football-Treffer für %s – %s (%.2f)", s["heim"], s["gast"], wert)
                continue
            self._uebernehmen(liga, s, f)

    def _uebernehmen(self, liga: str, s: dict, f: dict) -> None:
        status_api = ((f.get("fixture") or {}).get("status") or {})
        kurz = status_api.get("short")
        tore = f.get("goals") or {}
        neu: dict = {"quelle": "api-football", "spielminute": status_api.get("elapsed")}
        if kurz in APIF_LIVE or kurz in APIF_BEENDET:
            neu["tore_heim"] = tore.get("home")
            neu["tore_gast"] = tore.get("away")
        if kurz in APIF_BEENDET:
            neu["beendet"] = True
            neu["status_api"] = "beendet"
        elif kurz in APIF_LIVE:
            neu["status_api"] = "halbzeit" if kurz == "HT" else "live"
        elif kurz in APIF_ABGESAGT:
            neu["status_api"] = "abgesagt"
        else:
            neu["status_api"] = "geplant"
        s.update(neu)
        if kurz in APIF_BEENDET or kurz in APIF_ABGESAGT:
            self._endstaende[self._schluessel_spiel(liga, s)] = neu
