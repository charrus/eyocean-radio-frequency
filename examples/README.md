# ESPHome examples

These configurations turn compatible hardware into a 433.92 MHz ASK/OOK RF proxy for the [EYOCEAN RF Desk Lamp integration](../README.md). Both include a candidate decoder to help capture `remote_id` and `xor_key` from your original remote before configuring Home Assistant.

## Choose an example

| Hardware guide | ESPHome configuration | RF hardware | Capture output | Other features |
|---|---|---|---|---|
| [M5Stack ATOM Lite](m5stack-atom-lite.md) | [m5stack-atom-lite.yaml](m5stack-atom-lite.yaml) | External 433.92 MHz OOK transmitter and receiver required | ESPHome logs | RGB LED control and physical button state |
| [LILYGO T-Embed CC1101 Plus](t-embed-cc1101-plus.md) | [t-embed-cc1101-plus.yaml](t-embed-cc1101-plus.yaml) | Built-in CC1101 | Display, ESPHome logs and decoded identity text sensors | IR proxy, display backlight and optional local lamp buttons |

The ATOM Lite example targets the original ESP32 board, not the ATOM S3 Lite. The T-Embed example uses the **CC1101 Plus** pinout. Check your board revision and follow its guide before wiring or flashing; these configurations are not interchangeable across boards.

## Get started

1. Follow the chosen hardware guide and copy its YAML into your ESPHome configuration directory. Both files require ESPHome **2026.10.1** or later.
2. Customize the device name and provide `api_key`, `wifi_ssid` and `wifi_password` in your private `secrets.yaml`. Generate a device-specific API encryption key with `openssl rand -base64 32`. Keep secrets out of version control.
3. Validate, compile and flash with ESPHome. The T-Embed display uses Google Fonts, so validation/build requires network access unless the font is cached.
4. Press several buttons on your original lamp remote and read the candidate ID/key pair. Follow [Capturing `remote_id` and `xor_key`](../README.md#capturing-remote_id-and-xor_key) to check the values and distinguish them from the full frame and command byte.
5. Add the device through Home Assistant's ESPHome integration. In the [EYOCEAN integration setup](../README.md#configuration), select its **433MHz RF Transmitter** and enter your captured remote ID and XOR key.

## Capture and transmission behavior

Candidate decodes are observations, not proof that a remote belongs to your lamp. Check that the ID/key pair stays consistent across several different button presses. Values shown in the guides and photo are examples, not defaults for your lamp. Capturing never pairs the lamp or automatically sets the transmit identity.

Neither configuration sends a lamp command at boot. Their RF proxy transmitters accept Home Assistant requests without a local enable switch. The T-Embed's **Allow RF control** switch only guards its optional local ESPHome lamp buttons; it does not block RF or IR proxy transmissions. Integration buttons use the identity entered in Home Assistant, independently of the T-Embed YAML's local-button substitutions.

For wiring, display details and troubleshooting, use the individual hardware guides above. For adapter requirements and protocol details, see the [main README](../README.md).
