"""Platform for Easyplus Apex pushbuttons (digitale ingangen) als event entiteiten."""
import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, CONF_INPUT_NAMES, LONG_PRESS_TIME
from .coordinator import EasyplusCoordinator

_LOGGER = logging.getLogger(__name__)

EVENT_PRESS = "press"
EVENT_RELEASE = "release"
EVENT_SHORT_PRESS = "short_press"
EVENT_LONG_PRESS = "long_press"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak een event entiteit per drukknop.

    Drukknoppen staan meestal niet in de XML export, dus ze worden aangemaakt
    zodra ze voor het eerst gebruikt worden ("Discovery by Use"). Eerder gevonden
    knoppen worden bij het opstarten terug aangemaakt vanuit het entiteitenregister,
    zodat ook de eerste druk na een herstart niet verloren gaat.
    """
    coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]
    input_names = entry.options.get(CONF_INPUT_NAMES, {})
    prefix = f"{entry.entry_id}_input_"

    @callback
    def async_add_input(address: int):
        name = input_names.get(str(address), f"Apex Input {address}")
        async_add_entities([EasyplusButtonEvent(coordinator, entry, address, name)])

    # 1. Knoppen die al eerder gezien werden (entiteitenregister) of in de XML staan
    addresses: set[int] = set()
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.domain == "event" and reg_entry.unique_id.startswith(prefix):
            try:
                addresses.add(int(reg_entry.unique_id[len(prefix):]))
            except ValueError:
                continue
    for address in input_names:
        try:
            addresses.add(int(address))
        except ValueError:
            continue

    coordinator.known_inputs.update(addresses)
    for address in sorted(addresses):
        async_add_input(address)

    # 2. Nieuwe knoppen: aanmaken bij het eerste gebruik
    coordinator.listen_for_new_inputs(async_add_input)


class EasyplusButtonEvent(EventEntity):
    """Een Easyplus drukknop (digitale ingang)."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_translation_key = "pushbutton"
    _attr_event_types = [EVENT_PRESS, EVENT_RELEASE, EVENT_SHORT_PRESS, EVENT_LONG_PRESS]

    def __init__(self, coordinator, config_entry, address, name):
        self.coordinator = coordinator
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_input_{address}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Apex Systems International",
        )
        self._pressed = False
        self._long_fired = False
        self._cancel_long = None

    @callback
    def _handle_input(self, pressed: bool) -> None:
        attrs = {"input": self._address}
        if pressed:
            if self._pressed:
                return  # dubbel ON bericht negeren
            self._pressed = True
            self._long_fired = False
            self._cancel_long_timer()
            self._cancel_long = async_call_later(self.hass, LONG_PRESS_TIME, self._long_press)
            self._fire(EVENT_PRESS, attrs)
        else:
            if not self._pressed:
                return  # OFF zonder voorafgaande ON (bv. na herverbinden)
            self._pressed = False
            self._cancel_long_timer()
            self._fire(EVENT_RELEASE, attrs)
            if not self._long_fired:
                self._fire(EVENT_SHORT_PRESS, attrs)

    @callback
    def _fire(self, event_type: str, attrs: dict) -> None:
        # Elk event apart wegschrijven, anders ziet een automatisering enkel het laatste
        self._trigger_event(event_type, attrs)
        self.async_write_ha_state()

    @callback
    def _long_press(self, _now) -> None:
        self._cancel_long = None
        if self._pressed:
            self._long_fired = True
            self._fire(EVENT_LONG_PRESS, {"input": self._address})

    @callback
    def _cancel_long_timer(self) -> None:
        if self._cancel_long:
            self._cancel_long()
            self._cancel_long = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.add_input_listener(self._address, self._handle_input)
        )
        self.async_on_remove(self._cancel_long_timer)
