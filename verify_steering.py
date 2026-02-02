import time
try:
    from car_controller import car
except ImportError:
    print("Could not import car_controller. Make sure you are in the project directory.")
    exit(1)

def test_steering():
    print("--- Steering Verification Test ---")
    print("1. Center Steering (0.0)")
    car.set_steering(0.0)
    time.sleep(1)
    
    print("2. Turn RIGHT (Logic +1.0)")
    car.set_steering(1.0)
    time.sleep(2)
    
    print("3. Center Steering (0.0)")
    car.set_steering(0.0)
    time.sleep(1)
    
    print("4. Turn LEFT (Logic -1.0)")
    car.set_steering(-1.0)
    time.sleep(2)
    
    car.stop()
    print("--- Test Complete ---")
    print("Did the wheels turn RIGHT when step 2 executed? (y/n)")

if __name__ == "__main__":
    try:
        test_steering()
    except KeyboardInterrupt:
        car.stop()
        print("\nStopped.")
