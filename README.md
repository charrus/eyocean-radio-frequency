# EYOCEAN RF Desk Lamp for Home Assistant

Custom integration that sends EYOCEAN lamp commands through Home Assistant's **native `radio_frequency` transmitter abstraction**. It does not call ESPHome services or hardcode GPIOs/IP addresses, and can use any registered compatible 433.92 MHz OOK adapter.

**Tested against Home Assistant Core 2026.10.4 and rf-protocols 4.3.0.** No physical RF transmission or lamp response has been tested by creating this project. Native RF APIs are recent; other HA versions require their own compatibility checks.

## What it exposes

One device with six stateless buttons:

| Button | Command byte |
|---|---|
| Power toggle | `0x51` |
| Brightness cycle | `0x5B` |
| Color temperature cycle | `0x5A` |
| Reading mode | `0x49` |
| Night light | `0x41` by default |
| Timer | `0x4D` by default |

Enable **Swap Night light and Timer command codes** for variants where those functions are reversed. A remote variant may not support every listed function; disable unsupported button entities in Home Assistant.

The lamp has no feedback channel and the known commands are toggles/cycles. This integration deliberately does **not** create a misleading light entity, absolute brightness slider, or confirmed on/off state. Button timestamps mean that a button was invoked, not that the lamp responded. Adapter availability is tracked; transmitter errors propagate to Home Assistant.

## Prerequisites

1. Home Assistant Core **2026.10.4** (the version tested here), with support for the native `radio_frequency` domain.
2. An existing RF transmitter entity supporting **433.92 MHz ASK/OOK**, such as an ESPHome CC1101 RF proxy. Configure its RF hardware, antenna path and TX/RX switching correctly; proxy frequency metadata alone does not tune a radio.
3. A compatible EYOCEAN **32-bit fixed-code** remote. Not all EYOCEAN models are known to use this protocol.
4. The **remote ID** (16 bits) and **XOR key** (8 bits), captured from your own original remote. These are independent per-remote values, not universal model identifiers.

This integration does not scan frequencies, pair a lamp, capture RF, or send a test transmission during setup. Current stable HA 2026.10.4 exposes transmitter consumers but not the receiver-consumer API present on the upstream development branch. Learn identity values using ESPHome's existing decoder/logs or a separate capture tool, then enter them in setup.

## Installation

### Install with HACS (recommended)

