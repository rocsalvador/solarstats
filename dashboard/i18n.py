"""Internationalisation support for the SolarStats dashboard.

Provides a simple dictionary-based translation system for English and Catalan.
New languages can be added by extending the ``TRANSLATIONS`` dict.
"""

from __future__ import annotations

from typing import Literal

# Supported language codes.
Lang = Literal["en", "ca"]

# ── Translation strings ──────────────────────────────────────────────
# Organised by section so the structure stays clear as strings grow.
TRANSLATIONS: dict[Lang, dict[str, str]] = {
    "en": {
        # App
        "app.title": "SolarStats",
        "page.title": "Inverter Dashboard",

        # Hero
        "hero.title": "Inverter Dashboard",
        "hero.subtitle": "Live readings and recorded history from your inverter.",

        # Live section
        "live.heading": "Live",
        "live.description": "Current inverter register values, refreshed every {seconds} seconds.",

        # Register cards (live)
        "card.soc": "SOC",
        "card.load_power": "Load Power",
        "card.solar_power": "Solar Power",
        "card.daily_production": "Daily Production",
        "card.daily_consumption": "Daily Consumption",
        "card.total_production": "Total Production",

        # History section
        "history.heading": "History",
        "history.description": "Explore the data recorded by the logger. Choose a fixed timespan or pick a custom range.",
        "history.unavailable": "Historic data is unavailable because no database prefix was provided.",
        "history.no_data": "No historical data recorded for the selected range.",
        "history.start_logger": "Start the logger to record data, or pass --db-prefix to load an existing dataset.",

        # History range labels
        "range.24h": "Last 24 hours",
        "range.7d": "Last 7 days",
        "range.30d": "Last 30 days",
        "range.all": "All time",
        "range.custom": "Custom",
        "range.label": "Range",

        # History cards
        "history.energy_production": "Energy Production",
        "history.energy_consumption": "Energy Consumption",

        # Status
        "status.live": "Live",
        "status.offline": "Disconnected",
        "status.connecting": "Connecting...",

        # Error
        "error.reading": "Error reading inverter data. Retrying in {seconds} seconds...",

        # Language switcher
        "lang.en": "English",
        "lang.ca": "Català",
    },
    "ca": {
        # App
        "app.title": "SolarStats",
        "page.title": "Panell de l'inversor",

        # Hero
        "hero.title": "Panell de l'inversor",
        "hero.subtitle": "Lectures en directe i històric de dades del vostre inversor.",

        # Live section
        "live.heading": "Directe",
        "live.description": "Valors actuals dels registres de l'inversor, actualitzats cada {seconds} segons.",

        # Register cards (live)
        "card.soc": "SOC",
        "card.load_power": "Consum",
        "card.solar_power": "Energia solar",
        "card.daily_production": "Producció diària",
        "card.daily_consumption": "Consum diari",
        "card.total_production": "Producció total",

        # History section
        "history.heading": "Històric",
        "history.description": "Exploreu les dades enregistrades pel registrador. Trieu un període fix o personalitzeu-lo.",
        "history.unavailable": "Les dades històriques no estan disponibles perquè no s'ha proporcionat cap prefix de base de dades.",
        "history.no_data": "No hi ha dades històriques per al període seleccionat.",
        "history.start_logger": "Inicieu el registrador per a enregistrar dades, o passeu --db-prefix per a carregar un conjunt de dades existent.",

        # History range labels
        "range.24h": "Darreres 24 h",
        "range.7d": "Darrers 7 dies",
        "range.30d": "Darrers 30 dies",
        "range.all": "Tot el període",
        "range.custom": "Personalitzat",
        "range.label": "Període",

        # History cards
        "history.energy_production": "Producció d'energia",
        "history.energy_consumption": "Consum d'energia",

        # Status
        "status.live": "En directe",
        "status.offline": "Desconnectat",
        "status.connecting": "Connectant...",

        # Error
        "error.reading": "Error en llegir les dades de l'inversor. Es tornarà a intentar en {seconds} segons...",

        # Language switcher
        "lang.en": "English",
        "lang.ca": "Català",
    },
}


class I18n:
    """Lightweight translation helper.

    Usage::

        t = I18n("ca")
        heading = t("live.heading")          # "Directe"
        desc = t("live.description", seconds=5)  # "… cada 5 segons."
    """

    def __init__(self, lang: Lang = "en"):
        if lang not in TRANSLATIONS:
            lang = "en"
        self._lang = lang

    @property
    def lang(self) -> Lang:
        """Return the current language code."""
        return self._lang

    def set_lang(self, lang: Lang) -> None:
        """Switch to *lang* if it is a supported language."""
        if lang in TRANSLATIONS:
            self._lang = lang

    def __call__(self, key: str, **kwargs) -> str:
        """Return the translated string for *key*, optionally formatting with *kwargs*."""
        text = TRANSLATIONS[self._lang].get(key)
        if text is None:
            # Fallback: try English, then return the raw key.
            text = TRANSLATIONS["en"].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def get(self, key: str, **kwargs) -> str:
        """Explicit getter, equivalent to calling the instance."""
        return self(key, **kwargs)
