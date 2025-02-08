class ParcelTrackerCard extends HTMLElement {
  setConfig(config) {
    if (!config.api_url) {
      throw new Error("Du musst in der Konfiguration 'api_url' definieren!");
    }
    this.config = config;
  }

  connectedCallback() {
    this.renderLoading();
    this._fetchData();
    const intervalMs = this.config.update_interval
      ? this.config.update_interval * 60000
      : 60000;
    this._interval = setInterval(() => this._fetchData(), intervalMs);
  }

  disconnectedCallback() {
    if (this._interval) {
      clearInterval(this._interval);
    }
  }

  renderLoading() {
    this.innerHTML = `
      <ha-card header="Paket Tracker">
        <div id="content" style="padding: 16px; text-align: center;">
          Daten werden geladen …
        </div>
      </ha-card>
    `;
  }

  async _fetchData() {
    try {
      const response = await fetch(this.config.api_url);
      if (!response.ok) {
        throw new Error(`HTTP-Fehler: ${response.status}`);
      }
      const data = await response.json();
      this._renderData(data);
    } catch (error) {
      this._displayError(error);
    }
  }

  _renderData(data) {
    let content = "";
    if (Array.isArray(data) && data.length > 0) {
      data.forEach((item, index) => {
        const title = item.tracking_name
          ? `${item.tracking_name} (${item.tracking_number})`
          : item.tracking_number;
        const bgColor =
          index % 2 === 0
            ? "rgba(255, 255, 255, 0.05)"
            : "rgba(255, 255, 255, 0.1)";
        const marginBottom = index < data.length - 1 ? "4px" : "0";
        const progressBar =
          item.progress != null &&
          item.maxProgress != null &&
          item.maxProgress > 0
            ? `<div style="margin-top: 4px; height: 8px; background: #444; border-radius: 4px;">
               <div style="height: 8px; width: ${(
                 (item.progress / item.maxProgress) *
                 100
               ).toFixed(0)}%; background: #2196F3; border-radius: 4px;"></div>
             </div>`
            : "";
        content += `<div style="padding: 8px; background: ${bgColor}; border-radius: 12px; margin-bottom: ${marginBottom};">
                      <div style="font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${title}</div>
                      <div style="font-size: 0.9em; color: #ccc;">${item.status}</div>
                      ${progressBar}
                    </div>`;
      });
    } else {
      content = `<div style="padding: 8px; text-align: center;">Keine Sendungen gefunden.</div>`;
    }
    this.innerHTML = `
      <ha-card header="Paket Tracker">
        <div id="content" style="padding: 8px;">${content}</div>
      </ha-card>
    `;
  }

  _displayError(error) {
    this.innerHTML = `
      <ha-card header="Paket Tracker">
        <div id="content" style="padding: 16px; color: red; text-align: center;">
          Fehler beim Abrufen der Daten: ${error.message}
        </div>
      </ha-card>
    `;
  }
}

customElements.define("parcel-tracker-card", ParcelTrackerCard);
