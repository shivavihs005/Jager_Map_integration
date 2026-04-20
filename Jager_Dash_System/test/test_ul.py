import pigpio
import time
import random

# --- CONFIGURATION ---
# Ultrasonic Pins
TRIG = 25
ECHO = 9

# Motor Pins (BTS7960)
RPWM = 13
LPWM = 12
REN  = 23
LEN  = 24

# Servo Pin
SERVO_PIN = 17
SERVO_MIN = 680   # MAX_LEFT
SERVO_CENTER = 1040
SERVO_MAX = 1460  # MAX_RIGHT

# Autonomous Settings
OBSTACLE_DIST_CM = 30  # Distance to trigger backup
SPEED = 120            # Normal forward speed
REVERSE_SPEED = 150    # Speed when backing up

print("Connecting to pigpio daemon...")
pi = pigpio.pi()

if not pi.connected:
    print("Error: pigpio daemon not running")
    print("Run: sudo pigpiod")
    exit()

# --- SETUP PINS ---
# Ultrasonic
pi.set_mode(TRIG, pigpio.OUTPUT)
pi.set_mode(ECHO, pigpio.INPUT)
pi.write(TRIG, 0)

# Motor
pi.set_mode(RPWM, pigpio.OUTPUT)
pi.set_mode(LPWM, pigpio.OUTPUT)
pi.set_mode(REN, pigpio.OUTPUT)
pi.set_mode(LEN, pigpio.OUTPUT)

# Enable motor drivers
pi.write(REN, 1)
pi.write(LEN, 1)
pi.set_PWM_frequency(RPWM, 1000)
pi.set_PWM_frequency(LPWM, 1000)

# --- FUNCTIONS ---
def get_distance():
    # Send 10us pulse to trigger
    pi.write(TRIG, 1)
    time.sleep(0.00001)
    pi.write(TRIG, 0)

    # Wait for echo to go high
    start_time = time.time()
    timeout = start_time + 0.1
    while pi.read(ECHO) == 0 and time.time() < timeout:
        start_time = time.time()
    
    if time.time() >= timeout:
        return 999  # Timeout/No reading

    # Wait for echo to go low
    stop_time = time.time()
    timeout = time.time() + 0.1
    while pi.read(ECHO) == 1 and time.time() < timeout:
        stop_time = time.time()

    if time.time() >= timeout:
        return 999  # Timeout

    # Calculate distance
    elapsed = stop_time - start_time
    distance = (elapsed * 34300) / 2
    return distance

def stop_motors():
    pi.set_PWM_dutycycle(RPWM, 0)
    pi.set_PWM_dutycycle(LPWM, 0)

def forward(speed=SPEED):
    pi.set_PWM_dutycycle(LPWM, 0)
    pi.set_PWM_dutycycle(RPWM, speed)

def reverse(speed=REVERSE_SPEED):
    pi.set_PWM_dutycycle(RPWM, 0)
    pi.set_PWM_dutycycle(LPWM, speed)

def set_steering(position):
    pi.set_servo_pulsewidth(SERVO_PIN, position)

# --- MAIN LOOP ---
try:
    print("Starting Ultrasonic Autonomous Mode...")
    set_steering(SERVO_CENTER)
    time.sleep(1)
    
    last_random_steer_time = time.time()
    
    while True:
        dist = get_distance()
        print(f"Distance: {dist:.1f} cm", end="\r")

        if dist < OBSTACLE_DIST_CM:
            print(f"\n⚠️ Obstacle detected at {dist:.1f} cm! Evading...")
            stop_motors()
            time.sleep(0.5)
            
            # Turn around logic: Steer one way and reverse
            evasion_steer = random.choice([SERVO_MIN, SERVO_MAX])
            set_steering(evasion_steer)
            time.sleep(0.5) # Wait for servo to reach position
            
            # Move back slightly
            print("Backing up and turning...")
            reverse(REVERSE_SPEED)
            time.sleep(1.5)
            
            # Stop and recenter
            stop_motors()
            set_steering(SERVO_CENTER)
            time.sleep(0.5)
            print("Escaped! Resuming forward motion...")

            last_random_steer_time = time.time() # Reset random steer timer

        else:
            # Move forward
            forward(SPEED)
            
            # Randomly drift left, right, or center every 3 seconds
            if time.time() - last_random_steer_time > 3.0:
                random_steer = random.choice([SERVO_MIN, SERVO_CENTER, SERVO_MAX, SERVO_CENTER]) # Bias towards center
                set_steering(random_steer)
                last_random_steer_time = time.time()

        time.sleep(0.05) # Small delay to prevent CPU maxout

except KeyboardInterrupt:
    print("\n🛑 Stopped by user.")

finally:
    stop_motors()
    set_steering(SERVO_CENTER)
    time.sleep(0.5)
    pi.set_servo_pulsewidth(SERVO_PIN, 0) # Turn off servo PWM
    pi.stop()
    print("Safely shut down.")
