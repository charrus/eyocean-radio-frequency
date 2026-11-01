# EYOCEAN RF Desk Lamp for Home Assistant

Control an EYOCEAN desk lamp with any compatible 433.92 MHz OOK adapter registered in Home Assistant. This custom integration uses the native `radio_frequency` API, without ESPHome service calls or hardcoded GPIOs or IP addresses.

Tested against **Home Assistant Core 2026.10.4 and rf-protocols 4.3.0**. Physical RF transmission and lamp response have not been tested. The native RF APIs are recent, so check compatibility before using another Home Assistant version.

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

Enable **Swap Night light and Timer command codes** if those functions are reversed on your remote. Some remotes may not support every function; disable unsupported button entities in Home Assistant.

The lamp has no feedback channel. Its known commands toggle or cycle settings, so the integration provides buttons rather than a light entity, absolute brightness slider or confirmed on/off state. Button timestamps record requests, not lamp responses. The integration tracks adapter availability and reports transmitter errors to Home Assistant.

## Prerequisites

1. Home Assistant Core **2026.10.4** (the version tested here), with support for the native `radio_frequency` domain.
2. An RF transmitter entity supporting **433.92 MHz ASK/OOK**, such as an ESPHome CC1101 RF proxy. Configure the radio, antenna path and TX/RX switching; declaring the proxy's frequency does not tune the radio.
3. A compatible EYOCEAN **32-bit fixed-code** remote. Not all EYOCEAN models are known to use this protocol.
4. The **remote ID** (16 bits) and **XOR key** (8 bits), captured from your original remote. These are separate per-remote values, not lamp-model identifiers.

