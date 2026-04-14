# -*- coding: utf-8 -*-
import pigpio
import time

RPWM = 13
LPWM = 12
REN  = 23
LEN  = 24

pi = pigpio.pi()
if not pi.connected:
    print("Error: pigpio daemon not running")
    print("Run: sudo systemctl start pigpiod")
    exit()

pi.set_mode(RPWM, pigpio.OUTPUT)
pi.set_mode(LPWM, pigpio.OUTPUT)
pi.set_mode(REN, pigpio.OUTPUT)
pi.set_mode(LEN, pigpio.OUTPUT)

pi.write(REN, 1)
pi.write(LEN, 1)
pi.set_PWM_frequency(RPWM, 1000)
pi.set_PWM_frequency(LPWM, 1000)

def stop():
    pi.set_PWM_dutycycle(RPWM, 0)
    pi.set_PWM_dutycycle(LPWM, 0)

def forward(speed=150):
    pi.set_PWM_dutycycle(LPWM, 0)
    pi.set_PWM_dutycycle(RPWM, speed)

def reverse(speed=150):
    pi.set_PWM_dutycycle(RPWM, 0)
    pi.set_PWM_dutycycle(LPWM, speed)

def ramp_forward(max_speed=200):
    for speed in range(0, max_speed, 10):
        forward(speed)
        time.sleep(0.1)

def ramp_reverse(max_speed=200):
    for speed in range(0, max_speed, 10):
        reverse(speed)
        time.sleep(0.1)

try:
    print("Starting motor test...")
    ramp_forward(200)
    time.sleep(2)
    stop()
    time.sleep(2)
    ramp_reverse(200)
    time.sleep(2)
    stop()
    time.sleep(2)
    forward(150)
    time.sleep(3)
    stop()
    time.sleep(2)
    reverse(150)
    time.sleep(3)
    stop()
except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    stop()
    pi.stop()
    print("Motor test completed safely")
