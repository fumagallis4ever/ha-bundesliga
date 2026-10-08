/* Bundesliga-Karte für Home Assistant – wird von der Integration "bundesliga" mitgeliefert. */

const STANDARD_ENTITIES = ["sensor.bundesliga_bl1", "sensor.bundesliga_bl2"];
const LIVE_ENTITY = "binary_sensor.bundesliga_live";

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class BundesligaCard extends HTMLElement {
  static getStubConfig() {
    return { entities: STANDARD_ENTITIES, anzeige: "heute", nur_live: false, logos: true };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "titel", selector: { text: {} } },
        {
          name: "entities",
          selector: { entity: { multiple: true, filter: { integration: "bundesliga", domain: "sensor" } } },
        },
        {
          name: "anzeige",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "heute", label: "Nur heutige Spiele" },
                { value: "spieltag", label: "Ganzer Spieltag" },
              ],
            },
          },
        },
        { name: "nur_live", selector: { boolean: {} } },
        { name: "logos", selector: { boolean: {} } },
      ],
      computeLabel: (s) =>
        ({
          titel: "Titel",
          entities: "Ligen",
          anzeige: "Anzeige",
          nur_live: "Nur anzeigen, wenn ein Spiel läuft oder bald beginnt",
          logos: "Vereinslogos anzeigen",
        })[s.name],
    };
  }

  setConfig(config) {
    this._config = {
      titel: "Bundesliga",
      entities: STANDARD_ENTITIES,
      anzeige: "heute",
      nur_live: false,
      logos: true,
      ...config,
    };
    if (!Array.isArray(this._config.entities) || !this._config.entities.length) {
      this._config.entities = STANDARD_ENTITIES;
    }
    this._sig = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const ids = [...this._config.entities, LIVE_ENTITY];
    const sig = ids.map((id) => hass.states[id]?.last_updated).join("|") + new Date().getMinutes();
    if (sig === this._sig) return;
    this._sig = sig;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _zeit(iso, mitTag) {
    if (!iso) return "–";
    const d = new Date(iso);
    const uhr = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
    return mitTag ? `${d.toLocaleDateString("de-DE", { weekday: "short" })} ${uhr}` : uhr;
  }

  _zeile(s, mitTag) {
    const live = s.status === "live";
    const st = live ? '<span class="live">● live</span>' : s.status === "beendet" ? "Ende" : esc(this._zeit(s.anstoss, mitTag));
    const ergebnis =
      s.tore_heim != null ? `${esc(s.tore_heim)} : ${esc(s.tore_gast)}` : live ? "0 : 0" : "– : –";
    const logo = (url) => (this._config.logos && url ? `<img src="${esc(url)}" alt="" loading="lazy">` : "");
    const tor =
      live && s.letztes_tor_von
        ? `<tr class="tor"><td></td><td colspan="3">⚽ ${esc(s.letztes_tor_minute)}' ${esc(s.letztes_tor_von)}</td></tr>`
        : "";
    return `<tr class="${live ? "aktiv" : ""}">
        <td class="st">${st}</td>
        <td class="heim">${esc(s.heim)}${logo(s.heim_logo)}</td>
        <td class="erg">${ergebnis}</td>
        <td class="gast">${logo(s.gast_logo)}${esc(s.gast)}</td>
      </tr>${tor}`;
  }

  _render() {
    if (!this._hass || !this._config || !this.shadowRoot) return;
    const live = this._hass.states[LIVE_ENTITY]?.state === "on";
    if (this._config.nur_live && !live) {
      this.style.display = "none";
      this.shadowRoot.innerHTML = "";
      return;
    }
    this.style.display = "";

    const heute = this._config.anzeige === "heute";
    let inhalt = "";
    for (const id of this._config.entities) {
      const e = this._hass.states[id];
      if (!e) {
        inhalt += `<div class="hinweis">Entity ${esc(id)} nicht gefunden</div>`;
        continue;
      }
      let spiele = e.attributes.spiele || [];
      if (heute) spiele = spiele.filter((s) => s.heute);
      if (!spiele.length) continue;
      inhalt += `<div class="liga">${esc(e.attributes.liga)} <span>· ${esc(e.state)}</span></div>
        <table>${spiele.map((s) => this._zeile(s, !heute)).join("")}</table>`;
    }
    if (!inhalt) inhalt = `<div class="hinweis">${heute ? "Heute keine Spiele" : "Keine Spiele"}</div>`;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 12px 16px 16px; }
        .kopf { display: flex; align-items: center; gap: 8px; font-size: 1.15em; font-weight: 500; margin-bottom: 4px; }
        .kopf .punkt { margin-left: auto; font-size: 0.75em; color: var(--error-color, #db4437); font-weight: 600; }
        .liga { margin: 12px 0 4px; font-weight: 600; }
        .liga span { font-weight: 400; color: var(--secondary-text-color); }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 4px 2px; vertical-align: middle; }
        tr + tr td { border-top: 1px solid var(--divider-color); }
        tr.tor td { border-top: none; padding-top: 0; font-size: 0.85em; color: var(--secondary-text-color); }
        .st { width: 4.5em; font-size: 0.85em; color: var(--secondary-text-color); white-space: nowrap; }
        .heim { text-align: right; }
        .erg { width: 3.8em; text-align: center; font-weight: 600; white-space: nowrap; }
        .heim, .gast { overflow: hidden; text-overflow: ellipsis; }
        img { width: 20px; height: 20px; object-fit: contain; vertical-align: middle; margin: 0 6px; }
        tr.aktiv .erg { color: var(--error-color, #db4437); }
        .live { color: var(--error-color, #db4437); font-weight: 600; }
        .hinweis { color: var(--secondary-text-color); padding: 8px 0; }
      </style>
      <ha-card>
        <div class="kopf"><ha-icon icon="mdi:soccer"></ha-icon>${esc(this._config.titel)}${
          live ? '<span class="punkt">● LIVE</span>' : ""
        }</div>
        ${inhalt}
      </ha-card>`;
  }
}

if (!customElements.get("bundesliga-card")) {
  customElements.define("bundesliga-card", BundesligaCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "bundesliga-card",
    name: "Bundesliga",
    description: "Spieltag, Ergebnisse und Live-Spiele aus der Bundesliga-Integration",
    preview: true,
  });
}
