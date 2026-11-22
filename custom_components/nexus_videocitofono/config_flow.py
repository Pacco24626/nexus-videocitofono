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
    BRAND_DAHUA,
    BRAND_DEFAULTS,
    BRAND_GENERIC,
    BRAND_VIMAR,
    CONF_ADMIN_PASSWORD,
    CONF_ADMIN_USER,
    CONF_ANSWER_BUTTON,
    CONF_BRAND,
    CONF_CALL_SENSOR,
    CONF_CAMERA,
    CONF_DASHBOARD_PATH,
    CONF_DOOR_BUTTON,
    CONF_ENABLE_NOTIFY,
    CONF_EXTENSION,
    CONF_HANGUP_BUTTON,
    CONF_MESSAGE,
    CONF_NOTIFY_TARGETS,
    CONF_RING_HOLD_SEC,
    CONF_TALK_TIMEOUT,
    CONF_TITLE,
    CONF_USE_ADDON,
    CONF_VTO_IP,
    DEFAULT_BRAND,
    DEFAULT_MESSAGE,
    DEFAULT_RING_HOLD_SEC,
    DEFAULT_TALK_TIMEOUT,
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
    """Pannello Configura, guidato per marca.

    Passo 1 (init): che citofono hai? (Vimar / Dahua / Altro). Passo 2 (config): i
    campi, con i default giusti per la marca scelta. L'integrazione resta
    brand-agnostica: la marca serve solo a precompilare i campi.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry
        self._brand = dict(config_entry.options).get(CONF_BRAND, DEFAULT_BRAND)
        self._dahua: dict[str, Any] = {}  # parametri ponte Dahua (use_addon, vto_ip, ...)
        self._extensions: list[dict[str, str]] = []
        self._device: dict[str, str] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Passo 1: scelta della marca."""
        if user_input is not None:
            self._brand = user_input[CONF_BRAND]
            self._dahua = {}
            if self._brand == BRAND_DAHUA:
                return await self.async_step_dahua_mode()
            return await self.async_step_config()

        schema = vol.Schema(
            {
                vol.Required(CONF_BRAND, default=self._brand): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": BRAND_VIMAR, "label": "Vimar By-me"},
                            {"value": BRAND_DAHUA, "label": "Dahua"},
                            {"value": BRAND_GENERIC, "label": "Altro / SIP generico"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    # ---------- Dahua: add-on FACOLTATIVO (risposta SIP / audio immediato) ----------
    async def async_step_dahua_mode(self, user_input: dict[str, Any] | None = None):
        """Interruttore: usare l'add-on? Spento = Dahua base (come oggi), nessun VTO."""
        cur = dict(self._entry.options)
        if user_input is not None:
            use = bool(user_input.get(CONF_USE_ADDON, False))
            self._dahua[CONF_USE_ADDON] = use
            if use:
                return await self.async_step_dahua_vto()
            return await self.async_step_config()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USE_ADDON, default=cur.get(CONF_USE_ADDON, False)
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="dahua_mode", data_schema=schema)

    async def async_step_dahua_vto(self, user_input: dict[str, Any] | None = None):
        """Credenziali admin del VTO: valida e legge modello + interni via CGI."""
        from .dahua_vto import async_probe_vto

        cur = dict(self._entry.options)
        errors: dict[str, str] = {}
        if user_input is not None:
            res = await async_probe_vto(
                self.hass,
                user_input[CONF_VTO_IP],
                user_input[CONF_ADMIN_USER],
                user_input[CONF_ADMIN_PASSWORD],
            )
            if not res.get("ok"):
                errors["base"] = "vto_auth"
            else:
                self._dahua[CONF_VTO_IP] = user_input[CONF_VTO_IP]
                self._dahua[CONF_ADMIN_USER] = user_input[CONF_ADMIN_USER]
                self._dahua[CONF_ADMIN_PASSWORD] = user_input[CONF_ADMIN_PASSWORD]
                self._device = res.get("device", {})
                self._extensions = res.get("extensions", [])
                return await self.async_step_dahua_ext()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_VTO_IP, default=cur.get(CONF_VTO_IP, "")
                ): selector.TextSelector(),
                vol.Required(
                    CONF_ADMIN_USER, default=cur.get(CONF_ADMIN_USER, "admin")
                ): selector.TextSelector(),
                vol.Required(CONF_ADMIN_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="dahua_vto", data_schema=schema, errors=errors
        )

    async def async_step_dahua_ext(self, user_input: dict[str, Any] | None = None):
        """Scelta dell'interno SIP del VTO (ultimo preselezionato, modificabile)."""
        if user_input is not None:
            self._dahua[CONF_EXTENSION] = user_input[CONF_EXTENSION]
            return await self.async_step_config()

        # solo i VTH (i monitor); se la lista e' vuota, lasciamo tutti quelli trovati.
        vth = [e["id"] for e in self._extensions if (e.get("type") or "").upper() == "VTH"]
        ids = vth or [e["id"] for e in self._extensions]
        options = [{"value": i, "label": i} for i in ids]
        default_ext = ids[-1] if ids else None  # ultimo della lista preselezionato

        ext_key = (
            vol.Required(CONF_EXTENSION, default=default_ext)
            if default_ext
            else vol.Required(CONF_EXTENSION)
        )
        schema = vol.Schema(
            {
                ext_key: selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="dahua_ext",
            data_schema=schema,
            description_placeholders={
                "model": self._device.get("model", "VTO"),
                "count": str(len(ids)),
            },
        )

    async def async_step_config(self, user_input: dict[str, Any] | None = None):
        """Passo 2: i campi, precompilati in base alla marca."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_BRAND: self._brand, **self._dahua, **user_input},
            )

        cur = dict(self._entry.options)
        bdef = BRAND_DEFAULTS.get(self._brand, {})

        def dflt(key, global_default=None):
            """Valore corrente se c'e', altrimenti il default della marca, altrimenti il globale."""
            if key in cur:
                return cur[key]
            if key in bdef:
                return bdef[key]
            return global_default

        # telefoni con l'app Companion gia' presenti (il cliente puo' anche digitarne uno)
        notify_services = sorted(
            s
            for s in self.hass.services.async_services().get("notify", {})
            if s.startswith("mobile_app_")
        )

        # CALL_SENSOR e' obbligatorio: se c'e' un valore (corrente o di marca) lo
        # precompila; se no (Dahua/Generico: nomi dipendenti dall'impianto) lo lascia
        # da scegliere, senza imporre il default Vimar.
        call_default = dflt(CONF_CALL_SENSOR)
        call_key = (
            vol.Required(CONF_CALL_SENSOR, default=call_default)
            if call_default
            else vol.Required(CONF_CALL_SENSOR)
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
                call_key: selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(
                    CONF_ANSWER_BUTTON,
                    description={"suggested_value": dflt(CONF_ANSWER_BUTTON)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_DOOR_BUTTON,
                    description={"suggested_value": dflt(CONF_DOOR_BUTTON)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_HANGUP_BUTTON,
                    description={"suggested_value": dflt(CONF_HANGUP_BUTTON)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=ACTION_DOMAINS)
                ),
                vol.Optional(
                    CONF_CAMERA,
                    description={"suggested_value": dflt(CONF_CAMERA)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="camera")
                ),
                vol.Optional(
                    CONF_DASHBOARD_PATH,
                    description={"suggested_value": dflt(CONF_DASHBOARD_PATH)},
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
                vol.Optional(
                    CONF_TALK_TIMEOUT,
                    description={
                        "suggested_value": cur.get(CONF_TALK_TIMEOUT, DEFAULT_TALK_TIMEOUT)
                    },
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=10,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="config", data_schema=schema)
