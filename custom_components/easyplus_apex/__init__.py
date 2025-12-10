"""The Easyplus Apex System integration."""
import asyncio
import logging
import re
import xml.etree.ElementTree as ET

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN, CONF_HOST, CONF_PORT, 
    CONF_XML_CONTENT, CONF_COVERS, CONF_NAMING_MAP, 
    CONF_XML_SWITCHES, CONF_XML_DIMMERS,
    CONF_COVER_NAME, CONF_ADDR_DIR, CONF_ADDR_POWER, 
    CONF_TRAVEL_TIME, CONF_STRICT_MODE
)
from .coordinator import EasyplusCoordinator

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.COVER]

_LOGGER = logging.getLogger(__name__)

# Regex om "rommel" namen te herkennen uit de XML
JUNK_NAME_PATTERN = re.compile(r"^(Re \+\d+|relay \d+|Ch \d+|In \d+|\d+)$", re.IGNORECASE)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easyplus Apex from a config entry."""
    
    # 1. Verwerk XML (indien aanwezig)
    if CONF_XML_CONTENT in entry.options:
        _LOGGER.info("Processing imported XML configuration with Smart Filtering...")
        await parse_and_apply_xml(hass, entry)

    # 2. Verbinden
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    coordinator = EasyplusCoordinator(hass, entry)

    if not await coordinator.connect():
        raise ConfigEntryNotReady(f"Failed connection to {host}:{port}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 3. Listeners & Background tasks
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    entry.async_create_background_task(
        hass,
        coordinator._receive_loop(),
        name=f"Easyplus Apex Receive Loop - {entry.entry_id}"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 4. INITIAL STATE FETCH
    if entry.options.get(CONF_STRICT_MODE, False):
        _LOGGER.debug("Strict Mode active: Fetching initial states...")
        await asyncio.sleep(1)
        await coordinator.fetch_initial_states()
    else:
        _LOGGER.info("Auto-Discovery Mode: Waiting for user activity (Discovery by Use).")

    return True

async def parse_and_apply_xml(hass: HomeAssistant, entry: ConfigEntry):
    """Parse de XML, filter rommel, en scheid Switches van Dimmers (zonder dubbels)."""
    xml_content = entry.options[CONF_XML_CONTENT]
    new_options = dict(entry.options)
    
    naming_map = {}
    covers = []
    
    # AANGEPAST: Gebruik 'set' in plaats van 'list' om dubbele adressen te voorkomen
    valid_switches = set()
    valid_dimmers = set()
    
    try:
        root = ET.fromstring(xml_content)
        
        for item in root.iter():
            if item.tag not in ['digout', 'dim']:
                continue

            try:
                address = int(item.get('adr'))
                raw_name = item.get('name', "")
                name = raw_name.strip()
                item_type = item.get('type') # light, dimmer, shutter
                tag = item.tag # 'dim' of 'digout'

                if not name: continue

                # FILTER: Is het rommel?
                is_junk = JUNK_NAME_PATTERN.match(name)
                
                # Uitzondering: Rolluiken mogen rommel-namen hebben
                if is_junk and item_type != 'shutter':
                    continue

                naming_map[str(address)] = name

                if item_type == 'shutter':
                    # Rolluiken checken we handmatig op dubbels in de lijst
                    # (Sets werken niet direct met dicts, dus eenvoudige check)
                    existing_ids = [c[CONF_ADDR_DIR] for c in covers]
                    if address not in existing_ids:
                        covers.append({
                            CONF_COVER_NAME: name,
                            CONF_ADDR_DIR: address,
                            CONF_ADDR_POWER: address + 1,
                            CONF_TRAVEL_TIME: 25.0,
                            "origin": "xml"
                        })
                elif tag == 'dim':
                    valid_dimmers.add(address) # .add() voor sets
                elif tag == 'digout':
                    valid_switches.add(address) # .add() voor sets
                        
            except (ValueError, TypeError):
                continue

        new_options[CONF_NAMING_MAP] = naming_map
        new_options[CONF_COVERS] = covers
        # AANGEPAST: Converteer sets terug naar lijsten voor opslag in JSON
        new_options[CONF_XML_SWITCHES] = list(valid_switches)
        new_options[CONF_XML_DIMMERS] = list(valid_dimmers)
        new_options[CONF_STRICT_MODE] = True
        new_options.pop(CONF_XML_CONTENT)

        hass.config_entries.async_update_entry(entry, options=new_options)
        _LOGGER.info(f"XML Import: {len(valid_switches)} switches, {len(valid_dimmers)} dimmers, {len(covers)} covers.")

    except ET.ParseError as err:
        _LOGGER.error(f"Could not parse XML: {err}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and coordinator:
        await coordinator.stop()
        await asyncio.sleep(1.0)
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
