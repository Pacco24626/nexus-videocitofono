"""Telecamera del videocitofono: ripubblica lo stream "intercom" dell'add-on.

Caricata SOLO quando use_addon e' ON. stream_source e' una sorgente go2rtc
`webrtc:ws://.../api/ws?src=intercom` (NON RTSP): dal 2024.11 il go2rtc integrato di HA
le fa da provider WebRTC, e il formato ws porta anche il MICROFONO del browser verso
l'add-on (traccia audio sendonly -> backchannel SIP -> targa), cosa che l'RTSP non puo'.
Il browser resta su HA (camera/webrtc/offer), quindi funziona anche da remoto; solo il
link go2rtc-HA -> go2rtc-add-on e' locale. Vedi const.py per il perche' ws e non WHEP.
"""
from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature

try:  # CameraEntityCapabilities esiste solo da HA 2026.11 (import protetto)
    from homeassistant.components.camera import CameraEntityCapabilities
except ImportError:  # core piu' vecchi: resta None -> nessun pulsante "parla" nativo
    CameraEntityCapabilities = None

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDON_SRC, DEFAULT_ADDON_SRC, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Ci si arriva SOLO se use_addon e' ON (forward condizionato in __init__)."""
    async_add_entities([VideocitofonoCamera(entry)])


class VideocitofonoCamera(Camera):
    """Camera che ripubblica lo stream "intercom" (go2rtc webrtc:ws) dell'add-on.

    Dichiara la capability two_way_audio (HA >= 2026.11): con la feature Labs
    "two_way_audio" accesa dall'utente, HA mostra il pulsante "Inizia a parlare" NATIVO
    nel more-info (usa il backchannel della sorgente webrtc:ws). Oggi il nativo usa
    getUserMedia -> solo https, come la plancia; il vantaggio vero sara' il microfono
    nativo dell'app su http (epic home-assistant/epics#102, in sviluppo).
    """

    _attr_has_entity_name = True
    _attr_name = "Videocitofono"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__()
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        # Capability two_way_audio (HA >= 2026.11): fa comparire il pulsante "parla"
        # nativo nel more-info (richiede la feature Labs accesa dall'utente + WEB_RTC, che
        # il provider go2rtc da'). L'integrazione dichiara SOLO la capability: la
        # negoziazione del mic la fa go2rtc sul backchannel della sorgente webrtc:ws.
        if CameraEntityCapabilities is not None:
            self._attr_camera_entity_capabilities = CameraEntityCapabilities(
                two_way_audio=True
            )

    def _src(self) -> str:
        return self._entry.options.get(CONF_ADDON_SRC) or DEFAULT_ADDON_SRC

    async def stream_source(self) -> str | None:
        """Sorgente passata al provider go2rtc di HA (che fa il WebRTC).

        E' una sorgente go2rtc `webrtc:ws://...` (due vie), non un RTSP: vedi const.py.
        ATTENZIONE: il metodo si chiama `stream_source` (coroutine SENZA il prefisso
        `async_`): con `async_stream_source` HA usa quello della base -> None -> la
        camera risulta "HLS only / does not support streaming".
        NOTA HLS: col provider go2rtc la camera annuncia sempre anche HLS, e ffmpeg non
        apre `webrtc:`; ma qui non si usano HLS/registrazione/stills (async_camera_image
        torna None, use_stream_for_stills resta False) -> create_stream non scatta,
        nessuna rottura pratica.
        """
        return self._src()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        # Niente still dedicato: lo stream basta per card, guardiano e WebRTC.
        return None
