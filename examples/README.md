# ESPHome examples

Use either configuration as a 433.92 MHz ASK/OOK RF proxy for the [EYOCEAN RF Desk Lamp integration](../README.md). Both decode candidate frames so you can capture `remote_id` and `xor_key` from your original remote before setting up the integration.

## Choose an example

| Hardware guide | ESPHome configuration | RF hardware | Capture output | Other features |
|---|---|---|---|---|
| [M5Stack ATOM Lite](m5stack-atom-lite.md) | [m5stack-atom-lite.yaml](m5stack-atom-lite.yaml) | External 433.92 MHz OOK transmitter and receiver required | ESPHome logs | RGB LED control and physical button state |
| [LILYGO T-Embed CC1101 Plus](t-embed-cc1101-plus.md) | [t-embed-cc1101-plus.yaml](t-embed-cc1101-plus.yaml) | Built-in CC1101 | Display, ESPHome logs and decoded identity text sensors | IR proxy, display backlight and optional local lamp buttons |

Choose the configuration for your board: the original ESP32 ATOM Lite, not the ATOM S3 Lite, or the T-Embed **CC1101 Plus**. Their pinouts differ. Check your board revision and read its guide before wiring or flashing.

## Get started

1. Follow the chosen hardware guide and copy its YAML into your ESPHome configuration directory. Both files require ESPHome **2026.10.1** or later.
2. Set the device name and add `api_key`, `wifi_ssid` and `wifi_password` to your private `secrets.yaml`. Generate a device-specific API encryption key with `openssl rand -base64 32`. Keep secrets out of version control.
3. Validate, compile and flash with ESPHome. The T-Embed display uses Google Fonts, so validation and compilation need network access unless the font is cached.
4. Press several buttons on your original lamp remote and read the candidate ID/key pair. Use [Capturing `remote_id` and `xor_key`](../README.md#capturing-remote_id-and-xor_key) to check the values. Do not confuse them with the full frame or command byte.
5. Add the device through Home Assistant's ESPHome integration. In the [EYOCEAN integration setup](../README.md#configuration), select its **433MHz RF Transmitter** and enter your captured remote ID and XOR key.

## Capture and transmission behavior

The decoder cannot tell whether a remote belongs to your lamp. Check that the ID/key pair stays the same when you press different buttons. The guides and photo show example values, not defaults for your lamp. Capture does not pair the lamp or set the identity used to transmit commands.

Neither configuration sends lamp commands at boot, but both accept Home Assistant RF transmission requests without a local enable switch. The T-Embed's **Allow RF control** switch only controls its optional local ESPHome lamp buttons. It does not block RF or IR proxy transmissions. Integration buttons use the identity entered in Home Assistant, not the T-Embed YAML's local-button substitutions.

The hardware guides cover wiring, display details and troubleshooting. The [main README](../README.md) covers adapter requirements and the RF protocol.
