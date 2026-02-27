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
| `TURN_RELATIVE` | `ROTATION_SPEED` (20%) | ±1.0 (full lock) | Pure rotation in place |

---

## Pure Rotation Turn — How It Works

> **Key insight:** A 90° turn is NOT "drive and steer." It is a **pure rotation maneuver.** The motor provides minimal torque only to rotate the chassis, not to drive forward.

### Sequence

```
Press Turn +90°
    → Steering goes full right (+1.0)
    → Motor applies 20% rotational power
    → Yaw approaches target
    → When |error| ≤ 3°:
        → Motor = 0 (STOP)
        → Steering = 0 (CENTER)
        → State = IDLE
```

### Bang-Bang Steering

- `error > 0` → steering = **+1.0** (full right lock)
- `error < 0` → steering = **-1.0** (full left lock)
- No proportional ramping — full lock ensures fastest rotation

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

- **Increase `ROTATION_SPEED`** if vehicle stalls during turns
- **Decrease `ROTATION_SPEED`** if vehicle drifts forward during turns
- **Increase `TOLERANCE`** if vehicle oscillates at target

---

## API Endpoints

| Endpoint | Method | Body | Action |
|----------|--------|------|--------|
| `/api/state` | POST | `{"state": "FORWARD", "speed": 50}` | Set state |
| `/api/turn_relative` | POST | `{"angle": 90}` | Pure rotation turn |
| `/api/stop` | POST | — | Emergency stop |
| `/api/sensors` | GET | — | Includes `controller` telemetry |

---

## Dashboard UI

| Button | Behavior |
|--------|----------|
| ▲ Forward | Hold-to-drive at slider speed |
| ▼ Backward | Hold-to-drive reverse |
| ↺ Turn −90° | Click → pure rotation left, auto-stops |
| ↻ Turn +90° | Click → pure rotation right, auto-stops |
| ■ Stop | Immediate halt |

Live telemetry shows: **State**, **Target Yaw**, **Error** (green ≤ 3°, red otherwise)

---

## Testing Procedure

1. Deploy to Raspberry Pi, run `python app.py`
2. Open `http://<pi-ip>:5001`
3. Press **Zero IMU** to set reference heading
4. Press **Turn +90°** — verify:
   - Steering locks right, motor slowly rotates
   - No forward drift
   - Auto-stops within ±3° of target
   - Steering returns to center
5. Press **Turn −90°** — verify same behavior left
6. Test boundary: rotate near ±170°, then turn ±90°
7. Test **Forward (hold)** — verify slider speed works
8. Test **Emergency Stop** — verify immediate halt

---

## Future Enhancements

- **PID control** for smoother final approach
- **Braking ramp** to decelerate near target
- **Gyro-only fine adjustment** for sub-degree precision
- **Drift compensation** using accelerometer feedback
