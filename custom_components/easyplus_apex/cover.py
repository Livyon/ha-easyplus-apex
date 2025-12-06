"""Platform for Easyplus Apex cover integration (User Configured via Wizard)."""
import asyncio
import logging
import time
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    DOMAIN, CONF_COVERS, CONF_COVER_NAME, 
    CONF_ADDR_DIR, CONF_ADDR_POWER, 
    CONF_TRAVEL_TIME, CONF_INVERT_DIR
)
from .coordinator import EasyplusCoordinator

_LOGGER = logging.getLogger(__name__)

# States
STATE_OPENING = "opening"
STATE_CLOSING = "closing"
STATE_STOPPED = "stopped"
STATE_UNKNOWN = "unknown"

# Relay Values
CONTROL_START = 1
CONTROL_STOP = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easyplus Apex cover platform from config options."""
    coordinator: EasyplusCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Haal de rolluiken uit de configuratie opties (die de Wizard heeft opgeslagen)
    covers_config = entry.options.get(CONF_COVERS, [])
    
    entities = []
    for cover_conf in covers_config:
        entities.append(
            EasyplusCover(
                coordinator, 
                entry, 
                cover_conf[CONF_COVER_NAME],
                cover_conf[CONF_ADDR_DIR],
                cover_conf[CONF_ADDR_POWER],
                cover_conf[CONF_TRAVEL_TIME],
                cover_conf.get(CONF_INVERT_DIR, False)
            )
        )

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d Easyplus Apex covers from options", len(entities))


class EasyplusCover(CoverEntity):
    """Representation of an Easyplus Apex Cover."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP |
        CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        coordinator: EasyplusCoordinator,
        config_entry: ConfigEntry,
        name: str,
        direction_addr: int,
        control_addr: int,
        travel_time: float,
        invert_direction: bool
    ) -> None:
        """Initialize the cover."""
        self.coordinator = coordinator
        self._config_entry_id = config_entry.entry_id
        self._direction_addr = direction_addr
        self._control_addr = control_addr
        self._travel_time = max(1.0, travel_time)

        # Bepaal open/dicht waarden op basis van invert optie
        if invert_direction:
            self._open_dir_val = 0
            self._close_dir_val = 1
        else:
            self._open_dir_val = 1
            self._close_dir_val = 0

        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_cover_{direction_addr}_{control_addr}"

        self._estimated_position: int | None = None
        self._assumed_state: str = STATE_UNKNOWN
        self._last_move_start_time: float | None = None
        self._start_move_position: int | None = None
        self._stop_timer_unsub: asyncio.TimerHandle | None = None
        self._last_known_direction_state: int | None = None
        self._last_known_control_state: bool | None = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Apex Systems International",
        )

    # --- Properties & Logica ---
    @property
    def current_cover_position(self) -> int | None:
        if self._is_moving:
            self._update_estimated_position()
        return self._estimated_position

    @property
    def is_opening(self) -> bool | None:
        return self._assumed_state == STATE_OPENING

    @property
    def is_closing(self) -> bool | None:
        return self._assumed_state == STATE_CLOSING

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None: return None
        return pos <= 5

    async def _set_direction_and_start(self, direction_value: int) -> bool:
        """Zet richting en start motor."""
        success_dir = await self.coordinator.async_send_command(f"Setrelay {self._direction_addr},{direction_value}")
        if not success_dir: return False
        await asyncio.sleep(0.15)
        success_ctrl = await self.coordinator.async_send_command(f"Setrelay {self._control_addr},{CONTROL_START}")
        return success_ctrl

    async def async_open_cover(self, **kwargs: Any) -> None:
        if self._assumed_state == STATE_CLOSING:
            await self.async_stop_cover()
            await asyncio.sleep(0.2)
        
        if await self._set_direction_and_start(self._open_dir_val):
            self._start_internal_move(STATE_OPENING)
            full_travel_remaining_time = self._calculate_remaining_time(100)
            if full_travel_remaining_time > 0.1:
                self._stop_timer_unsub = async_call_later(
                    self.hass, full_travel_remaining_time, self._async_complete_move
                )
        else:
            await self.async_stop_cover()

    async def async_close_cover(self, **kwargs: Any) -> None:
        if self._assumed_state == STATE_OPENING:
            await self.async_stop_cover()
            await asyncio.sleep(0.2)

        if await self._set_direction_and_start(self._close_dir_val):
            self._start_internal_move(STATE_CLOSING)
            full_travel_remaining_time = self._calculate_remaining_time(0)
            if full_travel_remaining_time > 0.1:
                self._stop_timer_unsub = async_call_later(
                    self.hass, full_travel_remaining_time, self._async_complete_move
                )
        else:
            await self.async_stop_cover()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        self._stop_internal_move()
        await self.coordinator.async_send_command(f"Setrelay {self._control_addr},{CONTROL_STOP}")
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        target_position = kwargs[ATTR_POSITION]
        current_pos = self.current_cover_position
        if current_pos is None: current_pos = 50

        command_success = False
        if target_position > current_pos:
            direction = STATE_OPENING
            command_success = await self._set_direction_and_start(self._open_dir_val)
        elif target_position < current_pos:
            direction = STATE_CLOSING
            command_success = await self._set_direction_and_start(self._close_dir_val)
        else:
            await self.async_stop_cover()
            return

        if command_success:
            self._start_internal_move(direction)
            distance_to_travel = abs(target_position - current_pos)
            time_needed = (distance_to_travel / 100.0) * self._travel_time
            if time_needed > 0.1:
                self._cancel_stop_timer()
                self._stop_timer_unsub = async_call_later(
                    self.hass, time_needed, self._async_stop_cover_callback
                )
            else:
                await asyncio.sleep(0.1)
                await self.async_stop_cover()
        else:
            await self.async_stop_cover()

    def _start_internal_move(self, direction: str) -> None:
        if self._assumed_state == direction and getattr(self, "_last_move_start_time", None) is not None:
            return
        self._cancel_stop_timer()
        self._update_estimated_position()
        current_pos = self._estimated_position
        self._last_move_start_time = time.monotonic()
        self._start_move_position = current_pos if current_pos is not None else (0 if direction == STATE_OPENING else 100)
        self._assumed_state = direction
        self.async_write_ha_state()

    def _stop_internal_move(self) -> None:
        was_moving = self._assumed_state in [STATE_OPENING, STATE_CLOSING]
        self._cancel_stop_timer()
        if was_moving:
            self._update_estimated_position()
        self._assumed_state = STATE_STOPPED
        self._last_move_start_time = None
        self._start_move_position = None

    def _calculate_remaining_time(self, target_position: int) -> float:
        current_pos = self.current_cover_position
        if current_pos is None: return self._travel_time
        remaining_distance = abs(target_position - current_pos)
        return (remaining_distance / 100.0) * self._travel_time

    def _cancel_stop_timer(self):
        if self._stop_timer_unsub:
            self._stop_timer_unsub()
            self._stop_timer_unsub = None

    @callback
    def _async_complete_move(self, *args):
        target_pos = 100 if self._assumed_state == STATE_OPENING else (0 if self._assumed_state == STATE_CLOSING else None)
        if target_pos is not None:
            self._estimated_position = target_pos
            self._stop_internal_move()
            self.hass.async_create_task(
                self.coordinator.async_send_command(f"Setrelay {self._control_addr},{CONTROL_STOP}")
            )
            self.async_write_ha_state()

    @callback
    def _async_stop_cover_callback(self, *args):
        self.hass.async_create_task(self.async_stop_cover())

    def _update_estimated_position(self):
        if self._assumed_state not in [STATE_OPENING, STATE_CLOSING]: return
        start_time = self._last_move_start_time
        start_pos = self._start_move_position
        if start_time is None or start_pos is None: return

        elapsed = time.monotonic() - start_time
        effective_elapsed = min(elapsed, self._travel_time)
        progress = (effective_elapsed / self._travel_time) * 100.0
        
        if self._assumed_state == STATE_OPENING:
            new_pos = start_pos + progress
        else:
            new_pos = start_pos - progress
        
        self._estimated_position = max(0, min(100, int(round(new_pos))))

    @callback
    def _handle_coordinator_update(self) -> None:
        """Luister naar updates van de relais om status te bepalen."""
        dir_state = self.coordinator.get_relay_state(self._direction_addr)
        ctrl_state = self.coordinator.get_relay_state(self._control_addr)
        
        if dir_state is None or ctrl_state is None: return

        if ctrl_state:
            if dir_state == self._open_dir_val:
                if self._assumed_state != STATE_OPENING:
                    if self._assumed_state == STATE_STOPPED:
                        self._start_internal_move(STATE_OPENING)
                    else:
                        self._assumed_state = STATE_OPENING
                    self.async_write_ha_state()
            elif dir_state == self._close_dir_val:
                if self._assumed_state != STATE_CLOSING:
                    if self._assumed_state == STATE_STOPPED:
                        self._start_internal_move(STATE_CLOSING)
                    else:
                        self._assumed_state = STATE_CLOSING
                    self.async_write_ha_state()
        else:
            if self._assumed_state in [STATE_OPENING, STATE_CLOSING]:
                self._stop_internal_move()
                self.async_write_ha_state()

    async def _update_initial_state(self):
        await asyncio.sleep(2.0)
        ctrl_state = self.coordinator.get_relay_state(self._control_addr)
        if ctrl_state == CONTROL_STOP:
            self._estimated_position = 0
            self._assumed_state = STATE_STOPPED
        elif ctrl_state == CONTROL_START:
            self._estimated_position = None
            self._assumed_state = STATE_UNKNOWN

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.add_listener(f"relay_{self._direction_addr}", self._handle_coordinator_update)
        )
        self.async_on_remove(
            self.coordinator.add_listener(f"relay_{self._control_addr}", self._handle_coordinator_update)
        )
        await self._update_initial_state()
        self.async_write_ha_state()

    @property
    def _is_moving(self) -> bool:
        return self._assumed_state in [STATE_OPENING, STATE_CLOSING]