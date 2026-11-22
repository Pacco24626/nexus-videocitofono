"""Lettura di SOLA LETTURA dal VTO Dahua via CGI (digest admin), per il config flow.

Durante la configurazione guidata l'add-on non e' ancora avviato, quindi
l'integrazione non puo' chiamare i metodi del plugin: rifacciamo qui le due CGI
(semplici) per validare le credenziali e ricavare modello + elenco interni SIP.
NON legge MAI le password degli interni (VTHPassword): solo numero e tipo.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8)


def _parse_challenge(header: str) -> dict[str, str]:
    """Scompone un header WWW-Authenticate: Digest in un dizionario."""
    out: dict[str, str] = {}
    _scheme, _, rest = header.partition(" ")
    for part in rest.split(","):
        if "=" not in part:
            continue
        key, _, val = part.strip().partition("=")
        out[key.strip().lower()] = val.strip().strip('"')
    return out


def _digest_header(method: str, uri: str, user: str, password: str, chal: dict[str, str]) -> str:
    """Costruisce l'header Authorization: Digest (MD5, qop=auth) per una richiesta."""
    realm = chal.get("realm", "")
    nonce = chal.get("nonce", "")
    qop = chal.get("qop", "")
    algorithm = chal.get("algorithm", "MD5")
    opaque = chal.get("opaque")

    def md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    ha1 = md5(f"{user}:{realm}:{password}")
    ha2 = md5(f"{method}:{uri}")
    nc = "00000001"
    cnonce = os.urandom(8).hex()
    if qop:
        response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
    else:
        response = md5(f"{ha1}:{nonce}:{ha2}")
    parts = [
        f'username="{user}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        f"algorithm={algorithm}",
    ]
    if qop:
        parts += ["qop=auth", f"nc={nc}", f'cnonce="{cnonce}"']
    if opaque:
        parts.append(f'opaque="{opaque}"')
    return "Digest " + ", ".join(parts)


async def _digest_get(
    session: aiohttp.ClientSession, base: str, path: str, user: str, password: str
) -> str | None:
    """GET con autenticazione digest in due passi; None se errore/credenziali errate."""
    url = base + path
    try:
        async with session.get(url, timeout=_TIMEOUT) as r1:
            if r1.status == 200:
                return await r1.text()
            if r1.status != 401:
                return None
            chal = _parse_challenge(r1.headers.get("WWW-Authenticate", ""))
        auth = _digest_header("GET", path, user, password, chal)
        async with session.get(url, headers={"Authorization": auth}, timeout=_TIMEOUT) as r2:
            if r2.status == 200:
                return await r2.text()
            return None
    except (aiohttp.ClientError, TimeoutError, OSError) as err:  # noqa: BLE001
        _LOGGER.debug("Dahua VTO %s: %s", path, err)
        return None


def _kv(text: str) -> dict[str, str]:
    """Risposte CGI 'chiave=valore' una per riga."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip()
    return out


def _parse_contacts(text: str) -> list[dict[str, str]]:
    """recordFinder VideoTalkContact -> [{id, type}] (numero + tipo, MAI la password)."""
    rows: dict[int, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("records[") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        try:
            idx = int(key[key.index("[") + 1 : key.index("]")])
        except (ValueError, IndexError):
            continue
        field = key.split(".")[-1].strip()
        rows.setdefault(idx, {})[field] = val.strip()
    out: list[dict[str, str]] = []
    for idx in sorted(rows):
        num = rows[idx].get("VTShortNumber")
        if num:
            out.append({"id": num, "type": rows[idx].get("Type", "")})
    return out


async def async_probe_vto(
    hass: HomeAssistant, ip: str, user: str, password: str
) -> dict[str, Any]:
    """Valida le credenziali e ritorna {ok, error, device, extensions}.

    - ok False + error 'auth' se IP irraggiungibile o credenziali errate.
    - device: {manufacturer, model, sw_version}.
    - extensions: [{id, type}] (es. {"id": "9901#0", "type": "VTH"}), senza password.
    """
    session = async_get_clientsession(hass)
    base = f"http://{ip}"

    device_type = await _digest_get(
        session, base, "/cgi-bin/magicBox.cgi?action=getDeviceType", user, password
    )
    if device_type is None:
        return {"ok": False, "error": "auth", "device": {}, "extensions": []}

    software = await _digest_get(
        session, base, "/cgi-bin/magicBox.cgi?action=getSoftwareVersion", user, password
    )
    device = {
        "manufacturer": "Dahua",
        "model": _kv(device_type).get("type", ""),
        "sw_version": _kv(software or "").get("version", ""),
    }

    contacts = await _digest_get(
        session,
        base,
        "/cgi-bin/recordFinder.cgi?action=find&name=VideoTalkContact",
        user,
        password,
    )
    return {
        "ok": True,
        "error": None,
        "device": device,
        "extensions": _parse_contacts(contacts or ""),
    }
