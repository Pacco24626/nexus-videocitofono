"""Gestore notifiche (funzione A).

Quando il sensore di chiamata va a ON manda una notifica azionabile ai telefoni
scelti; le azioni della notifica (Rispondi/Apriporta/Riaggancia) premono i pulsanti
corrispondenti. A chiamata finita la notifica viene rimossa. Niente e' Vimar: legge
solo entita' HA standard, tutte scelte dall'utente nelle opzioni.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import slugify

from .const import (
    ACTION_ANSWER,
    ACTION_DOOR,
    ACTION_HANGUP,
    CONF_ANSWER_BUTTON,
    CONF_CALL_SENSOR,
    CONF_DASHBOARD_PATH,
    CONF_DOOR_BUTTON,
    CONF_ENABLE_NOTIFY,
    CONF_HANGUP_BUTTON,
    CONF_MESSAGE,
    CONF_NOTIFY_TARGETS,
    CONF_TITLE,
    DEFAULT_ANSWER_BUTTON,
    DEFAULT_CALL_SENSOR,
    DEFAULT_DASHBOARD,
    DEFAULT_DOOR_BUTTON,
    DEFAULT_HANGUP_BUTTON,
    DEFAULT_MESSAGE,
    DEFAULT_TITLE,
    EVENT_ACTION,
    NOTIFY_TAG,
)

_LOGGER = logging.getLogger(__name__)

# Come "premere" un'azione, qualunque sia il tipo di entita' (brand-agnostico):
# su Vimar l'apriporta e' un button, su Dahua/altri puo' essere switch, lock, rele'
# o uno script. Per casi esotici basta puntare a uno script.* che fa il lavoro.
PRESS_SERVICE: dict[str, tuple[str, str]] = {
    "button": ("button", "press"),
    "input_button": ("input_button", "press"),
    "switch": ("switch", "turn_on"),
    "light": ("light", "turn_on"),
    "lock": ("lock", "unlock"),
    "cover": ("cover", "open_cover"),
    "script": ("script", "turn_on"),
    "scene": ("scene", "turn_on"),
    "automation": ("automation", "trigger"),
}


class NotifyManager:
    """Ascolta la chiamata e dispatcha le notifiche azionabili."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsub: list = []

    def _opt(self, key: str, default):
        """Legge un'opzione (options prevale su data, poi default)."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    async def async_start(self) -> None:
        call_sensor = self._opt(CONF_CALL_SENSOR, DEFAULT_CALL_SENSOR)
        self._unsub.append(
            async_track_state_change_event(self.hass, [call_sensor], self._on_call_state)
        )
        self._unsub.append(self.hass.bus.async_listen(EVENT_ACTION, self._on_action))
        _LOGGER.debug("Nexus Videocitofono in ascolto su %s", call_sensor)

    @callback
    def async_stop(self) -> None:
        while self._unsub:
            self._unsub.pop()()

    async def _on_call_state(self, event: Event) -> None:
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is None:
            return
        if not self._opt(CONF_ENABLE_NOTIFY, True):
            return
        # Solo sul fronte di salita. Non togliamo la notifica quando il sensore
        # torna a OFF: cosi' funziona sia coi sensori "di stato" (Vimar, resta ON
        # per tutta la chiamata) sia con quelli "a impulso" (un campanello che
        # pulsa ON/OFF). La notifica si chiude quando si preme un'azione, oppure
        # viene sostituita dalla suonata successiva (stesso tag).
        if new.state == "on" and (old is None or old.state != "on"):
            await self._send()

    def _ent(self, key: str):
        """Entita' di un'azione dalle opzioni; vuota/assente -> None (nessuna azione)."""
        return self.entry.options.get(key) or None

    def _notify_data(self) -> dict:
        dash = self._opt(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD)
        answer = self._ent(CONF_ANSWER_BUTTON)
        door = self._ent(CONF_DOOR_BUTTON)
        hangup = self._ent(CONF_HANGUP_BUTTON)
        # Mostra SOLO le azioni che esistono davvero (brand-agnostico).
        actions = []
        # Rispondi: se c'e' un "rispondi" backend (SIP, es. Vimar) lo preme; altrimenti,
        # se c'e' una plancia (citofono-telecamera, es. Dahua), apre il video dal vivo
        # (dove si abilita l'audio bidirezionale). Se non c'e' ne' l'uno ne' l'altra, niente.
        if answer:
            actions.append({"action": ACTION_ANSWER, "title": "Rispondi"})
        elif dash:
            actions.append({"action": "URI", "title": "Rispondi", "uri": dash})
        if door:
            actions.append({"action": ACTION_DOOR, "title": "Apriporta"})
        if hangup:
            actions.append({"action": ACTION_HANGUP, "title": "Riaggancia"})
        data: dict = {
            "tag": NOTIFY_TAG,
            "channel": "Videocitofono",
            "importance": "high",
            "priority": "high",
            "ttl": 0,
            "sticky": True,
            "notification_icon": "mdi:doorbell-video",
            "actions": actions,
            "push": {"interruption-level": "time-sensitive"},
        }
        if dash:
            data["url"] = dash
            data["clickAction"] = dash
        return data

    async def _send(self) -> None:
        payload = {
            "title": self._opt(CONF_TITLE, DEFAULT_TITLE),
            "message": self._opt(CONF_MESSAGE, DEFAULT_MESSAGE),
            "data": self._notify_data(),
        }
        for svc in self._opt(CONF_NOTIFY_TARGETS, []):
            await self._call_notify(svc, payload)

    async def _clear(self) -> None:
        payload = {"message": "clear_notification", "data": {"tag": NOTIFY_TAG}}
        for svc in self._opt(CONF_NOTIFY_TARGETS, []):
            await self._call_notify(svc, payload)

    async def _call_notify(self, service: str, payload: dict) -> None:
        if not service:
            return
        service = service.split(".")[-1]  # accetta "notify.mobile_app_x" o "mobile_app_x"
        try:
            await self.hass.services.async_call("notify", service, payload, blocking=False)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Nexus Videocitofono: notify.%s fallito: %s", service, err)

    async def _activate(self, entity: str) -> None:
        """"Preme" un'entita' qualsiasi col servizio giusto per il suo dominio."""
        if not entity:
            return
        domain = entity.split(".")[0]
        svc = PRESS_SERVICE.get(domain)
        if svc is None:
            _LOGGER.warning(
                "Nexus Videocitofono: non so come attivare %s (dominio %s); "
                "usa uno script.* se serve",
                entity,
                domain,
            )
            return
        try:
            await self.hass.services.async_call(
                svc[0], svc[1], {"entity_id": entity}, blocking=False
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Nexus Videocitofono: %s.%s su %s fallito: %s", svc[0], svc[1], entity, err)

    async def _on_action(self, event: Event) -> None:
        action = event.data.get("action")
        mapping = {
            ACTION_ANSWER: self._ent(CONF_ANSWER_BUTTON),
            ACTION_DOOR: self._ent(CONF_DOOR_BUTTON),
            ACTION_HANGUP: self._ent(CONF_HANGUP_BUTTON),
        }
        if action not in mapping:
            return
        # Solo i telefoni SCELTI possono comandare (qui si apre la porta!). Se l'evento
        # porta il device_id e riusciamo a risolvere i target, verifichiamo l'appartenenza;
        # se non c'e' device_id o non risolviamo nulla, non blocchiamo (compatibilita').
        device_id = event.data.get("device_id")
        if device_id:
            allowed = self._allowed_device_ids()
            if allowed and device_id not in allowed:
                _LOGGER.debug(
                    "Nexus Videocitofono: azione %s da dispositivo non autorizzato, ignorata",
                    action,
                )
                return
        await self._activate(mapping[action])
        await self._clear()

    def _allowed_device_ids(self) -> set[str]:
        """device_id dei telefoni scelti (per non far aprire la porta da altri device)."""
        targets = {str(t).split(".")[-1] for t in self._opt(CONF_NOTIFY_TARGETS, [])}
        if not targets:
            return set()
        reg = dr.async_get(self.hass)
        allowed: set[str] = set()
        for dev in reg.devices.values():
            if any(iden[0] == "mobile_app" for iden in dev.identifiers):
                name = dev.name_by_user or dev.name or ""
                if ("mobile_app_" + slugify(name)) in targets:
                    allowed.add(dev.id)
        return allowed
