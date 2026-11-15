"""Baseline functional & structural tests for Easyplus Apex."""
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, EVENT_STATE_CHANGED, Platform
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.easyplus_apex import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
    parse_and_apply_xml,
)
from custom_components.easyplus_apex.config_flow import (
    EasyplusApexConfigFlow,
    EasyplusOptionsFlowHandler,
)
from custom_components.easyplus_apex.const import (
    CONF_COVERS,
    CONF_INPUT_NAMES,
    CONF_NAMING_MAP,
    CONF_STRICT_MODE,
    CONF_XML_CONTENT,
    CONF_XML_DIMMERS,
    CONF_XML_SWITCHES,
    DOMAIN,
    LONG_PRESS_TIME,
)
from custom_components.easyplus_apex.coordinator import EasyplusCoordinator
from custom_components.easyplus_apex.cover import EasyplusCover
from custom_components.easyplus_apex.event import EasyplusButtonEvent
from custom_components.easyplus_apex.light import EasyplusLight
from custom_components.easyplus_apex.switch import EasyplusSwitch

COMPONENT_DIR = Path("custom_components/easyplus_apex")


def test_manifest_and_translations_structure():
    """Verify required manifest keys and translation JSON parity."""
    manifest = json.loads((COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8"))
    for key in ("domain", "name", "codeowners", "config_flow", "iot_class", "version"):
        assert key in manifest, f"Missing '{key}' in manifest.json"
    assert manifest["domain"] == DOMAIN

    strings = json.loads((COMPONENT_DIR / "strings.json").read_text(encoding="utf-8"))
    assert "config" in strings and "options" in strings

    translations_dir = COMPONENT_DIR / "translations"
    if translations_dir.exists():
        for lang_file in translations_dir.glob("*.json"):
            data = json.loads(lang_file.read_text(encoding="utf-8"))
            assert "config" in data and "options" in data, f"Missing sections in {lang_file}"


def test_core_symbols_present():
    """Verify required integration platforms and core classes exist."""
    assert Platform.SWITCH in PLATFORMS
    assert Platform.LIGHT in PLATFORMS
    assert Platform.COVER in PLATFORMS
    assert Platform.EVENT in PLATFORMS    
    assert callable(async_setup_entry)
    assert callable(async_unload_entry)
    assert callable(parse_and_apply_xml)
    assert EasyplusCoordinator is not None
    assert EasyplusApexConfigFlow is not None
    assert EasyplusOptionsFlowHandler is not None
    assert EasyplusSwitch is not None
    assert EasyplusLight is not None
    assert EasyplusCover is not None
    assert EasyplusButtonEvent is not None


async def test_parse_and_apply_xml(hass):
    """Verify XML parsing filters junk names and separates switches, dimmers, and covers."""
    sample_xml = """
    <config>
        <digout adr="1" name="Woonkamer Lamp" type="light" />
        <digout adr="2" name="Re +02" type="light" />
        <digout adr="10" name="Rolluik Keuken" type="shutter" />
        <dim adr="5" name="Eettafel Dimmer" type="dimmer" />
        <digin adr="69" name="Voordeur Bel" />
        <digin adr="70" name="In 70" />        
    </config>
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_PORT: 2024, CONF_PASSWORD: "pass"},
        options={CONF_XML_CONTENT: sample_xml},
    )
    entry.add_to_hass(hass)

    await parse_and_apply_xml(hass, entry)

    assert entry.options[CONF_STRICT_MODE] is True
    assert CONF_XML_CONTENT not in entry.options
    assert entry.options[CONF_XML_SWITCHES] == [1]
    assert entry.options[CONF_XML_DIMMERS] == [5]
    assert entry.options[CONF_NAMING_MAP]["1"] == "Woonkamer Lamp"
    assert "2" not in entry.options[CONF_NAMING_MAP]
    assert entry.options[CONF_INPUT_NAMES] == {"69": "Voordeur Bel"}
    assert len(entry.options[CONF_COVERS]) == 1
    assert entry.options[CONF_COVERS][0]["address_direction"] == 10
    assert entry.options[CONF_COVERS][0]["address_power"] == 11


def test_coordinator_protocol_parsing(hass):
    """Verify coordinator parses DigitalOut and AnalogOut lines accurately."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_PORT: 2024, CONF_PASSWORD: "pass"},
    )
    bus_events = async_capture_events(hass, f"{DOMAIN}_input")
    coordinator = EasyplusCoordinator(hass, entry)

    coordinator._parse_line(">DigitalOut 12,ON")
    coordinator._parse_line(">AnalogOut 5,180")
    coordinator._parse_line(">DigitalIn 69,ON")

    assert coordinator.get_relay_state(12) is True
    assert 12 in coordinator.known_relays
    assert coordinator.get_dimmer_state(5) == 180
    assert 5 in coordinator.known_dimmers
    assert 69 in coordinator.known_inputs
    assert len(bus_events) == 1
    assert bus_events[0].data == {"input": 69, "state": "on"}    


def test_cover_direction_inversion(hass):
    """Verify EasyplusCover direction values respect invert_direction."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_PORT: 2024, CONF_PASSWORD: "pass"},
    )
    coordinator = EasyplusCoordinator(hass, entry)

    normal = EasyplusCover(coordinator, entry, "Normal", 10, 11, 20.0, False)
    inverted = EasyplusCover(coordinator, entry, "Inverted", 12, 13, 20.0, True)

    assert (normal._open_dir_val, normal._close_dir_val) == (1, 0)
    assert (inverted._open_dir_val, inverted._close_dir_val) == (0, 1)
    assert normal.is_closed is False


async def test_pushbutton_first_press_short_and_long(hass):
    """Verify first-press discovery buffering, short_press, and long_press events."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_PORT: 2024, CONF_PASSWORD: "pass"},
        options={},
    )
    entry.add_to_hass(hass)

    captured = async_capture_events(hass, EVENT_STATE_CHANGED)

    with (
        patch.object(EasyplusCoordinator, "connect", return_value=True),
        patch.object(EasyplusCoordinator, "_receive_loop", return_value=None),
        patch.object(EasyplusCoordinator, "fetch_initial_states", return_value=None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]

        # 1. Regressietest: allereerste korte druk op een nog onbekende knop (69)
        coordinator._parse_line(">DigitalIn 69,ON")
        coordinator._parse_line(">DigitalIn 69,OFF")
        await hass.async_block_till_done()

        input_69_events = [
            e.data["new_state"].attributes.get("event_type")
            for e in captured
            if e.data.get("entity_id", "").endswith("_69")
            and e.data.get("new_state") is not None
            and e.data["new_state"].attributes.get("event_type") is not None
        ]
        assert input_69_events == ["press", "release", "short_press"]

        # 2. Long press flow op knop 70 (ingedrukt -> > 0.8s wachten -> losgelaten)
        coordinator._parse_line(">DigitalIn 70,ON")
        await hass.async_block_till_done()

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=LONG_PRESS_TIME + 0.1))
        await hass.async_block_till_done()

        coordinator._parse_line(">DigitalIn 70,OFF")
        await hass.async_block_till_done()

        input_70_events = [
            e.data["new_state"].attributes.get("event_type")
            for e in captured
            if e.data.get("entity_id", "").endswith("_70")
            and e.data.get("new_state") is not None
            and e.data["new_state"].attributes.get("event_type") is not None
        ]
        assert input_70_events == ["press", "long_press", "release"]

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()    
