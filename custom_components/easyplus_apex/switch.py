"""Platform for Easyplus Apex switch integration (Auto-Discovery)."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EasyplusCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easyplus Apex switch platform with Auto-Discovery."""
    coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_add_switch(address: int):
        """Maak een switch entiteit aan wanneer ontdekt."""
        _LOGGER.info("Creating switch entity for address %s", address)
        # We geven nu een generieke naam. De gebruiker kan dit hernoemen in HA.
        name = f"Apex Relay {address}" 
        async_add_entities([EasyplusSwitch(coordinator, entry, address, name)])

    # Registreer de callback bij de coordinator
    coordinator.listen_for_new_relays(async_add_switch)
    
    # Check voor reeds ontdekte apparaten (voor het geval dit platform later laadt)
    for address in coordinator.known_relays:
        async_add_switch(address)


class EasyplusSwitch(SwitchEntity):
    """Representation of an Easyplus Apex Switch."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyplusCoordinator,
        config_entry: ConfigEntry,
        address: int,
        name: str
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._address = address
        
        self._attr_name = name
        # Unieke ID is cruciaal voor hernoemen in UI!
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
        listener_key = f"relay_{self._address}"
        self.async_on_remove(
            self.coordinator.add_listener(listener_key, self._handle_coordinator_update)
        )