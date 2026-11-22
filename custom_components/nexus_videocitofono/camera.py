"""Telecamera del videocitofono: ripubblica lo stream "intercom" dell'add-on.

Caricata SOLO quando use_addon e' ON. E' una camera con stream_source RTSP: dal
2024.11 il go2rtc integrato di HA le fa da provider WebRTC in automatico, quindi il
player (RTCPeerConnection + camera/webrtc/offer) funziona senza negoziazione custom.
L'audio bidirezionale (backchannel) e' un problema separato (2c).
"""
from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDON_RTSP, DEFAULT_ADDON_RTSP, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Ci si arriva SOLO se use_addon e' ON (forward condizionato in __init__)."""
    async_add_entities([VideocitofonoCamera(entry)])


class VideocitofonoCamera(Camera):
    """Camera che punta allo stream RTSP del go2rtc dell'add-on."""

    _attr_has_entity_name = True
    _attr_name = "Videocitofono"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__()
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    def _rtsp(self) -> str:
        return self._entry.options.get(CONF_ADDON_RTSP) or DEFAULT_ADDON_RTSP

    async def stream_source(self) -> str | None:
        """URL passato al provider go2rtc di HA (che fa il WebRTC).

        ATTENZIONE: il metodo si chiama `stream_source` (coroutine SENZA il prefisso
        `async_`): con `async_stream_source` HA usa quello della base -> None -> la
        camera risulta "HLS only / does not support streaming".
        """
        return self._rtsp()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        # Niente still dedicato: lo stream basta per card, guardiano e WebRTC.
        return None
