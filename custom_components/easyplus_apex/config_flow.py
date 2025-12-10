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
    CONF_ADDR_POWER, CONF_TRAVEL_TIME, CONF_INVERT_DIR,
    CONF_XML_CONTENT
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
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=10
        )

        ready_received = False
        try:
            for _ in range(10): 
                line_bytes = await asyncio.wait_for(reader.readuntil(b'\n'), timeout=2)
                line = line_bytes.decode('ascii').strip()
                if line.lstrip().startswith(">Ready"):
                    ready_received = True
                    break
            if not ready_received:
                raise CannotConnect("Did not receive '>Ready' prompt.")
        except Exception as e:
            raise CannotConnect(f"Error reading banner: {e}")

        pass_cmd = f"Pass {password}\n"
        writer.write(pass_cmd.encode('ascii'))
        await writer.drain()

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
    
    def __init__(self):
        """Initialize flow."""
        self.login_data = {} # Tijdelijke opslag voor login gegevens
        self.title = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EasyplusOptionsFlowHandler(config_entry)

    # --- STAP 1: Login ---
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
                # Validatie gelukt! Sla data tijdelijk op.
                self.login_data = user_input
                self.title = info["title"]
                
                # Ga nu naar de keuze: XML of Auto?
                return await self.async_step_choice()

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

    # --- STAP 2: Keuze Menu ---
    async def async_step_choice(self, user_input=None) -> ConfigFlowResult:
        """Laat de gebruiker kiezen tussen Auto-Discovery of XML."""
        return self.async_show_menu(
            step_id="choice",
            menu_options=["auto_discovery", "upload_xml"]
        )

    # --- STAP 3A: Auto Discovery (Direct afronden) ---
    async def async_step_auto_discovery(self, user_input=None) -> ConfigFlowResult:
        """Maak entry aan zonder XML data."""
        return self.async_create_entry(title=self.title, data=self.login_data)

    # --- STAP 3B: XML Uploaden ---
    async def async_step_upload_xml(self, user_input=None) -> ConfigFlowResult:
        """Vraag om XML en maak dan entry aan."""
        if user_input is not None:
            # We hebben login data (self.login_data) EN XML data (user_input)
            # De XML data stoppen we in de 'options' van de entry.
            return self.async_create_entry(
                title=self.title, 
                data=self.login_data,
                options={CONF_XML_CONTENT: user_input[CONF_XML_CONTENT]}
            )

        return self.async_show_form(
            step_id="upload_xml",
            data_schema=vol.Schema({
                vol.Required(CONF_XML_CONTENT): str, 
            }),
            description_placeholders={
                "info": "Open config.xml, kopieer alles en plak hier."
            }
        )

class EasyplusOptionsFlowHandler(OptionsFlow):
    """Handle Easyplus options (Manage Covers with Detection & XML)."""

    def __init__(self, config_entry):
        self.entry = config_entry 
        self.covers = self.entry.options.get(CONF_COVERS, [])

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Start menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "import_xml_config",
                "detect_cover_start", 
                "add_cover_manual", 
                "remove_cover"
            ]
        )

    # --- OPTIES: XML IMPORT (Later toevoegen/updaten) ---
    async def async_step_import_xml_config(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            # Update de bestaande options
            return self.async_create_entry(
                title="XML Imported", 
                data={CONF_XML_CONTENT: user_input[CONF_XML_CONTENT]}
            )

        return self.async_show_form(
            step_id="import_xml_config",
            data_schema=vol.Schema({vol.Required(CONF_XML_CONTENT): str}),
            description_placeholders={"info": "Plak nieuwe XML content."}
        )

    # --- WIZARD STAP 1: Instructie ---
    async def async_step_detect_cover_start(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_detect_listening()

        return self.async_show_form(
            step_id="detect_cover_start",
            description_placeholders={},
            data_schema=vol.Schema({}), 
            last_step=False
        )

    # --- WIZARD STAP 2: Luisteren (10 sec) ---
    async def async_step_detect_listening(self, user_input=None) -> ConfigFlowResult:
        coordinator = self.hass.data[DOMAIN][self.entry.entry_id]
        changed_relays = await coordinator.detect_activity(duration=10)
        self.detected_ids = sorted(list(changed_relays))

        if len(self.detected_ids) < 2:
            return self.async_show_form(step_id="detect_failed", errors={"base": "too_few_relays"})
        
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
                CONF_TRAVEL_TIME: float(user_input[CONF_TRAVEL_TIME]),
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
                vol.Required(CONF_TRAVEL_TIME, default=25.0): vol.Coerce(float),
                vol.Optional(CONF_INVERT_DIR, default=False): bool,
            })
        )

    async def async_step_detect_failed(self, user_input=None) -> ConfigFlowResult:
        return await self.async_step_init()

    # --- HANDMATIG ---
    async def async_step_add_cover_manual(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_TRAVEL_TIME] = float(user_input[CONF_TRAVEL_TIME])
            self.covers.append(user_input)
            return self.async_create_entry(title="", data={CONF_COVERS: self.covers})

        return self.async_show_form(
            step_id="add_cover_manual",
            data_schema=vol.Schema({
                vol.Required(CONF_COVER_NAME): str,
                vol.Required(CONF_ADDR_DIR): int,
                vol.Required(CONF_ADDR_POWER): int,
                vol.Required(CONF_TRAVEL_TIME, default=25.0): vol.Coerce(float),
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
