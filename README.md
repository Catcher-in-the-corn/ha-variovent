# Variovent DUO-Live for Home Assistant

Local control of **Variovent / ZSA DUO-Live** decentralised ventilation systems through the
**DUO-Live X-Spot** ("Control Center X-Serie") – no cloud, no changes to the spot.

The integration speaks the same local API the spot's own web interface uses, so everything
you can see and switch there is available in Home Assistant.

## Features

Per ventilator (DUO-Live, DUO-Smart, MONO-Smart, Silent variants):

| Entity | Description |
|---|---|
| Fan | on/off, 5 fan levels (0–4), operating mode as preset |
| Select *Operating mode* | Off, weekly schedule, normal, automatic, summer, party, away, supply air, exhaust air, humidity extraction, air quality |
| Select *Fan level* | 0–4 |
| Sensors | temperature (2nd temperature on DUO-Live), humidity, air quality (value + good/moderate/poor), active operating mode, hours until filter change, operating hours, radio signal |
| Binary sensors | filter change due, fault |
| Numbers (configuration) | settings of the operating modes, as in the spot's settings dialogs: *humidity extraction* (raise level above X %, by N levels, exhaust air above Y %, back below Z %), *air quality* (raise level above X, back below Y), *exhaust air* (leave below X % humidity), *party* (duration, fan level) |

For the spot: number of error messages, available firmware.

Like the spot's web UI, room sensors are reported as *unavailable* while a ventilator is
switched off – the device does not measure then and the last values would be stale.

DUO pairs (two units running in alternating direction) are shown as two devices. The spot
applies a change made to one unit to its partner as well; the partner's state in Home
Assistant follows with the next poll.

The spot accepts a fan level only in a manual operating mode. Setting a fan level on a
ventilator that is *off* or runs on its *weekly schedule* therefore switches it to normal
operation first (exhaust air for exhaust-only units). Select *weekly schedule* again to
return to the schedule.

## Installation

### HACS (recommended)

1. In Home Assistant open **HACS** → top right **⋮** → **Custom repositories**.
2. Repository: `https://github.com/Catcher-in-the-corn/ha-variovent`, type: **Integration** → **Add**.
3. Search for **Variovent DUO-Live**, open it, **Download**.
4. Restart Home Assistant.
5. **Settings → Devices & services → Add integration** → search **Variovent**.

Updates then show up in HACS automatically; a new version is one click away.

### Manual

Copy `custom_components/variovent` into the `custom_components` folder of your Home Assistant
configuration and restart.

### Configuration

* **Host** – IP address of the spot (the address you open the *Control Center* with).
* **Username / Password** – the login of the spot's web interface.

The polling interval (default 60 s) can be changed in the integration options.

## Compatibility

Tested with spot firmware **V2.08** (web app "DUO-Live Control Center"). Other firmware
versions may use a different internal protocol revision – please open an issue and attach
the integration's *diagnostics* (personal data is redacted).

## How it works / development

The spot runs a GWT web application. `custom_components/variovent/pyvariovent` contains a
small GWT-RPC client (`gwt.py`) plus a typed model (`models.py`) of the spot's data.
The same code is published as the Python package `pyvariovent`:

```bash
pip install -e .
pyvariovent --host 192.168.1.10 --user admin --password … dump
pytest
```

---

### Kurz auf Deutsch

Lokale Home-Assistant-Integration für Variovent/ZSA DUO-Live-Lüftungen über den X-Spot.
Installation über HACS (Custom Repository), danach *Integration hinzufügen → Variovent
DUO-Live* und IP-Adresse sowie Zugangsdaten der Spot-Weboberfläche eingeben.

*Not affiliated with Variovent or ZSA. All trademarks belong to their owners.*
