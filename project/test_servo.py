from gpiozero import AngularServo
from time import sleep

# Initialize servo
servo = AngularServo(18, min_angle=0, max_angle=180)

# Servo control function
def set_servo(angle):
    servo.angle = angle
    print(f"Servo moved to {angle} degrees")


# Test loop
while True:
    set_servo(0)
    sleep(2)

    set_servo(90)
    sleep(2)

    set_servo(180)
    sleep(2)