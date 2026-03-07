# RC-NAV-01 — System Architecture

> Raspberry Pi 3B · NEO-6M · MPU6500 · QMC5883L · BTS7960 · Pigpio Servo

---

## 1. Layer Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL DASHBOARD                 │
│          (Browser · Leaflet / OSM · OSRM Routing)            │
└─────────────────────────────┬────────────────────────────────┘
                              │  WebSocket / REST (future)
┌─────────────────────────────▼────────────────────────────────┐
│                      APPLICATION LAYER                       │
│   State Machine · Navigation Engine · Path Follower          │
└──────┬──────────────────────┬───────────────────────────┬────┘
       │                      │                           │
┌──────▼──────┐   ┌───────────▼──────────┐   ┌───────────▼────┐
│   PLANNING  │   │   SENSOR FUSION      │   │   CONTROL      │
│  OSRM Route │   │  GPS + IMU + Mag     │   │  Motor + Servo │
│  Waypoints  │   │  Kalman / Compl.     │   │  PWM / pigpio  │
└──────┬──────┘   └───────────┬──────────┘   └───────────┬────┘
       │                      │                           │
┌──────▼──────────────────────▼───────────────────────────▼────┐
│                   HARDWARE ABSTRACTION LAYER                  │
│     /dev/serial0 · /dev/i2c-1 · GPIO (pigpio) · BCM PWM      │
└──────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────┐
│                       PHYSICAL HARDWARE                       │
│   NEO-6M  ·  MPU6500  ·  QMC5883L  ·  BTS7960  ·  Servo     │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. State Machine

```
BOOT ──[click Calibrate]──▶ CALIBRATING
                                │
              ┌─────────────────▼─────────────────┐
              │  1. I²C scan (0x68, 0x0D)          │
              │  2. MPU6500 gyro bias calibration   │
              │  3. QMC5883L hard/soft iron cal     │
              │  4. GPS satellite acquisition       │
              └─────────────────┬─────────────────┘
                                │ all OK
                                ▼
                             READY ◀─────────────────────────────┐
                                │                                │
                      [map click on road]                        │
                                │                                │
               ┌────────────────┼────────────────┐              │
               │ OSRM /nearest  │                │              │
               ▼                ▼                │              │
          DEST_SET         DEST_INVALID ─[re-click]─▶ READY     │
               │                                                 │
    [CALCULATE PATH]                                             │
               │                                                 │
               ▼                                                 │
          CALCULATING ──[OSRM /route]──▶ PATH_READY             │
                                              │                  │
                                    [START NAVIGATION]           │
                                              │                  │
                                              ▼                  │
                                          RUNNING                │
                                              │                  │
                               [reaches last waypoint]           │
                                              │                  │
                                          COMPLETED ──[RESET]────┘
```

---

## 3. Module Breakdown

### 3.1 Sensor HAL (`hal/sensors.py`)

| Module | Interface | Rate | Purpose |
|--------|-----------|------|---------|
| `gps.py` | UART `/dev/serial0` 9600 bd | 1 Hz | Position fix, NMEA parsing |
| `imu.py` | I²C `0x68` | 100 Hz | Accel (m/s²) + Gyro (rad/s) |
| `mag.py` | I²C `0x0D` | 50 Hz | Magnetic heading (°) |

```python
# hal/imu.py — register map (MPU6500)
ACCEL_XOUT_H = 0x3B   # 6 bytes: XH XL YH YL ZH ZL
GYRO_XOUT_H  = 0x43   # 6 bytes
TEMP_OUT_H   = 0x41   # 2 bytes
PWR_MGMT_1   = 0x6B   # wake-up: write 0x00

ACCEL_SCALE  = 9.81 / 4096   # ±8g  → m/s²
GYRO_SCALE   = 1.0  / 131    # ±250°/s → °/s
```

```python
# hal/mag.py — QMC5883L register map
DATA_XL = 0x00   # 6 bytes: XL XH YL YH ZL ZH
STATUS  = 0x06
CTRL1   = 0x09   # Mode=Continuous, ODR=50Hz, RNG=2G, OSR=512
```

```python
# hal/gps.py — NMEA sentence priority
PRIORITY = ['GNGGA', 'GNRMC']  # lat/lon/alt/sats/hdop
```

### 3.2 Sensor Fusion (`fusion/`)

**Complementary filter** (heading):
```
heading = α · (heading + gyro_z · dt) + (1 − α) · mag_heading
α = 0.98   (trust gyro short-term, drift-correct with mag)
```

**Dead-reckoning fallback** (GPS gap > 2 s):
```
pos_new = pos_old + speed · dt · [sin(heading), cos(heading)]
speed   = motor_pwm_pct · MAX_SPEED_MPS
```

### 3.3 Navigation Engine (`nav/`)

```
nav/
├── planner.py     — OSRM REST call, GeoJSON → waypoint list
├── follower.py    — pure-pursuit controller
├── controller.py  — heading error → servo pulse
└── state.py       — global state machine
```

**Pure-pursuit lookahead:**
```python
LOOKAHEAD_M = 0.5          # metres ahead on path
heading_target = bearing(car_pos, lookahead_point)
heading_error  = normalize(heading_target - current_heading)
servo_pulse    = CENTER + heading_error * K_STEER   # K_STEER ≈ 6.3
```

