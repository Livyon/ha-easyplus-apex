"""The Easyplus Apex System integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_HOST, CONF_PORT
from .coordinator import EasyplusCoordinator

# Platforms: Switch en Light zijn nu dynamisch. Cover (rolluiken) nog even handmatig of later doen.
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.COVER]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easyplus Apex from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    _LOGGER.info("Setting up Easyplus Apex integration for %s:%s", host, port)

    coordinator = EasyplusCoordinator(hass, entry)

    if not await coordinator.connect():
        raise ConfigEntryNotReady(f"Failed initial connection/auth to Easyplus Apex at {host}:{port}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _LOGGER.info("Coordinator created and connection/auth successful.")

    entry.async_create_background_task(
        hass,
        coordinator._receive_loop(),
        name=f"Easyplus Apex Receive Loop - {entry.entry_id}"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Platform setup forwarded for: %s", PLATFORMS)

    # --- TRIGGER AUTO-DISCOVERY ---
    # Wacht 1 seconde en vraag dan alle data op. De antwoorden triggeren het aanmaken van entities.
    await asyncio.sleep(1)
    await coordinator.fetch_initial_states()
    # ------------------------------

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Easyplus Apex integration")
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and coordinator:
        await coordinator.stop()
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok