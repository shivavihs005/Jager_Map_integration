# Project Code Explanation & Architecture

This document explains the internal working of the **Jager Map Integration** autonomous car software. It details the Python modules, the flow of data, and how the system controls the hardware.

## 1. Architecture Overview

The system is built as a **Flask Web Application** that runs on a Raspberry Pi. It acts as the "Brain" of the car.
- **Frontend (Browser)**: Displays the map, joystick, and controls. It sends commands to the Pi via HTTP API.
- **Backend (Python/Flask)**: Receives commands, processes GPS data, calculates steering/speed, and talks to the hardware.
- **Hardware Layer**: Direct GPIO control of the Steering Servo and DC Motor Driver.

---

## 2. Key Python Modules

### `app.py` (The Web Server)
- **Role**: The entry point. Runs the Flask web server.
- **Functions**:
  - Serves `index.html`.
  - Exposes API endpoints like `/api/control`, `/api/navigate`, `/api/gps`.
  - Handlers user requests and passes them to the `StateMachine` or `Navigator`.

### `car_controller.py` (Hardware Driver)
- **Role**: The lowest level driver. Talk directly to `RPi.GPIO`.
- **Key Methods**:
  - `set_speed(val)`: Controls PWM for DC motors (Forward/Backward).
  - `set_steering(val)`: maps -1.0..1.0 to Servo Duty Cycle.
  - **Safety Logic**: Limits servo range (45°-135°) to prevent chassis damage. Uses a timer to "relax" the servo after moving to save power.

### `navigator.py` (The Pilot)
- **Role**: High-level autonomous driving logic.
- **Logic**:
  - Takes a list of **Waypoints** (Lat/Lng).
  - Reads **GPS Position** from `gps_reader.py`.
  - Calculates **Bearing** (direction to target) and **Heading Error** (difference from current facing).
  - **Steering Control**: Uses a P-Controller (Proportional) to steer towards the target.
  - **Straight Assist**: Detects straight road segments and suppresses small steering jitters for smooth driving.
  - **Smoothing**: Limits how fast the wheels can turn ("turn little by little").

### `state_machine.py` (The Manager)
- **Role**: Manages the global state of the car.
- **States**: `MANUAL`, `AUTONOMOUS`.
- **Config**: Stores global limits like `MAX_SPEED` and `MAX_TURN`.

### `gps_reader.py` (The Sensor)
- **Role**: Reads raw NMEA data from the USB GPS module.
- **Logic**:
  - Parses `$GPRMC` and `$GPGGA` sentences.
  - Filters invalid data.
  - Updates the global `current_location` object with Lat, Lng, Speed, and Heading.

### `turning_test/` (Sub-Project)
- **Role**: A standalone app to strictly test turning logic without the full map stack.
- **Files**:
  - `app.py`: Separate Flask server for the test UI.
  - `turn_manager.py`: Simulates or executes turns to specific Compass Headings (N/S/E/W).
  - `car_driver.py`: A copy of the hardware driver specifically for this test.

---

## 3. Code Flow Examples

### Flow A: Manual Joystick Control
1. **User** moves Javascript Javascript Joystick on phone.
2. **JS** sends `POST /api/control` with `{speed: 50, angle: 0.5}`.
3. **Flask (`app.py`)** receives data.
4. **Flask** calls `car_controller.set_steering(0.5)` and `set_speed(50)`.
5. **Car Controller** generates PWM signals on GPIO pins.
6. **Car** moves.

### Flow B: Autonomous Navigation
1. **User** clicks a destination on the Map.
2. **JS** calculates route using OSRM (Leaflet Routing Machine).
3. **JS** extracts waypoints and sends `POST /api/navigate`.
4. **Flask** triggers `navigator.start_navigation()`.
5. **Navigator Thread** starts a loop:
   - READ `gps_reader.get_location()`.
   - CALCULATE distance and bearing to next waypoint.
   - CALCULATE `steering_angle` = `(Bearing - CurrentHeading) * P_Gain`.
   - SMOOTH the steering (don't snap instantly).
   - CALL `car_controller.set_steering()`.
   - REPEAT every 0.1 seconds.

### Flow C: Turning Test (Compass Calibration)
1. **User** clicks "West" on the Test UI.
2. **Test App** sets `target_heading` to 270°.
3. **Turn Manager Loop**:
   - Compares `current_heading` vs 270°.
   - If `current_heading` < 270°, turn **Left**.
   - Send command to `car_driver`.
   - Wait for sensor update (or simulated update).
   - When `abs(error) < 5°`, STOP.

---

## 4. Hardware Wiring Reference (Implicit in Code)

- **Servo Signal**: GPIO 18 (PWM)
- **Motor Forward**: GPIO 13
- **Motor Backward**: GPIO 12
- **Motor Enable A/B**: GPIO 23, 24 (Always HIGH)
