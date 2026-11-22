"""Config flow + pannello Opzioni (Configura) di Nexus Videocitofono.

Il cliente aggiunge l'integrazione una volta, poi imposta TUTTO da Configura:
quali telefoni avvisare, quale sensore di chiamata, quali pulsanti, ecc. Niente e'
scritto a mano. I default sono per Vimar By-me ma si cambiano con un menu' a tendina.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

# Domini "azionabili" per apriporta/rispondi/riaggancia: brand-agnostico.
# Vimar usa button; Dahua & co. possono usare switch/lock/rele'/script.
ACTION_DOMAINS = [
    "button",
    "input_button",
    "switch",
    "light",
    "lock",
    "cover",
    "script",
    "scene",
    "automation",
]

from .const import (
    CONF_ANSWER_BUTTON,
    CONF_CALL_SENSOR,
    CONF_CAMERA,
    CONF_DASHBOARD_PATH,
    CONF_DOOR_BUTTON,
    CONF_ENABLE_NOTIFY,
    CONF_HANGUP_BUTTON,
    CONF_MESSAGE,
    CONF_NOTIFY_TARGETS,
    CONF_RING_HOLD_SEC,
    CONF_TITLE,
    DEFAULT_ANSWER_BUTTON,
    DEFAULT_CALL_SENSOR,
    DEFAULT_DASHBOARD,
    DEFAULT_DOOR_BUTTON,
    DEFAULT_HANGUP_BUTTON,
    DEFAULT_MESSAGE,
    DEFAULT_RING_HOLD_SEC,
    DEFAULT_TITLE,
    DOMAIN,
)


class NexusVideocitofonoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Aggiunta dell'integrazione (una sola istanza)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Nexus Videocitofono", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NexusVideocitofonoOptionsFlow(config_entry)


class NexusVideocitofonoOptionsFlow(OptionsFlow):
    """Pannello Configura. Per ora: Notifiche (A). In seguito: Plancia (B), Sorgenti (C)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        cur = dict(self._entry.options)
        # telefoni con l'app Companion gia' presenti (il cliente puo' anche digitarne uno)
        notify_services = sorted(
            s
            for s in self.hass.services.async_services().get("notify", {})
            if s.startswith("mobile_app_")
        )

        # NB: i campi opzionali usano "suggested_value" (non "default"), cosi' si possono
        # LASCIARE VUOTI: un campo svuotato resta assente e l'azione non viene mostrata.
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENABLE_NOTIFY, default=cur.get(CONF_ENABLE_NOTIFY, True)
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    description={"suggested_value": cur.get(CONF_NOTIFY_TARGETS, [])},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=notify_services,
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_CALL_SENSOR, default=cur.get(CONF_CALL_SENSOR, DEFAULT_CALL_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(
                    CONF_ANSWER_BUTTON,
                    description={"suggested_value": cur.get(CONF_ANSWER_BUTTON)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_DOOR_BUTTON,
                    description={
                        "suggested_value": cur.get(CONF_DOOR_BUTTON, DEFAULT_DOOR_BUTTON)
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_HANGUP_BUTTON,
                    description={"suggested_value": cur.get(CONF_HANGUP_BUTTON)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_CAMERA,
                    description={"suggested_value": cur.get(CONF_CAMERA)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="camera")
                ),
                vol.Optional(
                    CONF_DASHBOARD_PATH,
                    description={
                        "suggested_value": cur.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD)
                    },
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_TITLE,
                    description={"suggested_value": cur.get(CONF_TITLE, DEFAULT_TITLE)},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_MESSAGE,
                    description={"suggested_value": cur.get(CONF_MESSAGE, DEFAULT_MESSAGE)},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_RING_HOLD_SEC,
                    description={
                        "suggested_value": cur.get(
                            CONF_RING_HOLD_SEC, DEFAULT_RING_HOLD_SEC
                        )
                    },
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=300,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
