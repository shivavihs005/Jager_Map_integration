"""
test_servo.py — Standalone script to test servo rotation from 0 to 90 degrees
"""
import time
import RPi.GPIO as GPIO

SERVO_PIN = 18

print("Setting up GPIO...")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# 50Hz PWM frequency for standard RC servos
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

try:
    print("Moving to 0 degrees...")
    duty = 2.5 + (0 / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(2)
    
    print("Moving to 45 degrees...")
    duty = 2.5 + (45 / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(2)

    print("Moving to 90 degrees...")
    duty = 2.5 + (90 / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(2)
    
    print("Test complete.")

except KeyboardInterrupt:
    print("Interrupted by user.")

finally:
    print("Cleaning up...")
    pwm.stop()
    GPIO.cleanup()