**Speed governor:**
```python
if abs(heading_error) > 30:  pwm = 30   # sharp turn
elif abs(heading_error) > 15: pwm = 55  # gentle turn
else:                          pwm = 70  # straight
```

### 3.4 Actuator HAL (`hal/actuators.py`)

```python
# Servo (pigpio hardware PWM — jitter-free)
GPIO_SERVO   = 17
PULSE_LEFT   = 680    # µs  MAX_LEFT
PULSE_CENTER = 1060   # µs  CENTER
PULSE_RIGHT  = 1460   # µs  MAX_RIGHT
PWM_FREQ     = 50     # Hz

pi.set_servo_pulsewidth(GPIO_SERVO, pulse)

# BTS7960 DC Motor
GPIO_R_EN, GPIO_L_EN   = 23, 24
GPIO_RPWM, GPIO_LPWM   = 13, 12
PWM_FREQ_MOTOR         = 10_000   # Hz

def drive_forward(pwm_pct):
    pi.write(GPIO_R_EN, 1); pi.write(GPIO_L_EN, 1)
    pi.hardware_PWM(GPIO_RPWM, PWM_FREQ_MOTOR, pwm_pct * 10_000)
    pi.hardware_PWM(GPIO_LPWM, PWM_FREQ_MOTOR, 0)
```

---

## 4. Car Physical Model

```
        ← TRACK_WIDTH 0.16 m →
      ┌─────────────────────────┐  ─┐
      │    [FL]         [FR]    │   │
      │     ●─────────────●    │   │ WHEELBASE
      │           ┆           │   │ 0.18 m
      │     ●─────────────●    │   │
      │    [RL]         [RR]    │   │
      └─────────────────────────┘  ─┘
      CAR_LENGTH = 0.27 m
      CAR_WIDTH  = 0.16 m

Minimum turn radius:
  R_min = WHEELBASE / tan(MAX_STEER_ANGLE)
  MAX_STEER_ANGLE ≈ 30°  →  R_min ≈ 0.31 m
```

---

## 5. Directory Structure

```
rc-nav/
├── main.py                  # entry point, event loop
├── config.py                # all constants (pins, limits, PID gains)
├── hal/
│   ├── sensors.py           # unified sensor read
│   ├── imu.py               # MPU6500
│   ├── mag.py               # QMC5883L
│   ├── gps.py               # NEO-6M NMEA parser
│   └── actuators.py         # BTS7960 + pigpio servo
├── fusion/
│   ├── complementary.py     # heading filter
│   └── dead_reckoning.py    # GPS gap fallback
├── nav/
│   ├── state.py             # State enum + transitions
│   ├── planner.py           # OSRM routing
│   ├── follower.py          # pure-pursuit
│   └── controller.py        # PID / bang-bang
├── dashboard/
│   └── index.html           # browser UI (Leaflet + OSM)
└── tests/
    ├── test_sensors.py
    └── test_nav.py
```

---

## 6. Runtime Loop (`main.py`)

```
┌────────── 100 Hz loop ──────────────────────────────────────┐
│  1. Read IMU (accel + gyro)                                  │
│  2. Read MAG (heading raw)                                   │
│  3. Apply complementary filter → fused_heading              │
└──────────────────────────────────────────────────────────────┘

┌────────── 1 Hz loop ─────────────────────────────────────────┐
│  1. Parse GPS NMEA → lat, lon, sats, hdop                    │
│  2. Update dead-reckoning origin if fix OK                   │
└──────────────────────────────────────────────────────────────┘

┌────────── 10 Hz control loop ────────────────────────────────┐
│  if PHASE == RUNNING:                                        │
│    1. Find lookahead point on route                          │
│    2. Compute heading error                                  │
│    3. Set servo pulse  → pigpio                              │
│    4. Set motor PWM    → BTS7960                             │
│    5. Check arrival (dist to dest < 0.5 m)                  │
│    6. Broadcast telemetry to dashboard                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Future Expansion Hooks

| Module | Integration Point |
|--------|-------------------|
| **Camera (Pi Camera v2)** | `hal/camera.py` → lane-keep assist layer above pure-pursuit |
| **LiDAR (RPLidar A1)** | `hal/lidar.py` → obstacle detection, SLAM local map |
| **Obstacle avoidance** | `nav/avoidance.py` — inject detour waypoints into route |
| **RTK GPS** | Drop-in `hal/gps.py` replacement; improves position to <2 cm |
| **Remote override** | WebSocket channel to dashboard `STOP` / `MANUAL` button |

---

## 8. Dependencies

```
# requirements.txt
pigpio>=1.78
smbus2>=0.4
pyserial>=3.5
pynmea2>=1.19
requests>=2.31          # OSRM API
numpy>=1.24             # complementary filter matrix
flask>=3.0              # dashboard HTTP server (optional)
websockets>=12.0        # live telemetry (optional)
```

```bash
# System setup
sudo apt install pigpio python3-pigpio
sudo systemctl enable pigpiod && sudo systemctl start pigpiod
sudo raspi-config  # enable I2C, Serial (disable login shell on serial)
```

---

*Architecture version 1.0 — designed for Pi 3B, extensible to Pi 4/5*
