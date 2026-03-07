import threading

from config import MOTOR, SERVO

try:
    import pigpio
except ImportError:
    pigpio = None

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


class SteeringServo:
    def __init__(self):
        self._lock = threading.Lock()
        self.mock_mode = pigpio is None
        self.pi = None
        self.current_pulse = SERVO.pulse_center

        if self.mock_mode:
            return

        try:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                self.mock_mode = True
                self.pi = None
            else:
                self.pi.set_servo_pulsewidth(SERVO.gpio_pin, SERVO.pulse_center)
        except Exception:
            self.mock_mode = True
            self.pi = None

    def set_pulse(self, pulse):
        clamped = max(SERVO.pulse_left, min(SERVO.pulse_right, int(pulse)))
        with self._lock:
            self.current_pulse = clamped
            if not self.mock_mode and self.pi:
                self.pi.set_servo_pulsewidth(SERVO.gpio_pin, clamped)

    def center(self):
        self.set_pulse(SERVO.pulse_center)

    def get_state(self):
        with self._lock:
            return {"pulse": self.current_pulse, "mock_mode": self.mock_mode}


class DriveMotor:
    def __init__(self):
        self._lock = threading.Lock()
        self.mock_mode = GPIO is None
        self.current_pwm = 0.0
        self.direction = "STOP"
        self.pwm_fwd = None
        self.pwm_rev = None

        if self.mock_mode:
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup([MOTOR.gpio_r_en, MOTOR.gpio_l_en, MOTOR.gpio_r_pwm, MOTOR.gpio_l_pwm], GPIO.OUT)
            GPIO.output(MOTOR.gpio_r_en, GPIO.HIGH)
            GPIO.output(MOTOR.gpio_l_en, GPIO.HIGH)
            self.pwm_fwd = GPIO.PWM(MOTOR.gpio_r_pwm, MOTOR.pwm_frequency_hz)
            self.pwm_rev = GPIO.PWM(MOTOR.gpio_l_pwm, MOTOR.pwm_frequency_hz)
            self.pwm_fwd.start(0)
            self.pwm_rev.start(0)
        except Exception:
            self.mock_mode = True
            self.pwm_fwd = None
            self.pwm_rev = None

    def move_forward(self, pwm_percent):
        pwm = max(0.0, min(100.0, float(pwm_percent)))
        with self._lock:
            self.current_pwm = pwm
            self.direction = "FWD" if pwm else "STOP"
            if not self.mock_mode and self.pwm_fwd and self.pwm_rev:
                self.pwm_rev.ChangeDutyCycle(0)
                self.pwm_fwd.ChangeDutyCycle(pwm)

    def move_backward(self, pwm_percent):
        pwm = max(0.0, min(100.0, float(pwm_percent)))
        with self._lock:
            self.current_pwm = pwm
            self.direction = "REV" if pwm else "STOP"
            if not self.mock_mode and self.pwm_fwd and self.pwm_rev:
                self.pwm_fwd.ChangeDutyCycle(0)
                self.pwm_rev.ChangeDutyCycle(pwm)

    def stop(self):
        with self._lock:
            self.current_pwm = 0.0
            self.direction = "STOP"
            if not self.mock_mode and self.pwm_fwd and self.pwm_rev:
                self.pwm_fwd.ChangeDutyCycle(0)
                self.pwm_rev.ChangeDutyCycle(0)

    def get_state(self):
        with self._lock:
            return {
                "pwm_percent": self.current_pwm,
                "direction": self.direction,
                "mock_mode": self.mock_mode,
            }