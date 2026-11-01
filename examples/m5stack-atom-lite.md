# M5Stack ATOM Lite

Use an ATOM Lite with an **external 433.92 MHz ASK/OOK transmitter and receiver** as a Home Assistant RF proxy. The [ESPHome configuration](m5stack-atom-lite.yaml) also logs candidate EYOCEAN remote identities, exposes the RGB LED, and reports the physical button state.

This example targets the original ESP32 ATOM Lite, not the ATOM S3 Lite. The ATOM Lite has no built-in RF radio.

## Wiring

| Signal | GPIO | Purpose |
|---|---|---|
| External transmitter data input | GPIO25 | Sends OOK pulses |
| External receiver data output | GPIO19 | Receives pulses for the proxy and candidate decoder |
| Built-in RGB LED | GPIO27 | SK6812 LED exposed to Home Assistant |
| Built-in button | GPIO39 | Active-low input exposed as **Atom Button** |

Connect the modules' ground to the ATOM Lite's ground. Check their supply requirements and ensure data connections use ESP32-safe logic levels. The YAML does not tune the external radio: the modules themselves must support 433.92 MHz OOK. Fit an antenna according to the module's instructions.

## Setup

1. Copy [m5stack-atom-lite.yaml](m5stack-atom-lite.yaml) into your ESPHome configuration directory. The file declares ESPHome **2026.10.1** as its minimum version.
2. Customize `name` and `friendly_name`, and adjust TX/RX pins to match your wiring.
3. Add the following to your private `secrets.yaml` alongside the copied configuration:

   ```yaml
   api_key: "<device-specific base64 API encryption key>"
   wifi_ssid: "<your Wi-Fi SSID>"
   wifi_password: "<your Wi-Fi password>"
   ```

   Generate the API key with `openssl rand -base64 32`. Keep secrets out of version control.
4. Validate, compile and flash through ESPHome. With the CLI:

   ```sh
   esphome config m5stack-atom-lite.yaml
   esphome run m5stack-atom-lite.yaml
   esphome logs m5stack-atom-lite.yaml
   ```

5. Add the device through Home Assistant's ESPHome integration. It exposes **433MHz RF Transmitter** and **433MHz RF Receiver**.

## Capture your remote identity

Open the ESPHome logs and press a button on your original lamp remote. A recognized candidate produces an INFO message such as:

```text
Candidate frame=0xC6FB5109 remote_id=0xC6FB xor_key=0x58 command=0x51
```

These are example values, not defaults for your lamp. Press several different buttons and check that `remote_id` and `xor_key` stay consistent while `command` changes. Repeated RF frames can produce multiple messages per press. The decoder checks pulse timing and the six [known command bytes](../README.md#what-it-exposes); it does not authenticate the remote or confirm a lamp response.

Add **EYOCEAN RF Desk Lamp** in Home Assistant, select this device's **433MHz RF Transmitter**, and enter your captured remote ID and XOR key. Follow the [integration configuration instructions](../README.md#configuration). Do not enter the full `frame` value as the remote ID.

## Behavior and troubleshooting

- **Atom Button** only reports a press; no lamp command is attached to it. The LED is independently controllable and does not indicate RF reception or lamp state.
- No lamp command is sent at boot. The proxy accepts Home Assistant transmission requests without a local enable switch.
- If no candidate appears, check receiver power, ground, data wiring, antenna and remote compatibility. Set `logger.level: DEBUG` to inspect raw pulse dumps; candidate messages use INFO.
- If the transmitter is missing in setup, confirm the ESPHome device is connected and exposes its RF transmitter, then check the [integration prerequisites](../README.md#prerequisites).
- If requests succeed but the lamp does not react, check the captured identity, transmitter wiring, frequency and antenna. A successful request does not confirm reception by the lamp.
