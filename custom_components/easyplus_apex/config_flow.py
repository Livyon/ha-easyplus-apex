"""Config flow for Easyplus Apex System integration."""
import logging
import asyncio
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, CONF_HOST, CONF_PORT, CONF_PASSWORD,
    CONF_COVERS, CONF_COVER_NAME, CONF_ADDR_DIR, 
    CONF_ADDR_POWER, CONF_TRAVEL_TIME, CONF_INVERT_DIR
)

_LOGGER = logging.getLogger(__name__)

# Basis schema
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=2024): int,
    vol.Required(CONF_PASSWORD): str,
})

async def validate_input(host: str, port: int, password: str) -> dict[str, str]:
    """Validate connection."""
    _LOGGER.info("Validating connection to Easyplus Apex at %s:%s", host, port)
    reader = None
    writer = None
    try:
        # Stap 1: Verbinden
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=10
        )

        # Stap 2: Lees banner tot ">Ready"
        ready_received = False
        try:
            for _ in range(10): # Max 10 lijnen lezen
                line_bytes = await asyncio.wait_for(reader.readuntil(b'\n'), timeout=2)
                line = line_bytes.decode('ascii').strip()
                if line.lstrip().startswith(">Ready"):
                    ready_received = True
                    break

            if not ready_received:
                raise CannotConnect("Did not receive '>Ready' prompt.")

        except Exception as e:
            raise CannotConnect(f"Error reading banner: {e}")

        # Stap 3: Stuur wachtwoord
        pass_cmd = f"Pass {password}\n"
        writer.write(pass_cmd.encode('ascii'))
        await writer.drain()

        # Stap 4: Verifieer succes
        try:
            await asyncio.wait_for(reader.read(1), timeout=0.5)
        except asyncio.TimeoutError:
            pass 
        except asyncio.IncompleteReadError:
            raise InvalidAuth("Connection closed after password.")
        
        return {"title": f"Easyplus Apex ({host})"}

    except (InvalidAuth, CannotConnect) as err:
        raise err
    except Exception as err:
        _LOGGER.exception("Unexpected error")
        raise CannotConnect(f"Unexpected error: {err}")
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

class EasyplusApexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Easyplus Apex System."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EasyplusOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_PASSWORD],
                )
                return self.async_create_entry(title=info["title"], data=user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class EasyplusOptionsFlowHandler(OptionsFlow):
    """Handle Easyplus options (Manage Covers with Detection)."""

    def __init__(self, config_entry):
        # AANGEPAST: We gebruiken 'self.entry' in plaats van 'self.config_entry'
        # om conflicten met de base class property te vermijden.
        self.entry = config_entry 
        self.covers = self.entry.options.get(CONF_COVERS, [])
        self.detected_ids = []

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Start menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["detect_cover_start", "add_cover_manual", "remove_cover"]
        )

    # --- WIZARD STAP 1: Instructie ---
    async def async_step_detect_cover_start(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            # Gebruiker klikt op 'Verzenden' -> Start luisteren
            return await self.async_step_detect_listening()

        return self.async_show_form(
            step_id="detect_cover_start",
            description_placeholders={},
            data_schema=vol.Schema({}), # Alleen een knop
            last_step=False
        )

    # --- WIZARD STAP 2: Luisteren (10 sec) ---
    async def async_step_detect_listening(self, user_input=None) -> ConfigFlowResult:
        # Gebruik self.entry.entry_id
        coordinator = self.hass.data[DOMAIN][self.entry.entry_id]
        
        # Dit blokkeert de UI voor 10 seconden terwijl de gebruiker op de knop duwt
        changed_relays = await coordinator.detect_activity(duration=10)
        
        self.detected_ids = sorted(list(changed_relays))

        if len(self.detected_ids) < 2:
            return self.async_show_form(step_id="detect_failed", errors={"base": "too_few_relays"})
        
        # Als we meer dan 2 vinden, pakken we de eerste 2. 
        return await self.async_step_detect_confirm()

    # --- WIZARD STAP 3: Bevestigen ---
    async def async_step_detect_confirm(self, user_input=None) -> ConfigFlowResult:
        r1 = self.detected_ids[0]
        r2 = self.detected_ids[1]

        if user_input is not None:
            new_cover = {
                CONF_COVER_NAME: user_input[CONF_COVER_NAME],
                CONF_ADDR_DIR: int(user_input[CONF_ADDR_DIR]),
                CONF_ADDR_POWER: int(user_input[CONF_ADDR_POWER]),
                CONF_TRAVEL_TIME: user_input[CONF_TRAVEL_TIME],
                CONF_INVERT_DIR: user_input[CONF_INVERT_DIR]
            }
            self.covers.append(new_cover)
            return self.async_create_entry(title="", data={CONF_COVERS: self.covers})

        return self.async_show_form(
            step_id="detect_confirm",
            description_placeholders={"r1": str(r1), "r2": str(r2)},
            data_schema=vol.Schema({
                vol.Required(CONF_COVER_NAME): str,
                vol.Required(CONF_ADDR_DIR, default=r1): int,
                vol.Required(CONF_ADDR_POWER, default=r2): int,
                vol.Required(CONF_TRAVEL_TIME, default=25.0): float,
                vol.Optional(CONF_INVERT_DIR, default=False): bool,
            })
        )

    async def async_step_detect_failed(self, user_input=None) -> ConfigFlowResult:
        return await self.async_step_init()

    # --- HANDMATIG (Fallback) ---
    async def async_step_add_cover_manual(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self.covers.append(user_input)
            return self.async_create_entry(title="", data={CONF_COVERS: self.covers})

        return self.async_show_form(
            step_id="add_cover_manual",
            data_schema=vol.Schema({
                vol.Required(CONF_COVER_NAME): str,
                vol.Required(CONF_ADDR_DIR): int,
                vol.Required(CONF_ADDR_POWER): int,
                vol.Required(CONF_TRAVEL_TIME, default=25.0): float,
                vol.Optional(CONF_INVERT_DIR, default=False): bool,
            })
        )

    # --- VERWIJDEREN ---
    async def async_step_remove_cover(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input[CONF_COVER_NAME]
            self.covers = [c for c in self.covers if c[CONF_COVER_NAME] != name]
            return self.async_create_entry(title="", data={CONF_COVERS: self.covers})

        if not self.covers:
            return self.async_abort(reason="No covers to remove")

        names = [c[CONF_COVER_NAME] for c in self.covers]
        return self.async_show_form(
            step_id="remove_cover",
            data_schema=vol.Schema({vol.Required(CONF_COVER_NAME): vol.In(names)})
        )

class CannotConnect(HomeAssistantError): pass
class InvalidAuth(HomeAssistantError): pass