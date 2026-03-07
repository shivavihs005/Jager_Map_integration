from config import NAV, SERVO


def normalize_error(angle_deg):
    while angle_deg > 180.0:
        angle_deg -= 360.0
    while angle_deg < -180.0:
        angle_deg += 360.0
    return angle_deg


def pulse_from_heading_error(heading_error_deg):
    limited = max(-SERVO.max_heading_error_deg, min(SERVO.max_heading_error_deg, heading_error_deg))
    if limited < 0:
        ratio = abs(limited) / SERVO.max_heading_error_deg
        span = SERVO.pulse_center - SERVO.pulse_left
        return int(SERVO.pulse_center - (span * ratio))
    if limited > 0:
        ratio = limited / SERVO.max_heading_error_deg
        span = SERVO.pulse_right - SERVO.pulse_center
        return int(SERVO.pulse_center + (span * ratio))
    return SERVO.pulse_center


def pwm_from_heading_error(heading_error_deg):
    absolute = abs(heading_error_deg)
    if absolute > 30.0:
        return 30.0
    if absolute > 15.0:
        return 55.0
    return 70.0