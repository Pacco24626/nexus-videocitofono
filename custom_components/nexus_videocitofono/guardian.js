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
  var VERSION = "0.2.1";
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
    ".video img{width:100%;height:100%;object-fit:cover;display:block}" +
    ".parla{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:6px;background:rgba(0,0,0,.55);color:#fff;padding:4px 12px;border-radius:999px;font-size:11px}" +
    ".parla ha-icon{--mdc-icon-size:15px}" +
    ".cmds{display:grid;gap:10px;margin-top:14px}" +
    ".cmd{display:flex;flex-direction:column;align-items:center;gap:8px;border:0;background:transparent;cursor:pointer;font-size:13px;font-weight:500;color:var(--primary-text-color,#1F2933)}" +
    ".cmd .cer{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center}" +
    ".cmd .cer ha-icon{--mdc-icon-size:28px;color:#fff}" +
    ".cmd:active{transform:scale(.96)}";

  var cfg = null, host = null, sr = null, dismissed = false;

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
    var cam = c.camera && hass.states[c.camera];
    var pic = cam && cam.attributes && cam.attributes.entity_picture;
    if (pic) {
      return '<div class="video" id="video"><img id="img" src="' + esc(pic) + '">' +
        '<div class="parla"><ha-icon icon="mdi:microphone"></ha-icon>tocca per parlare</div></div>';
    }
    return '<div class="video" id="video"><ha-icon icon="mdi:cctv" style="--mdc-icon-size:46px;color:#bbb"></ha-icon></div>';
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
    var $ = function (id) { return sr.getElementById(id); };
    $("bd").addEventListener("click", function (e) { if (e.target === $("bd")) close(); });
    if ($("close")) $("close").onclick = userDismiss;
    if (c.answer && $("answer")) $("answer").onclick = function () { activate(hass, c.answer); };
    if (c.door && $("door")) $("door").onclick = function () { activate(hass, c.door); };
    if (c.hangup && $("hangup")) $("hangup").onclick = function () { activate(hass, c.hangup); userDismiss(); };
    if (c.camera && $("video")) $("video").onclick = function () {
      host.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: c.camera }, bubbles: true, composed: true }));
    };
  }

  function refreshVideo(hass) {
    if (!sr || !cfg || !cfg.camera) return;
    var img = sr.getElementById("img");
    var cam = hass.states[cfg.camera];
    var pic = cam && cam.attributes && cam.attributes.entity_picture;
    if (img && pic && img.getAttribute("src") !== pic) img.setAttribute("src", pic);
  }

  function close() { if (host) { host.remove(); host = null; sr = null; } }
  function userDismiss() { dismissed = true; close(); } // chiusura utente: non riaprire finche' squilla

  function tick() {
    var hass = getHass();
    if (!hass) return;
    if (!cfg) { ensureCfg(hass); return; }
    if (!lsGet()) { if (host) close(); dismissed = false; return; } // non abilitato qui
    var on = callIsOn(hass);
    if (!on) { dismissed = false; if (host) close(); return; } // fine chiamata: reset + chiudi
    if (host) { refreshVideo(hass); return; }
    if (!dismissed) show(hass); // non riaprire se l'utente ha chiuso QUESTA chiamata
  }

  setInterval(tick, 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) setTimeout(tick, 150); });
})();
