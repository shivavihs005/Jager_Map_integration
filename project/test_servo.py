import pigpio
import time

SERVO_PIN = 17

MAX_LEFT = 680
CENTER = 1060
MAX_RIGHT = 1460

STEP = 10
DELAY = 0.02

pi = pigpio.pi()

current = CENTER
pi.set_servo_pulsewidth(SERVO_PIN, CENTER)


def move_to(target):
    global current

    if target > current:
        step = STEP
    else:
        step = -STEP

    for pulse in range(current, target, step):
        pi.set_servo_pulsewidth(SERVO_PIN, pulse)
        time.sleep(DELAY)

    pi.set_servo_pulsewidth(SERVO_PIN, target)
    current = target


try:
    while True:

        move_to(MAX_LEFT)
        time.sleep(1)

        move_to(CENTER)
        time.sleep(1)

        move_to(MAX_RIGHT)
        time.sleep(1)

        move_to(CENTER)
        time.sleep(1)

except KeyboardInterrupt:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()