Setup does not scan frequencies, pair a lamp, capture RF or send a test transmission. Home Assistant 2026.10.4 supports transmitter consumers but lacks the receiver-consumer API on the upstream development branch. [Capture your remote ID and XOR key](#capturing-remote_id-and-xor_key) using ESPHome's decoder and logs or a separate capture tool, then enter them during setup.

## Installation

### Install with HACS (recommended)

Install [HACS](https://hacs.xyz/), then open this repository in your Home Assistant instance:

[![Open marketplace repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=charrus&repository=eyocean-radio-frequency&category=integration)

1. Download **EYOCEAN RF Desk Lamp** in HACS. Enable prerelease versions if the initial release is not listed.
2. Restart Home Assistant.
3. Add your lamp under [Configuration](#configuration).

The button requires [My Home Assistant](https://my.home-assistant.io/) configured with your instance's URL. To add the repository manually, go to **HACS → Custom repositories** and add `https://github.com/charrus/eyocean-radio-frequency` with type **Integration**. Download it and restart Home Assistant. It is not in the default HACS catalog.

### Install manually

1. Back up your Home Assistant configuration, including any existing custom `eyocean` integration.
2. Copy the entire `custom_components/eyocean` directory into your Home Assistant configuration directory:

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

   If using the release ZIP, extract it into the HA configuration directory, not another `eyocean` subdirectory. It contains the `custom_components/eyocean/` layout and README, but excludes the root `custom_components/__init__.py` test-discovery helper.
3. Restart Home Assistant.
4. Add your lamp under [Configuration](#configuration).

## Capturing `remote_id` and `xor_key`

Capture both values from your original lamp remote before setup. Both [ESPHome proxy examples](#esphome-proxy-examples) decode candidate 32-bit EYOCEAN frames:

| Example | Capture hardware | Where to read the values |
|---|---|---|
| [M5Stack ATOM Lite guide](examples/m5stack-atom-lite.md) / [YAML](examples/m5stack-atom-lite.yaml) | External 433.92 MHz OOK receiver, with data on GPIO19 in the example | ESPHome logs |
| [T-Embed CC1101 Plus guide](examples/t-embed-cc1101-plus.md) / [YAML](examples/t-embed-cc1101-plus.yaml) | Built-in CC1101 configured for 433.92 MHz ASK/OOK | On-device display, ESPHome logs, or **Decoded remote ID** and **Decoded XOR key** text sensors in Home Assistant |

1. Follow the hardware guide to wire, configure and flash your device. You need a working RF receiver and antenna; a transmitter alone cannot capture the remote.
2. Open the device's ESPHome logs, or watch the T-Embed display. Candidate messages use INFO logging; raw pulse dumps need DEBUG.
3. Press a button on your original lamp remote. If the decoder recognizes a candidate frame, it logs a message such as:

   ```text
   Candidate frame=0xC6FB5109 remote_id=0xC6FB xor_key=0x58 command=0x51
   ```

4. Press several different remote buttons. Check that `remote_id` and `xor_key` stay the same while `command` changes. One press can produce several messages because the remote repeats each frame. On the T-Embed, **Frames** counts accepted candidates and **Age** shows seconds since the latest candidate. Neither reports lamp state.
5. In [Configuration](#configuration), select your RF transmitter and enter the captured `remote_id` as **Remote ID** and `xor_key` as **XOR key**. For the example above, those would be `0xC6FB` and `0x58`. Do not enter the full frame (`0xC6FB5109`) or the command byte (`0x51`) in either field.

The values above are examples, not defaults for your lamp. The decoder checks pulse timing and known command bytes, but cannot tell whether a remote belongs to your lamp. Other compatible remotes can change the displayed values. Capture does not pair the lamp or transmit commands. You must enter the captured identity separately in Home Assistant or in the T-Embed YAML for its optional local buttons.

If no candidate appears, check receiver wiring, power, antenna, frequency and remote compatibility. Enable DEBUG logging to inspect raw pulses. The T-Embed's **Allow RF control** switch can stay off during capture; it only controls permission for its optional local lamp buttons.

## Configuration

After installation and restart, click **Add integration** below. The shortcut requires My Home Assistant configured with your instance's URL.

[![Add integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eyocean)

Alternatively, go to **Settings → Devices & services → Add integration → EYOCEAN RF Desk Lamp**.

![EYOCEAN integration setup](image-1.png)

Choose your RF transmitter and enter a lamp name, remote ID, XOR key and repeat count. Enable the Night/Timer swap if your remote needs it. Check the [prerequisites](#prerequisites) and [capture your remote ID and XOR key](#capturing-remote_id-and-xor_key) before starting setup.

The remote ID accepts one to four hexadecimal digits; the XOR key accepts one to two. Both allow an optional `0x` prefix. The remote ID cannot be zero; the XOR key can. Do not paste a full 32-bit frame into the remote-ID field. Each ID/key pair identifies one RF remote command group, so setup rejects duplicates even when they use different adapters.

Setup stores a transmitter registry reference that survives entity renaming. Use the integration entry's **Reconfigure** menu to change the adapter, remote ID, XOR key, lamp name, repeat count or Night/Timer assignment. Reconfiguration sends no RF commands. A missing transmitter registry entry requires reconfiguration; an offline adapter leaves buttons unavailable until it returns.

The project is licensed under **MIT**; see [LICENSE](LICENSE). Upstream protocol attribution and its MIT notice are retained separately in `custom_components/eyocean/UPSTREAM_LICENSE.txt`.

## ESPHome proxy examples

Complete ESPHome configurations are in [`examples/`](examples):

| Configuration | Hardware guide | Features |
|---|---|---|
| [`m5stack-atom-lite.yaml`](examples/m5stack-atom-lite.yaml) | [M5Stack ATOM Lite](examples/m5stack-atom-lite.md) with an external 433.92 MHz OOK transmitter/receiver | RF proxy, candidate remote-ID/key logging, RGB LED and button |
| [`t-embed-cc1101-plus.yaml`](examples/t-embed-cc1101-plus.yaml) | [LILYGO T-Embed CC1101 Plus](examples/t-embed-cc1101-plus.md) | CC1101 RF proxy, IR proxy, candidate decode display and optional local lamp buttons |

The examples have credentials and remote identities removed. Check your board revision and wiring before using them:

- The ATOM Lite has no built-in RF radio. Its example uses GPIO25 for external TX data and GPIO19 for RX data. Check the attached module's power requirements and logic levels.
- The T-Embed example uses the CC1101 Plus pinout and selects the 433 MHz antenna path. SD and nRF24L01 stay inactive; NFC and charger control are not configured.

Use ESPHome **2026.10.1 or later**, and check compatibility if using another release. Copy one YAML file into your ESPHome configuration directory. Add `api_key`, `wifi_ssid` and `wifi_password` to your private `secrets.yaml`. Generate a separate API key for the device with `openssl rand -base64 32`, and keep secrets out of version control. The T-Embed display downloads Roboto Mono from Google Fonts during validation or compilation.

After flashing, add the device through Home Assistant's ESPHome integration. Select its **433MHz RF Transmitter** when setting up EYOCEAN RF Desk Lamp. Neither example sends RF at boot, but both accept Home Assistant transmission requests without a local permission switch.

To use the T-Embed's optional local lamp buttons, replace the zeroed `remote_id` and `xor_key` in the YAML with your captured values, then enable **Allow RF control**. The switch resets to off at boot and **does not block RF or IR proxy transmissions**. Home Assistant integration buttons use the identity entered in Home Assistant, not the YAML substitutions. Decoded candidates never overwrite the configured identity.

If your device already has `rf_tx`, add this alongside its other top-level components:

```yaml
radio_frequency:
  - platform: ir_rf_proxy
    name: 433MHz RF Transmitter
    frequency: 433.92MHz
    remote_transmitter_id: rf_tx
```

The referenced `remote_transmitter` must have `carrier_duty_percent: 100%`. With CC1101, it must enter TX via `cc1101.begin_tx` before sending and return to RX via `cc1101.begin_rx` on completion. Do not copy generic GPIOs onto the T-Embed. Integration buttons transmit directly through the proxy, bypassing switches that guard separate ESPHome lamp-button scripts.

If your YAML already has a `radio_frequency:` key, merge the entries rather than adding another key. A transmitter listed in **Settings → Connectivity → Radio Frequency** should appear in setup if it declares the matching frequency and modulation.

## Signal and repetition

Published frame structure:

```text
(remote_id << 16) | (command << 8) | (command XOR xor_key)
```

A frame begins `+250, -6250` microseconds, then 32 bits MSB-first: zero=`+250,-750`, one=`+750,-250`. The default is **eight total transmissions**. `rf_protocols.repeat_count` counts additional transmissions, so this integration sets it to **seven**, not eight. The native ESPHome adapter adds one when passing the total to its API.

Set the total repeat count from 1 to 20. All EYOCEAN entries sharing a transmitter registry UUID send button requests one at a time, spaced by the encoded burst airtime. Unused transmitter locks are released on unload. This does not confirm reception or coordinate with other integrations using the adapter. Observe RF duty-cycle limits and local regulations. Commands are never replayed automatically or sent at boot or during setup.

## Development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run the commands below from the repository root. uv manages `.venv` and uses Python 3.14.4, pinned in `.python-version`. The supported range is Python 3.14.2 through 3.14.x; Home Assistant requires at least 3.14.2.

```sh
uv sync --locked
uv run --locked prek install
uv run --locked python -m pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check custom_components tests scripts
uv run --locked prek run --all-files
uv run --locked python scripts/package.py
```

Add development tools with `uv add --dev <package>`. This updates `[dependency-groups].dev` in `pyproject.toml` and the resolved versions in `uv.lock`; commit both files. Do not mix pip installs into this workflow. The pre-commit hooks check the lockfile, lint and formatting in the project environment. CI also runs tests and packaging.

Home Assistant installs the integration; it is not a Python package. The packaging script builds and verifies `dist/eyocean-radio-frequency-<version>.zip`, using the version in the integration manifest. Tests use an in-memory RF transmitter, so they cannot verify physical radio timing or lamp response.
