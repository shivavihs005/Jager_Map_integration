import pigpio
import time

SERVO_PIN = 17

LEFT = 680
CENTER = 1060
RIGHT = 1460

pi = pigpio.pi()
if not pi.connected:
    print("pigpio not running!")
    exit()

def set_servo(pulse):
    pi.set_servo_pulsewidth(SERVO_PIN, pulse)

try:
    print("Center")
    set_servo(CENTER)
    time.sleep(2)
    print("Left")
    set_servo(LEFT)
    time.sleep(2)
    print("Right")
    set_servo(RIGHT)
    time.sleep(2)
    print("Back to Center")
    set_servo(CENTER)
    time.sleep(2)
finally:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()
