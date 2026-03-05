"""
main.py — Clean Rebuild Entry Point
Integrates Motors, Servos, Sensors, Fusion, and Web Server.
"""
import sys
import threading
import time

# --- Import Clean Architecture Modules ---
from motors.motor_controller import MotorController
from motors.steering_servo import SteeringServo

from sensors.mpu6500 import MPU6500
from sensors.qmc5883 import QMC5883
from sensors.neo6m_gps import Neo6MGPS

from fusion.orientation_fusion import OrientationFusion
from web.web_server import start_server

def main():
    print("="*40)
    print(" JAGER: CLEAN REBUILD — MANUAL MODE")
    print("="*40)

    # 1. Initialize Motors and Servo
    motor_controller = MotorController()
    steering_servo = SteeringServo()
    
    # 2. Center Servo
    steering_servo.center()

    # 3. Initialize Sensors
    mpu = MPU6500()
    qmc = QMC5883()
    gps = Neo6MGPS(port="/dev/serial0", baudrate=9600)

    sensor_dict = {
        "mpu6500": mpu,
        "qmc5883": qmc,
        "neo6m": gps
    }

    # 4. Initialize Sensor Fusion
    fusion = OrientationFusion()
    data_lock = threading.Lock()

    # 5. Background Sensor & Fusion Thread
    def sensor_loop():
        last_time = time.time()
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Read raw sensors
            mpu.update()
            qmc.update()
            # GPS is handled in a separate thread if using serial, 
            # but we can poll it here for simplicity
            gps.update() 

            # Fuse data
            with data_lock:
                fusion.update(dt, mpu.get_data(), qmc.get_data())

            # Run at roughly 50Hz for sensor reads
            execution_time = time.time() - now
            sleep_time = 0.02 - execution_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    threading.Thread(target=sensor_loop, daemon=True).start()

    from behavior.turn_manager import AutonomousTurnManager
    turn_manager = AutonomousTurnManager(motor_controller, steering_servo, fusion)

    # 6. Start Web Server
    # Note: start_server blocks the main thread
    start_server(motor_controller, steering_servo, sensor_dict, fusion, data_lock, turn_manager, port=5001)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
