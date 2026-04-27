# PiHub

> A local Matter-protocol smart home hub running on a Raspberry Pi 4, built as a Final Year Project for BEng (Hons) Software and Electronic Engineering at Atlantic Technological University (ATU).

---

## Repository Map

| Repo | Description |
|------|-------------|
| [PiHub (this repo)](https://github.com/Tremainm/PiHub-FYP2025) | Hub software — FastAPI backend, React/Vite frontend, Docker Compose deployment |
| [ESP32C3-LED](https://github.com/Tremainm/ESP32C3-LED) | WS2812 RGB LED actuator node firmware (ESP-IDF / ESP-Matter) |
| [ESP32C3-DHT22-Sensor](https://github.com/Tremainm/ESP32C3-DHT22-Sensor) | DHT22 temperature & humidity sensor node firmware with on-device TinyML (ESP-IDF / ESP-Matter) |
| [PiHub-deploy](https://github.com/Tremainm/PiHub-deploy) | Deployment repo — Docker Compose two-stack config and `pihub.sh` startup script for the Pi |
| [train_tinyml](https://github.com/Tremainm/train_tinyml) | TensorFlow/Keras training pipeline for the on-device context classifier |

---

## What is PiHub?

PiHub is a self-hosted smart home controller that commissions, controls, and monitors Matter-compliant IoT devices entirely on a local network — no cloud dependency required. It runs on a Raspberry Pi 4 and exposes a touch-optimised web dashboard served via Nginx, backed by a FastAPI/PostgreSQL stack. Two custom ESP32-C3 firmware nodes connect to the hub over Wi-Fi using the Matter protocol, and one of them runs a TinyML context classifier entirely on-device.

The project covers the full IoT engineering stack: embedded firmware, Matter commissioning, WebSocket integration, containerised deployment, CI/CD, automated testing, and on-device machine learning.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4                       │
│                                                         │
│  ┌──────────────────────┐  ┌───────────────────────┐    │ 
│  │  python-matter-server│  │   App Stack (Docker)  │    │
│  │  (host network mode) │  │                       │    │
│  │  Matter commissioning│  │  FastAPI + PostgreSQL │    │
│  │  WebSocket API       │  │  React/Vite + Nginx   │    │
│  └──────────┬───────────┘  └──────────┬────────────┘    │
│             │  host.docker.internal   │                 │
│             └──────────────┬──────────┘                 │
│                            │ Wi-Fi (Matter/mDNS)        │
└────────────────────────────┼────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
   ┌──────┴──────┐                      ┌───────┴──────┐
   │ ESP32-C3    │                      │  ESP32-C3    │
   │ DHT22 Node  │                      │  LED Node    │
   │ + TinyML    │                      │  WS2812 RGB  │
   └─────────────┘                      └──────────────┘
```

---

## Hardware Nodes

### DHT22 Sensor Node — [`ESP32C3-DHT22-Sensor`](https://github.com/Tremainm/ESP32C3-DHT22-Sensor)

The sensor node runs on an ESP32-C3-DevKitM-1 and reads temperature and humidity from a DHT22 sensor. It exposes these as a Matter Temperature Measurement and Relative Humidity Measurement cluster on the network, meaning the hub can subscribe to live readings using the standard Matter protocol.

On top of sensor reporting, this node runs a three-class TinyML context classifier directly on the microcontroller using TensorFlow Lite Micro (TFLM). The classifier takes normalised temperature and humidity as input and outputs one of three context labels:

| Class | Label | Meaning |
|-------|-------|---------|
| 0 | `HEATING_ON` | Elevated temperature, low humidity |
| 1 | `NORMAL` | Baseline ambient conditions |
| 2 | `WINDOW_OPEN` | Lower temperature, higher humidity |

Because the ESP-IDF `esp_matter` SDK has a confirmed bug ([CHIP SDK #32371](https://github.com/project-chip/connectedhomeip/issues/32371)) where vendor cluster attributes are silently discarded by python-matter-server 8.1.0, the classifier result is encoded into the `MinMeasuredValue` attribute (0x0001) on the humidity endpoint as a workaround. The hub reads this attribute to surface the current context label in the dashboard.

**Key implementation details:**

- Firmware built with ESP-IDF and the ESP-Matter SDK (`release/v1.5`)
- TinyML model: int8 quantised MLP, 2128 bytes, trained on synthetic Gaussian data
- Inference runs entirely on-device — no network call required for classification
- Matter attribute path for context label: `endpoint 2 / cluster 0x0405 / attribute 0x0001`

### WS2812 LED Node — [`ESP32C3-LED`](https://github.com/Tremainm/ESP32C3-LED)

The LED node controls a WS2812 RGB LED connected to the ESP32-C3-DevKitM-1. It presents itself to the Matter network as an Extended Color Light device, supporting on/off, brightness, and full colour control via the Matter Color Control cluster using CIE xy colour space coordinates.

**Key implementation details:**

- The WS2812 LED requires the ESP32's RMT (Remote Control Transceiver) peripheral — not PWM/LEDC — to generate the precise timing pulses the LED protocol demands
- Colour values sent from the frontend go through a full sRGB gamma linearisation → XYZ tristimulus → CIE xy pipeline before being passed to `set_color_xy` on the device
- A firmware-level ordering fix ensures `setColorXY` is applied before `setBrightness` to prevent a white flash when adjusting brightness at a non-white colour

---

## Hub Software

### Backend — FastAPI + PostgreSQL

The backend is a Python FastAPI application that acts as the bridge between the React frontend and the Matter network. It maintains a WebSocket connection to `python-matter-server`, caches the latest device attribute values, and exposes a REST API for the frontend to poll.

Key endpoints include reading live sensor data, sending LED commands (on/off, brightness, colour), retrieving historical readings from PostgreSQL, and surfacing the TinyML context label from the DHT22 node.

Backend test coverage is at 78% overall (`main.py` at 92%, `matter_ws.py` at 58%), with tests written using `pytest` and `AsyncMock` for WebSocket patching.

### Frontend — React + Vite

The frontend is a touch-optimised dashboard built with React and Vite, served through Nginx on the Pi. It is designed to run as a Chromium kiosk on the Pi's touchscreen and polls the FastAPI backend at regular intervals rather than maintaining its own WebSocket connection.

The UI provides live temperature and humidity readings with historical charts, full LED colour/brightness control via a colour picker (with proper sRGB to CIE xy conversion), and a display of the current TinyML context label. It uses `react-icons` throughout and has no hover states — only `:active` states — since it targets a touch display.

Frontend tests are written with Vitest.

### python-matter-server

Matter commissioning and device communication is handled by [`python-matter-server`](https://github.com/home-assistant-libs/python-matter-server), running in its own Docker Compose stack with `network_mode: host`. This is required because Matter relies on Bluetooth (for commissioning) and mDNS multicast (for device discovery), neither of which work correctly inside a bridged Docker network. The app stack reaches it via `host.docker.internal`.

---

## TinyML Pipeline — [`train_tinyml`](https://github.com/Tremainm/train_tinyml)

The training pipeline lives in its own repo and is responsible for producing the quantised model that ships inside the sensor node firmware.

**Pipeline overview:**

1. **Data generation** — Synthetic Gaussian training data is generated for each of the three classes, with realistic temperature/humidity ranges and controlled variance per class
2. **Training** — A simple MLP is trained in TensorFlow/Keras on the synthetic data
3. **Quantisation** — The model is converted to int8 TFLite format using TensorFlow Lite's full-integer post-training quantisation. This reduces the model to 2128 bytes — small enough to fit comfortably in the ESP32-C3's flash
4. **Conversion** — `xxd -i` converts the `.tflite` file to a C byte array that is compiled directly into the firmware
5. **On-device inference** — TensorFlow Lite Micro (TFLM) loads the model from flash and runs inference after each DHT22 reading

Feature normalisation constants are hardcoded into the firmware to match the scaler fitted during training:

```c
// Scaler constants — must match train_tinyml output
const float feature_mins[2]   = {-0.68181818f, -0.89473684f};
const float feature_scales[2] = { 0.05681818f,  0.02288330f};
```

---

## Deployment — [`PiHub-deploy`](https://github.com/Tremainm/PiHub-deploy)

The deploy repo is cloned directly onto the Pi and contains the Docker Compose configuration for both stacks, along with `pihub.sh` — a startup script that brings up the hub services and launches Chromium in kiosk mode on the Pi's Wayland/labwc desktop.

Docker images for the FastAPI backend and React frontend are built and pushed to GHCR via GitHub Actions CI/CD on every push to `main`. The Pi pulls the latest images when `pihub.sh` is run.

**Two-stack architecture:**

```
matter-stack/                 # host-networked — Bluetooth + mDNS
  docker-compose.matter.yml   # python-matter-server

app-stack/                    # bridge-networked
  docker-compose.yml          # FastAPI + PostgreSQL + Nginx/React
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Firmware | ESP-IDF, ESP-Matter (`release/v1.5`), C++ |
| TinyML | TensorFlow/Keras, TFLite int8, TensorFlow Lite Micro |
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL, psycopg |
| Frontend | React, Vite, react-icons, Vitest |
| Matter integration | python-matter-server 8.1.0 (WebSocket) |
| Containerisation | Docker Compose (two-stack), GHCR |
| CI/CD | GitHub Actions |
| Hardware | Raspberry Pi 4, ESP32-C3-DevKitM-1 × 2, DHT22, WS2812 |

---

## Project Structure (this repo)

```
PiHub-FYP2025/
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions — build, test, push to GHCR
├── backend/
│   └── app/
│       ├── main.py           # FastAPI application, REST endpoints
│       ├── matter_ws.py      # python-matter-server WebSocket client
│       ├── models.py         # SQLAlchemy ORM models
│       ├── schemas.py        # Pydantic schemas
│       ├── database.py       # DB engine and session setup
│       └── tests/            # pytest test suite
├── frontend/
│   └── src/
│       ├── api/              # HTTP client modules (devices, sensors, matter)
│       ├── components/       # Reusable UI components (LED, sensor tiles, charts)
│       ├── pages/            # Dashboard, LedControl, SensorHistory, Settings
│       ├── hooks/            # useLedState
│       ├── context/          # ThemeContext
│       ├── config/           # nodeId.config.js — Matter node ID constants
│       └── test/             # Vitest test suite
└── docker-compose.yml        # Local Docker App stack (FastAPI + PostgreSQL + Nginx)
```

---

## Academic Context

Built as my Final Year Project for BEng (Hons) Software and Electronic Engineering at [Atlantic Technological University (ATU)](https://www.atu.ie/), academic year 2025/2026. The project demonstrates end-to-end IoT engineering across embedded firmware, network protocols, backend services, frontend UI, containerisation, CI/CD pipelines, and on-device machine learning.