Install [HACS](https://hacs.xyz/) first, then click the button below to open this integration's repository in your Home Assistant instance:

[![Open marketplace repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=charrus&repository=eyocean-radio-frequency&category=integration)

1. Download **EYOCEAN RF Desk Lamp** in HACS. Enable prerelease versions if the initial release is not listed.
2. Restart Home Assistant.
3. Continue to [Configuration](#configuration) below to add your lamp.

The button requires [My Home Assistant](https://my.home-assistant.io/) configured with your instance's URL. If you prefer to add the repository manually, go to **HACS → Custom repositories**, add `https://github.com/charrus/eyocean-radio-frequency` with type **Integration**, then download it and restart Home Assistant. This integration is not included in the default HACS catalog.

### Install manually

1. Back up your Home Assistant configuration. If you already have a custom `eyocean` integration, back it up rather than overwrite it blindly.
2. Copy the **entire** `custom_components/eyocean` directory into your Home Assistant configuration directory:

   ```text
   <HA config>/custom_components/eyocean/
     __init__.py
     button.py
     config_flow.py
     const.py
     manifest.json
     protocol.py
     strings.json
     translations/en.json
     UPSTREAM_LICENSE.txt
   ```

   The release ZIP contains the `custom_components/eyocean/` layout and README. Extract it into the HA configuration directory, not inside another `eyocean` subdirectory. The project root's `custom_components/__init__.py` is a test-discovery helper and is not included in the ZIP.
3. Restart Home Assistant **when you are ready**. Creating this project does not install or restart anything.
4. Continue to [Configuration](#configuration) below to add your lamp.

## Configuration

After installing the integration and restarting Home Assistant, click **Add integration** below to start setup. This shortcut also requires My Home Assistant configured with your instance's URL.

[![Add integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eyocean)

Alternatively, go to **Settings → Devices & services → Add integration → EYOCEAN RF Desk Lamp**.

Choose the existing compatible RF transmitter. Enter a lamp name, remote ID, XOR key, repeat count and optional Night/Timer swap. Have the values listed under [Prerequisites](#prerequisites) ready; installation does not configure your transmitter or capture your remote identity for you.

ID fields accept one to four / one to two hexadecimal digits, with optional `0x` prefix. The remote ID cannot be zero; the XOR key can. Do not paste a full 32-bit frame into the remote-ID field. Setup refuses duplicate ID/key pairs, even across different adapters, because the pair identifies the same RF remote command group.

The UI stores a stable transmitter registry reference, so normal entity renaming does not break the integration. Use the integration entry's **Reconfigure** menu to change adapter, identity, name, repeats or Night/Timer assignment. Reconfiguration itself sends no RF commands. A missing transmitter registry entry requires reconfiguration; an offline adapter leaves buttons unavailable until it returns.

The project is licensed under **MIT**; see [LICENSE](LICENSE). Upstream protocol attribution and its MIT notice are retained separately in `custom_components/eyocean/UPSTREAM_LICENSE.txt`.

## ESPHome proxy example

If your existing device already has `rf_tx`, add this alongside—not instead of—its other top-level components:

```yaml
radio_frequency:
  - platform: ir_rf_proxy
    name: 433MHz RF Transmitter
    frequency: 433.92MHz
    remote_transmitter_id: rf_tx
```

Its referenced `remote_transmitter` must have `carrier_duty_percent: 100%`. With CC1101, it must enter TX via `cc1101.begin_tx` before sending and return to RX via `cc1101.begin_rx` on completion. Do not copy generic GPIOs onto the T-Embed. The integration's buttons use this direct proxy path: an ESPHome switch guarding a separate lamp-button script **does not gate proxy transmissions**.

Do not add a second `radio_frequency:` key if your YAML already has one; merge entries. A transmitter appearing in **Settings → Connectivity → Radio Frequency** should be offered when it declares the matching frequency and modulation.

## Signal and repetition

Published frame structure:

```text
(remote_id << 16) | (command << 8) | (command XOR xor_key)
```

A frame begins `+250, -6250` microseconds, then 32 bits MSB-first: zero=`+250,-750`, one=`+750,-250`. The default is **eight total transmissions**. `rf_protocols.repeat_count` counts additional transmissions, so this integration sets it to **seven**, not eight. The native ESPHome adapter adds one when passing the total to its API.

Repeat count is configurable from 1 to 20. Local button requests across **all EYOCEAN entries using the same transmitter registry UUID** are serialized and spaced by the encoded burst airtime. Unused transmitter-lock bookkeeping is released on unload. This is not a hardware acknowledgment and does not coordinate unrelated integrations using the same adapter. Keep appropriate RF duty cycle and local regulations in mind. There is no automatic replay, boot-time command or setup-time command.

## Development and checks

Use Python 3.14:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
.venv/bin/python scripts/package.py
```

Tests execute actual HA config-entry setup, native RF entities and the native send helper with an explicitly **in-memory test transmitter**. They cover published waveform vectors, validation, UI setup, duplicate prevention, reconfiguration, Night/Timer swapping, adapter availability and rename handling, error propagation, unload/reload, and absence of setup transmissions. They do not prove physical radio timing, range, flash state, lamp compatibility or lamp response.

## Attribution

Protocol timings, frame structure and command mapping are based on [bl4ko/eyocean-ha](https://github.com/bl4ko/eyocean-ha). Its MIT notice is retained in `UPSTREAM_LICENSE.txt`. Home Assistant's native API usage was checked against the locally installed 2026.10.4 `radio_frequency`, `esphome.radio_frequency` and `honeywell_string_lights` source. Upstream `dev` has different APIs and was not treated as proof of stable-release compatibility.
