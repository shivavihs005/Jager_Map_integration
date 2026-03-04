"""
orientation_fusion.py — Combine MPU6500 and QMC5883 into steady yaw/pitch/roll
"""

class OrientationFusion:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0

        # Complementary filter weights for pitch/roll
        # Trust gyro for short term, accel for long term
        self.alpha_gyro = 0.96
        self.alpha_acc = 0.04

    def update(self, dt, mpu_data, qmc_data):
        """
        Takes dt (delta time), MPU6500 dict, and QMC5883 dict.
        Outputs stable yaw, pitch, roll.
        """
        # --- YAW (from Magnetometer) ---
        # Direct pass-through for this manual version
        self.yaw = qmc_data.get("heading", 0.0)

        # --- PITCH & ROLL (Complementary Filter) ---
        acc_pitch = mpu_data.get("pitch", 0.0)
        acc_roll = mpu_data.get("roll", 0.0)

        gyro_x = mpu_data.get("gyro_x", 0.0)
        gyro_y = mpu_data.get("gyro_y", 0.0)

        # Integrate gyro
        gyro_pitch = self.pitch + (gyro_x * dt)
        gyro_roll = self.roll + (gyro_y * dt)

        # Blend
        self.pitch = (self.alpha_gyro * gyro_pitch) + (self.alpha_acc * acc_pitch)
        self.roll = (self.alpha_gyro * gyro_roll) + (self.alpha_acc * acc_roll)

    def get_orientation(self):
        return {
            "yaw": round(self.yaw, 2),
            "pitch": round(self.pitch, 2),
            "roll": round(self.roll, 2)
        }
