"""Konstanten für PV Übersicht."""

from datetime import timedelta

DOMAIN = "pv_overview"

CONF_SOURCE = "source_entity"
CONF_THRESHOLD = "threshold"
CONF_INITIAL_TOTAL = "initial_total"

DEFAULT_NAME = "PV Anlage"
DEFAULT_THRESHOLD = 10.0  # W – ab dieser Leistung zählt die Zeit als "Produktionszeit"

UPDATE_INTERVAL = timedelta(seconds=30)
SAVE_DELAY = 60  # s
STORAGE_VERSION = 1
HISTORY_DAYS = 400
HISTORY_MONTHS = 36
