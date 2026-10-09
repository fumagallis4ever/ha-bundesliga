from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from datetime import timedelta

from .const import LIGEN
from .coordinator import LIVE_STATUS, BundesligaCoordinator, im_zeitfenster, status
from .sensor import geraet


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([LiveSensor(entry.runtime_data, entry)])


class LiveSensor(CoordinatorEntity[BundesligaCoordinator], BinarySensorEntity):
    """An, solange ein Spiel kurz bevorsteht, läuft oder gerade beendet wurde."""

    _attr_has_entity_name = True
    _attr_name = "Spiel läuft"
    _attr_icon = "mdi:soccer-field"

    def __init__(self, coordinator: BundesligaCoordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_live"
        self._attr_device_info = geraet(entry)
        self.entity_id = "binary_sensor.bundesliga_live"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._minuetlich, timedelta(minutes=1))
        )

    @callback
    def _minuetlich(self, _now) -> None:
        self.async_write_ha_state()

    def _alle(self):
        for liga, daten in (self.coordinator.data or {}).items():
            for s in daten["spiele"]:
                yield liga, s

    @property
    def is_on(self) -> bool:
        jetzt = dt_util.utcnow()
        return any(im_zeitfenster(s, jetzt) for _, s in self._alle())

    @property
    def extra_state_attributes(self):
        jetzt = dt_util.utcnow()
        live = [
            f"{LIGEN.get(liga, liga)}: {s['heim']} – {s['gast']}"
            for liga, s in self._alle() if status(s, jetzt) in LIVE_STATUS
        ]
        attribute = {"live_spiele": live, "anzahl_live": len(live)}
        if self.coordinator.api_football and self.coordinator.api_football.verbleibend is not None:
            attribute["api_football_abrufe_uebrig"] = self.coordinator.api_football.verbleibend
        return attribute
