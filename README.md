# Nexus Videocitofono

Integrazione **Home Assistant** che aggiunge le comodità d'uso a un videocitofono IP:
per ora la **notifica azionabile sul telefono** quando qualcuno suona (Rispondi /
Apriporta / Riaggancia direttamente dalla notifica, e tocco = apre la plancia). In
arrivo: la **plancia che compare da sola** sui tablet scelti e la distinzione
**targa / fuori porta**.

## Funziona con qualsiasi videocitofono IP

L'integrazione **non è legata a Vimar**: lavora su entità Home Assistant standard.
Ti basta che il tuo citofono esponga a HA:

1. un **sensore di chiamata** (`binary_sensor` che va a `on` quando suonano);
2. un **apriporta** (button, switch, lock, relè o uno `script`); facoltativi
   **rispondi** e **riaggancia**;
3. (per il video) uno **stream** / entità `camera`, usato dalla card.

I valori preimpostati puntano al bridge **Vimar By-me** (add-on `vimar_vdc_intercom`),
ma sono **tutti modificabili** dal pannello Configura. Esempi di citofoni che
espongono già queste entità: **Vimar By-me, Dahua VTO, Doorbird, 2N, Hikvision,
Reolink, Akuvox/Fanvil (SIP)**, o un generico **SIP via go2rtc**.

> L'**apriporta/rispondi/riaggancia** accettano entità di qualsiasi tipo (button,
> switch, lock, cover, script…): così un apriporta-relè Dahua o uno script personale
> funzionano come un button Vimar. Per casi esotici, punta a uno `script.*`.

## Installazione

1. Marketplace (ex HACS) → **⋮ → Repository personalizzati** → URL del repo con token
   di sola lettura, **Tipo: Integrazione** → Installa.
2. Riavvia Home Assistant.
3. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Nexus
   Videocitofono**.
4. Premi **Configura** e imposta telefoni, sensore di chiamata e pulsanti.

## Prerequisito per le notifiche

Sul telefono da avvisare serve l'app **Home Assistant Companion** installata e
collegata a questo impianto: è lei a creare il servizio `notify.mobile_app_…`.

## Configurazione (pannello Configura)

| Campo | A cosa serve |
|---|---|
| Attiva le notifiche | Interruttore generale |
| Telefoni da avvisare | Uno o più telefoni con l'app Companion |
| Sensore «chiamata in arrivo» | Il `binary_sensor` del citofono |
| Apriporta | Il comando che apre la porta |
| Rispondi / Riaggancia | Opzionali (lascia vuoti se il citofono non li ha) |
| Plancia da aprire al tocco | Es. `/videocitofono-vimar/citofono` |
| Titolo / Testo | Il testo della notifica |

## Licenza / stato

Prodotto Nexus-T. Versione 0.1.0 — funzione A (notifica). B (plancia automatica) e
C (sorgenti targa/fuori porta) in arrivo nello stesso pannello.
