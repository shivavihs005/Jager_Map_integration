"""
fusion.py — Complementary Sensor Fusion
Blends IMU quaternion yaw with GPS course-over-ground heading.
"""


class SensorFusion:
    def __init__(self):
        self.yaw = 0.0
        self.speed = 0.0

        # GPS heading blend weight (alpha)
        self.GPS_YAW_WEIGHT = 0.08
        
    @staticmethod
    def normalize_angle(angle):
        """Normalize an angle to the range [-180, +180]."""
        while angle > 180.0:
            angle -= 360.0
        while angle < -180.0:
            angle += 360.0
        return angle

    def update(self, imu_yaw, gps_heading, gps_speed, imu_accel_x=0.0):
        """
        Fuse IMU yaw with GPS heading.
        GPS heading only trusted when vehicle is moving (speed > 0.8 m/s).
        """
        if gps_speed > 0.8:
            # Gradually correct IMU yaw toward GPS heading
            error = self.normalize_angle(gps_heading - imu_yaw)
            self.yaw = self.normalize_angle(imu_yaw + self.GPS_YAW_WEIGHT * error)
        else:
            # Stationary or slow: trust IMU entirely, freeze correction
            self.yaw = imu_yaw

        # Speed: prefer GPS when available, otherwise use 0
        if gps_speed > 0.1:
            self.speed = gps_speed
        else:
            self.speed = 0.0

        return self.yaw

    def get_data(self):
        return {
            "fused_yaw": round(self.yaw, 2),
            "fused_speed": round(self.speed, 2)
        }
