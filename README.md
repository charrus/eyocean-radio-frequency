# EYOCEAN RF Desk Lamp for Home Assistant

Control an EYOCEAN desk lamp through Home Assistant's native `radio_frequency` integration. This custom integration works with any registered compatible 433.92 MHz OOK adapter. It does not call ESPHome services or hardcode GPIOs or IP addresses.

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

The lamp has no feedback channel, and the known commands toggle or cycle its settings. The integration therefore exposes buttons, not a light entity, an absolute brightness slider, or a confirmed on/off state. Button timestamps record requests, not lamp responses. The integration tracks adapter availability and reports transmitter errors to Home Assistant.

## Prerequisites

1. Home Assistant Core **2026.10.4** (the version tested here), with support for the native `radio_frequency` domain.
2. An existing RF transmitter entity supporting **433.92 MHz ASK/OOK**, such as an ESPHome CC1101 RF proxy. Configure its RF hardware, antenna path and TX/RX switching correctly; proxy frequency metadata alone does not tune a radio.
3. A compatible EYOCEAN **32-bit fixed-code** remote. Not all EYOCEAN models are known to use this protocol.
4. The **remote ID** (16 bits) and **XOR key** (8 bits), captured from your own original remote. These are independent per-remote values, not universal model identifiers.

Setup does not scan frequencies, pair a lamp, capture RF, or send a test transmission. Home Assistant 2026.10.4 supports transmitter consumers but lacks the receiver-consumer API on the upstream development branch. [Capture your remote ID and XOR key](#capturing-remote_id-and-xor_key) with ESPHome's decoder/logs or a separate capture tool, then enter them during setup.

## Installation

### Install with HACS (recommended)

Install [HACS](https://hacs.xyz/) first, then click the button below to open this integration's repository in your Home Assistant instance:

[![Open marketplace repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=charrus&repository=eyocean-radio-frequency&category=integration)

1. Download **EYOCEAN RF Desk Lamp** in HACS. Enable prerelease versions if the initial release is not listed.
2. Restart Home Assistant.
3. Add your lamp under [Configuration](#configuration).

The button requires [My Home Assistant](https://my.home-assistant.io/) configured with your instance's URL. If you prefer to add the repository manually, go to **HACS → Custom repositories**, add `https://github.com/charrus/eyocean-radio-frequency` with type **Integration**, then download it and restart Home Assistant. This integration is not included in the default HACS catalog.

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

   The release ZIP contains the `custom_components/eyocean/` layout and README. Extract it into the HA configuration directory, not inside another `eyocean` subdirectory. The project root's `custom_components/__init__.py` is a test-discovery helper and is not included in the ZIP.
3. Restart Home Assistant.
4. Add your lamp under [Configuration](#configuration).

## Capturing `remote_id` and `xor_key`

Capture these values from your original lamp remote before setup. Both [ESPHome proxy examples](#esphome-proxy-examples) can decode candidate frames using the supported 32-bit EYOCEAN protocol:

| Example | Capture hardware | Where to read the values |
|---|---|---|
| [M5Stack ATOM Lite guide](examples/m5stack-atom-lite.md) / [YAML](examples/m5stack-atom-lite.yaml) | External 433.92 MHz OOK receiver, with data on GPIO19 in the example | ESPHome logs |
| [T-Embed CC1101 Plus guide](examples/t-embed-cc1101-plus.md) / [YAML](examples/t-embed-cc1101-plus.yaml) | Built-in CC1101 configured for 433.92 MHz ASK/OOK | On-device display, ESPHome logs, or **Decoded remote ID** and **Decoded XOR key** text sensors in Home Assistant |

1. Follow the chosen hardware guide to wire, configure and flash the device. Receiving requires a working RF receiver and antenna; a transmitter alone cannot capture the remote.
2. Open the device's ESPHome logs, or watch the T-Embed display. Candidate messages use INFO logging; raw pulse dumps need DEBUG.
3. Press a button on your original lamp remote. If the decoder recognizes a candidate frame, it logs a message such as:

   ```text
   Candidate frame=0xC6FB5109 remote_id=0xC6FB xor_key=0x58 command=0x51
   ```

4. Press several different remote buttons. Check that `remote_id` and `xor_key` stay the same while `command` changes. One press can produce several messages because the remote repeats each frame. On the T-Embed, **Frames** counts accepted candidates and **Age** shows seconds since the latest candidate. Neither reports lamp state.
5. In [Configuration](#configuration), select your RF transmitter and enter the captured `remote_id` as **Remote ID** and `xor_key` as **XOR key**. For the example above, those would be `0xC6FB` and `0x58`. Do not enter the full frame (`0xC6FB5109`) or the command byte (`0x51`) in either field.

The values above are examples, not defaults for your lamp. The decoder checks pulse timing and known command bytes, but cannot tell whether a remote belongs to your lamp. Other compatible remotes can change the displayed values. Capture does not pair the lamp, transmit a command, or configure the integration or the T-Embed's local-button identity. Home Assistant integration buttons use the identity you enter in Home Assistant.

If no candidate appears, check receiver wiring/power, antenna, frequency and remote compatibility. Enable DEBUG logging to inspect raw pulses. The T-Embed's **Allow RF control** switch can remain off during capture; it only guards its optional local lamp buttons.

## Configuration

After installation and restart, click **Add integration** below. The shortcut requires My Home Assistant configured with your instance's URL.

[![Add integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eyocean)

Alternatively, go to **Settings → Devices & services → Add integration → EYOCEAN RF Desk Lamp**.

![EYOCEAN integration setup](image-1.png)

Choose your RF transmitter and enter a lamp name, remote ID, XOR key and repeat count. Enable the Night/Timer swap if your remote needs it. Check the [prerequisites](#prerequisites) and [capture your remote ID and XOR key](#capturing-remote_id-and-xor_key) before starting setup.

The remote ID accepts one to four hexadecimal digits; the XOR key accepts one to two. Both allow an optional `0x` prefix. The remote ID cannot be zero; the XOR key can. Do not paste a full 32-bit frame into the remote-ID field. Setup rejects duplicate ID/key pairs, even across different adapters, because each pair identifies the same RF remote command group.

Setup stores a stable transmitter registry reference, so renaming the transmitter entity does not break the integration. Use the integration entry's **Reconfigure** menu to change the adapter, remote ID, XOR key, lamp name, repeat count or Night/Timer assignment. Reconfiguration sends no RF commands. If the transmitter registry entry is missing, reconfigure the integration. If the adapter is offline, buttons remain unavailable until it returns.

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

The examples require ESPHome **2026.10.1 or later**; check compatibility when using another release. Copy one YAML file into your ESPHome configuration directory. Add `api_key`, `wifi_ssid` and `wifi_password` to your private `secrets.yaml`. Generate a separate API key for the device with `openssl rand -base64 32`, and keep secrets out of version control. The T-Embed display downloads Roboto Mono from Google Fonts during validation or compilation.

Add the flashed device to Home Assistant through the ESPHome integration, then select its **433MHz RF Transmitter** when configuring this integration. Neither example sends RF at boot. Their proxy transmitters accept Home Assistant requests without a local permission switch.

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

Do not add a second `radio_frequency:` key if your YAML already has one; merge entries. A transmitter appearing in **Settings → Connectivity → Radio Frequency** should be offered when it declares the matching frequency and modulation.

## Signal and repetition

Published frame structure:

```text
(remote_id << 16) | (command << 8) | (command XOR xor_key)
```

A frame begins `+250, -6250` microseconds, then 32 bits MSB-first: zero=`+250,-750`, one=`+750,-250`. The default is **eight total transmissions**. `rf_protocols.repeat_count` counts additional transmissions, so this integration sets it to **seven**, not eight. The native ESPHome adapter adds one when passing the total to its API.

Repeat count is configurable from 1 to 20. Button requests from all EYOCEAN entries sharing a transmitter registry UUID are sent one at a time, spaced by the encoded burst airtime. Unused transmitter locks are released on unload. This scheduling does not confirm reception or coordinate with unrelated integrations using the same adapter. Observe RF duty-cycle limits and local regulations. The integration does not automatically replay commands or send them at boot or during setup.
