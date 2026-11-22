"""Costanti dell'integrazione Nexus Videocitofono.

Integrazione BRAND-AGNOSTICA: lavora su entita' HA standard (un binary_sensor di
chiamata, pulsanti, uno stream video). I default puntano alle entita' del bridge
Vimar By-me (add-on vimar_vdc_intercom) solo per comodita': sono tutti
riconfigurabili dal pannello Opzioni.
"""

DOMAIN = "nexus_videocitofono"
VERSION = "0.3.3"

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
# Durata massima di una conversazione (secondi). 0 = nessun limite. Viene scritta nelle
# opzioni dell'add-on (chiave talk_timeout_s) via Supervisor: e' l'add-on a riagganciare da
# solo alla scadenza. La plancia mostra un conto alla rovescia da questo valore, da "in
# conversazione". Rilevante solo con l'add-on (use_addon ON); altrimenti ignorata.
CONF_TALK_TIMEOUT = "talk_timeout_s"

# --- default (Vimar By-me, ma riconfigurabili) ---
DEFAULT_CALL_SENSOR = "binary_sensor.vimar_videocitofonia_chiamata_in_arrivo"
DEFAULT_ANSWER_BUTTON = "button.vimar_videocitofonia_rispondi"
DEFAULT_DOOR_BUTTON = "button.vimar_videocitofonia_apriporta"
DEFAULT_HANGUP_BUTTON = "button.vimar_videocitofonia_riaggancia"
DEFAULT_DASHBOARD = "/videocitofono-vimar/citofono"
DEFAULT_TITLE = "\U0001F514 Videocitofono"
DEFAULT_MESSAGE = "Qualcuno sta suonando al videocitofono."
DEFAULT_RING_HOLD_SEC = 60
DEFAULT_TALK_TIMEOUT = 120  # pari al default dell'add-on: nessuna scrittura se non si cambia

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

# --- ponte add-on (Fase 2): opzioni raccolte dall'integrazione e passate all'add-on.
# I nomi combaciano con le options del config.yaml dell'add-on (profilo dahua). ---
CONF_USE_ADDON = "use_addon"  # Dahua: add-on facoltativo (risposta SIP / audio immediato)
CONF_VTO_IP = "vto_ip"
CONF_ADMIN_USER = "admin_user"
CONF_ADMIN_PASSWORD = "admin_password"
CONF_EXTENSION = "extension"
# URL RTSP dello stream "intercom" del go2rtc dell'ADD-ON, come lo raggiunge HA Core
# (NON 127.0.0.1: HA Core gira in un container separato). Configurabile; default =
# gateway hassio (l'host visto dal Core). Da verificare sul campo.
CONF_ADDON_RTSP = "addon_rtsp"
# Su HAOS il container Core gira con la rete dell'host, quindi 127.0.0.1 E' l'host e
# raggiunge il go2rtc dell'add-on (host_network, bind :8554 su tutte le interfacce).
# 172.30.32.1 (gateway hassio) e' il ripiego; l'IP LAN e' install-specifico, non qui.
DEFAULT_ADDON_RTSP = "rtsp://127.0.0.1:8554/intercom"

# Entita' del device MQTT dell'add-on, per UNIQUE_ID stabile (gli entity_id NON sono
# deducibili: vanno risolti dal registro, platform "mqtt"). Vedi
# [[reference_ha_embed_camera_stream]] e la lezione del 22/11 sugli entity_id.
ADDON_UNIQUE_IDS = {
    "call_sensor": ("binary_sensor", "vimar_vdc_call"),
    "answer": ("button", "vimar_vdc_answer"),
    "door": ("button", "vimar_vdc_door"),
    "hangup": ("button", "vimar_vdc_hangup"),
    "status_sensor": ("sensor", "vimar_vdc_status"),  # stato conversazione (guardiano)
    "reg_sensor": ("sensor", "vimar_vdc_reg"),  # registrazione SIP (chip di stato della card)
    "autostart": ("button", "vimar_vdc_monitor"),  # Autoaccensione (chiama la targa senza suonata); solo marche che la supportano
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
