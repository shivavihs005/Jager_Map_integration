# Jager Hardware Test — Behavior Controller Walkthrough

## Overview

The **Behavior Controller** provides high-level driving behaviors for the Jager autonomous vehicle. The key feature is **TURN_RELATIVE** — a pure rotation maneuver that rotates the vehicle in place without forward drift.

---

## Architecture

```
┌──────────────────────────────────────────┐
│              Flask App (app.py)           │
│                                          │
│  /api/state ──────► BehaviorController   │
│  /api/turn_relative ──► .set_relative()  │
│  /api/sensors ◄────── .get_data()        │
│  /api/stop ──────► .set_state("IDLE")    │
│                                          │
│  Threads:                                │
│    sensor_loop     100Hz  (IMU)          │
│    gps_loop         20Hz  (GPS serial)   │
│    fusion_loop      20Hz  (IMU+GPS)      │
│    controller_loop  20Hz  (Behavior)     │
└──────────────────────────────────────────┘
```

---

## States

| State | Motor | Steering | Description |
|-------|-------|----------|-------------|
| `IDLE` | 0 | 0 (center) | Fully stopped |
| `FORWARD` | `user_speed` | 0 | Straight ahead |
| `BACKWARD` | `-user_speed` | 0 | Reverse |
| `TURN_LEFT_90` | Variable (≤ `ROTATION_SPEED`) | P-controlled (Negative) | 90° pure rotation left using PID |
| `TURN_RIGHT_90`| Variable (≤ `ROTATION_SPEED`) | P-controlled (Positive) | 90° pure rotation right using PID |
| `HEADING_HOLD` | `user_speed` | PID-controlled | Continuously corrects steering against yaw drift |

---

## AI Control Layer & PID

The controller uses a **Drift-Tolerant AI Control Layer**:
1. **GPS Drift Correction**: When vehicle speed > 0.8 m/s, the SensorFusion module gradually blends GPS heading with IMU yaw (`alpha = 0.08`). When stationary or slow, correction freezes to prevent noise issues.
2. **PID Controller**: `behavior_controller.py` uses full PID objects for smooth, anti-windup rotational control. All PIDs are strictly reset on state transitions.

---

## Pure Rotation Turn — How It Works

> **Key insight:** A 90° turn is NOT "drive and steer." It is a **pure rotation maneuver.** The motor provides minimal torque only to rotate the chassis, not to drive forward.

### Sequence

```
Press Turn +90°
    → State = TURN_RIGHT_90
    → Target Yaw = normalize(current + 90)
    → Steering adjusts proportionally (error * Kp)
    → Motor rotation speed drops organically near target
    → When |error| ≤ 3°:
        → Motor = 0 (STOP)
        → Steering = 0 (CENTER)
        → State = IDLE
```

### Smoothed Steering and Speed
- **Steering:** `steering = clamp(error * Kp, -1.0, 1.0)`
  - Scaled smoothly using the error and gain constant.
  - Direction reversed if physically required (`INVERT_STEERING`).
- **Speed:** `speed = ROTATION_SPEED * (abs(error) / 20.0)`
  - Once `< 20°` from the target, rotation torque smoothly ramps down to prevent arc overshoot.

### Boundary Crossing Example

```
current_yaw = 170°,  Turn +90°
target = normalize(170 + 90) = normalize(260) = -100°
error  = normalize(-100 - 170) = normalize(-270) = +90°
→ Full right lock until reaching -100°
```

---

## Tuning Parameters

| Parameter | Default | Location |
|-----------|---------|----------|
| `ROTATION_SPEED` | `20` | `behavior_controller.py` |
| `TOLERANCE` | `3.0°` | `behavior_controller.py` |
| `Kp` | `0.02` | `behavior_controller.py` |

- **Increase `ROTATION_SPEED`** if vehicle stalls during turns
- **Decrease `ROTATION_SPEED`** if vehicle drifts forward during turns
- **Increase `TOLERANCE`** if vehicle oscillates at target

---

## API Endpoints

| Endpoint | Method | Body | Action |
|----------|--------|------|--------|
| `/api/state` | POST | `{"state": "FORWARD", "speed": 50}` | Set state |
| `/api/state` | POST | `{"state": "TURN_LEFT_90"}` | Start 90° pure rotation left |
| `/api/state` | POST | `{"state": "TURN_RIGHT_90"}` | Start 90° pure rotation right |
| `/api/state` | POST | `{"state": "HEADING_HOLD"}` | Continually steer to hold current yaw |
| `/api/stop` | POST | — | Emergency stop |
| `/api/sensors` | GET | — | Includes `controller` telemetry |

---

## Dashboard UI

| Button | Behavior |
|--------|----------|
| ▲ Forward | Hold-to-drive at slider speed |
| ▼ Backward | Hold-to-drive reverse |
| ↺ Turn −90° | Click → pure rotation left using PID, auto-stops |
| ↻ Turn +90° | Click → pure rotation right using PID, auto-stops |
| ⤖ Heading Hold | Click → captures yaw and drives forward, using PID to maintain heading |
| ■ Stop | Immediate halt |

Live telemetry shows: **State**, **Target Yaw**, **Error** (green ≤ 3°, red otherwise)

---

## Testing Procedure

1. Deploy to Raspberry Pi, run `python app.py`
2. Open `http://<pi-ip>:5001`
3. Press **Zero IMU** to set reference heading
4. Press **Turn +90°** — verify:
   - Steering locks right (or smooths via PID), motor slowly rotates
   - No forward drift
   - Auto-stops within ±3° of target
   - Steering returns to center
5. Press **Turn −90°** — verify same behavior left
6. Test **Heading Hold**: 
   - Press, observe the vehicle maintaining an exact straight line
   - Manually perturb/shove the chassis off-axis → wheels should auto-steer to recover heading
7. Test boundary: rotate near ±170°, then turn ±90°
8. Test **Forward (hold)** — verify slider speed works
9. Test **Emergency Stop** — verify immediate halt

---

## Future Enhancements

- **PID control** for smoother final approach
- **Braking ramp** to decelerate near target
- **Gyro-only fine adjustment** for sub-degree precision
- **Drift compensation** using accelerometer feedback
