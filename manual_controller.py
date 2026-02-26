import time
from car_controller import car

class ManualController:
    def __init__(self):
        self.max_speed = 100.0  # Percentage
        self.max_turn = 100.0   # Percentage
        self.current_mode = "MANUAL"

    def set_limits(self, max_speed, max_turn):
        self.max_speed = float(max_speed)
        self.max_turn = float(max_turn)

    def set_mode(self, mode):
        self.current_mode = mode
        if mode != "MANUAL":
            car.stop()
        return True

    def get_state(self):
        return {
            "mode": self.current_mode,
            "motion_state": "STOPPED",
            "max_speed": self.max_speed,
            "max_turn": self.max_turn
        }

    def execute_control(self, speed_input, angle_input):
        if self.current_mode != "MANUAL":
            return False
            
        # speed_input: -100 to 100
        # angle_input: -1.0 to 1.0
        
        effective_speed = speed_input * (self.max_speed / 100.0)
        
        # angle_percent mapping directly expected by car_controller (-1.0 to 1.0)
        effective_angle_percent = angle_input * (self.max_turn / 100.0)
        
        car.set_speed(effective_speed)
        car.set_steering(effective_angle_percent)
        return True

    def stop(self):
        car.stop()

manual_controller = ManualController()
