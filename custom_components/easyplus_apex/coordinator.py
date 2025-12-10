"""Coordinator voor de Easyplus Apex System integratie."""

import asyncio
import logging

from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)

class EasyplusCoordinator:
    """Beheert de verbinding en data-uitwisseling."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialiseer de coordinator."""
        self.hass = hass
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._password = entry.data[CONF_PASSWORD]

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._is_connected = False
        self._connect_lock = asyncio.Lock()
        self._shutdown_requested = False
        self._send_lock = asyncio.Lock()

        # State
        self._relay_states: dict[int, bool] = {}
        self._dimmer_states: dict[int, int] = {}
        
        # Discovery Sets
        self.known_relays: set[int] = set()
        self.known_dimmers: set[int] = set()

        # Listeners
        self._listeners: dict[str, list] = {}
        self._new_relay_callbacks = []
        self._new_dimmer_callbacks = []
        
        # Tijdelijke listeners voor de "Discovery by Use" wizard
        self._activity_callbacks = []

    # --- "Discovery by Use" Logica ---
    async def detect_activity(self, duration: int = 10) -> set[int]:
        """Luister gedurende x seconden naar actieve relais."""
        _LOGGER.info("Starting 'Discovery by Use' for %s seconds", duration)
        active_relays = set()

        @callback
        def _capture_activity(address: int):
            _LOGGER.debug("Activity detected on relay %s", address)
            active_relays.add(address)

        # Voeg tijdelijke listener toe
        self._activity_callbacks.append(_capture_activity)

        # Wacht (blokkeert niet de loop, maar wacht wel hier)
        await asyncio.sleep(duration)

        # Verwijder listener
        if _capture_activity in self._activity_callbacks:
            self._activity_callbacks.remove(_capture_activity)

        _LOGGER.info("Discovery finished. Found relays: %s", active_relays)
        return active_relays
    # ---------------------------------

    def listen_for_new_relays(self, callback_func):
        self._new_relay_callbacks.append(callback_func)

    def listen_for_new_dimmers(self, callback_func):
        self._new_dimmer_callbacks.append(callback_func)

    async def connect(self) -> bool:
        async with self._connect_lock:
            if self._is_connected: return True
            if self._shutdown_requested: return False
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port), timeout=10
                )
                if await self._authenticate():
                    self._is_connected = True
                    return True
                else:
                    await self.disconnect()
                    return False
            except Exception:
                await self.disconnect()
                return False

    async def _authenticate(self) -> bool:
        try:
            ready = False
            for _ in range(10):
                line = await asyncio.wait_for(self._reader.readuntil(b'\n'), timeout=2)
                if b">Ready" in line:
                    ready = True
                    break
            if not ready: return False
            self._writer.write(f"Pass {self._password}\n".encode('ascii'))
            await self._writer.drain()
            await asyncio.sleep(0.5)
            return not self._reader.at_eof()
        except Exception: return False

    async def _receive_loop(self) -> None:
        try:
            while self._is_connected:
                data = await self._reader.readuntil(b'\n')
                line = data.decode('ascii', errors='ignore').strip()
                if line: self._parse_line(line)
        except Exception: pass
        finally:
            self._is_connected = False

    def _parse_line(self, line: str) -> None:
        if not line.startswith(">"): return
        try:
            parts = line[1:].split(' ', 1)
            cmd = parts[0]
            params = parts[1] if len(parts) > 1 else ""
            if cmd == "DigitalOut":
                p = params.split(',')
                if len(p) == 2: self._update_relay_state(int(p[0]), p[1] == "ON")
            elif cmd == "AnalogOut":
                p = params.split(',')
                if len(p) == 2: self._update_dimmer_state(int(p[0]), int(p[1]))
        except Exception: pass

    def _update_relay_state(self, address: int, state: bool):
        # 1. Update de status
        changed = self._relay_states.get(address) != state
        self._relay_states[address] = state

        # 2. Trigger Discovery (Auto-create entities)
        if address not in self.known_relays:
            self.known_relays.add(address)
            for cb in self._new_relay_callbacks: cb(address)

        # 3. Trigger Activity Listeners (Voor de Wizard!)
        # We sturen dit ALTIJD, ook als het relais al bekend is
        for cb in self._activity_callbacks:
            cb(address)

        # 4. Update HA Entities
        if changed:
            self._notify_listeners(f"relay_{address}")

    def _update_dimmer_state(self, address: int, value: int):
        if address not in self.known_dimmers:
            self.known_dimmers.add(address)
            for cb in self._new_dimmer_callbacks: cb(address)
        
        value = max(0, min(255, value))
        if self._dimmer_states.get(address) != value:
            self._dimmer_states[address] = value
            self._notify_listeners(f"dimmer_{address}")

    def get_relay_state(self, address: int) -> bool | None:
        return self._relay_states.get(address)

    def get_dimmer_state(self, address: int) -> int | None:
        return self._dimmer_states.get(address)

    def add_listener(self, key: str, callback_func):
        self._listeners.setdefault(key, []).append(callback_func)
        return lambda: self._listeners[key].remove(callback_func)

    def _notify_listeners(self, key: str):
        if key in self._listeners:
            for cb in self._listeners[key]: cb()

    async def fetch_initial_states(self) -> None:
        await self.async_send_command("GetData")

    async def async_send_command(self, command: str) -> bool:
        if not self._is_connected or not self._writer: return False
        async with self._send_lock:
            try:
                self._writer.write(f"{command}\n".encode('ascii'))
                await self._writer.drain()
                return True
            except Exception: return False

    async def disconnect(self):
        self._is_connected = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception: pass
        self._writer = None
        self._reader = None

    async def stop(self):
        self._shutdown_requested = True
        await self.disconnect()
        await asyncio.sleep(1.0)
