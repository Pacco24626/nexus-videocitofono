"""Nexus Videocitofono — integrazione brand-agnostica per videocitofoni IP.

Si appoggia alle entita' che il videocitofono espone a Home Assistant (sensore di
chiamata, pulsanti, stream) e aggiunge le funzioni d'uso: per ora la notifica
azionabile sul telefono quando suonano. Tutto configurabile dal pannello Opzioni.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .notify_manager import NotifyManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Avvia l'integrazione: mette in ascolto il gestore notifiche."""
    manager = NotifyManager(hass, entry)
    await manager.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ferma l'integrazione."""
    manager: NotifyManager | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager is not None:
        manager.async_stop()
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ricarica quando l'utente cambia le opzioni dal pannello Configura."""
    await hass.config_entries.async_reload(entry.entry_id)
