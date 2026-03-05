import pigpio
import time

SERVO_PIN = 18

pi = pigpio.pi()

def set_servo(angle):
    pulse = 500 + (angle / 180) * 2000   # convert angle to pulse width
    pi.set_servo_pulsewidth(SERVO_PIN, pulse)
    print(f"Servo set to {angle}°")

set_servo(90)

while True:
    time.sleep(1)
