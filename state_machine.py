import threading
from enum import Enum

class CarMode(Enum):
    MANUAL = "MANUAL"
    SEMI_AUTO = "SEMI_AUTO"
    AUTO = "AUTO"

class MotionState(Enum):
    STOPPED = "STOPPED"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    PRECISION_TURN = "PRECISION_TURN"

class StateMachine:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_mode = CarMode.SEMI_AUTO # Use new robust defaults
        self.current_motion_state = MotionState.STOPPED
        self.max_speed = 20  # Percentage 0-100
        self.max_turn = 50   # Percentage 0-100

    def set_mode(self, mode_str):
        try:
            # Add backwards compatibility mapping
            if mode_str == "AUTONOMOUS": 
                mode_str = "SEMI_AUTO" 
                
            new_mode = CarMode(mode_str)
            with self.lock:
                self.current_mode = new_mode
            return True
        except ValueError:
            return False

    def set_limits(self, max_speed, max_turn):
        with self.lock:
            self.max_speed = max(0, min(100, int(max_speed)))
            self.max_turn = max(0, min(100, int(max_turn)))

    def set_motion_state(self, state: MotionState):
        with self.lock:
            self.current_motion_state = state

    def get_state(self):
        with self.lock:
            return {
                "mode": self.current_mode.value,
                "motion_state": self.current_motion_state.value,
                "max_speed": self.max_speed,
                "max_turn": self.max_turn
            }

state_machine = StateMachine()

