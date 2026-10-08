from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LIGEN
from .coordinator import BundesligaCoordinator, anstoss, status


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: BundesligaCoordinator = entry.runtime_data
    async_add_entities(LigaSensor(coordinator, entry, liga) for liga in coordinator.ligen)


def geraet(entry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Bundesliga",
        manufacturer="OpenLigaDB",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.openligadb.de/",
    )


class LigaSensor(CoordinatorEntity[BundesligaCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:soccer"

    def __init__(self, coordinator: BundesligaCoordinator, entry, liga: str) -> None:
        super().__init__(coordinator)
        self.liga = liga
        self._attr_name = LIGEN.get(liga, liga)
        self._attr_unique_id = f"{entry.entry_id}_{liga}"
        self._attr_device_info = geraet(entry)
        self.entity_id = f"sensor.bundesliga_{liga}"

    @property
    def _liga(self) -> dict:
        return (self.coordinator.data or {}).get(self.liga, {"spieltag": None, "spiele": []})

    @property
    def native_value(self):
        return self._liga["spieltag"]

    @property
    def extra_state_attributes(self):
        jetzt = dt_util.utcnow()
        heute = dt_util.now().date()
        spiele = []
        for s in self._liga["spiele"]:
            beginn = anstoss(s)
            spiele.append(
                {
                    **s,
                    "status": status(s, jetzt),
                    "heute": bool(beginn and dt_util.as_local(beginn).date() == heute),
                }
            )
        return {
            "liga": LIGEN.get(self.liga, self.liga),
            "kuerzel": self.liga,
            "live": sum(1 for s in spiele if s["status"] == "live"),
            "spiele_heute": sum(1 for s in spiele if s["heute"]),
            "spiele": spiele,
        }
