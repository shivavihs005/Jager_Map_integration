# Implementation Plan - Autonomous GPS Rover

The goal is to transform the GPS-tracking application into an autonomous driving system. The car will physically drive to the destination pinned on the map.

## Proposed Architecture
1.  **`car_controller.py`**: A hardware abstraction layer. It wraps the user's provided `RPi.GPIO` code into a clean class (`CarController`) with methods like `drive(speed)` and `steer(angle)`.
2.  **`navigator.py`**: The "brain". It runs a background loop that:
    *   Gets current location from `gps_reader`.
    *   Calculates distance and bearing to the target.
    *   Adjusts the `CarController` steering and speed.
3.  **App & Frontend Integration**:
    *   New "Start Travel" button on the dashboard.
    *   Flask API to receive the target coordinates from the frontend.
    *   Frontend updates to show dynamic status.

## Files to Create/Modify
### [NEW] `car_controller.py`
- encapsulate GPIO setup
- `set_speed(pwm_value)`: Controls DC motor (Forward/Backward/Stop)
- `set_steering(angle)`: Controls Servo (maps -1..1 or angle to duty cycle)

### [NEW] `navigator.py`
- `start_navigation(target_lat, target_lng)`
- `stop_navigation()`
- Math helper functions: `haversine_distance`, `calculate_bearing`
- Control loop: simple P-controller for steering based on heading error.

### [MODIFY] `app.py`
- Initialize `CarController` and `Navigator`.
- Add route `/api/navigate` (POST) to accept destination.
- Add route `/api/stop` (POST).

### [MODIFY] `templates/index.html`
- Add "Start Autonomous Travel" button in the action card.

### [MODIFY] `static/script.js`
- Handle button click.
- Send coordinates to `/api/navigate`.
- Update UI state (Travel/Stop toggle).

## User Review Required
> [!IMPORTANT]
> **Safety Warning**: Autonomous motors can be dangerous. Ensure the car is on a stand (wheels off ground) for first tests.
> **Compass**: This implementation uses "GPS-only" heading provided by change in position. It will not know which way it faces until it starts moving.
