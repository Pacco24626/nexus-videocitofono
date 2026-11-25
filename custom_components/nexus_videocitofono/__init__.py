"""Nexus Videocitofono — integrazione brand-agnostica per videocitofoni IP.

Si appoggia alle entita' che il videocitofono espone a Home Assistant (sensore di
chiamata, pulsanti, stream) e aggiunge le funzioni d'uso:
- A: notifica azionabile sul telefono quando suonano;
- B: la plancia che compare DA SOLA sui dispositivi scelti quando suonano
     (guardiano caricato su ogni pannello, come il tastierino allarme in preallarme).
Tutto configurabile dal pannello Opzioni.
"""
from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    ADDON_UNIQUE_IDS,
    CONF_ANSWER_BUTTON,
    CONF_CALL_SENSOR,
    CONF_CAMERA,
    CONF_DASHBOARD_PATH,
    CONF_DOOR_BUTTON,
    CONF_HANGUP_BUTTON,
    CONF_RING_HOLD_SEC,
    CONF_TALK_TIMEOUT,
    CONF_TITLE,
    CONF_USE_ADDON,
    DEFAULT_CALL_SENSOR,
    DEFAULT_RING_HOLD_SEC,
    DEFAULT_TALK_TIMEOUT,
    DEFAULT_TITLE,
    DOMAIN,
    GUARDIAN_URL,
    VERSION,
    WS_CONFIG,
)
from .notify_manager import NotifyManager

_LOGGER = logging.getLogger(__name__)
_FRONTEND = f"{DOMAIN}_frontend_registered"
_WS = f"{DOMAIN}_ws_registered"


