from config import NAV


def normalize_heading(angle_deg):
    return angle_deg % 360.0


def normalize_error(angle_deg):
    while angle_deg > 180.0:
        angle_deg -= 360.0
    while angle_deg < -180.0:
        angle_deg += 360.0
    return angle_deg


class ComplementaryHeadingFusion:
    def __init__(self, alpha=NAV.heading_filter_alpha):
        self.alpha = alpha
        self.heading = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self._initialized = False

    def update(self, dt, imu_data, mag_data):
        gyro_z = imu_data.get("gyro_z", 0.0)
        mag_heading = mag_data.get("heading", 0.0)

        if not self._initialized:
            self.heading = normalize_heading(mag_heading)
            self._initialized = True
        else:
            predicted = normalize_heading(self.heading + (gyro_z * dt))
            error = normalize_error(mag_heading - predicted)
            self.heading = normalize_heading(predicted + ((1.0 - self.alpha) * error))

        self.pitch = imu_data.get("pitch", 0.0)
        self.roll = imu_data.get("roll", 0.0)

    def get_orientation(self):
        return {
            "heading": round(self.heading, 2),
            "yaw": round(self.heading, 2),
            "pitch": round(self.pitch, 2),
            "roll": round(self.roll, 2),
        }