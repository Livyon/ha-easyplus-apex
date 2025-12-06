"""Constants for the Easyplus Apex System integration."""
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PASSWORD

DOMAIN = "easyplus_apex"

# Configuratie sleutels voor de Options Flow (Rolluiken)
CONF_COVERS = "covers"
CONF_COVER_NAME = "cover_name"
CONF_ADDR_DIR = "address_direction" # Het relais voor Richting
CONF_ADDR_POWER = "address_power"   # Het relais voor Stroom (Aan/Uit)
CONF_TRAVEL_TIME = "travel_time"
CONF_INVERT_DIR = "invert_direction" # Optie om open/dicht om te wisselen