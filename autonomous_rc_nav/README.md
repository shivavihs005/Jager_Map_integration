# Autonomous RC Navigation System

This folder contains a clean autonomous RC car scaffold based on the attached architecture and dashboard reference.

It is designed to run in two modes:

- Mock mode on desktop or Windows for UI and navigation testing.
- Hardware mode on Raspberry Pi with GPS, MPU6500, QMC5883L, BTS7960, and pigpio servo control.

## Structure

```text
autonomous_rc_nav/
├── main.py
├── system.py
├── config.py
├── dashboard/
│   ├── server.py
│   └── templates/
│       └── index.html
├── fusion/
│   ├── complementary.py
│   └── dead_reckoning.py
├── hal/
│   ├── actuators.py
│   ├── gps.py
│   ├── imu.py
│   ├── mag.py
│   └── sensors.py
└── nav/
    ├── controller.py
    ├── follower.py
    ├── planner.py
    └── state.py
```

## Run

```bash
pip install -r autonomous_rc_nav/requirements.txt
python autonomous_rc_nav/main.py
```

Open http://127.0.0.1:5050 in a browser.

## Notes

- OSRM routing uses the public demo endpoint and falls back to a generated straight-line path when routing is unavailable.
- The dashboard keeps the visual style of the supplied Mission Control reference while using a Flask backend instead of a fully local simulation.