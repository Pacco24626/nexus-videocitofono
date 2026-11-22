"""Costanti dell'integrazione Nexus Videocitofono.

Integrazione BRAND-AGNOSTICA: lavora su entita' HA standard (un binary_sensor di
chiamata, pulsanti, uno stream video). I default puntano alle entita' del bridge
Vimar By-me (add-on vimar_vdc_intercom) solo per comodita': sono tutti
riconfigurabili dal pannello Opzioni.
"""

DOMAIN = "nexus_videocitofono"
VERSION = "0.2.4"

# --- chiavi di configurazione (opzioni) ---
CONF_BRAND = "brand"  # marca scelta: guida i default del pannello Configura
CONF_ENABLE_NOTIFY = "enable_notify"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_CALL_SENSOR = "call_sensor"
CONF_ANSWER_BUTTON = "answer_button"
CONF_DOOR_BUTTON = "door_button"
CONF_HANGUP_BUTTON = "hangup_button"
CONF_CAMERA = "camera"
CONF_DASHBOARD_PATH = "dashboard_path"
CONF_TITLE = "title"
CONF_MESSAGE = "message"
# Per quanti secondi tenere aperta la plancia automatica dopo che il sensore di
# chiamata si e' acceso. Serve ai sensori "a impulso" (molti citofoni, es. Dahua,
# tengono il sensore ON solo pochi secondi per suonata): senza questo la plancia
# si richiuderebbe da sola subito. 0 = chiudi appena il sensore torna OFF.
CONF_RING_HOLD_SEC = "ring_hold_sec"

# --- default (Vimar By-me, ma riconfigurabili) ---
DEFAULT_CALL_SENSOR = "binary_sensor.vimar_videocitofonia_chiamata_in_arrivo"
DEFAULT_ANSWER_BUTTON = "button.vimar_videocitofonia_rispondi"
DEFAULT_DOOR_BUTTON = "button.vimar_videocitofonia_apriporta"
DEFAULT_HANGUP_BUTTON = "button.vimar_videocitofonia_riaggancia"
DEFAULT_DASHBOARD = "/videocitofono-vimar/citofono"
DEFAULT_TITLE = "\U0001F514 Videocitofono"
DEFAULT_MESSAGE = "Qualcuno sta suonando al videocitofono."
DEFAULT_RING_HOLD_SEC = 60

# --- marche supportate (guidano SOLO i default del pannello Configura; l'integrazione
# resta brand-agnostica e lavora su entita' HA standard qualunque sia la marca) ---
BRAND_VIMAR = "vimar"
BRAND_DAHUA = "dahua"
BRAND_GENERIC = "generic"
DEFAULT_BRAND = BRAND_GENERIC
# Default per marca. Vimar: il bridge crea entita' a nome fisso -> si predefiniscono.
# Dahua: i nomi dipendono dall'impianto (device "giardino"/"ingresso"...) -> l'utente
# sceglie, si predefinisce solo il percorso plancia. Generic: niente.
BRAND_DEFAULTS = {
    BRAND_VIMAR: {
        CONF_CALL_SENSOR: DEFAULT_CALL_SENSOR,
        CONF_ANSWER_BUTTON: DEFAULT_ANSWER_BUTTON,
        CONF_DOOR_BUTTON: DEFAULT_DOOR_BUTTON,
        CONF_HANGUP_BUTTON: DEFAULT_HANGUP_BUTTON,
        CONF_DASHBOARD_PATH: DEFAULT_DASHBOARD,
    },
    BRAND_DAHUA: {
        CONF_DASHBOARD_PATH: "/videocitofono-dahua/citofono",
    },
    BRAND_GENERIC: {},
}

# --- notifiche azionabili (app Companion) ---
EVENT_ACTION = "mobile_app_notification_action"
ACTION_ANSWER = "VIMAR_VDC_ANSWER"
ACTION_DOOR = "VIMAR_VDC_DOOR"
ACTION_HANGUP = "VIMAR_VDC_HANGUP"
NOTIFY_TAG = "vimar_vdc_call"

# --- guardiano (plancia automatica sui dispositivi scelti) ---
GUARDIAN_URL = "/nexus_videocitofono/guardian.js"
WS_CONFIG = "nexus_videocitofono/config"
