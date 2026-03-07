from hal.gps import Neo6MGPS
from hal.imu import MPU6500
from hal.mag import QMC5883


class SensorSuite:
    def __init__(self):
        self.imu = MPU6500()
        self.mag = QMC5883()
        self.gps = Neo6MGPS()

    @property
    def mock_mode(self):
        return self.imu.mock_mode or self.mag.mock_mode or self.gps.mock_mode

    def update(self):
        self.imu.update()
        self.mag.update()
        self.gps.update()

    def snapshot(self):
        return {
            "imu": self.imu.get_data(),
            "mag": self.mag.get_data(),
            "gps": self.gps.get_data(),
        }