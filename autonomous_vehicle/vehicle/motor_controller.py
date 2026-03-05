"""
motor_controller.py
BTS7960 DC motor driver using pigpio hardware PWM.
"""
import time

try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False

from vehicle_config import (MOTOR_R_EN, MOTOR_L_EN, MOTOR_RPWM, MOTOR_LPWM,
                            MOTOR_PWM_FREQ)


class MotorController:
    def __init__(self, pi=None):
        """
        pi: shared pigpio.pi() instance. Pass one from main to avoid
            multiple daemon connections.
        """
        self._mock  = not PIGPIO_AVAILABLE
        self._speed = 0.0    # current % (-100 to 100, negative = backward)

        if not self._mock:
            self.pi = pi or pigpio.pi()
            if not self.pi.connected:
                print("[Motor] pigpio daemon not running — mock mode")
                self._mock = True
            else:
                self._setup_pins()
                print("[Motor] BTS7960 initialised via pigpio")
        else:
            self.pi = None
            print("[Motor] pigpio not found — mock mode")

    def _setup_pins(self):
        for pin in (MOTOR_R_EN, MOTOR_L_EN, MOTOR_RPWM, MOTOR_LPWM):
            self.pi.set_mode(pin, pigpio.OUTPUT)
        # Enable bridges
        self.pi.write(MOTOR_R_EN, 1)
        self.pi.write(MOTOR_L_EN, 1)
        # Zero PWM
        self.pi.hardware_PWM(MOTOR_RPWM, MOTOR_PWM_FREQ, 0)
        self.pi.hardware_PWM(MOTOR_LPWM, MOTOR_PWM_FREQ, 0)

    def _set_pwm(self, dutycycle_pct):
        """dutycycle_pct: 0 to 100."""
        dc = int(max(0, min(100, dutycycle_pct)) * 10_000)  # pigpio uses 0-1_000_000
        return dc

    def set_speed(self, speed_pct):
        """
        speed_pct: -100 (full reverse) to +100 (full forward).
        0 = stop.
        """
        speed_pct = max(-100.0, min(100.0, float(speed_pct)))
        self._speed = speed_pct

        if self._mock:
            return

        if speed_pct >= 0:
            self.pi.hardware_PWM(MOTOR_LPWM, MOTOR_PWM_FREQ, 0)
            self.pi.hardware_PWM(MOTOR_RPWM, MOTOR_PWM_FREQ,
                                 self._set_pwm(speed_pct))
        else:
            self.pi.hardware_PWM(MOTOR_RPWM, MOTOR_PWM_FREQ, 0)
            self.pi.hardware_PWM(MOTOR_LPWM, MOTOR_PWM_FREQ,
                                 self._set_pwm(-speed_pct))

    def stop(self):
        self.set_speed(0)

    def get_speed(self):
        return self._speed

    def cleanup(self):
        self.stop()
        if not self._mock and self.pi:
            self.pi.write(MOTOR_R_EN, 0)
            self.pi.write(MOTOR_L_EN, 0)
            self.pi.hardware_PWM(MOTOR_RPWM, MOTOR_PWM_FREQ, 0)
            self.pi.hardware_PWM(MOTOR_LPWM, MOTOR_PWM_FREQ, 0)
        print("[Motor] Cleaned up")
