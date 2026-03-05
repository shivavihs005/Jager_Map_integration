"""
main_autonomous.py
Entry point for the Jager Autonomous Vehicle system.

Usage:
    cd autonomous_vehicle
    sudo pigpiod             # Start pigpio daemon (required for hardware)
    python main_autonomous.py
"""
import sys
import os
import time
import signal

# Make sure modules resolve from this folder
sys.path.insert(0, os.path.dirname(__file__))

import pigpio

# ── Sensors ──────────────────────────────────────────────────────────────────
from sensors.imu_mpu6500        import IMU_MPU6500
from sensors.magnetometer_qmc5883l import Magnetometer_QMC5883L
from sensors.gps_neo6m          import GPS_NEO6M

# ── Fusion ───────────────────────────────────────────────────────────────────
from fusion.madgwick_filter   import MadgwickFilter
from fusion.ekf_localization  import EKFLocalizer

# ── Navigation ───────────────────────────────────────────────────────────────
from navigation.path_planner  import PathPlanner
from navigation.pure_pursuit  import PurePursuitController

# ── Vehicle ──────────────────────────────────────────────────────────────────
from vehicle.motor_controller import MotorController
from vehicle.steering_servo   import SteeringServo

# ── Brain / Mission ──────────────────────────────────────────────────────────
from brain.state_estimator import StateEstimator
from brain.mission_manager import MissionManager

# ── Dashboard ────────────────────────────────────────────────────────────────
from dashboard.web_server import create_server, run_server
from dashboard.map_stream import MapStream

from vehicle_config import WHEELBASE_M, PURE_PURSUIT_LOOKAHEAD_M, MAX_STEERING_ANGLE_DEG


def main():
    print("=" * 50)
    print("  JAGER AUTONOMOUS  —  Starting Up")
    print("=" * 50)

    # ── Single pigpio connection shared across actuators ──────────────────────
    try:
        pi = pigpio.pi()
        if not pi.connected:
            print("[MAIN] Warning: pigpio daemon not running. Hardware in mock mode.")
            pi = None
    except Exception:
        pi = None
        print("[MAIN] Warning: pigpio unavailable.")

    # ── Sensors ──────────────────────────────────────────────────────────────
    imu = IMU_MPU6500()
    mag = Magnetometer_QMC5883L()
    gps = GPS_NEO6M()

    # Optional calibrations (uncomment on first run)
    # imu.calibrate()
    # mag.calibrate_hard_iron(seconds=15)

    # ── Fusion ───────────────────────────────────────────────────────────────
    madgwick = MadgwickFilter(beta=0.1)
    ekf      = EKFLocalizer()

    # ── Navigation ───────────────────────────────────────────────────────────
    planner   = PathPlanner(reached_threshold_m=0.30)
    pursuit   = PurePursuitController(wheelbase_m=WHEELBASE_M,
                                      lookahead_m=PURE_PURSUIT_LOOKAHEAD_M,
                                      max_steer_deg=MAX_STEERING_ANGLE_DEG)

    # ── Vehicle Actuators ────────────────────────────────────────────────────
    motor = MotorController(pi=pi)
    servo = SteeringServo(pi=pi)

    # ── Brain ─────────────────────────────────────────────────────────────────
    state_est = StateEstimator(imu, mag, gps, madgwick, ekf)
    mission   = MissionManager(state_est, planner, pursuit, motor, servo)

    # ── Dashboard ─────────────────────────────────────────────────────────────
    app, socketio = create_server(mission, state_est, planner, None)
    stream        = MapStream(socketio, state_est, mission, planner)
    # Inject stream reference back
    from dashboard import web_server as _ws
    _ws._stream = stream

    # ── Start background threads ──────────────────────────────────────────────
    state_est.start()
    time.sleep(0.5)   # Let sensors warm up

    mission.start()
    stream.start()

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    def shutdown(sig, frame):
        print("\n[MAIN] Shutting down…")
        mission.stop()
        state_est.stop()
        stream.stop()
        motor.cleanup()
        servo.cleanup()
        if pi:
            pi.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Blocking: run Flask dashboard ────────────────────────────────────────
    print("[MAIN] Dashboard starting — visit http://<pi-ip>:5001")
    run_server()


if __name__ == "__main__":
    main()
