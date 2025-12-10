"""Constants for the Easyplus Apex System integration."""
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PASSWORD

DOMAIN = "easyplus_apex"

# Configuratie sleutels
CONF_COVERS = "covers"
CONF_COVER_NAME = "cover_name"
CONF_ADDR_DIR = "address_direction"
CONF_ADDR_POWER = "address_power"
CONF_TRAVEL_TIME = "travel_time"
CONF_INVERT_DIR = "invert_direction"

# NIEUW: Voor XML Import
CONF_XML_CONTENT = "xml_content"      # De ruwe XML tekst
CONF_NAMING_MAP = "naming_map"        # Opslag: {adres: "Naam"}
CONF_STRICT_MODE = "strict_mode"      # Als True: negeer alles wat niet in XML staat
CONF_XML_SWITCHES = "xml_switches" # Lijst van adressen die ECHT switches zijn
CONF_XML_DIMMERS = "xml_dimmers"   # Lijst van adressen die ECHT dimmers zijn
