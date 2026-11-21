"""Costanti dell'integrazione Nexus Videocitofono.

Integrazione BRAND-AGNOSTICA: lavora su entita' HA standard (un binary_sensor di
chiamata, pulsanti, uno stream video). I default puntano alle entita' del bridge
Vimar By-me (add-on vimar_vdc_intercom) solo per comodita': sono tutti
riconfigurabili dal pannello Opzioni.
"""

DOMAIN = "nexus_videocitofono"
VERSION = "0.2.1"

# --- chiavi di configurazione (opzioni) ---
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

# --- default (Vimar By-me, ma riconfigurabili) ---
DEFAULT_CALL_SENSOR = "binary_sensor.vimar_videocitofonia_chiamata_in_arrivo"
DEFAULT_ANSWER_BUTTON = "button.vimar_videocitofonia_rispondi"
DEFAULT_DOOR_BUTTON = "button.vimar_videocitofonia_apriporta"
DEFAULT_HANGUP_BUTTON = "button.vimar_videocitofonia_riaggancia"
DEFAULT_DASHBOARD = "/videocitofono-vimar/citofono"
DEFAULT_TITLE = "\U0001F514 Videocitofono"
DEFAULT_MESSAGE = "Qualcuno sta suonando al videocitofono."

# --- notifiche azionabili (app Companion) ---
EVENT_ACTION = "mobile_app_notification_action"
ACTION_ANSWER = "VIMAR_VDC_ANSWER"
ACTION_DOOR = "VIMAR_VDC_DOOR"
ACTION_HANGUP = "VIMAR_VDC_HANGUP"
NOTIFY_TAG = "vimar_vdc_call"

# --- guardiano (plancia automatica sui dispositivi scelti) ---
GUARDIAN_URL = "/nexus_videocitofono/guardian.js"
WS_CONFIG = "nexus_videocitofono/config"
