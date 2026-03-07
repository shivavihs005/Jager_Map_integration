from dataclasses import dataclass


@dataclass(frozen=True)
class HomeConfig:
    lat: float = 13.1581
    lon: float = 80.3208


@dataclass(frozen=True)
class SensorConfig:
    imu_hz: float = 50.0
    control_hz: float = 10.0
    gps_timeout_s: float = 2.0
    default_satellites: int = 7
    default_hdop: float = 1.2


@dataclass(frozen=True)
class ServoConfig:
    gpio_pin: int = 17
    pulse_left: int = 680
    pulse_center: int = 1060
    pulse_right: int = 1460
    pwm_frequency_hz: int = 50
    max_heading_error_deg: float = 60.0


@dataclass(frozen=True)
class MotorConfig:
    gpio_r_en: int = 23
    gpio_l_en: int = 24
    gpio_r_pwm: int = 13
    gpio_l_pwm: int = 12
    pwm_frequency_hz: int = 1000
    max_speed_mps: float = 1.2


@dataclass(frozen=True)
class NavigationConfig:
    lookahead_m: float = 2.5
    arrival_threshold_m: float = 1.0
    waypoint_reach_m: float = 1.5
    max_destination_snap_m: float = 80.0
    heading_filter_alpha: float = 0.98


@dataclass(frozen=True)
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 5050
    osrm_base_url: str = "https://router.project-osrm.org"


HOME = HomeConfig()
SENSORS = SensorConfig()
SERVO = ServoConfig()
MOTOR = MotorConfig()
NAV = NavigationConfig()
APP = AppConfig()