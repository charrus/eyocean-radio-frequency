# EYOCEAN RF Desk Lamp

`eyocean` is a Home Assistant custom integration for 433.92 MHz ASK/OOK desk lamps. Its six stateless buttons use HA's native `radio_frequency` transmitter API, not ESPHome service calls. ESPHome proxy configurations and hardware guides are in `examples/`.

## Dev environment

- Use https://pydevtools.com/handbook/explanation/modern-python-project-setup-guide-for-ai-assistants.md as the authoritative playbook for Python.
- Use Python **3.14.4**, pinned in `.python-version`. The supported range is 3.14.2–3.14.x; Home Assistant requires at least 3.14.2. The code uses Python 3.14 exception syntax.
- Run uv from the repository root (CI uses 0.13.6). It manages `.venv` and installs locked development dependencies:
  ```sh
  uv sync --locked
  uv run --locked prek install
  ```
- Add development dependencies with `uv add --dev`; commit `pyproject.toml` and `uv.lock`. Dependencies belong in `[dependency-groups].dev`, not a separate requirements file. Do not use pip in this workflow.
- Home Assistant, rf-protocols, the HA pytest plugin and Ruff are pinned to exact versions. `[tool.uv] package = false` disables Python package installation; `scripts/package.py` builds the HA release.

## Build and checks

Run the CI checks from the repository root. uv runs each command in the project environment:

```sh
uv run --locked python -m pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check custom_components tests scripts
uv run --locked prek run --all-files
uv run --locked python scripts/package.py
```

- Pytest discovers `tests/`; asyncio mode is `auto`, with function-scoped fixture loops.
- Ruff checks `E`, `F`, and `I`, with a 100-character line limit.
- Packaging uses the version in `custom_components/eyocean/manifest.json`, writes `dist/eyocean-radio-frequency-<version>.zip`, verifies its contents and prints a SHA256.
- The ZIP includes the integration, README and LICENSE, not ESPHome examples. `dist/` is generated and ignored.

## Code map and conventions

- `custom_components/eyocean/protocol.py`: bounded hex parsing, command validation and signed-microsecond waveform encoding; no HA setup logic.
- `config_flow.py`: shared setup/reconfiguration form using `probatio` and HA selectors. Field errors use translation keys; duplicate identities abort the flow.
- `__init__.py`: config-entry validation, button-platform setup/unload and shared transmitter locks in `entry.runtime_data`.
- `button.py`: `EyoceanButton` inherits from `RadioFrequencyTransmitterConsumerEntity` and `ButtonEntity`, and sends through the inherited `_send_command` helper.
- `const.py` holds domain/config keys; UI strings live in `strings.json` and `translations/en.json`.
- Modules use relative imports internally, typed production functions, `async_` names for HA async entry points, and `_attr_*` entity metadata.
- Protocol validation raises `ValueError`; invalid stored setup data raises `ConfigEntryError`. Let transmitter errors propagate; do not report failed presses as successful.
- `tests/test_protocol.py` checks published frames, timings, repeat semantics and malformed input. `tests/test_integration.py` exercises real HA setup and RF helpers with an in-memory transmitter.

## RF invariants and pitfalls

- Never transmit during setup or reconfiguration. The lamp has no feedback channel; do not add confirmed on/off state or absolute brightness controls.
- `repeats` means total transmissions (1–20); `rf_protocols.repeat_count` means additional transmissions. The default total of eight becomes seven in `EyoceanCommand`.
- Remote ID is nonzero, 16-bit; XOR key is 8-bit and may be zero. Hex parsing rejects whitespace, signs, oversized values and full frames. Numeric command validation rejects booleans.
- The remote ID/key pair identifies a remote, regardless of adapter. Store transmitter registry UUIDs so entity renames work.
- All entries sharing a transmitter UUID share one lock. Preserve burst-airtime spacing: the native send call can return before physical transmission finishes.
- `tests/conftest.py` redirects `custom_components.__path__` to this checkout; the HA test plugin otherwise supplies a dummy package. Keep the root `custom_components/__init__.py` test-discovery helper out of install artifacts.
- `tests/test_integration.py` uses the locked HA 2026.10.4 fixture plugin. Run `uv run --no-project --python 3.14.4 --with homeassistant==2026.11.0 --with rf-protocols==4.3.0 python scripts/check_ha_compat.py` for a real, plugin-independent native RF compatibility check; CI runs it for both 2026.10.4 and 2026.11.0. It uses a temporary configuration and an in-memory transmitter, not the live instance. Do not force-install a different HA into the locked fixture environment: the plugin imports version-specific HA internals.
- Initialize the RF consumer with both its legacy UUID attribute and the resolved entity ID required by HA 2026.11. Keep UUIDs in config entries, and reload the entry on transmitter renames to replace the newer consumer's availability subscriptions.
- Tests check software behavior, not physical RF timing, lamp compatibility or response. HA 2026.10.4 lacks the receiver-consumer API available on upstream `dev`.
- Preserve the protocol attribution and `custom_components/eyocean/UPSTREAM_LICENSE.txt` when changing or packaging the integration.

## ESPHome examples

- Use `variant`, never `board`, in ESP32 configurations. Set flash size, PSRAM and hardware pins explicitly instead of relying on board presets.
- Start with `examples/README.md` and the hardware-specific guide. Examples require ESPHome 2026.10.1 or later; it is not in the uv development dependencies or checked by the Python CI workflow.
- `m5stack-atom-lite.yaml` targets the original ESP32 ATOM Lite with external RF TX/RX on GPIO25/GPIO19, not the ATOM S3 Lite.
- `t-embed-cc1101-plus.yaml` uses `variant: ESP32S3`, 16MB flash and octal PSRAM. Preserve Plus-specific pins, startup chip-select/power ordering, antenna routing and CC1101 TX/RX callbacks.
- Both examples use private `secrets.yaml` entries `api_key`, `wifi_ssid`, and `wifi_password`. Generate a device-specific key with `openssl rand -base64 32`; never copy credentials into tracked YAML.
- Keep example remote identities zeroed and optional local lamp controls off at boot. Candidate decodes must not overwrite the configured transmit identity.
- **Allow RF control** only controls local lamp-button scripts. It does not block RF or IR proxy requests. Integration buttons use the identity configured in HA, not YAML substitutions.
- T-Embed validation/build downloads Roboto Mono from Google Fonts unless cached. YAML `!secret` and `!lambda` tags need ESPHome-aware validation, not a generic YAML language server.
- The guides document `esphome config <filename>` for validation and `esphome run <filename>` for compilation/flashing. Do not use `run` for a validation-only task.
- `.gitignore` excludes `secrets.yaml`, `.esphome/`, `.venv/`, caches, logs and `dist/`.
