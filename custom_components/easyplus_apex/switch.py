"""Platform for Easyplus Apex switch integration (Smart XML Support)."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, 
    CONF_COVERS, 
    CONF_ADDR_DIR, 
    CONF_ADDR_POWER,
    CONF_NAMING_MAP,
    CONF_STRICT_MODE,
    CONF_XML_SWITCHES # Nieuw
)
from .coordinator import EasyplusCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches using the filtered XML list."""
    coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]

    naming_map = entry.options.get(CONF_NAMING_MAP, {})
    strict_mode = entry.options.get(CONF_STRICT_MODE, False)
    # Haal de "schone" lijst op
    xml_switches = entry.options.get(CONF_XML_SWITCHES, [])

    # Relais in gebruik door rolluiken (voor de zekerheid)
    used_by_covers = set()
    covers_config = entry.options.get(CONF_COVERS, [])
    for cover in covers_config:
        try:
            used_by_covers.add(int(cover[CONF_ADDR_DIR]))
            used_by_covers.add(int(cover[CONF_ADDR_POWER]))
        except (ValueError, KeyError):
            continue

    @callback
    def async_add_switch(address: int):
        # 1. Check Rolluiken
        if address in used_by_covers: return

        # 2. STRICT MODE LOGICA
        if strict_mode:
            # Als we in strict mode zijn, MOET het adres in de 'xml_switches' lijst staan.
            # Deze lijst bevat GEEN dimmers en GEEN rommel-namen meer.
            if address not in xml_switches:
                return

        # 3. Naam Bepalen
        xml_name = naming_map.get(str(address))
        if xml_name:
            name = xml_name
        else:
            name = f"Apex Relay {address}"

        async_add_entities([EasyplusSwitch(coordinator, entry, address, name)])

    # Als we Strict Mode (XML) gebruiken, itereren we direct over de schone lijst
    if strict_mode and xml_switches:
        for address in xml_switches:
            async_add_switch(address)
    else:
        # Fallback voor auto-discovery
        coordinator.listen_for_new_relays(async_add_switch)
        for address in coordinator.known_relays:
            async_add_switch(address)


class EasyplusSwitch(SwitchEntity):
    """Representation of an Easyplus Apex Switch."""
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, address, name):
        self.coordinator = coordinator
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_relay_{address}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Apex Systems International",
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.get_relay_state(self._address)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(f"Setrelay {self._address},1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(f"Setrelay {self._address},0")

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.add_listener(f"relay_{self._address}", self._handle_coordinator_update)
        )
