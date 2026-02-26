"""
imu.py — Madgwick Quaternion-Based IMU for MPU-6500
Provides stable yaw/pitch/roll via quaternion fusion of accel + gyro.
"""

import time
import numpy as np
from math import radians

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

ACCEL_SCALE = 16384.0   # ±2g
GYRO_SCALE = 131.0      # ±250°/s


class IMU:
    def __init__(self):
        self.bus = None
        self.mock_mode = True

        # Quaternion state [w, x, y, z]
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

        # Madgwick filter gain (higher = more accel trust, lower = more gyro trust)
        self.beta = 0.1

        # Timing
        self.last_time = time.time()

        # Raw cached values
        self.accel = np.array([0.0, 0.0, 1.0])
        self.gyro = np.array([0.0, 0.0, 0.0])

        # Gyro bias from calibration
        self.gyro_bias = np.array([0.0, 0.0, 0.0])

        if SMBus is None:
            print("[IMU] No SMBus module found. Running in mock mode.")
            return

        try:
            self.bus = SMBus(1)
            # Wake up MPU-6500
            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            # Gyro ±250°/s
            self.bus.write_byte_data(MPU_ADDR, GYRO_CONFIG, 0x00)
            # Accel ±2g
            self.bus.write_byte_data(MPU_ADDR, ACCEL_CONFIG, 0x00)
            self.mock_mode = False
            print("[IMU] MPU-6500 initialized successfully.")
        except Exception as e:
            print(f"[IMU] Init failed: {e}. Running in mock mode.")
            self.bus = None

    def calibrate(self, samples=500):
        """Average gyro readings at rest to find bias."""
        if self.mock_mode:
            return

        print("[IMU] Calibrating gyro bias... keep car still.")
        total = np.array([0.0, 0.0, 0.0])
        for _ in range(samples):
            _, gyro = self._read_raw()
            total += gyro
            time.sleep(0.004)
        self.gyro_bias = total / samples
        print(f"[IMU] Bias calibrated: {self.gyro_bias}")

    def _read_word(self, reg):
        try:
            high = self.bus.read_byte_data(MPU_ADDR, reg)
            low = self.bus.read_byte_data(MPU_ADDR, reg + 1)
            val = (high << 8) | low
            if val > 32767:
                val -= 65536
            return val
        except Exception:
            return 0

    def _read_raw(self):
        """Read raw accel (g) and gyro (deg/s) values."""
        ax = self._read_word(ACCEL_XOUT_H) / ACCEL_SCALE
        ay = self._read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
        az = self._read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE

        gx = self._read_word(GYRO_XOUT_H) / GYRO_SCALE
        gy = self._read_word(GYRO_XOUT_H + 2) / GYRO_SCALE
        gz = self._read_word(GYRO_XOUT_H + 4) / GYRO_SCALE

        return np.array([ax, ay, az]), np.array([gx, gy, gz])

    def update(self):
        """Read sensors and run one Madgwick filter iteration."""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        if self.mock_mode:
            return

        accel_raw, gyro_raw = self._read_raw()

        # Remove calibrated bias and convert gyro to rad/s
        gyro_corrected = gyro_raw - self.gyro_bias
        gx = radians(gyro_corrected[0])
        gy = radians(gyro_corrected[1])
        gz = radians(gyro_corrected[2])

        self.accel = accel_raw
        self.gyro = gyro_corrected

        # --- Madgwick AHRS Update ---
        q = self.q
        q0, q1, q2, q3 = q

        # Rate of change of quaternion from gyroscope
        q_dot = 0.5 * np.array([
            -q1 * gx - q2 * gy - q3 * gz,
             q0 * gx + q2 * gz - q3 * gy,
             q0 * gy - q1 * gz + q3 * gx,
             q0 * gz + q1 * gy - q2 * gx
        ])

        # Accelerometer correction (gradient descent)
        a = accel_raw.copy()
        a_norm = np.linalg.norm(a)
        if a_norm > 0.01:
            a /= a_norm

            # Objective function
            f = np.array([
                2.0 * (q1 * q3 - q0 * q2) - a[0],
                2.0 * (q0 * q1 + q2 * q3) - a[1],
                2.0 * (0.5 - q1**2 - q2**2) - a[2]
            ])

            # Jacobian
            J = np.array([
                [-2*q2,  2*q3, -2*q0,  2*q1],
                [ 2*q1,  2*q0,  2*q3,  2*q2],
                [ 0,    -4*q1, -4*q2,  0   ]
            ])

            # Gradient step
            step = J.T @ f
            step_norm = np.linalg.norm(step)
            if step_norm > 0:
                step /= step_norm

            q_dot -= self.beta * step

        # Integrate
        q += q_dot * dt
        q /= np.linalg.norm(q)
        self.q = q

    def get_yaw(self):
        """Extract yaw angle from quaternion (degrees, -180 to 180)."""
        q = self.q
        yaw = np.degrees(np.arctan2(
            2.0 * (q[0] * q[3] + q[1] * q[2]),
            1.0 - 2.0 * (q[2]**2 + q[3]**2)
        ))
        return float(yaw)

    def get_pitch(self):
        q = self.q
        pitch = np.degrees(np.arcsin(
            max(-1.0, min(1.0, 2.0 * (q[0] * q[2] - q[3] * q[1])))
        ))
        return float(pitch)

    def get_roll(self):
        q = self.q
        roll = np.degrees(np.arctan2(
            2.0 * (q[0] * q[1] + q[2] * q[3]),
            1.0 - 2.0 * (q[1]**2 + q[2]**2)
        ))
        return float(roll)

    def get_data(self):
        """Return a dict of all IMU outputs."""
        return {
            "yaw": round(self.get_yaw(), 2),
            "pitch": round(self.get_pitch(), 2),
            "roll": round(self.get_roll(), 2),
            "accel": {
                "x": round(float(self.accel[0]), 3),
                "y": round(float(self.accel[1]), 3),
                "z": round(float(self.accel[2]), 3)
            },
            "gyro": {
                "x": round(float(self.gyro[0]), 2),
                "y": round(float(self.gyro[1]), 2),
                "z": round(float(self.gyro[2]), 2)
            }
        }
