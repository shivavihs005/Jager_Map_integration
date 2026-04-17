# 🚀 FULL SYSTEM PROMPT — JAGER_DASH AUTONOMOUS VEHICLE

## 🎯 OBJECTIVE

Build a Raspberry Pi-based autonomous vehicle system called **Jager_Dash** with:

* Outdoor autonomous navigation (GPS + map-based waypoints using A*)
* Indoor autonomous navigation (sensor + camera minimal processing)
* Manual control (joystick via web UI)
* Real-time web dashboard with neon futuristic theme

---

## 1. GPS — NEO-6M (Hardware UART)

* VCC → 3.3V (Pin 1)
* GND → GND (Pin 6)
* RX → GPIO14 (TXD)
* TX → GPIO15 (RXD)

Device: `/dev/serial0`
Baud Rate: 9600

---

## 2. IMU — MPU6500 (I2C, Address 0x68)

* VCC → 3.3V
* GND → GND
* SDA → GPIO2
* SCL → GPIO3

---

## 3. Magnetometer — QMC5883L (I2C, Address 0x0D)

* VCC → 3.3V
* GND → GND
* SDA → GPIO2 (shared)
* SCL → GPIO3 (shared)

---

## 4. Motor Driver — BTS7960

* R_EN → GPIO23
* L_EN → GPIO24
* RPWM → GPIO13
* LPWM → GPIO12

---

## 5. Servo (Steering)

* Signal → GPIO17
* VCC → External 5V
* GND → Common GND

Pulse:

* LEFT = 680 µs
* CENTER = 1040 µs
* RIGHT = 1460 µs

---

## 6. SDM15 Energy Meter (Software UART)
Provides voltage, current, etc. No distance readings.
* TX (SDM15) → GPIO21 (RX on Pi)
* RX (SDM15) → GPIO20 (TX on Pi)
* Baud Rate: 9600

---

## 7. USB Camera

* Accessible via `/dev/video0`

---

# 🧠 SOFTWARE ARCHITECTURE

## Backend:

* Python (Flask)
* Runs on Raspberry Pi

## Frontend:

* HTML + CSS + JS
* Neon futuristic UI

## Map:

* OpenStreetMap via Leaflet

## Routing:

* OSRM API (A* Search Algorithm internally)

---

# ⚙️ SYSTEM MODES

## 1. HOME SCREEN

Title: Jager_Dash

Buttons:

* Outdoor Autonomous (Neon Blue)
* Indoor Autonomous (Neon Green)
* Manual Control (Neon Purple)

---

# 🛰️ OUTDOOR AUTONOMOUS MODE

## Behavior:

1. Calibrate sensors
2. Wait for GPS lock
3. Display UI:

### LEFT PANEL (scrollable):

* Back button
* Title: Jager_Dash
* Buttons:

  * Calculate Path
  * Start
  * Stop
  * Resume
  * Reset
* Speed slider
* GPS status

### RIGHT PANEL:

* Interactive map (Leaflet + OpenStreetMap)
* Click to set destination

---

## PATH LOGIC

1. Get route from OSRM:

```
http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}
```

2. Decode → waypoints

3. Simplify waypoints

4. Generate state plan:

* FORWARD
* TURN_LEFT
* TURN_RIGHT

Based on angle between segments

---

## EXECUTION LOOP

Priority:

1. Obstacle detection (SDM15)
2. Waypoint navigation
3. Heading correction (magnetometer)

---

# 🏠 INDOOR AUTONOMOUS MODE

## Layout:

LEFT PANEL + CAMERA FEED

### LEFT PANEL:

* Back button
* Title
* Start / Stop
* Speed slider
* Live SDM15 distance

### RIGHT PANEL:

* Live camera stream

---

## LOGIC:

* Move forward
* If obstacle → stop → avoid
* Use minimal camera:

  * brightness comparison (left vs right)
  * adjust steering

---

# 🎮 MANUAL MODE

## Layout:

Full screen

### Controls:

* Back button
* Joystick (X = steering, Y = speed)
* Speed slider

Use:

* nipplejs joystick library

---

# ⚙️ BACKEND API ROUTES

* `/` → Home
* `/outdoor`
* `/indoor`
* `/manual`

API:

* `/api/route`
* `/api/start`
* `/api/stop`
* `/api/resume`
* `/api/reset`
* `/api/control`
* `/api/sensors`
* `/video` → camera stream

---

# 🧠 STATE MACHINE

States:

* FORWARD
* REVERSE
* TURN_LEFT
* TURN_RIGHT
* STOP

Each state maps to:

* Motor PWM
* Servo angle

---

# 🔄 MAIN LOOP

```
while True:

    read sensors

    if mode == OUTDOOR:
        follow waypoint plan

    elif mode == INDOOR:
        obstacle avoidance + camera guidance

    elif mode == MANUAL:
        joystick control

    execute state
```

---

# 🎨 UI DESIGN (NEON FUTURE)

Colors:

* Background: #0a0a0a
* Blue: #00f0ff
* Green: #00ff9f
* Purple: #9f00ff

Style:

* Glow buttons
* Rounded edges
* Smooth transitions

---

# 🚀 OUTPUT REQUIREMENTS

The system should:

* Auto-start Flask server on Pi boot
* Open browser automatically
* Allow full control from web UI
* Perform real-time navigation
* Switch modes dynamically
* Be modular and extendable

---

# 🔥 FINAL GOAL

A fully working:

* Autonomous navigation system
* With map-based routing (A*)
* Sensor fusion
* Web-based control dashboard

Name: **Jager_Dash**

---
