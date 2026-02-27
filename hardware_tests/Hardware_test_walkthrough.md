# Jager Hardware Test — Behavior Controller Walkthrough

## Overview

This document describes the **Behavior Controller** module added to the Jager hardware test stack. It provides high-level driving behaviors (forward, backward, relative yaw turns) controlled from the web dashboard.

---

## Architecture

```
┌─────────────────────────────────────────┐
│              Flask App (app.py)          │
│                                         │
│  /api/state ──────► BehaviorController  │
│  /api/turn_relative ──► .set_relative() │
│  /api/sensors ◄────── .get_data()       │
│  /api/stop ──────► .set_state("IDLE")   │
│                                         │
│  Threads:                               │
│    sensor_loop     100Hz  (IMU)         │
│    gps_loop         20Hz  (GPS serial)  │
│    fusion_loop      20Hz  (IMU+GPS)     │
│    controller_loop  20Hz  (Behavior)    │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  behavior_controller.py                 │
│                                         │
│  States:                                │
│    IDLE · FORWARD · BACKWARD            │
│    TURN_LEFT · TURN_RIGHT               │
│    TURN_RELATIVE (P-controller)         │
│                                         │
│  Angle Math:                            │
│    normalize_angle(angle) → [-180,+180] │
│    calculate_relative_target(cur, Δ)    │
│                                         │
│  P-Controller:                          │
│    error = normalize(target - current)  │
│    steering = clamp(error × Kp, -1, 1)  │
│    Auto-stop when |error| ≤ 3°          │
└─────────────────────────────────────────┘
```

---

## Files Modified / Created

| File | Action | Description |
|------|--------|-------------|
| `behavior_controller.py` | **NEW** | Standalone controller with states, angle math, P-controller |
| `app.py` | **MODIFIED** | Added import, controller thread, `/api/state`, `/api/turn_relative` endpoints |
| `templates/index.html` | **MODIFIED** | Added Behavior Control card, 5 buttons, live controller telemetry |

---

## State Machine

| State | Speed | Steering | Notes |
|-------|-------|----------|-------|
| `IDLE` | 0 | 0 | Car stopped |
| `FORWARD` | `user_speed` | 0 | Straight ahead |
| `BACKWARD` | `-user_speed` | 0 | Reverse |
| `TURN_LEFT` | 25 | -1.0 | Full left, low speed |
| `TURN_RIGHT` | 25 | +1.0 | Full right, low speed |
| `TURN_RELATIVE` | 25 | P-controlled | Proportional yaw tracking |

---

## Relative Turn — How It Works

1. **User presses Turn +90°** → `POST /api/turn_relative {"angle": 90}`
2. Controller reads current `fused_yaw` (e.g. `10°`)
3. Computes `target = normalize(10 + 90) = 100°`
4. Each 20Hz update cycle:
   - `error = normalize(100 - current_yaw)`
   - `steering = clamp(error × 0.015, -1, 1)`
   - Car drives forward at 25% with proportional steering
5. When `|error| ≤ 3°` → `car.stop()`, state → `IDLE`

### Boundary Crossing Example

```
current_yaw = 170°
Turn +90°
target = normalize(170 + 90) = normalize(260) = -100°

error = normalize(-100 - 170) = normalize(-270) = 90°
→ car turns right until reaching -100°
```

---

## Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Kp` | `0.015` | Proportional gain (0.01–0.02 range) |
| `TOLERANCE` | `3.0°` | Angle error threshold for auto-stop |
| `LOW_FORWARD_SPEED` | `25` | Motor power during turns (0–100) |

**Tuning tips:**
- Increase `Kp` for faster response (risk of overshoot)
- Decrease `Kp` for smoother turns (slower convergence)
- Increase `TOLERANCE` if car oscillates near target
- Increase `LOW_FORWARD_SPEED` if car stalls during turns

---

## API Endpoints

### `POST /api/state`
Set the behavior controller state.
```json
{ "state": "FORWARD", "speed": 50 }
```
Valid states: `IDLE`, `FORWARD`, `BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`

### `POST /api/turn_relative`
Start a relative yaw turn.
```json
{ "angle": 90 }
```
Positive = clockwise (right), Negative = counter-clockwise (left)

### `GET /api/sensors` (updated)
Now includes `controller` object:
```json
{
  "controller": {
    "controller_state": "TURN_RELATIVE",
    "target_yaw": 100.0,
    "current_yaw": 45.23,
    "error": 54.77,
    "kp": 0.015
  }
}
```

---

## Dashboard UI

The **Behavior Control** card provides:

| Button | Action |
|--------|--------|
| ▲ Forward | `POST /api/state` → `FORWARD` |
| ▼ Backward | `POST /api/state` → `BACKWARD` |
| ↺ Turn −90° | `POST /api/turn_relative` → `{"angle": -90}` |
| ↻ Turn +90° | `POST /api/turn_relative` → `{"angle": 90}` |
| ■ Stop | `POST /api/state` → `IDLE` |

Live telemetry below the buttons shows:
- **State** — current controller state
- **Target** — target yaw angle
- **Error** — current yaw error (green when ≤3°, red otherwise)

The header state badge now reflects the controller state with color coding.

---

## Testing Procedure

1. **Deploy** — Copy all files to Raspberry Pi, run `python app.py`
2. **Open** — Navigate to `http://<pi-ip>:5001`
3. **Zero IMU** — Press "Zero IMU" to set current heading as 0°
4. **Forward/Backward** — Press behavior buttons, verify movement
5. **Turn +90°** — Press, watch:
   - Badge shows `TURN_RELATIVE`
   - Target/Error telemetry updates live
   - Car turns with decreasing steering
   - Auto-stops near target, badge returns to `IDLE`
6. **Boundary test** — Rotate near ±170°, then turn ±90° to cross the -180/+180 boundary
7. **Emergency Stop** — Verify immediate halt from any state

---

## Thread Safety

- All `fused_yaw` reads go through `data_lock` (shared with `fusion_loop`)
- The controller has its own dedicated 20Hz thread
- State transitions are atomic (single variable assignment)
- The UI polls at 7Hz, never writes to controller state directly
