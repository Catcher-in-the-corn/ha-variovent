"""Constants for the Variovent integration."""

from datetime import timedelta

DOMAIN = "variovent"
MANUFACTURER = "Variovent / ZSA"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MIN_SCAN_INTERVAL = 30
CONF_SCAN_INTERVAL = "scan_interval"

# Betriebsarten offered for selection (the spot also knows "wochenplan" = schedule)
SELECTABLE_MODES = [
    "aus",
    "wochenplan",
    "normalbetrieb",
    "automatik",
    "sommer",
    "party",
    "abwesenheit",
    "zuluft",
    "fortluft",
    "feuchteabluft",
    "luftguete",
]
