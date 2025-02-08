class ParcelTrackerCard extends HTMLElement {
  setConfig(config) {
    if (!config.api_url) {
      throw new Error("Du musst in der Konfiguration 'api_url' definieren!");
    }
    this.config = config;
  }

  connectedCallback() {
    this.innerHTML = `
        <ha-card header="Paket Tracker">
          <div id="content" style="padding: 16px;">Daten werden geladen …</div>
        </ha-card>
      `;
    this._fetchData();
    this._interval = setInterval(() => this._fetchData(), 60000);
  }

  disconnectedCallback() {
    if (this._interval) {
      clearInterval(this._interval);
    }
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
    if (Array.isArray(data)) {
      data.forEach((item) => {
        content += `<p><strong>${item.tracking_name ?? item.tracking_number}</strong>: ${item.status}</p>`;
      });
    } else {
      content = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    }
    this.innerHTML = `
        <ha-card header="Paket Tracker">
          <div id="content" style="padding: 16px;">${content}</div>
        </ha-card>
      `;
  }

  _displayError(error) {
    this.innerHTML = `
        <ha-card header="Paket Tracker">
          <div id="content" style="padding: 16px; color: red;">Fehler beim Abrufen der Daten: ${error.message}</div>
        </ha-card>
      `;
  }
}
customElements.define("parcel-tracker-card", ParcelTrackerCard);
