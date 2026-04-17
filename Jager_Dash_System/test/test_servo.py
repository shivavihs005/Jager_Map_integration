import time
import sys

try:
    import pigpio
except ImportError:
    print("Error: pigpio library not found. Please install it using 'pip install pigpio'.")
    sys.exit(1)

# Configuration from hardware spec
SERVO_PIN = 17
SERVO_MIN = 680   # MAX_LEFT
SERVO_CENTER = 1060
SERVO_MAX = 1460  # MAX_RIGHT
STEP = 10         # Microsecond step per sweep iteration
DELAY = 0.02      # Delay between steps (seconds)

def main():
    print(f"Connecting to pigpio daemon... (Ensure 'sudo pigpiod' is running)")
    pi = pigpio.pi()
    
    if not pi.connected:
        print("Failed to connect to pigpio daemon. Run 'sudo pigpiod' and try again.")
        sys.exit(1)

    print(f"Connected! Testing Servo on GPIO {SERVO_PIN}")
    print(f"Pulse Range: {SERVO_MIN}us -> {SERVO_MAX}us")
    
    try:
        print("Sweeping continuously from 680 us to 1460 us...")
        print("Press Ctrl+C to exit.")
        while True:
            # Sweep Min -> Max
            for pulse in range(SERVO_MIN, SERVO_MAX + 1, STEP):
                pi.set_servo_pulsewidth(SERVO_PIN, pulse)
                print(f"PWM: {pulse} us", end='\r')
                time.sleep(DELAY)
            
            # Sweep Max -> Min
            for pulse in range(SERVO_MAX, SERVO_MIN - 1, -STEP):
                pi.set_servo_pulsewidth(SERVO_PIN, pulse)
                print(f"PWM: {pulse} us", end='\r')
                time.sleep(DELAY)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        print("\nCleaning up...")
        # Reset to center before closing
        pi.set_servo_pulsewidth(SERVO_PIN, SERVO_CENTER)
        time.sleep(0.5)
        # Turn off pulses
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        print("Done.")

if __name__ == "__main__":
    main()