@callback
def resolve_addon(hass: HomeAssistant) -> dict[str, str]:
    """entity_id REALI delle entita' dell'add-on, risolti per UNIQUE_ID (platform mqtt).

    Gli entity_id non sono deducibili dal nome (HA puo' conservare vecchi id), quindi
    si parte sempre dagli unique_id stabili. Chiavi assenti = entita' non (ancora)
    registrata.
    """
    reg = er.async_get(hass)
    out: dict[str, str] = {}
    for key, (domain, uid) in ADDON_UNIQUE_IDS.items():
        eid = reg.async_get_entity_id(domain, "mqtt", uid)
        if eid:
            out[key] = eid
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Avvia l'integrazione."""
    manager = NotifyManager(hass, entry)
    await manager.async_start()
    # Con l'add-on (use_addon ON) esponiamo anche la camera "intercom".
    platforms = [Platform.CAMERA] if entry.options.get(CONF_USE_ADDON) else []
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "manager": manager,
        "platforms": platforms,  # salvato: l'unload deve usare lo STESSO set
    }
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await _async_register_frontend(hass)
    _async_register_ws(hass)
    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ferma l'integrazione (il guardiano frontend resta registrato finche' si riavvia)."""
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not data:
        return True
    platforms = data.get("platforms") or []
    if platforms:
        await hass.config_entries.async_unload_platforms(entry, platforms)
    manager: NotifyManager | None = data.get("manager")
    if manager is not None:
        manager.async_stop()
    return True


async def _async_sync_addon_timeout(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Allinea `talk_timeout_s` nelle opzioni dell'add-on (via Supervisor) alla scelta dell'utente.

    BEST-EFFORT: qualsiasi errore viene solo loggato, non deve mai rompere il setup. Scrive e
    riavvia l'add-on SOLO se: use_addon ON, siamo su HAOS/Supervisor, l'add-on esiste, ha gia' il
    campo talk_timeout_s nello schema (>=0.3.4) e il valore e' DIVERSO (cosi' al default non si
    tocca nulla e non si riavvia l'add-on inutilmente).
    """
    opt = dict(entry.options)
    if not opt.get(CONF_USE_ADDON):
        return
    timeout = int(opt.get(CONF_TALK_TIMEOUT, DEFAULT_TALK_TIMEOUT))
    try:
        from homeassistant.components.hassio import get_supervisor_info, is_hassio

        if not is_hassio(hass):
            return
        info = get_supervisor_info(hass) or {}
        slug = next(
            (
                a["slug"]
                for a in info.get("addons", [])
                if str(a.get("slug", "")).endswith("_vimar_vdc_intercom")
            ),
            None,
        )
        if not slug:
            return
        try:
            from homeassistant.components.hassio import AddonManager
        except ImportError:
            from homeassistant.components.hassio.addon_manager import AddonManager

        mgr = AddonManager(hass, _LOGGER, "Nexus Videocitofono (ponte)", slug)
        addon = await mgr.async_get_addon_info()
        options = dict(addon.options or {})
        if "talk_timeout_s" not in options:
            return  # add-on troppo vecchio: non infilare una chiave fuori schema
        if options.get("talk_timeout_s") == timeout:
            return  # gia' allineato
        options["talk_timeout_s"] = timeout
        await mgr.async_set_addon_options(options)
        if getattr(addon, "state", None) == "started":
            await mgr.async_restart_addon()
        _LOGGER.info(
            "Nexus Videocitofono: talk_timeout_s=%s scritto nell'add-on %s", timeout, slug
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Nexus Videocitofono: sync talk_timeout_s con l'add-on non riuscita: %s", err
        )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ricarica quando l'utente cambia le opzioni dal pannello Configura."""
    await _async_sync_addon_timeout(hass, entry)  # propaga la durata max all'add-on (best-effort)
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve il guardiano e lo carica su OGNI pannello (via add_extra_js_url)."""
    if hass.data.get(_FRONTEND):
        return
    hass.data[_FRONTEND] = True
    path = os.path.join(os.path.dirname(__file__), "guardian.js")
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(GUARDIAN_URL, path, False)]
        )
        add_extra_js_url(hass, f"{GUARDIAN_URL}?v={VERSION}")
        _LOGGER.debug("Nexus Videocitofono: guardiano registrato su %s", GUARDIAN_URL)
    except Exception as err:  # noqa: BLE001
        hass.data[_FRONTEND] = False
        _LOGGER.warning("Nexus Videocitofono: guardiano non registrato: %s", err)


@callback
def _async_register_ws(hass: HomeAssistant) -> None:
    """Comando WS che da' al guardiano la config corrente (cosa guardare e mostrare)."""
    if hass.data.get(_WS):
        return
    hass.data[_WS] = True

    @websocket_api.websocket_command({vol.Required("type"): WS_CONFIG})
    @callback
    def _ws_config(hass, connection, msg):
        entries = hass.config_entries.async_entries(DOMAIN)
        entry = entries[0] if entries else None
        opt = dict(entry.options) if entry else {}
        hold = opt.get(CONF_RING_HOLD_SEC)
        if hold is None:
            hold = DEFAULT_RING_HOLD_SEC  # 0 e' valido ("chiudi subito"), quindi niente `or`
        use_addon = bool(opt.get(CONF_USE_ADDON))
        result = {
            "use_addon": use_addon,  # la card lo usa per decidere se adeguarsi al ponte
            "call_sensor": opt.get(CONF_CALL_SENSOR) or DEFAULT_CALL_SENSOR,
            "answer": opt.get(CONF_ANSWER_BUTTON) or None,
            "door": opt.get(CONF_DOOR_BUTTON) or None,
            "hangup": opt.get(CONF_HANGUP_BUTTON) or None,
            "camera": opt.get(CONF_CAMERA) or None,
            "dashboard": opt.get(CONF_DASHBOARD_PATH) or None,
            "title": opt.get(CONF_TITLE) or DEFAULT_TITLE,
            "hold_sec": hold,
            "status_sensor": None,  # sensore "Stato" dell'add-on (tiene aperto in conversazione)
            "reg_sensor": None,  # sensore "Registrazione SIP" (chip di stato della card)
            "autostart": None,  # button "Autoaccensione" (chiama la targa senza suonata); None se la marca non la supporta
            "talk_timeout_s": opt.get(CONF_TALK_TIMEOUT, DEFAULT_TALK_TIMEOUT),  # durata max conversazione: la plancia ci fa il conto alla rovescia
            "floor_ring": None,  # EVENT "Fuoriporta" (Vimar): la card ne mostra un'indicazione; None se la marca non ce l'ha
        }
        # Con l'add-on ON: le sue entita' (risolte per unique_id) VINCONO sui CONF_*
        # manuali, e la camera e' lo stream "intercom" dell'integrazione.
        if use_addon:
            addon = resolve_addon(hass)
            for key in ("call_sensor", "answer", "door", "hangup", "status_sensor", "reg_sensor", "autostart", "floor_ring"):
                if addon.get(key):
                    result[key] = addon[key]
            if entry:
                cam = er.async_get(hass).async_get_entity_id(
                    "camera", DOMAIN, f"{entry.entry_id}_camera"
                )
                if cam:
                    result["camera"] = cam
        connection.send_result(msg["id"], result)

    websocket_api.async_register_command(hass, _ws_config)
