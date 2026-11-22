/*
 * Nexus Videocitofono — GUARDIANO
 * Caricato su OGNI pannello di Home Assistant (add_extra_js_url dall'integrazione).
 * Se QUESTO dispositivo e' abilitato, quando il videocitofono squilla apre la plancia
 * sopra qualunque pagina (come il tastierino allarme in preallarme) e la chiude a
 * fine chiamata. Definisce anche la card "nexus-videocitofono-guardian" =
 * l'interruttore per-dispositivo (ricordato in localStorage, per-origine).
 */
(function () {
  "use strict";
  var VERSION = "0.2.8";
  var LS_KEY = "nexus_vdc_guardian"; // "1" = abilitato su questo dispositivo
  if (window.__nexusVdcGuardian) return;
  window.__nexusVdcGuardian = true;
  try {
    console.info(
      "%c NEXUS-VDC GUARDIANO %c v" + VERSION + " ",
      "background:#2E9E6B;color:#fff;border-radius:3px 0 0 3px",
      "background:#333;color:#fff;border-radius:0 3px 3px 0"
    );
  } catch (e) {}

  function lsGet() { try { return localStorage.getItem(LS_KEY) === "1"; } catch (e) { return false; } }
  function lsSet(v) { try { localStorage.setItem(LS_KEY, v ? "1" : "0"); } catch (e) {} }
  function getHass() { var el = document.querySelector("home-assistant"); return el && el.hass; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var PRESS = {
    button: ["button", "press"], input_button: ["input_button", "press"],
    switch: ["switch", "turn_on"], light: ["light", "turn_on"],
    lock: ["lock", "unlock"], cover: ["cover", "open_cover"],
    script: ["script", "turn_on"], scene: ["scene", "turn_on"],
    automation: ["automation", "trigger"]
  };
  function activate(hass, ent) {
    if (!ent) return;
    var s = PRESS[ent.split(".")[0]];
    if (s) try { hass.callService(s[0], s[1], { entity_id: ent }); } catch (e) {}
  }

  // Player WebRTC incorporato: una RTCPeerConnection NOSTRA + l'API WS di HA
  // (camera/webrtc/offer). Gli elementi ha-camera-stream/ha-web-rtc-player non si
  // cablano in un overlay; questo invece riproduce una qualsiasi camera entity
  // (Dahua grezza oggi, lo stream go2rtc dell'add-on domani). Restituisce {stop()}.
  function startWebRTC(hass, entityId, videoEl, onFail) {
    var H = { stopped: false, pc: null, unsub: null, sid: null, candQ: [] };
    var pc;
    try { pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] }); }
    catch (e) { if (onFail) onFail(); return H; }
    H.pc = pc;
    var stream = new MediaStream();
    try { videoEl.srcObject = stream; } catch (e) {}
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });
    pc.ontrack = function (e) {
      try { stream.addTrack(e.track); } catch (x) {}
      if (videoEl.play) videoEl.play().catch(function () {});
    };
    function sendCand(c) {
      if (H.stopped || !H.sid) return;
      try {
        hass.connection.sendMessagePromise({
          type: "camera/webrtc/candidate", entity_id: entityId, session_id: H.sid,
          candidate: { candidate: c.candidate, sdpMid: c.sdpMid, sdpMLineIndex: c.sdpMLineIndex }
        }).catch(function () {});
      } catch (x) {}
    }
    pc.onicecandidate = function (e) {
      if (!e.candidate) return;
      if (H.sid) sendCand(e.candidate); else H.candQ.push(e.candidate);
    };
    pc.oniceconnectionstatechange = function () {
      if (pc.iceConnectionState === "failed" && onFail) onFail();
    };
    pc.createOffer().then(function (offer) {
      return pc.setLocalDescription(offer).then(function () { return offer; });
    }).then(function () {
      if (H.stopped) return;
      return hass.connection.subscribeMessage(function (msg) {
        if (H.stopped) return;
        if (msg.type === "session") { H.sid = msg.session_id; H.candQ.forEach(sendCand); H.candQ = []; }
        else if (msg.type === "answer") { pc.setRemoteDescription({ type: "answer", sdp: msg.answer }).catch(function () {}); }
        else if (msg.type === "candidate") { try { pc.addIceCandidate(msg.candidate); } catch (x) {} }
        else if (msg.type === "error") { if (onFail) onFail(); }
      }, { type: "camera/webrtc/offer", entity_id: entityId, offer: pc.localDescription.sdp }).then(
        function (unsub) { if (H.stopped) { try { unsub(); } catch (x) {} } else H.unsub = unsub; },
        function () { if (onFail) onFail(); }
      );
    }).catch(function () { if (onFail) onFail(); });
    H.stop = function () {
      H.stopped = true;
      try { if (H.unsub) H.unsub(); } catch (e) {}
      try { pc.close(); } catch (e) {}
    };
    return H;
  }

  // ====================== card: interruttore per-dispositivo ======================
  var CARD_CSS =
    "ha-card{padding:14px;display:block}" +
    ".row{display:flex;align-items:center;justify-content:space-between;gap:14px}" +
    ".t{font-size:14px;font-weight:500;color:var(--primary-text-color)}" +
    ".s{font-size:12px;color:var(--secondary-text-color);margin-top:3px;line-height:1.3}" +
    ".sw{width:46px;height:26px;border-radius:999px;background:var(--switch-unchecked-track-color,#CFD6DE);position:relative;cursor:pointer;flex:none;transition:background .15s}" +
    ".sw .k{position:absolute;top:2px;left:2px;width:22px;height:22px;border-radius:50%;background:#fff;transition:left .14s;box-shadow:0 1px 2px rgba(0,0,0,.3)}" +
    ".sw.on{background:#2E9E6B}.sw.on .k{left:22px}";

  function GuardianCard() { return HTMLElement.apply(this, arguments) || this; }
  GuardianCard.prototype = Object.create(HTMLElement.prototype);
  GuardianCard.prototype.constructor = GuardianCard;
  GuardianCard.prototype.setConfig = function (c) { this._c = c || {}; };
  Object.defineProperty(GuardianCard.prototype, "hass", {
    set: function (h) { this._h = h; if (!this._r) this._render(); }
  });
  GuardianCard.prototype._render = function () {
    this._r = this.attachShadow({ mode: "open" });
    this._r.innerHTML =
      "<style>" + CARD_CSS + "</style><ha-card><div class='row'>" +
      "<div><div class='t'>Apri il videocitofono su questo dispositivo</div>" +
      "<div class='s'>Quando qualcuno suona, la plancia compare qui sopra qualunque pagina. Vale solo per questo dispositivo/indirizzo.</div></div>" +
      "<div class='sw' id='sw'><span class='k'></span></div></div></ha-card>";
    var sw = this._r.getElementById("sw");
    function sync() { sw.className = "sw" + (lsGet() ? " on" : ""); }
    sync();
    sw.onclick = function () { lsSet(!lsGet()); sync(); };
  };
  GuardianCard.prototype.getCardSize = function () { return 1; };
  if (!customElements.get("nexus-videocitofono-guardian")) {
    customElements.define("nexus-videocitofono-guardian", GuardianCard);
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: "nexus-videocitofono-guardian",
      name: "Videocitofono: abilita su questo dispositivo",
      description: "Interruttore per-dispositivo: apre la plancia qui quando suonano.",
      preview: false
    });
  }

  // ====================== guardiano ======================
  var OVERLAY_CSS =
    ".bd{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}" +
    ".plancia{background:var(--card-background-color,#fff);color:var(--primary-text-color,#1F2933);border-radius:18px;padding:16px;width:100%;max-width:460px;box-shadow:0 18px 50px rgba(0,0,0,.5);font-family:var(--paper-font-body1_-_font-family,inherit)}" +
    ".hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}" +
    ".ttl{font-size:18px;font-weight:600}" +
    ".x{border:0;background:var(--secondary-background-color,#eee);width:34px;height:34px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--primary-text-color)}" +
    ".video{position:relative;background:#141414;border-radius:14px;aspect-ratio:16/10;overflow:hidden;display:flex;align-items:center;justify-content:center;color:#8A8A8A;cursor:pointer}" +
    ".video img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}" +
    ".video video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;background:#141414}" +
    ".video video.nxon{display:block}" +
    ".parla{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:6px;background:rgba(0,0,0,.55);color:#fff;padding:4px 12px;border-radius:999px;font-size:11px}" +
    ".parla ha-icon{--mdc-icon-size:15px}" +
    ".spk{position:absolute;top:10px;right:12px;width:30px;height:30px;border-radius:50%;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#F2F2F2}" +
    ".spk ha-icon{--mdc-icon-size:17px}" +
    ".spk.on{background:#2E9E6B;color:#fff}" +
    ".vbg{color:#555;--mdc-icon-size:46px}" +
    ".cmd.disab{opacity:.45;cursor:default}.cmd.disab:active{transform:none}" +
    ".cmds{display:grid;gap:10px;margin-top:14px}" +
    ".cmd{display:flex;flex-direction:column;align-items:center;gap:8px;border:0;background:transparent;cursor:pointer;font-size:13px;font-weight:500;color:var(--primary-text-color,#1F2933)}" +
    ".cmd .cer{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center}" +
    ".cmd .cer ha-icon{--mdc-icon-size:28px;color:#fff}" +
    ".cmd:active{transform:scale(.96)}";

  var cfg = null, host = null, sr = null, dismissed = false, shownAt = 0, rtc = null, audioOn = false;

  // Audio della targa nell'overlay: il <video> parte muto (l'autoplay muto non viene
  // bloccato); si smuta solo su gesto utente (Rispondi o il tasto altoparlante).
  function setOverlayAudio(on) {
    audioOn = !!on;
    var v = sr && sr.getElementById("live");
    if (v) { try { v.muted = !audioOn; } catch (e) {} }
    var spk = sr && sr.getElementById("spk");
    if (spk) {
      spk.className = "spk" + (audioOn ? " on" : "");
      var ic = spk.querySelector("ha-icon");
      if (ic) ic.setAttribute("icon", audioOn ? "mdi:volume-high" : "mdi:volume-off");
    }
  }
  function convActive(hass) {
    if (!cfg || !cfg.status_sensor) return false;
    var s = hass.states[cfg.status_sensor];
    return !!(s && /convers/.test((s.state || "").toLowerCase()));
  }
  function refreshButtons(hass) {
    if (!sr) return;
    var a = sr.getElementById("answer");
    if (a) { if (convActive(hass)) a.classList.add("disab"); else a.classList.remove("disab"); }
  }

  // Per quanti ms tenere aperta la plancia dopo l'apertura, anche se il sensore di
  // chiamata e' gia' tornato OFF (dato dall'integrazione via WS: molti citofoni, es.
  // Dahua, tengono il sensore ON solo ~5 s per suonata). 0 = chiudi appena va OFF.
  function holdMs() {
    var h = (cfg && typeof cfg.hold_sec === "number") ? cfg.hold_sec : 60;
    return h * 1000;
  }

  function ensureCfg(hass) {
    if (cfg) return;
    if (ensureCfg._busy) return;
    ensureCfg._busy = true;
    hass.connection.sendMessagePromise({ type: "nexus_videocitofono/config" }).then(
      function (r) { cfg = r || {}; ensureCfg._busy = false; },
      function () { ensureCfg._busy = false; }
    );
  }

  function callIsOn(hass) {
    if (!cfg || !cfg.call_sensor) return false;
    var s = hass.states[cfg.call_sensor];
    return !!(s && s.state === "on");
  }

  function videoHTML(hass, c) {
    if (!c.camera) {
      return '<div class="video" id="video"><ha-icon icon="mdi:cctv" style="--mdc-icon-size:46px;color:#bbb"></ha-icon></div>';
    }
    // Poster = snapshot istantaneo (entity_picture) mostrato subito; sopra, il <video>
    // WebRTC che lo copre appena parte il live. Cosi' niente schermo nero in attesa.
    var cam = hass.states[c.camera];
    var pic = cam && cam.attributes && cam.attributes.entity_picture;
    var poster = pic ? '<img id="img" src="' + esc(pic) + '">' : "";
    // Sfondo = icona cctv (lo still intercom non c'e' -> onerror nasconde l'img, niente
    // icona immagine rotta); sopra il <video> live; in alto a dx il tasto altoparlante.
    return '<div class="video" id="video">' +
      '<ha-icon class="vbg" icon="mdi:cctv"></ha-icon>' + poster +
      '<video id="live" autoplay playsinline muted></video>' +
      '<div class="spk" id="spk"><ha-icon icon="mdi:volume-off"></ha-icon></div>' +
      '<div class="parla"><ha-icon icon="mdi:microphone"></ha-icon>tocca per parlare</div></div>';
  }

  function overlayHTML(hass, c) {
    var cmds = [];
    if (c.answer) cmds.push(["answer", "#2E9E6B", "mdi:phone", "Rispondi"]);
    if (c.door) cmds.push(["door", "#E39B32", "mdi:door-open", "Apriporta"]);
    if (c.hangup) cmds.push(["hangup", "#DE4A51", "mdi:phone-hangup", "Riaggancia"]);
    var buttons = cmds.map(function (x) {
      return '<button class="cmd" id="' + x[0] + '"><span class="cer" style="background:' + x[1] + '">' +
        '<ha-icon icon="' + x[2] + '"></ha-icon></span><span>' + x[3] + '</span></button>';
    }).join("");
    var cmdsBox = buttons
      ? '<div class="cmds" style="grid-template-columns:repeat(' + cmds.length + ',1fr)">' + buttons + '</div>'
      : "";
    return "<style>" + OVERLAY_CSS + "</style>" +
      '<div class="bd" id="bd"><div class="plancia">' +
      '<div class="hdr"><span class="ttl">' + esc(c.title || "Videocitofono") + '</span>' +
      '<button class="x" id="close"><ha-icon icon="mdi:close"></ha-icon></button></div>' +
      videoHTML(hass, c) + cmdsBox + "</div></div>";
  }

  function show(hass) {
    var c = cfg || {};
    host = document.createElement("div");
    host.id = "nexus-vdc-overlay";
    host.style.cssText = "position:fixed;inset:0;z-index:2147483000;";
    sr = host.attachShadow({ mode: "open" });
    sr.innerHTML = overlayHTML(hass, c);
    document.body.appendChild(host);
    audioOn = false; // ogni overlay nuovo parte muto
    var $ = function (id) { return sr && sr.getElementById(id); };
    if ($("bd")) $("bd").addEventListener("click", function (e) { if (e.target === $("bd")) userDismiss(); });
    if ($("close")) $("close").onclick = userDismiss;
    // Rispondi = gesto utente -> smuto l'audio; bloccato se gia' "in conversazione"
    // (due dispositivi che rispondono riavviano il relay audio dell'add-on).
    if (c.answer && $("answer")) $("answer").onclick = function () { if (convActive(hass)) return; activate(hass, c.answer); setOverlayAudio(true); };
    if (c.door && $("door")) $("door").onclick = function () { activate(hass, c.door); };
    if (c.hangup && $("hangup")) $("hangup").onclick = function () { activate(hass, c.hangup); userDismiss(); };
    if (c.camera && $("video")) $("video").onclick = function () {
      host.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: c.camera }, bubbles: true, composed: true }));
    };
    // Tasto altoparlante: smuta/muta senza rispondere; stopPropagation per non aprire
    // la vista nativa (click sul .video). Still mancante (camera intercom): lo nascondo.
    if ($("spk")) $("spk").onclick = function (e) { e.stopPropagation(); setOverlayAudio(!audioOn); };
    var img0 = $("img");
    if (img0) img0.onerror = function () { img0.style.display = "none"; };
    // Video live via WebRTC: copre il poster snapshot appena parte lo stream.
    var vid = c.camera && $("live");
    if (vid) {
      vid.addEventListener("playing", function () { vid.classList.add("nxon"); });
      rtc = startWebRTC(hass, c.camera, vid, null);
    }
  }

  function refreshVideo(hass) {
    if (!sr || !cfg || !cfg.camera) return;
    var img = sr.getElementById("img");
    var cam = hass.states[cfg.camera];
    var pic = cam && cam.attributes && cam.attributes.entity_picture;
    if (img && pic && img.getAttribute("src") !== pic) img.setAttribute("src", pic);
  }

  function close() {
    if (rtc) { try { rtc.stop(); } catch (e) {} rtc = null; }
    if (host) { host.remove(); host = null; sr = null; }
    audioOn = false;
  }
  function userDismiss() { dismissed = true; close(); } // chiusura utente: non riaprire finche' squilla

  // Con l'add-on: il sensore STATO comanda. Torna true (in corso) / false (a riposo)
  // / null (sconosciuto -> usa il fallback sul sensore di chiamata). Serve perche' con
  // l'add-on il binary_sensor va OFF appena si RISPONDE, mentre la conversazione
  // continua: chiudere sul binary OFF farebbe sparire la plancia mentre si parla.
  function statoActive(hass) {
    if (!cfg || !cfg.status_sensor) return null;
    var s = hass.states[cfg.status_sensor];
    if (!s || s.state === "unavailable" || s.state === "unknown") return null;
    return s.state !== "a riposo";
  }

  function tick() {
    var hass = getHass();
    if (!hass) return;
    if (!cfg) { ensureCfg(hass); return; }
    if (!lsGet()) { if (host) close(); dismissed = false; shownAt = 0; return; } // non abilitato qui
    var now = Date.now();
    var sa = statoActive(hass);
    var active;
    if (sa !== null) {
      // add-on: "in corso" finche' lo Stato non torna "a riposo" (NON sul binary OFF).
      active = sa;
    } else {
      // fallback: mentre il sensore di chiamata e' ON, OPPURE — una volta aperta — per
      // almeno hold_sec dall'apertura (copre i sensori a impulso ~5 s). La finestra
      // parte da shownAt (non si aggiorna mentre e' ON: niente scia dopo una chiamata lunga).
      var on = callIsOn(hass);
      active = on || (!!host && shownAt && now < shownAt + holdMs());
    }
    if (!active) { if (host) close(); dismissed = false; shownAt = 0; return; } // fine: reset + chiudi
    if (host) { refreshVideo(hass); refreshButtons(hass); return; }
    if (!dismissed) { show(hass); shownAt = now; } // non riaprire se l'utente ha chiuso QUESTA chiamata
  }

  setInterval(tick, 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) setTimeout(tick, 150); });
})();
