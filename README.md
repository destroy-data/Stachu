# Stachu-san

Local-first fork of the M5Stack [StackChan](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot) AI desktop robot. This fork throws out everything that could unintentionally connect to the cloud / requires an account / doesn't make sense without the M5/XiaoZhi cloud.

Removed:

- the Flutter mobile app
- the Go relay server (and its MySQL)
- firmware apps that only made sense with the phone app or the cloud: the WS-driven avatar mimicry the app used to puppet the face, the on-device app center, the ezdata/account plumbing, and the app-triggered dance
- every hardcoded M5/XiaoZhi cloud endpoint – no silent fallback, so an empty `CONFIG_OTA_URL` fails the build

Functionally it's still StackChan – the robot keeps the name, wake word, and personality; "Stachu-san" is just the name of this fork.

## How it works

The firmware talks to a self-hosted [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) on your LAN. Two flows:

**At boot – one-time discovery.** Only the OTA URL is baked in. The firmware hits OTA once and the response carries the WebSocket AI endpoint. Repointing the device at a different backend is a single-URL change.

**Per prompt – wake word → response.** The firmware streams mic audio out and TTS audio back in over the same WebSocket; the server routes each prompt to whichever providers you configured.

```
[Stachu-san firmware (ESP32-S3)]
    ▲
    │  OTA:    http://<host>:<port>/xiaozhi/ota/    (once at boot – discovers WS URL)
    │  WS AI:  ws://<host>:<port>/xiaozhi/v1/       (mic audio up, TTS audio down)
    ▼
[xiaozhi-esp32-server]  ←──→ LLM
                        ←──→ ASR
                        ←──→ TTS
```

That's the whole runtime. There is no Go server, no Flutter app, no MySQL, no XiaoZhi/M5 cloud. The LLM, ASR, and TTS providers above are your responsibility to install and point the server at – none of them ship with this repo.

## Repo layout

| Path | Role |
| --- | --- |
| `firmware/` | Robot main-controller firmware (ESP-IDF 5.5.4, C++17, LVGL, Mooncake) |
| `remote/code/` | Optional ESP-NOW remote (separate ESP-IDF project) |
| `extra/` | Config examples, scripts etc. – non-essential |

## Quick start

### 1. Bring up the backend

The backend is **not** vendored in this repo – you install it separately. Clone [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) somewhere on your host and follow its own README for installing Python 3.10 dependencies, downloading model files (FunASR `SenseVoiceSmall`, Silero VAD), and starting the server:

```fish
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server
cd xiaozhi-esp32-server/main/xiaozhi-server
# create data/.config.yaml (see config.yaml for reference), pick LLM/ASR/TTS providers
python app.py
```

For local TTS use the `custom` provider. `extra/piper_http.py` is included as an example Piper HTTP wrapper you can use.

### 2. Build & flash the firmware

Prerequisites: **M5Stack CoreS3** (this fork only targets the CoreS3 variant of StackChan) and **[ESP-IDF 5.5.4](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32s3/get-started/index.html)** installed with its environment loaded (`. $IDF_PATH/export.sh`, or `export.fish` for fish). Target chip is `esp32s3`.

Fetch dependencies (first run only – clones mooncake, xiaozhi-esp32, esp-now, and applies `patches/xiaozhi-esp32.patch`, which adapts upstream xiaozhi-esp32 to this fork's audio/UI):

```fish
cd firmware
python3 fetch_repos.py
```

**Configure.**
`CONFIG_OTA_URL` has no built-in default, and an empty value fails the build. Everything else lives in the same Kconfig tree, including the UI language (default English; see *Default Language* in menuconfig for the full list), default assets, and board options. Two ways to set options:

- **`idf.py menuconfig`** – TUI, browse and toggle any option.
- **`firmware/sdkconfig.defaults.local`** – picked up by `CMakeLists.txt`. Minimal example:

  ```
  CONFIG_OTA_URL="http://<host>:<port>/xiaozhi/ota/"
  ```

**Build & flash:**

```fish
idf.py build
idf.py flash
idf.py monitor
```

> **Migrating from stock M5 firmware + phone app?** Run `idf.py erase-flash` once before the first flash to wipe stale NVS/OTA state – otherwise the old server URLs may linger.

### 3. (Optional) Build the ESP-NOW remote

```fish
cd remote/code
idf.py build flash monitor
```

Pairs with the firmware over ESP-NOW (peer-to-peer, no LAN required).

## Host-side unit tests

```fish
cd firmware
cmake -S tests -B build-host-tests
cmake --build build-host-tests
ctest --test-dir build-host-tests --output-on-failure
```

Currently covers the motion math only.

## Status

**Works today:** firmware boots, discovers the WS endpoint via OTA, and holds a WebSocket to xiaozhi-esp32-server for the duration of the session. Mic audio streams up, TTS audio streams back, LLM/ASR/TTS behave however you configure the server side. The CoreS3's built-in camera is wired to xiaozhi's `explain` endpoint, so vision prompts work if your server routes them. The optional ESP-NOW remote pairs peer-to-peer and drives the robot without needing LAN.

**Not there yet:** no auth on either endpoint – treat this as trusted-LAN only, don't expose it to the internet.

## Origin & license

Forked from [m5stack/StackChan](https://github.com/m5stack/StackChan). MIT-licensed; upstream copyright headers are preserved as required.
