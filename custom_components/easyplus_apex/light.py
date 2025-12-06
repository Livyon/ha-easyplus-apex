"""Platform for Easyplus Apex light integration (Auto-Discovery)."""
import logging
from typing import Any

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EasyplusCoordinator

_LOGGER = logging.getLogger(__name__)

# Constants
DEFAULT_SLOPE = 10
EPC_MIN = 60
EPC_MAX = 255
HA_MIN = 1
HA_MAX = 255

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easyplus Apex light platform with Auto-Discovery."""
    coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_add_dimmer(address: int):
        """Maak een dimmer entiteit aan wanneer ontdekt."""
        _LOGGER.info("Creating light entity for address %s", address)
        name = f"Apex Dimmer {address}"
        async_add_entities([EasyplusLight(coordinator, entry, address, name)])

    # Registreer de callback
    coordinator.listen_for_new_dimmers(async_add_dimmer)

    # Check reeds ontdekte
    for address in coordinator.known_dimmers:
        async_add_dimmer(address)


class EasyplusLight(LightEntity):
    """Representation of an Easyplus Apex Dimmer."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator, config_entry, address, name):
        self.coordinator = coordinator
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_dimmer_{address}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Apex Systems International",
        )

    @property
    def brightness(self) -> int | None:
        val = self.coordinator.get_dimmer_state(self._address)
        if val is None or val < EPC_MIN:
            return None
        # Convert EPC to HA
        return int(HA_MIN + (val - EPC_MIN) * ((HA_MAX - HA_MIN) / (EPC_MAX - EPC_MIN)))

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.get_dimmer_state(self._address)
        return val is not None and val >= EPC_MIN

    async def async_turn_on(self, **kwargs: Any) -> None:
        ha_bri = kwargs.get(ATTR_BRIGHTNESS, 255)
        # Convert HA to EPC
        epc_bri = int(EPC_MIN + (ha_bri - HA_MIN) * ((EPC_MAX - EPC_MIN) / (HA_MAX - HA_MIN)))
        await self.coordinator.async_send_command(f"SetDimmer {self._address},{epc_bri},{DEFAULT_SLOPE}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(f"SetDimmer {self._address},0,{DEFAULT_SLOPE}")

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.add_listener(f"dimmer_{self._address}", self._handle_coordinator_update)
        )